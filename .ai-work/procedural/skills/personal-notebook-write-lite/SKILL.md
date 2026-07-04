---
name: personal-notebook-write-lite
description: Lightweight skill to initialize and write Personal Notebook notes with status/authority/source hints
user-invocable: true
---

# SKILL: personal-notebook-write-lite

## Purpose
Help AI/HUMAN create, append, and lightly update file-based Personal Notebook notes.

## Guardrails
- Write only when HUMAN explicitly asks or confirms, unless local setup clearly allows otherwise.
- Do not auto-promote notebook content to Knowledge Hub.
- Do not treat notebook content as source of truth by default.
- Preserve status / authority / source hints.
- Do not rewrite or delete aggressively.
- Do not become decision authority or orchestrator.

## Inputs
- notebook path
- operation
- title
- status
- authority
- source
- intended use
- review needed
- body

## Supported operations
- `init_notebook`
- `append_inbox_note`
- `create_note_file`
- `mark_capture_candidate`
- `archive_note`

## Tool
`scripts/notebook_write.py`

## Example
```bash
python scripts/notebook_write.py \
  --operation append_inbox_note \
  --notebook-path ./.aiws/personal_notebook \
  --title "Future sprint idea: Notebook search" \
  --status future_sprint_idea \
  --authority personal \
  --source self \
  --intended-use "sprint planning" \
  --review-needed yes \
  --body "Consider a later sprint for Personal Notebook search/index support."
```

## Result
The tool writes to the configured Personal Notebook and returns a short JSON result.
