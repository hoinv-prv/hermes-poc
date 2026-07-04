#!/usr/bin/env python3
"""Lookup sources via the Wiki Source Index.

Modes:
  - lexical  : substring match across source_id, title, lookup_keys, path
  - id       : exact source_id match
  - path     : match against path tokens of artifact_locator
  - semantic : token-level bag-of-words match — splits query into tokens,
               scores each token against lookup_keys + summary; handles
               multi-word queries and concept-level retrieval

Scope & raw search (CR-AIWS-2026-06-052):
  --scope        comma-list of registered indices (project,local,aiws; 'all' = all three).
                 Default 'project,aiws' — local is rule-#11-gated (opt-in, requires --authorized).
  --include-raw  off | on-empty | always — un-registered (raw) Glob/Grep fallback over the
                 project dirs in document_search_guidelines.md. Requires --authorized.
  --authorized   human | aip | agent-rule — REQUIRED when --include-raw != off OR scope goes
                 beyond project,aiws. Absent → the tool refuses (halt-and-ask, never silent).
  --lookup-mode  object | concept (default concept). The on-empty raw fallback fires only for
                 object lookups (0 registered hits + object mode).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_ai_work_root, parse_frontmatter, read_jsonl  # noqa: E402


def _project_config(ai_work) -> dict:
    """Read .ai-work/project_profile.yml for multi-system scoping (CR-AIWS-2026-06-017).

    Returns {"multi_system": bool, "systems": [..]}. Absent/false → single-system (no scoping).
    """
    from pathlib import Path as _P
    p = _P(ai_work) / "project_profile.yml"
    if not p.exists():
        return {"multi_system": False, "systems": []}
    meta, _ = parse_frontmatter("---\n" + p.read_text(encoding="utf-8") + "\n---\n")
    ms = str((meta or {}).get("multi_system", "")).strip().lower() in ("true", "1", "yes")
    systems = (meta or {}).get("systems") or []
    if not isinstance(systems, list):
        systems = []
    return {"multi_system": ms, "systems": [str(s).strip() for s in systems if str(s).strip()]}


def _in_system(record: dict, active_system) -> bool:
    """CR-AIWS-2026-06-017 multi-system membership: True if the record belongs to the active
    system, where a common doc (no `system` field) is visible under every system. active_system
    None (single-system / --all-systems) → always True. Single source of this predicate —
    reused by smoke_test_wiki_lookup.py (CR-AIWS-2026-06-058) so the regression tool agrees
    with production instead of re-implementing the gate."""
    if active_system is None:
        return True
    sysv = record.get("system", "")
    return (not sysv) or sysv == active_system


SUPERSEDED_PENALTY = 0.2

DEFAULT_SCOPE = "project,aiws"          # CR-AIWS-2026-06-052: narrow-by-default (local is rule-#11-gated)
VALID_SCOPES = {"project", "local", "aiws"}


def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[\\/._\-\s]", s) if t]


def _parse_scope(raw: str) -> set[str]:
    """Parse a comma-list --scope value into a set of registered indices.

    'all' expands to the full set. Raises ValueError on an unknown token
    (CR-AIWS-2026-06-052).
    """
    toks = {t.strip().lower() for t in (raw or "").split(",") if t.strip()}
    if not toks:
        toks = {t.strip() for t in DEFAULT_SCOPE.split(",")}
    if "all" in toks:
        return set(VALID_SCOPES)
    bad = toks - VALID_SCOPES
    if bad:
        raise ValueError(
            f"unknown --scope value(s) {sorted(bad)}; valid: "
            f"{sorted(VALID_SCOPES)} or 'all' (comma-list)"
        )
    return toks


def _raw_dirs_from_guidelines(ai_work: Path) -> list[str]:
    """Extract the project-internal directory list from the 'Raw search fallback'
    table in document_search_guidelines.md (CR-AIWS-2026-06-052). Each first-column
    backtick-quoted path is a directory to Glob/Grep. Returns [] if the doc is absent.
    """
    doc = ai_work / "wiki" / "reference" / "document_search_guidelines.md"
    if not doc.exists():
        return []
    text = doc.read_text(encoding="utf-8")
    m = re.search(r"##\s+Raw search fallback.*?(?=\n##\s|\Z)", text, re.S)
    section = m.group(0) if m else text
    dirs: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        bt = re.match(r"`([^`]+)`", cells[0])
        if bt:
            d = bt.group(1).strip()
            if d and d not in dirs:
                dirs.append(d)
    return dirs


def _raw_search(query: str, qtokens: set[str], ai_work: Path,
                project_root: Path, limit: int) -> list[dict]:
    """Authorization-gated raw (un-registered) fallback (CR-AIWS-2026-06-052).

    Glob/grep the project-internal dirs listed in document_search_guidelines.md.
    Match by filename-token overlap first, then a light content substring grep.
    Results are labelled 'unregistered' and ranked below any registered hit
    (the caller renders them in a separate, lower block).
    """
    results: list[dict] = []
    seen: set[str] = set()
    q = query.lower()
    for d in _raw_dirs_from_guidelines(ai_work):
        base = project_root / d
        if not base.exists() or not base.is_dir():
            continue
        for fp in base.rglob("*.md"):
            if not fp.is_file():
                continue
            try:
                rel = fp.relative_to(project_root).as_posix()
            except ValueError:
                rel = fp.as_posix()
            if rel in seen:
                continue
            name_tokens = {t.lower() for t in _tokens(fp.stem)}
            score = 2 * len(qtokens & name_tokens)
            if score == 0:
                try:
                    if q and q in fp.read_text(encoding="utf-8", errors="ignore").lower():
                        score = 1
                except OSError:
                    continue
            if score > 0:
                seen.add(rel)
                results.append({
                    "score": score,
                    "source_id": f"unregistered:{rel}",
                    "title": fp.stem,
                    "artifact_locator": rel,
                    "match_reason": "raw (un-registered) artifact — Glob/Grep fallback; "
                                    "register via /build-wiki-source-meta if reused",
                    "recommended_next_action": "open_source_for_evidence",
                    "runtime_boundary": "unregistered raw hit; ranked below registered index results",
                    "unregistered": True,
                })
    results.sort(key=lambda r: -r["score"])
    return results[:limit]


def _apply_status_penalty(score: float, rec: dict, include_inactive: bool) -> float:
    """Apply ranking penalty for non-active entries unless include_inactive is set."""
    if include_inactive:
        return score
    if rec.get("status") == "superseded":
        return score * SUPERSEDED_PENALTY
    return score


def _score(rec: dict, query: str, qtokens: set[str]) -> int:
    """Lexical score: whole-query substring matching with underscore/hyphen normalization."""
    score = 0
    q = query.lower()
    q_norm = q.replace("_", " ").replace("-", " ")
    if rec.get("source_id", "").lower() == q:
        score += 100
    if q in rec.get("source_id", "").lower():
        score += 20
    if q in rec.get("title", "").lower():
        score += 15
    for k in rec.get("lookup_keys", []) or []:
        kl = k.lower()
        kl_norm = kl.replace("_", " ").replace("-", " ")
        if kl == q or kl_norm == q_norm:
            score += 12
        elif q in kl or kl in q or q_norm in kl_norm or kl_norm in q_norm:
            score += 4
    path_tokens = {t.lower() for t in _tokens(rec.get("artifact_locator", ""))}
    score += 3 * len(qtokens & path_tokens)
    if q in (rec.get("summary_short", "") or "").lower():
        score += 2
    return score


def _score_semantic(rec: dict, qtokens: set[str]) -> int:
    """Semantic score: per-token bag-of-words matching.

    Each query token is matched independently against lookup_keys, title,
    summary, and source_id. Handles multi-word queries and concept-level
    retrieval — a query like 'file màn hình định nghĩa' matches entries
    that have any of those tokens in their lookup_keys.
    """
    if not qtokens:
        return 0
    score = 0
    rec_keys = {k.lower() for k in (rec.get("lookup_keys", []) or [])}
    key_tokens: set[str] = set()
    for k in rec_keys:
        key_tokens.update(_tokens(k))
    title_tokens = {t.lower() for t in _tokens(rec.get("title", ""))}
    summary = (rec.get("summary_short", "") or "").lower()
    sid = rec.get("source_id", "").lower()

    matched = 0
    for qt in qtokens:
        if len(qt) < 2:
            continue
        if qt in key_tokens:
            score += 8
            matched += 1
        elif any(qt in k or k in qt for k in rec_keys):
            score += 4
            matched += 1
        if qt in title_tokens:
            score += 5
        if qt in summary:
            score += 3
        if qt in sid:
            score += 2

    # Bonus for high token coverage (≥ half of query tokens matched)
    if matched >= max(1, len(qtokens) // 2):
        score += matched * 3

    return score



def _runtime_entry(score: int, rec: dict) -> dict:
    """Return lookup result with explicit runtime boundary fields.

    Lookup result is a route/context candidate, not evidence verification.
    """
    representation_status = rec.get("source_representation_status") or rec.get("representation_status") or ""
    recommended = "open_source_for_evidence"
    if representation_status in {"partial", "needs_review"}:
        recommended = "request_human_check"
    elif representation_status == "failed":
        recommended = "request_reconversion"
    elif representation_status == "unknown":
        recommended = "check_representation_quality"

    return {
        "score": score,
        "source_id": rec.get("source_id", ""),
        "title": rec.get("title", ""),
        "summary_short": rec.get("summary_short", ""),
        "source_type": rec.get("source_type", ""),
        "status": rec.get("status", ""),
        "authority_level": rec.get("authority_level", ""),
        "freshness_status": rec.get("freshness_status", ""),
        "promotion_status": rec.get("promotion_status", ""),
        "source_representation_status": representation_status,
        "source_representation_caution": rec.get("source_representation_caution", ""),
        "index_entry": rec,
        "meta_locator": rec.get("meta_locator", ""),
        "artifact_locator": rec.get("artifact_locator", ""),
        "original_source_locator": rec.get("original_source_locator", ""),
        "representation_locator": rec.get("representation_locator", rec.get("artifact_locator", "")),
        "representation_type": rec.get("representation_type", ""),
        "conversion_method": rec.get("conversion_method", ""),
        "conversion_limitations": rec.get("conversion_limitations", []),
        "intended_ai_use": rec.get("intended_ai_use", ""),
        "match_reason": "matched Wiki Source Index entry; open AIWS-readable representation for verification",
        "recommended_next_action": recommended,
        "runtime_boundary": "lookup result is a candidate source route, not evidence verification",
    }


def _print_raw_fallback_hint(query: str) -> None:
    print("─" * 60)
    print("Hint — Not in index. Raw fallback required:")
    print(f"  1. Retry    : --mode semantic (if this was lexical)")
    print(f"  2. Raw search: check document_search_guidelines.md for artifact dirs,")
    print(f"                 then Glob/Grep '{query}' in those directories")
    print(f"  3. If no guidelines: ask HUMAN for artifact directory locations,")
    print(f"                 then promote to document_search_guidelines.md")
    print(f"  4. If found  : register source with /build-wiki-source-meta")
    print(f"  ❌ Do NOT report 'not found' without completing steps 1–3")
    print()
    print("If artifact is reusable (template / process doc / shared spec / guideline):")
    print(f"  → Mark in AIP input table : Capture flag = [retrieval_gap]")
    print(f"  → Add entry to AIP section: ## Pre-flight Pending Captures")
    print(f"  → After task              : register via /register-wiki-source")
    print("─" * 60)


def main() -> int:
    p = argparse.ArgumentParser(description="Lookup wiki source via index")
    p.add_argument("--query", required=True)
    p.add_argument("--mode", choices=["lexical", "id", "path", "semantic"],
                   default="lexical")
    p.add_argument("--index", help="Override index path (comma-separated for multiple)")
    p.add_argument("--scope", default=DEFAULT_SCOPE, metavar="LIST",
                   help="Comma-list of registered indices to search: project,local,aiws (combinable). "
                        f"Default '{DEFAULT_SCOPE}' — 'local' is rule-#11-gated (opt-in; requires "
                        "--authorized). 'all' = project,local,aiws. 'aiws' = the pre-built AIWS "
                        "methodology wiki shipped on install (index.aiws.jsonl).")
    p.add_argument("--include-raw", choices=["off", "on-empty", "always"], default="off",
                   help="Un-registered (raw) Glob/Grep fallback over project dirs in "
                        "document_search_guidelines.md (CR-AIWS-2026-06-052). off (default) | "
                        "on-empty (fires only for an object lookup with 0 registered hits) | "
                        "always. Any value != off REQUIRES --authorized.")
    p.add_argument("--authorized", choices=["human", "aip", "agent-rule"], default=None,
                   help="Authorization source for raw / beyond-default-scope search "
                        "(CR-AIWS-2026-06-052). REQUIRED when --include-raw != off OR --scope "
                        "extends beyond project,aiws. Absent → the tool refuses (halt-and-ask; "
                        "never silent raw, never silent miss for an object lookup).")
    p.add_argument("--lookup-mode", choices=["object", "concept"], default="concept",
                   help="object = a precise artifact/object lookup (enables the on-empty raw "
                        "fallback); concept = a fuzzy keyword/concept query (default; no on-empty raw).")
    p.add_argument("--limit", "--top", type=int, default=20,
                   dest="limit", metavar="N",
                   help="Max results to return (default: 20)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--slim", dest="slim", action="store_true", default=True,
                   help="One line per result (routing fields only: score, source_id, title, "
                        "source_type, status, artifact_locator, source_representation_status, "
                        "recommended_next_action, meta_locator). This is the DEFAULT; pass --full to opt out.")
    p.add_argument("--full", "--no-slim", dest="slim", action="store_false",
                   help="Verbose multi-line records per result (summary / authority / "
                        "representation fields inline). Opt out of the default slim output.")
    p.add_argument("--include-inactive", action="store_true", default=False,
                   help="Include superseded sources at full score (default: penalized at 0.2x)")
    p.add_argument("--source-type", action="append", default=None, metavar="TYPE",
                   help="Optional: keep only results whose source_type matches (repeatable or comma-list, "
                        "e.g. --source-type process_guideline,process_template). Applied AFTER matching — "
                        "does not change scoring; omitted = no filter. Bridge from Task Lens relevant_reference_types: "
                        "*_template->process_template, *_guideline/*_checklist/naming_convention->process_guideline, sop->sop.")
    p.add_argument("--excludes", "--exclude", dest="excludes", default="", metavar="IDS",
                   help="Comma-separated source_ids to drop before scoring (already-checked entries). "
                        "Pair with the has_more footer to fetch the next batch without re-seeing prior hits.")
    p.add_argument("--system", default=None, metavar="ID",
                   help="Multi-system scoping (CR-AIWS-2026-06-017): restrict to this system's docs + common docs. "
                        "In a multi_system project you MUST pass --system or --all-systems (no silent default).")
    p.add_argument("--all-systems", dest="all_systems", action="store_true", default=False,
                   help="Multi-system scoping: search across ALL systems (explicit opt-out of system scoping).")
    ns = p.parse_args()

    # Scope parsing + authorization gate (CR-AIWS-2026-06-052). Raw search OR a scope that
    # extends beyond the project,aiws default requires an explicit authorization source —
    # otherwise the tool refuses (halt-and-ask; never silent raw, never silent broad search).
    try:
        scope_set = _parse_scope(ns.scope)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    raw_requested = ns.include_raw != "off"
    scope_beyond_default = bool(scope_set - {"project", "aiws"})
    if (raw_requested or scope_beyond_default) and not ns.authorized:
        reasons = []
        if raw_requested:
            reasons.append(f"--include-raw={ns.include_raw}")
        if scope_beyond_default:
            reasons.append(f"--scope includes {sorted(scope_set - {'project', 'aiws'})}")
        print("error: " + " and ".join(reasons) + " requires --authorized {human|aip|agent-rule}. "
              "Raw / beyond-default-scope search is never silent — name the authorization source "
              "(HUMAN in conversation, the active AIP's allow_raw_search, or a standing agent rule) "
              "or STOP and ask HUMAN.", file=sys.stderr)
        return 2

    project_root = find_ai_work_root(Path.cwd())
    ai_work = project_root / ".ai-work"
    wiki_sources = ai_work / "wiki_sources"

    # Multi-system scoping (CR-AIWS-2026-06-017). HARD-REQUIRE (HUMAN-confirmed 2026-06-15):
    # in a multi_system project, refuse to search un-scoped — NO silent default, NO auto-pick.
    cfg = _project_config(ai_work)
    active_system = None
    if cfg["multi_system"]:
        if ns.all_systems:
            active_system = None                     # explicit: search all systems
        elif ns.system:
            active_system = ns.system.strip()
            if cfg["systems"] and active_system not in cfg["systems"]:
                print(f"error: --system {active_system!r} is not in this project's systems "
                      f"{cfg['systems']}.", file=sys.stderr)
                return 2
        else:
            print("error: this is a multi_system project — you MUST pass --system <id> "
                  "(restrict to that system + common docs) or --all-systems (search all). "
                  "Refusing to search un-scoped to avoid cross-system spec bleed; no silent default. "
                  f"Valid systems: {', '.join(cfg['systems']) or '(see project_profile.yml)'}",
                  file=sys.stderr)
            return 2
    # single-system project (multi_system:false / no project_profile.yml) → no scoping; flags ignored.

    if ns.index:
        index_paths = [Path(p).resolve() for p in ns.index.split(",")]
    else:
        index_paths = []
        if "project" in scope_set:
            index_paths.append(wiki_sources / "index.jsonl")
        if "local" in scope_set:
            local_idx = wiki_sources / "index.local.jsonl"
            if local_idx.exists():
                index_paths.append(local_idx)
        if "aiws" in scope_set:
            aiws_idx = wiki_sources / "index.aiws.jsonl"
            if aiws_idx.exists():
                index_paths.append(aiws_idx)

    index_paths = [p for p in index_paths if p.exists()]
    if not index_paths:
        print("error: no index file found", file=sys.stderr)
        return 2

    records: list[dict] = []
    for idx_path in index_paths:
        records.extend(read_jsonl(idx_path))
    exclude_ids = {e.strip() for e in (ns.excludes or "").split(",") if e.strip()}
    if exclude_ids:
        records = [r for r in records if r.get("source_id") not in exclude_ids]
    q = ns.query
    qtokens = {t.lower() for t in _tokens(q)}

    include_inactive = ns.include_inactive

    if ns.mode == "id":
        matches = [r for r in records if r.get("source_id") == q]
        scored = [(100, r) for r in matches]
    elif ns.mode == "path":
        scored = []
        for r in records:
            pt = {t.lower() for t in _tokens(r.get("artifact_locator", ""))}
            hit = len(qtokens & pt)
            if hit:
                scored.append((hit * 10, r))
    elif ns.mode == "semantic":
        scored = [(s, r) for r in records if (s := _score_semantic(r, qtokens)) > 0]
    else:  # lexical
        scored = [(s, r) for r in records if (s := _score(r, q, qtokens)) > 0]

    if ns.source_type:
        wanted = {s.strip().lower() for item in ns.source_type for s in item.split(",") if s.strip()}
        scored = [(s, r) for s, r in scored if r.get("source_type", "").lower() in wanted]

    # Multi-system filter (CR-AIWS-2026-06-017): keep the active system's docs + common docs
    # (common = no `system` field). active_system is None when single-system or --all-systems.
    if active_system is not None:
        scored = [(s, r) for s, r in scored if _in_system(r, active_system)]

    scored = [(_apply_status_penalty(s, r, include_inactive), r) for s, r in scored]
    scored.sort(key=lambda sr: -sr[0])
    total_matches = len(scored)
    scored = scored[: ns.limit]
    has_more = total_matches > len(scored)

    results = [_runtime_entry(s, r) for s, r in scored]

    # Raw (un-registered) tier (CR-AIWS-2026-06-052) — authorization-gated, ranked below registered.
    # Fires when authorized AND (include-raw=always) OR (include-raw=on-empty + object lookup + 0 registered hits).
    raw_results: list[dict] = []
    if ns.authorized and (
        ns.include_raw == "always"
        or (ns.include_raw == "on-empty" and ns.lookup_mode == "object" and total_matches == 0)
    ):
        raw_results = _raw_search(q, qtokens, ai_work, project_root, ns.limit)

    if ns.format == "json":
        payload = {"matches": [], "has_more": has_more,
                   "total_matches": total_matches, "shown": len(results)}
        if raw_results:
            payload["unregistered"] = [
                {"score": r["score"], "source_id": r["source_id"], "title": r["title"],
                 "artifact_locator": r["artifact_locator"], "match_reason": r["match_reason"]}
                for r in raw_results
            ]
        if not results:
            if not raw_results:
                payload["raw_fallback_hint"] = (
                    "Not in index. Retry --mode semantic, then raw search in artifact dirs "
                    "(see document_search_guidelines.md or ask HUMAN)."
                )
            print(json.dumps(payload, ensure_ascii=False))
        elif ns.slim:
            payload["matches"] = [{"score": r["score"], "source_id": r.get("source_id", ""),
                     "title": r.get("title", ""), "source_type": r.get("source_type", ""),
                     "status": r.get("status", ""),
                     "artifact_locator": r.get("artifact_locator", ""),
                     "source_representation_status": r.get("source_representation_status", ""),
                     "recommended_next_action": r.get("recommended_next_action", ""),
                     "meta_locator": r.get("meta_locator", "")} for r in results]
            print(json.dumps(payload, ensure_ascii=False))
        else:
            payload["matches"] = results
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Note: lookup-wiki-source returns candidate source routes; open source artifact for evidence.")
        if not scored and not raw_results:
            print("(no matches)")
            _print_raw_fallback_hint(ns.query)
        elif not scored:
            print("(no registered matches — see unregistered raw candidates below)")
        for item in results:
            _status_tag = " [SUPERSEDED]" if item.get("status") == "superseded" else ""
            if ns.slim:
                _rep = item.get("source_representation_status", "")
                _rep_tag = f" [rep:{_rep}]" if _rep in {"partial", "needs_review", "failed", "unknown"} else ""
                print(f"[{item['score']:>3}] {item.get('source_id', '')}{_status_tag}{_rep_tag}  "
                      f"{item.get('title', '')} | {item.get('source_type', '')} | "
                      f"artifact={item.get('artifact_locator', '')} | "
                      f"meta={item.get('meta_locator', '')}")
                continue
            print(f"[{item['score']:>3}] {item.get('source_id', '')}{_status_tag}  {item.get('title', '')}")
            _summary = (item.get("summary_short") or "").strip().lstrip("> ").strip()
            if _summary and not _summary.startswith(("Project:", "Date:", "Status:", "Version:")):
                print(f"       summary: {_summary}")
            print(f"       type={item.get('source_type', '')}  status={item.get('status', '')}")
            if item.get("authority_level") or item.get("promotion_status"):
                print(f"       authority={item.get('authority_level', '')}  promotion={item.get('promotion_status', '')}")
            if item.get("source_representation_status"):
                print(f"       representation={item.get('source_representation_status', '')}")
            if item.get("source_representation_caution"):
                print(f"       caution: {item.get('source_representation_caution', '')}")
            if item.get("intended_ai_use"):
                print(f"       use-hint: {item.get('intended_ai_use', '')}")
            print(f"       artifact: {item.get('artifact_locator', '')}")
            if item.get("representation_locator"):
                print(f"       representation: {item.get('representation_locator', '')}")
            if item.get("original_source_locator"):
                print(f"       original: {item.get('original_source_locator', '')}")
            if item.get("conversion_limitations"):
                print(f"       limitations: {item.get('conversion_limitations', '')}")
            print(f"       meta:     {item.get('meta_locator', '')}")
            print(f"       next:     {item.get('recommended_next_action', '')}")
        if has_more:
            _seen = ",".join(item.get("source_id", "") for item in results if item.get("source_id"))
            print(f"… {total_matches - len(results)} more match(es) not shown "
                  f"(showing {len(results)} of {total_matches}). "
                  f"If current hits are insufficient, re-run with --excludes \"{_seen}\" "
                  f"to fetch the next batch (or raise --limit). Continuing is your call.")
        if scored:
            print("Enumerate one kind: --source-type <type> --slim  (e.g. function | table | process_guideline)")
        if raw_results:
            print("─" * 60)
            print(f"Unregistered (raw) candidates — authorized={ns.authorized}; "
                  f"ranked below registered, NOT in index:")
            for r in raw_results:
                print(f"[{r['score']:>3}] {r['source_id']}  artifact={r['artifact_locator']}")
            print("  → open directly for this task; register via /build-wiki-source-meta if reused.")
    return 0 if (scored or raw_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
