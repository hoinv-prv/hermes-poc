#!/usr/bin/env python3
"""Source Build Routing registry CLI — CR-AIWS-2026-05-019 Stage 2.

Maps a `source_type` -> the builder tool that BUILDS/REFRESHES its wiki source metas,
so `register-wiki-sources` can dispatch DATA-DRIVEN instead of a hardcoded static table.

Registry: `.ai-work/wiki_sources/_build_routing.json` (JSON sidecar; NOT projected into
`index.jsonl` per SOURCE_BUILD_ROUTING_SPEC §3). Tool paths are stored portable
(`__PROJECT_ROOT__`-relative via `_common.portable_locator`) and resolved at read.

Subcommands:
  get <source_type>                 print the route (resolved + existence-checked) or the default_route
  list                              print all routes + default_route
  set <source_type> --tool P [...]  upsert a route (atomic write)
  remove <source_type>              delete a route (atomic write)
  render <source_type> [--root ...] print the argv LIST + shell-quoted preview (placeholders substituted)

default_route fallback = "generic" (the per-file /build-wiki-source-meta flow).
MVP (Stage 2): refresh_mode = rerun_tool only; the builder emits the FULL meta (no standard
completion layer). Routing keys are EXACT source_types → deterministic, no glob overlap.

stdlib-only; UTF-8 (cp932-safe).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import portable_locator, resolve_locator  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

KNOWN_PLACEHOLDERS = {"root", "prefix", "subdir", "artifact"}
DEFAULT_ROUTE = "generic"          # per-file /build-wiki-source-meta
REFRESH_MODES = ("rerun_tool",)    # MVP: rerun the tool only
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / ".ai-work").is_dir():
            return p
    return here.parents[2]


def _registry_path(root: Path) -> Path:
    return root / ".ai-work" / "wiki_sources" / "_build_routing.json"


def _load(root: Path) -> dict:
    p = _registry_path(root)
    if not p.exists():
        return {"version": 1, "default_route": DEFAULT_ROUTE, "routes": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:  # noqa: BLE001
        raise SystemExit(f"error: corrupt registry {p}: {e}")
    data.setdefault("version", 1)
    data.setdefault("default_route", DEFAULT_ROUTE)
    data.setdefault("routes", {})
    return data


def _atomic_write(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _unknown_placeholders(args: list[str]) -> set[str]:
    found: set[str] = set()
    for a in args:
        found.update(_PLACEHOLDER_RE.findall(a))
    return found - KNOWN_PLACEHOLDERS


def cmd_set(ns: argparse.Namespace, root: Path) -> int:
    data = _load(root)
    raw = Path(ns.tool)
    tool_abs = raw if raw.is_absolute() else (root / ns.tool)
    tool_port = portable_locator(tool_abs, root)          # store portable
    args = shlex.split(ns.args) if ns.args else []        # shlex string → argv LIST (handles -leading values)
    bad = _unknown_placeholders(args)
    if bad:
        print(f"WARNING: unknown placeholders {sorted(bad)} (known: {sorted(KNOWN_PLACEHOLDERS)})", file=sys.stderr)
    if not resolve_locator(tool_port, root).exists():     # soft-WARN (a just-created W2 tool may not exist yet)
        print(f"WARNING: tool path not found yet: {tool_abs} (ok for a just-authored W2 tool)", file=sys.stderr)
    data["routes"][ns.source_type] = {
        "tool": tool_port,
        "args": args,
        "refresh_mode": ns.refresh_mode,
        "profile_id": ns.profile_id or "",
    }
    _atomic_write(_registry_path(root), data)
    print(f"set route: {ns.source_type} -> {tool_port}")
    return 0


def cmd_get(ns: argparse.Namespace, root: Path) -> int:
    data = _load(root)
    route = data["routes"].get(ns.source_type)
    if not route:
        print(json.dumps({"source_type": ns.source_type,
                          "route": data.get("default_route", DEFAULT_ROUTE)}, ensure_ascii=False))
        return 0
    resolved = resolve_locator(route["tool"], root)        # re-check existence at READ (S2.2)
    out = dict(route)
    out.update({"source_type": ns.source_type,
                "tool_resolved": str(resolved), "tool_exists": resolved.exists()})
    if not resolved.exists():
        print(f"WARNING: route tool missing on disk: {resolved}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_list(ns: argparse.Namespace, root: Path) -> int:
    data = _load(root)
    print(json.dumps({"default_route": data.get("default_route", DEFAULT_ROUTE),
                      "routes": data.get("routes", {})}, ensure_ascii=False, indent=2))
    return 0


def cmd_remove(ns: argparse.Namespace, root: Path) -> int:
    data = _load(root)
    if ns.source_type in data["routes"]:
        del data["routes"][ns.source_type]
        _atomic_write(_registry_path(root), data)
        print(f"removed route: {ns.source_type}")
        return 0
    print(f"no route for {ns.source_type}", file=sys.stderr)
    return 1


def cmd_render(ns: argparse.Namespace, root: Path) -> int:
    data = _load(root)
    route = data["routes"].get(ns.source_type)
    if not route:
        print(f"no route for {ns.source_type} (default: {data.get('default_route', DEFAULT_ROUTE)})", file=sys.stderr)
        return 1
    subs = {"root": ns.root or "", "prefix": ns.prefix or "",
            "subdir": ns.subdir or "", "artifact": ns.artifact or ""}
    argv = [sys.executable, str(resolve_locator(route["tool"], root))]
    for a in route["args"]:
        for k, v in subs.items():
            a = a.replace("{" + k + "}", v)
        argv.append(a)
    print(json.dumps({"argv": argv, "preview": shlex.join(argv)}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Source Build Routing registry CLI (CR-05-019 Stage 2)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="print a route or the default_route")
    g.add_argument("source_type")
    sub.add_parser("list", help="print all routes")
    rm = sub.add_parser("remove", help="delete a route")
    rm.add_argument("source_type")

    s = sub.add_parser("set", help="upsert a route")
    s.add_argument("source_type")
    s.add_argument("--tool", required=True, help="builder tool path (stored __PROJECT_ROOT__-relative)")
    s.add_argument("--args", default="",
                   help="builder argv template as ONE shlex string (handles -leading values); "
                        "placeholders {root}{prefix}{subdir}{artifact}")
    s.add_argument("--profile-id", default="", help="non-authoritative back-reference to profile_id")
    s.add_argument("--refresh-mode", default="rerun_tool", choices=REFRESH_MODES)

    rn = sub.add_parser("render", help="render argv list + shell-quoted preview")
    rn.add_argument("source_type")
    rn.add_argument("--root", default="")
    rn.add_argument("--prefix", default="")
    rn.add_argument("--subdir", default="")
    rn.add_argument("--artifact", default="")

    ns = p.parse_args()
    root = _project_root()
    handlers = {"get": cmd_get, "set": cmd_set, "list": cmd_list,
                "remove": cmd_remove, "render": cmd_render}
    return handlers[ns.cmd](ns, root)


if __name__ == "__main__":
    raise SystemExit(main())
