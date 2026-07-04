#!/usr/bin/env python3
"""Detect which wiki source artifacts may have changed.

Strategy: maintain a snapshot of (size, mtime, sha1) per artifact under
`.ai-work/wiki_sources/.snapshot.json`. On each run, compare the current
state of artifacts referenced in source metas against the snapshot and
report changed / missing / new ones.

Git is NOT required. If `--use-git` is passed and a .git/ is present, we
also include modified files under git's output as a soft signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_ai_work_root, parse_frontmatter, read_text, write_text  # noqa: E402


def _fingerprint(path: Path) -> dict:
    b = path.read_bytes()
    return {
        "size": len(b),
        "mtime": int(path.stat().st_mtime),
        "sha1": hashlib.sha1(b).hexdigest(),
    }


def _git_modified(root: Path) -> set[str]:
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root, capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()
    out: set[str] = set()
    for line in r.stdout.splitlines():
        if len(line) > 3:
            out.add(str((root / line[3:].strip()).resolve()))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Detect changed wiki sources")
    p.add_argument("--refresh-snapshot", action="store_true",
                   help="Write new snapshot after comparing")
    p.add_argument("--use-git", action="store_true")
    p.add_argument("--format", choices=["text", "json"], default="text")
    ns = p.parse_args()

    root = find_ai_work_root(Path.cwd())
    ai_work = root / ".ai-work"
    meta_dir = ai_work / "wiki_sources" / "meta"
    snap_path = ai_work / "wiki_sources" / ".snapshot.json"

    if not meta_dir.is_dir():
        print(f"error: meta dir not found: {meta_dir}", file=sys.stderr)
        return 2

    snapshot_existed = snap_path.exists()
    old_snap: dict[str, dict] = {}
    if snapshot_existed:
        try:
            old_snap = json.loads(snap_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old_snap = {}

    current: dict[str, dict] = {}
    meta_by_sid: dict[str, dict] = {}
    missing: list[str] = []
    for meta_file in sorted(meta_dir.rglob("*.md")):
        meta, _ = parse_frontmatter(read_text(meta_file))
        artifact = Path(meta.get("artifact_locator", ""))
        sid = meta.get("source_id", meta_file.stem)
        meta_by_sid[sid] = meta
        if not artifact.exists():
            missing.append(sid)
            continue
        current[sid] = {"path": str(artifact), **_fingerprint(artifact)}

    changed: list[str] = []
    new: list[str] = []
    for sid, fp in current.items():
        old = old_snap.get(sid)
        if old is None:
            new.append(sid)
        elif old.get("sha1") != fp["sha1"]:
            changed.append(sid)

    removed = [sid for sid in old_snap if sid not in current]

    git_hits: set[str] = set()
    if ns.use_git:
        git_hits = _git_modified(root)

    git_modified = sorted(
        sid for sid, fp in current.items() if fp["path"] in git_hits
    )

    changed_sources: list[dict] = []
    def _record(sid: str, change_type: str, reason: str) -> None:
        fp = current.get(sid, {})
        old_fp = old_snap.get(sid, {})
        meta = meta_by_sid.get(sid, {})
        changed_sources.append({
            "source_id": sid,
            "change_type": change_type,
            "change_signal": reason,
            "artifact_locator": fp.get("path", old_fp.get("path", "")),
            "previous_artifact_locator": old_fp.get("path", ""),
            "original_source_locator": meta.get("original_source_locator", ""),
            "representation_locator": meta.get("representation_locator", meta.get("artifact_locator", "")),
            "source_representation_status": meta.get("source_representation_status", ""),
            "source_representation_caution": meta.get("source_representation_caution", ""),
            "fingerprint_old": old_fp.get("sha1", ""),
            "fingerprint_new": fp.get("sha1", ""),
            "requires_impact_evaluation": change_type != "unchanged",
            "reason": reason,
            "recommended_next_action": (
                "evaluate impact and create review/update candidate if needed"
                if change_type != "unchanged" else "no_action"
            ),
            "candidate_type": "wiki_meta_update_candidate" if change_type != "unchanged" else "",
            "runtime_boundary": "change detection is signal, not approval",
            "maintenance_model_version": "wsm_v1",
        })

    for sid in sorted(new):
        _record(sid, "added", "source appears in current inventory but not previous snapshot")
    for sid in sorted(changed):
        _record(sid, "modified", "source fingerprint changed")
    for sid in sorted(removed):
        _record(sid, "deleted", "source_id existed in previous snapshot but not current inventory")
    for sid in sorted(missing):
        _record(sid, "missing", "Wiki Source Meta artifact_locator is missing/unreachable")
    for sid in sorted(git_modified):
        if sid not in {r["source_id"] for r in changed_sources}:
            _record(sid, "modified", "git reports source path modified")

    result = {
        "changed": sorted(changed),
        "new": sorted(new),
        "removed": sorted(removed),
        "missing_artifacts": sorted(missing),
        "git_modified": git_modified,
        "snapshot_status": "missing_baseline" if not snapshot_existed else "ok",
        "changed_sources": changed_sources,
        "runtime_boundary": "change detection is signal, not approval",
        "recommended_next_action": "evaluate impact and create review/update candidate if needed",
        "candidate_type": "wiki_meta_update_candidate",
        "maintenance_model_version": "wsm_v1",
    }

    if ns.refresh_snapshot:
        write_text(snap_path, json.dumps(current, indent=2, ensure_ascii=False))

    if not snapshot_existed and ns.format == "text":
        print("NOTE: no baseline snapshot (.snapshot.json) found — all sources are "
              "reported as 'new'. This is expected on first run; run with "
              "--refresh-snapshot to initialize the baseline (then 'new' clears).")

    if ns.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for k, v in result.items():
            if k == "changed_sources":
                print("changed_sources:")
                for rec in v:
                    print(f"  - {rec.get('source_id')} [{rec.get('change_type')}] {rec.get('reason')}")
                continue
            if isinstance(v, list):
                print(f"{k}: {', '.join(v) if v else '(none)'}")
            else:
                print(f"{k}: {v}")
    any_changed = bool(changed or new or removed or missing)
    return 0 if not any_changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
