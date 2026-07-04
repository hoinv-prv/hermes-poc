# Command Spec — `/aiws-agent`

> **Status:** prompt/spec (file-first). A thin **NL front-door router** — NOT a fifth verb and NOT an executable CLI.
> **Built by:** AP-CR-22 (convenience layer over the existing gated verbs — Core runtime + Instance lifecycle — plus `run_agent.py` list/memory/fuzzy-resolver).
> **Source:** `development/ai_agents/docs/agent_runtime_design.md`; mirrors the thin-orchestrator shape of `/aiws-agent-run`.
> **Scope:** parse a natural-language request → resolve the instance → CONFIRM with the HUMAN → dispatch to one of the existing gated verbs. It is a convenience layer only; the gated verbs (Core runtime: create/run/feedback/review-learning · Instance lifecycle: upgrade/clone/rename) remain the canonical audit/gate path.

## Purpose
A single natural-language entry point so a HUMAN need not remember which verb to type or the full compound instance id. The router reads a free-text request (e.g. "have Henry review the order-cancel design", "show me what the PM agent has learned", "give feedback on Henry's last run"), figures out **which instance** and **which verb** are meant, confirms that reading with the HUMAN, then **dispatches** to the existing command / `run_agent.py` subcommand that actually does the work.

## HARD RULE — the router NEVER mutates
**`/aiws-agent` performs no state change of its own.** It does not write memory, does not set `status: completed`, does not emit/confirm learning candidates, does not scaffold run-folders, does not edit blueprints or Wiki. **Every mutation flows through the existing gated verbs** (`/aiws-agent-create | run | feedback | review-learning | upgrade | clone | rename`) or the `run_agent.py` subcommands they wrap. The router only does: **read-only resolution (`list`/`memory`/fuzzy match) → HUMAN confirmation → hand off.** If resolution is ambiguous or a verb is unclear, it STOPS and asks — it never guesses-then-acts.

## Flow
1. **Parse** the NL request into: a target **instance token** (a partial id, role word, or `display_name` such as "Henry"), an intended **verb**, and the **task / detail** text.
2. **Resolve the instance** (read-only) via the fuzzy resolver — `py tooling/run_agent.py list` to enumerate instances (`id · display_name · blueprint · status`), or let the verb's own `_resolve_instance` match the token. A **unique** match is required; ambiguous/none → show the `list` and ask the HUMAN to pick.
3. **Map the verb** to one of:
   - create a new agent → **`/aiws-agent-create`**
   - run a task / resume / check status / stop → **`/aiws-agent-run`** (`start`/`resume`/`status`/`stop`) or directly `py tooling/run_agent.py …`
   - give feedback on a run → **`/aiws-agent-feedback`**
   - review/confirm learning candidates → **`/aiws-agent-review-learning`**
   - reconcile an instance against a newer blueprint version → **`/aiws-agent-upgrade`**
   - clone an existing instance into a new one → **`/aiws-agent-clone`**
   - rename an instance / change its id → **`/aiws-agent-rename`**
   - "what does it know / remember" → read-only `py tooling/run_agent.py memory <instance> [--full]`
   - "is it behind its blueprint / drifted" → read-only `py tooling/run_agent.py list` (shows `[outdated]`/`[drift]`)
4. **CONFIRM** with the HUMAN — restate **instance + verb + task** in one line and wait for an explicit go before dispatching. (E.g. "Run `detailed_design_review_agent` (Henry — Detailed Design Review) → `/aiws-agent-run start` on task 'review the order-cancel design' — proceed?")
5. **Dispatch** to the chosen verb / subcommand. From there the canonical command's own guardrails and HUMAN gates apply unchanged.

## run_agent.py conveniences this router leans on (AP-CR-22/23)
- **`list`** — list instances (`id · display_name · blueprint · status`; flags `[aip_driven]`). The instance directory the router resolves against.
- **`memory <instance> [--full]`** — read-only view of an instance's confirmed memory (entry count + index of id · type · scope_tags, plus candidate/lessons counts); `--full` dumps every entry. The router uses this for "what has it learned?" requests — it never writes here.
- **Fuzzy instance resolver** — every instance arg accepts a partial id / role word / `display_name`; a **unique** match is required (ambiguous/none → error pointing at `list`). Lets the HUMAN say "Henry" instead of the full compound id.

## Guardrails (always)
- **No mutation in the router** (see HARD RULE) — read-only resolution + confirm + hand off only.
- **Confirm before dispatch** — never silently fire a verb; the HUMAN approves the (instance, verb, task) reading first.
- **Unique-match required** — ambiguous instance → STOP and show `list`; never act on a guess.
- **Inherited gates stand** — `aip_driven` enforcement, no-auto-promotion, no-auto-confirm, `non_responsibilities`, and the boundary guard all live in the dispatched verbs and are unaffected by the router.

## Related
The four canonical verbs remain the audit/gate surface:
`/aiws-agent-create` (make the instance) · `/aiws-agent-run` (run/track/resume/stop) · `/aiws-agent-feedback` (feedback → candidates) · `/aiws-agent-review-learning` (confirm candidates → memory).
Lifecycle verbs (AP-CR-27/28/30): `/aiws-agent-upgrade` (reconcile vs a newer blueprint) · `/aiws-agent-clone` (new instance from an existing one) · `/aiws-agent-rename` (change an instance's id + folder, with a `previous_ids` alias).
`/aiws-agent-board` (a status-board view across instances) is **deferred — Post-MVP**.
