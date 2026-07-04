# Setup Guide — AI Agents Pack (current agents)  (Phase J-1)

> **STAGING / NON-CANONICAL.** Built by AIP-EXEC-141 (Phase J-1) STEP-02.
>
> **SCOPE = current agents only.** This guide installs/enables the **3 priority agents**
> (`detailed_design_review_agent`, `testcase_review_agent`, `pm_agent`) + the A/B/C foundation
> (Blueprint/Instance model, `/aiws-agent-create`, instance workspace + run/learning loop) and the
> Runtime Command Set — Core runtime (`/aiws-agent-run` + `/aiws-agent-feedback`), Instance lifecycle (`/aiws-agent-upgrade`/`clone`/`rename`), and the `/aiws-agent` router. The remaining agent types
> (program phases **D**/**E**/**F**/**G**/**H** — coordinators, metadata, tooling, wiki lifecycle,
> wiki-consumer) are **deferred — see `known_limitations_and_backlog.md`**.
>
> The pack is **file-first**: there is no executable `aiws` CLI. "Install" means copying files and
> wiring an instance's context — nothing more. All paths below are relative to the **pack root** (`development/ai_agents/` in the AIWS dev repo · `.ai-work/agents/` when installed (single-track)).

## 1. Prerequisites

- **Python 3.8+, stdlib only** — no `pip install`. The only tool, `tooling/run_agent.py`, imports
  stdlib modules only (`argparse`, `datetime`, `re`, `shutil`, `pathlib`).
- **Run Python with `py`** — on this machine bare `python` is a broken WindowsApps stub; use
  `py tooling/run_agent.py ...`.
- **UTF-8** — the tool reconfigures stdout/stderr to UTF-8 (cp932-safe on Windows); no extra setup
  needed, but write/read the agent files as UTF-8.
- A target project with a **Knowledge Hub** (Wiki Source Index) so instances can ground Wiki-first.
  The current default sample wiring points at `.ai-work/wiki_sources/index.jsonl` (see §4).

## 2. Install ≠ auto-run (read first)

Installing the pack **never runs an agent**. Copying the files only makes the blueprints and
commands available. Creating an instance (`/aiws-agent-create`) does **not** run it either —
`create ≠ run`. An agent only acts when a HUMAN explicitly starts a run (`/aiws-agent-run start`)
and then the AI reads the materialized Active Run Context and acts as the agent. Nothing auto-runs,
auto-chains, or auto-promotes at any point.

## 3. What to copy / wire

There are **two distinct modes** — do not conflate them. The difference is **instances**: dev/dogfood
keeps the sample instances; install/promote **never** ships instances (they are created on the target).
Because every cross-reference inside the pack is **relative**, the tree resolves identically wherever it
lands (this is what makes a future promotion to `.ai-work/` a mechanical path rebase — see
`promotion_readiness_note.md`).

### (a) Try in place — inside `development/ai_agents/` (dev / dogfood)

For iterating on or dogfooding the pack in this staging repo, nothing is copied out: you run against
the tree as-is, **including the 5 sample instances** (`*__sample_project`) that ship here as dev/test
fixtures. Point a run at an existing sample instance (e.g.
`detailed_design_review_agent__sample_project`) or `/aiws-agent-create` a new one in
`agents/instances/`. This mode is the only one that uses the `agents/instances/` content directly.

### (b) Install / promote into a real project (ships **NO** instances)

When installing the pack into a real target project (the future promotion CR, AP-CR-10), the ship-set
is **only** the reusable definitions + commands + tooling — **never any instance**:

- `agents/blueprint_registry.yaml`
- `agents/blueprints/**`
- `agents/templates/**`
- `commands/*.md`
- `tooling/run_agent.py`

Instances are **NOT shipped**. On the target, promotion creates an **empty**
`.ai-work/agents/instances/.gitkeep` (a write location only), and a **real instance is created on the
target via `/aiws-agent-create`** — never by copying a `*__sample_project` instance across. The 5
sample instances stay behind in staging as fixtures (the naming law `*__sample_project` = never-ship;
see `agent_authoring_guide.md`). The PROMOTION-EXCLUDES invariant for this ship-set is recorded in
`promotion_readiness_note.md` §3(1).

Minimum set to enable the current agents (the **ship-set** of mode (b); mode (a) additionally has the
sample `instances/` already present):

```
<pack_root>/
  agents/
    blueprint_registry.yaml        # index of available blueprints (3 priority + coordinator)
    blueprints/
      _shared/review/              # shared review process/checklists/output_templates (referenced, not copied per-agent)
      detailed_design_review_agent/
      testcase_review_agent/
      pm_agent/
      wiki_meta_strategy_coordinator/   # foundation sample (planning-only); not in J-1 run scope
    instances/                     # NOT in the install ship-set — created on target via /aiws-agent-create
                                   #   (mode (a) only: the 5 *__sample_project fixtures live here in staging)
    templates/                     # instance / run / learning / memory templates used by the commands
  commands/                        # the 8 command specs (prompt/spec, file-first): Core runtime + Instance lifecycle + router
    aiws-agent-create.md           #  Core runtime
    aiws-agent-run.md
    aiws-agent-feedback.md
    aiws-agent-review-learning.md
    aiws-agent-upgrade.md          #  Instance lifecycle (AP-CR-27)
    aiws-agent-clone.md            #  Instance lifecycle (AP-CR-28)
    aiws-agent-rename.md           #  Instance lifecycle (AP-CR-30)
    aiws-agent.md                  #  Convenience router (AP-CR-22)
  tooling/
    run_agent.py                   # thin runtime orchestrator (stdlib; run with py)
```

Notes:
- `_shared/review/` is **document-type-agnostic** review assets (process, severity, finding format,
  source-trace + lesson-capture rules, the common checklist, the output templates). Both review
  blueprints reference it by relative path (`../_shared/review/...`) — do not copy it per agent or
  the trees will drift.
- `agents/templates/` holds the instance skeleton (`context/`, `run/`, `tools/`),
  `learning_candidate_schema.md`, `confirmed_memory_schema.md`, `learning_loop_lifecycle.md`,
  `instance_creation_wizard.md`, `instance_setup_summary.md`, etc. The commands read these.
- The command specs are **prompt/specs**, not executable binaries. The tooling-backed verbs
  (`/aiws-agent-run` + the Instance-lifecycle `upgrade`/`clone`/`rename`) run via `run_agent.py`;
  `create`/`feedback`/`review-learning` are followed by the AI directly.

## 4. How the 3 blueprints are registered

The blueprints are already registered — no extra registration step. `agents/blueprint_registry.yaml`
lists each blueprint with `blueprint_id`, `name`, `type`, `status: active`, a **relative** `path:`
under `agents/blueprints/…/`, and a `description`. The current registry (`version: 1`) contains:

| `blueprint_id` | `type` | `path` |
|---|---|---|
| `wiki_meta_strategy_coordinator` | `coordinator` | `agents/blueprints/wiki_meta_strategy_coordinator/` |
| `pm_agent` | `project_management` | `agents/blueprints/pm_agent/` |
| `detailed_design_review_agent` | `review` | `agents/blueprints/detailed_design_review_agent/` |
| `testcase_review_agent` | `review` | `agents/blueprints/testcase_review_agent/` |

`/aiws-agent-create blueprint=<id>` (Mode A) looks an id up here; if absent it offers AI-assisted
selection (Mode B) or custom no-blueprint (Mode C). To add your own blueprint later, see
`agent_authoring_guide.md`. **Verify** each `path:` directory exists and holds a `blueprint.yaml`
after copying (this is also smoke-test step A in `smoke_test_checklist.md`).

## 5. Point an instance's `context/` at your project Knowledge Hub

An **instance** is the real tracked runtime unit — it binds a blueprint to one project's context,
memory, and workspace. Create one with `/aiws-agent-create` (see `command_usage_guide.md`), which
generates the instance folder skeleton, or wire an existing sample instance. The Knowledge Hub wiring
lives in the instance's `context/` directory (Detailed Design v0.2 §7), **not** in the blueprint:

- `context/wiki_references.yaml` — set `wiki_index:` to your project's Wiki Source Index path (the
  sample uses `.ai-work/wiki_sources/index.jsonl`) and list `recommended_entries:` to read first.
  Carries `usage_rule: wiki_first_not_wiki_only` and the `source_verification_required_when:` triggers.
- `context/source_references.yaml` — source dirs that back findings (requirements, basic design,
  API/DB/screen specs, detailed design, `src/`).
- `context/source_priority.yaml` — Wiki-first ordering + when source verification is required.
- `context/working_inventory.yaml` — specific **non-wiki / not-yet-indexed** files this instance
  needs. **Instance-owned**: a blueprint update must never overwrite it (FR-AI-05). Ships empty `[]`.
- `context/ignored_paths.yaml` — paths to skip.

The instance also carries `scope:` in `instance.yaml` (`target_document_areas`, `target_source_areas`,
`ignored_paths`). When a run starts, `run_agent.py` reads these `context/` files (plus the blueprint
and confirmed memory) to materialize the Active Run Context — so wiring `context/` correctly is what
"points the agent at your project".

> **Wiki-first, NOT Wiki-only.** Instances ground in the Wiki/index first, then **verify important
> findings against source** and report conflicts rather than treat the Wiki as the sole authority.

## 6. Verify the install (smoke)

Run the smoke checklist (`smoke_test_checklist.md`): registry resolves the 3 blueprints (A); create
an instance from a blueprint (B, `create ≠ run`, empty-skeleton memory); start a review run on MOCK
input (C); start a PM run (D); feedback emits a candidate not auto-confirmed (E); review-learning
surfaces it without auto-confirm (F); guardrail checks (G). A green smoke run confirms the install.

## 7. Related guides

- `user_guide.md` — run the agents day to day.
- `command_usage_guide.md` — the command groups (Core runtime · Instance lifecycle · Convenience router) in detail.
- `agent_authoring_guide.md` — author a new blueprint/instance.
- `known_limitations_and_backlog.md` — what's deferred (D/E/F/G/H + full cross-pack E2E → J-2).
- `promotion_readiness_note.md` — what a future CR must cover to promote staging → canonical.
