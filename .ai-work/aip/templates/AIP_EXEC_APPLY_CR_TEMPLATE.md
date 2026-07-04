---
artifact_type: aip_exec
artifact_id: AIP-EXEC-NNN
title: "Apply <CR-ID> — <short change summary>"
status: draft
project: vti-ai-work-system
owner: "<owner>"
root_aip: AIP-ROOT
plan_source: "Direct execution — apply approved <CR-ID> (status approved_for_ai_update)"
updated_at: YYYY-MM-DD
---

<!-- APPLY-CR EXEC MINI-TEMPLATE (CR-AIWS-2026-05-037 Option C). Lint-conformant by construction: real `### Step:` headings + all required §6.3 sections + the 7 step fields, kept TERSE (one-line fields). Use for tasks that APPLY an already-approved CR. Rule #8 HARD GATE must ALREADY be satisfied (AIWS-Product-Owner approved for AIWS-canonical CRs; Wiki-Manager for wiki CRs — CR-031) BEFORE instantiating. Replace every <…> placeholder and set updated_at to a real YYYY-MM-DD; then `lint_aip.py --path <file>` MUST report 0 errors before `run-aip start` (run-aip now fails fast on lint errors — CR-037 Option A). -->
<!-- Stable control: Done Criteria declarative (never tick [x]). Runtime state → workspace. Scope change → Re-plan Log. -->

# AIP_EXEC — Apply <CR-ID>

## SOP Compliance
[SOP_MASTER](../../truth/SOP_MASTER.md) Universal Gates: U1 (HARD GATE) → STEP-00; U2 (soft) → Input Understanding; U3 (soft) → Known Open Points.

## Objective
Apply the approved changes of <CR-ID> exactly as authorized, then set the CR `status: applied` with an Apply Outcome. No change beyond the CR's approved scope.

## Execution Scope
### In Scope
- Apply each approved change of <CR-ID> with the correct edit-flow (canonical dual-tree byte-identical; tooling .ai-work→test→product; skills full-content trees only).

### Out of Scope
- Any change not in <CR-ID>'s approved scope; re-deciding settled open_decisions.

## Expected Outputs
- All <CR-ID> changes applied; <CR-ID> `status: applied` + Apply Outcome recorded; this AIP lint-clean.

## Execution Input Package
### Plan Source
- Direct execution; grounded in approved <CR-ID>.

### Required Truth Inputs
- SOP_MASTER §4.1 (CR-before-canonical-change — satisfied by approval); AI_WORK_CONTRACT §5.

### Required Wiki Inputs
| Input | Wiki Source ID | Artifact Path | Ghi chú | Capture flag |
|---|---|---|---|---|
| I-01 Approved CR | (none — direct) | product/change_requests/<CR-ID>.md | authority for every edit | — |

## Input Understanding
| Input artifact | Key understanding | Assumptions | Ambiguities | BrSE confirmed? |
|---|---|---|---|---|
| <CR-ID> | <approved scope = list of changes> | <edit-flow per target type> | <none / list> | ⬜ pending |

## References to Read First
- <CR-ID> (Targets, each Change/Option, Guardrails, apply_gates, must_preserve).

## Current Risks / Constraints
- Dual-tree drift: verify byte-identity per pair after canonical edits (edit-one→cp→diff); never exceed CR scope.
- Concurrent-mutation drift (CAP-065-01): a shared target may change between apply_gates-resolution and the edit; re-anchor before each edit.

## Known Open Points
- Open Points log: workspace `05_open_questions.md`
- (none expected — apply of a settled CR)

## Workspace Execution Rule
Update Active Step Context · Queue · Findings · Open Questions · Draft Output · Capture Inbox as applicable.

## Execution Steps

### Step: STEP-00 — Confirm Task Understanding (HARD GATE)
Objective:
Confirm scope = apply approved <CR-ID> (restate its changes); out-of-scope items excluded; finish by marking the CR applied.
Recommended Mode:
Clarifying
Applicable Guidelines:
- SOP_MASTER Gate U1
- wiki:none — HARD GATE preflight default. Replace with the relevant `product/wiki_guidelines/...` path after running `lookup_wiki_source.py`; keep `wiki:none` only when pre-flight confirms no wiki coverage.
Inputs:
- <CR-ID> (approved); HUMAN directive to apply
Expected Outputs:
- Understanding confirmed (apply-only of approved scope)
Done Condition:
Scope restated and not contradicted by HUMAN.
Notes / Constraints:
- Apply pre-approved scope only; no expansion without a Re-plan entry.

### Step: STEP-01 — Apply <CR-ID> changes
Objective:
Resolve the CR's apply_gates AND verify the CR's DP/decision statements (tree-set, version-targets, file lists) against current repo state — flag any stale assertion before applying (CAP-045-01) — then apply each approved change with the correct edit-flow. (apply_gates verification fixtures MUST be IN-REPO — never a consumer-project artifact — rule #9 / CR-034.)
Recommended Mode:
Canonical-edit
Applicable Guidelines:
- product/wiki_guidelines/core/specs/WIKI_CHANGE_REQUEST_SPEC.md
Inputs:
- <CR-ID> Changes/Options; confirmed edit-target paths
Expected Outputs:
- All changes applied; per-pair byte-identity verified for canonical dual-tree edits
Done Condition:
Every approved change applied; apply_gates satisfied; nothing outside CR scope touched.
Notes / Constraints:
- Canonical dual-tree byte-identical; tooling .ai-work→test→product; skills full-content trees only.
- **Byte-identical METHOD (CAP-074-01):** edit ONE tree → `cp` to the sibling path → `diff -q` to confirm 0 difference. Do NOT hand-edit both trees.
- **SKILL.md body = dual-tree (CR-037 C2):** edit `.ai-work/procedural/skills/<n>/SKILL.md` → `cp` → `product/procedural/skills/<n>/SKILL.md` (the `product/skills/<n>` pointer is unchanged). **Numbered-test label (CR-037 C2):** if the CR adds a test case, verify the next-free `Tn` against the target file at apply — do not pin a colliding label.
- **Re-anchor before each edit (CAP-065-01):** immediately before each edit, re-read/re-anchor the target's current state (re-grep the OLD wording — do not pin line numbers); a parallel actor may have mutated the shared target since apply_gates were resolved.

### Step: STEP-02 — Verify + finalize CR (status applied + Apply Outcome)
Objective:
Run lint to 0 errors; confirm Done Criteria; **pre-close OLD-wording sweep (CAP-010)** — before flipping status, grep the OLD wording being replaced across all SKILL.md + guidelines (both `.ai-work/` and `product/` trees); update in-scope hits, justify any remaining hit (no stale sibling copy may survive silently); set <CR-ID> `status: applied` and record an Apply Outcome (what / where / evidence). Then **move the CR file to `product/change_requests/applied/`** (the archive — CR-034).
Recommended Mode:
Reviewing
Applicable Guidelines:
- product/wiki_guidelines/core/specs/WIKI_CHANGE_REQUEST_SPEC.md
Inputs:
- All edited files; <CR-ID>; lint output
Expected Outputs:
- Lint-clean; <CR-ID> `status: applied` + Apply Outcome block
Done Condition:
lint 0 errors; CR marked applied with Apply Outcome; nothing applied outside CR scope.
Notes / Constraints:
- Pre-existing repo lint debt out of scope.

## Done Criteria
- [ ] All <CR-ID> approved changes applied with the correct edit-flow
- [ ] Canonical dual-tree edits byte-identical per pair (edit-one→cp→diff)
- [ ] CR DP/decision statements verified against repo state at apply time; stale assertions flagged (CAP-045-01)
- [ ] Each edit re-anchored against the target's current state immediately before applying (CAP-065-01)
- [ ] Pre-close OLD-wording sweep run; no stale copy of replaced wording remains in sibling SKILL.md/guidelines (each remaining hit justified) (CAP-010)
- [ ] <CR-ID> set to `status: applied` with an Apply Outcome
- [ ] This AIP passes lint_aip with 0 errors
- [ ] Nothing applied outside <CR-ID>'s approved scope
- [ ] **Gate U1/U2/U3** satisfied

## Self-check / Review Points
- Apply_gates resolved before editing? CR DP/decision statements verified vs repo (CAP-045-01)? Each edit re-anchored just before applying (CAP-065-01)? Byte-identity verified per pair via edit-one→cp→diff (CAP-074-01)?
- Pre-close OLD-wording sweep run across all SKILL.md + guidelines (both trees), not just the CR's listed files (CAP-010)?
- CR status=applied with a concrete Apply Outcome? No scope creep?

## Finalization Notes
- After apply, <CR-ID> lifecycle is complete (draft → approved_for_ai_update → applied).

## Pre-flight Pending Captures
- (none)

## Re-plan Rule
Macro scope/output change → explicit Re-plan Log entry + evidence before editing AIP.

## Re-plan Log
- (no re-plan yet)
