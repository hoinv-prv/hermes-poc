# Source Trace Rule (shared)

> Shared across all Document Review Agent blueprints.
> Mapped from: REVIEW_AGENT_BLUEPRINT_TEMPLATE.md §10 (Source/Wiki Usage Policy) + §7 (Review
> Principles) (v0.1).
> Document-type-agnostic.

---

## 1. Wiki-first, NOT Wiki-only

> ⚖ **governance_invariant** `wiki_first` — read Wiki first but verify important findings against source; never Wiki-only.

The agent reads relevant Wiki entries FIRST to understand project context, terminology, design
decisions, cautions, and source-navigation hints. Wiki is the starting point for grounding — it is
NOT the sole authority. For findings that matter, the agent verifies against the underlying
source / reference documents.

## 2. Evidence requirement for important findings

> ⚖ **governance_invariant** `evidence` — important findings cite source/reference; an inference is marked assumption / open question, never presented as confirmed fact.

For each important finding, identify the supporting source / reference when available and record it
in the Evidence / Reference column (see `finding_format.md`):
- cite the specific Wiki entry, source document, section, or line.
- if the finding is based only on inference, mark it `possible_issue` or `open_question` and state
  that it is an assumption — do NOT present an inference as a confirmed fact.

## 3. Conflict policy

> ⚖ **governance_invariant** `conflict_report` — report conflicts as findings; never silently resolve or pick a side.

If the target document conflicts with Wiki / source / reference documents:
- REPORT the conflict as a `conflict`-type finding.
- do NOT silently resolve it or silently pick a side.
- when Wiki and source disagree, surface both and request a HUMAN decision if it affects the
  review outcome.

## 4. Staleness / uncertainty

When a Wiki entry is stale or unverified, prefer the source and note the staleness. Source
verification is required when:
- the Wiki entry is stale or unverified,
- a source / code conflict is detected,
- the output will feed an official deliverable.

## 5. Trace recorded in references_used

All Wiki entries and source documents actually used are listed in `references_used.md` (shared
output template) with what each was used for — so a reader can audit the grounding of the review.
