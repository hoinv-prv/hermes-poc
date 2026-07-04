# skills/

Place execution-support skill docs here.

Skills are not AIP and not Playbooks.
They support micro-execution of a step.

## Relationship with `product/skills/`

Files here are **brief canonical descriptions** — purpose, inputs/outputs, flow summary, core rules.
They serve as the authoritative reference for what each skill is supposed to do.

The installable full SKILL.md files live in `product/skills/` and may contain additional
practical steps (e.g., lint, gap report, orient phase) beyond what is described here.

**Precedence rule:** If a flow step defined here is absent from `product/skills/`, that is a gap
to fix in `product/skills/`. Extra steps in `product/skills/` that are not here are acceptable
as practical additions, provided they do not contradict the canonical description.
