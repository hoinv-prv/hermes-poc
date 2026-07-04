---
name: build-aiws-install-package
description: Build a versioned installable package for AI Work System MVP
user-invocable: true
---

# SKILL: build-aiws-install-package

## Purpose
Package the current state of AI Work System MVP into a self-contained
installable folder to be deployed into other projects via `/init-project`.

## Inputs
- `version` — **NOT a CLI input.** Pinned in [`product/aiws_version.md`](../../../../product/aiws_version.md) (`aiws_version` + optional `release_date`), the single source of truth so every build produces the same version. To release a new version, **bump that file FIRST**.
- `prev package path` (optional) — auto-detected from `releases/` if omitted
- `output path` (optional) — default: `releases/AI_Work_System_MVP_<pinned version>_<date>/`

## Flow
1. Read the pinned version from `product/aiws_version.md`. If the user wants a *new* release, ask them to bump `aiws_version` (+ `release_date`) there first — do NOT type a version on the CLI. (prev auto-detected; output optional.)
2. Pre-flight — verify source sections exist; output path `releases/AI_Work_System_MVP_<pinned version>_<date>/` must not yet exist (if it does, the version is already released → bump the pin)
3. Run `build_aiws_install_package.py` (no `--version` — it reads the pin file)
4. Verify output: START_HERE.md, README.md, MANIFEST.md, CHANGELOG.md, payload/ with 8 subfolders
5. Report results to user — state which pinned version was built

## Rules
- **version is pinned** in `product/aiws_version.md` — never pass a version on the CLI for an official build; bump the pin to cut a new version. (`--override-version` exists ONLY for trial/ephemeral builds via `quick_install_aiws.py`.)
- do NOT modify source files during build
- do NOT ship runtime folders (`workspaces/`, `aip/exec|plans|local/`, `history/`, `wiki/`)
- do NOT ship project Truth files (`SOP_MASTER`, `AI_WORK_CONTRACT`, `AIP_ROOT`)
- do NOT ship personal files (`*.local.md`, `*.bak-*`, `*.preview`)
- do NOT ship `methodology/00_brainstorming/`, `methodology/90_delta_tracking/`, `aip_templates/tracking/`, `10_design/Detail_Design_MVP_Core_Artifacts.md` — fully excluded
- `10_design/` (4 files: Architecture, Basic, Conceptual, Methodology) — strip-and-copy: sections explaining AIWS design rationale/phases are removed, operational content kept
- always create a new versioned folder side-by-side — never overwrite previous package
- CLAUDE_SLIM_TEMPLATE must be generic — no project-specific references
- **Agents package (CR-AIWS-2026-06-055/051/049):** `product/agents/` ships as one PAYLOAD_SECTION → `.ai-work/agents/` (self-contained — single-track, no `.aiws-staging`). Its verb `commands/*.md` + `aiws-agent` router skill are auto-wired into `.claude/` at build by `wire_agent_pack_claude` (copied into `payload/commands` + `payload/skills`), and an **install smoke-check FAILS the build** if any verb is unwired. `lint_agents.py` rides inside the package; `/lint-all` runs it when `.ai-work/agents/` exists. NOT shipped: `agents/instances/`, `sample_project_package/`, dev-process docs. Optional — absent `product/agents/` → default build unchanged.
