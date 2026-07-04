#!/usr/bin/env python3
"""INV-5 acceptance test — an object source_id resolves as BOTH relation endpoints.

CR-AIWS-2026-05-023 (two-kind node model) INV-5 ("read-by-named-consumer"):

    wiki_relations.py resolves an object source_id as BOTH an out- and an in-edge
    endpoint; this test MUST pass BEFORE any object meta is authored.

It is the HARD PRECONDITION gate for the object-enabling tooling/lint guards
(AIP-EXEC-049 STEP-01). If it fails, STOP — do not trust the object guards.

How it works (hermetic — no real wiki_sources/ is touched; objects are NOT yet
authored in the live store, per DP6 + the object-authoring gate):

  * Writes fixture metas to a temp dir:
      - SRC-FUNC-FIXTURE  (node_kind=object, artifact_locator=__OBJECT__) declaring
          - x:calls         -> SRC-FUNC-FIXTURE-CALLEE   (domain OUT-edge, object->object)
          - represented_by  -> SRC-BD-FIXTURE            (representation, object-side)
      - SRC-BD-FIXTURE    (artifact) declaring
          - represents      -> SRC-FUNC-FIXTURE          (representation, doc-side)
  * Builds the projection through build_relations.build_relations (exactly what
    `wiki_relations.py --rebuild` delegates to) and drives wiki_relations.cmd_relations
    (exactly what `wiki_relations.py --relations <id>` runs).
  * Asserts SRC-FUNC-FIXTURE appears as source_ref of >=1 edge (## out) AND as
    target_ref of >=1 edge (## in) — i.e. it is resolved as BOTH endpoints.

The out-edge proves the domain register works object->object; the in-edge proves the
representation register's reverse/impact view ("everything about F03") resolves AT the
object — the two failure modes that killed the retired KO are structurally closed.

Exit codes: 0 pass · 1 fail (INV-5 not satisfied) · 2 error.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_relations as br  # noqa: E402  (the projection builder = the named consumer's core)
import wiki_relations as wr  # noqa: E402   (the named consumer: --relations / --rebuild)
from _common import (  # noqa: E402
    extract_sections,
    parse_frontmatter,
    read_text,
    write_jsonl,
)

OBJ_ID = "SRC-FUNC-FIXTURE"
CALLEE_ID = "SRC-FUNC-FIXTURE-CALLEE"
DOC_ID = "SRC-BD-FIXTURE"

OBJECT_META = """\
---
source_id: SRC-FUNC-FIXTURE
title: "Fixture Function (INV-5 acceptance-test object)"
node_kind: object
source_type: function
artifact_locator: __OBJECT__
meta_locator: "(fixture)"
authority_level: reference
status: active
summary_short: "Hermetic fixture object meta for the INV-5 named-consumer test; not real knowledge."
lookup_keys:
  - fixture function
  - INV-5 test object
---

# Fixture Function (INV-5 acceptance-test object)

## Summary
Fixture function-kind Knowledge Object for the INV-5 named-consumer acceptance test.
It declares a domain out-edge (x:calls) and is represented_by a design document, so the
relations consumer resolves it as BOTH an out- and an in-edge endpoint.

## Related Sources
- **SRC-FUNC-FIXTURE-CALLEE** — role: x:calls — fixture domain out-edge (object -> object)
- **SRC-BD-FIXTURE** — role: represented_by — fixture BD document describes this function
"""

DOC_META = """\
---
source_id: SRC-BD-FIXTURE
title: "Fixture Basic Design (INV-5 acceptance-test artifact)"
source_type: basic_design
artifact_locator: "(fixture)/SRC-BD-FIXTURE.md"
meta_locator: "(fixture)"
authority_level: reference
status: active
summary_short: "Hermetic fixture artifact meta that represents the fixture object; not real knowledge."
---

# Fixture Basic Design (INV-5 acceptance-test artifact)

## Summary
Fixture design document that describes (represents) the fixture function object.

## Related Sources
- **SRC-FUNC-FIXTURE** — role: represents — fixture BD describes the fixture function object
"""

FIXTURE_INDEX = [
    {"source_id": OBJ_ID, "title": "Fixture Function", "authority_level": "reference", "status": "active"},
    {"source_id": CALLEE_ID, "title": "Fixture Callee", "authority_level": "reference", "status": "active"},
    {"source_id": DOC_ID, "title": "Fixture Basic Design", "authority_level": "reference", "status": "active"},
]


def _check_object_shape(meta_path: Path) -> list[str]:
    """Sanity-check the fixture object meta shape (node_kind / __OBJECT__ / >=1 out-edge)."""
    problems: list[str] = []
    meta, body = parse_frontmatter(read_text(meta_path))
    if meta.get("node_kind") != "object":
        problems.append("fixture object meta missing node_kind: object")
    if meta.get("artifact_locator") != "__OBJECT__":
        problems.append("fixture object meta missing artifact_locator: __OBJECT__ (INV-9)")
    section = extract_sections(body).get("Related Sources", "")
    if not br.parse_related_sources(section):
        problems.append("fixture object meta declares no out-edge (INV-4 requires >=1)")
    return problems


def run() -> int:
    with tempfile.TemporaryDirectory(prefix="inv5_object_") as td:
        tmp = Path(td)
        meta_dir = tmp / "meta"
        meta_dir.mkdir()
        obj_path = meta_dir / f"{OBJ_ID}.md"
        obj_path.write_text(OBJECT_META, encoding="utf-8")
        (meta_dir / f"{DOC_ID}.md").write_text(DOC_META, encoding="utf-8")
        index_path = tmp / "index.jsonl"
        write_jsonl(index_path, FIXTURE_INDEX)
        rel_path = tmp / "relations.jsonl"

        # 0. fixture object shape sanity (INV-9 / INV-4)
        shape_problems = _check_object_shape(obj_path)

        # 1. build the projection — exactly what `wiki_relations.py --rebuild` delegates to
        edges, warnings = br.build_relations(meta_dir, index_path)
        write_jsonl(rel_path, edges)

        # 2. drive the named consumer — exactly what `wiki_relations.py --relations <id>` runs
        print("=== wiki_relations.py --relations evidence ===")
        idx = wr._load_index(index_path)
        rc = wr.cmd_relations(OBJ_ID, rel_path, idx)
        print("=" * 47)

        # 3. decide INV-5 with the SAME predicate cmd_relations uses (wiki_relations.py L63-64)
        out_edges = [e for e in edges if e.get("source_ref") == OBJ_ID]
        in_edges = [e for e in edges if e.get("target_ref") == OBJ_ID]

    # ── report ──────────────────────────────────────────────────────────────
    problems = list(shape_problems)
    if rc != 0:
        problems.append(f"wiki_relations.cmd_relations returned {rc} (expected 0)")
    if not out_edges:
        problems.append(f"{OBJ_ID} did NOT resolve as an out-edge endpoint (## out empty)")
    if not in_edges:
        problems.append(f"{OBJ_ID} did NOT resolve as an in-edge endpoint (## in empty)")
    broken = [w for w in warnings if "[BROKEN REF]" in w]
    if broken:
        problems.append("unexpected broken refs in fixture: " + "; ".join(broken))

    print()
    print(f"INV-5 object named-consumer test for {OBJ_ID}:")
    print(f"  out-edges (## out): {len(out_edges)}  -> {[(e['relationship_type'], e['target_ref']) for e in out_edges]}")
    print(f"  in-edges  (## in) : {len(in_edges)}  -> {[(e['source_ref'], e['relationship_type']) for e in in_edges]}")
    if problems:
        print("\n[FAIL] INV-5 NOT satisfied:")
        for p in problems:
            print(f"  - {p}")
        print("\nSummary: 0/1 PASS  1 FAIL  [FAIL]")
        return 1
    print("\n[PASS] object resolves as BOTH an out- and an in-edge endpoint (INV-5).")
    print("Summary: 1/1 PASS  0 FAIL  [OK]")
    return 0


def main() -> int:
    try:
        return run()
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
