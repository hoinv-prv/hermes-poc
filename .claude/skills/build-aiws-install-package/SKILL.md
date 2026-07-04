---
name: build-aiws-install-package
description: >
  Package the current AI Work System MVP into a versioned, self-contained install package so it
  can be deployed into other projects via /init-project. TRIGGER when: user says "tạo package
  AIWS", "build install package", "đóng gói AIWS", "xuất package", "release new AIWS version";
  preparing a new AIWS version to distribute. Does NOT ship runtime files (workspaces, aip/exec,
  history, wiki) or Truth files. Always creates a new versioned folder — never overwrites previous
  package.
user-invocable: true
---

# SKILL: build-aiws-install-package

> **Full definition (common):** [.ai-work/procedural/skills/build-aiws-install-package/SKILL.md](.ai-work/procedural/skills/build-aiws-install-package/SKILL.md)
> Read that file for complete instructions before proceeding.
