# Agent Authoring Guide — AI Agents Pack (current agents)  (Phase J-1)

> **STAGING / NON-CANONICAL.** Built by AIP-EXEC-141 (Phase J-1) STEP-04.
>
> How to author a new **Blueprint** (reusable agent definition) or **Instance** (named, tracked
> runtime unit) in this pack. Worked example throughout = the 3 priority agents built in AIP-EXEC-139
> (`detailed_design_review_agent`, `testcase_review_agent`, `pm_agent`) + the `wiki_meta_strategy_coordinator`
> precedent. This guide is **current-agents-scope**; the deferred agent types (program phases
> **D**/**E**/**F**/**G**/**H**) are **deferred — see `known_limitations_and_backlog.md`**.
>
> Schema reference: Detailed Design v0.2 §3 (blueprint) / §4 (instance) / §5 (blueprint_ref) / §7 +
> §7.5 (context / working_inventory) / §15 (memory). Paths are relative to the **pack root** (`development/ai_agents/` in the AIWS dev repo · `.ai-work/agents/` when installed (single-track)).

## Blueprint vs Instance (what you author)

- **Blueprint** (`agents/blueprints/<blueprint_id>/`) — reusable **initial-state** definition. Stores
  **no** project-specific memory. Defines mission, responsibilities/non_responsibilities, input/output
  contracts, skills, policies, and references to process/checklist/output assets.
- **Instance** (`agents/instances/<instance_id>/`) — the real tracked unit: binds a blueprint to one
  project's `context/`, `memory/`, `workspace/`, `training/`, `tools/`. Created with
  `/aiws-agent-create` (see `command_usage_guide.md`).

You usually only author a **new blueprint** when no existing one fits; otherwise you author an
**instance** of an existing blueprint. Both follow the disciplines below.

## NAMING LAW — `*__sample_project` instances are DEV-ONLY (never shipped)

**Any instance whose id ends with the suffix `__sample_project` is a dev/test fixture (dogfood) and is
NEVER shipped or promoted.** It exists only in staging (`development/ai_agents/agents/instances/`) so the
pack can be exercised end to end here. The install/promotion ship-set is blueprints + registry +
templates + commands + tooling **only** — **no instance is ever shipped**. **Real instances are created
on the target** via `/aiws-agent-create` (promotion lays down an empty `.ai-work/agents/instances/.gitkeep`
as the write location). This is a **one-line rule, not a hand-maintained exclusion list**: the suffix
`__sample_project` alone marks an instance as never-ship. So when you author a fixture for dogfooding,
**name it `<blueprint_id>__sample_project`**; when you author a real instance for an actual project, give
it a project-meaningful id with **no** `__sample_project` suffix. Ref: **AP-CR-24** (PROMOTION-EXCLUDES
invariant in `promotion_readiness_note.md` §3(1)).

## 1. MAP-DON'T-FORK

When a new blueprint comes from an external/source template, **map it into the pack schema — never
fork a parallel shape.** This is the contract recorded in
`agents/blueprints/_shared/review/MAPPING_NOTE_template_to_pack_schema.md` and used to build all three
priority agents. Three operations:

- **RENAME** template keys → pack-schema keys: `blueprint_name`→`name`, `agent_type`→`type`,
  `version`→`blueprint_version` (quoted string, e.g. `"0.1"`), `inputs`→`input_contract`,
  `outputs`→`output_contract` (keep the `required`/`recommended`/`optional` tiers). Values that already
  match (`blueprint_id`, `status`, `mission`, `responsibilities`, `non_responsibilities`) carry over.
- **FOLD** template detail into the pack shape: process/checklist/output content folds to **relative
  references** to shared/blueprint-local files rather than being copied 1:1; placeholder `<...>` slots
  are resolved to plain text.
- **ADD** required + template-unique blocks **additively**: always add `creation_mode:
  blueprint_based` and `blueprint_id`. **Template-unique fields with no pack-schema home are kept as
  ADDITIVE blocks (not dropped, not silently merged), placed AFTER the pack-schema core keys** so a
  reader sees the canonical contract first. (For the review blueprints these are `target_document`,
  `review_principles`, `finding_categories`, `severity_examples`, `learning_candidate_types`.)

**Core-key order** mirrors the precedent: `creation_mode`, `blueprint_id`, `blueprint_version`, `name`,
`type`, `status`, `mission`, `responsibilities`, `non_responsibilities`, `input_contract`,
`output_contract`, `skills`, `default_tools`, `memory_policy`, `workspace_policy`,
`human_gate_policy` — then additive blocks. YAML uses **plain or literal (`|`) scalars only — no folded
`>-`**, and **all cross-references are relative paths** (never absolute, never `.ai-work/`-rooted) so
the staged tree and a future promoted tree resolve identically.

> **Worked example.** `agents/blueprints/detailed_design_review_agent/blueprint.yaml` was mapped from
> the read-only `docs/agent_pack_impl_package/agent_templates/Document_Review_Agent_Blueprint`
> (template_version v0.1): RENAME applied, FOLD to `../_shared/review/...` refs, ADD of
> `creation_mode`/`blueprint_id` + the review-specific additive blocks. AIP-EXEC-140 later **additively**
> grafted a single `memory_load_policy` block (new keys only) — it modified no existing key. That is
> MAP-DON'T-FORK in practice: extend additively, never re-shape.

## 2. Reuse `_shared/` assets — don't copy

Document-type-agnostic review assets live once under
`agents/blueprints/_shared/review/` and are **referenced**, not duplicated per blueprint:

```
agents/blueprints/_shared/review/
  MAPPING_NOTE_template_to_pack_schema.md
  process/{document_review_process,severity_definition,finding_format,source_trace_rule,lesson_capture_rule}.md
  checklists/common_document_review_checklist.md
  output_templates/{review_report,findings_table,open_questions,references_used,review_limitations}.md
```

A review blueprint references them with relative paths from its own folder, e.g.:

```yaml
process_docs:
  review_process:      ../_shared/review/process/document_review_process.md
  severity_definition: ../_shared/review/process/severity_definition.md
  # ...
checklists:
  common:            ../_shared/review/checklists/common_document_review_checklist.md
  document_specific: checklists/<doc_type>_review_checklist.md   # blueprint-local (type-specific)
output_templates:
  shared_dir: ../_shared/review/output_templates/
```

**Rule of thumb:** document-type-agnostic content (review process, severity tiers, finding format,
source-trace + lesson-capture rules, common checklist, report shape) → **shared**; document-type-specific
content (the per-type checklist, type-specific skills, mission wording, type severity examples) → lives
under the individual blueprint. This is why a change to common review behavior is made once and picked
up by every review blueprint — no drift. **PM caveat:** the PM blueprint reuses RENAME/ADD but does
**not** use the shared review assets (those are review-specific); PM = planning/advisory only.

## 3. `context/working_inventory.yaml` is instance-owned

`context/working_inventory.yaml` (Detailed Design v0.2 §7.5) lists the specific **non-wiki /
not-yet-indexed** files an instance needs (project drafts, working files, scratch artifacts not yet in
the Wiki Source Index). It is **INSTANCE-OWNED: a blueprint update must NOT overwrite it** (FR-AI-05).
Author it on the instance, not the blueprint. It ships **empty** (`working_inventory: []`); register
shared/stable files into the Wiki Source Index (status `draft`) and reference them by `source_id`
rather than copying raw paths into multiple agents' inventories (avoids drift). Wiki content belongs in
`context/wiki_references.yaml`, not here.

## 4. Memory empty-skeleton rule (no fabricated seed)

**Instances ship with empty memory.** Create the memory files as empty skeletons (header +
`_(none yet)_`); seed content **only** when a HUMAN approves it through the learning loop. There is no
auto-seeding, no fabricated examples. The review blueprints declare **exactly 7** memory files
(`INSTANCE_INITIALIZATION_GUIDE.md` §3): `confirmed_memory.jsonl`, `lessons_learned.md`,
`retrieval_hints.jsonl`, `common_issue_patterns.md`, `false_positive_notes.md`,
`output_preferences.md`, `tool_usage_notes.md` — all empty at creation.

How memory actually fills: a run captures **learning candidates** (`status: candidate`,
`agents/templates/learning_candidate_schema.md`); `/aiws-agent-feedback` adds more candidates;
`/aiws-agent-review-learning` is the HUMAN gate that turns a confirmed candidate into a
`confirmed_memory.jsonl` entry (`source_candidate` + `confirmed_by: HUMAN`). Nothing is auto-confirmed.

> **Worked example.** The 3 priority-agent sample instances ship empty memory by design — e.g.
> `…/detailed_design_review_agent__sample_project/memory/lessons_learned.md` is just a header +
> `_(none yet)_`, and `working_inventory.yaml` is `[]`. AIP-EXEC-140 explicitly **dropped** the source
> template's `memory/examples/{good,bad}_outputs.md` because seeding unapproved placeholder content
> would violate the empty-skeleton rule.

## 5. Provenance (`source_template` / `template_version` in the changelog)

Every authored blueprint records where it came from in its `changelog.md`, so a mapping is auditable and
a future promotion CR can trace it. Record at minimum:

- `source_template:` — the read-only provenance template path.
- `template_version:` — e.g. `v0.1`.
- `mapping_note:` — the MAPPING_NOTE used.
- `target_schema:` — the Detailed Design schema sections targeted.
- `on_disk_precedent_mirrored:` — the existing blueprint whose shape you mirrored.
- `mapping_rules_applied:` — the RENAME / FOLD / ADD decisions.

Also note `creation_mode` / `blueprint_id` / `blueprint_version` in the blueprint header comment, and in
the **instance** carry `blueprint_ref.yaml` (Detailed Design v0.2 §5) with the blueprint id/version, a
**relative** `blueprint_path`, and a `customization_summary`.

> **Worked example.** `agents/blueprints/detailed_design_review_agent/changelog.md` records `0.1` (initial
> map from `Document_Review_Agent_Blueprint`, template_version v0.1, mapping_note + target_schema +
> mirrored precedent + RENAME/FOLD/ADD) and the additive `0.1.1` graft — including the "NOT absorbed"
> items each with a reason. The instance's `blueprint_ref.yaml` points back with
> `blueprint_path: ../../blueprints/detailed_design_review_agent/` (relative).

## 6. Authoring checklist

- [ ] No suitable blueprint exists → author a new one (else just `/aiws-agent-create` an instance).
- [ ] Mapped from the source template via RENAME / FOLD / ADD — **not forked**; additive blocks kept.
- [ ] `creation_mode: blueprint_based` + `blueprint_id`; core-key order mirrors the precedent.
- [ ] Document-type-agnostic assets referenced from `_shared/` (relative); only type-specific assets
      are blueprint-local.
- [ ] All cross-refs relative; YAML plain/literal only (no folded `>-`).
- [ ] Instance memory created **empty** per the blueprint's `memory_profile.required_files` (review agents = UNION-8); no fabricated seed.
- [ ] `context/working_inventory.yaml` authored on the instance (empty by default); never overwritten
      by a blueprint update.
- [ ] Provenance recorded in `changelog.md` (`source_template` / `template_version` / mapping rules);
      instance `blueprint_ref.yaml` set with a relative `blueprint_path`.
- [ ] Registered in `agents/blueprint_registry.yaml` (id / name / type / status / relative path /
      description) — see the registry-update step / `setup_guide.md` §4.
- [ ] Guardrails baked in: review/PM = advisory (honor `non_responsibilities`); no auto-run /
      auto-promotion; learning candidates HUMAN-gated.

## Related guides

`setup_guide.md` (install/wire) · `command_usage_guide.md` (the command groups: Core runtime · Instance lifecycle · Convenience router) · `user_guide.md` (run the
agents) · `known_limitations_and_backlog.md` (deferred scope) · `promotion_readiness_note.md`.
