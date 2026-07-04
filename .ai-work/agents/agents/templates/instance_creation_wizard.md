# Instance Creation Wizard — HUMAN question flow

> Used by `/aiws-agent-create` (commands/aiws-agent-create.md). 8-step flow; 11 init categories.
> Keep it sufficient but not heavy — skip questions whose answer is already given on the command line.

## Step 1 — Purpose
- What should this agent support? (build wiki meta / refresh wiki / create extraction tool /
  consume wiki for AIP planning / task context prep / output review / other)

## Step 2 — Blueprint selection or Custom mode
- Mode A: confirm the named Blueprint.
- Mode B: AI recommends Blueprint(s) + reason → HUMAN accepts / picks another / switches to custom.
- Mode C: custom no-Blueprint → collect the `agent_design_snapshot.yaml` minimum fields.

## Step 3 — Identity  *(category: identity, project/context scope)*  *(AP-CR-23)*
- **`display_name`?** *(ask FIRST)* — a friendly person-name HUMAN label (e.g. `Henry`). Renamable.
- project / context name?
- suggested `instance_id`? — auto-suggest from the blueprint, then confirm. Convention:
  - `<blueprint_short>` — single-project default (one instance of the blueprint).
  - `<blueprint_short>_<NN>` — multiple instances of the SAME blueprint (e.g. `_01`, `_02`).
  - append `__<project>` ONLY for multi-project / shared-pool setups.
  - `instance_id` = stable machine key — **never renamed** once set (rename `display_name` instead).
- owner / reviewer?

## Step 4 — Mission customization  *(category: mission)*
- What is the instance's specific mission emphasis for this project?

## Step 5 — Context references  *(categories: wiki refs, source doc refs, source code paths, ignored paths)*
- wiki index / path? relevant existing wiki entries?
- source document folders?
- source code folders?
- ignored paths (generated/vendor/cache)?
- priority modules / domains?

## Step 6 — Tool bindings  *(category: tool bindings)*
- bind existing tools? (list tool ids) — or declare tooling needs (candidate tools stay agent-local, no auto-activate)

## Step 7 — Policies  *(categories: memory, workspace, review/HUMAN-gate)*
- memory policy (default: capture after run, no auto-confirm, HUMAN review required)
- workspace policy (default: save run history + handoff artifacts)
- review / HUMAN-gate policy (default: HUMAN review for memory_update / tool_activation / wiki_candidate / blueprint_improvement)

## Step 8 — Generate + Summary
- Generate the instance folder skeleton from templates.
- **Process (AP-CR-31 / §6D):** A/B (blueprint-based) → copy the blueprint's effective process (`process_docs`-resolved set, flattened/self-contained) into `process/` + capture `.blueprint_snapshot/process/`; C (custom) → author a minimal own `process/`. The instance owns its process thereafter (`governance_invariant` steps must not be silently dropped).
- Write `instance_readme.md`; produce `instance_setup_summary` (instance_setup_summary.md) for HUMAN review.
- **STOP** — do not run the agent (FR-CMD-08).
