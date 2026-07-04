# PM Agent Instance Initialization Guide

> Mapped from PM_Agent_Blueprint/templates/INSTANCE_INITIALIZATION_GUIDE.md (template_version v0.1).
> Use when creating a PM Agent Instance from this blueprint (`blueprint_id: pm_agent`). The instance
> mirrors the precedent instance shape (see
> ../../../instances/wiki_meta_strategy_coordinator__sample_project/). PM = PLANNING / ADVISORY only.

## 1. Purpose
Create a project-specific, trainable copy of the PM Agent blueprint. The instance is INSTANCE-OWNED
and is not overwritten by blueprint updates (FR-AI-05).

## 2. Required instance information
```yaml
instance_id: pm_agent__<project_name>
instance_name: PM Agent for <Project Name>
creation_mode: blueprint_based
blueprint_id: pm_agent
blueprint_version: "0.1"
project_id: <project_id>
owner: <HUMAN/PM/Team>
status: active
created_at: "YYYY-MM-DDThh:mm:ss+09:00"
last_reviewed_at: null
```

## 3. Project context setup (ask HUMAN)
- What project does this PM Agent support?
- Is it sprint-based, milestone-based, or ad-hoc?
- What are the main deliverables and the main deadlines/milestones?
- Where is the task list? the project Wiki? the meeting notes? the risk/issue/action logs?
- Who reviews PM reports? Who is the official decision owner (always HUMAN)?

## 4. Context files (instance `context/`, mirroring the precedent instance)
- `source_priority.yaml` — source_priority ordering (Detailed Design §7.4): **Wiki-first NOT
  Wiki-only** — Wiki/metadata first, then AIP / task list / schedule / status / meeting notes;
  conflicts reported, never silently resolved.
- `source_references.yaml` — task sources, report sources, AIP/working-AIP paths.
- `wiki_references.yaml` — project Wiki entries the agent consults first.
- `ignored_paths.yaml` — e.g. `tmp/`, `archive/`.
- (working_inventory per §7.5 may be added as the instance is used.)

## 5. Memory initialization (CONFIRMED default = 8 files, created EMPTY)
Create, EMPTY (no unapproved seed):
```text
memory/confirmed_memory.jsonl
memory/lessons_learned.md
memory/planning_patterns.md
memory/reporting_preferences.md
memory/recurring_risks.md
memory/stakeholder_preferences.md
memory/false_alarm_notes.md
memory/retrieval_hints.jsonl
```
Memory grows only through HUMAN-confirmed learning candidates (see MEMORY_AND_LEARNING_RULES.md).

## 6. Workspace initialization
```text
workspace/
  active_runs/
  completed_runs/
  step_outputs/
  handoff_artifacts/
training/
  feedback_log.jsonl
  candidate_queue.jsonl
  periodic_review_log.md
```

## 7. Tool bindings
This blueprint ships NO default tools. The instance `tools/tool_bindings.yaml` starts empty; tool
activation is HUMAN-gated and is not required for PM (planning/advisory) operation.

## 8. First run recommendation
Recommended first run — create a project status baseline: known tasks, milestones, current risks,
current blockers, open questions, reporting-format preference. Output: `project_pm_baseline.md`
(a proposal/baseline draft; HUMAN reviews).
