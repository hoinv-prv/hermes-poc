# GitHub Copilot Rules for hermes-poc

This repository uses AI Work System MVP v1.0.5.
Always follow these rules before proposing code, edits, or reviews.

## Source of truth and precedence
- Treat files under .ai-work/truth/ as authoritative.
- Use this precedence for knowledge conflicts:
  1. Truth
  2. Project Wiki
  3. Local Wiki
  4. Common Wiki
  5. History
- If there is a conflict, methodology/spec wins unless an approved deviation exists in .ai-work/truth/AI_WORK_CONTRACT.md.

## Mandatory workflow for non-trivial tasks
- For non-trivial work (review, analysis, implementation, investigation):
  1. Run /create-aip if no AIP exists.
  2. Run /run-aip to wire workspace execution context.
  3. Work in workspace files, not in AIP body.
  4. Run /lint-all before finalize.
- No AIP is required for ad-hoc Q&A, quick lookup, or short research.

## Wiki-first behavior
- For canonical project concepts, lookup source first:
  - python .ai-work/tooling/lookup_wiki_source.py --query <keyword>
- Use the right tool shape:
  - Find one document: lookup --query
  - Enumerate one source type: lookup --source-type <type> --slim
  - Traverse relations: python .ai-work/tooling/wiki_relations.py --relations <source_id>
- Do not read index.jsonl or relations.jsonl directly just to enumerate.
- If lookup misses:
  1. Retry semantic mode.
  2. Then use targeted glob/grep in hinted artifact paths.
  3. Do not stop after a single miss.

## Net COBOL manuals lookup
- Net COBOL wiki meta lives at .ai-work/wiki_sources/net_cobol/.
- Net COBOL index file is .ai-work/wiki_sources/index.net_cobol.jsonl.
- Important: Net COBOL manuals include Japanese source documents. Prefer adding Japanese query terms to improve lookup recall.
- For Net COBOL topics (COPY, PERFORM, CALL, FILE I/O, FORM), prefer lookup against this index first:
  - python .ai-work/tooling/lookup_wiki_source.py --query "COPY" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl
  - python .ai-work/tooling/lookup_wiki_source.py --query "COPY REPLACING" --mode semantic --index .ai-work/wiki_sources/index.net_cobol.jsonl
  - python .ai-work/tooling/lookup_wiki_source.py --query "COPY文 REPLACING" --mode lexical --index .ai-work/wiki_sources/index.net_cobol.jsonl
- If cross-check with AIWS docs is needed, query multiple indices in one command:
  - python .ai-work/tooling/lookup_wiki_source.py --query "COPY" --index .ai-work/wiki_sources/index.net_cobol.jsonl,.ai-work/wiki_sources/index.aiws.jsonl

## AIP stability rules (strict)
- AIP is stable control artifact, not runtime notebook.
- Do not mark Done Criteria checkboxes as runtime progress.
- Do not put runtime metrics/findings/decisions into AIP sections.
- Do not silently edit earlier AIP sections after scope changes.
- For replans, append dated Re-plan Log entries first.
- updated_at is not a last-touched timestamp; update only by exception.

## Editing and curation guardrails
- Never silently rewrite Truth or official Wiki.
- Follow candidate -> review -> apply for canonical updates.
- Capture first, curate later:
  - Put unknowns into workspace capture inbox (08_capture_inbox.jsonl).
- SOP first:
  - If a task is outside SOP/AIP_ROOT scope, confirm with user before proceeding.
- Lint is guardrail, not reviewer. Do not auto-fix canonical artifacts blindly.

## Artifact handling rules
- Never read PDF or DOCX binaries directly when a primary Markdown companion exists.
- Use companion_of pointer in source meta and read primary Markdown.

## Environment and tooling constraints
- Work from project root (where .ai-work/ exists).
- Use Python stdlib only for project tooling (no pip install).
- Assume Windows shell behavior and UTF-8-safe output handling.

## Project pointers
- Methodology: .ai-work/truth/canonical/methodology/
- Wiki Guidelines: .ai-work/truth/canonical/wiki_guidelines/
- Preset knowledge: .ai-work/preset_knowledge/
- Tooling catalog: .ai-work/tooling/README.md
- Key skills: .claude/skills/
