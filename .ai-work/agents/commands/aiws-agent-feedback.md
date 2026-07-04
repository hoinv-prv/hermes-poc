# Command Spec — `/aiws-agent-feedback`

> **Status:** prompt/spec (file-first). NOT an executable CLI.
> **Built by:** AIP-EXEC-142 (Agent Runtime Command Set; AP-CR-21, DDR-11).
> **Source:** `development/ai_agents/docs/agent_runtime_design.md` §5; Requirements v0.4 §6 (FR-MEM-04 no-auto-learning).
> **Scope:** record HUMAN feedback on a completed/active run and turn it into learning **candidates**. Does **not** confirm memory (that stays in `/aiws-agent-review-learning`).

## Purpose
Capture a HUMAN's feedback on an agent run so the instance can improve — **without** writing memory directly. Feedback becomes `human_feedback.md` evidence + learning **candidates** that a later HUMAN gate confirms.

## Guardrails (always)
- **No direct memory write.** Feedback NEVER touches `memory/confirmed_memory.jsonl`. It only appends evidence + emits candidates (`status=candidate`). Confirmation is the existing 2-step gate `/aiws-agent-review-learning` → confirmed memory (FR-MEM-04).
- **No auto-learning / no auto-promotion.** Candidates stay candidates until HUMAN confirms.
- Writes only under the run-folder + the instance `training/` (staging; boundary-guarded).

## Flow
```
/aiws-agent-feedback <instance> <run_id>
```
1. **Append to run evidence:** add the HUMAN feedback to the run-folder `human_feedback.md` (dated; verbatim + any AI-noted interpretation).
2. **Emit learning candidate(s)** — `status: candidate` — to **BOTH** (OQ-4):
   - run-local `learning_candidates.jsonl` (evidence tied to this run), and
   - instance `training/candidate_queue.jsonl` (the queue `/aiws-agent-review-learning` scans).
   Candidate kinds (per `agents/templates/learning_candidate_schema.md`): memory / lesson / retrieval-hint / local-guideline / skill-improvement / blueprint-improvement / **process-improvement** (`process_improvement_candidate` — AP-CR-31; proposes a change to the instance's OWN `process/`, applied on confirm by `/aiws-agent-review-learning`) / tool / wiki candidate.
3. **Point to confirmation:** tell the HUMAN to run `/aiws-agent-review-learning` to review/confirm candidates → `confirmed_memory.jsonl` (or reject/defer). Nothing is promoted here.

## What it does NOT do
- Does not run the agent (`/aiws-agent-run`), does not confirm/auto-apply candidates, does not edit the blueprint, does not write Official Wiki.

## Related
`/aiws-agent-run` (produce the run being fed back on) · `/aiws-agent-review-learning` (confirm candidates → memory) · `agents/templates/learning_candidate_schema.md` + `confirmed_memory_schema.md`.
Lifecycle (AP-CR-27/28): `/aiws-agent-upgrade` (reconcile vs a newer blueprint) · `/aiws-agent-clone` (new instance from an existing one; carried memory is review-flagged).
