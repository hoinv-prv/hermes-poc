# Lesson Capture Rule (shared)

> Shared across all Document Review Agent blueprints.
> Mapped from: MEMORY_AND_LEARNING_RULES_TEMPLATE.md + REVIEW_AGENT_BLUEPRINT_TEMPLATE.md §13-§16
> (v0.1).
> Document-type-agnostic.

---

## 1. Core rule

```text
Run output is evidence.
Learning candidate is a proposal.
Confirmed memory requires HUMAN approval.
```

The agent never auto-confirms a candidate, never overwrites Official Wiki, never updates a
checklist or blueprint on its own. Promotion is HUMAN-gated.

> ⚖ **governance_invariant** `no_auto_promote` — never auto-confirm a candidate or overwrite Wiki / checklist / blueprint / **the instance's own process**; promotion is HUMAN-gated (incl. `process_improvement_candidate`, AP-CR-31).

## 2. When to capture

After each meaningful review run, propose learning candidates when useful — and inline on
discovery, not only at the end. Typical triggers:
- a recurring document-type review point worth adding to a checklist,
- a project-specific reference-navigation hint,
- a HUMAN-rejected finding likely to recur (false positive),
- a recurring project issue pattern,
- an output-format preference the HUMAN asked for,
- official project knowledge discovered during review (wiki_candidate),
- a reusable rule worth pushing to the blueprint (blueprint_improvement_candidate).

## 3. Candidate types

```text
review_rule_candidate
checklist_update_candidate
retrieval_hint_candidate
false_positive_note_candidate
project_issue_pattern_candidate
output_preference_candidate
wiki_candidate
blueprint_improvement_candidate
process_improvement_candidate
```

> **`process_improvement_candidate` (AP-CR-31) — universal kind, all agents.** Proposes a change to **this instance's own process** (`instances/<id>/process/`, FR-AI-13 / Detailed Design §6D). On HUMAN confirm via `/aiws-agent-review-learning` it is written to the instance process + an Instance `changelog.md` entry (`layer: override`, `source: learning-candidate`). It must NOT drop/weaken a `governance_invariant` step. Never agent-self-applied (`no_auto_promote`).

## 4. Candidate schema (JSONL)

```json
{
  "candidate_id": "LC-YYYYMMDD-001",
  "source_run": "RUN-YYYYMMDD-HHMM-<short_task_name>",
  "type": "checklist_update_candidate",
  "scope": "<review_scope>",
  "content": "<candidate content>",
  "evidence": "<why this candidate was proposed>",
  "recommended_destination": "memory | checklist | wiki | blueprint",
  "status": "candidate"
}
```

All entries are emitted with `status: candidate`. Allowed statuses over the lifecycle:
`candidate / confirmed / rejected / deferred / deprecated` (Detailed Design v0.2 §14).

## 5. Destination rules

```text
Agent Instance Memory:   project/context-specific review behavior, retrieval hints, false positives.
Checklist Update:        recurring document-type-specific review point.
Wiki Candidate:          official project knowledge discovered during review.
Blueprint Improvement:   reusable rule for future agents of this document type.
```

## 6. Capture routing by run context (Detailed Design v0.2 §14 / AP-CR-13)

- Agent running UNDER an AIP: tier the capture UP to the project capture inbox
  `08_capture_inbox.jsonl` / the wiki-candidate flow; the instance keeps only a POINTER back to
  that capture (not a duplicate).
- Agent running WITHOUT an AIP: the capture stays local in the instance
  `training/candidate_queue.jsonl`.

In both branches, promotion to confirmed memory / Official Wiki remains HUMAN-gated.

## 7. Where candidates are written

```text
workspace/completed_runs/<run_id>/learning_candidates.jsonl   (per-run evidence)
training/candidate_queue.jsonl                                (instance-level queue)
```

## 8. No auto-promotion

Instance memory files start EMPTY. Candidates are never auto-confirmed. Confirmed memory, checklist
updates, Wiki candidates, and blueprint improvements are applied only after HUMAN approval (see
`document_review_process.md` Step 8-9).
