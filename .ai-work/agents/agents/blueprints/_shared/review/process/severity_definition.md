# Severity Definition (shared)

> Shared across all Document Review Agent blueprints.
> Mapped from: REVIEW_AGENT_BLUEPRINT_TEMPLATE.md §11 (v0.1).
> Document-type-agnostic baseline. A document-type blueprint MAY add type-specific examples for
> each tier in its own profile/checklist, but MUST NOT change the meaning of the tiers below.

---

## Severity tiers

### Critical
Causes serious requirement/design failure, data loss, security risk, release blocker, or major
implementation misdirection. Must be resolved or explicitly accepted by HUMAN before the document
is used downstream.

### Major
Likely to cause a bug, rework, missing requirement, test failure, or handoff misunderstanding.
Should be fixed before the document is relied on.

### Minor
Reduces clarity or completeness but does not block implementation or review. Fix when convenient.

### Suggestion
Improvement idea for readability, maintainability, or future quality. Optional.

---

## How to assign severity

- Severity reflects implementation / project RISK, not how easy the finding was to spot.
- A finding with no evidence is not automatically Minor — assess the risk if the suspicion is
  correct, then mark it as `possible_issue` or `open_question` (see `finding_format.md`).
- A conflict between the document and Wiki/source is at least Major; raise to Critical when it
  would cause a release blocker or data/security problem if shipped.
- When unsure between two tiers, pick the higher tier and state the uncertainty in the finding.

---

## Per-type examples (blueprint-local)

Each document-type blueprint supplies concrete examples for its type, e.g.:
- Critical example: <type-specific>
- Major example: <type-specific>
- Minor example: <type-specific>
- Suggestion example: <type-specific>

These examples illustrate the tiers for that document type; they do not redefine the tiers.
