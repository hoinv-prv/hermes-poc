---
name: point-step
description: Set the current-step pointer for a workspace (which AIP + step is active)
user-invocable: true
---

# SKILL: point-step

## Purpose
Move the current-step pointer in a workspace so subsequent context builds
and lints know which AIP step is active.

## Tool
`.ai-work/tooling/set_current_step.py`

### Example
```
python .ai-work/tooling/set_current_step.py \
  --workspace .ai-work/workspaces/TASK-20260414-review-mo-update \
  --aip AIP-PLAN-001 \
  --aip-path .ai-work/aip/plans/AIP-PLAN-001-review-mo-update.md \
  --step-id STEP-02 \
  --status active
```

## Effect
- writes `.current_step.json` in the workspace
- updates `00b_active_aip.md` with the new AIP id/path and status

## Rules
- do not point to a step that does not exist in the AIP
- use this before `build-active-step-context`
- status should be `active | blocked | done`
