# Command Spec — `/aiws-agent-rename`

> **Status:** prompt/spec (file-first), backed by thin tooling `tooling/run_agent.py` (stdlib, `py`). NOT a full CLI. Post-MVP lifecycle verb.
> **Built by:** AIP-EXEC-147 (Instance rename; AP-CR-30, AP-DDR-18).
> **Source:** Detailed Design §6C + §4 (`previous_ids`) + §6.3 (amended immutability note); requirements FR-AI-12; [09 AP-CR-30](../../../docs/agent_pack_impl_package/docs/09_Change_Requests.md).
> **Scope:** controlled rename of an **existing** Agent Instance's machine identity (`instance_id` + folder) and, optionally, its HUMAN-facing names. Does **not** run the instance (`/aiws-agent-run`), does **not** modify any other instance, and is the **only** sanctioned way to change an `instance_id` (supersedes the AP-CR-23 / §6.3 "MUST NOT be renamed" rule).

## Purpose
A create-time `instance_id` can prove unsuitable or collision-prone, and a growing fleet needs clean, memorable ids. `/aiws-agent-rename` changes one existing instance's id (and folder) in place while keeping every prior reference resolvable — the old id is recorded as an alias so clone lineage, the instance's own run-history, and a HUMAN typing the old id all still resolve.

## HARD RULE — controlled rename, alias not breakage, no cross-instance rewrite
Rename happens **only** through this command (never ad-hoc). It mutates the **one** existing instance in place: the folder + `instance_id` (+ optional `instance_name`/`display_name`) change, and the instance's OWN run-history is repointed — but creation provenance (`created_at`) and any clone lineage are **preserved** (this is the same instance, not a new one). The old id is appended to the instance's accumulating **`previous_ids`** alias, and the fuzzy resolver matches `previous_ids`, so old references keep resolving. **No other instance's files are touched** (chosen over rewrite-all churn / accept-stale breakage). The command does **not** run the agent.

## Guardrails (always)
- **Rename ≠ run.** No LLM, no auto-run, no chaining. The renamed instance is at rest.
- **Validate before moving:** refuse a no-op (`new_id == old_id`), an invalid id (`_ID_RE`: letters/digits/`_`/`-`, ≤80 chars), or a collision — `new_id` already in use as another instance's **current id** OR as another instance's **`previous_id`** (keeps alias resolution unambiguous). Nothing is moved on refusal.
- **Same instance, in place:** `created_at`/`last_reviewed_at` and clone lineage (`cloned_from`) are not reset (contrast `/aiws-agent-clone`, which mints a fresh identity and resets `created_at`).
- **No cross-instance rewrite** — only the renamed instance's own folder + run-history change.
- Writes only under `agents/instances/` (relative to the pack root; staging; boundary-guarded via `_ensure_inside`).

## Invocation
```
/aiws-agent-rename <source> --to <new_instance_id> [--name "<instance_name>"] [--as "<display_name>"] [--why "<reason>"]
```
Tool: `py tooling/run_agent.py rename <source> --to <new_id> [--name "..."] [--as "..."] [--why "..."]`
- `<source>` resolves via the fuzzy resolver (partial id / role word / `display_name` / a **previous id** after an earlier rename). `--to` (required) is the new `instance_id`. `--name` / `--as` optionally update `instance_name` / `display_name`. `--why` is recorded in the changelog.

## What it does
1. **Validate** `<source>` → `old_id`; check `--to` (`_ID_RE`, not a no-op, not colliding with a current id or another instance's `previous_id`).
2. **Hard-move** `instances/<old_id>/` → `instances/<new_id>/`.
3. **Rewrite identity** in `instance.yaml`: `instance_id` → `<new_id>`; optional `instance_name`/`display_name`; append `old_id` to `previous_ids` (accumulating, no cap); `created_at`/`last_reviewed_at` left untouched.
4. **Repoint own run-history:** `agent_instance_id` in each run's `run_state.yaml` + `run_request.yaml` (active + completed) → `<new_id>`.
5. **Changelog:** prepend an instance `changelog.md` entry (WHAT + WHY; `layer: override`, `source: HUMAN-feedback`) per §4A / FR-AI-10.

## After renaming
- The old id still resolves: `py tooling/run_agent.py list` shows the new id; `... memory <old_id>` (or any verb) resolves to the renamed instance via `previous_ids`.
- Other instances' `cloned_from: <old_id>` and historical run pointers keep resolving (no rewrite needed).

## Outputs
The instance folder renamed to `agents/instances/<new_id>/` with updated identity + `previous_ids` alias + repointed own run-history + a changelog entry. No other instance changed; the agent is not run.

## Related
`/aiws-agent-create` (make a fresh instance from a Blueprint) · `/aiws-agent-clone` (new instance from an existing one — mints a fresh id, does NOT rename the source) · `/aiws-agent-upgrade` (reconcile vs a newer blueprint) · `/aiws-agent-run` (run the renamed instance) · `/aiws-agent` (NL front-door router — routes rename requests here).
