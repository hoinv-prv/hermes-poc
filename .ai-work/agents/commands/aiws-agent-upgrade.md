# Command Spec — `/aiws-agent-upgrade`

> **Status:** prompt/spec (file-first), backed by thin tooling `tooling/run_agent.py` (stdlib, `py`). NOT a full CLI. Post-MVP lifecycle verb.
> **Built by:** AIP-EXEC-146 (Instance lifecycle; AP-CR-27, AP-DDR-15).
> **Source:** Detailed Design §6A + §4A + §5; requirements FR-AI-09/FR-AI-10; [09 AP-CR-27](../../../docs/agent_pack_impl_package/docs/09_Change_Requests.md).
> **Scope:** reconcile an existing blueprint-based Agent Instance against a **newer Blueprint version**, HUMAN-gated, without overwriting the instance's own work. Does **not** create instances (`/aiws-agent-create`), does **not** run them (`/aiws-agent-run`), does **not** confirm memory (`/aiws-agent-review-learning`).

## Purpose
When AIWS ships a newer version of a Blueprint, an Instance created from it may **drift** behind. `/aiws-agent-upgrade` detects that drift and **presents** the Blueprint's changes (with their WHY) next to the Instance's customizations (with their WHY) so the **HUMAN decides, per change**, what to adopt — without ever silently overwriting what the instance has learned or been customized to do.

## HARD RULE — present, never auto-apply; never touch the instance-learned layer
The tool **PRESENTS** the diff and **RECORDS a HUMAN decision**. It does **not** merge Blueprint content into the instance automatically, and it **NEVER writes the instance-learned layer** (`memory/`, `training/`, `local_guidelines`, `context/`) — the **Three-Layer Ownership Invariant (FR-AI-09)**. Adopting a Blueprint change into the instance-override layer is a HUMAN edit; the tool only re-pins the version, refreshes the snapshot, and logs the decision.

## Guardrails (always)
- **Upgrade ≠ auto-apply.** No LLM, no auto-merge, no chaining. Drift is *shown*; the HUMAN decides.
- **Ownership invariant (FR-AI-09):** Blueprint (AIWS-owned, upgradeable) / Instance-override (HUMAN-confirm per change) / Instance-learned (**never** auto-overwritten — advisory only).
- **No auto-promotion:** reconcile decisions are HUMAN-gated; learned memory is advisory-never-delete.
- Writes only under `agents/instances/<instance>/` (relative to the pack root; staging; boundary-guarded) — and only the blueprint-derived metadata (`blueprint_ref.yaml` version pin + `reconcile_log`, `.blueprint_snapshot/`, the instance `changelog.md`), never the learned layer.

## Subcommands

### present drift (default)
```
/aiws-agent-upgrade <instance>
```
Tool: `py tooling/run_agent.py upgrade <instance>`
- Shows pinned vs current `blueprint_version` and a `.blueprint_snapshot/` vs current `blueprint.yaml` diff signal (`[outdated]` = version pin behind; `[drift]` = content differs). The first run on an instance with no snapshot **captures the baseline** (setup, not a reconcile).
- When drift exists, **presents** the Blueprint `changelog.md` (WHY of each blueprint change — §4A), the Instance `changelog.md` + `customization_summary` (WHY of each instance customization), then prints the `--reconcile` command to record a decision. It applies nothing.

### record a HUMAN-confirmed reconcile
```
/aiws-agent-upgrade <instance> --reconcile --to-version "<v>" --decisions "adopted X, skipped Y"
```
- Re-pins `blueprint_ref.blueprint_version`, refreshes `.blueprint_snapshot/`, appends a `reconcile_log` entry (§5) and an Instance `changelog.md` entry (`layer: override`, `source: HUMAN-feedback`). The instance-learned layer is **not** touched; apply any adopted blueprint changes to the instance-override layer yourself.

## Drift in `list`
`py tooling/run_agent.py list` flags genuinely-diverged instances `[outdated]`/`[drift]` beside `[aip_driven]`. A not-yet-baselined instance shows **no** marker (benign).

## Outputs
`blueprint_ref.yaml` (re-pinned `blueprint_version` + appended `reconcile_log`) · `.blueprint_snapshot/` (refreshed baseline) · instance `changelog.md` (reconcile entry). Never: `memory/`, `training/`, `context/`, `local_guidelines`.

## Related
`/aiws-agent-create` (make the instance — writes the initial snapshot) · `/aiws-agent-clone` (clone an instance — clones inherit the pinned version + snapshot and still reconcile) · `/aiws-agent-rename` (change an instance's id + folder, with a `previous_ids` alias) · `/aiws-agent-run` (run a task) · `/aiws-agent-review-learning` (confirm candidates → memory).
