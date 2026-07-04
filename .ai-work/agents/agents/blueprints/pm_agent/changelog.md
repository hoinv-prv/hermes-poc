# Changelog — PM Agent (blueprint)

## Provenance
- source_template: `docs/agent_pack_impl_package/agent_templates/PM_Agent_Blueprint`
- template_version: v0.1
- mapping_note: `../_shared/review/MAPPING_NOTE_template_to_pack_schema.md` (RENAME + ADD rules;
  PM does NOT use the shared review process/checklist/output assets — those are review-specific)
- target_schema: Detailed Design v0.2 §3 (blueprint), §2 (registry)
- on-disk precedent mirrored: `../wiki_meta_strategy_coordinator/`

## 0.1 — 2026-06-21
- Initial blueprint created (AIP-EXEC-139 / STEP-04), type `project_management`, PLANNING/ADVISORY only.
- Mapped from PM_Agent_Blueprint template (v0.1):
  - RENAME: `blueprint_name`->`name`, `agent_type`->`type` (`project_management`), `version`->`blueprint_version`,
    `inputs`->`input_contract`, `outputs`->`output_contract`.
  - ADD: `creation_mode: blueprint_based` + `blueprint_id: pm_agent`.
  - FOLD: process_docs / output_templates folded to blueprint-local relative paths.
  - ADDITIVE blocks (template-unique, kept): `target_use_cases`, `wiki_policy` (Wiki-first NOT
    Wiki-only), `output_rules`, `pm_modes`, `learning_candidate_types`, `known_limitations`,
    `workspace_policy` — placed after the pack-schema core keys.
- output_contract split per CONFIRMED default (R-6 / OQ-4):
  - required: `task_breakdown.md`, `progress_report.md`, `risk_issue_decision_log.md`
  - optional: `replan_options.md`, `prioritization_output.md`
- non_responsibilities forbid: final decisions, auto-run/self-trigger, orchestrate, dispatch other
  agents; plus no official schedule/owner/scope/release without HUMAN confirmation.
- Skills: flat list (31 skills) in `blueprint.yaml`; the 7 PM categories preserved in
  `skills/skill_index.yaml` (skill_categories).
- default_tools: empty (planning/advisory; no extraction/execution tools).
- default_memory_seed/memory_seed.jsonl: empty (no unapproved seed).
- memory_policy: auto_confirm_memory false, human_review_required true.
- AP-DDR-01: PM catalogued as a Wiki Consumer Agent; blueprint `type` stays `project_management`.
- YAML: plain/literal scalars only (NO folded `>-`); cross-refs use relative paths.
- Registered in `agents/blueprint_registry.yaml`.
