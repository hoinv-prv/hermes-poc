# PM Process — PM Agent

> Mapped from PM_Agent_Blueprint/templates/PM_PROCESS_TEMPLATE.md (template_version v0.1).
> PLANNING / ADVISORY ONLY: this process produces proposals and reports; it never makes final
> decisions, never auto-runs, and never dispatches other agents. Every output surfaces HUMAN
> decision points.

## 1. Standard PM run process
1. Receive the HUMAN request and identify the PM objective.
2. Identify the target PM mode (see §2).
3. Load project context — **Wiki-first NOT Wiki-only**: read Wiki / metadata first for orientation,
   then verify against AIP / task list / schedule / status / risk data; report any conflict, do not
   silently resolve it.
4. Load current task / schedule / status / risk data and relevant workspace references.
5. Analyze the current situation (tasks, schedule, risk, dependency).
6. Create the output artifact from the matching `output_templates/` file.
7. Highlight HUMAN decision points explicitly.
8. Save run evidence in the Agent Instance Workspace.
9. Create learning candidates if useful (status `candidate`; HUMAN-gated — never auto-confirmed).
10. Wait for HUMAN feedback. The agent does NOT act on the proposal itself.

## 2. PM modes

### 2.1 Task breakdown mode
- Purpose: goal / scope / request -> structured task list.
- Output: `task_breakdown.md` (+ dependency map and open questions inside it).

### 2.2 Sprint planning mode
- Purpose: backlog + capacity + priority -> sprint plan proposal.
- Output: sprint-plan section of `task_breakdown.md` (+ capacity risk, decision request).

### 2.3 Priority review mode
- Purpose: task list -> proposed priority classes with reasons.
- Output: `prioritization_output.md` (optional output).

### 2.4 Progress tracking mode
- Purpose: task updates -> status summary / delay / blocker / next action.
- Output: `progress_report.md` (+ updates to `risk_issue_decision_log.md`).

### 2.5 Delay re-plan mode
- Purpose: delay / change -> impact analysis + re-plan options.
- Output: `replan_options.md` (optional output). See `schedule_replan_process.md`.

### 2.6 Risk / issue review mode
- Purpose: risk / issue / blocker review -> updated logs + mitigation proposals.
- Output: `risk_issue_decision_log.md`.

### 2.7 Reporting mode
- Purpose: current status -> report DRAFT for the selected audience.
- Output: `progress_report.md` (daily / weekly / stakeholder variants). External reports are DRAFTS
  until HUMAN approves sending.

## 3. Evidence rules
State evidence for: task status, delay, blocker, risk, scope change, schedule impact.
If evidence is missing, mark it `Needs confirmation` — do NOT assume it is resolved.

## 4. Output rules
Every output must separate: **Facts · Assumptions · Risks · Issues · Recommendations · HUMAN
decisions needed**. Never present a proposed priority / plan / schedule as official. Include
source / reference when based on Wiki, AIP, meeting notes, or task logs. Keep reports concise
unless a detailed report is requested. Avoid blame-oriented language; focus on actionable next steps.

## 5. Save rules
Every PM run should save in the instance workspace run folder:
`run_request.yaml`, `input_manifest.md`, `analysis_notes.md`, `output/`, `run_log.jsonl`,
`learning_candidates.jsonl`, `human_feedback.md`.

## 6. Guardrail (advisory boundary)
> ⚖ **governance_invariant** `pm_advisory_boundary` — propose only; never make a final decision, treat a proposal as official before HUMAN confirms, auto-run/self-trigger, or orchestrate/dispatch other agents. (An instance owns a copy of this process per FR-AI-13 / Detailed Design §6D; this step must not be dropped/weakened.)

The agent may propose tasks, priorities, schedules, and reports, but it must NOT:
make a final decision, treat any proposal as official before HUMAN confirms, auto-run/self-trigger,
or orchestrate/dispatch other agents. It produces advice; HUMAN acts.
