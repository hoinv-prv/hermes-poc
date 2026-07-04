---
name: lint-all
description: Run AIP + workspace + wiki lints and aggregate a single report
user-invocable: true
---

# SKILL: lint-all

## Purpose
Single-command deterministic lint across all MVP targets:
- AIP (ROOT / PLAN / EXEC / LOCAL)
- Wiki entries
- Wiki Source Meta
- Wiki Source Index
- Every workspace under `.ai-work/workspaces/`

## Tool
`.ai-work/tooling/lint_all.py`

### Example
```
python .ai-work/tooling/lint_all.py --strict --format text
```

### Exit codes
- `0` — clean (or only info)
- `1` — warnings present AND `--strict`
- `2` — at least one error

## When to run
- after creating/updating any AIP
- after generating an Active Step Context
- after building/refreshing a Wiki Source Meta or Index
- before finalizing a wiki update
- in CI on every push touching `.ai-work/`

## Rules
- lint is a guardrail, not a reviewer
- do not ask the tool to auto-fix wiki or truth
- treat warnings as "please look before merging"
