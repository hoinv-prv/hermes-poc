---
name: point-step
description: >
  Set the current-step pointer in a workspace so subsequent context builds and lints know which
  AIP step is active. TRIGGER when: user says "chuyển sang step", "nhảy step", "point to step",
  "set current step", "move to STEP-NN"; advancing manually from one AIP step to the next without
  using /run-aip step; workspace pointer needs to be corrected. Must be called BEFORE
  build-active-step-context when advancing steps manually.
user-invocable: true
---

# SKILL: point-step

> **Full definition (common):** [.ai-work/procedural/skills/point-step/SKILL.md](.ai-work/procedural/skills/point-step/SKILL.md)
> Read that file for complete instructions before proceeding.
