# Clone Memory Review — checklist (AP-CR-28 / FR-AI-11)

After `/aiws-agent-clone`, the carried-over confirmed memory is flagged `clone_review: pending` (+ `cloned_from`).
The HUMAN keeps or prunes each entry **for the NEW project** via `/aiws-agent-review-learning` — nothing is silently
dropped or auto-confirmed. Run `py tooling/run_agent.py memory <new_id> --full` to see the flagged entries.

## Per-entry decision (for each `clone_review: pending`)
- [ ] **Keep** — still true/useful for the new project → clear the `clone_review` flag (entry stays confirmed).
- [ ] **Prune** — source-project-specific / no longer applies → remove the entry.
- [ ] **Re-scope** — keep but adjust `applies_when` / `scope_tags` for the new project's context.

## Guardrails
- Decide per entry by relevance to the **new** project — do not bulk-keep blindly (the value of a clone is a *curated* baseline, not a verbatim copy).
- `confirmed_by` stays `HUMAN`; no auto-confirm. Lineage (`cloned_from`) is retained for kept entries.
- Pruning here does not touch the source instance (clone is independent).
