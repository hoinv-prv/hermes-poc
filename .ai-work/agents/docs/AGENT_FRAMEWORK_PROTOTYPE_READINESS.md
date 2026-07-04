# Agent Framework Prototype — Package-build & Demo-test Readiness

> **STAGING / NON-CANONICAL.** Built by **AIP-EXEC-154** (reuse-first Agent Framework prototype).
> Pairs with draft **CR-AIWS-AGENT-FRAMEWORK-002** (`docs/agent_pack_impl_package/others/`).
> Purpose: let HUMAN build a package from this staging tree and test the prototype on the **demo project**, then iterate the spec before any promotion CR.
> All paths relative to the **pack root** (`development/ai_agents/` in the AIWS dev repo · `.ai-work/agents/` when installed, single-track) unless noted.

## 1. What changed in this prototype (the delta to test)

Additive only — nothing removed; existing instances/runs keep working.

| Change | File(s) | What to observe |
|---|---|---|
| **`lookup_intents` binding** (intent → index/source query) | `agents/templates/context/wiki_references.yaml` (default `[]` + commented example); `agents/instances/detailed_design_review_agent__sample_project/context/wiki_references.yaml` (3 real intents) | A process-named intent resolves through `lookup_wiki_source.py` (pointers, no auto-load); `--system` when multi_system |
| **ARC §4A — selection rationale** | `tooling/run_agent.py` (`_materialize_arc`) | Materialized ARC shows §4A: Process Interpretation · Selected/Excluded References · Reference Gaps · Assumptions · Limitations (scaffold the AI fills) + §4 `lookup_intents` note |
| **Create-time reference suggestion** | `commands/aiws-agent-create.md` (Wizard Step 4) | AI suggests candidate refs via `lookup_wiki_source.py` + project scan → HUMAN gates → populates context refs |
| **No-blueprint process bootstrap** | `commands/aiws-agent-create.md` (Mode C / Step 7 / Generated-files) | Custom no-blueprint create → AI bootstraps draft `process/agent_process.md` (markers) → HUMAN reviews |

No new subsystem: no `asset_mapping.yaml` / `asset_registry.yaml` / `project_agent_assets/` / standalone lookup-policy / context-pack / `process_steps.yaml`.

## 2. Build the package (ship-set)

Per `rollout/setup_guide.md` §3(b), the install ship-set is **definitions + commands + tooling, NO instances**. Copy this tree into the demo project's `.ai-work/agents/` (single-track install — CR-AIWS-2026-06-055; supersedes the two-track AP-CR-29):

```
agents/blueprint_registry.yaml
agents/blueprints/**          # incl. _shared/review/**
agents/templates/**           # << carries the updated context/wiki_references.yaml (lookup_intents)
commands/*.md                 # << carries the updated aiws-agent-create.md
tooling/run_agent.py          # << carries ARC §4A
```

> Do **not** ship `agents/instances/**` (the `*__sample_project` fixtures stay in staging). Instances are created on the demo via `/aiws-agent-create`.
> Because every internal ref is relative, the tree resolves identically wherever it lands.

## 3. Test on the demo project

**Prereq:** the demo project has a Knowledge Hub (Wiki Source Index at `.ai-work/wiki_sources/index.jsonl`). Run Python with `py`.

### 3.1 Blueprint-based + lookup_intents + ARC §4A
1. `/aiws-agent-create blueprint=detailed_design_review_agent` (Mode A) — at Wizard Step 4, AI **suggests** demo refs (via `lookup_wiki_source.py` on demo's index); accept the relevant ones → they populate `context/wiki_references.yaml` (`recommended_entries` + `lookup_intents`), `source_references.yaml`, `working_inventory.yaml`.
2. Edit the instance's `context/wiki_references.yaml` `lookup_intents` so `search_targets` use the **demo's real source_type / reference_type** (per Task-Lens bridge: `*_guideline/*_checklist → process_guideline`, `*_template → process_template`, `sop → sop`; requirement/design = demo's own types).
3. `py tooling/run_agent.py start <instance_id> --task "[test] review detailed design of <function>" --aip <demo AIP>` (this blueprint is `aip_driven:true`).
4. Open the run's `00_active_run_context.md` → confirm **§4A** scaffold + §4 `lookup_intents` note. Acting as the agent, resolve each intent via `lookup_wiki_source.py --query <kw> --source-type <search_targets> [--system <id>]` and fill §4A (Selected/Excluded/Gaps/Assumptions/Limitations). Unresolved intent → apply its `fallback`.

### 3.2 No-blueprint custom + process bootstrap
1. `/aiws-agent-create mode=custom` (Mode C) — AI **bootstraps** a draft `process/agent_process.md` from the stated mission (markers: Reference intents / Wiki lookup intents / Expected output / HUMAN gate / Constraints); review/edit it.
2. At Step 4, AI suggests refs; accept → populates context refs incl. `lookup_intents`.
3. `py tooling/run_agent.py start <instance_id> --task "[test] ..."` → confirm ARC §4A renders for the no-blueprint instance too.

### 3.3 Smoke
- Re-use `rollout/smoke_test_checklist.md` (registry resolves blueprints; create ≠ run; empty-skeleton memory; run materializes ARC; feedback → candidate not auto-confirmed; review-learning no auto-confirm; guardrails).
- New prototype checks: ARC §4A present; an intent with a registered demo asset resolves to a pointer; an intent with no asset hits its `fallback`.

## 4. Verification status in staging (this AIP)

- `py -m py_compile tooling/run_agent.py` → OK.
- `py tooling/lint_agents.py` → **errors=0** (4 warnings = pre-existing legacy runs missing `run_state.yaml`).
- `py .ai-work/tooling/lint_all.py` → **0 NEW** errors/warnings (the 1 error is the pre-existing `TASK-20260622-exec-148` capture-inbox `missing field: title`).
- MOCK validation runs (stopped, in `completed_runs/`): ARC §4A rendered on `detailed_design_review_agent__sample_project` (blueprint-based) and `custom_wiki_advisor_agent__sample_project` (no-blueprint).

## 5. Iterate before promotion

This is a **draft + staging prototype** (HUMAN task 3 = refine before promote). After demo testing, refine CR-002 / the 7 open-question defaults (`05_open_questions.md` of TASK-20260623-exec-154), then prepare a **promotion CR** (allocate AP-CR ≥42; reconcile AP-DDR-07 via the AP-DDR-33 draft) to land deltas into `01–09` + `.ai-work/agents/`. Promotion is CR-gated (rule #8 / AIWS-Product-Owner) — **not** part of this prototype.
