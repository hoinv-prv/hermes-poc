# Command Spec — `/aiws-agent-run`

> **Status:** prompt/spec (file-first), backed by thin tooling `tooling/run_agent.py` (stdlib, `py`). NOT a full CLI.
> **Built by:** AIP-EXEC-142 (Agent Runtime Command Set; AP-CR-19/20, DDR-09/10).
> **Source:** `development/ai_agents/docs/agent_runtime_design.md`; mirrors `/run-aip` (thin orchestrator).
> **Scope:** assign a task to an existing Agent Instance, track progress, resume/stop. Does **not** create instances (`/aiws-agent-create`), does **not** confirm memory (`/aiws-agent-review-learning`).

## Purpose
Run one task on an Agent Instance. The tool **prepares state** (Active Run Context + run-folder + status); the **AI then acts as the agent** by reading the ARC. Single-shot happy path; resume/stop when a run is interrupted.

## Guardrails (always)
- **Run ≠ auto-run.** `start` only materializes the ARC + scaffolds the run-folder. The tool NEVER calls an LLM, NEVER does the task, NEVER chains/dispatches other agents. The AI does the task, HUMAN-prompted.
- **No auto-promotion:** run output = evidence; learning = candidate (HUMAN-gated via `/aiws-agent-review-learning`). Official Wiki / memory / blueprint are NOT auto-updated.
- **Honor the agent's `non_responsibilities`** (in ARC §3): review/advisory/PM agents propose, never approve/edit/execute.
- **`aip_driven` gate (AP-CR-25 presence + AP-CR-41 conformance):** an instance declaring `policies.run_policy.aip_driven: true` may NOT `start` without a driving `--aip <AIP-ID>` (**stage 1, presence**). **Stage 2 (AP-CR-41):** if it also declares `run_policy.aip_template`, the driving AIP's `template_source` (stamped by create-aip — CR-AIWS-2026-06-050) MUST match it, compared **basename-normalized** so `aip_template` can be given as a full ID, a short alias, OR a full path. Mismatch → **refuse before scaffolding** (names expected vs actual + points at `/create-aip --template <expected>`); a legacy AIP with **no `template_source` stamp** → **degrade-to-warn + proceed** (use `--strict-template` to refuse instead); unresolvable `--aip` → warn + proceed; `--aip` matching >1 file → ambiguous-refuse. All outcomes fire **before** scaffolding → **no orphan run-folder**. Instances without `run_policy` (or `aip_driven: false`, or no `aip_template`) behave exactly as before — **backward-compatible**.
- **Wiki-first NOT Wiki-only:** ground in Wiki/index first, verify important findings against source.
- Writes only under `agents/instances/<instance>/workspace/` (relative to the pack root; staging; boundary-guarded).

## Subcommands

### `start` — assign a task (AP-CR-20)
```
/aiws-agent-run start <instance> --task "<what to do>" [--slug <short>] [--aip <AIP-ID>] [--strict-template]
```
Tool: `py tooling/run_agent.py start <instance> --task "..."`
- Creates `workspace/active_runs/RUN-<ts>-<slug>/` (Phase C run templates copied) + `run_state.yaml` (status=active) + `00_active_run_context.md` (ARC).
- **`--aip <AIP-ID>` (AP-CR-25):** required when the instance declares `policies.run_policy.aip_driven: true` — the gate runs **before** scaffolding (refused start → no orphan run-folder; prints `/create-aip → /run-aip` guidance). When supplied, the id is seeded into `run_request.yaml` → `related_aip`, and ARC gains a **`## 8. Run policy`** section naming the driving AIP, `aip_template`, and a **`template_conformance:`** line (OK / MISMATCH / unverified) so the run is read as one step of that AIP. Optional / ignored for non-`aip_driven` instances.
- **`--strict-template` (AP-CR-41):** escalate the legacy degrade-to-warn (driving AIP without a `template_source` stamp) into a refuse-before-scaffold. Default off = warn-and-proceed (backward-compatible). No effect when conformance is already verifiable or the instance is non-`aip_driven`.
- **Then the AI** reads the ARC and acts as the agent: writes `output/` (per blueprint `output_templates/`), ticks `run_state.yaml` `progress`, captures ≥1 learning candidate to `learning_candidates.jsonl` (status=candidate). On finish, set `run_state.yaml` `status: completed` (or leave `incomplete` if stopping mid-way).

### `resume` — continue an interrupted run
```
/aiws-agent-run resume <instance> <run_id>
```
- Refreshes ARC + shows `run_state.yaml` (progress). AI reloads ARC + run-so-far (`output/`, `run_log.jsonl`, progress) and continues. Refuses if the run is `completed`/`stopped`.

### `status` — check progress / list runs
```
/aiws-agent-run status <instance> [run_id]
```
- With `run_id`: prints that run's status + `run_state.yaml`. Without: **lists** all runs (active + completed) and their status. Reconciles any `completed`/`stopped` run still in `active_runs/` → `completed_runs/`.
- This is where the HUMAN decides **resume vs stop** for an `incomplete` run.

### `stop` — abandon a run
```
/aiws-agent-run stop <instance> <run_id> [--reason "<why>"]
```
- Sets `status: stopped` (+ reason), moves the run to `completed_runs/` (evidence kept). Not deleted; rollback-friendly.

## Status lifecycle
`active` (open) → `incomplete` (exited, resume-able) → `completed` (done) / `stopped` (HUMAN abandoned). A run-folder with no `run_state.yaml` (pre-runtime runs) = `completed` (backward-compat).

## Outputs (per run)
`00_active_run_context.md` (ARC) · `run_state.yaml` (status+progress) · `output/` (agent deliverables) · `learning_candidates.jsonl` · `human_feedback.md` (via `/aiws-agent-feedback`) · plus the Phase C run-record files. On close the run sits in `completed_runs/`.

## Related
`/aiws-agent-create` (make the instance) · `/aiws-agent-feedback` (feedback on a run) · `/aiws-agent-review-learning` (confirm candidates → memory).
Lifecycle (AP-CR-27/28): `/aiws-agent-upgrade` (reconcile vs a newer blueprint) · `/aiws-agent-clone` (new instance from an existing one).
