---
artifact_type: wiki_source_meta
source_id: SRC-METHOD-methodology-20-specs-knowledge-expansion-link-spec-mvp-md-f5f8
title: methodology / 20_specs/Knowledge_Expansion_Link_Spec_MVP.md
source_type: methodology_spec
artifact_locator: .ai-work/truth/canonical/methodology/20_specs/Knowledge_Expansion_Link_Spec_MVP.md
profile_id: methodology_spec
status: active
updated_at: 2026-06-01T10:10:53.434733+00:00
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
# Wiki Source Meta — methodology / 20_specs/Knowledge_Expansion_Link_Spec_MVP.md

## Summary
Canonical MVP spec for cross-artifact relationships in the 2-layer model (rewritten v0.3, CR-AIWS-2026-05-020). Directional, typed, lens-aware relations are expressed via the `## Related Sources` section (role enum) inside each artifact meta, replacing the removed Layer-2 expansion_links / Knowledge Object (CR-AIWS-2026-05-005). AI use: reference for how AI expands from a first hit to related sources, the relationship role taxonomy, and the `## Related Sources` vs `related_artifact_refs` separation.

## Knowledge Targets
- reference
- domain
- pattern

## Lookup Keys
- Related
- Sources
- role
- jsonl
- node
- quan
- relations
- artifact
- Object
- meta
- intent
- AIWS
- edge
- coupling
- Knowledge
- object
- reverse
- F03
- expansion
- F04
- knowledge
- typed
- layer
- confidence
- hop
- task
- upstream_input
- edges
- kind
- expansion_links
- contract
- projection
- SRC
- related
- model
- asserted
- one
- graph
- Artifact
- downstream_target

## Source-Specific Hints
- heading: Knowledge Relationship (Related Sources) Spec for AI Work System MVP
- heading: 1. Purpose of this spec
- heading: 2. Một relationship (`## Related Sources` entry) là gì / không là gì
- heading: 2.1. Là gì
- heading: 2.2. Không là gì
- heading: 3. Cấu trúc một `## Related Sources` entry
- heading: Related Sources
- heading: 4. Relation type registry (typed relations)
- heading: 4.0. Three relation registers (v0.5 — two-kind node)
- heading: 4.1. Open registry + extension (CR-022 OP-4)
- heading: 4.2. Confidence note (optional; net-new ở v0.4)
- heading: 4.3. Entry line format (v0.4)
- heading: 4.4. Basis note: objective stakes, intent-agnostic (CR-AIWS-2026-06-002)
- heading: dependency edge — fact + objective stakes/coupling:
- heading: skippable edge — objective no-coupling:
- heading: on F03's meta:
- heading: on F04's meta (seen from F03 as a reverse `## in` edge):
- heading: 5. Lens-aware expansion (intent giữ nguyên)
- heading: 6. Three-Way Separation (2-layer) — ba cơ chế cross-artifact
- heading: 6A. `relations.jsonl` — queryable projection (reverse index) [v0.4, CR-022]
- heading: 7. Cross-references
