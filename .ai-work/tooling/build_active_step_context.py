#!/usr/bin/env python3
"""Materialize Active Step Context from an AIP step + workspace state.

Reads the AIP file, finds the target STEP, and writes a filled Active Step
Context markdown file in the workspace. The context combines step fields
(Objective, Mode, Guidelines, Skills, Inputs, Expected Outputs, Done
Condition, Notes) with pointers to relevant workspace runtime items.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    dump_frontmatter,
    extract_sections,
    find_ai_work_root,
    parse_aip_steps,
    parse_frontmatter,
    read_text,
    today,
    write_text,
)



def _load_jsonl_safe(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def _bullet_refs(rows: list[dict], id_key: str = "id", max_items: int = 10) -> str:
    if not rows:
        return "- ..."
    lines = []
    for r in rows[:max_items]:
        rid = r.get(id_key) or r.get("output_id") or r.get("discussion_trace_id") or "?"
        title = r.get("title") or r.get("output_type") or r.get("final_decision") or r.get("summary") or ""
        status = r.get("status") or r.get("review_status") or r.get("handoff_status") or ""
        lines.append(f"- {rid} — {title} ({status})".rstrip())
    return "\n".join(lines)


def _format_multiline(value: str) -> str:
    """Turn a field block into markdown body lines."""
    value = (value or "").strip()
    if not value:
        return "- ..."
    return value


def _extract_selected_lens(body: str) -> str:
    """Return the AIP's selected Task Lens label (CR-AIWS-2026-05-030).

    Reads the optional `## Selected Task Lens / Mode` section and returns the value of its
    `- Lens:` bullet, or "" when the section is absent/empty (No-Lens). The lens is a HINT
    that shapes the ASC reading-surface ordering — never a hard filter; No-Lens = zero overhead.
    """
    section = extract_sections(body).get("Selected Task Lens / Mode", "")
    for line in section.splitlines():
        s = line.strip().lstrip("-").strip()
        if s.lower().startswith("lens:"):
            val = s.split(":", 1)[1].strip()
            # treat an explicit No-Lens / empty placeholder as no lens
            if not val or val.lower() in {"no-lens", "no lens", "none", "(none)", "n/a"}:
                return ""
            return val
    return ""


_STEP_HEAD_RE = re.compile(r"^#+\s*Step:\s*(STEP-\S+)", re.I)


def _step_block(body: str, step_id: str) -> str:
    """Return the raw text block of one step (heading → next step / next top-level H2).

    Used to read inline step-level flags that parse_aip_steps does not capture
    (it recognizes a fixed Field-list only). Read-only; does not touch _common.
    """
    out: list[str] = []
    capturing = False
    for line in body.splitlines():
        m = _STEP_HEAD_RE.match(line)
        if m:
            if capturing:
                break
            capturing = (m.group(1) == step_id)
            continue
        if capturing and line.startswith("## ") and not line.lstrip("#").strip().lower().startswith("step:"):
            break
        if capturing:
            out.append(line)
    return "\n".join(out)


def _allow_raw_search(body: str, step_id: str) -> str | None:
    """Read an optional inline `allow_raw_search: true|false` flag from a step block
    (CR-AIWS-2026-06-052). Returns 'true' / 'false', or None when the step does not
    declare it (the common case — no AIP-level raw-search grant)."""
    m = re.search(r"(?im)^\s*allow_raw_search\s*:\s*(true|false|yes|no|1|0)\s*$",
                  _step_block(body, step_id))
    if not m:
        return None
    return "true" if m.group(1).lower() in {"true", "yes", "1"} else "false"


def _digest_lines(text: str, max_lines: int) -> str:
    """Compact digest of an AIP-level section: first `max_lines` non-empty lines.

    Keeps the ASC an orientation surface, not a reproduction of the AIP
    (Active_Step_Context_Spec_MVP §5 — prefer pointers/compact over full content).
    """
    text = (text or "").strip()
    if not text:
        return "- ..."
    kept = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    out = kept[:max_lines]
    if len(kept) > max_lines:
        out.append("- … (digest trimmed — open the AIP for the full text)")
    return "\n".join(out)


def _indent(text: str, prefix: str = "  ") -> str:
    """Indent every line of `text` (for nesting a digest under a label)."""
    if not text:
        return prefix + "- ..."
    return "\n".join(prefix + ln for ln in text.splitlines())


def _step_map(steps: list[dict], active_step_id: str) -> tuple[str, int, int]:
    """Render the 'you are here' step map; return (1-based active index, total).

    CR-AIWS-2026-06-036: the full step list is already parsed — surface it so the
    AI knows its position without reading the whole AIP.
    """
    total = len(steps)
    idx = next((i for i, s in enumerate(steps) if s.get("step_id") == active_step_id), -1)
    lines: list[str] = []
    for i, s in enumerate(steps):
        sid = s.get("step_id", "?")
        title = s.get("title", "")
        if i == idx:
            mark = f"  ◀ ACTIVE (step {i + 1} of {total})"
        elif idx >= 0 and i < idx:
            mark = "  [upstream — done]"
        else:
            mark = "  [downstream]"
        lines.append(f"- {sid} — {title}{mark}")
    return ("\n".join(lines) if lines else "- ..."), (idx + 1 if idx >= 0 else 0), total


def _downstream_contract(steps: list[dict], active_idx_1based: int) -> str:
    """What the next step needs from this step's output (forward handoff).

    CR-AIWS-2026-06-036: echo the next step's declared Inputs so the current step
    shapes its output to what successors consume.
    """
    idx = active_idx_1based - 1
    nxt = steps[idx + 1] if 0 <= idx and idx + 1 < len(steps) else None
    if not nxt:
        return "- (final step — no downstream step consumes this output)"
    lines = [f"- Next step ({nxt.get('step_id', '?')} — {nxt.get('title', '')}) needs as Inputs:"]
    nxt_inputs = (nxt.get("Inputs") or "").strip()
    if nxt_inputs:
        for ln in nxt_inputs.splitlines():
            if ln.strip():
                lines.append(f"  {ln.strip()}")
    else:
        lines.append("  - (next step declares no explicit Inputs)")
    lines.append("- Shape this step's output to satisfy the above + the AIP final outcome "
                 "(see AIP Goal & Outcome).")
    return "\n".join(lines)


def _resolve_aip_path(aip_ref: str, ai_work: Path) -> Path:
    """Resolve AIP id or path to a file under .ai-work/aip/."""
    p = Path(aip_ref)
    if p.is_file():
        return p.resolve()
    # id-ish — search plans/exec/local for matching artifact_id
    for sub in ("plans", "exec", "local"):
        for f in (ai_work / "aip" / sub).glob("*.md"):
            meta, _ = parse_frontmatter(read_text(f))
            if meta.get("artifact_id") == aip_ref:
                return f.resolve()
    raise SystemExit(f"error: cannot resolve AIP '{aip_ref}'")


def main() -> int:
    p = argparse.ArgumentParser(description="Build Active Step Context")
    p.add_argument("--workspace", required=True)
    p.add_argument("--aip", help="AIP id or path (omit to read pointer)")
    p.add_argument("--step-id", help="Step id (omit to read pointer)")
    p.add_argument("--pointer-file",
                   help="Alternate pointer file (default <workspace>/.current_step.json)")
    p.add_argument("--output",
                   help="Override output path (default 00c_active_step_context.md)")
    p.add_argument("--digest-lines", type=int, default=8,
                   help="Max lines for the AIP Goal/Outcome orientation digest (default 8)")
    p.add_argument("--scope-lines", type=int, default=5,
                   help="Max lines for the AIP Scope orientation digest (default 5)")
    ns = p.parse_args()

    ws = Path(ns.workspace).resolve()
    if not ws.is_dir():
        print(f"error: workspace not found: {ws}", file=sys.stderr)
        return 2

    aip_ref, step_id = ns.aip, ns.step_id
    if not (aip_ref and step_id):
        pointer_path = Path(ns.pointer_file) if ns.pointer_file else ws / ".current_step.json"
        if not pointer_path.exists():
            print(
                "error: no --aip/--step-id and no pointer file; "
                "run set_current_step.py first",
                file=sys.stderr,
            )
            return 2
        ptr = json.loads(read_text(pointer_path))
        aip_ref = aip_ref or ptr.get("aip_path") or ptr.get("aip_id")
        step_id = step_id or ptr.get("step_id")

    ai_work = find_ai_work_root(ws) / ".ai-work"
    aip_path = _resolve_aip_path(aip_ref, ai_work)
    meta, body = parse_frontmatter(read_text(aip_path))
    steps = parse_aip_steps(body)
    selected_lens = _extract_selected_lens(body)  # CR-030: Task Lens hint for the reading surface
    allow_raw_search = _allow_raw_search(body, step_id)  # CR-052: optional AIP-level raw-search grant
    step = next((s for s in steps if s["step_id"] == step_id), None)
    if step is None:
        print(
            f"error: step {step_id} not found in {aip_path}",
            file=sys.stderr,
        )
        return 2

    # CR-AIWS-2026-06-036: per-step orientation derived from the already-parsed AIP body + step list.
    aip_sections = extract_sections(body)
    step_map, step_index, step_total = _step_map(steps, step_id)
    downstream = _downstream_contract(steps, step_index)
    goal_digest = _digest_lines(aip_sections.get("Objective", ""), ns.digest_lines)
    outcome_digest = _digest_lines(aip_sections.get("Expected Outputs", ""), ns.digest_lines)
    scope_text = (aip_sections.get("Execution Scope") or aip_sections.get("In Scope")
                  or aip_sections.get("Scope") or "")
    scope_digest = _digest_lines(scope_text, ns.scope_lines)

    task_id = ws.name
    queue_path = _first_existing(ws / "02_runtime_queue.jsonl", ws / "02_investigation_queue.jsonl")
    queue_rows = _load_jsonl_safe(queue_path) if queue_path else []
    blocking_queue = [
        r for r in queue_rows
        if str(r.get("blocking", "")).lower() in {"true", "1", "yes"} or r.get("status") == "blocked"
    ]
    capture_rows = _load_jsonl_safe(ws / "08_capture_inbox.jsonl")
    output_index = _load_jsonl_safe(ws / "step_outputs" / "index.jsonl")
    decision_index = _load_jsonl_safe(ws / "decision_traces" / "index.jsonl")

    asc_meta = {
        "artifact_type": "active_step_context",
        "artifact_id": f"ASC-{task_id}-{step_id}",
        "task_id": task_id,
        "working_aip_ref": meta.get("artifact_id", ""),
        "working_aip_path": str(aip_path),
        "active_step_id": step_id,
        "active_step_title": step.get("title", ""),
        "source_aip": meta.get("artifact_id", ""),
        "source_aip_path": str(aip_path),
        "step_id": step_id,
        "step_index": step_index,
        "step_total": step_total,
        "status": "active",
        "active_task_lens": selected_lens,
        "staleness_status": "fresh",
        "staleness_reason": "",
        "updated_at": today(),
    }

    out_lines: list[str] = [
        dump_frontmatter(asc_meta),
        f"# Active Step Context — {step.get('title', '')}",
        "",
        "## AIP Goal & Outcome",
        "- Goal (AIP-level objective):",
        _indent(goal_digest),
        "- Final outcome (AIP Expected Outputs):",
        _indent(outcome_digest),
        "- Scope:",
        _indent(scope_digest),
        "",
        "## Step Map — You Are Here",
        step_map,
        "",
        "## Downstream / Output Contract",
        downstream,
        "",
        "## Active Task Lens",
        (f"- {selected_lens}" if selected_lens
         else "- No explicit lens (No-Lens) — read from intent (zero forced overhead)"),
        "- Reading-surface hint (CR-030): when a lens is set, prioritise its preset "
        "`relevant_source_types` + `register_priority`/`expansion_priority` "
        "(`.ai-work/wiki/task_lens_presets/`) when ordering what to read — a HINT, not a hard "
        "filter; expand or verify raw/source when correctness needs it.",
        "",
        "## Step Objective",
        _format_multiline(step.get("Objective", "")),
        "",
        "## Recommended Mode",
        _format_multiline(step.get("Recommended Mode", "")),
        "",
        "## Applicable Guidelines",
        _format_multiline(step.get("Applicable Guidelines", "")),
        "",
        "## Recommended Skills",
        _format_multiline(step.get("Recommended Skills", "")),
        "",
        "## Inputs",
        _format_multiline(step.get("Inputs", "")),
        "",
        "## Expected Outputs",
        _format_multiline(step.get("Expected Outputs", "")),
        "",
        "## Step Output / Decision Persistence Requirements",
        "- Persist required step outputs as Step Output Artifacts in Workspace.",
        "- Persist HUMAN–AI interaction-derived decisions/conclusions if used by later steps or final output.",
        "- Persist key discussion process as Decision Discussion Trace when it affects later steps/final output.",
        "- ASC references these artifacts; Workspace stores them.",
        "",
        "## Source Verification Requirements",
        "- ASC may carry source routes and verification requirements.",
        "- Verified evidence still requires reading AIWS-readable source representation.",
        "- Record source_refs + verification_level in Step Output Meta when source evidence is used.",
        "",
        "## Done Condition",
        _format_multiline(step.get("Done Condition", "")),
        "",
        "## Notes / Constraints",
        _format_multiline(step.get("Notes / Constraints", "")),
        "",
    ]

    # CR-AIWS-2026-06-052: surface an explicit AIP-level raw-search grant ONLY when the step declares
    # it (lean — the common no-grant case adds no section; the default is governed by the lookup tool
    # + the CLAUDE.md raw-search-authorization rule).
    if allow_raw_search == "true":
        out_lines.extend([
            "## Raw Search Authorization",
            "- This step GRANTS raw (un-registered) search (`allow_raw_search: true`). When a "
            "registered lookup misses, you MAY run `lookup_wiki_source.py --authorized aip "
            "--include-raw on-empty --lookup-mode object`. Raw hits are un-registered — open directly "
            "and register via /build-wiki-source-meta if reused. (CR-AIWS-2026-06-052)",
            "",
        ])
    elif allow_raw_search == "false":
        out_lines.extend([
            "## Raw Search Authorization",
            "- This step explicitly does NOT grant raw search (`allow_raw_search: false`). Raw / "
            "beyond-default-scope search needs HUMAN authorization — halt and ask. (CR-AIWS-2026-06-052)",
            "",
        ])

    # CR-AIWS-2026-06-036 (full-lean): runtime-pointer sections render ONLY when they carry data —
    # empty "- ..." placeholders are dropped. Dead Finding/Open-Question-ID slots were removed
    # entirely (findings live in 04_findings.md, open questions in 05_open_questions.md). Pure
    # duplicates (Step ID/Title, Source AIP, Active References) dropped — covered by frontmatter,
    # the H1, the Step Map, and ## Inputs respectively.
    def _append_if(title: str, rows: list[dict], **kw) -> None:
        if rows:
            out_lines.extend([title, _bullet_refs(rows, **kw), ""])

    _append_if("## Runtime Queue Blockers", blocking_queue)
    _append_if("## Relevant Queue Item IDs", queue_rows)
    _append_if("## Previous Step Results / Handoff Inputs", output_index)
    _append_if("## Decision Discussion Trace References", decision_index,
               id_key="discussion_trace_id")
    _append_if("## Capture Inbox References", capture_rows)

    out_path = Path(ns.output) if ns.output else ws / "00c_active_step_context.md"
    write_text(out_path, "\n".join(out_lines))
    print(f"active step context written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
