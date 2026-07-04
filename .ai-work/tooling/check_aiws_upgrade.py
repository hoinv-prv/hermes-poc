#!/usr/bin/env python3
"""AIWS upgrade safety check — snapshot protected zones before upgrade,
verify no degradation after upgrade.

Usage:
    python check_aiws_upgrade.py --snapshot        # run BEFORE upgrade
    python check_aiws_upgrade.py --verify          # run AFTER upgrade
    python check_aiws_upgrade.py --clean           # remove snapshot file
    python check_aiws_upgrade.py --status          # show current zone state (no snapshot needed)

Exit codes: 0 OK, 1 degradation detected, 2 error.

Protected zones checked:
  truth/              — file checksums must not change (CRITICAL)
  wiki_sources/       — index entries and meta files must not be lost
  wiki/               — project wiki output dirs must not be deleted
  aip/exec|plans|local/ — AIP history files must not be deleted
  workspaces/         — task workspace dirs must not be deleted
  .claude/skills/     — skill dirs and SKILL.md must not be deleted
  personal_notebook/  — must not be deleted if it existed
  history/            — file count must not drop significantly
  settings.local.json — must not be modified by upgrade
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from _common import find_ai_work_root

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

SNAPSHOT_FILENAME = ".ai-work/upgrade_snapshot.json"
SNAPSHOT_VERSION = 1
HISTORY_DROP_THRESHOLD = 0.95  # warn if history drops below 95% of previous count


# ---------- helpers ----------

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def jsonl_field_values(path: Path, field: str) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            val = json.loads(ln).get(field)
            if val is not None:
                out.append(str(val))
        except json.JSONDecodeError:
            pass
    return out


def list_files_rel(base: Path, suffix: str | None = None) -> list[str]:
    if not base.exists():
        return []
    return sorted(
        f.relative_to(base).as_posix()
        for f in base.rglob("*")
        if f.is_file() and (suffix is None or f.suffix == suffix)
    )


def list_subdirs(base: Path) -> list[str]:
    if not base.exists():
        return []
    return sorted(d.name for d in base.iterdir() if d.is_dir())


def list_skills(skills_dir: Path) -> dict[str, bool]:
    """skill_name -> has_SKILL_md"""
    if not skills_dir.exists():
        return {}
    return {
        d.name: (d / "SKILL.md").exists()
        for d in sorted(skills_dir.iterdir())
        if d.is_dir()
    }


def file_count(base: Path) -> int:
    if not base.exists():
        return 0
    return sum(1 for f in base.rglob("*") if f.is_file())


# ---------- snapshot ----------

def take_snapshot(project_root: Path) -> dict[str, Any]:
    ai_work = project_root / ".ai-work"
    claude_dir = project_root / ".claude"
    wiki_src = ai_work / "wiki_sources"

    def truth_checksums() -> dict[str, str]:
        truth_dir = ai_work / "truth"
        if not truth_dir.exists():
            return {}
        return {
            f.relative_to(truth_dir).as_posix(): sha256_file(f)
            for f in sorted(truth_dir.rglob("*"))
            if f.is_file()
        }

    settings_local = claude_dir / "settings.local.json"

    snap: dict[str, Any] = {
        "version": SNAPSHOT_VERSION,
        "zones": {
            "truth": truth_checksums(),
            "wiki_index": {
                "count": count_jsonl(wiki_src / "index.jsonl"),
                "source_paths": jsonl_field_values(wiki_src / "index.jsonl", "source_path"),
            },
            "wiki_meta": list_files_rel(wiki_src / "meta"),
            "wiki_local": {
                "exists": (wiki_src / "index.local.jsonl").exists(),
                "count": count_jsonl(wiki_src / "index.local.jsonl"),
            },
            "wiki_project": list_subdirs(ai_work / "wiki"),
            "aip_exec": list_files_rel(ai_work / "aip" / "exec", ".md"),
            "aip_plans": list_files_rel(ai_work / "aip" / "plans", ".md"),
            "aip_local": list_files_rel(ai_work / "aip" / "local", ".md"),
            "workspaces": list_subdirs(ai_work / "workspaces"),
            "skills": list_skills(claude_dir / "skills"),
            "history_file_count": file_count(ai_work / "history"),
            "personal_notebook": {
                "exists": (ai_work / "personal_notebook").exists(),
                "file_count": file_count(ai_work / "personal_notebook"),
            },
            "settings_local": {
                "exists": settings_local.exists(),
                "checksum": sha256_file(settings_local) if settings_local.exists() else None,
            },
        },
    }
    return snap


def print_snapshot_summary(snap: dict[str, Any]) -> None:
    z = snap["zones"]
    print(f"  truth files:          {len(z.get('truth', {}))}")
    print(f"  wiki index entries:   {z['wiki_index']['count']}")
    print(f"  wiki meta files:      {len(z.get('wiki_meta', []))}")
    print(f"  wiki local entries:   {z['wiki_local']['count']}")
    print(f"  wiki/ output dirs:    {len(z.get('wiki_project', []))}")
    print(f"  aip/exec files:       {len(z.get('aip_exec', []))}")
    print(f"  aip/plans files:      {len(z.get('aip_plans', []))}")
    print(f"  aip/local files:      {len(z.get('aip_local', []))}")
    print(f"  workspaces:           {len(z.get('workspaces', []))}")
    print(f"  skills:               {len(z.get('skills', {}))}")
    print(f"  history files:        {z.get('history_file_count', 0)}")
    nb = z.get("personal_notebook", {})
    print(f"  personal_notebook:    {'yes' if nb.get('exists') else 'no'} ({nb.get('file_count', 0)} files)")
    sl = z.get("settings_local", {})
    print(f"  settings.local.json:  {'yes' if sl.get('exists') else 'no'}")


# ---------- verify ----------

def verify_snapshot(snap: dict[str, Any], project_root: Path) -> tuple[list[str], list[str], list[str]]:
    """Returns (errors, warnings, infos)."""
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []
    ai_work = project_root / ".ai-work"
    claude_dir = project_root / ".claude"
    wiki_src = ai_work / "wiki_sources"
    z = snap["zones"]

    # 1. Truth — CRITICAL: any modification means upgrade touched protected files
    truth_dir = ai_work / "truth"
    for rel, old_hash in z.get("truth", {}).items():
        f = truth_dir / rel
        if not f.exists():
            errors.append(f"[CRITICAL] truth/{rel}: deleted by upgrade")
        elif sha256_file(f) != old_hash:
            errors.append(f"[CRITICAL] truth/{rel}: modified by upgrade (checksum mismatch)")

    # 2. Wiki index entries
    idx_path = wiki_src / "index.jsonl"
    old_wi = z.get("wiki_index", {})
    old_wi_count = old_wi.get("count", 0)
    new_wi_count = count_jsonl(idx_path)
    if new_wi_count < old_wi_count:
        errors.append(f"wiki_sources/index.jsonl: entries lost {old_wi_count} → {new_wi_count}")
    old_paths = set(old_wi.get("source_paths", []))
    lost_paths = old_paths - set(jsonl_field_values(idx_path, "source_path"))
    for p in sorted(lost_paths):
        errors.append(f"wiki_sources/index.jsonl: source_path removed: {p}")
    if new_wi_count > old_wi_count:
        infos.append(f"wiki index: +{new_wi_count - old_wi_count} new entries")

    # 3. Wiki meta files
    meta_dir = wiki_src / "meta"
    for rel in z.get("wiki_meta", []):
        if not (meta_dir / rel).exists():
            errors.append(f"wiki_sources/meta/{rel}: deleted by upgrade")
    new_meta_count = len(list_files_rel(meta_dir))
    old_meta_count = len(z.get("wiki_meta", []))
    if new_meta_count > old_meta_count:
        infos.append(f"wiki meta: +{new_meta_count - old_meta_count} new files")

    # 4. Wiki local index
    old_wl = z.get("wiki_local", {})
    local_idx = wiki_src / "index.local.jsonl"
    if old_wl.get("exists"):
        if not local_idx.exists():
            errors.append("wiki_sources/index.local.jsonl: deleted by upgrade")
        else:
            new_local = count_jsonl(local_idx)
            old_local = old_wl.get("count", 0)
            if new_local < old_local:
                errors.append(f"wiki_sources/index.local.jsonl: entries lost {old_local} → {new_local}")

    # 5. Wiki project output dirs (.ai-work/wiki/)
    wiki_dir = ai_work / "wiki"
    for name in z.get("wiki_project", []):
        if not (wiki_dir / name).is_dir():
            errors.append(f".ai-work/wiki/{name}/: directory deleted by upgrade")

    # 6. AIP exec / plans / local
    for zone_key, subdir, label in [
        ("aip_exec",   ai_work / "aip" / "exec",  "aip/exec"),
        ("aip_plans",  ai_work / "aip" / "plans", "aip/plans"),
        ("aip_local",  ai_work / "aip" / "local", "aip/local"),
    ]:
        for rel in z.get(zone_key, []):
            if not (subdir / rel).exists():
                errors.append(f"{label}/{rel}: deleted by upgrade")

    # 7. Workspaces
    for name in z.get("workspaces", []):
        if not (ai_work / "workspaces" / name).is_dir():
            errors.append(f"workspaces/{name}/: deleted by upgrade")

    # 8. Skills
    skills_dir = claude_dir / "skills"
    old_skills: dict[str, bool] = z.get("skills", {})
    for skill_name, had_skill_md in old_skills.items():
        skill_dir = skills_dir / skill_name
        if not skill_dir.is_dir():
            errors.append(f".claude/skills/{skill_name}/: deleted by upgrade")
        elif had_skill_md and not (skill_dir / "SKILL.md").exists():
            errors.append(f".claude/skills/{skill_name}/SKILL.md: deleted by upgrade")
    new_skill_count = len(list_skills(skills_dir))
    if new_skill_count > len(old_skills):
        infos.append(f"skills: +{new_skill_count - len(old_skills)} new skills added")

    # 9. History — soft check
    old_hist = z.get("history_file_count", 0)
    if old_hist > 0:
        new_hist = file_count(ai_work / "history")
        if new_hist < old_hist * HISTORY_DROP_THRESHOLD:
            warnings.append(
                f"history: file count dropped {old_hist} → {new_hist} "
                f"(>{int((1 - HISTORY_DROP_THRESHOLD) * 100)}% loss)"
            )

    # 10. Personal notebook
    old_nb = z.get("personal_notebook", {})
    nb_dir = ai_work / "personal_notebook"
    if old_nb.get("exists") and not nb_dir.exists():
        errors.append("personal_notebook/: deleted by upgrade")

    # 11. settings.local.json — warn if modified (upgrade should never touch this)
    old_sl = z.get("settings_local", {})
    settings_local = claude_dir / "settings.local.json"
    if old_sl.get("exists") and old_sl.get("checksum"):
        if not settings_local.exists():
            warnings.append(".claude/settings.local.json: deleted by upgrade")
        elif sha256_file(settings_local) != old_sl["checksum"]:
            warnings.append(".claude/settings.local.json: modified by upgrade")

    return errors, warnings, infos


# ---------- status (no snapshot needed) ----------

def show_status(project_root: Path) -> None:
    snap = take_snapshot(project_root)
    print("current zone state (no snapshot comparison):")
    print_snapshot_summary(snap)


# ---------- main ----------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AIWS upgrade safety check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "workflow:\n"
            "  1. python check_aiws_upgrade.py --snapshot   # before upgrade\n"
            "  2. /update-aiws-package (run the upgrade)\n"
            "  3. python check_aiws_upgrade.py --verify     # after upgrade\n"
            "  4. python check_aiws_upgrade.py --clean      # remove snapshot"
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", action="store_true", help="capture pre-upgrade state")
    mode.add_argument("--verify",   action="store_true", help="check post-upgrade state against snapshot")
    mode.add_argument("--clean",    action="store_true", help="remove snapshot file")
    mode.add_argument("--status",   action="store_true", help="show current zone state (no snapshot needed)")
    parser.add_argument("--root", help="project root (default: auto-detect .ai-work ancestor)")
    args = parser.parse_args()

    project_root = Path(args.root).resolve() if args.root else find_ai_work_root(Path.cwd())
    snap_path = project_root / SNAPSHOT_FILENAME

    if args.status:
        show_status(project_root)
        return 0

    if args.clean:
        if snap_path.exists():
            snap_path.unlink()
            print(f"removed: {snap_path}")
        else:
            print(f"no snapshot found at {snap_path}")
        return 0

    if args.snapshot:
        if snap_path.exists():
            print(f"warning: overwriting existing snapshot at {snap_path}", file=sys.stderr)
        snap = take_snapshot(project_root)
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        snap_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"snapshot written: {snap_path}")
        print_snapshot_summary(snap)
        print("\nrun /update-aiws-package, then: python check_aiws_upgrade.py --verify")
        return 0

    # --verify
    if not snap_path.exists():
        print(f"error: no snapshot found at {snap_path}", file=sys.stderr)
        print("run --snapshot BEFORE the upgrade", file=sys.stderr)
        return 2

    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    if snap.get("version") != SNAPSHOT_VERSION:
        print(
            f"error: snapshot version {snap.get('version')} incompatible with tool version {SNAPSHOT_VERSION}",
            file=sys.stderr,
        )
        return 2

    errors, warnings, infos = verify_snapshot(snap, project_root)

    if errors:
        print("DEGRADATION DETECTED")
        print("-" * 40)
        for e in errors:
            print(f"  ERROR   {e}")
    if warnings:
        if not errors:
            print("WARNINGS")
            print("-" * 40)
        for w in warnings:
            print(f"  WARN    {w}")
    if infos:
        for i in infos:
            print(f"  INFO    {i}")

    print()
    print(f"summary: errors={len(errors)} warnings={len(warnings)} info={len(infos)}")

    if not errors and not warnings:
        print("OK — upgrade did not degrade any protected zone")

    if errors:
        print("\nnext steps: investigate errors above before using the upgraded installation")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
