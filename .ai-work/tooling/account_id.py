#!/usr/bin/env python3
"""Provision the local AIWS account_id + account_info.yaml — CR-AIWS-2026-06-016.

`account_info.yaml` (gitignored, one per install) carries `account_id` + the per-member
`next_aip_id` counter that allocate_aip_id.py consumes (CR-015 v2). This tool sets/validates it.
AI NEVER invents an account_id — `set` requires an explicit `--account-id` from the HUMAN.

Subcommands:
  get                     print the current account_id (error if unset)
  set --account-id <id>   validate (dir-safe) + write account_info.yaml (preserve existing
                          next_aip_id, else seed from disk-max+1) + ensure .gitignore ignores it
  validate [--repair]     check account_id (dir-safe) + next_aip_id (exec/plan/local present);
                          --repair re-seeds a missing/partial counter from disk-max+1 (OP-4)

stdlib-only; UTF-8 (cp932-safe).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_ai_work_root, parse_frontmatter, write_text  # noqa: E402
from allocate_aip_id import _account_info_path, _disk_max  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ACCOUNT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")   # dir-safe (OP-2)
_KINDS = ("exec", "plan", "local")
_HEADER = (
    "# AIWS local member identity + AIP id counter — CR-AIWS-2026-06-015 v2 / CR-AIWS-2026-06-016.\n"
    "# LOCAL FILE: gitignored, never committed. account_id + per-member NEXT AIP number per kind.\n"
)


def _read(ai_work: Path) -> dict:
    p = _account_info_path(ai_work)
    if not p.exists():
        return {}
    meta, _ = parse_frontmatter("---\n" + p.read_text(encoding="utf-8") + "\n---\n")
    return meta or {}


def _seed_counter(ai_work: Path, account_id: str, existing: dict) -> dict:
    nxt = existing.get("next_aip_id")
    nxt = nxt if isinstance(nxt, dict) else {}
    out = {}
    for kind in _KINDS:
        if str(nxt.get(kind, "")).strip().isdigit():
            out[kind] = int(nxt[kind])
        else:
            out[kind] = _disk_max(ai_work, account_id, kind) + 1   # re-seed from disk (OP-4)
    return out


def _write(ai_work: Path, account_id: str, counter: dict) -> None:
    body = _HEADER + f"account_id: {account_id}\nnext_aip_id:\n"
    for kind in _KINDS:
        body += f"  {kind}: {counter[kind]}\n"
    write_text(_account_info_path(ai_work), body)


def _ensure_gitignore(ai_work: Path) -> bool:
    gi = ai_work.parent / ".gitignore"
    line = ".ai-work/account_info.yaml"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line in existing:
        return False
    with open(gi, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(f"\n# AIWS local identity (CR-AIWS-2026-06-016) — never commit\n{line}\n")
    return True


def cmd_get(ns: argparse.Namespace, ai_work: Path) -> int:
    aid = str(_read(ai_work).get("account_id", "")).strip()
    if not aid:
        print("error: account_id not set (run: account_id.py set --account-id <id>)", file=sys.stderr)
        return 2
    print(aid)
    return 0


def cmd_set(ns: argparse.Namespace, ai_work: Path) -> int:
    aid = ns.account_id.strip().lower()
    if not ACCOUNT_ID_RE.match(aid):
        print(f"error: account_id {ns.account_id!r} not dir-safe; allowed pattern: {ACCOUNT_ID_RE.pattern}",
              file=sys.stderr)
        return 2
    counter = _seed_counter(ai_work, aid, _read(ai_work))
    _write(ai_work, aid, counter)
    gi = _ensure_gitignore(ai_work)
    print(f"set account_id: {aid}; next_aip_id={counter}" + ("; .gitignore updated" if gi else ""))
    return 0


def cmd_validate(ns: argparse.Namespace, ai_work: Path) -> int:
    p = _account_info_path(ai_work)
    if not p.exists():
        print(f"error: {p} missing (run: account_id.py set --account-id <id>)", file=sys.stderr)
        return 2
    info = _read(ai_work)
    aid = str(info.get("account_id", "")).strip()
    problems = []
    if not ACCOUNT_ID_RE.match(aid):
        problems.append(f"account_id {aid!r} missing/not dir-safe")
    nxt = info.get("next_aip_id")
    if not isinstance(nxt, dict) or any(not str(nxt.get(k, "")).strip().isdigit() for k in _KINDS):
        problems.append("next_aip_id missing/partial (need exec/plan/local)")
    if problems and ns.repair and aid and ACCOUNT_ID_RE.match(aid):
        counter = _seed_counter(ai_work, aid, info)
        _write(ai_work, aid, counter)
        print(f"repaired: next_aip_id re-seeded from disk = {counter}")
        return 0
    if problems:
        for pr in problems:
            print(f"  - {pr}", file=sys.stderr)
        print("validate FAILED (use --repair to re-seed next_aip_id)", file=sys.stderr)
        return 1
    print(f"account_info.yaml OK: account_id={aid} next_aip_id={nxt}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Provision AIWS account_id (CR-AIWS-2026-06-016)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("get", help="print the current account_id")
    s = sub.add_parser("set", help="set account_id (write account_info.yaml + .gitignore)")
    s.add_argument("--account-id", required=True, help="dir-safe id; normalized lowercase")
    v = sub.add_parser("validate", help="validate account_info.yaml")
    v.add_argument("--repair", action="store_true", help="re-seed a missing/partial next_aip_id from disk")
    ns = ap.parse_args()
    ai_work = find_ai_work_root(Path.cwd()) / ".ai-work"
    return {"get": cmd_get, "set": cmd_set, "validate": cmd_validate}[ns.cmd](ns, ai_work)


if __name__ == "__main__":
    raise SystemExit(main())
