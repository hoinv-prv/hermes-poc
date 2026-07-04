# Command Spec — `/aiws-agent-clone`

> **Status:** prompt/spec (file-first), backed by thin tooling `tooling/run_agent.py` (stdlib, `py`). NOT a full CLI. Post-MVP lifecycle verb.
> **Built by:** AIP-EXEC-146 (Instance lifecycle; AP-CR-28, AP-DDR-16).
> **Source:** Detailed Design §6B + §5 + §4A; requirements FR-AI-11; [09 AP-CR-28](../../../docs/agent_pack_impl_package/docs/09_Change_Requests.md).
> **Scope:** create a **new** Agent Instance from an **existing** one (horizontal reuse) when a trained instance is a better starting point than its Blueprint. Does **not** run the new instance (`/aiws-agent-run`), does **not** confirm the carried-over memory (`/aiws-agent-review-learning`), does **not** modify the source.

## Purpose
When an Instance has been customized/trained well beyond its Blueprint, recreating from the Blueprint and re-training wastes that work. `/aiws-agent-clone` copies the source's **instance-owned layer** into a new instance with a new identity, flags the carried-over memory for review, and records lineage — so the new project starts from the trained baseline, not from scratch.

## HARD RULE — full-copy minus run-history; carried memory is review-flagged, never auto-confirmed
The clone copies config + context + learned/confirmed memory + change-log + the Blueprint reference (pinned version + snapshot), but **not** run-history, and it **resets** the candidate queue. Every copied confirmed-memory entry is marked **`clone_review: pending`** (+ `cloned_from`) — it is **not** silently dropped and **not** auto-confirmed; the HUMAN keeps or prunes it **for the new project** via `/aiws-agent-review-learning`. The command does **not** run the agent and does **not** modify the source.

## Guardrails (always)
- **Clone ≠ run.** No LLM, no auto-run, no chaining. The clone is a new instance at rest.
- **New identity:** a new `instance_id` is minted (validated + collision-checked) plus the new `display_name`; the source `instance_id` is never reused or renamed (AP-CR-23 identity rules).
- **Auto-flag-review, not auto-keep:** carried confirmed-memory is `clone_review: pending` → HUMAN keep/prune (no silent drop, no auto-confirm — FR-MEM-01/04).
- **Source is read-only.** The clone never writes to the source instance.
- Writes only under `agents/instances/<new_id>/` (relative to the pack root; staging; boundary-guarded).

## Invocation
```
/aiws-agent-clone <source> --as "<display_name>" [--id <new_instance_id>] [--why "<reason>"]
```
Tool: `py tooling/run_agent.py clone <source> --as "<display_name>" [--id <id>] [--why "..."]`
- `<source>` resolves via the fuzzy resolver (partial id / role word / `display_name`). `--as` (required) sets the new `display_name`. `--id` overrides the auto-derived id (default: derived from `--as`, collision-suffixed). `--why` is recorded in lineage + changelog.

## What it does
1. **Full-copy the instance-owned layer:** `instance.yaml` (new id/display_name; `created_at` reset, `last_reviewed_at: null`), `instance_readme.md`, `agent_design_snapshot.yaml` (custom only), `blueprint_ref.yaml` (+ lineage; keeps pinned `blueprint_version` + `.blueprint_snapshot/`), `.blueprint_snapshot/`, `context/`, `memory/`, `tools/`, `changelog.md`.
2. **Exclude / reset (no run-history):** the whole `workspace/` is recreated **empty**; `training/candidate_queue.jsonl` + `feedback_log.jsonl` + `periodic_review_log.md` start fresh.
3. **Auto-flag-review:** each copied `memory/confirmed_memory.jsonl` entry gets `clone_review: "pending"` + `cloned_from: <source_id>` (malformed lines copied verbatim, not flagged).
4. **Lineage:** `cloned_from` / `cloned_at` / `clone_why` recorded in `blueprint_ref.yaml`; a clone entry prepended to the instance `changelog.md` (`layer: override`, `source: HUMAN-feedback`).

## After cloning
- Review the carried-over memory for the new project: `py tooling/run_agent.py memory <new_id>` → then `/aiws-agent-review-learning` to keep/prune the `clone_review: pending` entries.
- The clone keeps the source's pinned Blueprint version + snapshot, so it **still reconciles vs its Blueprint** via `/aiws-agent-upgrade`.

## Outputs
A new `agents/instances/<new_id>/` (instance-owned layer copied; run-history empty; memory flagged for review; lineage recorded). Source instance unchanged.

## Related
`/aiws-agent-create` (make a fresh instance from a Blueprint instead) · `/aiws-agent-upgrade` (reconcile the clone vs its Blueprint) · `/aiws-agent-rename` (change an instance's id + folder, with a `previous_ids` alias) · `/aiws-agent-review-learning` (keep/prune the carried-over `clone_review` memory) · `/aiws-agent-run` (run the new instance).
