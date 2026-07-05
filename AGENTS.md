# AGENTS.md - hermes-poc

Persistent project context. Read first in a new session. This file is the executor-neutral baseline for AI coding agents. Runtime-specific overlays such as `CLAUDE.md` may add assistant-specific wiring, but must defer to this file and `.ai-work/` on project rules.

## What this project is

Hermes PoC là dự án proof-of-concept để xây dựng và kiểm chứng quy trình làm việc với AI Work System trong bối cảnh phát triển phần mềm thực tế. Dự án tập trung vào chuẩn hóa workflow theo AIP, quản trị tri thức qua wiki source, và đảm bảo tính truy vết trong quá trình thực thi.

Adopted **AI Work System MVP v1.0.5** as working methodology since 2026-07-04. Live tree: `.ai-work/` at project root.

## Agent / Model Neutrality

- These instructions apply to every AI assistant/runtime: hosted models, local models, IDE assistants, and CLI coding agents.
- Canonical AIWS procedures live under `.ai-work/procedural/skills/`. Runtime-specific instruction files, skill folders, or slash commands are adapters only.
- If a runtime supports slash commands or native skills, it may expose aliases such as `/create-aip`, `/run-aip`, and `/lint-all`.
- If a runtime does not support those aliases, follow the common SKILL.md files in `.ai-work/procedural/skills/` and run the deterministic tooling in `.ai-work/tooling/` directly.
- Do not treat runtime-specific adapters as the source of truth when they conflict with `AGENTS.md`, `.ai-work/procedural/skills/`, or `.ai-work/truth/`.

## Adopted Canonical Knowledge

- **Methodology:** [AI Work System MVP](.ai-work/truth/canonical/methodology/) - `source_of_truth`, `authoritative`. Overrides `curated` / `reference` / `history` on conflict.
- **Wiki operational guidance:** [Wiki Guideline Package + deltas](.ai-work/truth/canonical/wiki_guidelines/) - complements methodology. On conflict with spec, **spec wins**. Nav: [.ai-work/wiki/reference/wiki-guidelines.md](.ai-work/wiki/reference/wiki-guidelines.md).
- **Project Truth:** [SOP_MASTER](.ai-work/truth/SOP_MASTER.md), [AI_WORK_CONTRACT](.ai-work/truth/AI_WORK_CONTRACT.md), [AIP_ROOT](.ai-work/truth/AIP_ROOT.md).

Rule mềm: spec wins unless there is an Approved Deviation in `AI_WORK_CONTRACT.md`.

## Core Concepts

- **Truth** (`.ai-work/truth/`) - authoritative, no silent rewrite.
- **AIP** (`.ai-work/aip/` - ROOT / PLAN / EXEC / LOCAL) - **stable macro-control**, not a runtime notebook.
- **Workspace** (`.ai-work/workspaces/<task-id>/`) - runtime execution memory: findings, draft, capture, final output.
- **Wiki / Knowledge Hub** (`.ai-work/wiki/`) - curated knowledge: domain, function, module, data, pattern, reference.
- **History** (`.ai-work/history/`) - trail, evidence, archive.

**Precedence:** Truth > Project Wiki > Local Wiki > Common Wiki > History (content). SOP > Contract > AIP_ROOT > AIP_PLAN/EXEC > Guidelines > Skills > Wiki > Workspace artifact. Knowledge classes: `source_of_truth` > `curated` > `reference` > `history`.

## Hot Operational Rules (MUST follow)

1. **Wiki Source lookup FIRST** when the user asks about a concept that belongs to canonical project knowledge: run `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>` first, then read the primary MD meta and relevant chapter/spec if needed.
   - **Match need -> tool:** find one doc = `lookup --query`; enumerate one kind, such as all functions/tables = `lookup --source-type <type> --slim`; traverse relations = `wiki_relations.py --relations <source_id>`.
   - **Chain rule:** `wiki_relations` needs a `source_id` from lookup output. Do not start with relations before you have an id.
   - **Do not read full `index.jsonl` / `relations.jsonl` just to enumerate.** Use `--source-type --slim`, `wiki_relations`, or targeted grep.
   - **Index miss requires escalation:** retry with `--mode semantic`, then raw Glob/Grep in artifact dirs hinted by tooling. Do not report "not found" after only one lookup.
2. **Never read PDF/DOCX binaries.** Follow `companion_of` pointer in meta to the primary MD.
3. **Runtime state lives in Workspace**, never in AIP body. Findings, metrics, progress, decisions, drafts belong to workspace files, not AIP sections.
4. **No silent drift from AIP.** Scope/output/objective changes require a dated Re-plan Log entry. Do not silently edit earlier AIP sections to rewrite history.
5. **No silent rewrite of Truth or official Wiki.** Use candidate -> review -> apply.
6. **Capture first, curate later.** Unknowns go to `08_capture_inbox.jsonl`, not directly into wiki.
7. **SOP first.** Tasks outside SOP/AIP_ROOT scope must be confirmed with the user.
8. **Lint is a guardrail, not a reviewer.** Do not ask tools to auto-fix wiki/truth.
9. **`wiki_first` is default behavior, not an absolute mandate.** Override only through explicit HUMAN/rule/AIP instruction. If ambiguous, clarify instead of guessing. Details and conflict rules: [wiki-guidelines.md](.ai-work/wiki/reference/wiki-guidelines.md).

## AIP Stability Rules (CRITICAL)

AIP is a stable control artifact (AIP_Detail_Spec §2.3 / §10 / §11). Turning it into a live working file is explicitly forbidden.

- **Never tick `[x]` in Done Criteria.** Done Criteria are declarative, not a progress checklist.
- **Never embed runtime metrics** in AIP. Counts, findings, and decisions discovered during execution belong in `04_findings.md`.
- **Never silently edit earlier sections** to reflect scope change. Append a Re-plan Log entry BEFORE editing.
- **`updated_at` is not a last-touched timestamp.** Bump only for real update-by-exception (§10.1).
- Allowed updates: objective, scope, expected outputs, major assumptions, explicit re-plan. Each update requires a Re-plan Log entry.
- `lint_aip.py` catches `live_working_file`, `runtime_metric_in_aip`, and missing sections. Treat warnings as errors during review.

## Execution Protocol

Before any non-trivial task (review, analysis, implementation, investigation, etc.), if no AIP exists, use the AIWS common create-aip flow first, then use run-aip to wire the workspace. Do not execute substantive work directly in chat unless the task is explicitly ad hoc.

Canonical flow:

1. Read and follow [.ai-work/procedural/skills/create-aip/SKILL.md](.ai-work/procedural/skills/create-aip/SKILL.md).
2. Read and follow [.ai-work/procedural/skills/run-aip/SKILL.md](.ai-work/procedural/skills/run-aip/SKILL.md).
3. Work in workspace files, not in the AIP body.
4. Run [.ai-work/procedural/skills/lint-all/SKILL.md](.ai-work/procedural/skills/lint-all/SKILL.md) / `python .ai-work/tooling/lint_all.py` before finalizing.

Runtime aliases:

- If available, `/create-aip`, `/run-aip`, and `/lint-all` are acceptable shorthand.
- If not available, execute the same common flow manually using `.ai-work/procedural/skills/` and `.ai-work/tooling/`.
- If `.ai-work/account_info.yaml` is missing, do not invent `account_id`; ask HUMAN to set it with `python .ai-work/tooling/account_id.py set --account-id <id>`. For explicitly requested urgent ad hoc maintenance, keep the edit tightly scoped and report the AIP precondition gap.

**No AIP needed:** ad hoc Q&A, one-off question, quick lookup, or short research can be answered directly in chat.

## Tooling & Procedural Skills

- **Tooling:** [.ai-work/tooling/](.ai-work/tooling/) - Python stdlib by default, no `pip install` unless the tool README documents an exception.
  - Find a document: `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>`.
  - Find a source's relations: `python .ai-work/tooling/wiki_relations.py --relations <source_id>`.
- **Common procedural skills:** [.ai-work/procedural/skills/](.ai-work/procedural/skills/) - canonical definitions for `create-aip`, `run-aip`, `init-workspace`, `init-project`, `point-step`, `build-active-step-context`, `build-wiki-source-meta`, `lookup-wiki-source`, `refresh-wiki-source-meta`, `lint-all`, and related AIWS operations.
- **Runtime adapters:** assistant-specific files such as `CLAUDE.md`, IDE instructions, native skill aliases, or model-specific prompts may point to the common definitions, but they are not canonical on conflict.
- **Spec reference:** [Methodology](.ai-work/truth/canonical/methodology/) and [Wiki Guidelines](.ai-work/truth/canonical/wiki_guidelines/).

## Notes

- Python stdlib only unless explicitly documented.
- Windows: tools force UTF-8 stdout where supported.
- User language: Vietnamese + English mixed by default.
- Always work from project root, where `.ai-work/` sits.

## AIWS Knowledge Sources (installed)

When the user asks about AI Work System or needs to create an AIP template, search these sources:

- Methodology: `.ai-work/truth/canonical/methodology/`
  - Use for AIWS design, spec, concepts, SOP flow.
- Wiki Guidelines: `.ai-work/truth/canonical/wiki_guidelines/`
  - Use for Knowledge Hub, wiki source, wiki meta, canonical guideline questions.
- Preset Knowledge: `.ai-work/preset_knowledge/`
  - Use when creating a new AIP and looking for an exec template or suitable sample.
  - Nav: `aip_exec/`, `aip_samples/`, `AIP_SELECTION_GUIDE.md`.

## Net COBOL Knowledge Source (manuals)

When the user asks about Net COBOL (`COPY`, `PERFORM`, `CALL`, file I/O, SCREEN/FORM), prioritize wiki lookup against Net COBOL meta/index:

- Note: the Net COBOL manuals include Japanese source documents. Add Japanese keywords when useful for recall.
- Meta dir: `.ai-work/wiki_sources/net_cobol/`
- Index file: `.ai-work/wiki_sources/index.net_cobol.jsonl`
- Artifact root: `manuals/net_cobol/`

Recommended lookup commands:

- Lexical:
  `python .ai-work/tooling/lookup_wiki_source.py --query "COPY" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl`
- Semantic:
  `python .ai-work/tooling/lookup_wiki_source.py --query "cach dung COPY trong Net COBOL" --mode semantic --index .ai-work/wiki_sources/index.net_cobol.jsonl`
- Japanese keywords:
  `python .ai-work/tooling/lookup_wiki_source.py --query "COPY文 REPLACING" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl`

To search both Net COBOL and AIWS docs in one lookup, use multiple indices:

`python .ai-work/tooling/lookup_wiki_source.py --query "COPY REPLACING" --index .ai-work/wiki_sources/index.net_cobol.jsonl,.ai-work/wiki_sources/index.aiws.jsonl`
