# AI Agents Pack — Staging (`development/ai_agents/`)

> **Status:** NON-CANONICAL staging. File-first, client-side, HUMAN-gated.
> **Built by:** AIP-EXEC-107 (Phase A of program AIP-PLAN-002).
> **Source baseline:** `docs/agent_pack_impl_package/`.

This folder is the staging build of the **AIWS Wiki Meta Build & Consume Agent Pack** — the
**Agent Blueprint → Agent Instance** model. It is built here (not in `product/` or `.ai-work/`)
exactly like the earlier `development/ai_assisstant/` feature: iterate + dogfood first, then
promote to canonical via a Change Request.

## Governance

- Building / iterating inside `development/ai_agents/` needs **no CR**.
- **Promotion** of this pack into `product/` and/or `.ai-work/` is **CR-gated** (CLAUDE.md rule #8 /
  SOP_MASTER §4.1) and is **out of scope** for the staging phases.
- **Single-track install (CR-AIWS-2026-06-055/049; supersedes the two-track AP-CR-29 / AP-DDR-17):** the pack
  installs to a target project's **`.ai-work/agents/`** whether trialed or matured — there is no `.aiws-staging/`.
  Maturity is managed by **git branch** in the AIWS source repo; promotion `development/`→`product/` (CR-gated)
  graduates the pack into the canonical build, not a change of target dir.
- **No silent promotion** at any layer: generated metadata → Wiki, Wiki candidate → Official Wiki,
  learning candidate → confirmed memory, candidate tool → active tool, instance lesson → Blueprint —
  every step requires HUMAN approval.
- Coordinator agents are **planning-only** (plan / task-card / integration-summary). They do **not**
  auto-run other agents. HUMAN invokes each agent explicitly; collaboration is via manual handoff
  artifacts (Shared Task Workspace is Post-MVP, not built).

## Layout (OQ-1 resolved — AIP-EXEC-107 STEP-00, 2026-06-18)

```
development/ai_agents/            <- staging wrapper  (maps to .ai-work/ on promotion)
  README.md                       <- this file
  agents/
    blueprint_registry.yaml       <- index of available Blueprints
    blueprints/<blueprint_id>/    <- reusable agent definitions (no project-specific memory)
    instances/<instance_id>/      <- named, tracked agents (config + context + memory + workspace)
  wiki_meta/                      <- GENERATED metadata (inventories/relations/meta_reviews/tool_outputs)
  wiki_candidates/                <- candidate_packs / patch_proposals / review_packs (pre-approval)
  tools/                          <- project/ + common/ tools (candidate tools live agent-local first)
```

**Install/promotion mapping — single-track by maturity (CR-AIWS-2026-06-055/049; supersedes two-track AP-CR-29 / AP-DDR-17):**
- **One target** — the pack installs to the project's **`.ai-work/agents/`** whether incubating (trial) or matured (`.../agents/` → `.ai-work/agents/`, `.../wiki_meta/` → `.ai-work/agents/wiki_meta/`, …). There is no `.aiws-staging/`.
- **Maturity = git branch** in the AIWS source repo (HUMAN-managed). Promotion `development/`→`product/` (CR-gated, CLAUDE.md #8 / SOP_MASTER §4.1) graduates the pack into the canonical `product/`→`.ai-work/agents/` build; it does **not** change the target dir.

All internal cross-references are **relative**, so the install rebase is mechanical. The pack is promoted into `product/agents/` and ships via a dedicated builder PAYLOAD_SECTION → **`CR-AIWS-2026-06-055`** (with CR-049 install-model + CR-051 `.claude` wiring; AIWS-Product-Owner approved 2026-06-23).

> **`instances/` are EXCLUDED from the install** (AP-CR-24). Instances are **created on the target**
> via `/aiws-agent-create`, **not shipped** — the ship-set is blueprints + registry + templates + commands +
> tooling only. The install target gets instances created at runtime under `.ai-work/agents/agents/instances/`
> (a write location only); the `*__sample_project` instances stay here as dev/test fixtures. See the
> PROMOTION-EXCLUDES invariant in `docs/rollout/promotion_readiness_note.md` §3(1).

**Folder separation is a guardrail** — `wiki_meta/` (generated, not Wiki) ≠ `wiki_candidates/`
(reviewable candidates/patches) ≠ Official Wiki (only after HUMAN approval).

## Phase status (program AIP-PLAN-002)

| Phase | Scope | This folder |
|---|---|---|
| **A** (AIP-EXEC-107) | Foundation: skeleton + schemas + 1 sample blueprint + 1 sample instance | ✅ built |
| **B** (AIP-EXEC-108) | Create-Agent-Instance command (3 modes incl. custom no-blueprint + `agent_design_snapshot.yaml`) | ✅ built |
| **C** (AIP-EXEC-109) | Instance Workspace + run/learning/confirmed-memory loop | ✅ built |
| **Priority workstream** (AIP-EXEC-139) | 3 priority agents mapped from v0.1 templates: `detailed_design_review_agent`, `testcase_review_agent`, `pm_agent` — incl. `_shared/review/` assets, registry +3, 3 sample instances, 3 MOCK sample runs | ✅ built (2026-06-21) |
| **Runtime Command Set** (AIP-EXEC-142) | `/aiws-agent-run` (start/resume/status/stop) + `/aiws-agent-feedback` + tooling `run_agent.py` (stdlib, thin) + Active Run Context (`00_active_run_context.md`) + additive `run_state.yaml`; dogfood MOCK on `detailed_design_review_agent` | ✅ built (2026-06-21) |
| D · E · F · G | Coordinators → metadata sub-agents → tooling → wiki lifecycle | pending |
| **H** Wiki Consumer agents | **re-scoped OUT of EXEC-139 (2026-06-21)** → separate AIP, not yet created | pending |
| **I** (AIP-EXEC-140) | Assistant (DDR) **absorbed** into `detailed_design_review_agent` (additive `memory_load_policy` graft) + `development/ai_assisstant/` **retired** (archived to `.ai-work/history/archive/`) | ✅ done (2026-06-21) |
| **J-1** (AIP-EXEC-141) | Scoped E2E (review+PM) + FULL packaging for current agents: `docs/rollout/` (setup/user/command/authoring guides + smoke + known-limitations + promotion-readiness) + `sample_project_package/` | ✅ done (2026-06-21) |
| J-2 | Full cross-pack E2E (build/refresh/consume) + remaining agents (D/E/F/G/H) | pending (deferred — needs create-wiki pipeline) |

> The `memory/` and `training/` files inside the sample instances are intentionally **empty skeletons**
> (header + `_(none yet)_`) — confirmed learning is created only via the Phase-C run/learning loop with
> HUMAN approval (no fabricated/seeded learning). The Phase-C demo populated the coordinator sample only;
> the 3 priority-agent instances ship with empty memory by design.
