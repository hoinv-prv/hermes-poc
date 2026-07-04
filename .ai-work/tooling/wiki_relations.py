#!/usr/bin/env python3
"""Query the Wiki Relations edge layer (opt-in, one-hop).

Given a node (source_id), return its relations so AI can expand from a confirmed
source WITHOUT reopening raw artifacts or running fragile repo-wide grep:

    --relations <id>   query relations.jsonl → `## out` (id → others) + `## in`
                       (others → id, the REVERSE / impact view). Bidirectional.
    --expand <id>      read that meta's `## Related Sources` out-edges directly
                       (authoritative), resolve each target against the index.
    --rebuild          regenerate relations.jsonl from metas (delegates to build_relations).

This is a ONE-HOP query over a rebuilt projection — NOT a graph engine, NOT
transitive closure (Knowledge_Relationship Spec §5 "no precomputed global graph").
Default invocation does NOTHING unless a relation param is given (additive; no impact
on lookup_wiki_source.py, which stays the discovery tool). CR-AIWS-2026-05-022.

Runtime flow: lookup_wiki_source.py (discovery) → open meta (confirm file + read its
`## Related Sources`) → IF the intent needs impact / what-feeds-this / neighbours:
wiki_relations.py --relations <id> for the reverse view the meta cannot provide.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_relations as br  # noqa: E402  (reuse the parser + builder; same tooling dir)
from _common import (  # noqa: E402
    find_ai_work_root,
    read_jsonl,
    read_text,
    resolve_locator,
    write_jsonl,
)


def _load_index(index_path: Path) -> dict[str, dict]:
    return {r.get("source_id", ""): r for r in read_jsonl(index_path)} if index_path.exists() else {}


def _node_tag(idx: dict[str, dict], source_id: str) -> str:
    """[authority/status] tag for a node, or [BROKEN REF] when not in the index."""
    rec = idx.get(source_id)
    if rec is None:
        return "[BROKEN REF]"
    auth = rec.get("authority_level", "?")
    status = rec.get("status", "?")
    return f"[{auth}/{status}]"


def _title(idx: dict[str, dict], source_id: str) -> str:
    rec = idx.get(source_id)
    return rec.get("title", "") if rec else ""


def cmd_relations(source_id: str, rel_path: Path, idx: dict[str, dict]) -> int:
    if not rel_path.exists():
        print(f"error: {rel_path} not found — run: wiki_relations.py --rebuild", file=sys.stderr)
        return 2
    edges = read_jsonl(rel_path)
    out_edges = [e for e in edges if e.get("source_ref") == source_id]
    in_edges = [e for e in edges if e.get("target_ref") == source_id]

    title = _title(idx, source_id)
    head = f"relations for {source_id}" + (f"  ({title})" if title else "")
    if source_id not in idx:
        head += "  [NOTE: node not in index]"
    print(head)
    print()

    print(f"## out  ({source_id} → others)")
    if not out_edges:
        print("  (none)")
    for e in out_edges:
        tgt = e.get("target_ref", "")
        conf = e.get("relationship_confidence_note", "asserted")
        note = e.get("relationship_basis_note", "")
        line = f"  - {e.get('relationship_type','')} → {tgt}  {_node_tag(idx, tgt)} ({conf})"
        if note:
            line += f"  — {note}"
        print(line)

    print()
    print(f"## in  (others → {source_id})   [reverse / impact]")
    if not in_edges:
        print("  (none)")
    for e in in_edges:
        src = e.get("source_ref", "")
        conf = e.get("relationship_confidence_note", "asserted")
        note = e.get("relationship_basis_note", "")
        line = f"  - {src} --{e.get('relationship_type','')}-->  {_node_tag(idx, src)} ({conf})"
        if note:
            line += f"  — {note}"
        print(line)
    return 0


def cmd_expand(source_id: str, idx: dict[str, dict], project_root: Path) -> int:
    rec = idx.get(source_id)
    if rec is None:
        print(f"error: {source_id} not found in index", file=sys.stderr)
        return 2
    meta_loc = rec.get("meta_locator", "")
    if not meta_loc:
        print(f"error: {source_id} has no meta_locator in index", file=sys.stderr)
        return 2
    meta_path = resolve_locator(meta_loc, project_root)
    if not meta_path.exists():
        print(f"error: meta file not found: {meta_path}", file=sys.stderr)
        return 2

    from _common import parse_frontmatter, extract_sections
    _meta, body = parse_frontmatter(read_text(meta_path))
    section = extract_sections(body).get("Related Sources", "")
    edges = br.parse_related_sources(section)

    title = _title(idx, source_id)
    print(f"out-edges declared in {source_id} meta" + (f"  ({title})" if title else ""))
    print(f"  (authoritative; from ## Related Sources of {meta_path.name})")
    if not edges:
        print("  (none — meta has no resolved ## Related Sources entries)")
    for e in edges:
        tgt = e["target_ref"]
        line = f"  - {e['relationship_type']} → {tgt}  {_node_tag(idx, tgt)} ({e['relationship_confidence_note']})"
        if e["relationship_basis_note"]:
            line += f"  — {e['relationship_basis_note']}"
        print(line)
    return 0


def cmd_rebuild(ai_work: Path, meta_dir: Path, index_path: Path, rel_path: Path) -> int:
    records, warnings = br.build_relations(meta_dir, index_path)
    write_jsonl(rel_path, records)
    br._write_relations_rebuild_log(ai_work, rel_path, len(records))
    for w in warnings:
        print(f"  WARN  {w}", file=sys.stderr)
    print(f"rebuilt {len(records)} edges → {rel_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Query the Wiki Relations edge layer (opt-in, one-hop). "
                    "Default does nothing unless a relation param is given.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--relations", metavar="SOURCE_ID",
                   help="print out-edges + in-edges (reverse/impact) from relations.jsonl")
    g.add_argument("--expand", metavar="SOURCE_ID",
                   help="print the meta's ## Related Sources out-edges (authoritative)")
    g.add_argument("--rebuild", action="store_true", help="regenerate relations.jsonl from metas")
    p.add_argument("--relations-file", help="override relations.jsonl path")
    p.add_argument("--index", help="override index.jsonl path")
    p.add_argument("--meta-dir", help="override meta dir (for --rebuild)")
    ns = p.parse_args()

    project_root = find_ai_work_root(Path.cwd())
    ai_work = project_root / ".ai-work"
    rel_path = Path(ns.relations_file).resolve() if ns.relations_file else (ai_work / "wiki_sources" / "relations.jsonl")
    index_path = Path(ns.index).resolve() if ns.index else (ai_work / "wiki_sources" / "index.jsonl")
    meta_dir = Path(ns.meta_dir).resolve() if ns.meta_dir else (ai_work / "wiki_sources" / "meta")

    if ns.rebuild:
        return cmd_rebuild(ai_work, meta_dir, index_path, rel_path)

    idx = _load_index(index_path)
    if ns.relations:
        return cmd_relations(ns.relations, rel_path, idx)
    if ns.expand:
        return cmd_expand(ns.expand, idx, project_root)

    # additive / opt-in: no relation param → do nothing but show usage
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
