#!/usr/bin/env python3
"""Lint a runtime workspace directory.

v0.9.12 alignment:
- preferred Runtime Queue file: 02_runtime_queue.jsonl
- legacy alias: 02_investigation_queue.jsonl
- supports legacy investigation queue schema and new runtime queue schema
- extended Capture Inbox enums
- lint/check is deterministic guardrail, not semantic reviewer
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    LintReport,
    emit_report,
    parse_frontmatter,
    read_jsonl,
    read_text,
)

QUEUE_PRIMARY = "02_runtime_queue.jsonl"
QUEUE_LEGACY = "02_investigation_queue.jsonl"
CAPTURE_FILE = "08_capture_inbox.jsonl"

STEP_OUTPUT_META_REQUIRED = [
    "output_id", "result_type", "working_aip_ref", "step_id",
    "output_locator", "created_at", "review_status",
]
DECISION_TRACE_REQUIRED = [
    "discussion_trace_id", "related_output_id", "working_aip_ref", "step_id",
    "discussion_summary", "question_or_issue", "final_decision", "created_at",
]
STEP_RESULT_TYPES = {
    "output", "decision", "conclusion", "assumption", "clarification",
    "review_judgment", "accepted_limitation",
}
STEP_REVIEW_STATUS = {
    "draft", "ready_for_review", "reviewed", "approved_for_next_step",
    "needs_revision", "rejected", "superseded", "archived", "unknown",
}

# Required non-queue files. Queue is checked separately to support legacy alias.
REQUIRED_FILES = [
    "00_task_brief.md",
    "00b_active_aip.md",
    "00c_active_step_context.md",
    "04_findings.md",
    "05_open_questions.md",
    "07_output_draft.md",
    CAPTURE_FILE,
    "11_output_final.md",
]

LEGACY_QUEUE_HINT_FIELDS = {"kind", "target", "question", "why"}
NEW_QUEUE_HINT_FIELDS = {"title", "type", "reason", "next_action", "blocking"}

# Common validation
QUEUE_COMMON_REQUIRED = ["id", "status"]
QUEUE_COMMON_RECOMMENDED = ["priority"]

QUEUE_STATUS_ENUM = {
    # v0.9.12 canonical
    "pending", "in_progress", "resolved", "blocked", "deferred", "cancelled",
    "moved_to_capture_inbox", "moved_to_open_questions", "moved_to_backlog",
    # v0.9.2 legacy
    "queued", "done", "discarded",
}
QUEUE_PRIORITY_ENUM = {
    # v0.9.12 canonical
    "high", "medium", "low",
    # v0.9.2 legacy
    "critical", "normal", "defer",
}
QUEUE_TYPE_ENUM = {
    "source_check", "design_check", "review_followup", "output_update",
    "active_step_context_check", "step_output_check", "decision_trace_check",
    "package_update_step", "changelog_manifest_step", "feedback_fix",
    "formatting_check", "consistency_check", "source_representation_check",
    "wiki_meta_check", "working_aip_update", "workspace_cleanup",
    "close_check", "other_task_action",
}

CAPTURE_REQUIRED = ["id", "type", "title", "content", "status", "suggested_target"]
CAPTURE_TYPE_ENUM = {
    # v0.9.2 legacy
    "insight", "qa_candidate", "summary_candidate", "playbook_candidate",
    "relation_candidate", "deferred_note", "wiki_update_candidate",
    # v0.9.10+ canonical additions
    "finding_candidate", "wiki_meta_update_candidate",
    "aip_template_improvement_candidate", "run_aip_improvement_candidate",
    "guideline_improvement_candidate", "source_representation_issue",
    "future_backlog_candidate", "notebook_note_candidate",
    # v0.9.23+
    "tooling_opportunity_candidate",
}
CAPTURE_STATUS_ENUM = {
    "captured", "triaged", "promoted", "archived", "discarded",
    "deferred", "retained_local",
}
CAPTURE_TARGET_ENUM = {
    # v0.9.10+ canonical
    "knowledge_hub_curated", "knowledge_hub_reference", "wiki_meta",
    "aip_template", "run_aip", "guideline", "skill", "notebook",
    "future_backlog", "history_only", "discard", "tooling",
    # v0.9.2 legacy aliases
    "wiki_curated", "wiki_reference", "truth", "playbook",
}


def _queue_paths(ws: Path) -> tuple[Path, Path]:
    return ws / QUEUE_PRIMARY, ws / QUEUE_LEGACY


def _select_queue_file(ws: Path, report: LintReport) -> Path | None:
    primary, legacy = _queue_paths(ws)
    if primary.exists() and legacy.exists():
        if legacy.stat().st_size > 0:
            report.warn(
                "queue_dual_files",
                f"both {QUEUE_PRIMARY} and legacy {QUEUE_LEGACY} exist; primary is used",
                path=str(ws),
            )
        else:
            report.info(
                "queue_legacy_empty",
                f"empty legacy queue alias present: {QUEUE_LEGACY}",
                path=str(ws),
            )
        return primary
    if primary.exists():
        return primary
    if legacy.exists():
        report.info(
            "queue_legacy_alias",
            f"using legacy queue alias {QUEUE_LEGACY}; consider migration to {QUEUE_PRIMARY}",
            path=str(ws),
        )
        return legacy
    return None


def _detect_queue_schema(rec: dict) -> str:
    keys = set(rec.keys())
    if keys & NEW_QUEUE_HINT_FIELDS:
        return "runtime_queue"
    if keys & LEGACY_QUEUE_HINT_FIELDS:
        return "legacy_investigation_queue"
    return "unknown"


def _lint_queue(path: Path, report: LintReport) -> None:
    try:
        records = read_jsonl(path)
    except ValueError as e:
        report.error("queue_parse", str(e), path=str(path))
        return

    seen: set[str] = set()
    for idx, rec in enumerate(records, start=1):
        loc = f"line {idx}"
        schema = _detect_queue_schema(rec)

        for f in QUEUE_COMMON_REQUIRED:
            if f not in rec or rec[f] in (None, ""):
                report.error("queue_field", f"queue missing field: {f}",
                             path=str(path), loc=loc)
        for f in QUEUE_COMMON_RECOMMENDED:
            if f not in rec or rec[f] in (None, ""):
                report.warn("queue_field_recommended",
                            f"queue recommended field missing: {f}",
                            path=str(path), loc=loc)

        rid = rec.get("id")
        if rid and rid in seen:
            report.error("queue_dup", f"duplicate queue id: {rid}",
                         path=str(path), loc=loc)
        if rid:
            seen.add(rid)

        if schema == "legacy_investigation_queue":
            report.info("queue_legacy_schema",
                        "legacy investigation queue schema detected",
                        path=str(path), loc=loc)
            if not (rec.get("question") or rec.get("target")):
                report.warn("queue_legacy_missing_context",
                            "legacy queue item should include question or target",
                            path=str(path), loc=loc)
        elif schema == "runtime_queue":
            if not rec.get("title"):
                report.error("queue_title",
                             "runtime queue item missing title",
                             path=str(path), loc=loc)
            if not rec.get("next_action"):
                report.warn("queue_next_action",
                            "runtime queue item should include next_action",
                            path=str(path), loc=loc)
        else:
            report.warn("queue_schema_unknown",
                        "queue item schema is unknown; accepted as extension but should be reviewed",
                        path=str(path), loc=loc)

        status = rec.get("status")
        if status and status not in QUEUE_STATUS_ENUM:
            report.warn("queue_status",
                        f"status '{status}' not in known values {sorted(QUEUE_STATUS_ENUM)}",
                        path=str(path), loc=loc)

        priority = rec.get("priority")
        if priority and priority not in QUEUE_PRIORITY_ENUM:
            report.warn("queue_priority",
                        f"priority '{priority}' not in known values {sorted(QUEUE_PRIORITY_ENUM)}",
                        path=str(path), loc=loc)

        qtype = rec.get("type")
        if qtype and qtype not in QUEUE_TYPE_ENUM:
            report.info("queue_type",
                        f"type '{qtype}' not in known runtime queue types; accepted as extension",
                        path=str(path), loc=loc)


def _lint_capture(path: Path, report: LintReport) -> None:
    try:
        records = read_jsonl(path)
    except ValueError as e:
        report.error("capture_parse", str(e), path=str(path))
        return

    seen: set[str] = set()
    for idx, rec in enumerate(records, start=1):
        loc = f"line {idx}"
        for f in CAPTURE_REQUIRED:
            if f not in rec or rec[f] in (None, ""):
                # suggested_target is useful, but legacy captures may omit it.
                if f == "suggested_target":
                    report.warn("capture_field", f"capture missing recommended field: {f}",
                                path=str(path), loc=loc)
                else:
                    report.error("capture_field", f"capture missing field: {f}",
                                 path=str(path), loc=loc)

        cid = rec.get("id")
        if cid and cid in seen:
            report.error("capture_dup", f"duplicate capture id: {cid}",
                         path=str(path), loc=loc)
        if cid:
            seen.add(cid)

        ctype = rec.get("type")
        if ctype and ctype not in CAPTURE_TYPE_ENUM:
            report.warn("capture_type",
                        f"type '{ctype}' not in known values {sorted(CAPTURE_TYPE_ENUM)}",
                        path=str(path), loc=loc)

        cstatus = rec.get("status")
        if cstatus and cstatus not in CAPTURE_STATUS_ENUM:
            report.warn("capture_status",
                        f"status '{cstatus}' not in known values {sorted(CAPTURE_STATUS_ENUM)}",
                        path=str(path), loc=loc)

        tgt = rec.get("suggested_target")
        if tgt and tgt not in CAPTURE_TARGET_ENUM:
            report.warn("capture_target",
                        f"suggested_target '{tgt}' not in known values {sorted(CAPTURE_TARGET_ENUM)}",
                        path=str(path), loc=loc)

        # CAP-088-02 (CR-AIWS-2026-06-029): only `promoted` captures need source_refs.
        # A sanctioned `triaged` capture with a terminal disposition legitimately has none,
        # so firing on `triaged` produced a recurring post-triage warning floor.
        if cstatus == "promoted" and not rec.get("source_refs"):
            report.warn("capture_refs",
                        "promoted capture should carry source_refs",
                        path=str(path), loc=loc)


def _workspace_status(ws: Path) -> str:
    brief = ws / "00_task_brief.md"
    if not brief.exists():
        return ""
    text = read_text(brief)
    status_line = next(
        (l for l in text.splitlines() if l.strip().lower().startswith("current status")),
        "",
    )
    return status_line.lower()


def _check_close_sanity(ws: Path, report: LintReport) -> None:
    status_line = _workspace_status(ws)
    if "done" in status_line or "closed" in status_line:
        final = ws / "11_output_final.md"
        if not final.exists() or not final.read_text(encoding="utf-8").strip():
            report.error("final_missing",
                         "task marked done/closed but 11_output_final.md is empty",
                         path=str(ws))

        queue = _select_queue_file(ws, report)
        if queue and queue.exists():
            try:
                records = read_jsonl(queue)
                for idx, rec in enumerate(records, start=1):
                    blocking = rec.get("blocking")
                    if isinstance(blocking, str):
                        blocking = blocking.lower() in {"true", "yes", "1"}
                    if blocking and rec.get("status") not in {"resolved", "done", "deferred", "cancelled", "discarded"}:
                        report.error("queue_blocking_open",
                                     f"blocking queue item still open: {rec.get('id', 'line '+str(idx))}",
                                     path=str(queue), loc=f"line {idx}")
            except ValueError:
                pass

        capture = ws / CAPTURE_FILE
        if capture.exists():
            try:
                records = read_jsonl(capture)
                for idx, rec in enumerate(records, start=1):
                    if rec.get("status") == "captured":
                        report.warn("capture_untriaged",
                                    f"capture item remains untriaged at close: {rec.get('id', 'line '+str(idx))}",
                                    path=str(capture), loc=f"line {idx}")
            except ValueError:
                pass



def _read_yamlish_meta(path: Path) -> dict:
    text = read_text(path)
    if text.lstrip().startswith("---"):
        meta, _ = parse_frontmatter(text)
        return meta
    result: dict = {}
    for line in text.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            result[k] = v
    return result


def _lint_step_outputs(ws: Path, report: LintReport) -> None:
    step_outputs = ws / "step_outputs"
    decision_traces = ws / "decision_traces"

    if step_outputs.exists():
        for meta_file in sorted(step_outputs.rglob("*.meta.yml")) + sorted(step_outputs.rglob("*.meta.yaml")):
            meta = _read_yamlish_meta(meta_file)
            rel = str(meta_file)
            for k in STEP_OUTPUT_META_REQUIRED:
                if k not in meta or meta[k] in (None, "", []):
                    report.warn("step_output_meta_field",
                                f"step output meta missing field: {k}",
                                path=rel)
            result_type = meta.get("result_type")
            if result_type and result_type not in STEP_RESULT_TYPES:
                report.warn("step_output_result_type",
                            f"unknown result_type: {result_type}",
                            path=rel)
            review_status = meta.get("review_status")
            if review_status and review_status not in STEP_REVIEW_STATUS:
                report.warn("step_output_review_status",
                            f"unknown review_status: {review_status}",
                            path=rel)
            if meta.get("used_by_steps") and not review_status:
                report.warn("step_output_handoff_review",
                            "used_by_steps exists but review_status is missing",
                            path=rel)
            if meta.get("used_by_final_output") in {"true", True, "yes", "1"} and not (
                meta.get("discussion_trace_locator") or meta.get("source_refs")
            ):
                report.warn("step_output_final_trace",
                            "used_by_final_output=true should have discussion trace and/or source refs",
                            path=rel)
            if meta.get("source_refs") and "verification_level" not in str(meta.get("source_refs")):
                report.warn("step_output_source_verification",
                            "source_refs present but verification_level not visible",
                            path=rel)

        index = step_outputs / "index.jsonl"
        if index.exists():
            try:
                rows = read_jsonl(index)
                seen = set()
                for idx, row in enumerate(rows, start=1):
                    oid = row.get("output_id")
                    if not oid:
                        report.warn("step_output_index_field", "index row missing output_id",
                                    path=str(index), loc=f"line {idx}")
                    elif oid in seen:
                        report.error("step_output_index_duplicate", f"duplicate output_id: {oid}",
                                     path=str(index), loc=f"line {idx}")
                    else:
                        seen.add(oid)
            except ValueError as e:
                report.error("step_output_index_parse", str(e), path=str(index))

    if decision_traces.exists():
        for trace_file in sorted(decision_traces.rglob("*.yml")) + sorted(decision_traces.rglob("*.yaml")):
            if trace_file.name == "index.yml":
                continue
            meta = _read_yamlish_meta(trace_file)
            rel = str(trace_file)
            for k in DECISION_TRACE_REQUIRED:
                if k not in meta or meta[k] in (None, "", []):
                    report.warn("decision_trace_field",
                                f"decision trace missing field: {k}",
                                path=rel)
            if not (meta.get("options_considered") or meta.get("rationale")):
                report.info("decision_trace_rationale",
                            "important decision trace should include options_considered and rationale when available",
                            path=rel)

        index = decision_traces / "index.jsonl"
        if index.exists():
            try:
                rows = read_jsonl(index)
                seen = set()
                for idx, row in enumerate(rows, start=1):
                    tid = row.get("discussion_trace_id")
                    if not tid:
                        report.warn("decision_trace_index_field", "index row missing discussion_trace_id",
                                    path=str(index), loc=f"line {idx}")
                    elif tid in seen:
                        report.error("decision_trace_index_duplicate", f"duplicate discussion_trace_id: {tid}",
                                     path=str(index), loc=f"line {idx}")
                    else:
                        seen.add(tid)
            except ValueError as e:
                report.error("decision_trace_index_parse", str(e), path=str(index))


def lint_workspace_dir(ws: Path, report: LintReport) -> None:
    if not ws.is_dir():
        report.error("not_a_dir", f"workspace not found: {ws}")
        return

    for name in REQUIRED_FILES:
        if not (ws / name).exists():
            report.error("file_missing", f"required file missing: {name}",
                         path=str(ws))

    queue = _select_queue_file(ws, report)
    if queue is None:
        report.warn("queue_missing",
                    f"Runtime Queue missing: expected {QUEUE_PRIMARY}; legacy alias {QUEUE_LEGACY} also absent",
                    path=str(ws))
    else:
        _lint_queue(queue, report)

    capture = ws / CAPTURE_FILE
    if capture.exists():
        _lint_capture(capture, report)

    _check_close_sanity(ws, report)
    _lint_step_outputs(ws, report)

    # Active Step Context frontmatter sanity
    asc = ws / "00c_active_step_context.md"
    if asc.exists():
        meta, _ = parse_frontmatter(read_text(asc))
        if meta.get("artifact_type") and meta.get("artifact_type") != "active_step_context":
            report.error("asc_type",
                         f"active_step_context artifact_type wrong: {meta.get('artifact_type')}",
                         path=str(asc))
        if not (meta.get("active_step_id") or meta.get("step_id")):
            report.warn("asc_active_step",
                        "active step context missing active_step_id/step_id",
                        path=str(asc))
        if not meta.get("staleness_status"):
            report.info("asc_staleness",
                        "active step context missing staleness_status",
                        path=str(asc))


def main() -> int:
    p = argparse.ArgumentParser(description="Lint runtime workspace")
    p.add_argument("--workspace", required=True)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--format", choices=["text", "json"], default="text")
    ns = p.parse_args()

    ws = Path(ns.workspace).resolve()
    report = LintReport(target=str(ws))
    lint_workspace_dir(ws, report)
    return emit_report(report, ns.format, ns.strict)


if __name__ == "__main__":
    raise SystemExit(main())
