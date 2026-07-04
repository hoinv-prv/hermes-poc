---
artifact_type: aip_review_guideline
artifact_id: AIP-REVIEW-GUIDELINE-v0_3
title: AIP v0.3 Conformance Checklist — Companion Guideline
status: active
project: AI Work System
methodology_version: ai_work_system_mvp
authoritative_spec: ../methodology/ai_work_system/20_specs/AIP_Detail_Spec_MVP.md
companion_checklist: AIP_REVIEW_CHECKLIST_v0_3.md
updated_at: 2026-04-15
---

<!-- Reference-tier companion. Not a mandatory linear read. Look up when a checklist criterion is unclear. -->

# AIP v0.3 Conformance Checklist — Companion Guideline

Per-criterion **Purpose / Anti-pattern / Spec reference** for [`AIP_REVIEW_CHECKLIST_v0_3.md`](AIP_REVIEW_CHECKLIST_v0_3.md). **Reference-tier** — read when a criterion is unclear during review, not linearly.

**How purpose sentences are written:** "This criterion exists to prevent X bad outcome." Rationale is outcome-focused, not rule-restating. If the criterion doesn't prevent a concrete bad outcome, it shouldn't be in the checklist.

---

## A. Minimum Tier — Structural

### A.1 Metadata frontmatter (§5)

#### S-01 — YAML frontmatter present at file top
- **Purpose:** Enables tooling (lint_aip.py, run_aip.py, workspace builders) to parse artifact metadata. Without frontmatter, AIP is invisible to the tool chain.
- **Anti-pattern:** AIP file starts directly with `# Title` heading, no `---` block above. Lint fails with `meta_missing`. Tooling cannot determine artifact_type → cannot apply type-specific checks.
- **Spec ref:** §5.1

#### S-02 — `artifact_type` ∈ enum
- **Purpose:** Dispatches type-specific required sections + step-field enforcement. Wrong or missing type breaks downstream lint + workspace wiring.
- **Anti-pattern:** `artifact_type: aip_exec` on a file that is actually ROOT metadata; `artifact_type: plan` (missing `aip_` prefix).
- **Spec ref:** §5.2–§5.5

#### S-03 — `artifact_id` present
- **Purpose:** Stable identifier for cross-referencing (plan_source, decision evidence, re-plan log). Without ID, consumers cannot refer to the AIP unambiguously.
- **Anti-pattern:** `artifact_id:` left blank; ID contains spaces or special chars; ID does not match file naming (`AIP-EXEC-005` inside file but filename `AIP-EXEC-003_...md`).
- **Spec ref:** §5.2–§5.5

#### S-04 — `title` present and non-empty
- **Purpose:** Human-readable label used in ASC materialization + review packages. Missing title makes workspace artifacts say "untitled".
- **Anti-pattern:** `title: <title>` (placeholder never filled); `title: ""`.
- **Spec ref:** §5.2–§5.5 · **lint gap** — manual check required

#### S-05 — `status` ∈ {draft, active, done, archived}
- **Purpose:** Lifecycle state drives execution readiness + archival filters. Invalid status blocks downstream queries.
- **Anti-pattern:** `status: in_progress` (not in enum); `status: WIP`; mixing with `active` when work is complete.
- **Spec ref:** §5.6

#### S-06 — `project` present
- **Purpose:** Multi-project consumption — disambiguates which project the AIP belongs to when aggregated (e.g. AIP_ROOT references from multiple consumers).
- **Anti-pattern:** `project:` empty; `project: <project-name>` placeholder never filled.
- **Spec ref:** §5.2–§5.5 · **lint gap**

#### S-07 — `updated_at` present, format `YYYY-MM-DD`
- **Purpose:** Enables change-tracking + staleness detection. Wrong format breaks date comparisons.
- **Anti-pattern:** `updated_at: 2026/04/15` (slashes); `updated_at: April 15 2026`; `updated_at: today`.
- **Spec ref:** §5.2–§5.5 · **lint partial** — presence not enforced

#### S-08 — `root_aip` present (PLAN/EXEC)
- **Purpose:** Child AIPs must anchor to project root AIP for precedence resolution + scope alignment. Orphan PLAN/EXEC undermines §11.2 relationship.
- **Anti-pattern:** PLAN/EXEC file without `root_aip` field; `root_aip: project-name` (should be ID like `AIP-ROOT`).
- **Spec ref:** §5.3–§5.4

#### S-09 — `plan_source` present (EXEC)
- **Purpose:** Execution must trace to planning artifact (or explicit direct-execution rationale). Missing plan_source undermines PLAN→EXEC handoff audit.
- **Anti-pattern:** EXEC with no `plan_source`, no explanation of direct execution; `plan_source:` pointing to non-existent PLAN.
- **Spec ref:** §5.4 · **lint warn** — spec uses "should" not "must"

---

### A.2 Required sections (§6)

#### S-11 — AIP_ROOT has 6 required sections
- **Purpose:** Each section addresses a specific project-level concern (objective, scope, priorities, refs, constraints, notes). Missing section = missing concern.
- **Anti-pattern:** AIP_ROOT without "Project Priorities" — consumers cannot determine priority order.
- **Spec ref:** §6.1

#### S-12 — AIP_PLAN has 11 required sections
- **Purpose:** Plan artifact must carry full handoff package (§9.1) — missing sections break PLAN→EXEC handoff.
- **Anti-pattern:** PLAN without "Review Points" — reviewer cannot execute quality gate; PLAN without "Open Questions" — unknowns leak into execution.
- **Spec ref:** §6.2

#### S-13 — AIP_EXEC has 8 required sections
- **Purpose:** Execution artifact must carry work context (scope, refs, steps, risks, done criteria, review notes). Missing section = incomplete execution brief.
- **Anti-pattern:** EXEC without "Current Risks / Constraints" — blocker discovery delayed to runtime.
- **Spec ref:** §6.3

#### S-14 — AIP_LOCAL has 4 required sections
- **Purpose:** Minimal private-notes structure — even local notes need basic shape.
- **Anti-pattern:** LOCAL used as a full PLAN substitute (shared coordination treated as private).
- **Spec ref:** §6.4

---

### A.3 Step structure (§7.1)

#### S-15 — Unique Step ID (`STEP-NN` pattern)
- **Purpose:** Identifier drives pointer (`run_aip.py step --step STEP-02`), ASC materialization, and cross-references. Duplicates break pointer logic.
- **Anti-pattern:** Two `STEP-02` in same AIP; `STEP-2a` and `STEP-2b` non-standard pattern.
- **Spec ref:** §7.4

#### S-16 — Step Title in header
- **Purpose:** Title communicates intent at-a-glance. Required so ASC title materializes correctly.
- **Anti-pattern:** `### Step: STEP-02 —` with empty title.
- **Spec ref:** §7.1

#### S-17 through S-23 — 7 required step fields
- **Purpose:** Each field addresses a specific execution concern (Objective, Mode, Guidelines, Inputs, Outputs, Done Condition, Notes). Missing field = ambiguous step.
- **Anti-pattern:**
  - Missing `Objective` → step has no "why"
  - Missing `Recommended Mode` → ASC cannot suggest execution stance
  - Missing `Applicable Guidelines` → step has no grounding
  - Missing `Inputs` → AI cannot pre-gate inputs
  - Missing `Expected Outputs` → no success criteria
  - Missing `Done Condition` → step cannot be marked complete
  - Missing `Notes / Constraints` → edge cases invisible
- **Spec ref:** §7.1

#### S-24 — Path refs in Applicable Guidelines / Recommended Skills resolve on disk
- **Purpose:** Prevents broken references. Lint warns, not errors — some paths may be intentionally future-dated or external.
- **Anti-pattern:** Reference to deleted skill file; typo in path.
- **Spec ref:** §12.4 · **lint warn**

---

### A.4 Stability guards (§10 / §2.3)

#### S-25 — No `[x]` in Done Criteria
- **Purpose:** Done Criteria are **declarative** ("what constitutes done"), not a progress checkbox. Ticking `[x]` treats AIP as live working file, violating §2.3 stability principle.
- **Anti-pattern:**
  ```
  ## Done Criteria
  - [x] All edits applied    ← WRONG — AIP mutated to track progress
  - [ ] Lint passes
  ```
  Correct pattern: leave as `- [ ]` (declarative) and track completion in `07_output_draft.md` workspace log.
- **Spec ref:** §2.3 + §10.2 · **lint warn** (treat as error)

#### S-26 — No runtime metrics inline
- **Purpose:** Runtime counts/findings belong in workspace `04_findings.md`, not AIP body. Runtime state in AIP = live working file anti-pattern.
- **Anti-pattern:**
  ```
  ## Expected Outputs
  - Batch lint report (82 files, pass/fail per criterion)  ← WRONG
  ```
  Correct: "Batch lint report (per-file pass/fail per criterion)" — count moved to workspace.
- **Spec ref:** §2.3 + §10.2 · **lint warn** (treat as error)

#### S-28 — Re-plan Log section present
- **Purpose:** Scope/objective changes must have appendable home. Missing section forces silent drift.
- **Anti-pattern:** No `## Re-plan Log` section in AIP; drift happens via silent inline edits to earlier sections.
- **Spec ref:** §10.1 + §9.3 · **lint gap**

---

## B. Recommended Tier — Semantic

### B.1 Optional step fields (§7.2)

#### SM-01 — `Recommended Skills` field present where applicable
- **Purpose:** Surfaces reusable skill integrations to reviewer + AI. Absent when relevant skills exist = missed reuse opportunity.
- **Anti-pattern:** Step does manual tooling invocation without pointing to a `.claude/skills/` skill that already automates it.
- **Spec ref:** §7.2

#### SM-02 — `Workspace Actions` field present
- **Purpose:** Tells execution engine what files to write during step (runtime hooks). Absent = execution implicit, harder to audit.
- **Anti-pattern:** Step writes to workspace but AIP doesn't say where → reviewer cannot verify audit trail.
- **Spec ref:** §7.2

#### SM-03 — `Step Dependencies` field present when chain matters
- **Purpose:** Explicit dependencies prevent out-of-order execution. Critical in multi-gate flows (e.g. pre-flight check → destructive action).
- **Anti-pattern:** STEP-05 requires STEP-03 done but dependency not stated → execution risks running STEP-05 first.
- **Spec ref:** §7.2

---

### B.2 Naming & identity (§4)

#### SM-04 — Slug follows `lowercase-hyphen-separated`
- **Purpose:** Consistent naming eases discovery + cross-reference. Mixed conventions confuse grep.
- **Anti-pattern:** `AIP-EXEC-002_LegacyGovernance_P0_Cleanup.md` (camel + underscore); `aip-exec-002-legacy-governance.MD` (uppercase extension).
- **Spec ref:** §4.2

#### SM-05 — Slug short, meaningful, reflects deliverable
- **Purpose:** Slug is the artifact's identity. Generic or verbose slugs dilute meaning.
- **Anti-pattern:**
  - Too generic: `task-1`, `work-item`, `thing-to-do`
  - Too verbose: `align-legacy-common-templates-with-canonical-ai-work-system-mvp-v0-3-methodology`
  - Sentence-like: `how-to-fix-the-thing-that-broke-last-week`
- **Spec ref:** §4.2

---

### B.3 Granularity (§8)

#### SM-06 — Medium-sized deliverable (not micro, not broad-phase)
- **Purpose:** AIP is for coherent work units. Micro-AIPs waste overhead; broad-phase AIPs become unmaintainable.
- **Anti-pattern:**
  - Micro: "AIP for fixing a single typo"
  - Broad-phase: "AIP for everything in Q2"
- **Spec ref:** §8.1 + §8.3

#### SM-07 — Multiple major outputs → split into separate AIPs
- **Purpose:** Each AIP should have one coherent deliverable intent. Bundled AIPs confuse handoff + Done Criteria.
- **Anti-pattern:** One EXEC that "updates 3 templates + writes 2 rules + runs a cleanup sweep" — should be 3 EXECs.
- **Spec ref:** §8.2

#### SM-08 — PLAN→EXEC handoff boundary respected
- **Purpose:** PLAN delivers handoff; EXEC consumes it. EXEC that re-plans = scope drift, wasted planning effort.
- **Anti-pattern:** EXEC file contains "Triage decisions" section that should have been resolved in PLAN.
- **Spec ref:** §8.2 + §9

---

### B.4 PLAN → EXEC Handoff (§9)

#### SM-09 — PLAN Handoff section contains all §9.1 items
- **Purpose:** Handoff is the interface between PLAN and EXEC. Missing handoff items force EXEC to re-discover context.
- **Anti-pattern:** PLAN without explicit "Handoff to EXEC" section, or section listing only 5 of 11 required items.
- **Spec ref:** §9.1 · **lint partial** — §6.2 required sections cover most items

#### SM-10 — EXEC consumes handoff by reference, not copy
- **Purpose:** Avoid duplication between PLAN and EXEC. EXEC says "per PLAN-003 STEP-05 handoff" not copy of PLAN text.
- **Anti-pattern:** EXEC body copies PLAN objective + scope + refs verbatim → drift when PLAN re-plans.
- **Spec ref:** §9.2

---

### B.5 Stability discipline — deeper semantic

#### S-27 — `updated_at` bumped only on material change
- **Purpose:** `updated_at` is a semantic signal, not a file-touched timestamp. Bumping on cosmetic edits undermines staleness detection.
- **Anti-pattern:** Bumping `updated_at` every time reviewer adds a newline; using `updated_at` as "last reviewed" timestamp.
- **Spec ref:** §10.1 · **lint gap** — requires git diff analysis

#### S-29 — Re-plan Log entry BEFORE earlier-section edit
- **Purpose:** Append-then-edit order preserves audit trail. Edit-then-append creates a gap where reviewer can't trace what changed and why.
- **Anti-pattern:** Editing Objective inline, then adding Re-plan Log entry as an afterthought → git shows ordering violation.
- **Spec ref:** §10.1 + §9.3 · **lint gap** — requires git sequence analysis

#### SM-14 — Done Criteria items are declarative, not imperative
- **Purpose:** "All edits applied" is declarative (a state); "Apply all edits" is imperative (a command). Imperative phrasing confuses AIP with task queue.
- **Anti-pattern:**
  - Imperative (wrong): "- [ ] Apply D-B1 edits"
  - Declarative (correct): "- [ ] D-B1 edits applied"
- **Spec ref:** §2.3 + §10

---

### B.6 Clarity & grounding

#### SM-11 — Objective is task-oriented, not output-oriented
- **Purpose:** "Why we're doing this" > "what comes out". Output-only objective makes "why" implicit.
- **Anti-pattern:**
  - Output-only (weak): "Produce 3 updated templates"
  - Task-oriented (strong): "Align 3 legacy templates with canonical v0.3 structure to unblock consumer package release"
- **Spec ref:** §2.1

#### SM-12 — Scope In has ≥2 concrete items
- **Purpose:** Single-sentence scope = vague. Concrete bullets force explicit boundaries.
- **Anti-pattern:** "Scope In: Improve the template system" — no enforcement boundary.
- **Spec ref:** §2.1

#### SM-13 — Non-scope explicit
- **Purpose:** Explicit Out-of-scope prevents scope creep. Absent = arguments at review time.
- **Anti-pattern:** PLAN/EXEC with "Scope: ..." but no "Non-scope" → reviewer can't reject out-of-scope work.
- **Spec ref:** §2.1 + §6.2

#### SM-15 — Rationale grounded in canonical spec/SOP/Contract refs
- **Purpose:** Free-form rationale invites arbitrary decisions. Grounded rationale makes judgment traceable.
- **Anti-pattern:** "We should delete this because it's old" — no ref.
- **Good example:** "Per SOP_MASTER §6.1 Profile A precedence, legacy templates are reference-tier; deletion per AIP-PLAN-003 D-A3."
- **Spec ref:** §11.1

---

### B.7 Artifact relationship integrity (§11)

#### SM-16 — Does not contradict AI_WORK_CONTRACT
- **Purpose:** Contract is source-of-truth at project level. AIP contradicting Contract = silent Contract override.
- **Anti-pattern:** AIP directs "tick Done Criteria [x] per step" — contradicts §2.3 stability rule in Contract.
- **Spec ref:** §11.1

#### SM-17 — References, does not duplicate
- **Purpose:** Duplication drifts. Reference single-source-of-truth.
- **Anti-pattern:** AIP body embeds the full text of a playbook instead of `.claude/skills/<name>/SKILL.md` reference.
- **Spec ref:** §11.1 + §11.4

#### SM-18 — Runtime state references point to workspace files
- **Purpose:** Runtime state belongs in `04_findings.md`/`07_output_draft.md`. Inline state = live working file.
- **Anti-pattern:** AIP body says "current progress: 3 of 5 tasks done" — progress is runtime, belongs in draft.
- **Spec ref:** §11.2

#### SM-19 — `owner` present for accountability
- **Purpose:** Accountable person visible at artifact top. Absent = diffused ownership.
- **Anti-pattern:** `owner: (BrSE TBD)` left for weeks without resolution.
- **Spec ref:** §5.3–§5.5

---

## Usage notes

- **When a criterion is unclear during review:** search this file by criterion ID (e.g. `S-25`) and read Purpose + Anti-pattern. If still unclear, open the spec ref section.
- **When adding a new criterion:** it must have a concrete Purpose (what bad outcome it prevents) + concrete Anti-pattern example. If you cannot state either, the criterion may not be load-bearing.
- **When a criterion becomes automatable:** move `lint_covered` note from "manual only" to "lint covered" in the checklist + add lint extension candidate to workspace capture inbox.

---

## References

- [AIP_REVIEW_CHECKLIST_v0_3.md](AIP_REVIEW_CHECKLIST_v0_3.md) — companion checklist (reviewer-facing form)
- [AIP_Detail_Spec_MVP.md](../methodology/ai_work_system/20_specs/AIP_Detail_Spec_MVP.md) — authoritative spec
- `lint_aip.py` — automated layer (see `.ai-work/tooling/lint_aip.py` in target project)
- `SOP_MASTER §4` — quality gates (see `.ai-work/truth/SOP_MASTER.md` in target project)
- `AI_WORK_CONTRACT` — stability rules (see `.ai-work/truth/AI_WORK_CONTRACT.md` in target project)
