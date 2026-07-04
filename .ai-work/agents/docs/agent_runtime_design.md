# Agent Runtime Design — run/feedback (AI Agents Pack, staging)

> **Status:** staging design (non-canonical). **Source:** DDR-09/10/11 + AP-CR-19/20/21 (`docs/agent_pack_impl_package/docs/08_/09_`).
> **Built by:** AIP-EXEC-142 STEP-01 (Design deliverable, embedded). **Mental-model:** mirrors `/run-aip` (thin orchestrator).
> **Reuses:** Phase C run schema (`development/ai_agents/agents/templates/run/`) — this design only **ADDS** `run_state.yaml` + `00_active_run_context.md`; it does **not** modify the existing run-record fields.

The Agent Runtime Command Set lets a HUMAN **assign a task to an agent instance, track progress, resume/stop, and give feedback** — file-first, HUMAN-controlled, no auto-run, no auto-promotion. The runtime is a **thin orchestrator** (`run_agent.py`): it prepares state (Active Run Context + run-folder + status) for the AI to **act as the agent**; it never calls an LLM, never auto-runs a task, never chains agents.

## 1. Run model

- **One run = one task assignment** to one instance. Happy path = **single-shot** (AI reads the Active Run Context, does the task in-session, writes the run-record).
- A run can be **interrupted** (long task / AI stopped mid-way). The HUMAN inspects progress via `status` and decides **resume** or **stop**.
- **Lifecycle `status`** (OQ-3):
  | status | meaning |
  |---|---|
  | `active` | run open / in progress (just started, or being worked) |
  | `incomplete` | exited before done — **resume-able** (work remains) |
  | `completed` | task done; run closed |
  | `stopped` | HUMAN stopped/abandoned; run closed (evidence kept) |
- **Folder placement:** an open run lives under `instances/<id>/workspace/active_runs/RUN-<id>/`; on `completed`/`stopped` it **moves** to `workspace/completed_runs/RUN-<id>/` (mirror Phase C).
- **Task Workspace reuse (agent-via-AIP) — CR-AIWS-2026-06-057 Phase 1:** when the instance is `aip_driven` and the run is started with a driving `--aip`, the run does **not** create a separate in-instance run-folder — it **reuses the driving AIP's Task Workspace** (`.ai-work/workspaces/{account}/{task_id}/`, resolved via the AIP's write-once `runtime_workspace` pointer). The run's ARC + `run_state.yaml` + `run_request.yaml` + `output/` materialize INTO that Task Workspace; the instance keeps a boundary-legal `run_index.jsonl` back-pointer (so `status`/`resume`/`stop` still resolve the run). Captures tier up to that Task Workspace's `08_capture_inbox.jsonl` (applied CR-042 C1). This removes the "two workspaces to track" problem for agent-via-AIP. A no-AIP / agent-only run keeps the in-instance folder above (Task-Workspace generalization for agent-only is CR-057 Phase 2).
- **Backward-compat (R-6):** a run-folder with **no** `run_state.yaml` (e.g. the EXEC-139 sample run) is treated as `completed`. Additive only — existing run-records stay valid.

## 2. `run_state.yaml` schema (NEW — additive, OQ-2)

One per run-folder. Plain/literal YAML only (no folded `>-`). Holds status + progress so the run is resume-able and inspectable.

```yaml
# run_state.yaml — runtime state of one agent run (additive to Phase C run-record)
run_id: RUN-20260621-0930-mock-design
agent_instance_id: detailed_design_review_agent__sample_project
status: active            # active | incomplete | completed | stopped
created_at: "2026-06-21"
updated_at: "2026-06-21"
stopped_reason: null      # filled only when status=stopped
progress:                 # ordered checklist the AI ticks as it works (resume reads this)
  - step: read ARC + task request
    done: true
  - step: produce review_report
    done: false
notes: <one-line current-state note for the HUMAN>
```

- `status` is the single source of truth for lifecycle. `progress` is a coarse checklist (NOT per-token) — enough for a HUMAN to judge resume vs stop.
- `run_agent.py` reads/writes ONLY this file for state; it does not parse `run_log.jsonl` for status.

## 3. Active Run Context (ARC) — `00_active_run_context.md` (NEW)

Materialized by `run_agent.py start` (and refreshed by `resume`) into the run-folder. It is the **focused reading surface** the AI reads to act as the agent — analogous to `00c_active_step_context.md` (ASC) for AIPs. Sections:

1. **Run identity** — run_id, instance_id, status, created_at.
2. **Task request** — the HUMAN's task prompt (free text the HUMAN supplies).
3. **Agent definition (from blueprint via `blueprint_ref`)** — mission · responsibilities · **non_responsibilities** · skills (skill_index) · process (refs) · output_templates (refs).
4. **Context (from instance `context/`)** — wiki_references · source_references · source_priority · **working_inventory** (non-wiki files) · ignored_paths.
5. **Confirmed memory** — instance `memory/confirmed_memory.jsonl` (load confirmed-only; newest-first) + lessons/local_guidelines.
6. **Output contract** — where to write outputs (`output/`) + which templates; learning candidates → `learning_candidates.jsonl`.
7. **Guardrails** — Wiki-first-not-Wiki-only · no auto-promotion · HUMAN-gated · the agent's non_responsibilities.

ARC is a **read surface for the AI**; `run_agent.py` assembles it by reading the instance + blueprint files (it does not invent content).

## 4. Subcommand semantics — `/aiws-agent-run <sub>` (AP-CR-19/20)

`run_agent.py` does state prep ONLY; the **AI** does the task by reading ARC. (OQ-5)

| subcommand | tooling (`run_agent.py`) does | AI then does |
|---|---|---|
| `start <instance> [--task "..."]` | create `active_runs/RUN-<ts>-<slug>/` from Phase C templates; write `run_request.yaml` + `run_state.yaml` (status=active); materialize `00_active_run_context.md` from blueprint+context+memory+task | read ARC → act as agent → write `output/` + `learning_candidates.jsonl`; tick `progress`; set status `completed` (or leave `incomplete`) |
| `resume <run>` | refresh ARC; show `run_state.yaml` (progress) | reload ARC + run-so-far → continue → update progress/status |
| `status [instance|run]` | read `run_state.yaml`; with no run-id → **list** runs of the instance + their status | (decide resume/stop) |
| `stop <run> [--reason]` | set status=`stopped` + `stopped_reason`; move to `completed_runs/` | — |
| *(completed)* | when AI sets status=`completed`, tooling moves run → `completed_runs/` | — |

- **No `start` auto-runs the task.** Tooling stops after materializing ARC; the AI (prompted by HUMAN) does the work. No chaining/dispatch of other agents.

## 5. Feedback flow — `/aiws-agent-feedback <run>` (AP-CR-21)

```
HUMAN feedback on a run
  → append to run-folder human_feedback.md
  → emit learning candidate(s) status=candidate to BOTH (OQ-4):
       • run-folder  learning_candidates.jsonl   (run-local evidence)
       • instance    training/candidate_queue.jsonl   (review queue)
  → /aiws-agent-review-learning  (existing)  → HUMAN confirm → confirmed_memory.jsonl
```

- **NO direct memory write** (FR-MEM-04): feedback only produces candidates; confirmation is the existing 2-step HUMAN gate. `run_agent.py`/feedback never touch `confirmed_memory.jsonl`.

## 6. `run_agent.py` scope / boundaries (OQ-5, R-1/R-4)

- **Thin wrapper, stdlib-only**, run with `py` (bare `python` broken on this machine); UTF-8 stdout (cp932-safe). Mirror `run_aip.py` structure (argparse subcommands + boundary guard).
- Does: scaffold run-folder, write/read `run_state.yaml`, materialize/refresh ARC, list/show runs, move active→completed.
- Does **NOT**: call an LLM, act as the agent, auto-run/loop/chain, write `confirmed_memory.jsonl`, write outside `development/ai_agents/`.
- **Boundary guard:** refuse any write whose resolved path is outside `development/ai_agents/` (mirror `run_aip.py` `_ensure_inside`).

## 7. Guardrails (carry pack philosophy)

- File-first · HUMAN invokes each run (no auto-run/chain) · single-shot happy path · resume is HUMAN-driven.
- No auto-promotion: output = evidence, learning = candidate (HUMAN-gated via review-learning); Official Wiki / memory / blueprint not auto-updated.
- Staging-only (`development/ai_agents/`); promotion → canonical = future CR (AP-CR-10).

## 8. Relationship to existing surfaces

- **Reuses** Phase C run-record (run_request/run_context/run_log/output/used_*/human_feedback/learning_candidates) — adds `run_state.yaml` + `00_active_run_context.md`.
- **Complements** `/aiws-agent-create` (makes the instance) and `/aiws-agent-review-learning` (confirms candidates). The **Core runtime** group = create → run → feedback → review-learning; the **Instance lifecycle** group (upgrade / clone / rename) maintains an instance after creation; `/aiws-agent` is the **Convenience router** over both.
- DD §8 addendum: `run_state.yaml` + ARC are the runtime additions to the §8 run/workspace model (additive; §8 fields unchanged).
