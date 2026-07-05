# CLAUDE.md - hermes-poc

Claude-specific project overlay.

## Read First

Read `AGENTS.md` first. It is the shared repository operating guide for all models and agents.

This file only adds Claude-specific execution rules and pointers. It must not duplicate, replace, or weaken the shared rules in `AGENTS.md`.

On conflict:

1. `.ai-work/truth/` and canonical AIWS specs win.
2. `AGENTS.md` wins for shared project rules.
3. `.ai-work/procedural/skills/` wins for common AIWS procedure definitions.
4. This file and `.claude/skills/` are Claude adapters only.

## Claude-Specific AIWS Protocol

For Claude, non-trivial work should use the AIWS slash-command flow:

1. If the task is non-trivial and no suitable AIP exists, run `/create-aip`.
2. Run `/run-aip` to wire the workspace before execution.
3. Keep runtime findings, progress, metrics, decisions, and drafts in workspace files, not in AIP body sections.
4. Run `/lint-all` before finalizing AIWS artifacts when feasible.

No AIP is required for ad hoc Q&A, single-command checks, quick lookup, or short research tasks.

If `.ai-work/account_info.yaml` is missing, do not invent `account_id`; ask HUMAN to set it with:

```powershell
python .ai-work/tooling/account_id.py set --account-id <id>
```

## Claude Skills And Commands

Claude-compatible AIWS skills may live under `.claude/skills/`. Treat them as command adapters and entry points, not as canonical project truth.

Common commands:

- `/create-aip`
- `/run-aip`
- `/init-workspace`
- `/init-project`
- `/point-step`
- `/build-active-step-context`
- `/build-wiki-source-meta`
- `/lookup-wiki-source`
- `/refresh-wiki-source-meta`
- `/lint-all`

Before using a Claude skill, read the relevant `.claude/skills/<skill-name>/SKILL.md`. If that file points to `.ai-work/procedural/skills/<skill-name>/SKILL.md`, follow the common definition there.

## Claude Tooling Notes

- AIWS tooling lives in `.ai-work/tooling/`.
- AIWS tooling is Python stdlib by default; do not install packages unless the tool README documents an exception or the user explicitly asks.
- Always work from the project root where `.ai-work/` sits.
- Preserve UTF-8 output on Windows where possible.
- Do not read PDF/DOCX binaries directly; follow `companion_of` pointers to primary Markdown artifacts.

## Knowledge Lookup Reminders

- For AIWS/project canonical concepts, run `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>` before answering or changing related artifacts.
- For Net COBOL questions, prefer the Net COBOL index:

```powershell
python .ai-work/tooling/lookup_wiki_source.py --query "COPY" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl
```

- On index miss, retry semantic lookup before raw file search.
