# Finding Format (shared)

> Shared across all Document Review Agent blueprints.
> Mapped from: REVIEW_AGENT_BLUEPRINT_TEMPLATE.md §12 + REVIEW_OUTPUT_TEMPLATE.md §6 (v0.1).
> Document-type-agnostic.

---

## 1. Finding table structure

Every finding is one row in the findings table:

```markdown
| ID | Severity | Type | Category | Location | Finding | Evidence / Reference | Impact | Suggested Action | HUMAN Decision |
|---|---|---|---|---|---|---|---|---|---|
```

Column meaning:
- ID — stable per-run id, e.g. `F-001`.
- Severity — Critical / Major / Minor / Suggestion (see `severity_definition.md`).
- Type — one of the finding types below.
- Category — which checklist area it came from (e.g. completeness, consistency, alignment).
- Location — where in the target document (section / page / line / table).
- Finding — what is wrong or unclear, stated specifically (NOT generic).
- Evidence / Reference — Wiki entry / source doc / source line backing the finding, OR an explicit
  note that it is an assumption / open question (see `source_trace_rule.md`).
- Impact — the implementation / project risk if not addressed.
- Suggested Action — concrete, actionable fix or question.
- HUMAN Decision — left blank for the HUMAN to fill (accept / reject / defer / fixed).

## 2. Finding types

- `confirmed_issue` — backed by evidence; the document is wrong/incomplete.
- `possible_issue` — suspected issue without full evidence; state the uncertainty.
- `open_question` — needs HUMAN/author input to resolve; not yet a defect.
- `suggestion` — improvement idea, not a defect.
- `conflict` — the document contradicts Wiki/source/another reference; report, do not resolve
  silently.

## 3. Quality rules for findings

- Be specific and actionable — avoid generic findings ("improve clarity" with no location/fix).
- Separate defects, risks, open questions, and suggestions — do not blend them into one bucket.
- Every important finding carries evidence OR is explicitly marked as assumption / open question.
- Report conflicts; do not silently pick a side (Wiki-first NOT Wiki-only — when Wiki and source
  disagree, surface it for HUMAN decision).
- If the HUMAN later rejects a finding as a false positive and it is likely to recur, capture a
  `false_positive_note_candidate` (see `lesson_capture_rule.md`).
