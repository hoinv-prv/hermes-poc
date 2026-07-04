#!/usr/bin/env python3
"""Lint AIP files (ROOT / PLAN / EXEC / LOCAL).

Enforces AIP_Detail_Spec_MVP_v0_1 §5–§12:
- metadata: artifact_type, artifact_id, status enum, root_aip / plan_source
- full required sections per AIP type (§6.1–§6.4)
- full step structure per §7.1 (id, title, objective, mode, guidelines,
  inputs, expected outputs, done condition, notes / constraints)
- reference lint: guideline / skill paths (warn if missing on disk)
- live-working-file guard: warn when AIP is being used as a runtime tracker
  (Done Criteria with [x], runtime metrics inline)

Usage:
  lint_aip.py --path <file-or-dir> [--strict] [--format text|json]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    LintReport,
    apply_lint_accept,
    emit_report,
    extract_sections,
    find_ai_work_root,
    has_section,
    parse_aip_steps,
    parse_frontmatter,
    read_text,
)

STATUS_ENUM = {"draft", "active", "done", "archived"}
TYPE_ENUM = {"aip_root", "aip_plan", "aip_exec", "aip_local"}

# Required sections per AIP_Detail_Spec §6. Some entries accept alternative
# section names ("A | B") so templates that split sections still pass.
REQUIRED_SECTIONS = {
    "aip_root": [
        "Objective", "Project Scope", "Project Priorities",
        "Core References", "Constraints / Assumptions", "Notes",
    ],
    "aip_plan": [
        "Objective",
        "Background / Context",
        "Scope",
        "Expected Outputs",
        "References to Read First",
        "Assumptions / Constraints",
        "Open Questions | Open Questions / Risks",
        "Risks / Constraints | Risks",
        "Execution Steps",
        "Done Criteria",
        "Review Points",
    ],
    "aip_exec": [
        "Objective",
        "Execution Scope",
        "Expected Outputs",
        "References to Read First",
        "Execution Steps",
        "Current Risks / Constraints",
        "Done Criteria",
        "Review / Finalization Notes | Self-check / Review Points | Finalization Notes",
    ],
    "aip_local": [
        "Objective", "Notes",
        "Personal Constraints / Reminders",
        "Local Execution Notes",
    ],
}

# Required step fields per §7.1 (Step ID + Title come from the header regex).
REQUIRED_STEP_FIELDS = [
    "Objective",
    "Recommended Mode",
    "Applicable Guidelines",
    "Inputs",
    "Expected Outputs",
    "Done Condition",
    "Notes / Constraints",
]

# Heuristics for the "live working file" guard.
RUNTIME_METRIC_RE = re.compile(
    r"\(\s*\d{2,}\s+(metas|entries|chapters|files|items|records|companions|docs)\b",
    re.IGNORECASE,
)

# Heuristics for the "wiki-first preflight at HARD GATE" rule.
# See product/procedural/skills/run-aip/SKILL.md §"Wiki-first preflight at HARD GATE".
HARD_GATE_RE = re.compile(r"\bHARD\s+GATE\b", re.IGNORECASE)
WIKI_REF_RE = re.compile(
    r"(\bwiki:[^\s/]|product/wiki_guidelines/|\.ai-work/wiki/)",
    re.IGNORECASE,
)
WIKI_NONE_RE = re.compile(r"\bwiki:none\b", re.IGNORECASE)


def _check_wiki_first_preflight(step: dict, rel: str, sid: str, report: LintReport) -> None:
    """Warn when a HARD GATE step lacks a wiki cross-reference in Applicable Guidelines.

    Detection: step is HARD GATE if "HARD GATE" appears in the step TITLE only
    (CR-AIWS-2026-06-007 Change 1). Objective / Notes are intentionally excluded —
    they commonly quote or mention "HARD GATE" as data, not as gate intent, which
    produced false-positives (e.g. an apply-AIP for a CR about the preflight rule).
    Convention marks a real HARD GATE in the step title, e.g. "(HARD GATE)".
    Pass if Applicable Guidelines contains a wiki path (under product/wiki_guidelines/
    or .ai-work/wiki/) or the explicit opt-out "wiki:none".
    """
    title = step.get("title", "") or ""
    if not HARD_GATE_RE.search(title):
        return
    guidelines = step.get("Applicable Guidelines", "") or ""
    if WIKI_NONE_RE.search(guidelines):
        return
    if WIKI_REF_RE.search(guidelines):
        return
    report.warn(
        "wiki_first_preflight_at_hard_gate",
        f"HARD GATE step {sid} lacks a Wiki cross-reference in 'Applicable Guidelines'. "
        f"Per run-aip SKILL.md §'Wiki-first preflight at HARD GATE', consult Wiki via "
        f"lookup_wiki_source.py before posing the clarifying question and cite the relevant "
        f"wiki path (or add 'wiki:none' as a bullet to confirm explicit opt-out).",
        path=rel, loc=sid,
    )


def _lint_file(path: Path, ai_work: Path | None, report: LintReport) -> None:
    rel = str(path)
    text = read_text(path)
    meta, body = parse_frontmatter(text)

    if not meta:
        report.error("meta_missing", "no YAML frontmatter", path=rel)
        return

    atype = meta.get("artifact_type", "")
    if atype not in TYPE_ENUM:
        report.error("meta_type", f"artifact_type '{atype}' not in {sorted(TYPE_ENUM)}", path=rel)
        return

    if not meta.get("artifact_id"):
        report.error("meta_id", "artifact_id missing", path=rel)

    # S-04: title presence (per AIP_REVIEW_CHECKLIST_v0_3 §A.1)
    if not meta.get("title"):
        report.error("meta_title", "title missing or empty", path=rel)

    # S-06: project presence (per AIP_REVIEW_CHECKLIST_v0_3 §A.1)
    if not meta.get("project"):
        report.error("meta_project", "project missing or empty", path=rel)

    # S-07: updated_at presence + YYYY-MM-DD format (per AIP_REVIEW_CHECKLIST_v0_3 §A.1)
    # CR-AIWS-2026-06-007 Change 2 (Option A): template files under aip(_)templates/
    # intentionally ship the literal `YYYY-MM-DD` placeholder. Downgrade THAT to info
    # (not error) so the template floor does not pollute lint_all. Non-template files,
    # and template files with a real/malformed date, still error as before.
    _is_template = "/aip/templates/" in path.as_posix() or "/aip_templates/" in path.as_posix()
    updated_at = meta.get("updated_at", "")
    if _is_template and str(updated_at) == "YYYY-MM-DD":
        report.info("meta_updated_at",
                    "template placeholder updated_at (YYYY-MM-DD) — expected for template files",
                    path=rel)
    elif not updated_at:
        report.error("meta_updated_at", "updated_at missing", path=rel)
    elif not re.match(r"^\d{4}-\d{2}-\d{2}$", str(updated_at)):
        report.error("meta_updated_at",
                     f"updated_at format invalid (expected YYYY-MM-DD): {updated_at}",
                     path=rel)

    status = meta.get("status", "")

    def _status_hint(value: str) -> str:
        # Common drift: humans/AI write 'completed' (or variants) instead of 'done'.
        # Per AIP_Detail_Spec §5.6 the only finished-state value is 'done'.
        aliases = {
            "completed": "done",
            "complete": "done",
            "candidate-completed": "done",
            "finished": "done",
            "closed": "done",
            "in_progress": "active",
            "in-progress": "active",
            "open": "active",
            "todo": "draft",
            "wip": "active",
        }
        suggestion = aliases.get(value.strip().lower())
        return f" (did you mean '{suggestion}'?)" if suggestion else ""

    if atype == "aip_root":
        if status and status not in STATUS_ENUM:
            report.error("meta_status", f"status '{status}' invalid{_status_hint(status)}", path=rel)
    else:
        if status not in STATUS_ENUM:
            report.error("meta_status",
                         f"status '{status}' not in {sorted(STATUS_ENUM)}{_status_hint(status)}",
                         path=rel)

    if atype in ("aip_plan", "aip_exec") and not meta.get("root_aip"):
        report.error("meta_root_aip", "root_aip missing", path=rel)
    if atype == "aip_exec" and not meta.get("plan_source"):
        report.warn("meta_plan_source",
                    "plan_source not declared (direct execution allowed but should be explicit)",
                    path=rel)

    for sec in REQUIRED_SECTIONS.get(atype, []):
        # Accept "A | B | C" meaning at least one of A/B/C must be present
        alternatives = [s.strip() for s in sec.split("|")]
        if not any(has_section(body, alt) for alt in alternatives):
            label = " or ".join(alternatives) if len(alternatives) > 1 else alternatives[0]
            report.error("section_missing", f"required section missing: {label}", path=rel)

    # ---- Live-working-file guard (§2.3 + §10.2) ----
    if atype in ("aip_plan", "aip_exec"):
        sections = extract_sections(body)
        done_body = sections.get("Done Criteria", "")
        for line in done_body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                report.warn(
                    "live_working_file",
                    "Done Criteria contains '[x]' — AIP must stay stable; "
                    "progress tracking belongs in the workspace "
                    "(07_output_draft.md / active step context)",
                    path=rel, loc="Done Criteria",
                )
                break
        for sec_name, sec_body in sections.items():
            for line in sec_body.splitlines():
                if RUNTIME_METRIC_RE.search(line):
                    report.warn(
                        "runtime_metric_in_aip",
                        f"runtime metric inline ('{line.strip()[:60]}…') — "
                        "move concrete counts/findings to workspace "
                        "04_findings.md",
                        path=rel, loc=sec_name,
                    )
                    break

    if atype in ("aip_plan", "aip_exec"):
        steps = parse_aip_steps(body)
        if not steps:
            report.error("steps_empty", "no Execution Steps found", path=rel)
        seen_ids: set[str] = set()
        for step in steps:
            sid = step["step_id"]
            loc = sid
            if sid in seen_ids:
                report.error("step_dup", f"duplicate step id: {sid}", path=rel, loc=loc)
            seen_ids.add(sid)
            for f in REQUIRED_STEP_FIELDS:
                if not step.get(f):
                    # CAP-088-03 (CR-AIWS-2026-06-029): distinguish "present but indented"
                    # from truly missing. An indented field label (e.g. 2 spaces, rendering as a
                    # bullet-list continuation) is not recognised as a column-0 field, so it is
                    # absorbed into another field's value. Detect it there and emit a precise
                    # message; it stays an error (markdown is malformed).
                    _label_re = re.compile(r"(?m)^[ \t]+" + re.escape(f) + r"[ \t]*:[ \t]*$")
                    if any(isinstance(v, str) and _label_re.search(v) for v in step.values()):
                        report.error("step_field_indented",
                                     f"step {sid} field '{f}' present but indented; move its "
                                     f"label to column 0 (lint anchors required step fields "
                                     f"at column 0)", path=rel, loc=loc)
                    else:
                        report.error("step_field_missing",
                                     f"step {sid} missing field: {f}", path=rel, loc=loc)

            # Wiki-first preflight rule — warn-level
            _check_wiki_first_preflight(step, rel, sid, report)

            if ai_work is not None:
                for field_name in ("Applicable Guidelines", "Recommended Skills"):
                    raw = step.get(field_name, "")
                    for line in raw.splitlines():
                        line = line.strip().lstrip("-").strip()
                        if not line or line == "...":
                            continue
                        candidate = line.split()[0].strip("`")
                        if candidate.startswith(("http://", "https://")):
                            continue
                        if "/" in candidate and not candidate.endswith(":"):
                            search = [
                                ai_work / candidate,
                                ai_work / "procedural" / candidate,
                                ai_work.parent / candidate,
                            ]
                            if not any(c.exists() for c in search):
                                report.warn(
                                    "ref_missing",
                                    f"{field_name} path not found: {candidate}",
                                    path=rel, loc=sid,
                                )

        # Sequential step numbering check — warn on gaps (e.g. STEP-04 → STEP-06)
        _step_nums: list[int] = []
        for _s in steps:
            _m = re.search(r"(\d+)$", _s["step_id"])
            if _m:
                _step_nums.append(int(_m.group(1)))
        for _i in range(1, len(_step_nums)):
            if _step_nums[_i] != _step_nums[_i - 1] + 1:
                report.warn(
                    "step_numbering_gap",
                    f"step numbering gap: STEP-{_step_nums[_i-1]:02d} → "
                    f"STEP-{_step_nums[_i]:02d}",
                    path=rel,
                )


def _collect(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(p for p in root.rglob("*.md") if "/aip/" in p.as_posix() or p.name == "AIP_ROOT.md")


def main() -> int:
    p = argparse.ArgumentParser(description="Lint AIP files")
    p.add_argument("--path", required=True, help="File or directory to lint")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--show-accepted", action="store_true",
                   help="list lint_accept-muted findings instead of just tallying them")
    ns = p.parse_args()

    target = Path(ns.path).resolve()
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 2

    try:
        ai_work = find_ai_work_root(target) / ".ai-work"
    except SystemExit:
        ai_work = None

    files = _collect(target)
    report = LintReport(target=str(target))
    if not files:
        report.warn("no_files", "no AIP files found")
    for f in files:
        _lint_file(f, ai_work, report)

    if ai_work is not None:
        apply_lint_accept(report, ai_work)
    return emit_report(report, ns.format, ns.strict, ns.show_accepted)


if __name__ == "__main__":
    raise SystemExit(main())
