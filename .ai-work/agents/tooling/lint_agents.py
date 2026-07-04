#!/usr/bin/env python3
"""lint_agents.py — AI Agents Pack staging lint.

Two layers:
  * Governance-invariant floor (AP-CR-31, Detailed Design §6D) — ADVISORY (warn, exit 0 per OP-148-03):
    WARN when an instance's OWN `process/` dropped or weakened a `governance_invariant` step that its
    base process (`.blueprint_snapshot/process/` or the blueprint's resolved `process_docs`) carries.
  * Broad structural checks (AP-CR-40, ports DDR-30) — STRUCTURAL DEFECTS are ERRORS (exit 1):
    YAML tab-indentation + run_state quote-safety (F-04), JSONL parse, blueprint structure, instance
    structure, blueprint-ref resolves to an existing blueprint, instance memory/ matches the blueprint
    `memory_profile` (F-05 / AP-CR-36), run-folder completeness (advisory), no placeholder learning
    candidate in a completed run (F-09), and no Post-MVP folder (e.g. shared_workspaces) in the MVP tree.

Severity: structural defects -> ERRORS (return 1). The GI floor + soft gaps (missing profile, run-folder
gaps) stay warnings (return 0 if warn-only) so the advisory contract of AP-CR-31/OP-148-03 is preserved.

Stdlib-only (no-pip; regex/structural YAML, `json` for JSONL). Read-only — never mutates the corpus.
Canonical `/lint-all` integration is deferred to promotion.

Usage:  py tooling/lint_agents.py   (run from the pack root)
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]          # the pack root (dev: development/ai_agents/ · installed: .ai-work/agents/ (single-track))
INSTANCES = ROOT / "agents" / "instances"
BLUEPRINTS = ROOT / "agents" / "blueprints"

# A governance-invariant marker is exactly:  **governance_invariant** `<id>`
# (the bold form — so the explanatory legend prose, which writes the word inside backticks, never matches).
GI_RE = re.compile(r"\*\*governance_invariant\*\*\s+`([a-z_]+)`")

# run_state free-text keys whose values must be quote-safe (AP-CR-35 / F-04).
_FREE_TEXT_KEYS = ("notes", "stopped_reason")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _gi_ids(text: str) -> "set":
    return set(GI_RE.findall(text))


def _yaml_list(text: str, key: str) -> "list":
    """Read a simple 'key:\n  - item\n  - item' block (stdlib; no YAML lib). Returns the item strings."""
    m = re.search(rf"(?ms)^[ \t]*{re.escape(key)}:[ \t]*\n(.*?)(?=^\S|\Z)", text)
    if not m:
        return []
    return [x.strip().strip('"').strip("'") for x in re.findall(r"(?m)^[ \t]*-[ \t]*(\S.*?)[ \t]*$", m.group(1))]


def _blueprint_id_of(inst_dir: Path) -> str:
    m = re.search(r"(?m)^\s*blueprint_id:\s*(\S+)", _read(inst_dir / "blueprint_ref.yaml"))
    return m.group(1).strip().strip('"').strip("'") if m else ""


def _resolve_blueprint_process(inst_dir: Path) -> "dict":
    """Fallback when no snapshot: resolve the current blueprint's process_docs set for the instance."""
    ref = _read(inst_dir / "blueprint_ref.yaml")
    bp = None
    mp = re.search(r"(?m)^\s*blueprint_path:\s*(\S+)", ref)
    if mp:
        val = mp.group(1).strip().strip('"').strip("'")
        cand = (inst_dir / val).resolve() if ("/" in val or "\\" in val or val.startswith(".")) else (BLUEPRINTS / val)
        if cand.is_dir():
            bp = cand
    if bp is None:
        mid = re.search(r"(?m)^\s*blueprint_id:\s*(\S+)", ref)
        if mid:
            cand = BLUEPRINTS / mid.group(1).strip().strip('"').strip("'")
            if cand.is_dir():
                bp = cand
    if bp is None:
        return {}
    files = {}
    mm = re.search(r"(?ms)^process_docs:\s*\n(.*?)(?=^\S|\Z)", _read(bp / "blueprint.yaml"))
    if mm:
        for rel in re.findall(r":\s*(\S+\.md)\s*$", mm.group(1), re.M):
            p = (bp / rel).resolve()
            if p.is_file():
                files[p.name] = _read(p)
    pdir = bp / "process"
    if pdir.is_dir():
        for c in sorted(pdir.iterdir()):
            if (c.is_file() and c.suffix == ".md"
                    and not c.name.lower().startswith("readme") and c.name not in files):
                files[c.name] = _read(c)
    return files


# --- AP-CR-40 broad structural checks --------------------------------------

def _check_yaml(errors: list) -> None:
    """YAML hygiene (stdlib, conservative — NO full parse): tab-indentation (YAML forbids tabs) +
    run_state free-text scalar quote-safety (the F-04 class)."""
    for p in sorted(set(BLUEPRINTS.rglob("*.yaml")) | set(INSTANCES.rglob("*.yaml"))):
        rel = p.relative_to(ROOT)
        txt = _read(p)
        for i, line in enumerate(txt.splitlines(), 1):
            lead = line[:len(line) - len(line.lstrip())]
            if "\t" in lead:
                errors.append(f"{rel}:{i} YAML tab indentation (YAML forbids tabs)")
        if p.name == "run_state.yaml":
            for i, line in enumerate(txt.splitlines(), 1):
                m = re.match(r"^(\w+):[ \t]+(.*)$", line)
                if m and m.group(1) in _FREE_TEXT_KEYS:
                    val = m.group(2).strip()
                    if val and val != "null" and not val.startswith(('"', "'")) and ": " in val:
                        errors.append(f"{rel}:{i} run_state `{m.group(1)}` unquoted scalar contains ': ' "
                                      f"— emit via _yq (AP-CR-35 / F-04)")


def _check_jsonl(errors: list) -> None:
    for p in sorted(INSTANCES.rglob("*.jsonl")):
        rel = p.relative_to(ROOT)
        for i, line in enumerate(_read(p).splitlines(), 1):
            if line.strip():
                try:
                    json.loads(line)
                except Exception as e:
                    errors.append(f"{rel}:{i} invalid JSONL: {str(e)[:60]}")


def _check_blueprints(errors: list) -> None:
    if not BLUEPRINTS.is_dir():
        return
    for b in sorted(p for p in BLUEPRINTS.iterdir() if p.is_dir() and p.name != "_shared"):
        for req in ("blueprint.yaml", "profile.md", "skills/skill_index.yaml"):
            if not (b / req).exists():
                errors.append(f"blueprints/{b.name}: missing required {req}")


def _check_instances(errors: list, warnings: list) -> None:
    if not INSTANCES.is_dir():
        return
    for i in sorted(p for p in INSTANCES.iterdir() if p.is_dir()):
        name = i.name
        if not (i / "instance.yaml").exists():
            errors.append(f"instances/{name}: missing instance.yaml")
        ref, snap = i / "blueprint_ref.yaml", i / "agent_design_snapshot.yaml"
        if not ref.exists() and not snap.exists():
            errors.append(f"instances/{name}: missing blueprint_ref.yaml AND agent_design_snapshot.yaml")
        bid = _blueprint_id_of(i) if ref.exists() else ""
        if bid and bid != "null" and not (BLUEPRINTS / bid).is_dir():
            errors.append(f"instances/{name}: blueprint_ref blueprint_id '{bid}' has no blueprints/{bid}/ dir")
        # memory/ matches the blueprint memory_profile (AP-CR-36 / F-05)
        mem = i / "memory"
        prof = []
        if bid and (BLUEPRINTS / bid / "blueprint.yaml").exists():
            prof = [Path(x).name for x in _yaml_list(_read(BLUEPRINTS / bid / "blueprint.yaml"), "required_files")]
        if prof and mem.is_dir():
            disk = {p.name for p in mem.glob("*") if p.is_file() and p.name != "candidate_queue.jsonl"}
            miss = set(prof) - disk
            if miss:
                errors.append(f"instances/{name}: memory/ missing memory_profile files {sorted(miss)} (AP-CR-36)")
        # placeholder learning-candidate row in a COMPLETED run (F-09)
        comp = i / "workspace" / "completed_runs"
        if comp.is_dir():
            for lc in comp.rglob("learning_candidates.jsonl"):
                for j, line in enumerate(_read(lc).splitlines(), 1):
                    # placeholder = the template's angle-bracket sentinels, NOT a real `LC-001` id
                    if line.strip() and ("<instance_id>" in line or "RUN-YYYYMMDD" in line or "<learning content" in line):
                        errors.append(f"{lc.relative_to(ROOT)}:{j} placeholder learning-candidate row in a completed run (F-09)")
        # run-folder completeness (advisory)
        for sub in ("active_runs", "completed_runs"):
            base = i / "workspace" / sub
            if base.is_dir():
                for d in sorted(base.iterdir()):
                    if d.is_dir() and d.name.startswith("RUN-") and not (d / "run_state.yaml").exists():
                        warnings.append(f"{d.relative_to(ROOT)}: run folder missing run_state.yaml")


def _check_post_mvp(errors: list) -> None:
    for bad in ("shared_workspaces",):
        for d in ROOT.rglob(bad):
            if d.is_dir():
                errors.append(f"{d.relative_to(ROOT)}: Post-MVP folder '{bad}' must not be present in the MVP tree")


def _check_gi_floor(warnings: list) -> int:
    """AP-CR-31 governance-invariant floor — ADVISORY (warnings only)."""
    checked = 0
    if not INSTANCES.is_dir():
        return 0
    for inst_dir in sorted(p for p in INSTANCES.iterdir() if p.is_dir()):
        proc = inst_dir / "process"
        inst_md = {p.name: _read(p) for p in proc.glob("*.md")} if proc.is_dir() else {}
        if not inst_md:
            continue  # pre-fork / no instance process — nothing to compare
        snap = inst_dir / ".blueprint_snapshot" / "process"
        if snap.is_dir():
            base = {p.name: _read(p) for p in snap.glob("*.md")}
            base_src = ".blueprint_snapshot/process"
        else:
            base = _resolve_blueprint_process(inst_dir)
            base_src = "blueprint process_docs"
        if not base:
            continue  # custom no-Blueprint (no base) — floor comparison N/A
        checked += 1
        for fname, btext in base.items():
            bids = _gi_ids(btext)
            if not bids:
                continue
            if fname not in inst_md:
                warnings.append(f"{inst_dir.name}: process/{fname} MISSING — base ({base_src}) carries "
                                f"governance_invariant {sorted(bids)}")
                continue
            dropped = bids - _gi_ids(inst_md[fname])
            if dropped:
                warnings.append(f"{inst_dir.name}: process/{fname} dropped/weakened governance_invariant "
                                f"{sorted(dropped)} (base {base_src})")
    return checked


def main() -> int:
    errors, warnings = [], []
    if not INSTANCES.is_dir():
        print("lint_agents: no instances dir — nothing to check")
        return 0
    # AP-CR-40 broad structural checks (errors fail the gate)
    _check_yaml(errors)
    _check_jsonl(errors)
    _check_blueprints(errors)
    _check_instances(errors, warnings)
    _check_post_mvp(errors)
    # AP-CR-31 governance-invariant floor (advisory)
    gi_checked = _check_gi_floor(warnings)
    for e in errors:
        print(f"  [error] {e}")
    for w in warnings:
        print(f"  [warning] {w}")
    print(f"lint_agents: broad structural checks + governance-invariant floor "
          f"(GI checked {gi_checked} forked instance(s)) — errors={len(errors)} warnings={len(warnings)} "
          f"(GI floor + soft gaps advisory per AP-CR-31/OP-148-03; structural defects fail the gate per AP-CR-40)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
