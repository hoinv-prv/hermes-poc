# Capture and Triage Rules

## Principle
Capture first, curate later.

## Flow
Runtime discoveries → Capture Inbox → Triage → Promote / Archive / Discard

## Safety rules
- do not promote directly to Truth by default
- if unsure between Curated and Reference → choose Reference
- if unsure between Curated and Truth → choose Curated

## Intake rule — external / downstream IR (adversarial verify)
An external or downstream **improvement-request (IR)** describes THAT project's state, not
necessarily this canonical's. Before folding ANY IR claim into a plan or CR:
- **Verify each claim against canonical** (file/line) — confirm the named file/symbol/token
  actually exists and behaves as claimed.
- **Reject or annotate** false premises; fold in **only verified** claims.
- Evidence this matters: AIP-082 demo IR — 3/5 claims carried false premises (wrong linter file, phantom tokens/targets).
(Operationalises `AIWS_Change_Request_Spec_MVP` §17 source-basis rule.)
