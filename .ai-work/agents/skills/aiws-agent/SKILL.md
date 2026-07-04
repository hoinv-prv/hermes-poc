---
name: aiws-agent
description: >
  NL front-door router for the AI Agents Pack — resolve an Agent Instance + intended verb from a
  natural-language request, CONFIRM with the HUMAN, then dispatch to the matching gated verb. The
  router itself NEVER mutates state. TRIGGER when the user refers to an agent instance by
  name/role/display_name or asks to operate one — e.g. "cho <tên> review thiết kế ...", "tạo agent
  mới / create agent", "clone agent X / nhân bản agent", "upgrade agent theo blueprint", "đổi tên /
  đổi id agent / rename agent", "chạy /
  run / review qua agent <X>", "resume / status / stop run của agent", "feedback cho run của agent",
  "duyệt learning candidate / confirm memory cho agent", "agent X có gì / đã học gì / list agents".
  This is the AI Agents Pack (development/ai_agents/) — NOT /run-aip, /create-aip, or the wiki skills.
  If the user has ALREADY named the exact verb (e.g. invokes a verb spec directly / "dùng lệnh clone"),
  follow that verb directly — do not add a routing layer on top.
user-invocable: true
---

# SKILL: aiws-agent — NL front-door router (AI Agents Pack)

> Convenience layer over the gated verbs (`create | run | feedback | review-learning | upgrade | clone`)
> + `run_agent.py list/memory`. NOT a verb itself, NOT a CLI. Auto-activates from natural language so you
> needn't remember each verb. Spec: `development/ai_agents/commands/aiws-agent.md`.

## ⚠️ PATH BASE (per environment)
In THIS repo (AIWS) the pack is staged under **`development/ai_agents/`** (tooling + specs) — use the paths
below. In an installed project the same pack lives under **`.ai-work/agents/`** (single-track — trial and
matured) — rebase the paths to the local install. The router only READS
(`list` / `memory` / fuzzy match); it writes nothing.

## HARD RULE — the router NEVER mutates
No memory write, no `status: completed`, no learning-candidate emit/confirm, no run-folder scaffold, no
blueprint/Wiki edit. **Every mutation goes through a gated verb** (create | run | feedback | review-learning
| upgrade | clone) or the `run_agent.py` subcommand it wraps. Router = **resolve read-only → HUMAN confirm →
hand off.** Ambiguous instance or unclear verb → **STOP and ask** (never guess-then-act).

## Flow
1. **Parse** the NL request → instance token (partial id / role word / `display_name` like "Henry") + intended verb + task/detail.
2. **Resolve instance (read-only):**
   ```bash
   py development/ai_agents/tooling/run_agent.py list
   ```
   Require a UNIQUE match. Ambiguous / none → print `list` and ask the HUMAN to choose. (Use `... memory <instance>` to disambiguate by what it knows.)
3. **Map verb** → create | run (start|resume|status|stop) | feedback | review-learning | upgrade | clone | rename.
4. **CONFIRM** with the HUMAN — restate (instance + verb + task) in one line and wait for an explicit go before dispatch.
5. **Execute-inline:** follow the chosen verb's spec (`development/ai_agents/commands/aiws-agent-<verb>.md`); its own gates apply and own all audit. Tool-backed verbs run `py development/ai_agents/tooling/run_agent.py <subcommand>`.

## Verb map (quick reference)
| Intent (NL) | Verb | Spec |
|---|---|---|
| tạo / create agent (blueprint / custom) | create | `development/ai_agents/commands/aiws-agent-create.md` |
| chạy / run / review / resume / status / stop | run | `development/ai_agents/commands/aiws-agent-run.md` |
| feedback / nhận xét cho run | feedback | `development/ai_agents/commands/aiws-agent-feedback.md` |
| duyệt / confirm learning candidate | review-learning | `development/ai_agents/commands/aiws-agent-review-learning.md` |
| upgrade / reconcile vs blueprint (drift) | upgrade | `development/ai_agents/commands/aiws-agent-upgrade.md` |
| clone / nhân bản agent | clone | `development/ai_agents/commands/aiws-agent-clone.md` |
| rename / đổi tên / đổi id agent | rename | `development/ai_agents/commands/aiws-agent-rename.md` |
| list / "agent nào / có gì / đã học gì" | (read-only) | `run_agent.py list` (+ `memory <instance>`) |

## Guardrails
- Router **no state change** — all mutation via a gated verb.
- Ambiguous resolve / unknown verb → STOP + ask; no guess-then-act.
- **Defer to an explicit verb:** if the user already named the exact verb (or invoked its spec directly), dispatch to that verb — don't re-route or second-guess. (The verb's own CONFIRM/gates still apply.)
- The verbs remain the canonical audit/gate surface; this skill is convenience only.
- After CONFIRM, the dispatched verb enforces its own gate: create stops for HUMAN; run enforces `run_policy.aip_driven` (needs `--aip`); feedback never writes confirmed memory; review-learning HUMAN-gated; clone flags `clone_review: pending`; upgrade presents drift, never auto-merges; rename validates the new id (refuses no-op / invalid / collision-with-current-id-or-another's-previous_id), keeps the old id as a `previous_ids` alias, and never rewrites another instance.
- **Task Workspace (CR-AIWS-2026-06-057 Phase 1):** an `aip_driven` run started with `--aip` REUSES the driving AIP's Task Workspace (`.ai-work/workspaces/{account}/{task_id}/`) — it does NOT create a second workspace; the instance keeps only a `run_index.jsonl` back-pointer.
