---
name: test-wiki-lookup
description: >
  Test wiki lookup quality after creating index/meta — verify entries are discoverable.
  TRIGGER when: user says "test wiki lookup", "kiểm tra wiki lookup", "thử lookup",
  "hãy test wiki lookup cho...", "verify lookup", "lookup có tìm ra không",
  "check if wiki can find", "test xem wiki tìm được gì cho tác vụ...";
  after registering new wiki source meta/index; after updating lookup_keys;
  when investigating why a source is not surfaced by lookup.
  Supports 3 modes: (A) self-test automated, (B) structured JSONL cases, (C) natural language task description.
user-invocable: true
---

# SKILL: test-wiki-lookup

> **Full definition (common):** [.ai-work/procedural/skills/test-wiki-lookup/SKILL.md](.ai-work/procedural/skills/test-wiki-lookup/SKILL.md)
> Read that file for complete instructions before proceeding.
