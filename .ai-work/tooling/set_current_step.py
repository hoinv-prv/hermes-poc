#!/usr/bin/env python3
"""Set the current-step pointer for a workspace.

Writes a small pointer file at <workspace>/.current_step.json and updates
the Active AIP reference markdown so the runtime knows which AIP/step
is active. Does NOT materialize the Active Step Context — use
build_active_step_context.py for that after pointing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import parse_frontmatter, read_text, write_text, today  # noqa: E402


def _regenerate_active_aip(ws: Path, aip_id: str, aip_path: str,
                           status: str) -> None:
    """Rewrite 00b_active_aip.md deterministically from AIP frontmatter.

    Previous implementation patched individual lines, which left stale
    fields (AIP Type, Root AIP) when an AIP was swapped. FND-032
    remediation: regenerate the whole file from the AIP frontmatter so
    pointer recovery is a single command.
    """
    aip_type = ""
    root_aip = "AIP-ROOT"
    if aip_path:
        ap = Path(aip_path)
        if ap.exists():
            meta, _ = parse_frontmatter(read_text(ap))
            aip_type = str(meta.get("artifact_type", "")).replace("aip_", "")
            root_aip = str(meta.get("root_aip", "AIP-ROOT"))

    body = (
        "# Active AIP Reference\n"
        "\n"
        f"- Source AIP ID: {aip_id}\n"
        f"- Source AIP Path: {aip_path}\n"
        f"- AIP Type: {aip_type}\n"
        f"- Root AIP: {root_aip}\n"
        f"- Status: {status}\n"
    )
    write_text(ws / "00b_active_aip.md", body)


def main() -> int:
    p = argparse.ArgumentParser(description="Set current step pointer")
    p.add_argument("--workspace", required=True, help="Workspace directory")
    p.add_argument("--aip", required=True,
                   help="Source AIP id, e.g. AIP-PLAN-001")
    p.add_argument("--aip-path", help="Source AIP file path (optional)")
    p.add_argument("--step-id", required=True, help="Step id, e.g. STEP-02")
    p.add_argument("--status", default="active",
                   choices=["active", "blocked", "done"])
    ns = p.parse_args()

    ws = Path(ns.workspace).resolve()
    if not ws.is_dir():
        print(f"error: workspace not found: {ws}", file=sys.stderr)
        return 2

    pointer = {
        "aip_id": ns.aip,
        "aip_path": ns.aip_path or "",
        "step_id": ns.step_id,
        "status": ns.status,
        "updated_at": today(),
    }
    pointer_path = ws / ".current_step.json"
    write_text(pointer_path, json.dumps(pointer, indent=2, ensure_ascii=False) + "\n")

    _regenerate_active_aip(ws, ns.aip, ns.aip_path or "", ns.status)

    print(f"pointer set: {ns.aip} / {ns.step_id} ({ns.status})")
    print(f"  -> {pointer_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
