#!/usr/bin/env python3
"""Create or refresh a Wiki Source Meta artifact from a source + profile.

A source meta is a small, memory-friendly markdown file with YAML frontmatter
describing a source artifact (code file, design doc, table, etc.) so that
Wiki authors can look up + orient before opening the full source.

Profiles describe HOW to interpret a source type — see
`.ai-work/wiki_sources/profiles/README.md`. Profiles optionally
include: format_signature, summary_extraction, t1_key_extraction,
hints_extraction.

Usage:
  build_wiki_source_meta.py --artifact <path> --source-id <id> \
      --source-type <type> --profile <profile.yml> \
      [--title <title>] [--out <meta.md>] [--mode create|refresh]

Semantic override args (AI-derived content takes priority over profile):
  --summary "..."                AI-derived summary
  --knowledge-targets "a,b,c"   Comma-separated, overrides profile targets
  --lookup-keys "k1,k2"         Pinned T1/T2/T3 keys at top of list
  --hints-depth N               Max heading depth for Source-Specific Hints (default: 2)

Format validation (Phase 1 = WARNING only — never blocks):
  Mismatch prints a warning but always proceeds.
  --skip-format-check           Bypass format validation entirely (requires all 4 semantic args)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    dump_frontmatter,
    find_ai_work_root,
    parse_frontmatter,
    read_text,
    source_mtime_iso,
    write_text,
    # CR-AIWS-2026-06-043 Change A: stopword sets/helpers now live in _common (moved + extended).
    STOPWORDS,
    PROJECT_DESIGN_STOPWORDS,
    lookup_key_stopwords,
    strip_html,
    _HTML_HINT_RE,
)
from lookup_wiki_source import _project_config  # noqa: E402  reuse the multi-system reader (CR-AIWS-2026-06-058)

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
HEADING_MD_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_VERSION_RE = re.compile(r"^v\d+(?:_\d+)*$", re.IGNORECASE)
_FILE_EXT_NOISE = {"md", "txt", "py", "yml", "yaml", "json", "js", "ts", "csv", "xml", "html"}
_BOM = "﻿"


def _load_profile(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"error: profile not found: {path}")
    text = read_text(path)
    meta, _ = parse_frontmatter("---\n" + text + "\n---\n")
    return meta or {}


def _unquote_yaml(s: str) -> str:
    """Strip YAML quotes; process escape sequences for double-quoted strings."""
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        inner = s[1:-1]
        inner = inner.replace('\\\\', '\x00').replace('\\"', '"').replace('\x00', '\\')
        return inner
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    return s


def _coerce_yaml_scalar(s: str):
    """Coerce a PMP scalar: unquoted true/false -> bool, null/~ -> None, int if integer, else str.
    (CR-AIWS-2026-06-043 Change B added bool/null so emit_scaffold:false in a PMP is honored; int retained.)"""
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    try:
        return int(s)
    except ValueError:
        return s


def _parse_yaml_nested(lines: list[str], start: int, parent_indent: int) -> tuple[dict, int]:
    """Parse indented YAML lines into a nested dict. Returns (dict, next_line_idx).

    Handles: scalars (int-coerced), flow lists, block lists, nested dicts,
    and double-quoted YAML escape sequences (backslash-backslash to backslash).
    """
    result: dict = {}
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if parent_indent >= 0 and indent <= parent_indent:
            break
        if ':' not in stripped:
            i += 1
            continue
        key, _, val_raw = stripped.partition(':')
        key = key.strip()
        val_raw = val_raw.strip()
        if val_raw.startswith('[') and val_raw.endswith(']'):
            inner = val_raw[1:-1].strip()
            result[key] = [_unquote_yaml(p)
                           for p in inner.split(',') if p.strip()] if inner else []
            i += 1
        elif val_raw in ('', '>'):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or (len(lines[j]) - len(lines[j].lstrip())) <= indent:
                result[key] = None
                i = j
                continue
            child_indent = len(lines[j]) - len(lines[j].lstrip())
            if lines[j].lstrip().startswith('- '):
                items: list[str] = []
                i = j
                while i < len(lines):
                    cl = lines[i]
                    if not cl.strip():
                        i += 1
                        continue
                    if (len(cl) - len(cl.lstrip())) < child_indent:
                        break
                    cs = cl.lstrip()
                    if cs.startswith('- '):
                        items.append(_unquote_yaml(cs[2:]))
                        i += 1
                    else:
                        break
                result[key] = items
            else:
                nested, i = _parse_yaml_nested(lines, j, indent)
                result[key] = nested
        else:
            result[key] = _coerce_yaml_scalar(_unquote_yaml(val_raw))
            i += 1
    return result, i


def _load_pmp(profile_path: Path) -> dict:
    """Load the Project Mapping Pattern for this profile, if it exists.

    PMP lives alongside profiles at pmp_<profile_id>.yml.
    Returns {} (empty dict) if no PMP found — callers must handle gracefully.
    """
    try:
        profile = _load_profile(profile_path)
        profile_id = profile.get("profile_id", "")
    except SystemExit:
        return {}
    if not profile_id:
        return {}
    pmp_path = profile_path.parent / f"pmp_{profile_id}.yml"
    if not pmp_path.exists():
        return {}
    text = read_text(pmp_path)
    result, _ = _parse_yaml_nested(text.splitlines(), 0, -1)
    return result


def _is_path_noise(token: str) -> bool:
    """Return True for path/filesystem tokens with no lookup value."""
    t = token.lower()
    if t.endswith(":"):
        return True
    if _VERSION_RE.match(t):
        return True
    if t in _FILE_EXT_NOISE:
        return True
    return False


def _extract_lookup_keys(text: str, path_tokens: list[str],
                         source_type: str, max_keys: int = 40,
                         pinned_keys: list[str] | None = None,
                         profile_path: "Path | None" = None) -> list[str]:
    # CR-AIWS-2026-06-043 Change A: config-driven stopwords (universal ∪ project/profile config) +
    # HTML-strip for HTML/ui_mockup sources so domain words are seen, not Tailwind/DOM tokens.
    stopwords = (lookup_key_stopwords(profile_path) if profile_path is not None
                 else STOPWORDS | PROJECT_DESIGN_STOPWORDS)
    if source_type == "ui_mockup" or _HTML_HINT_RE.search(text or ""):
        text = strip_html(text)
    keys: dict[str, int] = {}
    for t in path_tokens:
        if not _is_path_noise(t):
            keys[t.lower()] = keys.get(t.lower(), 0) + 5
    for m in IDENT_RE.findall(text):
        k = m.strip()
        if len(k) < 3 or k.lower() in stopwords:
            continue
        keys[k] = keys.get(k, 0) + 1
    pinned = [k for k in (pinned_keys or []) if k]
    pinned_lower = {k.lower() for k in pinned}
    ranked = [k for k, _ in sorted(keys.items(), key=lambda kv: -kv[1])
              if k not in pinned_lower]
    return pinned + ranked[:max(0, max_keys - len(pinned))]


# STOPWORDS + PROJECT_DESIGN_STOPWORDS moved to _common.py (CR-AIWS-2026-06-043 Change A) and
# imported above — single shared home so all builders use one mechanism + projects tune via config.


def _summary_from_text(text: str, max_chars: int = 400) -> str:
    """Fallback: return first non-heading, non-special, non-metadata line."""
    _META_LINE_RE = re.compile(
        r"^(Version|Project|Document\s*ID|Function\s*ID|Function\s*name|Date|Author|Status|Phase|Scope|doc[-_]?id|doc_type|document_type|title|version)\s*:",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        s = line.strip().lstrip(_BOM)
        if not s:
            continue
        if s.startswith(("#", "---", "```", "//", "*", "-", "|")):
            continue
        if _META_LINE_RE.match(s):
            continue
        return s[:max_chars - 3] + "..." if len(s) > max_chars else s
    return ""


def _summary_from_table(rows: list[str], max_chars: int = 400) -> str:
    """Extract a meaningful summary from markdown table rows (IR-14).

    Prefers a row whose first cell labels Summary/Overview/Purpose/Description
    (incl. JP 概要/概略); otherwise joins the first data row after the header.
    Skips separator rows (|---|---|)."""
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    data_rows = [r for r in rows if set(r.replace("|", "").strip()) - set("-: ")]
    label_re = re.compile(r"(summary|overview|purpose|description|概要|概略)", re.IGNORECASE)
    for r in data_rows:
        cs = cells(r)
        if cs and label_re.search(cs[0]):
            val = " ".join(c for c in cs[1:] if c) or " ".join(c for c in cs if c)
            if val.strip():
                return val.strip()
    # fallback: first data row that isn't the header row
    for r in (data_rows[1:] if len(data_rows) > 1 else data_rows):
        cs = [c for c in cells(r) if c]
        if cs:
            return " — ".join(cs)
    return ""


def _extract_section_first_paragraph(text: str, section_name: str,
                                     max_chars: int = 400) -> str:
    """Find section by name and return its full content (prose + bullets), truncated to max_chars.

    If the section body is a table (IR-14), extract a meaningful row instead of
    skipping all table lines, so table-formatted target sections don't yield an
    empty summary that silently degrades to a low-confidence fallback."""
    in_section = False
    collected: list[str] = []
    table_rows: list[str] = []
    for line in text.splitlines():
        s = line.strip().lstrip(_BOM)
        if re.search(rf"^#{{1,6}}\s+.*{re.escape(section_name)}\s*$", s, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if s.startswith("#"):
                break
            if s.startswith("|"):
                table_rows.append(s)
                continue
            if not s or s.startswith(("```", ">")):
                continue
            item = s.lstrip("-* ").strip() if s.startswith(("-", "*")) else s
            if item:
                collected.append(item)
    result = " ".join(collected)
    if not result and table_rows:
        result = _summary_from_table(table_rows, max_chars)
    return result[:max_chars - 3] + "..." if len(result) > max_chars else result


def _summary_from_profile(text: str, spec: dict, max_chars: int = 400) -> str:
    """Extract summary using extraction spec (PMP if available, else profile)."""
    extraction = spec.get("summary_extraction") or {}
    target_sections = extraction.get("target_sections") or []
    # Stdlib YAML parser yields strings for scalars; coerce max_chars to int.
    chars = extraction.get("max_chars", max_chars)
    try:
        chars = int(chars)
    except (TypeError, ValueError):
        chars = max_chars
    for section_name in target_sections:
        content = _extract_section_first_paragraph(text, section_name, chars)
        if content:
            return content
    return ""


def _headings(text: str, max_depth: int = 2) -> list[str]:
    """Extract all headings up to max_depth level — no count limit."""
    pattern = re.compile(rf"^#{{1,{max_depth}}}\s+(.+)$", re.MULTILINE)
    return pattern.findall(text)


def _validate_format_signature(text: str, spec: dict) -> dict | None:
    """Check artifact against format_signature from extraction spec (PMP if available).
    Returns None if OK (or no signature defined), dict with mismatch details otherwise."""
    sig = spec.get("format_signature") or {}
    required = sig.get("required_headings") or []
    if not required:
        return None
    found = [h.lower() for h in HEADING_MD_RE.findall(text)]
    missing = [r for r in required if not any(r.lower() in h for h in found)]
    if not missing:
        return None
    return {
        "missing_headings": missing,
        "required_headings": required,
        "profile_id": spec.get("profile_id", spec.get("pmp_id", "unknown")),
    }


def _extract_t1_keys_from_profile(text: str, spec: dict) -> list[str]:
    """Extract T1 keys using t1_key_extraction from extraction spec (PMP if available)."""
    t1_spec = spec.get("t1_key_extraction") or {}
    pattern = t1_spec.get("pattern")
    patterns = t1_spec.get("patterns") or ([pattern] if pattern else [])
    keys: list[str] = []
    seen: set[str] = set()
    for pat in patterns:
        for m in re.findall(pat, text):
            if m not in seen:
                keys.append(m)
                seen.add(m)
    return keys


def _print_mismatch_warning(mismatch: dict) -> None:
    """Print format mismatch as WARNING — always proceeds (Phase 1 behaviour)."""
    pid = mismatch["profile_id"]
    missing = mismatch["missing_headings"]
    print(f"\nWARNING: Format partially matches extraction spec '{pid}'", file=sys.stderr)
    print(f"  Missing required_headings: {missing}", file=sys.stderr)
    print("  Proceeding anyway. Options to resolve:", file=sys.stderr)
    print("    (a) Create a new profile/PMP for this format, then retry", file=sys.stderr)
    print("    (b) Use a different profile: --profile <other.yml>", file=sys.stderr)
    print("    (c) Suppress: --skip-format-check (also requires --lookup-keys)",
          file=sys.stderr)


# ── Related Sources scaffold (CR-AIWS-2026-05-017) ───────────────────────────
RS_ROLES = ("upstream_input", "downstream_navigation", "downstream_target", "triggered_flow",
            "system_foundation", "companion_design", "companion_requirement",
            "output_template", "related")


def _extract_md_section(text: str, heading: str) -> str:
    """Return the '## <heading>' section (heading line + body up to next '## ') or ''."""
    out: list[str] = []
    capturing = False
    for ln in text.splitlines():
        if ln.strip().startswith("## "):
            if capturing:
                break
            capturing = ln.strip()[3:].strip().lower() == heading.lower()
            if capturing:
                out.append(ln)
            continue
        if capturing:
            out.append(ln)
    return "\n".join(out).strip()


def _is_rs_scaffold_only(section: str) -> bool:
    """True if the Related Sources section is still unresolved scaffold (TODO markers, no real ids)."""
    return ("<SRC-id: TODO>" in section) or ("TODO: fill real source_ids" in section)


def _related_sources_scaffold(rs_cfg: dict) -> "list[str]":
    """Lớp 1 (spec-driven role slots) + Lớp 3 (always-on enum + TODO marker)."""
    lines = ["", "## Related Sources",
             "<!-- roles: " + " · ".join(RS_ROLES[:4]) + " ·",
             "     " + " · ".join(RS_ROLES[4:]) + " -->"]
    roles: list[str] = []
    for r in (rs_cfg.get("expected_roles") or []):
        if isinstance(r, str) and r.strip():
            roles.append(r.strip())          # flat list form: "- upstream_input"
        elif isinstance(r, dict) and r.get("role"):
            roles.append(str(r["role"]))     # dict form (real YAML): "- role: upstream_input"
    for role in roles:
        lines.append(f"- **<SRC-id: TODO>** — role: {role} — <why/when to open>")
    lines.append("<!-- TODO: fill real source_ids or delete this section if no relationships -->")
    return lines


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wiki Source Meta")
    p.add_argument("--artifact", required=True, help="Source artifact path")
    p.add_argument("--source-id", required=True, help="Unique source id")
    p.add_argument("--source-type", required=True,
                   help="Category, e.g. basic_design|requirement_spec")
    p.add_argument("--profile", required=True, help="Source Interpretation Profile file")
    p.add_argument("--title", help="Human title (default: filename)")
    p.add_argument("--out", help="Output meta path (default: wiki_sources/meta/<source-id>.md)")
    p.add_argument("--mode", choices=["create", "refresh"], default="create")
    p.add_argument("--authority-level", default="unknown")
    p.add_argument("--freshness-status", default="unknown")
    p.add_argument("--source-representation-status", default="unknown")
    p.add_argument("--source-representation-caution",
                   default="Representation quality has not been reviewed.")
    p.add_argument("--source-representation-quality-issue", action="store_true")
    p.add_argument("--knowledge-value", default="unknown")
    p.add_argument("--intended-ai-use", default="unknown")
    p.add_argument("--promotion-status", default="draft")
    p.add_argument("--maintenance-status", default="needs_review")
    p.add_argument("--original-source-locator", default="")
    p.add_argument("--representation-locator", default="")
    p.add_argument("--representation-type", default="markdown")
    p.add_argument("--conversion-method", default="unknown")
    p.add_argument("--conversion-date", default="")
    p.add_argument("--converted-by", default="")
    p.add_argument("--conversion-limitations", default="",
                   help="Comma-separated conversion limitations")
    p.add_argument("--representation-scope", default="unknown")
    # Semantic override args (AI-derived content)
    p.add_argument("--summary", default="",
                   help="Override auto-extracted summary with AI-derived semantic summary")
    p.add_argument("--knowledge-targets", default="",
                   help="Comma-separated list to override profile knowledge_targets")
    p.add_argument("--lookup-keys", default="",
                   help="Comma-separated T1/T2/T3 keys pinned to top of lookup key list")
    p.add_argument("--hints-depth", type=int, default=None,
                   help="Max heading depth for Source-Specific Hints (default: PMP value or 2)")
    p.add_argument("--skip-format-check", action="store_true",
                   help="Bypass format validation. Requires --summary, --knowledge-targets, "
                        "and --lookup-keys.")
    p.add_argument("--no-related-sources", action="store_true",
                   help="Do not emit the ## Related Sources scaffold (opt-out for artifacts "
                        "with no relationships).")
    # CR-AIWS-2026-06-058: set the meta's multi-system `system:` at create time (mirror the lookup gate).
    p.add_argument("--system", default=None, metavar="ID",
                   help="Multi-system (CR-017): tag this meta to system <id> (validated against "
                        "project_profile.systems). In a multi_system project pass this or --common.")
    p.add_argument("--common", action="store_true",
                   help="Multi-system: mark this meta system-agnostic/common (emit NO system key). "
                        "Mutually exclusive with --system.")
    ns = p.parse_args()

    artifact = Path(ns.artifact).resolve()
    if not artifact.exists():
        print(f"error: artifact not found: {artifact}", file=sys.stderr)
        return 2

    profile_path = Path(ns.profile).resolve()
    profile = _load_profile(profile_path)
    pmp = _load_pmp(profile_path)
    extraction_spec = pmp if pmp else profile

    ai_work = find_ai_work_root(artifact) / ".ai-work"
    out_path = Path(ns.out).resolve() if ns.out else (
        ai_work / "wiki_sources" / "meta" / f"{ns.source_id}.md")

    if ns.mode == "create" and out_path.exists():
        print(f"error: {out_path} already exists (use --mode refresh)", file=sys.stderr)
        return 2

    # ── Multi-system `system:` resolution (CR-AIWS-2026-06-058) ───────────────
    # Mirror lookup_wiki_source's gate: in a multi_system project require --system or --common.
    # Single-system → flags ignored unless --system explicitly given. Refresh preserves an
    # existing system: when no flag is passed (never silently drops it).
    if ns.system and ns.common:
        print("error: --system and --common are mutually exclusive", file=sys.stderr)
        return 2
    _cfg = _project_config(ai_work)
    _existing_system = None
    if ns.mode == "refresh" and out_path.exists():
        _existing_system = (parse_frontmatter(read_text(out_path))[0] or {}).get("system") or None
    system_val = None
    if ns.system:
        system_val = ns.system.strip()
        if _cfg["multi_system"] and _cfg["systems"] and system_val not in _cfg["systems"]:
            print(f"error: --system {system_val!r} is not in this project's systems "
                  f"{_cfg['systems']}.", file=sys.stderr)
            return 2
    elif ns.common:
        system_val = None                                   # explicit common (no key)
    elif ns.mode == "refresh" and _existing_system:
        system_val = _existing_system                       # preserve on refresh
    elif _cfg["multi_system"]:
        print("error: this is a multi_system project — pass --system <id> (the meta's system) "
              "or --common (system-agnostic). No silent default.", file=sys.stderr)
        return 2
    # single-system + no flag → system_val stays None (byte-identical to pre-CR behavior)

    text = read_text(artifact)
    title = ns.title or artifact.stem

    # ── Format validation ────────────────────────────────────────────────────
    if ns.skip_format_check:
        missing_args = [a for a, v in [
            ("--summary", ns.summary.strip()),
            ("--knowledge-targets", ns.knowledge_targets.strip()),
            ("--lookup-keys", ns.lookup_keys.strip()),
        ] if not v and v != ""]
        if missing_args:
            print(f"error: --skip-format-check requires: {', '.join(missing_args)}",
                  file=sys.stderr)
            return 2
    else:
        mismatch = _validate_format_signature(text, extraction_spec)
        if mismatch:
            _print_mismatch_warning(mismatch)  # always proceeds (Phase 1)

    # ── Summary (priority: arg > extraction_spec > fallback) ─────────────────
    if ns.summary.strip():
        summary = ns.summary.strip()
    else:
        summary = _summary_from_profile(text, extraction_spec)
        if not summary:
            summary = _summary_from_text(text)
            if summary:
                print("WARNING: summary came from low-confidence fallback (no profile/PMP "
                      "section matched). Pass --summary for a quality meta.", file=sys.stderr)
        if not summary:
            summary = "(no semantic summary — re-run with --summary \"...\" for quality meta)"
            print("WARNING: could not extract summary. Use --summary for quality meta.",
                  file=sys.stderr)

    # ── Knowledge targets (priority: arg > profile) ──────────────────────────
    if ns.knowledge_targets.strip():
        knowledge_targets = [k.strip() for k in ns.knowledge_targets.split(",") if k.strip()]
    else:
        knowledge_targets = profile.get("knowledge_targets") or []
    if not knowledge_targets:
        knowledge_targets = [ns.source_type]

    # ── Lookup keys: T1 patterns (from PMP/profile) + pinned arg + auto-extract
    spec_t1_keys = _extract_t1_keys_from_profile(text, extraction_spec)
    pinned_keys = spec_t1_keys + [
        k.strip() for k in ns.lookup_keys.split(",") if k.strip()
    ]
    path_tokens = [
        t for t in re.split(r"[\\/._\-]", artifact.stem) if t and len(t) > 2
    ]
    lookup_keys = _extract_lookup_keys(text, path_tokens, ns.source_type,
                                       pinned_keys=pinned_keys, profile_path=profile_path)

    # ── Headings for Source-Specific Hints ───────────────────────────────────
    # CLI --hints-depth wins; fall back to PMP value, then default 2
    if ns.hints_depth is not None:
        hints_depth_val = ns.hints_depth
    else:
        hints_depth_val = extraction_spec.get("hints_extraction", {}).get("max_depth", 2)
    hints_depth = max(1, min(hints_depth_val, 6))
    headings = _headings(text, max_depth=hints_depth)

    try:
        _rel = artifact.relative_to(ai_work.parent).as_posix()
    except ValueError:
        print("WARNING: artifact is outside project root; storing absolute path in artifact_locator",
              file=sys.stderr)
        _rel = str(artifact)
    if "\\" in _rel:
        print(f"WARNING: relative path still contains backslashes after normalization: {_rel}",
              file=sys.stderr)
    representation_locator = ns.representation_locator or _rel
    original_source_locator = ns.original_source_locator or ""
    conversion_limitations = [
        x.strip() for x in ns.conversion_limitations.split(",") if x.strip()
    ]

    meta: dict = {
        "artifact_type": "wiki_source_meta",
        "source_id": ns.source_id,
        "title": title,
        "source_type": ns.source_type,
        "artifact_locator": representation_locator,
        "profile_id": profile.get("profile_id", profile_path.stem),
        "status": "active",
        "updated_at": source_mtime_iso(artifact),  # CR-AIWS-2026-06-024: source-backed = source file mtime
        "authority_level": ns.authority_level,
        "freshness_status": ns.freshness_status,
        "promotion_status": ns.promotion_status,
        "source_representation_status": ns.source_representation_status,
        "source_representation_caution": ns.source_representation_caution,
        "knowledge_value": ns.knowledge_value,
        "intended_ai_use": ns.intended_ai_use,
        "representation_type": ns.representation_type,
        "conversion_method": ns.conversion_method,
        "conversion_limitations": conversion_limitations,
    }
    if system_val:                                          # CR-058: conditional — absent = common
        meta["system"] = system_val
    if original_source_locator:
        meta["original_source_locator"] = original_source_locator
    if ns.conversion_date:
        meta["conversion_date"] = ns.conversion_date
    if ns.converted_by:
        meta["converted_by"] = ns.converted_by

    body_lines: list[str] = [
        f"# Wiki Source Meta — {title}",
        "",
        "## Summary",
        summary,
        "",
        "## Knowledge Targets",
    ]
    for kt in knowledge_targets:
        body_lines.append(f"- {kt}")
    body_lines += ["", "## Lookup Keys"]
    for k in lookup_keys:
        body_lines.append(f"- {k}")
    if headings:
        body_lines += ["", "## Source-Specific Hints"]
        for h in headings:
            body_lines.append(f"- heading: {h}")
    # ## Profile Mapping body section dropped (CR-AIWS-2026-05-024): it mirrored the
    # frontmatter `profile_id` verbatim (zero AI-orientation value). The frontmatter
    # profile_id stays the single source of truth.

    # ── Related Sources scaffold (CR-017): spec-driven roles + always-on TODO ──
    # Refresh preserves a human/AI-RESOLVED section; only (re)writes the scaffold otherwise.
    if not ns.no_related_sources:
        rs_cfg = extraction_spec.get("related_sources") or {}
        if rs_cfg.get("emit_scaffold", True):
            existing_rs = ""
            if ns.mode == "refresh" and out_path.exists():
                existing_rs = _extract_md_section(read_text(out_path), "Related Sources")
            if existing_rs and not _is_rs_scaffold_only(existing_rs):
                body_lines += ["", existing_rs.rstrip()]   # keep resolved section as-is
            else:
                body_lines += _related_sources_scaffold(rs_cfg)
    body_lines.append("")

    write_text(out_path, dump_frontmatter(meta) + "\n".join(body_lines))
    print(f"source meta {'refreshed' if ns.mode == 'refresh' else 'created'}: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
