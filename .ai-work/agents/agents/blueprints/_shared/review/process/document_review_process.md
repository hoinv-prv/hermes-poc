# Document Review Process (shared)

> Shared across all Document Review Agent blueprints in the pack.
> Mapped from: Document_Review_Agent_Blueprint/templates/REVIEW_PROCESS_TEMPLATE.md (v0.1).
> Document-type-agnostic. A document-type blueprint adds its own checklist and skills on top of
> this process; it does not replace the steps below.

---

> **Governance-invariant floor (AP-CR-31).** Lines tagged `⚖ governance_invariant` `<id>` mark non-overridable governance steps. An Agent Instance owns a copy of this process (FR-AI-13, §6D) and may add / reorder / annotate / mark-satisfied-elsewhere, but must NOT silently drop or weaken a `governance_invariant` step; the staging lint `tooling/lint_agents.py` warns if a copied instance process is missing one.

## 1. Purpose

Define the standard, repeatable process a Review Agent Instance follows to review a document.

---

## 2. Process

### Step 1 — Understand the review request

Confirm:
- target document and its path
- document type
- review scope (and any excluded scope)
- review depth: quick / standard / deep
- expected output
- deadline / priority if any

If any of these is unclear, ask the HUMAN before reviewing. Do not assume scope.

### Step 2 — Select review mode / checklist

Select and combine:
- the common document review checklist (`../checklists/common_document_review_checklist.md`)
- the document-specific checklist (blueprint-local: `checklists/<doc_type>_review_checklist.md`)
- any optional focus lens requested by the HUMAN

### Step 3 — Load references (Wiki-first, NOT Wiki-only)

Read in this order:
1. relevant Wiki entries first — for project context, terminology, design decisions, cautions,
   and source-navigation hints.
2. related source / reference documents (verify Wiki against source where it matters).
3. related AIP / task plan if any.
4. agent memory: retrieval hints, false-positive notes, confirmed memory.

Wiki is the starting point for grounding, not the only authority. When Wiki is stale, unverified,
or contradicts the source, verify against the source and follow `source_trace_rule.md`.

### Step 4 — Create review plan

Produce a short review plan (`review_plan.md`) capturing:
- review scope
- references to use
- checklist / lens selected
- expected output
- known limitations going in

### Step 5 — Review the document

Apply the checklist and record findings. Distinguish clearly:
- confirmed_issue
- possible_issue
- open_question
- conflict
- suggestion

Follow `finding_format.md` for structure and `severity_definition.md` for severity. Every
important finding needs evidence per `source_trace_rule.md`, or must be marked as an
assumption / open question.

### Step 6 — Produce the review report

Produce, using the shared output templates in `../output_templates/`:
- review_report.md
- findings_table.md (or findings.jsonl)
- open_questions.md
- references_used.md
- review_limitations.md

### Step 7 — Capture learning candidates

Emit `learning_candidates.jsonl` per `lesson_capture_rule.md`. All entries `status: candidate`.
Candidate types: review_rule_candidate, checklist_update_candidate, retrieval_hint_candidate,
false_positive_note_candidate, project_issue_pattern_candidate, output_preference_candidate,
wiki_candidate, blueprint_improvement_candidate.

### Step 8 — Wait for HUMAN feedback

> ⚖ **governance_invariant** `human_gate` — do NOT update confirmed memory / checklist / Wiki / blueprint without HUMAN confirmation; promotion is HUMAN-gated.

Do NOT update confirmed memory, checklist, Wiki, or blueprint automatically. Promotion is
HUMAN-gated.

### Step 9 — Update after HUMAN confirmation

Only after the HUMAN confirms candidates:
- update memory files
- update the checklist if approved
- create a Wiki candidate if approved
- create a blueprint improvement candidate if approved
- update the relevant changelog

---

## 3. Run evidence

For formal review runs, save evidence under the instance workspace:
`workspace/completed_runs/<run_id>/` (run record + outputs + learning_candidates.jsonl).
When the run serves an AIP task, the PRIMARY deliverable lives in the AIP workspace
(`.ai-work/workspaces/<task-id>/`); the instance workspace keeps a run record + pointer, not a
duplicate (Detailed Design v0.2 §8 / AP-CR-14).
