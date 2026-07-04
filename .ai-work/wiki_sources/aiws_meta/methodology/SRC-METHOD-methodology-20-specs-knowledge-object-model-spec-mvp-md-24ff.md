---
artifact_type: wiki_source_meta
source_id: SRC-METHOD-methodology-20-specs-knowledge-object-model-spec-mvp-md-24ff
title: methodology / 20_specs/Knowledge_Object_Model_Spec_MVP.md
source_type: methodology_spec
artifact_locator: .ai-work/truth/canonical/methodology/20_specs/Knowledge_Object_Model_Spec_MVP.md
profile_id: methodology_spec
status: active
updated_at: 2026-06-20T03:05:33.682277+00:00
authority_level: unknown
freshness_status: unknown
promotion_status: draft
source_representation_status: unknown
source_representation_caution: Representation quality has not been reviewed.
knowledge_value: unknown
intended_ai_use: unknown
representation_type: markdown
conversion_method: unknown
conversion_limitations: []
system: aiws
---
# Wiki Source Meta — methodology / 20_specs/Knowledge_Object_Model_Spec_MVP.md

## Summary
Canonical MVP spec for the knowledge unit in the 2-layer model (rewritten v0.2, CR-AIWS-2026-05-020). The artifact-level meta is the knowledge unit; canonical identity / aliases / multi-language + natural-language resolution live in the meta's lookup_keys; cross-artifact relationships are expressed via the `## Related Sources` section (typed roles). The first-class Knowledge Object record (Layer 2) and expansion_links were removed (CR-AIWS-2026-05-005). AI use: reference for how knowledge is identified, routed, and expanded without a separate object layer.

## Knowledge Targets
- reference
- domain
- pattern

## Lookup Keys
- object
- meta
- node
- artifact
- kind
- Object
- INV
- SRC
- Knowledge
- Sources
- Related
- source_id
- knowledge
- bis
- identity
- model
- node_kind
- layer
- jsonl
- Layer
- aliases
- AIWS
- unit
- core
- object_id
- objects
- metas
- file
- lookup_keys
- F03
- product
- two
- record
- AIP
- never
- concept
- source
- HUMAN
- domain
- FUNC

## Source-Specific Hints
- heading: Knowledge Unit Model Spec for AI Work System MVP
- heading: 1. Purpose of this spec
- heading: 2. Mô hình 2-layer + two-kind node
- heading: 2.1. Đơn vị tri thức = meta (node_kind: artifact | object)
- heading: 2.2. Object node = POINTER, KHÔNG phải container (hard invariant — SHAPE 2 forbidden)
- heading: 3. Identity, naming, và natural-language resolution
- heading: 3bis. Knowledge Object discovery & identity extraction
- heading: 3bis.1. Object Kind Catalog (canonical-but-extensible)
- heading: 3bis.2. Identity (NO object_id — identity = source_id)
- heading: 3bis.3. source_id lifecycle (synthesized core)
- heading: 3bis.4. Discovery hints (heuristic)
- heading: 3bis.5. Inference contract + necessity test (MVP, inference-first)
- heading: 3bis.6. Relations của object node (3 registers — DP4)
- heading: 4. Quan hệ & expansion = `## Related Sources`
- heading: 5. Design goals (intent giữ nguyên, đặt trên substrate 2-layer two-kind node)
- heading: 6. Quan hệ với Working AIP / Use Case
- heading: 7. Cross-references
