# Instance Initialization Guide — Test Case Review Agent

> Mapped from: Document_Review_Agent_Blueprint/templates/INSTANCE_INITIALIZATION_GUIDE.md (template_version v0.1).
> Aligned to pack instance schema: Detailed Design v0.2 §4 (instance) + §5 (blueprint_ref) + §7 (context) + §8 (workspace) + §15 (memory).
> Mirror the precedent instance shape: agents/instances/wiki_meta_strategy_coordinator__sample_project/.

## 1. Instance identity (`instance.yaml` — §4)
```yaml
instance_id: testcase_review_agent__<project_or_context>
instance_name: <Readable Name>
creation_mode: blueprint_based
blueprint_id: testcase_review_agent
blueprint_version: "0.1"
project_id: <project_id>
owner: HUMAN
status: active
created_at: "<YYYY-MM-DDThh:mm:ss+09:00>"
last_reviewed_at: null
```
Also write `blueprint_ref.yaml` (§5) pointing at this blueprint + version.

## 2. Context (`context/` — §7, Wiki-first NOT Wiki-only)
- `wiki_references.yaml` — Wiki entries to read FIRST (project overview, business rules,
  feature/screen/API behavior, known cautions, past defects).
- `source_references.yaml` — source the cases must trace back to (requirements, design,
  feature/API/screen specs, the test-case document under review).
- `source_priority.yaml` (§7.4) — Wiki-first ordering; source verification required when Wiki is
  stale/unverified, a conflict is detected, or output feeds an official deliverable.
- `ignored_paths.yaml` — paths to skip.

## 3. Memory (`memory/` — §15; blueprint `memory_profile`) — EXACTLY 8 files (review-family UNION-8), created EMPTY (AP-CR-36)
```text
memory/confirmed_memory.jsonl
memory/lessons_learned.md
memory/retrieval_hints.jsonl
memory/common_issue_patterns.md
memory/false_positive_notes.md
memory/local_guidelines.md
memory/output_preferences.md
memory/tool_usage_notes.md
```
Create EMPTY. Seed ONLY HUMAN-approved initial memory — never auto-seed. `false_positive_notes.md`
is important for review agents (prevents repeated invalid coverage findings).

## 4. Workspace + training (§8 / §14)
```text
workspace/active_runs/
workspace/completed_runs/
workspace/handoff_artifacts/
workspace/step_outputs/
training/feedback_log.jsonl
training/candidate_queue.jsonl
training/periodic_review_log.md
```

## 5. Tools (§16)
```text
tools/local_tools/
tools/tool_bindings.yaml   # default_tools is [] — bind tools only when HUMAN-activated
```

## 6. Run capture routing (§14 / AP-CR-13)
- Running UNDER an AIP: tier the capture UP to the project capture inbox
  `08_capture_inbox.jsonl` / wiki-candidate flow; the instance keeps a POINTER, not a duplicate.
- Running WITHOUT an AIP: capture stays local in `training/candidate_queue.jsonl`.
Promotion to confirmed memory / Official Wiki is HUMAN-gated in both branches.

## 7. Done criteria
Identity clear; blueprint_ref set; Wiki/source references configured (Wiki-first ordering); shared
checklist/process/output bound via the blueprint; memory/training/workspace/tools folders exist
(memory empty); HUMAN understands the agent reviews coverage + advises only (no approve, no edit, no
test execution, no auto-update).
