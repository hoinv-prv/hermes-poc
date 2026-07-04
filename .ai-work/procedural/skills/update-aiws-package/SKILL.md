---
name: update-aiws-package
description: Upgrade an existing AI Work System installation to a newer package version
user-invocable: true
---

# SKILL: update-aiws-package

## Purpose
Upgrade payload sections of an existing AIWS installation (skills, tooling,
wiki_guidelines, etc.) from a newer install package.
Never touches Truth files or project runtime.

## Inputs
- `package_path` (required) — absolute path to the new install package folder
- `project_root` (optional) — default: current directory
- `sections` (required) — which sections to upgrade (all / by number / `changed`)

## Flow
1. Self-update check — if package has a newer version of this skill, offer to update it first
2. Version detection — detect current installed version vs package version; show comparison
3. Section selection — show section status (ADD / UPDATE / UNCHANGED); ask user to select
4. Diff analysis — per-file status (ADD / UPDATE / UNCHANGED / REMOVED) for selected sections
5. Temp-first: copy ADD/UPDATE files to `.aiws-upgrade.tmp` — do not touch originals yet
6. Show upgrade report to user; ask for confirmation
7. Apply — copy temp files to destinations; delete temp files; write `.aiws-version`. **Exception — `wiki_source_profiles`:** project-owned → do NOT copy-overwrite; **MERGE** via `py .ai-work/tooling/merge_wiki_source_profiles.py --from <pkg>/payload/wiki_source_profiles --into .ai-work/wiki_sources/profiles --apply` (adds only missing canonical top-level keys; preserves the project's profiles + `extra_stopwords`; never writes `project_stopwords.yml`) — CR-AIWS-2026-06-047
7b. AIWS wiki refresh (CR-040) — if the new package ships `payload/aiws_wiki/`, refresh ONLY the `aiws` namespace: replace `.ai-work/wiki_sources/aiws_meta/` with the new bundle, then rebuild `py .ai-work/tooling/build_wiki_source_index.py --scope project --meta-dir .ai-work/wiki_sources/aiws_meta --out .ai-work/wiki_sources/index.aiws.jsonl`. NEVER touch the project's own `index.jsonl` / `meta/` (domain wiki).
8. Post-upgrade checklist — remind user to review REMOVED files, update CLAUDE.local.md, run `/lint-all`

## Rules
- `wiki_source_profiles` is project-owned — **merge, never overwrite** (use `merge_wiki_source_profiles.py`); never write `project_stopwords.yml` (CR-AIWS-2026-06-047)
- never overwrite Truth files (`SOP_MASTER`, `AI_WORK_CONTRACT`, `AIP_ROOT`)
- never touch project runtime (`workspaces/`, `aip/exec|plans|local/`, `history/`, `wiki/`)
- AIWS wiki refresh (CR-040) touches ONLY `wiki_sources/aiws_meta/` + `index.aiws.jsonl` (the `aiws` namespace); NEVER the project's own `wiki_sources/index.jsonl` / `wiki_sources/meta/` (domain wiki)
- never auto-delete REMOVED files — only notify
- never apply before user confirmation — temp-first is mandatory
- stop and ask on any permission or encoding error
