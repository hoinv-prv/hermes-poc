#!/usr/bin/env python3
"""Refresh a Wiki Source Meta against the current source artifact.

Compares the freshly-projected meta with the existing meta, writes a new
draft alongside (`.meta.refresh.md`) OR updates in-place (`--apply`), and
reports whether material change was detected (lookup_keys, summary, size).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    append_maintenance_log,
    extract_sections,
    parse_frontmatter,
    portable_locator,
    read_text,
    write_text,
)

# Reuse build_wiki_source_meta.py by importing it as a module
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Body sections intentionally NOT preserved on refresh:
#  - Profile Mapping: dropped by builder (CR-AIWS-2026-05-024); mirrors frontmatter profile_id.
#  - Artifact Reference: mirrors frontmatter artifact_locator.
_BODY_PRESERVE_DENY = {"profile mapping", "artifact reference"}

_FALLBACK_SUMMARY_RE = re.compile(r"^(phase|scope|version|status)\s*:", re.IGNORECASE)


def _looks_curated_summary(s: str) -> bool:
    """Heuristic: curated summary (worth preserving) vs a mechanical fallback
    line like 'Phase: X'. Curated = long-ish or multi-sentence, not a metadata line."""
    s = (s or "").strip()
    if not s or s.startswith("(no semantic summary"):
        return False
    if _FALLBACK_SUMMARY_RE.match(s):
        return False
    return len(s) >= 60 or s.count(".") >= 2


def _project(artifact: Path, source_id: str, source_type: str, profile: Path,
             title: str | None, summary: str | None = None,
             seed_text: str | None = None) -> str:
    """Run build_wiki_source_meta.py in a subprocess to avoid import coupling.

    `summary`, when provided, is passed through as --summary so a curated summary
    is preserved instead of being regenerated mechanically (Fix 1). `seed_text`,
    when provided, is written to the temp out-file so the builder's refresh-mode
    preserve logic sees the existing meta — keeping a RESOLVED ## Related Sources
    section instead of overwriting it with a fresh scaffold (Fix R1). Builder
    WARNINGs on stderr are surfaced, not swallowed (Fix 4 — guardrail visibility)."""
    import subprocess
    from tempfile import NamedTemporaryFile

    tmp = NamedTemporaryFile(suffix=".md", delete=False)
    tmp.close()
    if seed_text:
        Path(tmp.name).write_text(seed_text, encoding="utf-8")
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "build_wiki_source_meta.py"),
        "--artifact", str(artifact),
        "--source-id", source_id,
        "--source-type", source_type,
        "--profile", str(profile),
        "--out", tmp.name,
        "--mode", "refresh",
    ]
    if title:
        cmd += ["--title", title]
    if summary:
        cmd += ["--summary", summary]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"build_wiki_source_meta failed: {r.stderr}")
    if r.stderr.strip():
        for line in r.stderr.splitlines():
            if line.strip():
                print(f"  [builder] {line.strip()}", file=sys.stderr)
    content = Path(tmp.name).read_text(encoding="utf-8")
    Path(tmp.name).unlink(missing_ok=True)
    return content



def _append_maintenance_log(meta_path: Path, action: str, source_id: str,
                            target_artifact: Path, old_locator: str,
                            new_locator: str, change_summary: str,
                            impact_level: str, review_decision: str,
                            rollback_hint: str) -> None:
    """Append a minimal WSM maintenance log entry.

    This log is traceability support only. It is not promotion approval.
    """
    from datetime import datetime, timezone

    ai_work = None
    for parent in [meta_path.parent, *meta_path.parents]:
        if parent.name == ".ai-work":
            ai_work = parent
            break
    if ai_work is None:
        # Expected path: .ai-work/wiki_sources/meta/<file>
        for parent in meta_path.parents:
            candidate = parent / ".ai-work"
            if candidate.exists():
                ai_work = candidate
                break
    if ai_work is None:
        ai_work = meta_path.parent.parent if meta_path.parent.name == "meta" else meta_path.parent

    log_path = ai_work / "wiki_sources" / "maintenance_log.jsonl"
    # Store portable __PROJECT_ROOT__-relative locators (not absolute paths).
    project_root = ai_work.parent
    entry = {
        "log_id": f"WSMLOG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{source_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "maintenance_model_version": "wsm_v1",
        "action": action,
        "source_id": source_id,
        "target_artifact": portable_locator(target_artifact, project_root),
        "old_locator": portable_locator(old_locator, project_root) if old_locator else "",
        "new_locator": portable_locator(new_locator, project_root) if new_locator else "",
        "change_summary": change_summary,
        "reason": "Wiki Source Meta refresh",
        "impact_level": impact_level,
        "review_decision": review_decision,
        "applied_by": "tool:refresh_wiki_source_meta.py",
        "rollback_hint": rollback_hint,
        "runtime_boundary": "maintenance log records apply/draft; it is not promotion approval",
    }
    append_maintenance_log(log_path, entry)


def _parse_bullets(section_text: str) -> list[str]:
    """Parse a '- key' bullet list section into a list of keys (order-preserving)."""
    out: list[str] = []
    for line in (section_text or "").splitlines():
        s = line.strip()
        if s.startswith("- "):
            v = s[2:].strip()
            if v:
                out.append(v)
    return out


def _dedupe_stable(keys: list[str]) -> list[str]:
    """Case-insensitive de-dup, preserving first-seen casing and order."""
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        lk = k.lower()
        if lk not in seen:
            seen.add(lk)
            out.append(k)
    return out


def _render_bullets(keys: list[str]) -> str:
    return "\n".join(f"- {k}" for k in keys)


_SECTION_HDR_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


def _replace_section(body: str, heading: str, new_content: str) -> str:
    """Replace the body of the named section (keeping its heading) with new_content.
    Line-based; no-op if the heading is not found."""
    lines = body.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        m = _SECTION_HDR_RE.match(lines[i])
        if m and m.group(1).strip() == heading:
            out.append(lines[i])                 # keep heading
            out.extend(new_content.splitlines())  # new section body
            i += 1
            while i < n and not _SECTION_HDR_RE.match(lines[i]):
                i += 1                            # drop old section body
            if i < n:
                out.append("")                    # single blank line before next heading
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")


def _signature(text: str) -> dict:
    meta, body = parse_frontmatter(text)
    sections = extract_sections(body)
    return {
        "summary": sections.get("Summary", "").strip(),
        "lookup_keys": sections.get("Lookup Keys", "").strip(),
        "knowledge_targets": sections.get("Knowledge Targets", "").strip(),
        "artifact_locator": meta.get("artifact_locator", ""),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Refresh Wiki Source Meta")
    p.add_argument("--meta", required=True, help="Existing meta path")
    p.add_argument("--profile", required=True)
    p.add_argument("--apply", action="store_true",
                   help="Overwrite existing meta (default writes .refresh.md draft)")
    p.add_argument("--review-decision", default="draft_created",
                   help="Review decision for traceability; use approved_to_apply when applying after review")
    p.add_argument("--impact-level", default="unknown")
    p.add_argument("--change-summary", default="Refresh Wiki Source Meta from current source artifact.")
    p.add_argument("--regenerate-summary", action="store_true",
                   help="Re-derive summary mechanically instead of preserving the curated one")
    p.add_argument("--regenerate-lookup-keys", action="store_true",
                   help="Re-derive lookup keys mechanically instead of merging (union) with the curated ones")
    ns = p.parse_args()

    meta_path = Path(ns.meta).resolve()
    if not meta_path.exists():
        print(f"error: meta not found: {meta_path}", file=sys.stderr)
        return 2

    old_text = read_text(meta_path)
    old_meta, old_body = parse_frontmatter(old_text)
    old_sections = extract_sections(old_body)
    artifact = Path(old_meta.get("artifact_locator", ""))
    if not artifact.exists():
        print(f"error: artifact locator unreachable: {artifact}", file=sys.stderr)
        return 2

    # Fix 1 — preserve curated Summary unless explicitly regenerating.
    old_summary = old_sections.get("Summary", "").strip()
    preserve_summary = None
    if not ns.regenerate_summary and old_summary:
        preserve_summary = old_summary
        if not _looks_curated_summary(old_summary):
            print(f"WARNING: preserving an old summary that looks low-quality "
                  f"({old_summary[:50]!r}); pass --regenerate-summary to re-derive it.",
                  file=sys.stderr)

    new_text = _project(
        artifact=artifact,
        source_id=old_meta.get("source_id", meta_path.stem),
        source_type=old_meta.get("source_type", "unknown"),
        profile=Path(ns.profile).resolve(),
        title=old_meta.get("title"),
        summary=preserve_summary,
        seed_text=old_text,
    )

    # Preserve curated frontmatter from old meta. Refresh ≠ re-assessment, so the
    # builder's placeholder defaults must neither clobber an assessed value nor
    # bloat a minimal meta with un-assessed stubs.
    new_meta, new_body = parse_frontmatter(new_text)
    _PLACEHOLDERS = ("", "unknown", None, [])

    # (a) Builder always re-emits these with placeholder defaults: keep a
    #     previously-assessed value, else drop the pure placeholder (Fix 5).
    for key in (
        "authority_level", "freshness_status", "source_representation_status",
        "source_representation_caution", "knowledge_value", "intended_ai_use",
        "conversion_method", "conversion_limitations", "representation_type",
    ):
        old_val = old_meta.get(key)
        if old_val not in _PLACEHOLDERS:
            new_meta[key] = old_val
        elif new_meta.get(key) in _PLACEHOLDERS:
            new_meta.pop(key, None)

    # (b) Builder may not emit these; preserve curated value if new lacks it.
    for key in (
        "source_representation_quality_issue", "representation_scope",
        "converted_by", "conversion_date", "representation_locator",
        "original_source_locator",
    ):
        if key in old_meta and key not in new_meta:
            new_meta[key] = old_meta[key]

    new_meta.setdefault("promotion_status", "draft")
    # Fix R2 — reflect review outcome in apply mode; keep draft markers otherwise.
    # An applied, human-approved refresh must not keep claiming "not approved".
    if ns.apply and ns.review_decision == "approved_to_apply":
        new_meta["maintenance_status"] = "active"
        new_meta["review_required"] = False
        new_meta["review_status"] = ns.review_decision
    else:
        new_meta.setdefault("maintenance_status", "needs_review")
        new_meta.setdefault("review_required", True)
        new_meta["review_status"] = "draft_refresh_not_approved"

    # Fix 2 — preserve enriched body sections the builder does not regenerate
    # (e.g. ## Cautions, ## Change Impact Hints, or sections added by other tools).
    new_sections = extract_sections(new_body)
    new_names_lower = {k.strip().lower() for k in new_sections}
    preserved_blocks = [
        (name, content)
        for name, content in old_sections.items()
        if name.strip().lower() not in new_names_lower
        and name.strip().lower() not in _BODY_PRESERVE_DENY
    ]
    if preserved_blocks:
        extra = "".join(f"\n## {name}\n{content}\n" for name, content in preserved_blocks)
        new_body = new_body.rstrip() + "\n" + extra
        print("preserved body sections: " + ", ".join(n for n, _ in preserved_blocks))

    # Fix 6 — preserve/MERGE curated Lookup Keys (union) unless --regenerate-lookup-keys.
    # Mirrors Fix 1 (Summary): the builder always re-emits ## Lookup Keys from mechanical
    # extraction, so without this a refresh DROPS curated keys (screen IDs, cross-fn refs,
    # multi-word domain phrases). Default = union(old curated, new derived), curated first,
    # case-insensitive de-dup → never lose a curated key; new keys are still surfaced.
    if not ns.regenerate_lookup_keys:
        old_lookup = _parse_bullets(old_sections.get("Lookup Keys", ""))
        if old_lookup:
            new_lookup = _parse_bullets(new_sections.get("Lookup Keys", ""))
            merged = _dedupe_stable(old_lookup + new_lookup)
            # CR-AIWS-2026-06-044: re-filter the UNIONED single-token keys against the profile's
            # CURRENT stopword union, so a stopword-config change (project_stopwords.yml /
            # extra_stopwords) propagates to existing metas on a normal refresh — without
            # --regenerate-lookup-keys (which drops ALL curated keys). Multi-word/curated keys kept;
            # fail-open (never drop keys) if the profile/stopwords cannot be resolved.
            try:
                from _common import lookup_key_stopwords, code_key_stopwords
                _prof = Path(ns.profile).resolve()
                _stype = old_meta.get("source_type", "")
                _stop = (code_key_stopwords(_prof) if _stype in ("java_source", "code")
                         else lookup_key_stopwords(_prof))
                merged = [k for k in merged
                          if (" " in k.strip()) or (k.strip().lower() not in _stop)]
            except Exception:  # noqa: BLE001 — never drop keys without a valid stopword union
                pass
            if merged != new_lookup:
                new_body = _replace_section(new_body, "Lookup Keys", _render_bullets(merged))
                new_only = [k for k in new_lookup
                            if k.lower() not in {o.lower() for o in old_lookup}]
                print(f"merged lookup keys: {len(old_lookup)} curated + {len(new_only)} new "
                      f"-> {len(merged)} total (union; --regenerate-lookup-keys to re-derive)")

    from _common import dump_frontmatter, strip_lint_accept
    strip_lint_accept(new_meta)  # reset accepts on rewrite (strip-on-refresh, CR-AIWS-2026-06-065)
    new_text = dump_frontmatter(new_meta) + new_body

    old_sig = _signature(old_text)
    new_sig = _signature(new_text)
    changed = old_sig != new_sig

    if ns.apply:
        backup = meta_path.with_suffix(meta_path.suffix + ".bak")
        shutil.copy2(meta_path, backup)
        write_text(meta_path, new_text)
        rollback_hint = f"Restore backup at {backup} and rebuild Wiki Source Index if needed."
        _append_maintenance_log(
            meta_path=meta_path,
            action="meta_applied",
            source_id=old_meta.get("source_id", meta_path.stem),
            target_artifact=meta_path,
            old_locator=str(backup),
            new_locator=str(meta_path),
            change_summary=ns.change_summary,
            impact_level=ns.impact_level,
            review_decision=ns.review_decision,
            rollback_hint=rollback_hint,
        )
        print(f"applied refresh: {meta_path} (backup at {backup})")
        print(f"rollback_hint: {rollback_hint}")
        print("note: apply writes the file, but does not by itself prove Knowledge Hub promotion/approval.")
    else:
        draft = meta_path.with_suffix(".refresh.md")
        write_text(draft, new_text)
        _append_maintenance_log(
            meta_path=meta_path,
            action="refresh_draft_created",
            source_id=old_meta.get("source_id", meta_path.stem),
            target_artifact=draft,
            old_locator=str(meta_path),
            new_locator=str(draft),
            change_summary=ns.change_summary,
            impact_level=ns.impact_level,
            review_decision="draft_created",
            rollback_hint="Delete draft if rejected; no canonical meta was changed.",
        )
        print(f"draft written: {draft}")
        print("status: draft_created — review required before apply/promotion")

    print(f"material change: {'yes' if changed else 'no'}")
    for k in old_sig:
        if old_sig[k] != new_sig[k]:
            print(f"  field changed: {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
