---
artifact_type: aip_review_checklist
artifact_id: AIP-REVIEW-CHECKLIST-v0_3
title: AIP v0.3 Conformance Checklist
status: active
project: AI Work System
methodology_version: ai_work_system_mvp
authoritative_spec: ../methodology/ai_work_system/20_specs/AIP_Detail_Spec_MVP.md
companion_guideline: AIP_REVIEW_GUIDELINE_v0_3.md
updated_at: 2026-04-15
---

<!-- Stable review artifact. Criteria derived from AIP_Detail_Spec §5/§6/§7.1/§10. Instances (filled copies) are reviewer output, not edits to this template. -->

# AIP v0.3 Conformance Checklist

Human-facing review checklist for evaluating **one AIP artifact** (ROOT / PLAN / EXEC / LOCAL) against AI Work System MVP v0.3 canonical spec. Complements automated [`lint_aip.py`](../../tooling/lint_aip.py) by adding a semantic review layer that automation cannot enforce.

**How to use:** Copy this file to a working location (e.g. `.ai-work/workspaces/<task>/aip_review_<target>.md`), fill the subject block, run lint first, then walk the criteria. For each criterion marked `lint_covered: yes`, skip unless lint already flagged a failure for the target file. Focus manual effort on the **Recommended tier** (semantic criteria) — that's where this checklist adds value beyond lint.

**Companion:** See [`AIP_REVIEW_GUIDELINE_v0_3.md`](AIP_REVIEW_GUIDELINE_v0_3.md) for per-criterion Purpose / Anti-pattern / Spec reference.

---

## Subject under evaluation

| Field | Value |
|---|---|
| **File path** | `___` |
| **Artifact type** | [ ] ROOT  [ ] PLAN  [ ] EXEC  [ ] LOCAL |
| **Artifact ID** | `___` |
| **Reviewer** | `___` |
| **Review date** | `___` |
| **Git commit hash reviewed** | `___` |
| **Lint run first?** | [ ] yes (`lint_aip.py` output attached below) [ ] no |

**Lint output (if run):**
```
<paste lint_aip.py output here, or `OK — no findings` if clean>
```

---

## Verdict summary

| Tier | Criteria | Pass | Fail | N/A | Notes |
|---|---|---|---|---|---|
| **Minimum (structural, mandatory gate)** | 26 | | | | |
| **Recommended (semantic, aspirational)** | 21 | | | | |
| **Total** | 47 | | | | |

> **ID prefix convention:** `S-NN` = criterion derived from structural spec sections (§5/§6/§7.1/§10). `SM-NN` = criterion is semantic-only (no structural source). **Tier membership is separate from prefix** — a few `S-` criteria (S-27, S-29) live in the Recommended tier because they require human judgment despite their structural origin.

**Gate decision:**
- [ ] PASS minimum → eligible for merge/sign-off
- [ ] FAIL minimum → BLOCK merge; owner must fix before re-review
- [ ] PASS minimum + semantic issues flagged → merge-eligible, semantic items logged for follow-up

**Summary notes:**
> ___

---

## A. Minimum Tier — Structural (mandatory gate)

Criteria in this section are **binary pass/fail** and **objectively verifiable**. Failure = block. Most are auto-enforced by `lint_aip.py` — reviewer skips unless lint flagged a failure.

> Legend: `applies_to` = which AIP types the criterion applies to (all = ROOT/PLAN/EXEC/LOCAL). `lint` = automation coverage (`yes` = fully automated, `partial` = partially, `no` = manual only).

### A.1 Metadata frontmatter (§5)

| ID | Criterion | applies_to | spec_ref | lint | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|---|
| S-01 | YAML frontmatter present at file top | all | §5.1 | yes | [ ] | [ ] | [ ] | |
| S-02 | `artifact_type` ∈ {aip_root, aip_plan, aip_exec, aip_local} | all | §5.2-§5.5 | yes | [ ] | [ ] | [ ] | |
| S-03 | `artifact_id` present and non-empty | all | §5.2-§5.5 | yes | [ ] | [ ] | [ ] | |
| S-04 | `title` present and non-empty | all | §5.2-§5.5 | no | [ ] | [ ] | [ ] | Manual check — lint gap |
| S-05 | `status` ∈ {draft, active, done, archived} | PLAN/EXEC/LOCAL | §5.6 | yes | [ ] | [ ] | [ ] | ROOT may omit status |
| S-06 | `project` present | all | §5.2-§5.5 | no | [ ] | [ ] | [ ] | Manual check — lint gap |
| S-07 | `updated_at` present, format `YYYY-MM-DD` | all | §5.2-§5.5 | partial | [ ] | [ ] | [ ] | Presence not enforced |
| S-08 | `root_aip` present | PLAN/EXEC | §5.3-§5.4 | yes | [ ] | [ ] | [ ] | |
| S-09 | `plan_source` present (or direct-execution rationale explicit) | EXEC | §5.4 | partial | [ ] | [ ] | [ ] | Lint warns only |

### A.2 Required sections (§6)

| ID | Criterion | applies_to | spec_ref | lint | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|---|
| S-11 | AIP_ROOT has 6 required sections (Objective / Project Scope / Project Priorities / Core References / Constraints / Notes) | ROOT | §6.1 | yes | [ ] | [ ] | [ ] | |
| S-12 | AIP_PLAN has 11 required sections (Objective / Background / Scope / Expected Outputs / References / Assumptions / Open Questions / Risks / Execution Steps / Done Criteria / Review Points) | PLAN | §6.2 | yes | [ ] | [ ] | [ ] | Alt names accepted per lint |
| S-13 | AIP_EXEC has 8 required sections (Objective / Execution Scope / Expected Outputs / References / Execution Steps / Risks / Done Criteria / Review) | EXEC | §6.3 | yes | [ ] | [ ] | [ ] | |
| S-14 | AIP_LOCAL has 4 required sections (Objective / Notes / Personal Constraints / Local Execution Notes) | LOCAL | §6.4 | yes | [ ] | [ ] | [ ] | |

### A.3 Step structure (§7.1)

| ID | Criterion | applies_to | spec_ref | lint | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|---|
| S-15 | Each step has unique `Step ID` (`STEP-NN` pattern) | PLAN/EXEC | §7.4 | yes | [ ] | [ ] | [ ] | |
| S-16 | Each step has `Step Title` in header | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | Parser-enforced |
| S-17 | Each step has `Objective` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-18 | Each step has `Recommended Mode` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-19 | Each step has `Applicable Guidelines` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-20 | Each step has `Inputs` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-21 | Each step has `Expected Outputs` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-22 | Each step has `Done Condition` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-23 | Each step has `Notes / Constraints` field | PLAN/EXEC | §7.1 | yes | [ ] | [ ] | [ ] | |
| S-24 | All path refs in `Applicable Guidelines` / `Recommended Skills` resolve on disk | PLAN/EXEC | §12.4 | partial | [ ] | [ ] | [ ] | Lint warns only |

### A.4 Stability guards (§10 / §2.3)

| ID | Criterion | applies_to | spec_ref | lint | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|---|
| S-25 | Done Criteria items contain no `[x]` / `[X]` checkboxes (declarative only) | PLAN/EXEC | §2.3 + §10.2 | yes | [ ] | [ ] | [ ] | Lint warns; treat as error |
| S-26 | No runtime metric inline in AIP body (`N files`, `M items`, etc.) | PLAN/EXEC | §2.3 + §10.2 | yes | [ ] | [ ] | [ ] | Lint warns; treat as error |
| S-28 | "Re-plan Log" section present with appendable entry format | PLAN/EXEC | §10.1 + §9.3 | no | [ ] | [ ] | [ ] | Manual check — lint gap |

**A-tier subtotal:** _/26 pass, _/26 fail, _/26 N/A

---

## B. Recommended Tier — Semantic (aspirational)

Criteria in this section require **human judgment**. Failure is not a hard block but should be logged for follow-up. This is the tier where reviewer effort should focus — automation cannot cover these.

### B.1 Optional-but-recommended step fields (§7.2)

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| SM-01 | Step has `Recommended Skills` field where applicable skills exist | PLAN/EXEC | §7.2 | [ ] | [ ] | [ ] | |
| SM-02 | Step has `Workspace Actions` field describing runtime writes | PLAN/EXEC | §7.2 | [ ] | [ ] | [ ] | |
| SM-03 | Step has `Step Dependencies` where multi-step dependency chain exists | PLAN/EXEC | §7.2 | [ ] | [ ] | [ ] | |

### B.2 Naming & identity (§4)

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| SM-04 | Slug follows `lowercase-hyphen-separated` convention | PLAN/EXEC/LOCAL | §4.2 | [ ] | [ ] | [ ] | |
| SM-05 | Slug is short but meaningful, reflects deliverable/workstream (not generic like `task-1`, not sentence-like) | PLAN/EXEC/LOCAL | §4.2 | [ ] | [ ] | [ ] | |

### B.3 Granularity (§8)

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| SM-06 | AIP maps to medium-sized deliverable/workstream (not micro, not broad-phase) | PLAN/EXEC | §8.1 + §8.3 | [ ] | [ ] | [ ] | |
| SM-07 | If multiple major outputs of different kinds → split into separate AIPs (not bundled) | PLAN/EXEC | §8.2 | [ ] | [ ] | [ ] | |
| SM-08 | PLAN→EXEC handoff boundary respected (PLAN delivers handoff; EXEC consumes, doesn't re-plan) | PLAN/EXEC | §8.2 + §9 | [ ] | [ ] | [ ] | Cross-AIP read needed |

### B.4 Handoff (§9)

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| SM-09 | PLAN Handoff section contains all §9.1 items (Objective / Context / Scope / Non-scope / Outputs / Refs / Step skeleton / Open Questions / Risks / Done / Review) | PLAN | §9.1 | [ ] | [ ] | [ ] | |
| SM-10 | EXEC consumes PLAN handoff by reference, not copy-paste of PLAN content | EXEC | §9.2 | [ ] | [ ] | [ ] | Cross-AIP read needed |

### B.5 Stability discipline — deeper semantic (§10)

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| S-27 | `updated_at` bumped only on material change (not last-touched) | all | §10.1 | [ ] | [ ] | [ ] | git diff analysis |
| S-29 | Scope/objective/output changes have dated Re-plan Log entry BEFORE earlier-section edit | PLAN/EXEC | §10.1 + §9.3 | [ ] | [ ] | [ ] | git sequence analysis |
| SM-14 | Done Criteria items are declarative conditions (not imperative task list disguised as criteria) | PLAN/EXEC | §2.3 + §10 | [ ] | [ ] | [ ] | Phrasing judgment |

### B.6 Clarity & grounding

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| SM-11 | Objective is task-oriented (what task does), not output-oriented (what gets produced), ≥1 sentence | all | §2.1 | [ ] | [ ] | [ ] | |
| SM-12 | Scope In has ≥2 concrete items (not generic single-sentence scope statement) | PLAN/EXEC | §2.1 | [ ] | [ ] | [ ] | |
| SM-13 | Non-scope / Out-of-scope explicit (boundary drawn, not just implied) | PLAN/EXEC | §2.1 + §6.2 | [ ] | [ ] | [ ] | |
| SM-15 | Rationale grounded in canonical spec / SOP / Contract refs (not free-form opinion) | PLAN/EXEC | §11.1 | [ ] | [ ] | [ ] | |

### B.7 Artifact relationship integrity (§11)

| ID | Criterion | applies_to | spec_ref | Pass | Fail | N/A | Note |
|---|---|---|---|---|---|---|---|
| SM-16 | AIP does not contradict AI_WORK_CONTRACT | PLAN/EXEC | §11.1 | [ ] | [ ] | [ ] | |
| SM-17 | AIP references (does not duplicate) SOP / Contract / Skill / Playbook content | PLAN/EXEC | §11.1 + §11.4 | [ ] | [ ] | [ ] | |
| SM-18 | Runtime state references explicitly point to workspace files (not inline) | PLAN/EXEC | §11.2 | [ ] | [ ] | [ ] | |
| SM-19 | `owner` present (optional per spec but recommended for accountability) | PLAN/EXEC/LOCAL | §5.3-§5.5 | [ ] | [ ] | [ ] | |

**B-tier subtotal:** _/21 semantic criteria evaluated

---

## C. Cross-ref with `lint_aip.py` automation

This table documents which criteria are automated by [`lint_aip.py`](../../tooling/lint_aip.py), so reviewers know where to focus manual effort.

| Lint rule | Behavior | Covers criteria | Note |
|---|---|---|---|
| `meta_missing` | error | S-01 | |
| `meta_type` | error | S-02 | |
| `meta_id` | error | S-03 | |
| `meta_status` | error | S-05 | ROOT permissive |
| `meta_root_aip` | error | S-08 | |
| `meta_plan_source` | warn | S-09 | |
| `section_missing` | error | S-11 / S-12 / S-13 / S-14 | Alternative names accepted |
| `steps_empty` | error | (S-15 precondition) | |
| `step_dup` | error | S-15 uniqueness | |
| `step_field_missing` | error | S-17 / S-18 / S-19 / S-20 / S-21 / S-22 / S-23 | Per missing field per step |
| `live_working_file` | warn | S-25 | Treat as error per project policy |
| `runtime_metric_in_aip` | warn | S-26 | Treat as error per project policy |
| `ref_missing` | warn | S-24 | |

**Gaps (criteria NOT covered by current lint — reviewer must check manually):**
- **S-04** — `title` field presence
- **S-06** — `project` field presence
- **S-07** — `updated_at` presence + format validation
- **S-16** — `Step Title` explicit check (implicit via header parser)
- **S-27** — `updated_at` bump discipline (git history comparison)
- **S-28** — Re-plan Log section presence
- **S-29** — Re-plan Log sequencing (git diff analysis)
- **SM-01 through SM-18** — all semantic criteria

**Lint extension candidates (trivially automatable):**
- S-04, S-06, S-07 (presence), S-28 (section presence) → could be added as new lint rules in a future iteration (see `.ai-work/workspaces/<task>/08_capture_inbox.jsonl` for candidate items tagged `lint_extension_candidate`, then execute via AIP-EXEC-009 STEP-02).

---

## D. Sign-off block

**Reviewer judgment:**
- [ ] All Minimum tier criteria PASS (or have explicit N/A with rationale) → **gate OK**
- [ ] Recommended tier issues logged (if any) → follow-up tracked at: `___`

**Lint gate confirmation:**
- [ ] `lint_aip.py` ran on target file → result: `___`
- [ ] `lint_all.py` ran project-wide → result: `___`

**Reviewer signature:** `___` · **Date:** `___`

**BrSE sign-off (if applicable):** `___` · **Date:** `___`

---

## References

- [AIP_Detail_Spec_MVP.md](../methodology/ai_work_system/20_specs/AIP_Detail_Spec_MVP.md) — authoritative spec
- [AIP_REVIEW_GUIDELINE_v0_3.md](AIP_REVIEW_GUIDELINE_v0_3.md) — companion guideline (Purpose / Anti-pattern / Spec ref per criterion)
- `lint_aip.py` — automated layer enforcement (see `.ai-work/tooling/lint_aip.py` in target project)
- `SOP_MASTER §4` — quality gates that invoke this checklist (see `.ai-work/truth/SOP_MASTER.md` in target project)
- `AI_WORK_CONTRACT §6` — review & sign-off rules (see `.ai-work/truth/AI_WORK_CONTRACT.md` in target project)
