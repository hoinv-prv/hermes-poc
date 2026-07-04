#!/usr/bin/env python3
"""Orchestrate AIP execution: start, resume, jump-to-step, status, list-steps.

This tool wires together init_workspace / set_current_step /
build_active_step_context so one command prepares the workspace to work on
a specific AIP step. It does NOT execute the step content — it just
guarantees workspace state is ready and points the LLM at the right place.

Subcommands:

  start   <aip>                  # create workspace + point STEP-01 + build ASC
  resume  <aip>                  # read existing workspace pointer + rebuild ASC
  step    <aip> --step STEP-XX   # jump to a specific step (creates/updates)
  status  <aip>                  # print current pointer + workspace summary
  list    <aip>                  # list all steps in the AIP with titles

In every mode `<aip>` accepts either an AIP id (e.g. AIP-EXEC-001) or a
file path. Task id defaults to `TASK-YYYYMMDD-<aip-slug>`; override with
`--task-id`.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    find_ai_work_root,
    parse_aip_steps,
    read_account_id,
    parse_frontmatter,
    portable_locator,
    read_jsonl,
    read_text,
    today,
    write_text,
)

TOOL = Path(__file__).resolve().parent

# --- Project-boundary guardrails --------------------------------------------
# run_aip.py is allowed to auto-run without per-call approval, so it must
# refuse any operation that would read or write outside the project's
# `.ai-work/` tree. These helpers enforce that contract; every path the tool
# touches must resolve strictly inside `ai_work_root`.

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")


def _ensure_inside(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise SystemExit(
            f"error: {label} path escapes project boundary\n"
            f"  path: {resolved}\n"
            f"  must be inside: {root.resolve()}"
        )
    return resolved


def _safe_task_id(task_id: str) -> str:
    if not _TASK_ID_RE.match(task_id or ""):
        raise SystemExit(
            f"error: invalid --task-id '{task_id}'\n"
            f"  allowed: [A-Za-z0-9][A-Za-z0-9_-]{{0,63}} (no path separators, no '..')"
        )
    return task_id


def _aip_account_scope(f: Path, ai_work: Path) -> str:
    """Account namespace of an AIP path: '<account_id>' under aip/<account_id>/<kind>/,
    or '(legacy)' for flat aip/<kind>/ AIPs (CR-015 v2)."""
    try:
        parts = f.relative_to(ai_work / "aip").parts
    except ValueError:
        return "(unknown)"
    if not parts or parts[0] in ("exec", "plans", "local"):
        return "(legacy)"
    return parts[0]


def _resolve_aip(aip_ref: str, ai_work: Path) -> tuple[Path, dict]:
    """Return (path, frontmatter) for an AIP id or path.

    When `aip_ref` is an AIP id, walk the full AIP zone and collect every
    file whose frontmatter matches. If more than one file claims the same
    id, fail loudly instead of silently picking the first match — this
    is the FND-030 / FND-032 guardrail.
    """
    p = Path(aip_ref)
    if p.is_file():
        path = _ensure_inside(p, ai_work, "AIP file")
    else:
        # CR-015 v2: AIPs live under per-account folders aip/<account_id>/<kind>/ AND legacy
        # flat aip/<kind>/ — scan the whole aip tree (recursive, incl. done/).
        aip_root = ai_work / "aip"
        matches: list[Path] = []
        if aip_root.is_dir():
            for f in sorted(aip_root.rglob("*.md")):
                try:
                    meta, _ = parse_frontmatter(read_text(f))
                except Exception:
                    continue
                if meta.get("artifact_id") == aip_ref:
                    matches.append(f)
        if not matches:
            raise SystemExit(f"error: cannot resolve AIP '{aip_ref}'")
        if len(matches) > 1:
            # A bare id may legitimately recur across account folders — prefer the CURRENT
            # account's match; only error if still ambiguous within one scope.
            acct = read_account_id(ai_work)
            pref = [m for m in matches if _aip_account_scope(m, ai_work) == acct] if acct else []
            if len(pref) == 1:
                matches = pref
            else:
                joined = "\n  ".join(str(m) for m in matches)
                raise SystemExit(
                    f"error: AIP id '{aip_ref}' resolves to {len(matches)} files:\n"
                    f"  {joined}\n"
                    f"refusing to pick silently — pass the AIP file path, or fix the collision "
                    f"(run 'python .ai-work/tooling/lint_all.py')."
                )
        path = matches[0].resolve()
    meta, _ = parse_frontmatter(read_text(path))
    return path, meta


def _default_task_id(aip_meta: dict) -> str:
    aid = aip_meta.get("artifact_id", "AIP").lower().replace("aip-", "")
    return f"TASK-{today().replace('-', '')}-{aid}"


def _run(cmd: list[str]) -> int:
    r = subprocess.run(cmd, encoding="utf-8")
    return r.returncode


def _lint_gate(aip_path: Path) -> bool:
    """Fail-fast lint gate before start/resume (CR-AIWS-2026-05-037 Option A).

    Runs lint_aip on the target AIP. lint_aip (non-strict) returns 2 when the
    AIP has ERRORS and 0 otherwise — so WARNINGS do NOT block, matching
    run-aip SKILL.md §'Pre-start AIP validation'. Returns True to proceed,
    False if the AIP has lint errors (caller must refuse). If the lint tool is
    missing, do not hard-block run-aip.
    """
    lint = TOOL / "lint_aip.py"
    if not lint.exists():
        return True
    print(f"lint-gate: checking {aip_path.name} (CR-037 Option A) ...")
    rc = _run([sys.executable, str(lint), "--path", str(aip_path)])
    if rc != 0:
        print(
            f"error: lint_aip reported errors on {aip_path.name} — refusing to "
            f"start/resume.\n"
            f"  fix the AIP to 0 errors, then retry (see lint output above).",
            file=sys.stderr,
        )
        return False
    return True


def _steps(aip_path: Path) -> list[dict]:
    _, body = parse_frontmatter(read_text(aip_path))
    return parse_aip_steps(body)


def _workspace_dir(ai_work: Path, task_id: str) -> Path:
    _safe_task_id(task_id)
    ws = ai_work / "workspaces" / task_id
    return _ensure_inside(ws, ai_work / "workspaces", "workspace")


def _new_workspace_dir(ai_work: Path, task_id: str, account_id: str) -> Path:
    """Target dir for a NEW workspace (CR-015 v2): a per-account folder when account_id is set,
    else legacy flat."""
    _safe_task_id(task_id)
    base = (ai_work / "workspaces" / account_id) if account_id else (ai_work / "workspaces")
    return _ensure_inside(base / task_id, ai_work / "workspaces", "workspace")


def _read_pointer(ws: Path) -> dict | None:
    p = ws / ".current_step.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _resolve_workspace(ai_work: Path, meta: dict, explicit_task_id: str | None,
                       *, allow_today_fallback: bool = True) -> Path:
    """Resolve an AIP's workspace (CR-AIWS-2026-06-015 Facet 5a).

    Order: explicit --task-id → reverse-scan each workspace's `.current_step.json`
    back-link (`aip_id`) → `runtime_workspace` frontmatter pointer (F5b) →
    today()-based fallback. This replaces blind `TASK-<today()>-<slug>` derivation so
    `resume`/`status` work across days (fixes the today() bug). If MORE THAN ONE live
    workspace maps to the AIP, STOP and ask the human (possible bug) — never silent-pick.
    """
    ws_root = ai_work / "workspaces"
    if explicit_task_id:
        tid = _safe_task_id(explicit_task_id)
        flat = ws_root / tid
        if flat.is_dir():
            return _ensure_inside(flat, ws_root, "workspace")
        if ws_root.is_dir():  # search per-account folders for the task dir
            for acct in sorted(d for d in ws_root.iterdir()
                               if d.is_dir() and not d.name.startswith(".")):
                cand = acct / tid
                if cand.is_dir():
                    return _ensure_inside(cand, ws_root, "workspace")
        acct_id = read_account_id(ai_work)  # not found → default to current account's folder
        base = (ws_root / acct_id) if acct_id else ws_root
        return _ensure_inside(base / tid, ws_root, "workspace")
    aip_id = meta.get("artifact_id", "")
    matches: list[Path] = []
    if aip_id and ws_root.is_dir():  # reverse-scan, RECURSIVE (per-account + legacy workspaces)
        for ptr_file in sorted(ws_root.rglob(".current_step.json")):
            ws = ptr_file.parent
            ptr = _read_pointer(ws)
            if ptr and ptr.get("aip_id") == aip_id:
                matches.append(ws)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = "\n  ".join(str(m) for m in matches)
        raise SystemExit(
            f"error: {len(matches)} workspaces map to '{aip_id}' (possible bug):\n  {joined}\n"
            f"  pass --task-id <TASK-ID> to choose which workspace to use."
        )
    # 0 matches: try a frontmatter runtime_workspace pointer (F5b), else today() fallback
    rw = str(meta.get("runtime_workspace", "")).strip()
    if rw:
        from _common import resolve_locator
        cand = resolve_locator(rw, ai_work.parent)
        return _ensure_inside(cand, ws_root, "workspace")
    if allow_today_fallback:  # fallback now lands under the current account's folder
        acct_id = read_account_id(ai_work)
        base = (ws_root / acct_id) if acct_id else ws_root
        return _ensure_inside(base / _default_task_id(meta), ws_root, "workspace")
    raise SystemExit(
        f"error: no workspace found for '{aip_id}' — run 'start' first or pass --task-id")


def _write_runtime_workspace(aip_path: Path, ws: Path, ai_work: Path, force: bool) -> None:
    """F5b (CR-AIWS-2026-06-015): stamp a WRITE-ONCE `runtime_workspace` provenance
    pointer into the AIP frontmatter. Set only if absent (write-once); on --force,
    update to the new workspace. Surgical line-level edit — never reformats the rest of
    the frontmatter, never touches the body. NOT runtime state (AIP_Detail_Spec §2.3)."""
    text = read_text(aip_path)
    m = re.match(r"^(---\s*\n)(.*?\n)(---\s*\n)(.*)$", text, re.DOTALL)
    if not m:
        return
    head, fm, fence, body = m.group(1), m.group(2), m.group(3), m.group(4)
    loc = portable_locator(ws, ai_work.parent)
    line = f"runtime_workspace: {loc}\n"
    lines = fm.splitlines(keepends=True)
    has = any(l.startswith("runtime_workspace:") for l in lines)
    if has and not force:
        return  # write-once — leave the existing pointer untouched
    out: list[str] = []
    placed = False
    for l in lines:
        if l.startswith("runtime_workspace:"):
            out.append(line)  # force-update in place
            placed = True
            continue
        if l.startswith("updated_at:") and not has:
            out.append(line)  # insert just before updated_at (matches §5.4 schema order)
            placed = True
        out.append(l)
    if not placed:
        out.append(line)
    write_text(aip_path, head + "".join(out) + fence + body)


# ---------- subcommands ----------

def cmd_start(ns) -> int:
    ai_work = find_ai_work_root(Path.cwd()) / ".ai-work"
    aip_path, meta = _resolve_aip(ns.aip, ai_work)
    if not _lint_gate(aip_path):
        return 2
    task_id = ns.task_id or _default_task_id(meta)
    account_id = read_account_id(ai_work)  # CR-015 v2: new workspaces under per-account folder
    ws = _new_workspace_dir(ai_work, task_id, account_id)
    if ws.exists() and not ns.force:
        print(
            f"error: workspace already exists: {ws}\n"
            f"  use 'resume' to continue, or pass --force to reinitialize",
            file=sys.stderr,
        )
        return 2

    init_cmd = [
        sys.executable, str(TOOL / "init_workspace.py"),
        "--task-id", task_id,
        "--aip", meta.get("artifact_id", ""),
        "--aip-path", str(aip_path),
        "--aip-type", meta.get("artifact_type", "").replace("aip_", ""),
        "--root-aip", meta.get("root_aip", "AIP-ROOT"),
    ]
    if account_id:
        init_cmd += ["--account", account_id]
    if ns.title:
        init_cmd += ["--title", ns.title]
    if ns.force:
        init_cmd.append("--force")
    rc = _run(init_cmd)
    if rc != 0:
        return rc

    # F5b: stamp the write-once runtime_workspace provenance pointer into the AIP.
    try:
        _write_runtime_workspace(aip_path, ws, ai_work, ns.force)
    except Exception as e:  # noqa: BLE001
        print(f"warn: could not write runtime_workspace pointer: {e}", file=sys.stderr)

    steps = _steps(aip_path)
    if not steps:
        print(f"warn: AIP has no parseable steps; workspace initialized only")
        return 0
    first = steps[0]["step_id"]
    target = ns.step or first

    return _point_and_build(ai_work, aip_path, meta, ws, target)


def cmd_resume(ns) -> int:
    ai_work = find_ai_work_root(Path.cwd()) / ".ai-work"
    aip_path, meta = _resolve_aip(ns.aip, ai_work)
    if not _lint_gate(aip_path):
        return 2
    ws = _resolve_workspace(ai_work, meta, ns.task_id)
    if not ws.exists():
        print(
            f"error: workspace not found: {ws}\n"
            f"  run 'run_aip.py start {ns.aip}' first",
            file=sys.stderr,
        )
        return 2

    pointer = _read_pointer(ws)
    if pointer is None and not ns.step:
        print(
            "error: no current_step pointer and --step not provided",
            file=sys.stderr,
        )
        return 2

    target = ns.step or pointer.get("step_id", "STEP-01")
    return _point_and_build(ai_work, aip_path, meta, ws, target)


def cmd_step(ns) -> int:
    return cmd_resume(ns)  # step is resume with forced --step


def cmd_status(ns) -> int:
    ai_work = find_ai_work_root(Path.cwd()) / ".ai-work"
    aip_path, meta = _resolve_aip(ns.aip, ai_work)
    ws = _resolve_workspace(ai_work, meta, ns.task_id)
    task_id = ws.name

    print(f"AIP:       {meta.get('artifact_id', '?')}  ({aip_path})")
    print(f"Task ID:   {task_id}")
    print(f"Workspace: {ws} {'(exists)' if ws.exists() else '(missing)'}")

    steps = _steps(aip_path)
    print(f"Steps:     {len(steps)}")

    if not ws.exists():
        print("Status:    not started — run 'run_aip.py start <aip>'")
        return 0
    pointer = _read_pointer(ws)
    if pointer:
        print(f"Pointer:   {pointer.get('step_id')} ({pointer.get('status')})  "
              f"updated {pointer.get('updated_at')}")
    else:
        print("Pointer:   (none) — run 'run_aip.py resume <aip> --step STEP-01'")

    for f in ("00c_active_step_context.md", "04_findings.md",
              "07_output_draft.md", "11_output_final.md"):
        p = ws / f
        state = "✔" if p.exists() and p.stat().st_size > 0 else "·"
        print(f"  [{state}] {f}")
    # CR-015 F4: surface the capture-triage rollup (the playbook L16 promise, now real).
    inbox = ws / "08_capture_inbox.jsonl"
    if inbox.exists():
        try:
            rows = read_jsonl(inbox)
            captured = sum(1 for r in rows if r.get("status") == "captured")
            print(f"Captures:  {len(rows)} total, {captured} need triage (status=captured)")
        except Exception:
            print("Captures:  (inbox unreadable)")
    return 0


def cmd_list(ns) -> int:
    ai_work = find_ai_work_root(Path.cwd()) / ".ai-work"
    aip_path, meta = _resolve_aip(ns.aip, ai_work)
    print(f"{meta.get('artifact_id', '?')} — {meta.get('title', '')}")
    for s in _steps(aip_path):
        print(f"  {s['step_id']}  {s.get('title', '')}")
    return 0


def _point_and_build(ai_work: Path, aip_path: Path, meta: dict,
                     ws: Path, step_id: str) -> int:
    set_cmd = [
        sys.executable, str(TOOL / "set_current_step.py"),
        "--workspace", str(ws),
        "--aip", meta.get("artifact_id", ""),
        "--aip-path", str(aip_path),
        "--step-id", step_id,
    ]
    rc = _run(set_cmd)
    if rc != 0:
        return rc
    build_cmd = [
        sys.executable, str(TOOL / "build_active_step_context.py"),
        "--workspace", str(ws),
    ]
    rc = _run(build_cmd)
    if rc != 0:
        return rc
    print()
    print("READY:")
    print(f"  workspace: {ws}")
    print(f"  step:      {step_id}")
    print(f"  active step context: {ws / '00c_active_step_context.md'}")
    print(f"Next: open 00c_active_step_context.md and work the step.")
    print("Wiki candidate check: append candidates to 08_capture_inbox.jsonl IMMEDIATELY on discovery — do not batch to end of step or AIP.")
    print("Do not promote candidates into Wiki / Knowledge Hub without HUMAN review.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Orchestrate AIP execution")
    sub = p.add_subparsers(dest="cmd", required=True)

    def _add_common(sp):
        sp.add_argument("aip", help="AIP id (e.g. AIP-EXEC-001) or file path")
        sp.add_argument("--task-id", help="Override task id (default: derived)")

    sp_start = sub.add_parser("start", help="Create workspace + start AIP")
    _add_common(sp_start)
    sp_start.add_argument("--title", help="Task title (goal)")
    sp_start.add_argument("--step", help="Start at step (default: first)")
    sp_start.add_argument("--force", action="store_true",
                          help="Overwrite existing workspace")
    sp_start.set_defaults(func=cmd_start)

    sp_resume = sub.add_parser("resume", help="Resume existing workspace")
    _add_common(sp_resume)
    sp_resume.add_argument("--step", help="Jump to step (default: pointer)")
    sp_resume.set_defaults(func=cmd_resume)

    sp_step = sub.add_parser("step", help="Jump to a specific step")
    _add_common(sp_step)
    sp_step.add_argument("--step", required=True, help="Target step id")
    sp_step.set_defaults(func=cmd_step)

    sp_status = sub.add_parser("status", help="Show workspace + pointer status")
    _add_common(sp_status)
    sp_status.set_defaults(func=cmd_status)

    sp_list = sub.add_parser("list", help="List steps in the AIP")
    _add_common(sp_list)
    sp_list.set_defaults(func=cmd_list)

    ns = p.parse_args()
    return ns.func(ns)


if __name__ == "__main__":
    raise SystemExit(main())
