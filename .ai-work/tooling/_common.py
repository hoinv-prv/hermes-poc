"""Shared helpers for AI Work System MVP tooling.

Deterministic, zero-dependency utilities: YAML frontmatter parsing,
Markdown section extraction, JSONL helpers, lint result formatting.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

# Force UTF-8 stdout/stderr so non-ASCII (— etc.) works on Windows cp932.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------- YAML frontmatter (minimal) ----------

def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-ish frontmatter. Supports scalars, lists (block + flow).

    Returns (meta, body). If no frontmatter, returns ({}, text).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    return _parse_yaml_block(raw), body


def _parse_yaml_block(raw: str) -> dict[str, Any]:
    meta, _ = _parse_yaml_mapping(raw.splitlines(), 0, -1)
    return meta


def _coerce_scalar(val: str):
    """Coerce a frontmatter/profile scalar. Quoted -> literal string. Unquoted
    true/false -> bool; null/~ -> None; everything else stays a string (NO int
    coercion — version strings, ids, dates, paths stay as-is). CR-AIWS-2026-06-043
    Change B: booleans MUST coerce so a profile's `emit_scaffold: false` is bool False
    (not the truthy string 'false') and is honored by gates."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    low = val.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    return val.strip('"').strip("'")


def _strip_inline_comment(raw_val: str) -> str:
    """Strip a YAML inline comment (' #…' — a '#' preceded by whitespace) from an UNQUOTED
    value and return it stripped. A '#' with NO preceding whitespace (regex 'BD#\\d+', hex
    '#fff', a fragment 'a#b') is not a comment and is left intact. Callers MUST skip quoted
    values (a '#' inside quotes is literal). CR-AIWS-2026-06-058 (IR-C)."""
    h = 1
    while True:
        h = raw_val.find("#", h)
        if h < 1:
            break
        if raw_val[h - 1] in (" ", "\t"):
            return raw_val[:h].strip()
        h += 1
    return raw_val.strip()


def _parse_block_mapping_list(lines: list[str], start: int,
                              item_indent: int) -> tuple[list[dict], int]:
    """Parse a YAML block list whose items are mappings (CR-AIWS-2026-06-065):
        - key: val
          key2: val2
        - key: val3
    Returns (list_of_dicts, next_line_index). The dash line may carry the first
    'key: val'; deeper-indented 'key: val' lines extend the current item. A dedent
    (indent < item_indent) ends the list. Quoted values + a '#' with no preceding
    space are kept intact (mirrors the scalar parser)."""
    out: list[dict] = []
    cur: "dict | None" = None
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent < item_indent:
            break
        s = line.lstrip()
        if s.startswith("- "):
            if cur is not None:
                out.append(cur)
            cur = {}
            rest = s[2:].strip()
            if ":" in rest:
                k, _, raw = rest.partition(":")
                v = raw.strip()
                v = v if v[:1] in ('"', "'") else _strip_inline_comment(raw)
                cur[k.strip()] = _coerce_scalar(v)
            i += 1
        elif cur is not None and indent > item_indent and ":" in s:
            k, _, raw = s.partition(":")
            v = raw.strip()
            v = v if v[:1] in ('"', "'") else _strip_inline_comment(raw)
            cur[k.strip()] = _coerce_scalar(v)
            i += 1
        else:
            break
    if cur is not None:
        out.append(cur)
    return out, i


def _parse_yaml_mapping(lines: list[str], start: int,
                        parent_indent: int) -> tuple[dict[str, Any], int]:
    """Parse an indented YAML-ish mapping: scalars, flow lists, block lists, and
    NESTED mappings. Unquoted booleans/null coerce (true/false -> bool, null/~ -> None;
    see _coerce_scalar, CR-AIWS-2026-06-043 Change B); other scalars stay strings (no
    int coercion). Returns (dict, next_line_index)."""
    result: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if parent_indent >= 0 and indent <= parent_indent:
            break
        if ":" not in line:
            i += 1
            continue
        key, _, raw_val = line.partition(":")
        key = key.strip()
        val = raw_val.strip()
        # IR-C (CR-AIWS-2026-06-058): drop a YAML inline comment (' #…') from an UNQUOTED value
        # so 'systems:  # note' before a block list reads as an empty value, and 'scalar  # note'
        # coerces from the scalar. Quoted values + a '#' with no preceding space are left intact.
        if val[:1] not in ('"', "'"):
            val = _strip_inline_comment(raw_val)
        if val == "":
            # Look ahead: nested mapping, block list, or empty value.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            child_indent = (len(lines[j]) - len(lines[j].lstrip())) if j < len(lines) else -1
            if j >= len(lines) or child_indent <= indent:
                result[key] = []                      # empty value (backward-compatible)
                i = j
            elif lines[j].lstrip().startswith("- "):
                first_rest = lines[j].lstrip()[2:].strip()
                # mapping-style item: 'key: value' after the dash (':' followed by space/eol)
                is_mapping = bool(re.match(r"[^:\s][^:]*:(\s|$)", first_rest))
                if is_mapping:
                    result[key], i = _parse_block_mapping_list(lines, j, child_indent)
                else:
                    items: list[str] = []                 # block list (scalars)
                    k = j
                    while k < len(lines):
                        l2 = lines[k]
                        if not l2.strip():
                            k += 1
                            continue
                        if (len(l2) - len(l2.lstrip())) < child_indent:
                            break
                        s2 = l2.lstrip()
                        if s2.startswith("- "):
                            items.append(s2[2:].strip().strip('"').strip("'"))
                            k += 1
                        else:
                            break
                    result[key] = items
                    i = k
            else:
                nested, i = _parse_yaml_mapping(lines, j, indent)   # nested mapping
                result[key] = nested
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            result[key] = [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()]
            i += 1
        else:
            result[key] = _coerce_scalar(val)
            i += 1
    return result, i


def dump_frontmatter(meta: dict[str, Any]) -> str:
    """Serialize meta back to minimal YAML-ish frontmatter."""
    out: list[str] = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            if not v:
                out.append(f"{k}: []")
            else:
                out.append(f"{k}:")
                for item in v:
                    out.append(f"  - {item}")
        else:
            out.append(f"{k}: {v}")
    out.append("---")
    return "\n".join(out) + "\n"


def strip_lint_accept(meta: dict[str, Any]) -> dict[str, Any]:
    """Remove the lint_accept block so an accept never survives a content rewrite
    (strip-on-refresh reset, CR-AIWS-2026-06-065). Mutates and returns meta."""
    meta.pop("lint_accept", None)
    return meta


# ---------- Markdown section extraction ----------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def extract_sections(body: str) -> dict[str, str]:
    """Map heading text -> section body (any level). Later duplicates overwrite."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = HEADING_RE.match(line)
        if m:
            if current_key is not None:
                sections[current_key] = "\n".join(buf).strip()
            current_key = m.group(2).strip()
            buf = []
        else:
            if current_key is not None:
                buf.append(line)
    if current_key is not None:
        sections[current_key] = "\n".join(buf).strip()
    return sections


def has_section(body: str, name: str) -> bool:
    n = name.strip().lower()
    for line in body.splitlines():
        m = HEADING_RE.match(line)
        if m and m.group(2).strip().lower() == n:
            return True
    return False


# ---------- Step parsing for AIP ----------

STEP_HEADING_RE = re.compile(r"^#{2,4}\s+Step:\s*(STEP-[A-Za-z0-9_-]+)\s*—\s*(.+?)\s*$")


def parse_aip_steps(body: str) -> list[dict[str, str]]:
    """Parse 'Step: STEP-xx — title' blocks with simple 'Field:' lines.

    Recognises: Objective, Recommended Mode, Applicable Guidelines,
    Recommended Skills, Inputs, Expected Outputs, Done Condition,
    Notes / Constraints, Workspace Actions, Step Dependencies, Review Note,
    Step Output / Execution Artifact.
    """
    fields = [
        "Objective", "Recommended Mode", "Applicable Guidelines",
        "Recommended Skills", "Inputs", "Expected Outputs", "Done Condition",
        "Notes / Constraints", "Workspace Actions", "Step Dependencies",
        "Review Note", "Step Output / Execution Artifact",
    ]
    field_re = re.compile(r"^(" + "|".join(re.escape(f) for f in fields) + r")\s*:\s*$")

    steps: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_field: str | None = None
    buf: list[str] = []
    in_fence = False  # inside a fenced code block (``` ... ```)

    def flush_field() -> None:
        nonlocal current_field, buf
        if current is not None and current_field is not None:
            current[current_field] = "\n".join(buf).strip()
        current_field = None
        buf = []

    def flush_step() -> None:
        nonlocal current
        flush_field()
        if current is not None:
            steps.append(current)
        current = None

    for line in body.splitlines():
        # Toggle fence state on ``` lines; collect as content but skip structural parsing
        if line.startswith("```"):
            in_fence = not in_fence
            if current_field is not None:
                buf.append(line)
            continue
        if in_fence:
            if current_field is not None:
                buf.append(line)
            continue

        sm = STEP_HEADING_RE.match(line)
        if sm:
            flush_step()
            current = {"step_id": sm.group(1), "title": sm.group(2)}
            continue
        if current is None:
            continue
        # New top-level H2 heading (not a Step: heading) ends the current step
        if HEADING_RE.match(line) and line.startswith("## ") and not line.lstrip("#").strip().startswith("Step:"):
            flush_step()
            continue
        fm = field_re.match(line)
        if fm:
            flush_field()
            current_field = fm.group(1)
            continue
        if current_field is not None:
            buf.append(line)
    flush_step()
    return steps


# ---------- JSONL ----------

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        raw = raw.strip().strip('\x00')
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: invalid JSON on line {i}: {e}") from e
    return out


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


# ---------- Wiki Source maintenance-log writer (CR-AIWS-2026-05-006) ----------

# Single source of truth for required maintenance-log fields. lint_wiki imports
# this instead of keeping its own copy, so the writer and the linter cannot drift.
WSM_REQUIRED_LOG_FIELDS = [
    "log_id", "timestamp", "action", "source_id", "target_artifact",
    "change_summary", "review_decision", "rollback_hint",
]


def append_maintenance_log(log_path: Path, entry: dict[str, Any]) -> None:
    """Append one WSM maintenance entry, schema-checked and newline-safe.

    Used by every tool/skill that writes maintenance_log.jsonl so the schema and
    newline framing cannot drift between writers (CR-AIWS-2026-05-006, IR-07/08).

    - Raises ValueError if any WSM_REQUIRED_LOG_FIELDS is missing/empty.
    - Heals a prior missing trailing newline before appending (fixes IR-08:
      two JSON objects concatenated onto one physical line).
    - Writes exactly one record followed by a single newline.
    """
    missing = [k for k in WSM_REQUIRED_LOG_FIELDS if entry.get(k) in (None, "", [])]
    if missing:
        raise ValueError(f"maintenance_log entry missing required fields: {missing}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        data = log_path.read_bytes()
        if data and not data.endswith(b"\n"):
            with log_path.open("ab") as f:
                f.write(b"\n")  # heal a prior append that omitted its newline
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------- Lint result model ----------

SEV_ERROR = "error"
SEV_WARNING = "warning"
SEV_INFO = "info"

# ---------- Inline lint_accept (CR-AIWS-2026-06-065) ----------
# Self-guard codes generated by apply_lint_accept itself — never acceptable.
LINT_ACCEPT_SELF_CODES = {"lint_accept_malformed", "lint_accept_unused"}
# Required fields on every lint_accept entry (governance audit trail).
LINT_ACCEPT_REQUIRED = ("code", "reason", "accepted_by")
# In-scope dirs (relative to .ai-work) for inline lint_accept; AIP_ROOT handled explicitly.
LINT_ACCEPT_SCOPE_DIRS = ("wiki_sources/meta", "wiki", "aip")


@dataclass
class LintFinding:
    severity: str
    code: str
    message: str
    path: str = ""
    location: str = ""


@dataclass
class AcceptedFinding:
    """A finding muted by an inline lint_accept entry (CR-AIWS-2026-06-065)."""
    finding: LintFinding
    reason: str
    accepted_by: str


@dataclass
class LintReport:
    target: str
    findings: list[LintFinding] = field(default_factory=list)
    accepted: list[AcceptedFinding] = field(default_factory=list)

    def error(self, code: str, msg: str, path: str = "", loc: str = "") -> None:
        self.findings.append(LintFinding(SEV_ERROR, code, msg, path, loc))

    def warn(self, code: str, msg: str, path: str = "", loc: str = "") -> None:
        self.findings.append(LintFinding(SEV_WARNING, code, msg, path, loc))

    def info(self, code: str, msg: str, path: str = "", loc: str = "") -> None:
        self.findings.append(LintFinding(SEV_INFO, code, msg, path, loc))

    def counts(self) -> dict[str, int]:
        c = {SEV_ERROR: 0, SEV_WARNING: 0, SEV_INFO: 0}
        for f in self.findings:
            c[f.severity] = c.get(f.severity, 0) + 1
        c["accepted"] = len(self.accepted)
        return c

    def exit_code(self, strict: bool) -> int:
        c = self.counts()
        if c[SEV_ERROR] > 0:
            return 2
        if strict and c[SEV_WARNING] > 0:
            return 1
        return 0


def _is_lint_accept_scope(path: Path, ai_work: Path) -> bool:
    """True if path is a frontmatter-bearing file eligible for inline lint_accept
    (CR-AIWS-2026-06-065): an .md under wiki_sources/meta/, wiki/, aip/, or AIP_ROOT.md."""
    try:
        if path.suffix.lower() != ".md" or not path.is_file():
            return False
        if path.resolve() == (ai_work / "truth" / "AIP_ROOT.md").resolve():
            return True
        rel = path.resolve().relative_to(ai_work.resolve()).as_posix()
    except (ValueError, OSError):
        return False
    return any(rel == d or rel.startswith(d + "/") for d in LINT_ACCEPT_SCOPE_DIRS)


def apply_lint_accept(report: LintReport, ai_work: Path) -> None:
    """Post-pass: honor inline `lint_accept` frontmatter on in-scope files.
    Moves accepted findings from report.findings to report.accepted; appends
    lint_accept_malformed (ERROR) / lint_accept_unused (WARNING) findings.
    Self-guard codes can never be accepted. (CR-AIWS-2026-06-065)"""
    by_path: dict[str, list[LintFinding]] = {}
    for f in report.findings:
        if f.path:
            by_path.setdefault(f.path, []).append(f)

    accepts: dict[str, list[dict]] = {}
    malformed: dict[str, list[str]] = {}
    for p in by_path:
        path = Path(p)
        if not _is_lint_accept_scope(path, ai_work):
            continue
        try:
            meta, _ = parse_frontmatter(read_text(path))
        except OSError:
            continue
        raw = meta.get("lint_accept")
        if not raw:
            continue
        entries: list[dict] = []
        msgs: list[str] = []
        if not isinstance(raw, list):
            msgs.append("lint_accept must be a list of mappings")
        else:
            for e in raw:
                if not isinstance(e, dict):
                    msgs.append(f"entry is not a mapping: {e!r}")
                    continue
                miss = [k for k in LINT_ACCEPT_REQUIRED if not str(e.get(k, "")).strip()]
                if miss:
                    msgs.append(f"entry missing {miss} (code={e.get('code')!r})")
                    continue
                if e["code"] in LINT_ACCEPT_SELF_CODES:
                    msgs.append(f"cannot accept self-guard code {e['code']}")
                    continue
                entries.append(e)
        accepts[p] = entries
        if msgs:
            malformed[p] = msgs

    active: list[LintFinding] = []
    for f in report.findings:
        entry = next((e for e in accepts.get(f.path, []) if e["code"] == f.code), None)
        if entry is not None:
            report.accepted.append(
                AcceptedFinding(f, str(entry["reason"]), str(entry["accepted_by"]))
            )
        else:
            active.append(f)
    report.findings = active

    for p, msgs in malformed.items():
        for m in msgs:
            report.error("lint_accept_malformed", m, path=p)
    for p, entries in accepts.items():
        present = {f.code for f in by_path.get(p, [])}
        for e in entries:
            if e["code"] not in present:
                report.warn("lint_accept_unused",
                            f"lint_accept code '{e['code']}' matches no finding on this file",
                            path=p)


def render_report(report: LintReport, fmt: str, show_accepted: bool = False) -> str:
    if fmt == "json":
        return json.dumps(
            {
                "target": report.target,
                "counts": report.counts(),
                "findings": [asdict(f) for f in report.findings],
                "accepted": [
                    {"finding": asdict(a.finding), "reason": a.reason,
                     "accepted_by": a.accepted_by}
                    for a in report.accepted
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    # text
    lines = [f"lint target: {report.target}"]
    if not report.findings:
        lines.append("  OK — no findings")
    for f in report.findings:
        loc = f" @ {f.location}" if f.location else ""
        p = f" ({f.path})" if f.path else ""
        lines.append(f"  [{f.severity.upper()}] {f.code}: {f.message}{loc}{p}")
    if show_accepted:
        for a in report.accepted:
            p = f" ({a.finding.path})" if a.finding.path else ""
            lines.append(f"  [ACCEPTED] {a.finding.code}: {a.finding.message}{p}")
            lines.append(f"      reason: {a.reason!r} — by {a.accepted_by}")
    c = report.counts()
    summary = (f"summary: errors={c[SEV_ERROR]} warnings={c[SEV_WARNING]} "
               f"info={c[SEV_INFO]}")
    if c["accepted"]:
        summary += f" accepted={c['accepted']}"
    lines.append(summary)
    if c["accepted"] and not show_accepted:
        lines.append(f"  ({c['accepted']} findings hidden by lint_accept — "
                     f"run with --show-accepted to list)")
    return "\n".join(lines)


def emit_report(report: LintReport, fmt: str, strict: bool,
                show_accepted: bool = False) -> int:
    print(render_report(report, fmt, show_accepted))
    return report.exit_code(strict)


# ---------- Path helpers ----------

def find_ai_work_root(start: Path) -> Path:
    """Walk up from start to find a directory containing .ai-work/."""
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".ai-work").is_dir():
            return p
    raise SystemExit(f"error: no .ai-work/ ancestor found from {start}")


ACCOUNT_INFO_NAME = "account_info.yaml"


def read_account_id(ai_work: Path) -> str:
    """Read account_id from .ai-work/account_info.yaml (CR-AIWS-2026-06-015 v2).

    The local, gitignored account_info.yaml carries the member identity + the per-member AIP id
    counter. Returns the account_id, or '' if the file is missing/unset — callers decide whether
    that is fatal (the allocator errors; init_workspace / run_aip fall back to legacy flat).
    """
    p = ai_work / ACCOUNT_INFO_NAME
    if not p.is_file():
        return ""
    try:
        meta, _ = parse_frontmatter("---\n" + read_text(p).strip("\n") + "\n---\n")
    except Exception:
        return ""
    return str(meta.get("account_id", "")).strip()


LOCATOR_PLACEHOLDER = "__PROJECT_ROOT__"

# ---------- Two-kind node model (CR-AIWS-2026-05-023) ----------
# A node_kind=object meta is a logical entity (function / screen / table / …) with NO
# backing source file; its artifact_locator is this sentinel. The sentinel is preserved
# verbatim by the index projection and is never resolved to a filesystem path (INV-9 / DP7).
# node_kind itself is a META-ONLY field — default 'artifact' when omitted (zero migration,
# DP2) — and MUST NOT be projected into the slim index (INV-7). Defined once here so the
# index builder, lint, and tests share one authoritative sentinel.
OBJECT_LOCATOR_SENTINEL = "__OBJECT__"
NODE_KIND_OBJECT = "object"
NODE_KIND_ARTIFACT = "artifact"

# CR-AIWS-2026-06-002: data-flow relationship types whose ## Related Sources edge carries real
# data/contract coupling — a bare (blank-basis-note) edge of these types is the failure mode the
# basis-note convention (Knowledge_Expansion_Link_Spec §4.4) targets. Defined once here so
# build_relations, lint_wiki, and tests share one authoritative set. WARN-only (never error).
# Representation (represents/represented_by) + companion roles are EXCLUDED (not data-flow).
DATA_FLOW_TYPES = frozenset({"upstream_input", "downstream_target", "x:reads", "x:writes"})


def resolve_locator(s: str, project_root: Path) -> Path:
    """Resolve a locator that may start with __PROJECT_ROOT__."""
    if s.startswith(LOCATOR_PLACEHOLDER):
        rel = s[len(LOCATOR_PLACEHOLDER):].lstrip("/\\")
        return project_root / rel
    return Path(s)


def portable_locator(path: "Path | str", project_root: Path) -> str:
    """Replace project_root prefix with __PROJECT_ROOT__ to make path portable.

    The object-meta sentinel (OBJECT_LOCATOR_SENTINEL) is a logical marker, not a path —
    it is returned verbatim (CR-AIWS-2026-05-023 INV-9), so a node_kind=object meta's
    artifact_locator survives index projection unchanged.
    """
    s = str(path)
    if s == OBJECT_LOCATOR_SENTINEL:
        return s
    pr = str(project_root)
    if s.lower().startswith(pr.lower()):
        # Emit a POSIX placeholder so the locator stays portable across OSes:
        # on Windows str(Path) yields backslashes, but the index / maintenance log
        # are shared, cross-platform artifacts. resolve_locator() reads both styles.
        return (LOCATOR_PLACEHOLDER + s[len(pr):]).replace("\\", "/")
    return s


def today() -> str:
    from datetime import date
    return date.today().isoformat()


def now_utc_iso() -> str:
    """Current time as a UTC ISO 8601 timestamp (CR-AIWS-2026-06-024).

    Used for wiki-meta updated_at on a SOURCELESS meta (object/__OBJECT__ or hand-authored)
    where there is no source file to anchor to."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def source_mtime_iso(path: "Path | str") -> str:
    """A source file's mtime as a UTC ISO 8601 timestamp (CR-AIWS-2026-06-024).

    wiki-meta updated_at for a SOURCE-BACKED meta = the source file's mtime, so the value
    reflects when the source content changed (not when build/refresh ran). Sourceless metas
    use now_utc_iso() instead. CAVEAT: git does not preserve mtime — a fresh clone resets it
    to checkout time; the value is captured-then-frozen, so run build/refresh on the editing
    machine before committing."""
    import os
    from datetime import datetime, timezone
    return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Lookup-key stopwords (shared by all meta builders) — CR-AIWS-2026-06-043 Change A.
# Universal sets stay BUILT-IN here; PROJECT-specific generics are config-driven via
# `configured_stopwords()` (profiles/project_stopwords.yml + a profile's extra_stopwords),
# so a project adds its own generic terms WITHOUT editing any builder.
# (Upstreamed from the YPO Japanet PoC; see CR-AIWS-2026-06-043.)
# ─────────────────────────────────────────────────────────────────────────────

_HTML_HINT_RE = re.compile(r"<(?:!doctype|html|head|body|div|span|script|style)\b", re.IGNORECASE)
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_html(text: str) -> str:
    """Reduce HTML to its visible text: drop <script>/<style> blocks, comments, and all
    tags (with attributes). Leaves label/content text — so lookup-key extraction sees domain
    words (incl. Japanese labels), not Tailwind classes / DOM identifiers."""
    if not text:
        return text
    text = _HTML_COMMENT_RE.sub(" ", text)
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    return text


STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "when",
    "then", "not", "are", "was", "will", "can", "has", "have", "been",
    "but", "you", "your", "our", "all", "any", "use", "used", "using",
}

PROJECT_DESIGN_STOPWORDS = {
    # ── Vietnamese (romanized, no diacritics) ───────────────────────────────
    "nhi", "cho", "khi", "tri", "nay", "van", "voi", "cua", "hay",
    "trong", "theo", "danh", "hoac", "cung", "duoc", "viec", "khong",
    "nguoi", "cac", "mot", "nhu", "sau", "tren", "thi",
    "moi", "neu", "phai", "nhung", "dieu", "sang", "tiep",
    "nua", "roi", "lai", "luon", "rat", "vay",
    "nen", "luc", "tat", "biet", "den",
    "hien", "nhap", "chon", "xem", "tao", "xoa", "sua", "luu",
    "tim", "them", "muon",
    # ── English — instruction / qualifier words ──────────────────────────────
    "yes", "must", "before", "per", "next", "applicable",
    "defined", "missing", "explicitly", "stated", "specified",
    "proceed", "above", "below", "item", "items", "section",
    "note", "notes", "rule", "rules",
    "shall", "ensure", "each", "other", "also", "only",
    "based", "such", "both", "given", "via",
    # ── English — UI / structure layout terms ────────────────────────────────
    "screen", "view", "display", "button", "form",
    "table", "column", "row", "list", "detail",
    "input", "text", "data",
    "field", "label", "icon", "link", "header", "footer",
    "panel", "modal", "popup", "tooltip", "placeholder",
    "layout", "format", "style",
    # ── English — generic CRUD / form action verbs ───────────────────────────
    "check", "select", "click", "apply", "navigate",
    "show", "hide", "open", "close", "save", "enter",
    "submit", "cancel", "confirm", "delete", "create", "add",
    "get", "set", "send", "load", "reset",
    # ── English — generic states / conditions ────────────────────────────────
    "error", "required", "optional", "initial", "empty",
    "active", "true", "false", "result", "status",
    "valid", "invalid", "enabled", "disabled", "visible",
    "success", "failed", "pending", "complete",
    # ── English — generic process / flow concepts ────────────────────────────
    "validation", "function", "design", "overview", "spec",
    "flow", "case", "mode", "step", "state", "event",
    "action", "message", "process", "scenario",
    # ── English — generic value / type descriptors ───────────────────────────
    "value", "values", "type", "types", "name", "number",
    "code", "level", "index", "count", "order",
    # ── English — review / checklist meta words ──────────────────────────────
    "pass", "fail", "review", "verify", "criteria",
    "correct", "accurate", "consistent", "compliant",
}

# Common English filler words with no domain signal.
COMMON_ENGLISH_STOPWORDS = {
    "one", "two", "three", "four", "five", "first", "second", "third", "last",
    "more", "most", "many", "much", "some", "few", "less", "least", "than",
    "over", "under", "after", "while", "during", "between", "within", "without",
    "about", "because", "since", "until", "though", "although", "however",
    "therefore", "thus", "hence", "too", "very", "just", "even", "still", "yet",
    "ever", "never", "always", "often", "same", "such", "own", "another", "every",
    "make", "made", "makes", "take", "takes", "took", "taken", "give", "gives",
    "got", "gets", "going", "goes", "come", "comes", "came", "need", "needs",
    "keep", "kept", "put", "say", "said", "see", "seen", "look", "find", "found",
    "work", "works", "way", "ways", "part", "parts", "thing", "things", "kind",
    "lot", "lots", "end", "begin", "start", "starts", "cold", "hot", "heavy",
    "light", "hard", "easy", "fast", "slow", "high", "low", "big", "small",
    "long", "short", "early", "late", "good", "best", "better", "new", "old",
    "full", "path", "cost", "costs", "price", "month", "months", "week", "weeks",
    "year", "years", "day", "days", "night", "time", "times", "today", "now",
    "version", "amount", "total", "main", "basic", "general", "common", "simple",
    "various", "several", "multiple", "single", "here", "there", "back", "down",
}

# HTML/CSS/JS/Tailwind tokens — for HTML mockups, attributes + <script>/<style> are stripped
# first (strip_html), but this catches residual leakage from any source.
WEB_TECH_STOPWORDS = {
    "div", "span", "html", "body", "head", "nav", "main", "section", "article",
    "aside", "ul", "img", "svg", "path", "rect", "circle", "src", "alt",
    "href", "class", "style", "onclick", "onchange", "onsubmit", "id", "role",
    "aria", "viewbox", "xmlns", "stroke", "fill",
    "const", "let", "var", "function", "return", "document", "window", "queryselector",
    "getelementbyid", "addeventlistener", "console", "null", "undefined", "async",
    "await", "import", "export", "default",
    "flex", "grid", "block", "inline", "hidden", "relative", "absolute", "fixed",
    "border", "rounded", "shadow", "ring", "outline", "opacity", "overflow",
    "font", "bold", "medium", "semibold", "italic", "uppercase", "center",
    "left", "right", "justify", "items", "gap", "space", "col", "row", "auto",
    "white", "black", "gray", "slate", "blue", "red", "green", "yellow",
    "indigo", "purple", "pink", "transition", "transform", "scale", "hover",
    "focus", "active", "group", "shrink", "grow", "min", "max", "none", "full",
    "lucide", "colors", "color", "background", "padding", "margin", "width", "height",
}


def _read_yaml_stopword_list(path: "Path", key: str) -> set:
    """Read a simple block list `<key>:` + `  - a` / `  - b` from a YAML file → lowercased set.
    Self-contained (no full YAML dep); tolerant of quotes and a trailing top-level key."""
    out: set = set()
    try:
        if not path.exists():
            return out
        in_list = False
        for line in read_text(path).splitlines():
            stripped = line.strip()
            if not in_list:
                if stripped == f"{key}:" or stripped.startswith(f"{key}:"):
                    in_list = True
                continue
            if stripped.startswith("- "):
                w = stripped[2:].strip().strip('"').strip("'")
                if w:
                    out.add(w.lower())
            elif stripped and not (line.startswith(" ") or line.startswith("\t")):
                break  # next top-level key ends the list
    except Exception:  # noqa: BLE001
        return out
    return out


def configured_stopwords(profile_path: "Path") -> set:
    """PROJECT-configurable stopwords (lowercased), self-contained from files:
      • the profile's own `extra_stopwords:` list (per source type), and
      • sibling `project_stopwords.yml` `stopwords:` list (project-wide).
    Adding project generics needs only these config files — never a builder edit."""
    out: set = set()
    out |= _read_yaml_stopword_list(profile_path, "extra_stopwords")
    out |= _read_yaml_stopword_list(profile_path.parent / "project_stopwords.yml", "stopwords")
    return out


def lookup_key_stopwords(profile_path: "Path") -> set:
    """Full prose/doc lookup-key stopword set: ALL universal built-ins ∪ project/profile config.
    Use for prose/doc + HTML-mockup metas (build_wiki_source_meta)."""
    return (STOPWORDS | PROJECT_DESIGN_STOPWORDS | COMMON_ENGLISH_STOPWORDS
            | WEB_TECH_STOPWORDS | configured_stopwords(profile_path))


def code_key_stopwords(profile_path: "Path") -> set:
    """Lookup-key stopword set tuned for SOURCE CODE (java/ts) — CR-AIWS-2026-06-043 Change A.
    Deliberately EXCLUDES PROJECT_DESIGN_STOPWORDS (it holds code-relevant words like event/
    state/type/message/data/status that are valid domain identifiers). Uses common-English
    filler + web-tech + project/profile config, so project generics (member/admin/…) drop from
    code keys WITHOUT discarding domain class/identifier names."""
    return COMMON_ENGLISH_STOPWORDS | WEB_TECH_STOPWORDS | configured_stopwords(profile_path)


# ─────────────────────────────────────────────────────────────────────────────
# Step-2 enrich engine (shared by all language meta builders) — CR-AIWS-2026-06-048.
# A language meta builder = canonical Step-1 (facts → lean meta, AIWS-owned) ⊕ project Step-2
# enrich (project-owned, NOT shipped). apply_enrich consumes the Step-1 FACTS DICT (engine-agnostic
# — identical under regex or tree-sitter) + the project's profile, and returns augmentations the
# builder folds in. Two mechanisms (HYBRID): (1) the profile's declarative `enrich:` block (PRIMARY),
# (2) an optional project code-hook `.ai-work/wiki_sources/enrich/<source_type>.py` (ESCAPE).
# Graceful by contract: no `enrich:` and no hook → empty augmentations; any error → that source is
# skipped (never raises), so Step-1 output is preserved. Deterministic + idempotent.
# ─────────────────────────────────────────────────────────────────────────────

ENRICH_AUG_KEYS = ("extra_lookup_keys", "extra_edges", "extra_concepts", "extra_sections")


def _load_profile_yaml(profile_path: "Path") -> dict:
    """Parse a profile .yml (no --- fence) into a dict, reusing the minimal frontmatter parser.
    Returns {} on any error. NOTE: the parser does NOT process YAML escapes — scalar values are
    taken verbatim (so regex patterns in `enrich:` use SINGLE backslashes, e.g. '\\b[MA]-\\d{2}\\b')."""
    try:
        p = Path(profile_path)
        if not p.is_file():
            return {}
        meta, _ = parse_frontmatter("---\n" + read_text(p).strip("\n") + "\n---\n")
        return meta or {}
    except Exception:  # noqa: BLE001
        return {}


def apply_enrich(facts: dict, profile_path: "Path", src: str) -> dict:
    """Step-2 enrich (CR-AIWS-2026-06-048). Returns augmentations:
    {extra_lookup_keys, extra_edges, extra_concepts, extra_sections} (deterministic, deduped).

    Declarative `enrich:` schema v1 (profile, project-owned):
      enrich:
        lookup_key_patterns:        # each is a Python regex, applied verbatim to raw `src`; every
          - '\\b[MA]-\\d{2}\\b'      #   match (group 0) becomes an extra lookup key
        concept_keywords:           # signal token (annotation / type-name / package) -> concepts
          Scheduled: ["batch job", "scheduled task"]
    Single-token added keys pass the CR-043 code-key stopword filter; multi-word keys are kept.
    Optional code-hook `.ai-work/wiki_sources/enrich/<source_type>.py` exposing
    `def enrich(facts, src, ctx) -> dict` is imported if present (its lists merge in)."""
    aug: dict = {k: [] for k in ENRICH_AUG_KEYS}
    profile = _load_profile_yaml(profile_path)
    enrich = profile.get("enrich") or {}

    if isinstance(enrich, dict):
        # (1) declarative — lookup_key_patterns: regex over raw src -> extra lookup keys
        stop = code_key_stopwords(Path(profile_path))
        patterns = enrich.get("lookup_key_patterns") or []
        if isinstance(patterns, list):
            for pat in patterns:
                try:
                    rx = re.compile(str(pat))
                except re.error:
                    continue
                for m in rx.finditer(src or ""):
                    k = (m.group(0) or "").strip()
                    if not k:
                        continue
                    # CR-043 single-token stopword filter; multi-word kept
                    if (" " in k) or (k.lower() not in stop):
                        if k not in aug["extra_lookup_keys"]:
                            aug["extra_lookup_keys"].append(k)
        # (1) declarative — concept_keywords: signal present in facts -> add its concepts
        ck = enrich.get("concept_keywords") or {}
        if isinstance(ck, dict) and ck:
            annos = [a for t in facts.get("types", []) for a in t.get("annotations", [])]
            names = [t.get("name", "") for t in facts.get("types", [])]
            haystack = " ".join(annos + names + [facts.get("package", "")])
            for signal, concepts in ck.items():
                if str(signal) and str(signal) in haystack:
                    vals = concepts if isinstance(concepts, list) else [concepts]
                    for c in vals:
                        c = str(c).strip()
                        if c and c not in aug["extra_concepts"]:
                            aug["extra_concepts"].append(c)

    # (2) optional project code-hook (ESCAPE) — never break Step-1 on hook trouble
    try:
        source_type = str(profile.get("source_type") or "").strip()
        if source_type:
            hook = Path(profile_path).parent.parent / "enrich" / f"{source_type}.py"
            if hook.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"_enrich_{source_type}", hook)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    fn = getattr(mod, "enrich", None)
                    if callable(fn):
                        res = fn(facts, src, {"profile": profile, "profile_path": str(profile_path)}) or {}
                        if isinstance(res, dict):
                            for key in ENRICH_AUG_KEYS:
                                for v in (res.get(key) or []):
                                    if v not in aug[key]:
                                        aug[key].append(v)
    except Exception:  # noqa: BLE001 — hook error degrades to declarative-only
        pass

    return aug
