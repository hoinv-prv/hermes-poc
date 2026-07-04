---
name: lint-all
description: >
  Run all lints (AIP + workspace + wiki + wiki source meta + index) and produce a single aggregated
  report. TRIGGER when: user says "lint", "kiểm tra lỗi", "validate", "check AIP", "check wiki",
  "lint-all", "run lint"; before finalizing any AIP; before committing wiki changes; after creating
  or updating a Wiki Source Meta; after building Active Step Context; in CI on .ai-work/ changes.
  Treats warnings as errors when --strict is passed.
user-invocable: true
---

# SKILL: lint-all

> **Full definition (common):** [.ai-work/procedural/skills/lint-all/SKILL.md](.ai-work/procedural/skills/lint-all/SKILL.md)
> Read that file for complete instructions before proceeding.
