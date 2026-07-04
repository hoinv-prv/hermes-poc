---
name: run-aip
description: >
  Orchestrate AIP execution: start a new execution, resume an in-progress task, jump to a specific
  step, or check status. TRIGGER when: user says "run AIP", "start AIP", "resume AIP", "chạy AIP",
  "bắt đầu task", "tiếp tục task", "resume task", "nhảy step", "jump to step", "xem status AIP",
  "AIP status"; after /create-aip completes and user wants to begin execution; after pointing to
  a new step. SUBCOMMANDS: start / resume / step / status / list. Creates workspace and materializes
  Active Step Context (00c_active_step_context.md) so AI can begin working.
user-invocable: true
---

# SKILL: run-aip

> **Full definition (common):** [.ai-work/procedural/skills/run-aip/SKILL.md](.ai-work/procedural/skills/run-aip/SKILL.md)
> Read that file for complete instructions before proceeding.

## Reminder — capture wiki candidates IMMEDIATELY on discovery

Every time you invoke this skill (`start` / `resume` / `step`), re-read this rule:

- The moment you notice a wiki-promotable item — reusable pattern, spec/impl drift,
  non-obvious convention, HUMAN-confirmed decision, missing wiki knowledge,
  retrieval friction, tooling opportunity — append it to
  `.ai-work/workspaces/<task-id>/08_capture_inbox.jsonl` **right then**.
- Do **not** batch captures to step end or AIP close. Inline-as-you-discover is the default;
  end-of-step is only a final sweep for items missed mid-stream.
- Filter for Knowledge Value (non-obvious + reusable). Don't capture noise.
- Never promote into Wiki / Knowledge Hub directly — promotion is HUMAN-controlled.

Refer to [`.ai-work/procedural/wiki_candidate_capture_playbook.md`](../../../.ai-work/procedural/wiki_candidate_capture_playbook.md) for triggers, kinds, and JSON record format.

## New rules — see canonical for full text

The canonical run-aip SKILL.md gained these sections at 2026-05-12 (ported from an AIWS deployment):

- **Wiki-first preflight at HARD GATE** → [canonical §Wiki-first preflight at HARD GATE](../../../.ai-work/procedural/skills/run-aip/SKILL.md#wiki-first-preflight-at-hard-gate) — 3-step preflight before posing HARD GATE clarifying questions; cite wiki path in `Applicable Guidelines` or use `wiki:none` opt-out. Enforced by `lint_aip.py` rule `wiki_first_preflight_at_hard_gate`.
- **When closing an AIP — Target-spec attribution check** → [canonical §When closing an AIP](../../../.ai-work/procedural/skills/run-aip/SKILL.md#when-closing-an-aip) — before flipping status `active → done`, grep target specs for AIP-ID and verify Re-plan Log reflects landed changes.
- **Section-number conflict heuristic** → [canonical §Step execution heuristics](../../../.ai-work/procedural/skills/run-aip/SKILL.md#step-execution-heuristics) — when an OP-decision pins an occupied section number, append as `§N+1` (next-available adjacent); document in Re-plan Log + target-doc Revision History; do not re-clarify unless intent is ambiguous.

Read the canonical SKILL.md before applying these rules — pointer-only summaries here are a reminder, not a substitute.
