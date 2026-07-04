---
name: init-project
description: Initialize a new project with AI Work System MVP from an install package
user-invocable: true
---

# SKILL: init-project

## Purpose
Set up a new project with AI Work System MVP: create `.ai-work/` structure,
copy skills/tooling from install package, create truth stubs, and wire `CLAUDE.local.md`.

## Inputs
- `project_root` (required) — absolute path to the target project
- `project_name` (required) — project name (used in CLAUDE.local.md)
- `package_path` (required) — path to the install package folder (contains `payload/`)
- `claude_target` (optional) — `CLAUDE.md` or `CLAUDE.local.md` (default: `CLAUDE.local.md`)

## Flow
1. Clarify inputs; confirm with HUMAN before any file changes
2. Pre-flight — check Python >= 3.8, detect conflicts, verify package structure
3. Create `.ai-work/` directory structure (incl. `.ai-work/wiki/reference/`) + `.claude/skills/` + `.claude/commands/`
4. Copy payload sections to destinations (skills → `.claude/skills/`, commands → `.claude/commands/`, tooling → `.ai-work/tooling/`, etc.) — the **authoritative** payload→target list is the package's generated `install_guide.md` (§2 Payload mapping + §3); when a payload Section is added, this list + the install_guide update together (single source — CR-037 C4). **Exception — `wiki_source_profiles`:** project-owned → **MERGE** (never `cp -r`-overwrite) via `py .ai-work/tooling/merge_wiki_source_profiles.py --from <pkg>/payload/wiki_source_profiles --into .ai-work/wiki_sources/profiles --apply`; preserves a project's customized profiles + `extra_stopwords`, never writes `project_stopwords.yml` (CR-AIWS-2026-06-047). (Fresh init = the merge simply adds both canonical profiles.)
4b. Scaffold project-local reference doc — copy `wiki_guidelines/install/document_search_guidelines.template.md` → `.ai-work/wiki/reference/document_search_guidelines.md` (a fill-in starting point; keep the `## Raw search fallback — project artifact directories` heading verbatim; replace `<...>` placeholders with the project's task types / source-ids / artifact dirs, or leave to fill on first use). Required by `INSTALL_CHECKLIST.md`.
4c. Set account_id (CR-AIWS-2026-06-016) — ASK the HUMAN for their `account_id`, then run `py .ai-work/tooling/account_id.py set --account-id <id>` (validates dir-safe + lowercases; writes the gitignored `.ai-work/account_info.yaml` with a seeded `next_aip_id` counter; ensures `.gitignore` ignores it). Required before any AIP id allocation (CR-015 v2 precondition). NEVER invent the id — it is HUMAN-set.
4d. Build the AIWS wiki index (CR-040) — after `payload/aiws_wiki/` is copied to `.ai-work/wiki_sources/aiws_meta/`, build the searchable `aiws` namespace: `py .ai-work/tooling/build_wiki_source_index.py --scope project --meta-dir .ai-work/wiki_sources/aiws_meta --out .ai-work/wiki_sources/index.aiws.jsonl`. Makes AIWS methodology/spec/preset lookup-able immediately via `lookup_wiki_source.py --scope aiws` (or default `--scope all`). The project's own `index.jsonl` stays empty until `/build-project-wiki` — the two namespaces are disjoint (never index `aiws_meta/` into `index.jsonl`).
5. Init truth stubs — copy SOP templates; create empty `AI_WORK_CONTRACT.md` + `AIP_ROOT.md`
6. Wire `CLAUDE.local.md` from slim template; replace `<PROJECT_NAME>` and `<YYYY-MM-DD>`
7. Create `.claude/settings.local.json` only if not already present
8. Smoke test — run `lint_all.py --help`, `lookup_wiki_source.py --query methodology`, and `lookup_wiki_source.py --query AIP --scope aiws` (the last MUST return ≥1 AIWS hit — confirms the `aiws` namespace built)
9. Report results; suggest `/lint-all` next

## Rules
- `wiki_source_profiles` is project-owned — **merge, never overwrite** (use `merge_wiki_source_profiles.py`); never create/overwrite `project_stopwords.yml` (CR-AIWS-2026-06-047)
- never overwrite existing files without asking HUMAN first
- never invent Truth content — only create empty stubs or copy templates
- stop and report clearly if pre-flight fails; do not proceed
- `settings.local.json` — create only if absent; do not auto-merge
- scaffold `.ai-work/wiki/reference/document_search_guidelines.md` from `wiki_guidelines/install/document_search_guidelines.template.md` — a fill-in starting point (INSTALL_CHECKLIST requires it); the project fills its task-type sources + artifact dirs
- AIWS wiki (CR-040): build `index.aiws.jsonl` from `.ai-work/wiki_sources/aiws_meta/` (step 4d); keep the `aiws` namespace disjoint from the project's own `index.jsonl`/`meta/` — never index `aiws_meta/` into the project index
- **Agents package (CR-AIWS-2026-06-055), single-track:** if the package ships `payload/agents/`, copy it to **`.ai-work/agents/`** (install_guide §2 row 14 is authoritative); the pack's verb commands + `aiws-agent` router skill arrive via the standard `payload/commands`→`.claude/commands` + `payload/skills`→`.claude/skills` copy (wired at build). Single target `.ai-work/` — there is **no `.aiws-staging`**; maturity is managed by branch in the AIWS source repo, not by a target dotfolder.
- suggest `/lint-all` after install to verify
