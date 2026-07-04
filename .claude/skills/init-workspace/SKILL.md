---
name: init-workspace
description: >
  Scaffold a new task workspace at .ai-work/workspaces/<task-id>/ to hold runtime execution memory
  (brief, active AIP, active step context, queue, findings, capture inbox, draft, final output).
  TRIGGER when: starting execution of a new AIP and no workspace exists yet; user says "tạo
  workspace", "khởi tạo workspace", "init workspace for task"; typically called automatically by
  /run-aip start — call manually only when run-aip is not used. Do NOT reuse old workspaces without
  --force.
user-invocable: true
---

# SKILL: init-workspace

> **Full definition (common):** [.ai-work/procedural/skills/init-workspace/SKILL.md](.ai-work/procedural/skills/init-workspace/SKILL.md)
> Read that file for complete instructions before proceeding.
