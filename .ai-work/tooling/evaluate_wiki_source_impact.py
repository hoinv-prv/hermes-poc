#!/usr/bin/env python3
"""Evaluate whether a source change likely impacts the wiki.

Input: a set of changed source_ids (from detect_changed_wiki_sources.py or
manual flag). For each, we load the source meta, apply its Source
Interpretation Profile's `impact_rules`, and emit a recommendation:

  - create_update_candidate : wiki candidate update likely needed
  - review_required : entries marked needs_review
  - review_optional       : change, but not expected to impact wiki meaningfully

This tool is heuristic and MUST NOT auto-rewrite wiki entries.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    find_ai_work_root,
    parse_frontmatter,
    read_jsonl,
    read_text,
    resolve_locator,
)


def _load_profile(path: Path) -> dict:
    if not path.exists():
        return {}
    meta, _ = parse_frontmatter("---\n" + read_text(path) + "\n---\n")
    return meta or {}


def _evaluate(meta_path: Path, ai_work: Path) -> dict:
    meta, _ = parse_frontmatter(read_text(meta_path))
    profile_id = meta.get("profile_id", "")
    profile_path = ai_work / "wiki_sources" / "profiles" / f"{profile_id}.yml"
    profile = _load_profile(profile_path) if profile_path.exists() else {}
    default_severity = profile.get("default_impact", "medium")
    knowledge_targets = meta.get("knowledge_targets") or []

    # Cross-ref: find wiki entries that reference this source's artifact_locator
    referring: list[str] = []
    wiki_root = ai_work / "wiki"
    if wiki_root.is_dir():
        artifact = meta.get("artifact_locator", "")
        for f in wiki_root.rglob("*.md"):
            try:
                text = read_text(f)
            except OSError:
                continue
            if artifact and artifact in text:
                referring.append(str(f))

    source_representation_status = meta.get("source_representation_status", "")
    if source_representation_status in {"partial", "needs_review", "failed"}:
        default_severity = "high"
        recommendation = "blocked_source_representation_issue"
    elif source_representation_status == "unknown":
        default_severity = "unknown"
        recommendation = "human_check_required"
    elif default_severity == "high" or referring:
        recommendation = "create_update_candidate"
    elif default_severity == "low" and not referring:
        recommendation = "review_optional"
    else:
        recommendation = "review_required"

    review_required = default_severity in {"medium", "high", "unknown"} or recommendation in {
        "refresh_meta_draft", "create_update_candidate", "human_check_required",
        "blocked_source_representation_issue", "review_required",
    }
    candidate_type = ""
    if recommendation in {"create_update_candidate", "review_required", "human_check_required"}:
        candidate_type = "wiki_meta_update_candidate"
    if recommendation == "blocked_source_representation_issue":
        candidate_type = "source_representation_issue"

    return {
        "source_id": meta.get("source_id"),
        "title": meta.get("title", ""),
        "source_type": meta.get("source_type", ""),
        "profile_id": profile_id,
        "change_type": "unknown",
        "severity": default_severity,
        "impact_level": default_severity,
        "knowledge_targets": knowledge_targets,
        "referring_wiki_entries": referring,
        "recommendation": recommendation,
        "candidate_type": candidate_type,
        "suggested_target": "wiki_meta" if candidate_type == "wiki_meta_update_candidate" else (
            "source_representation" if candidate_type == "source_representation_issue" else ""
        ),
        "reason": "profile/default impact and referring wiki entries evaluated",
        "next_action": (
            "resolve source representation issue before relying on source evidence"
            if recommendation == "blocked_source_representation_issue"
            else ("create refresh draft and review" if review_required else "review optional")
        ),
        "review_required": review_required,
        "blocking_current_task": recommendation == "blocked_source_representation_issue",
        "affected_meta_locator": str(meta_path),
        "affected_index_locator": "",
        "affected_artifact_locator": meta.get("artifact_locator", ""),
        "related_sources": meta.get("related_sources", []),
        "runtime_boundary": "impact evaluation is signal/recommendation, not approval",
        "maintenance_model_version": "wsm_v1",
        "source_representation_status": source_representation_status,
        "source_representation_caution": meta.get("source_representation_caution", ""),
        "conversion_limitations": meta.get("conversion_limitations", []),
        "verification_level": (
            "source_verified" if source_representation_status in {"complete", "not_applicable"}
            else "source_verified_with_caveat" if source_representation_status == "partial"
            else "representation_reviewed"
        ),
        "source_verification_boundary": "AI can only verify what is present in the AIWS-readable representation unless HUMAN verifies original",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate wiki source change impact")
    p.add_argument("--source-ids", nargs="+", required=True,
                   help="One or more source_ids to evaluate")
    p.add_argument("--format", choices=["text", "json"], default="text")
    ns = p.parse_args()

    ai_work = find_ai_work_root(Path.cwd()) / ".ai-work"
    wiki_sources = ai_work / "wiki_sources"
    index_paths = [wiki_sources / "index.jsonl"]
    local_idx = wiki_sources / "index.local.jsonl"
    if local_idx.exists():
        index_paths.append(local_idx)

    index_paths = [p for p in index_paths if p.exists()]
    if not index_paths:
        print("error: no index file found", file=sys.stderr)
        return 2

    index: dict = {}
    for idx_path in index_paths:
        index.update({r["source_id"]: r for r in read_jsonl(idx_path)})
    results: list[dict] = []
    for sid in ns.source_ids:
        entry = index.get(sid)
        if not entry:
            results.append({"source_id": sid, "error": "not in index"})
            continue
        meta_path = resolve_locator(entry.get("meta_locator", ""), ai_work.parent)
        if not meta_path.exists():
            results.append({"source_id": sid, "error": "meta missing"})
            continue
        results.append(_evaluate(meta_path, ai_work))

    if ns.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            if "error" in r:
                print(f"- {r['source_id']}: ERROR {r['error']}")
                continue
            print(f"- {r['source_id']} [{r.get('impact_level', r.get('severity'))}] → {r['recommendation']}")
            if r.get("next_action"):
                print(f"    next_action: {r['next_action']}")
            if r.get("candidate_type"):
                print(f"    candidate_type: {r['candidate_type']}")
            if r.get("review_required") is not None:
                print(f"    review_required: {r['review_required']}")
            if r.get("blocking_current_task") is not None:
                print(f"    blocking_current_task: {r['blocking_current_task']}")
            if r.get("source_representation_status"):
                print(f"    representation: {r['source_representation_status']}")
            if r.get("source_representation_caution"):
                print(f"    caution: {r['source_representation_caution']}")
            if r["referring_wiki_entries"]:
                for e in r["referring_wiki_entries"]:
                    print(f"    referring: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
