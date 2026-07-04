#!/usr/bin/env python3
"""Lint wiki knowledge artifacts and wiki source-side artifacts.

Three target groups:
  1. Official wiki entries  (.ai-work/wiki/<type>/*.md)
  2. Wiki source metas      (.ai-work/wiki_sources/meta/*.md or *.yml)
  3. Wiki source index      (.ai-work/wiki_sources/index.jsonl)

Each has its own required-metadata + section checks, per
Wiki_Truth_History_Spec_MVP_v0_1.md and Lint_and_Tooling_Spec_MVP_v0_2.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    DATA_FLOW_TYPES,
    NODE_KIND_ARTIFACT,
    NODE_KIND_OBJECT,
    OBJECT_LOCATOR_SENTINEL,
    WSM_REQUIRED_LOG_FIELDS,
    SEV_ERROR,
    LintReport,
    apply_lint_accept,
    emit_report,
    extract_sections,
    find_ai_work_root,
    has_section,
    parse_frontmatter,
    read_jsonl,
    read_text,
    resolve_locator,
)

# Source Build Routing registry (CR-AIWS-2026-05-019 Stage 2).
# Keep in sync with route_build_tool.KNOWN_PLACEHOLDERS / REFRESH_MODES.
_BUILD_ROUTING_PLACEHOLDERS = {"root", "prefix", "subdir", "artifact"}
_BUILD_ROUTING_REFRESH_MODES = {"rerun_tool"}

# CR-AIWS-2026-06-024: wiki-meta updated_at / last_verified_at accept BOTH a legacy date
# (YYYY-MM-DD) AND a UTC ISO 8601 timestamp — permanently. Legacy date metas MUST stay valid
# (no forced migration), so a value matching either form is OK; only a malformed value is flagged.
_TS_OR_DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}$"                                                 # legacy date
    r"|^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$"  # UTC ISO 8601 timestamp
)


def _valid_ts_or_date(v) -> bool:
    """True if v is a YYYY-MM-DD date or an ISO-8601 timestamp (or empty — presence is checked elsewhere)."""
    return bool(_TS_OR_DATE_RE.match(str(v).strip())) if v else True


ENTRY_REQUIRED_META = [
    "artifact_type", "entry_type", "artifact_id", "title",
    "knowledge_class", "use_rule", "status",
    "canonical_references", "last_verified_at", "updated_at",
]
ENTRY_SECTIONS = ["Purpose", "Scope", "Canonical References", "Recommended Next Reads"]

ENTRY_TYPE_ENUM = {"domain", "function", "module", "data", "pattern", "reference"}
KNOWLEDGE_CLASS_ENUM = {"source_of_truth", "curated", "reference", "history"}
USE_RULE_ENUM = {"authoritative", "verify_when_decision_matters",
                 "verify_before_use", "historical_only"}
ENTRY_STATUS_ENUM = {"active", "needs_review", "superseded"}

META_REQUIRED = [
    "source_id", "title", "source_type", "artifact_locator", "profile_id", "status",
]
META_SECTIONS = ["Summary", "Knowledge Targets", "Lookup Keys"]  # Profile Mapping dropped (CR-024): mirrored frontmatter profile_id

INDEX_REQUIRED = [
    "source_id", "title", "source_type", "artifact_locator",
    "profile_id", "summary_short", "knowledge_targets", "status",
]

WTA_OPTIONAL_META_FIELDS = [
    "authority_level",
    "freshness_status",
    "source_representation_status",
    "knowledge_value",
    "intended_ai_use",
    "promotion_status",
]

SRI_OPTIONAL_META_FIELDS = [
    "original_source_locator",
    "representation_locator",
    "representation_type",
    "conversion_method",
    "conversion_date",
    "converted_by",
    "conversion_limitations",
    "representation_scope",
]
AIWS_READABLE_EXTS = {".md", ".txt", ".json", ".jsonl", ".csv", ".yml", ".yaml"}
RAW_NON_TEXT_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".bin"}

AUTHORITY_LEVEL_ENUM = {
    "source_of_truth", "curated_reference", "working_reference",
    "history_reference", "candidate", "unknown",
}
SOURCE_REPRESENTATION_STATUS_ENUM = {
    "complete", "partial", "needs_review", "failed", "unknown", "not_applicable",
}
PROMOTION_STATUS_ENUM = {
    "approved", "candidate", "draft", "needs_review", "archived",
}
SOURCE_TYPE_VOCAB = {
    "requirement_definition", "basic_design", "detail_design",
    "customer_requirement", "process_guideline", "process_template",
    "sop", "canonical_doc", "test_spec", "methodology_spec",
    "meeting_note", "legacy_design", "screen_mockup", "api_manual",
    "db_schema", "unit_test_spec", "wiki_guideline",  # wiki_guideline: CR-AIWS-2026-05-034 (also profile-declared)
}
UNSAFE_RECOMMENDATIONS = {
    "approve_update", "auto_promote", "auto_apply",
}

# WSM_REQUIRED_LOG_FIELDS lives in _common (single source of truth, shared with
# append_maintenance_log) — imported above so writer and linter cannot drift.
WSM_ACTION_ENUM = {
    "refresh_draft_created", "meta_applied", "index_rebuilt", "candidate_created",
    "candidate_deferred", "source_representation_issue_recorded", "meta_archived",
    "meta_restored", "no_action_recorded", "source_deregistered", "aiws_package_apply",
    "relations_rebuilt",
}

# CR-AIWS-2026-06-020: stray tool-call / markup artifacts that can survive into a meta
# body via a botched Write (e.g. </invoke>). They parse-harmlessly, so extract_sections
# folds them into the last section and the rest of the linter never sees them.
_TRAILING_JUNK_RE = re.compile(
    r"</?(?:invoke|antml:parameter|function_calls|parameter|content)\b", re.IGNORECASE
)


@lru_cache(maxsize=8)
def _ms_config(ai_work_str: str) -> tuple:
    """(multi_system: bool, systems: frozenset) from .ai-work/project_profile.yml (CR-06-017). Absent → off."""
    p = Path(ai_work_str) / "project_profile.yml"
    if not p.exists():
        return (False, frozenset())
    meta, _ = parse_frontmatter("---\n" + p.read_text(encoding="utf-8") + "\n---\n")
    ms = str((meta or {}).get("multi_system", "")).strip().lower() in ("true", "1", "yes")
    systems = (meta or {}).get("systems") or []
    systems = systems if isinstance(systems, list) else []
    return (ms, frozenset(str(s).strip() for s in systems if str(s).strip()))



def _looks_raw_non_text(locator: str) -> bool:
    if not locator:
        return False
    suffix = Path(str(locator).split("#")[0]).suffix.lower()
    return suffix in RAW_NON_TEXT_EXTS


def _looks_aiws_readable(locator: str) -> bool:
    if not locator:
        return False
    suffix = Path(str(locator).split("#")[0]).suffix.lower()
    return suffix in AIWS_READABLE_EXTS


def _lint_wiki_entry(path: Path, report: LintReport) -> None:
    rel = str(path)
    meta, body = parse_frontmatter(read_text(path))
    if meta.get("artifact_type") != "wiki_entry":
        return  # not an entry (might be a README, glossary, etc.)

    for k in ENTRY_REQUIRED_META:
        if k not in meta or meta[k] in (None, "", []):
            report.error("entry_meta", f"missing metadata: {k}", path=rel)

    # CR-AIWS-2026-06-024: accept date OR UTC ISO 8601 timestamp; flag only malformed values.
    for ts_field in ("updated_at", "last_verified_at"):
        val = meta.get(ts_field)
        if val and not _valid_ts_or_date(val):
            report.warn("entry_ts_format",
                        f"{ts_field} should be a date (YYYY-MM-DD) or UTC ISO 8601 timestamp: {val}",
                        path=rel)

    et = meta.get("entry_type")
    if et and et not in ENTRY_TYPE_ENUM:
        report.error("entry_type", f"entry_type '{et}' invalid", path=rel)
    kc = meta.get("knowledge_class")
    if kc and kc not in KNOWLEDGE_CLASS_ENUM:
        report.error("knowledge_class", f"knowledge_class '{kc}' invalid", path=rel)
    ur = meta.get("use_rule")
    if ur and ur not in USE_RULE_ENUM:
        report.error("use_rule", f"use_rule '{ur}' invalid", path=rel)
    st = meta.get("status")
    if st and st not in ENTRY_STATUS_ENUM:
        report.error("entry_status", f"status '{st}' invalid", path=rel)

    for sec in ENTRY_SECTIONS:
        if not has_section(body, sec):
            report.error("entry_section", f"missing section: {sec}", path=rel)

    if kc == "source_of_truth":
        refs = meta.get("canonical_references") or []
        if not refs:
            report.warn("sot_weak_ref",
                        "source_of_truth entry has no canonical_references",
                        path=rel)

    if st == "needs_review":
        report.warn("needs_review", "entry is marked needs_review", path=rel)


@lru_cache(maxsize=None)
def _allowed_source_types(profiles_dir_str: str) -> frozenset:
    """Valid source_types = canonical base vocab ∪ source_type declared by each shipped
    profile (CR-AIWS-2026-05-008 / IR-04). A project adds a type by declaring it on a
    profile — no hardcoded edit needed, and lint stays in sync with shipped profiles.
    """
    allowed = set(SOURCE_TYPE_VOCAB)
    pdir = Path(profiles_dir_str)
    if pdir.is_dir():
        for f in pdir.glob("*.yml"):
            lines = read_text(f).splitlines()
            for i, line in enumerate(lines):
                s = line.strip()
                # singular form: `source_type: X` (one value)
                if s.startswith("source_type:"):
                    val = s.split(":", 1)[1].strip().strip("\"'")
                    if val:
                        allowed.add(val)
                # plural form: `source_types: [a, b]` OR a `- item` block list
                # (CR-AIWS-2026-06-004 C3 — a profile may declare many source_types,
                # e.g. knowledge_object.yml carries the object kinds per DP2/DP3).
                elif s.startswith("source_types:"):
                    inline = s.split(":", 1)[1].strip()
                    if inline.startswith("[") and inline.endswith("]"):
                        for v in inline[1:-1].split(","):
                            v = v.strip().strip("\"'")
                            if v:
                                allowed.add(v)
                    else:
                        for nxt in lines[i + 1:]:
                            t = nxt.strip()
                            if t.startswith("- "):
                                v = t[2:].strip().strip("\"'")
                                if v:
                                    allowed.add(v)
                            elif t and not t.startswith("#"):
                                break
    return frozenset(allowed)


def _ai_work_for(path: Path) -> "Path | None":
    for parent in path.parents:
        if parent.name == ".ai-work":
            return parent
    return None


def _orphan_artifact_check(meta_path: Path, artifact_locator: str,
                           report: LintReport, rel: str) -> None:
    """Warn when a source meta's artifact_locator resolves to a nonexistent file.

    Checks existence regardless of locator style — __PROJECT_ROOT__ placeholder,
    project-relative, OR absolute path. (Portability of absolute paths is a separate
    concern flagged by meta_absolute_locator; existence is independent.)
    URLs / external locators (with '://') are skipped.
    """
    # node_kind=object metas have NO backing file — the __OBJECT__ sentinel is not a path
    # and must never be flagged as an orphan (CR-AIWS-2026-05-023 DP7/INV-9).
    if artifact_locator == OBJECT_LOCATOR_SENTINEL:
        return
    if not artifact_locator or "://" in artifact_locator:
        return
    loc = str(artifact_locator).split("#")[0].strip()
    if not loc:
        return
    # derive project root from the meta path (.ai-work/wiki_sources/meta/...)
    project_root = None
    for parent in meta_path.parents:
        if parent.name == ".ai-work":
            project_root = parent.parent
            break
    if project_root is None:
        return  # cannot resolve (e.g. external/local meta) — skip
    if loc.startswith("__PROJECT_ROOT__"):
        resolved = project_root / loc[len("__PROJECT_ROOT__"):].replace("\\", "/").lstrip("/")
    elif (len(loc) >= 2 and loc[1] == ":") or loc.startswith("/"):
        resolved = Path(loc)  # absolute — STILL existence-check (orphan detection)
    else:
        resolved = project_root / loc.replace("\\", "/").lstrip("/")
    if not resolved.exists():
        report.warn("meta_orphan_artifact",
                    f"artifact_locator points to a nonexistent file: {artifact_locator}",
                    path=rel, loc="artifact_locator")


def _lint_source_meta(path: Path, report: LintReport) -> None:
    rel = str(path)
    text = read_text(path)
    meta, body = parse_frontmatter(text)
    if not meta:
        report.error("meta_missing", "no frontmatter on source meta", path=rel)
        return
    if meta.get("artifact_type") != "wiki_source_meta":
        report.warn("meta_type",
                    f"artifact_type != wiki_source_meta (got {meta.get('artifact_type')})",
                    path=rel)
    # Two-kind node model (CR-AIWS-2026-05-023): node_kind is meta-only, default 'artifact'
    # (DP2 — zero migration). is_object drives the object-scoped INV guards below.
    node_kind = meta.get("node_kind") or NODE_KIND_ARTIFACT
    is_object = node_kind == NODE_KIND_OBJECT
    # profile_id is REQUIRED for ALL metas incl. node_kind=object — object metas carry
    # profile_id: knowledge_object (CR-AIWS-2026-06-004 C1; supersedes CR-035 OP-2 omit-exemption).
    # EXCEPT binary-by-design stubs (CR-AIWS-2026-06-066): not_meta_applicable metas have no text
    # body → profile_id is intentionally absent (scoped exemption from CR-004 C1). Identity fields stay required.
    not_applicable = meta.get("not_meta_applicable") is True
    required_fields = ([k for k in META_REQUIRED if k != "profile_id"]
                       if not_applicable else META_REQUIRED)
    for k in required_fields:
        if k not in meta or meta[k] in (None, "", []):
            report.error("meta_field", f"missing field: {k}", path=rel)
    # CR-AIWS-2026-06-024: updated_at (optional on source metas) accepts date OR UTC ISO 8601 timestamp.
    ua = meta.get("updated_at")
    if ua and not _valid_ts_or_date(ua):
        report.warn("meta_ts_format",
                    f"updated_at should be a date (YYYY-MM-DD) or UTC ISO 8601 timestamp: {ua}",
                    path=rel)
    # not_meta_applicable stubs intentionally omit Summary/Knowledge Targets/Lookup Keys (CR-066).
    if not not_applicable:
        for sec in META_SECTIONS:
            if not has_section(body, sec):
                report.error("meta_section", f"missing section: {sec}", path=rel)
    # IR-14: flag degenerate/placeholder Summary. WARN for artifact metas; promoted to
    # ERROR for node_kind=object metas (CR-AIWS-2026-05-023 INV-4: an object is never empty).
    if has_section(body, "Summary"):
        summary_text = (extract_sections(body).get("Summary", "") or "").strip()
        if (not summary_text
                or summary_text.startswith("(no semantic summary")
                or len(summary_text) < 40):
            if is_object:
                report.error("meta_summary_degenerate",
                             "Summary is empty/placeholder or too short; a node_kind=object meta "
                             "must carry a real summary (CR-023 INV-4: objects are never empty)",
                             path=rel)
            else:
                report.warn("meta_summary_degenerate",
                            "Summary is empty/placeholder or too short to be useful; "
                            "rebuild with --summary for a quality meta",
                            path=rel)
    # CR-017: warn on unresolved Related Sources scaffold (left-over TODO markers)
    if has_section(body, "Related Sources"):
        rs_text = extract_sections(body).get("Related Sources", "") or ""
        if ("<SRC-id: TODO>" in rs_text) or ("TODO: fill real source_ids" in rs_text):
            report.warn("meta_related_sources_todo",
                        "Related Sources scaffold left unresolved (contains <SRC-id: TODO>); "
                        "fill real source_ids or delete the section",
                        path=rel)
        # CR-AIWS-2026-06-002: warn (never error) a data-flow edge left with a blank basis note.
        # Conservative — detects ABSENCE of a note only; cannot judge whether a note is meaningful.
        try:
            import build_relations as _br
            for _edge in _br.parse_related_sources(rs_text):
                if (_edge.get("relationship_type") in DATA_FLOW_TYPES
                        and not (_edge.get("relationship_basis_note") or "").strip()):
                    report.warn("relations_thin_basis",
                                f"data-flow edge → {_edge.get('target_ref','?')} "
                                f"(role: {_edge.get('relationship_type')}) has no basis note; add objective "
                                f"stakes/coupling per Knowledge_Expansion_Link_Spec §4.4",
                                path=rel)
        except Exception:  # noqa: BLE001
            pass
    for k in WTA_OPTIONAL_META_FIELDS:
        if k not in meta or meta[k] in (None, "", []):
            report.info("meta_wta_field",
                        f"recommended WTA field missing: {k}",
                        path=rel)

    for k in SRI_OPTIONAL_META_FIELDS:
        if k not in meta or meta[k] in (None, "", []):
            report.info("meta_sri_field",
                        f"recommended SRI field missing: {k}",
                        path=rel)

    source_type = meta.get("source_type", "")
    ai_work = _ai_work_for(path)
    allowed_types = (_allowed_source_types(str(ai_work / "wiki_sources" / "profiles"))
                     if ai_work else frozenset(SOURCE_TYPE_VOCAB))
    if source_type and source_type not in allowed_types:
        report.warn("meta_source_type_unknown",
                    f"unrecognized source_type '{source_type}'; use a canonical base value "
                    f"or declare it via a profile's source_type (wiki_sources/profiles/)",
                    path=rel)

    authority = meta.get("authority_level")
    if authority and authority not in AUTHORITY_LEVEL_ENUM:
        report.warn("meta_authority",
                    f"unknown authority_level: {authority}",
                    path=rel)

    artifact_locator = meta.get("artifact_locator", "")
    original_locator = meta.get("original_source_locator", "")
    representation_locator = meta.get("representation_locator", "")

    # ── Two-kind node model invariants (CR-AIWS-2026-05-023) ──────────────────
    # INV-2: the retired 3-layer Knowledge-Object record fields must never reappear as a
    # frontmatter KEY in ANY meta (object OR artifact) — ERROR. (Body text / lookup_keys that
    # merely mention these terms — e.g. a spec describing their removal — is fine; only a
    # real frontmatter key is forbidden.)
    for forbidden in ("object_id", "expansion_links", "canonical_object_refs", "source_anchor"):
        if forbidden in meta:
            report.error("meta_forbidden_ko_field",
                         f"forbidden frontmatter field '{forbidden}' — retired Knowledge-Object "
                         f"record field (CR-023 INV-2)",
                         path=rel)
    # INV-9: the __OBJECT__ sentinel and node_kind=object must agree (both directions).
    if artifact_locator == OBJECT_LOCATOR_SENTINEL and not is_object:
        report.error("meta_object_sentinel_misuse",
                     f"artifact_locator={OBJECT_LOCATOR_SENTINEL} is reserved for node_kind=object "
                     f"metas (CR-023 INV-9)",
                     path=rel)
    if is_object and artifact_locator != OBJECT_LOCATOR_SENTINEL:
        report.error("meta_object_locator",
                     f"node_kind=object meta must set artifact_locator: {OBJECT_LOCATOR_SENTINEL} "
                     f"(CR-023 INV-9)",
                     path=rel)
    if is_object:
        # INV-4: an object is never empty — it must declare >=1 ## Related Sources out-edge.
        rs_text = extract_sections(body).get("Related Sources", "")
        try:
            import build_relations as _br
            n_out = len(_br.parse_related_sources(rs_text))
        except Exception:  # noqa: BLE001
            n_out = 1 if rs_text.strip() else 0
        if n_out == 0:
            report.error("meta_object_no_outedge",
                         "node_kind=object meta declares no ## Related Sources out-edge "
                         "(CR-023 INV-4: an object must never be empty — needs >=1 out-edge)",
                         path=rel)
        # INV-3 / DP5: an object is a POINTER, never a container/aggregator.
        if re.search(r"(?im)^#{1,3}\s*(Contents|Aggregated|Synthesized|Child Sources)\b", body):
            report.error("meta_object_aggregation_heading",
                         "node_kind=object meta carries an aggregation heading "
                         "(Contents/Aggregated/Synthesized/Child Sources) — objects are pointers, "
                         "not containers (CR-023 DP5/INV-3)",
                         path=rel)
        if "wiki_sources/objects" in text:
            report.error("meta_object_store_ref",
                         "node_kind=object meta references a wiki_sources/objects/ store — the "
                         "retired Knowledge-Object store is forbidden (CR-023 INV-1/INV-3)",
                         path=rel)
    # ──────────────────────────────────────────────────────────────────────────

    if _looks_raw_non_text(artifact_locator):
        report.warn("meta_artifact_raw_non_text",
                    "artifact_locator appears to point to raw/non-text file; runtime artifact_locator should point to AIWS-readable representation",
                    path=rel)
    # DESIGN-04: flag absolute paths — meta files should store project-relative paths
    if artifact_locator and (
        (len(artifact_locator) >= 2 and artifact_locator[1] == ":")
        or artifact_locator.startswith("/")
    ):
        report.error("meta_absolute_locator",
                     "artifact_locator contains an absolute path; use a project-relative path for portability",
                     path=rel)
    # CR-AIWS-2026-05-007: orphan doctor check — meta points to a nonexistent artifact.
    # Complements the index→meta stale check (build_wiki_source_index.py). Warn-level so
    # intentional external/remote placeholders don't break CI.
    _orphan_artifact_check(path, artifact_locator, report, rel)
    if original_locator and not representation_locator:
        report.warn("meta_missing_representation_locator",
                    "original_source_locator exists but representation_locator is missing",
                    path=rel)
    if representation_locator and not _looks_aiws_readable(representation_locator):
        report.warn("meta_representation_locator_not_text",
                    "representation_locator does not appear to be markdown/text/structured AI-readable format",
                    path=rel)

    rep_status = meta.get("source_representation_status")
    if rep_status and rep_status not in SOURCE_REPRESENTATION_STATUS_ENUM:
        report.warn("meta_representation_status",
                    f"unknown source_representation_status: {rep_status}",
                    path=rel)
    if rep_status in {"partial", "needs_review", "failed"} and not meta.get("source_representation_caution"):
        report.warn("meta_representation_caution",
                    "source representation status requires caution text",
                    path=rel)
    if meta.get("source_representation_quality_issue") is True and not (
        meta.get("source_representation_caution") or meta.get("review_required")
    ):
        report.warn("meta_representation_issue",
                    "source_representation_quality_issue=true should include caution/review_required",
                    path=rel)

    promotion = meta.get("promotion_status")
    if promotion and promotion not in PROMOTION_STATUS_ENUM:
        report.warn("meta_promotion_status",
                    f"unknown promotion_status: {promotion}",
                    path=rel)
    if promotion == "approved" and not (
        meta.get("review_status") or meta.get("last_reviewed_at") or meta.get("change_summary")
    ):
        report.warn("meta_promotion_trace",
                    "promotion_status=approved should have review trace/change summary",
                    path=rel)

    if meta.get("review_required") is True and not (
        meta.get("next_action") or meta.get("source_representation_caution") or meta.get("review_status")
    ):
        report.warn("meta_review_required",
                    "review_required=true should have next_action/caution/review_status",
                    path=rel)

    if meta.get("maintenance_status") in {"needs_review", "stale"}:
        report.warn("meta_maintenance_status",
                    f"maintenance_status indicates review: {meta.get('maintenance_status')}",
                    path=rel)

    if len(text) > 8_000:
        report.warn("meta_heavy",
                    f"source meta is large ({len(text)} bytes) — may be too heavy",
                    path=rel)

    # CR-AIWS-2026-06-020: flag stray tool-call/markup artifacts in the meta body.
    # Raw line-walk (NOT extract_sections, which folds the tail into the last section and
    # hides the junk). WARN-level so the sec_lint_negative error-only/rc==2 contract is
    # preserved; surfaced by --strict.
    for ln in body.splitlines():
        if _TRAILING_JUNK_RE.search(ln):
            report.warn("meta_trailing_junk",
                        f"stray tool-call/markup artifact in meta body: {ln.strip()[:60]!r}",
                        path=rel)
            break

    # CR-AIWS-2026-06-017: optional `system` scope axis. NOT required (absent = common).
    # When the project is multi_system, a non-empty `system` must be a declared project system.
    ai_work_dir = next((par for par in path.parents if par.name == ".ai-work"), None)
    if ai_work_dir is not None:
        ms, systems = _ms_config(str(ai_work_dir))
        sysval = str(meta.get("system", "")).strip()
        if ms and sysval and systems and sysval not in systems:
            report.warn("meta_system",
                        f"system {sysval!r} not in project systems {sorted(systems)} "
                        f"(project_profile.yml)", path=rel)


def _lint_source_index(path: Path, report: LintReport) -> None:
    rel = str(path)
    try:
        records = read_jsonl(path)
    except ValueError as e:
        report.error("index_parse", str(e), path=rel)
        return
    seen_ids: set[str] = set()
    for idx, rec in enumerate(records, start=1):
        loc = f"line {idx}"
        # Binary-by-design stubs (CR-066): index projects not_meta_applicable:true; exempt the
        # text-meta fields such stubs intentionally lack.
        idx_exempt = ({"profile_id", "summary_short", "knowledge_targets"}
                      if rec.get("not_meta_applicable") is True else set())
        for k in INDEX_REQUIRED:
            if k in idx_exempt:
                continue
            if k not in rec or rec[k] in (None, "", []):
                report.error("index_field", f"missing field: {k}", path=rel, loc=loc)
        sid = rec.get("source_id")
        if sid and sid in seen_ids:
            report.error("index_dup", f"duplicate source_id: {sid}", path=rel, loc=loc)
        if sid:
            seen_ids.add(sid)
        if "meta_locator" not in rec and "meta_id" not in rec:
            report.error("index_no_meta_ref",
                         "entry has neither meta_locator nor meta_id", path=rel, loc=loc)
        if not rec.get("lookup_keys"):
            report.warn("index_weak_lookup",
                        "entry has no lookup_keys surface", path=rel, loc=loc)
        for k in ("authority_level", "freshness_status", "source_representation_status", "promotion_status"):
            if k not in rec:
                report.info("index_wta_field",
                            f"recommended WTA projection field missing: {k}",
                            path=rel, loc=loc)

        rep_status = rec.get("source_representation_status")
        if rep_status and rep_status not in SOURCE_REPRESENTATION_STATUS_ENUM:
            report.warn("index_representation_status",
                        f"unknown source_representation_status: {rep_status}",
                        path=rel, loc=loc)

        promotion = rec.get("promotion_status")
        if promotion and promotion not in PROMOTION_STATUS_ENUM:
            report.warn("index_promotion_status",
                        f"unknown promotion_status: {promotion}",
                        path=rel, loc=loc)

        recommendation = rec.get("recommendation")
        if recommendation and recommendation in UNSAFE_RECOMMENDATIONS:
            report.error("index_unsafe_recommendation",
                         f"unsafe recommendation: {recommendation}",
                         path=rel, loc=loc)

        summary = rec.get("summary_short") or ""
        if len(summary) > 500:
            report.warn("index_heavy_summary",
                        f"summary_short too long ({len(summary)} chars)",
                        path=rel, loc=loc)
        # projection guard: index entry should not embed fat bodies
        for fat_key in ("full_meta", "body", "raw", "full_source", "source_body", "meta_body"):
            if fat_key in rec:
                report.error("index_projection",
                             f"entry contains fat field '{fat_key}' (violates projection rule)",
                             path=rel, loc=loc)



def _lint_maintenance_log(path: Path, report: LintReport) -> None:
    rel = str(path)
    # Per-line tolerant parse (IR-09): a single corrupt line must record one
    # parse error but must NOT suppress checks on every other record / mask
    # aggregate counts. Mirrors read_jsonl's BOM + null handling.
    records: list[dict] = []
    if path.exists():
        for i, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            raw = raw.strip().strip("\x00")
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError as e:
                report.error("maintenance_log_parse", f"line {i}: {e}",
                             path=rel, loc=f"line {i}")

    seen: set[str] = set()
    for idx, rec in enumerate(records, start=1):
        loc = f"line {idx}"
        for k in WSM_REQUIRED_LOG_FIELDS:
            if k not in rec or rec[k] in (None, "", []):
                report.warn("maintenance_log_field",
                            f"maintenance log missing field: {k}",
                            path=rel, loc=loc)
        log_id = rec.get("log_id")
        if log_id and log_id in seen:
            report.error("maintenance_log_dup",
                         f"duplicate maintenance log_id: {log_id}",
                         path=rel, loc=loc)
        if log_id:
            seen.add(log_id)

        action = rec.get("action")
        if action and action not in WSM_ACTION_ENUM:
            report.info("maintenance_log_action",
                        f"unknown maintenance action: {action}",
                        path=rel, loc=loc)

        recommendation = rec.get("recommendation")
        if recommendation and recommendation in UNSAFE_RECOMMENDATIONS:
            report.error("maintenance_log_unsafe_recommendation",
                         f"unsafe recommendation: {recommendation}",
                         path=rel, loc=loc)

        if action in {"meta_applied", "index_rebuilt"} and not rec.get("rollback_hint"):
            report.warn("maintenance_log_rollback",
                        "applied/rebuild action should have rollback_hint",
                        path=rel, loc=loc)


def _lint_relations(path: Path, index_path: Path, meta_dir: Path, report: LintReport) -> None:
    """Lint the relations.jsonl projection (CR-AIWS-2026-05-022).

    Warn-not-error, skip-if-absent: relations.jsonl is an OPTIONAL projection.
    Checks: malformed edge (missing core fields), broken target/source ref (not
    resolvable in the index), unknown BARE relationship_type, and a staleness
    rebuild HINT (a non-empty projection older than the newest meta). All findings
    are warnings (never errors) except a hard parse failure. Object-scoped lints
    (non-aggregation, degenerate-summary→error, etc.) are DEFERRED to CR-023.
    """
    rel = str(path)
    if not path.exists():
        return
    try:
        edges = read_jsonl(path)
    except ValueError as e:
        report.error("relations_parse", str(e), path=rel)
        return

    try:
        known_ids = {r.get("source_id", "") for r in read_jsonl(index_path)} if index_path.exists() else set()
    except ValueError:
        known_ids = set()

    try:
        import build_relations as _br
        known_types, ext_prefix = _br.KNOWN_RELATION_TYPES, _br.EXTENSION_PREFIX
    except Exception:  # noqa: BLE001
        known_types, ext_prefix = set(), "x:"

    for i, e in enumerate(edges, start=1):
        loc = f"line {i}"
        for k in ("relationship_type", "source_ref", "target_ref"):
            if not e.get(k):
                report.warn("relations_field", f"edge missing field: {k}", path=rel, loc=loc)
        src, tgt, rtype = e.get("source_ref", ""), e.get("target_ref", ""), e.get("relationship_type", "")
        if known_ids:
            if tgt and tgt not in known_ids:
                report.warn("relations_broken_ref",
                            f"target_ref not in index: {src} --{rtype}--> {tgt}", path=rel, loc=loc)
            if src and src not in known_ids:
                report.warn("relations_orphan_source",
                            f"source_ref not in index: {src}", path=rel, loc=loc)
        if rtype and not (rtype.startswith(ext_prefix) or rtype in known_types):
            report.warn("relations_unknown_type",
                        f"unknown relationship_type '{rtype}' (promote via CR or namespace as x:)",
                        path=rel, loc=loc)

    # staleness HINT: a non-empty projection older than the newest meta → rebuild
    if edges and meta_dir.is_dir():
        try:
            newest_meta = max((f.stat().st_mtime for f in meta_dir.rglob("*.md")), default=0.0)
            if path.stat().st_mtime < newest_meta:
                report.warn("relations_stale",
                            "relations.jsonl is older than the newest meta — rebuild with build_relations.py",
                            path=rel)
        except OSError:
            pass


def _lint_object_node_invariants(ai_work: Path, report: LintReport) -> None:
    """Repo-structure anti-KO guards for the two-kind node model (CR-AIWS-2026-05-023).

    ERROR-grade CI guards so a node_kind=object meta can never drift back into the retired
    3-layer Knowledge-Object record:
      INV-8: hand-authored only — no _pending_object_refresh.jsonl refresh queue, and
             build_relations.py must not write into wiki_sources/meta/.
      INV-8: no functional build-/refresh-knowledge-object skill — any such SKILL.md must stay a
             retired tombstone (status: retired, not user-invocable) in every skill tree.
      INV-1: one store / no separate object store (wiki_sources/objects/).

    The INV-8 "no build/refresh-knowledge-object skill" clause was deferred by AIP-049 to ship
    WITH the skill removal (the skills were CR-gated — CAP-049-01). It landed in AIP-055 (CR-035
    Change 10) AFTER the Change-9 tombstones, so CI does not go red on a pre-existing leak.

    Called from this module's main() AND from lint_all.main() (the CI driver), mirroring
    _check_duplicate_artifact_ids — so the guard runs in every full lint.
    """
    wiki_sources = ai_work / "wiki_sources"

    # INV-1 — one store / one index: no separate Knowledge-Object store. wiki_sources/objects/
    # was the retired Layer-2 store (CR-005/CR-020 removed the layer; this is the remaining
    # CR-022 cleanup CI assertion). Object metas live in wiki_sources/meta/ like any artifact.
    objects_dir = wiki_sources / "objects"
    if objects_dir.exists():
        report.error("object_store_present",
                     "wiki_sources/objects/ exists — the retired Knowledge-Object store is "
                     "forbidden; object metas live in wiki_sources/meta/ (CR-023 INV-1)",
                     path=str(objects_dir))

    # INV-8 — no tool-driven object refresh queue (the retired KO had one).
    for q in (wiki_sources / "_pending_object_refresh.jsonl",
              ai_work / "_pending_object_refresh.jsonl"):
        if q.exists():
            report.error("object_refresh_queue_present",
                         "_pending_object_refresh.jsonl exists — objects are hand-authored only; "
                         "no tool refresh queue (CR-023 INV-8)",
                         path=str(q))

    # INV-8 — build_relations.py must only project relations.jsonl, never write object metas
    # into wiki_sources/meta/. Heuristic source guard: flag a write_jsonl/write_text call whose
    # argument list mentions a meta path (build_relations legitimately READS meta_dir, but must
    # never WRITE there).
    br_path = Path(__file__).resolve().parent / "build_relations.py"
    if br_path.exists():
        try:
            br_src = read_text(br_path)
        except OSError:
            br_src = ""
        if re.search(r"write_(?:jsonl|text)\s*\([^)]*\bmeta\b", br_src):
            report.error("build_relations_writes_meta",
                         "build_relations.py appears to write into a meta path — it must only "
                         "project relations.jsonl; object metas are hand-authored (CR-023 INV-8)",
                         path=str(br_path))

    # INV-8 — no functional KO skill may reappear in any skill tree (CR-035 Change 10, deferred
    # from AIP-049). A build-/refresh-knowledge-object SKILL.md is allowed ONLY as a retired
    # tombstone: status: retired AND not user-invocable. Tombstone-safe (the Change-9 tombstones
    # keep status: retired). Scans all 4 live skill trees (2 FULL canonical + 2 short-pointer).
    root = ai_work.parent
    skill_trees = (
        ai_work / "procedural" / "skills",
        root / "product" / "procedural" / "skills",
        root / ".claude" / "skills",
        root / "product" / "skills",
    )
    for tree in skill_trees:
        for ko_name in ("build-knowledge-object", "refresh-knowledge-object"):
            sk = tree / ko_name / "SKILL.md"
            if not sk.exists():
                continue
            try:
                fm, _ = parse_frontmatter(read_text(sk))
            except OSError:
                continue
            status = str(fm.get("status", "")).strip().strip("\"'").lower()
            inv = fm.get("user-invocable")
            inv_true = (inv is True) or (str(inv).strip().strip("\"'").lower() == "true")
            if status != "retired" or inv_true:
                report.error("ko_skill_reappeared",
                             f"{ko_name} SKILL.md must be a retired tombstone (status: retired, "
                             "not user-invocable) — a functional Knowledge-Object skill must not "
                             "reappear; objects are hand-authored via node_kind=object "
                             "(CR-023 INV-8 / CR-035 Change 9)",
                             path=str(sk))


def _lint_object_golden_fixtures(ai_work: Path, report: LintReport) -> None:
    """Assert golden source-meta fixtures stay lint-clean (regression guard).

    Lints each fixture meta in the golden dirs below into a throwaway report; if any produces an
    ERROR, surface ONE error here so a future propagation gap (e.g. the profile_id requirement,
    the object-kind whitelist, or an enum regressing) fails CI. Called from this module's main()
    AND lint_all.main(), mirroring _lint_object_node_invariants.

      • tooling/fixtures/object_nodes/          object-node golden fixture (CR-AIWS-2026-06-004 C5)
      • tests/fixtures/wiki_corpus/metas_good/  wiki regression-suite spec-correct corpus metas
        (test_wiki_regression.py — consolidated to .ai-work/tests/ 2026-06-20). metas_broken/ is
        deliberately NOT scanned — those must fail. Both dirs are skipped if absent (slim install).
    """
    golden_dirs = (
        ai_work / "tooling" / "fixtures" / "object_nodes",
        ai_work / "tests" / "fixtures" / "wiki_corpus" / "metas_good",
    )
    for fixtures_dir in golden_dirs:
        if not fixtures_dir.is_dir():
            continue
        for fx in sorted(fixtures_dir.glob("*.md")):
            sub = LintReport(target=str(fx))
            try:
                _lint_source_meta(fx, sub)
            except Exception as exc:  # noqa: BLE001
                report.error("object_fixture_lint_crash",
                             f"golden fixture {fx.name} raised {exc!r} during lint "
                             "(CR-AIWS-2026-06-004 C5)", path=str(fx))
                continue
            codes = sorted({f.code for f in sub.findings if f.severity == SEV_ERROR})
            if codes:
                report.error("object_fixture_regressed",
                             f"golden fixture {fx.name} no longer lints clean "
                             f"(errors: {', '.join(codes)}) — a spec-correct meta must stay "
                             "lint-clean (CR-AIWS-2026-06-004 C5)", path=str(fx))


def _lint_build_routing(path: Path, ai_work: Path, report: LintReport) -> None:
    """Validate the Source Build Routing registry `_build_routing.json` (CR-AIWS-2026-05-019 Stage 2).

    Absence is valid (handled by the caller). Checks: JSON parses; default_route present; each route has
    required keys (tool, args); tool path resolves on disk (WARN); args use only known placeholders (WARN);
    refresh_mode known; profile_id (if set) resolves to a profiles/<id>.yml back-reference (WARN).
    """
    rel = str(path)
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as e:  # noqa: BLE001
        report.error("build_routing_json", f"_build_routing.json is not valid JSON: {e}", path=rel)
        return
    if not isinstance(data, dict):
        report.error("build_routing_shape", "_build_routing.json must be a JSON object", path=rel)
        return
    if not data.get("default_route"):
        report.warn("build_routing_default", "missing default_route (expected e.g. 'generic')", path=rel)
    routes = data.get("routes", {})
    if not isinstance(routes, dict):
        report.error("build_routing_routes", "'routes' must be an object", path=rel)
        return
    project_root = ai_work.parent
    profiles_dir = ai_work / "wiki_sources" / "profiles"
    for st, route in routes.items():
        if not isinstance(route, dict):
            report.error("build_routing_route", f"route '{st}' must be an object", path=rel)
            continue
        for k in ("tool", "args"):
            if k not in route:
                report.error("build_routing_field", f"route '{st}' missing required key '{k}'", path=rel)
        tool = route.get("tool", "")
        if tool and not resolve_locator(tool, project_root).exists():
            report.warn("build_routing_tool_missing",
                        f"route '{st}' tool not on disk: {resolve_locator(tool, project_root)}", path=rel)
        args = route.get("args", [])
        if not isinstance(args, list):
            report.error("build_routing_args", f"route '{st}' args must be a list", path=rel)
        else:
            bad: set[str] = set()
            for a in args:
                bad.update(re.findall(r"\{(\w+)\}", str(a)))
            bad -= _BUILD_ROUTING_PLACEHOLDERS
            if bad:
                report.warn("build_routing_placeholder",
                            f"route '{st}' uses unknown placeholders {sorted(bad)} "
                            f"(known: {sorted(_BUILD_ROUTING_PLACEHOLDERS)})", path=rel)
        rmode = route.get("refresh_mode", "")
        if rmode and rmode not in _BUILD_ROUTING_REFRESH_MODES:
            report.warn("build_routing_refresh_mode",
                        f"route '{st}' unknown refresh_mode '{rmode}' "
                        f"(known: {sorted(_BUILD_ROUTING_REFRESH_MODES)})", path=rel)
        pid = route.get("profile_id", "")
        if pid and not (profiles_dir / f"{pid}.yml").exists():
            report.warn("build_routing_profile",
                        f"route '{st}' profile_id '{pid}' has no profiles/{pid}.yml back-reference", path=rel)


def main() -> int:
    p = argparse.ArgumentParser(description="Lint wiki + wiki sources")
    p.add_argument("--path",
                   help="Override path to scan; default = <ai-work>/wiki + wiki_sources")
    p.add_argument("--paths", nargs="+", metavar="GLOB_OR_FILE",
                   help="Restrict meta lint to specific files or glob patterns (e.g. 'meta/SRC-*.md'). "
                        "Applied relative to <ai-work>/wiki_sources/meta/. Use to scope batch results.")
    p.add_argument("--entries-only", action="store_true")
    p.add_argument("--sources-only", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--show-accepted", action="store_true",
                   help="list lint_accept-muted findings instead of just tallying them")
    ns = p.parse_args()

    start = Path(ns.path).resolve() if ns.path else Path.cwd()
    try:
        ai_work = find_ai_work_root(start) / ".ai-work"
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2

    report = LintReport(target=str(ai_work))

    if not ns.sources_only:
        wiki_root = ai_work / "wiki"
        if wiki_root.is_dir():
            for f in sorted(wiki_root.rglob("*.md")):
                if f.name.lower() == "readme.md":
                    continue
                _lint_wiki_entry(f, report)

    if not ns.entries_only:
        meta_root = ai_work / "wiki_sources" / "meta"
        if meta_root.is_dir():
            if ns.paths:
                import glob as _glob
                meta_files: list[Path] = []
                for pat in ns.paths:
                    base = meta_root if not Path(pat).is_absolute() else Path(".")
                    matched = [Path(p) for p in _glob.glob(str(base / pat), recursive=True)]
                    if not matched:
                        # try direct stem match
                        direct = meta_root / pat if not pat.endswith(".md") else meta_root / pat
                        if direct.exists():
                            matched = [direct]
                    meta_files.extend(matched)
                meta_files = sorted(set(meta_files))
            else:
                meta_files = sorted(meta_root.rglob("*.md"))
            for f in meta_files:
                _lint_source_meta(f, report)
        for idx_name in ("index.jsonl", "index.local.jsonl"):
            index_path = ai_work / "wiki_sources" / idx_name
            if index_path.exists():
                _lint_source_index(index_path, report)
        for rel_name in ("relations.jsonl", "relations.local.jsonl"):
            rel_path = ai_work / "wiki_sources" / rel_name
            if rel_path.exists():
                idx_for = ai_work / "wiki_sources" / ("index.local.jsonl" if "local" in rel_name else "index.jsonl")
                _lint_relations(rel_path, idx_for, ai_work / "wiki_sources" / "meta", report)
        maintenance_log = ai_work / "wiki_sources" / "maintenance_log.jsonl"
        if maintenance_log.exists():
            _lint_maintenance_log(maintenance_log, report)
        build_routing = ai_work / "wiki_sources" / "_build_routing.json"
        if build_routing.exists():
            _lint_build_routing(build_routing, ai_work, report)
        # Repo-structure anti-KO guards (two-kind node model, CR-023 INV-1/INV-8)
        _lint_object_node_invariants(ai_work, report)
        # Object-node golden-fixture regression guard (CR-AIWS-2026-06-004 C5)
        _lint_object_golden_fixtures(ai_work, report)

    apply_lint_accept(report, ai_work)
    return emit_report(report, ns.format, ns.strict, ns.show_accepted)


if __name__ == "__main__":
    raise SystemExit(main())
