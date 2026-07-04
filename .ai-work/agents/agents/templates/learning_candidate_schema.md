# Learning Candidate Schema (Detailed Design v0.2 §14)

Learning candidates are proposed from runs / HUMAN feedback. They live UNCONFIRMED until HUMAN review.

- Per-run: `workspace/completed_runs/<RUN>/learning_candidates.jsonl` (the run-folder template ships **EMPTY**; see `templates/run/learning_candidates.example.jsonl` for a sample row — AP-CR-39)
- Instance queue: `training/candidate_queue.jsonl`

## JSONL record
```json
{"candidate_id":"LC-001","agent_instance_id":"<instance_id>","type":"retrieval_hint","status":"candidate","content":"<content + inline evidence>","source_run":"<RUN-id>","created_at":"<YYYY-MM-DD>"}
```

### Fields
| Field | Required | Notes |
|---|---|---|
| `candidate_id` | yes | unique within instance (LC-NNN) |
| `agent_instance_id` | yes | owning instance |
| `type` | yes | candidate type (below) |
| `status` | yes | `candidate` / `confirmed` / `rejected` / `deferred` / `deprecated` |
| `content` | yes | the proposed learning + inline evidence |
| `source_run` | yes | RUN-id that produced it |
| `created_at` | yes | date |

### Candidate types
memory_candidate · lesson_candidate · retrieval_hint · local_guideline_candidate · tool_usage_note_candidate ·
skill_improvement_candidate · tool_improvement_candidate · **blueprint_improvement_candidate** · **process_improvement_candidate** · wiki_candidate

> `blueprint_improvement_candidate` is routed SEPARATELY from instance memory (FR-AI-05) — it never auto-updates a Blueprint.
> `process_improvement_candidate` (AP-CR-31) proposes a change to the instance's OWN `process/` (Detailed Design §6D); on confirm `/aiws-agent-review-learning` writes the instance process + an Instance `changelog.md` entry (`layer: override`, `source: learning-candidate`), and must not drop/weaken a `governance_invariant` step.
> Nothing here is auto-promoted (FR-MEM-04). Promotion to confirmed memory is via `/aiws-agent-review-learning` (HUMAN).
