# Skill-Authoring & Maintenance Conventions (MVP)

> Canonical conventions for authoring/maintaining AIWS `SKILL.md` files. Established by **CR-AIWS-2026-06-032** (CAP-060-01 + CAP-058-01). Companion guard for the Object Kind Catalog: `Knowledge_Object_Model_Spec_MVP §3bis.1` (CAP-064-01).

## 1. Traceability separation — keep opaque codes out of AI action text  *(CAP-060-01)*

Opaque governance/decision codes — `#NN` (rule numbers), `DPn` (design principles), `INV-x` (invariants) — must **NOT** appear as **labels or identifiers inside AI action text** (the steps/instructions the AI executes). The AI reads such a tag as noise and may skip the step.

- **Evidence (HUMAN-ruled 2026-05-31):** a step labelled `… (#19)` was skipped because `#19` was read as noise, not as part of the instruction.
- **Rule:** move the codes to a dedicated **`## Traceability`** section at the end of the skill (code → the rule/decision/step it governs). The action text states *what to do*; the Traceability section records *which governance code it derives from*.
- **Acceptable exception — inline provenance citations.** A code in an end-of-rule parenthetical that cites *why* a rule holds (e.g. "never auto-build an object meta (DP6/INV-8)") is a citation, not a step-identifier. These may remain inline, but prefer `## Traceability` when several accumulate.
- **Precedent:** CR-AIWS-2026-05-038 (CR-038) introduced the `## Traceability` section in `build-wiki-source-meta`/`register-wiki-source`.

## 2. Skill 4-tree topology — body-edit only the full trees  *(CAP-058-01)*

| Tree | Role | Body-edit? |
|---|---|---|
| `.ai-work/procedural/skills/<skill>/SKILL.md` | **FULL** (live) | ✅ edit here |
| `product/procedural/skills/<skill>/SKILL.md` | **FULL** (canonical mirror) | ✅ mirror byte-identical |
| `.claude/skills/<skill>/SKILL.md` | **STUB** (pointer) | ❌ never body-edit |
| `product/skills/<skill>/SKILL.md` | **STUB** (pointer) | ❌ never body-edit |

- Edit the skill **body in the 2 FULL trees only**, byte-identical (`diff -q` clean). The 2 STUB trees are pointers to the full definition — never body-edit them.
- A SKILL.md body change is `no_cr` (tooling/procedural dual-tree edit-flow); a *convention* like this guideline is `cr_required`.

## 3. Kind-vs-term guard (pointer)

When editing the Object Kind Catalog (`Knowledge_Object_Model_Spec_MVP §3bis.1`), a kind name may also be a `knowledge_target`/domain term (e.g. `business_rule`) — triage each occurrence by **role** (kind = edit; term = leave); never blind grep-replace. See that section's editing guard.

## Relationships
- `Knowledge_Object_Model_Spec_MVP §3bis.1` (kind-vs-term guard).
- `AIWS_Change_Request_Spec_MVP` (governs changes to this guideline; AIWS-Product-Owner approves).
- CR-AIWS-2026-06-032 (source), CR-AIWS-2026-05-038 (Traceability precedent).
