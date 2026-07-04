#!/usr/bin/env python3
"""Agent Runtime orchestrator (AI Agents Pack, staging) — thin wrapper.

Prepares state so the AI can ACT AS an agent instance for one task:
materialize an Active Run Context (ARC), scaffold a run-folder (Phase C schema
+ additive run_state.yaml), track status, list/show runs, stop runs.

It does NOT call an LLM, does NOT act as the agent, does NOT auto-run/chain,
and NEVER writes confirmed_memory or anything outside the pack root.
Mirrors the thin-orchestrator shape of .ai-work/tooling/run_aip.py.

Subcommands (AP-CR-19 surface B; +AP-CR-22 list/memory; +AP-CR-25 --aip; +AP-CR-27 upgrade; +AP-CR-28 clone; +AP-CR-30 rename; +AP-CR-41 template conformance):
  start  <instance> [--task TEXT] [--slug SLUG] [--aip AIP-ID] [--strict-template]   create run + ARC (status=active)
  resume <instance> <run_id>                      refresh ARC + show run_state
  status <instance> [run_id]                      show one run, or list runs (reconciles closed)
  stop   <instance> <run_id> [--reason TEXT]      mark stopped + move to completed_runs
  list                                            list instances (id · blueprint · display_name · status · drift)
  memory <instance> [--full]                      show an instance's confirmed memory (+ lessons/candidate counts)
  upgrade <instance> [--reconcile --to-version V --decisions "..."]   present blueprint drift; record HUMAN reconcile (AP-CR-27)
  clone  <source> --as "<display_name>" [--id NEWID] [--why "..."]    new instance from an existing one (AP-CR-28)
  rename <source> --to NEWID [--name "N"] [--as "D"] [--why "..."]    rename instance id (+folder) + previous_ids alias (AP-CR-30)

Instance args accept a FUZZY token (partial id / role word / display_name / a prior id via `previous_ids` after a
rename) — a unique match is required (AP-CR-22/23/30). Instances declaring `policies.run_policy.aip_driven: true`
require `start --aip <id>` (AP-CR-25).

Run with `py run_agent.py ...` (bare `python` is broken on this machine).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

# UTF-8 stdout (cp932-safe), like AIWS tooling.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

# DEV_ROOT = the pack root  (this script lives in <pack_root>/tooling/, so parent.parent = the pack root;
#   resolves to development/ai_agents/ in dev, .ai-work/agents/ when installed (single-track))
DEV_ROOT = Path(__file__).resolve().parent.parent
INSTANCES = DEV_ROOT / "agents" / "instances"
BLUEPRINTS = DEV_ROOT / "agents" / "blueprints"
RUN_TEMPLATES = DEV_ROOT / "agents" / "templates" / "run"

# CR-AIWS-2026-06-057 — project root (DEV_ROOT = development/ai_agents/ or .ai-work/agents/;
#   parent.parent = the project root that holds .ai-work/). Used to resolve an AIP's Task Workspace.
_PROJECT_ROOT = DEV_ROOT.parent.parent

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,79}$")

# CR-AIWS-2026-06-057 — roots allowed for writes IN ADDITION to the pack root. An aip_driven run that
# reuses its driving AIP's Task Workspace allow-lists that TW here so the boundary guard permits writes
# into it (the TW lives under <project>/.ai-work/workspaces/, outside the pack root).
_EXTRA_ALLOWED_ROOTS: "list[Path]" = []


def _allow_root(p: Path) -> None:
    """CR-AIWS-2026-06-057 — register an additional root the boundary guard will permit writes into
    (e.g. an AIP Task Workspace). Idempotent-ish; resolves before storing."""
    r = p.resolve()
    if r not in _EXTRA_ALLOWED_ROOTS:
        _EXTRA_ALLOWED_ROOTS.append(r)


# --- boundary guard (refuse writes outside the pack root) --------------------
def _ensure_inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(DEV_ROOT.resolve())
        return resolved
    except ValueError:
        pass
    # CR-AIWS-2026-06-057 — also allow paths inside any explicitly registered extra root.
    for root in _EXTRA_ALLOWED_ROOTS:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise SystemExit(
        f"error: {label} path escapes the pack-root boundary\n"
        f"  path: {resolved}\n  must be inside: {DEV_ROOT.resolve()}"
        + (f"\n  or one of: {', '.join(str(r) for r in _EXTRA_ALLOWED_ROOTS)}" if _EXTRA_ALLOWED_ROOTS else "")
    )


def _die(msg: str) -> "None":
    raise SystemExit(f"error: {msg}")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _write(p: Path, text: str) -> None:
    _ensure_inside(p, "write")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _now_id() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M")


def _today() -> str:
    return datetime.date.today().isoformat()


def _slug(text: str) -> str:
    s = _SLUG_RE.sub("-", (text or "run").lower()).strip("-")
    return (s[:32] or "run")


def _all_instances() -> "list[Path]":
    if not INSTANCES.is_dir():
        return []
    return [d for d in sorted(INSTANCES.iterdir())
            if d.is_dir() and (d / "instance.yaml").exists()]


def _instance_field(inst_dir: Path, key: str) -> str:
    return _yaml_get(_read(inst_dir / "instance.yaml"), key)


def _instance_display(inst_dir: Path) -> str:
    # AP-CR-23: person-name display_name is the HUMAN-facing label; fall back to the long
    # instance_name, then the id. instance_id stays the stable machine key.
    return (_instance_field(inst_dir, "display_name")
            or _instance_field(inst_dir, "instance_name")
            or inst_dir.name)


def _previous_ids_from_text(txt: str) -> "list[str]":
    """AP-CR-30 — parse instance.yaml `previous_ids` (rename aliases). Handles the inline-flow form the
    tool writes (`previous_ids: [a, b]`) and a defensive block form (`previous_ids:\\n  - a`). Stdlib-only."""
    m = re.search(r"(?m)^previous_ids:[ \t]*\[([^\]]*)\][ \t]*$", txt)
    if m:
        return [s.strip().strip('"').strip("'") for s in m.group(1).split(",") if s.strip()]
    m = re.search(r"(?m)^previous_ids:[ \t]*$\n((?:[ \t]+-[ \t]*\S.*\n?)+)", txt)
    if m:
        return [re.sub(r"^[ \t]+-[ \t]*", "", ln).strip().strip('"').strip("'")
                for ln in m.group(1).splitlines() if ln.strip()]
    return []


def _instance_previous_ids(inst_dir: Path) -> "list[str]":
    """AP-CR-30 — the instance's prior ids (alias). [] when never renamed."""
    return _previous_ids_from_text(_read(inst_dir / "instance.yaml"))


def _resolve_instance(token: str) -> str:
    """AP-CR-22/23/30 — resolve a fuzzy token (exact id, partial id, role word, display_name, or a prior
    id recorded in `previous_ids` after a rename) to a UNIQUE instance id, so HUMAN need not type the full
    compound id and old references still resolve. Ambiguous/none → _die."""
    token = (token or "").strip()
    if (INSTANCES / token).is_dir():
        return token
    t = token.lower()
    hits = []
    for d in _all_instances():
        disp = _instance_display(d).lower()
        prev = [p.lower() for p in _instance_previous_ids(d)]  # AP-CR-30: exact-match a renamed instance's old id
        if t in d.name.lower() or t == disp or t in disp or t in prev:
            hits.append(d.name)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        _die(f"no instance matches '{token}'. Try `list`.")
    _die(f"ambiguous instance '{token}' → {', '.join(hits)}. Use the full id.")


def _instance_dir(instance: str) -> Path:
    resolved = _resolve_instance(instance)
    if not _ID_RE.match(resolved):
        _die(f"invalid instance id '{resolved}'")
    d = INSTANCES / resolved
    if not d.is_dir():
        _die(f"instance not found: {d}")
    return d


def _instance_run_policy(inst_dir: Path) -> dict:
    """AP-CR-25 — indentation-tolerant read of nested policies.run_policy.{aip_driven,aip_template}
    (_yaml_get is flat/top-level only). Returns {} when not declared."""
    txt = _read(inst_dir / "instance.yaml")
    out: dict = {}
    for key in ("aip_driven", "aip_template"):
        m = re.search(rf"(?m)^[ \t]+{key}:[ \t]*([^#\n]*?)[ \t]*(?:#.*)?$", txt)
        if m:
            out[key] = m.group(1).strip().strip('"').strip("'")
    return out


# --- AP-CR-26: relevance-scoped confirmed-memory loading --------------------
def _tok(text: str) -> set:
    # len>=2: drop single chars (e.g. the "f" in "F-02"/"F-05") that would spuriously overlap.
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 2}


def _mem_entries(inst_dir: Path) -> "list[dict]":
    out: list[dict] = []
    for line in _read(inst_dir / "memory" / "confirmed_memory.jsonl").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"_raw": line})  # malformed → keep + treat as always-load (never hide)
    return out


def _mem_relevant(entry: dict, task: str) -> bool:
    """AP-CR-26 — load an entry in full if: malformed/legacy-untagged (never hide), `always`-tagged,
    or its scope_tags/applies_when overlap the task (token overlap OR separator-stripped substring,
    so `function:f02` matches "F-02"). Default = load (index-all + AI judgment is the safety net)."""
    if "_raw" in entry:
        return True
    tags = entry.get("scope_tags") or []
    cond = entry.get("applies_when") or ""
    if not tags and not cond:
        return True  # legacy untagged = always-load (backward-compat)
    if any(str(t).lower() == "always" for t in tags):
        return True
    task_tokens = _tok(task)
    if task_tokens & _tok(" ".join(str(t) for t in tags) + " " + cond):
        return True
    task_compact = re.sub(r"[^a-z0-9]+", "", (task or "").lower())
    for t in tags:
        for seg in re.split(r"[^a-z0-9]+", str(t).lower()):
            if len(seg) >= 2 and seg in task_compact:
                return True
    return False


def _yaml_get(text: str, key: str) -> str:
    """Minimal flat 'key: value' reader (stdlib; no YAML lib). Top-level only.
    Strips an inline ' # comment' so 'status: active   # ...' returns 'active'."""
    m = re.search(rf"(?m)^{re.escape(key)}:[ \t]*([^#\n]*?)[ \t]*(?:#.*)?$", text)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def _yq(value: str) -> str:
    """Emit a YAML-safe scalar for run_state free-text fields (AP-CR-35; stdlib, no YAML lib).
    The literal "null" sentinel stays a bareword (so `stopped_reason: null` keeps its YAML-null
    semantics); any other value becomes a double-quoted scalar with backslash + double-quote
    escaped, so values containing ':', '-', etc. emit as VALID YAML. The reader `_yaml_get`
    strips the outer quotes, so quoted values round-trip."""
    if value == "null":
        return "null"
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _blueprint_dir(inst_dir: Path) -> "Path | None":
    ref = _read(inst_dir / "blueprint_ref.yaml")
    bid = _yaml_get(ref, "blueprint_id")
    if not bid or bid == "null":
        return None
    bp = BLUEPRINTS / bid
    return bp if bp.is_dir() else None


def _yaml_list(text: str, key: str) -> "list":
    """Read a simple 'key:\n  - item\n  - item' block (stdlib; no YAML lib). Returns the item strings."""
    m = re.search(rf"(?ms)^[ \t]*{re.escape(key)}:[ \t]*\n(.*?)(?=^\S|\Z)", text)
    if not m:
        return []
    return [x.strip().strip('"').strip("'") for x in re.findall(r"(?m)^[ \t]*-[ \t]*(\S.*?)[ \t]*$", m.group(1))]


def _memory_profile_files(inst_dir: Path) -> "list":
    """AP-CR-36 — basenames in the instance's blueprint memory_profile.required_files; [] if no blueprint/profile."""
    bp = _blueprint_dir(inst_dir)
    if bp is None:
        return []
    return [Path(x).name for x in _yaml_list(_read(bp / "blueprint.yaml"), "required_files")]


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(DEV_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p)


# --- CR-AIWS-2026-06-057: AIP Task Workspace resolution + instance-local back-pointer ----
def _resolve_task_workspace(aip: str) -> "Path | None":
    """CR-AIWS-2026-06-057 — resolve the driving AIP's Task Workspace dir via its `runtime_workspace`
    front-matter. Uniquely resolve the AIP file (via _resolve_aip_path); read `runtime_workspace`;
    substitute a leading `__PROJECT_ROOT__` token with the real project root; return the Path if it
    `.is_dir()`, else None. None on any miss/ambiguity (caller falls back to the in-instance scaffold)."""
    path, n = _resolve_aip_path(aip)
    if path is None or n != 1:
        return None
    rw = _yaml_get(_read(path), "runtime_workspace")
    if not rw:
        return None
    rw = rw.replace("\\", "/")
    if rw.startswith("__PROJECT_ROOT__"):
        rw = str(_PROJECT_ROOT).replace("\\", "/") + rw[len("__PROJECT_ROOT__"):]
    tw = Path(rw)
    return tw if tw.is_dir() else None


def _run_index_path(inst_dir: Path) -> Path:
    return inst_dir / "run_index.jsonl"


def _read_run_index(inst_dir: Path) -> "list[dict]":
    """CR-AIWS-2026-06-057 — read the instance-local run_index.jsonl back-pointer (tolerant of
    missing file / malformed lines). Each entry maps a run_id to its (project-relative) Task Workspace."""
    out: list[dict] = []
    for line in _read(_run_index_path(inst_dir)).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            if isinstance(d, dict):
                out.append(d)
        except Exception:
            continue  # malformed → skip (best-effort back-pointer)
    return out


def _upsert_run_index(inst_dir: Path, run_id: str, task_workspace_rel: str,
                      related_aip: str, status: str) -> None:
    """CR-AIWS-2026-06-057 — append or update the run_index.jsonl line for run_id. `task_workspace_rel`
    is a project-root-relative POSIX path. Boundary-guarded write (run_index lives inside the pack root)."""
    rows = _read_run_index(inst_dir)
    found = False
    for r in rows:
        if r.get("run_id") == run_id:
            r["task_workspace"] = task_workspace_rel
            r["related_aip"] = related_aip
            r["status"] = status
            found = True
            break
    if not found:
        rows.append({
            "run_id": run_id,
            "task_workspace": task_workspace_rel,
            "related_aip": related_aip,
            "status": status,
            "created_at": _today(),
        })
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    _write(_run_index_path(inst_dir), body)


def _tw_rel(tw: Path) -> str:
    """Project-root-relative POSIX path for a Task Workspace (for run_index storage)."""
    try:
        return str(tw.resolve().relative_to(_PROJECT_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(tw.resolve()).replace("\\", "/")


# --- run_state.yaml (additive; status source of truth) ----------------------
def _run_state_path(run_dir: Path) -> Path:
    return run_dir / "run_state.yaml"


def _read_status(run_dir: Path) -> str:
    txt = _read(_run_state_path(run_dir))
    if not txt:
        return "completed"  # backward-compat: pre-run_state runs = completed (R-6)
    return _yaml_get(txt, "status") or "active"


def _write_run_state(run_dir: Path, run_id: str, instance: str, status: str,
                     task: str, stopped_reason: str = "null") -> None:
    body = (
        f"# run_state.yaml — runtime state of one agent run (additive to Phase C run-record)\n"
        f"run_id: {run_id}\n"
        f"agent_instance_id: {instance}\n"
        f"status: {status}            # active | incomplete | completed | stopped\n"
        f"created_at: \"{_today()}\"\n"
        f"updated_at: \"{_today()}\"\n"
        f"stopped_reason: {_yq(stopped_reason)}\n"
        f"progress:                 # AI ticks these as it works; resume reads this\n"
        f"  - step: read ARC + task request\n"
        f"    done: false\n"
        f"  - step: produce output per blueprint output_templates\n"
        f"    done: false\n"
        f"  - step: capture >=1 learning candidate\n"
        f"    done: false\n"
        f"notes: {_yq(task[:120] if task else '<current-state note for HUMAN>')}\n"
    )
    _write(_run_state_path(run_dir), body)


def _set_status(run_dir: Path, status: str, reason: str = "null") -> None:
    p = _run_state_path(run_dir)
    txt = _read(p)
    if not txt:
        _die(f"run_state.yaml missing in {run_dir}")
    txt = re.sub(r"(?m)^status:.*$", f"status: {status}", txt)
    txt = re.sub(r"(?m)^updated_at:.*$", f'updated_at: "{_today()}"', txt)
    if reason != "null":
        txt = re.sub(r"(?m)^stopped_reason:.*$", f"stopped_reason: {_yq(reason)}", txt)
    _write(p, txt)


# --- ARC materialization ----------------------------------------------------
def _materialize_arc(run_dir: Path, instance: str, inst_dir: Path, run_id: str,
                     task: str, aip: str = "", task_workspace: "Path | None" = None) -> Path:
    bp = _blueprint_dir(inst_dir)
    bp_line = _rel(bp) if bp else "(custom / no blueprint — see agent_design_snapshot.yaml)"

    # AP-CR-31: the agent follows its OWN process when forked; else the blueprint's (pre-fork fallback).
    inst_proc = inst_dir / "process"
    if inst_proc.is_dir() and any(inst_proc.glob("*.md")):
        proc_ptr = f"`{_rel(inst_proc)}` — instance-OWNED (AP-CR-31); improve ONLY via process_improvement_candidate (HUMAN-gated)"
    elif bp:
        proc_ptr = f"`{_rel(bp / 'process')}` — blueprint process (this instance has not forked its own process yet)"
    else:
        proc_ptr = "author/maintain your own `process/` (custom no-blueprint)"

    # AP-CR-26: relevance-scoped confirmed memory — load always-on + task-relevant in FULL; index ALL.
    entries = _mem_entries(inst_dir)

    def _mem_line(e: dict) -> str:
        return e["_raw"] if "_raw" in e else json.dumps(e, ensure_ascii=False)

    def _mem_idx(e: dict) -> str:
        if "_raw" in e:
            return f"- (raw) {e['_raw'][:80]}"
        eid = e.get("id") or e.get("cm_id") or "?"
        typ = e.get("type") or e.get("kind") or "memory"
        tags = ", ".join(str(t) for t in (e.get("scope_tags") or [])) or "-"
        cond = (e.get("applies_when") or "").strip()
        return f"- [{eid}] {typ} · tags: {tags}" + (f" · when: {cond}" if cond else "")

    loaded = [e for e in entries if _mem_relevant(e, task)]
    cm_path = _rel(inst_dir / "memory" / "confirmed_memory.jsonl")
    if entries:
        loaded_block = "\n".join(_mem_line(e) for e in loaded) if loaded else "(none task-relevant — see §5.2 index)"
        index_block = "\n".join(_mem_idx(e) for e in entries)
        mem_note = f"Loaded {len(loaded)} of {len(entries)} — open `{cm_path}` for any you judge relevant"
    else:
        loaded_block = "(empty — no confirmed memory yet)"
        index_block = "(none yet)"
        mem_note = "Loaded 0 of 0"

    # AP-CR-25 + AP-CR-41: run-policy + template-conformance on the AI's read surface (ARC §8).
    pol = _instance_run_policy(inst_dir)
    if pol.get("aip_driven", "").lower() in ("true", "yes"):
        _exp = (pol.get("aip_template") or "").strip()
        if _exp and (aip or "").strip():
            _p, _n = _resolve_aip_path(aip)
            if _n > 1:
                _conf = f"AMBIGUOUS (--aip matches {_n} files)"
            elif _p is None:
                _conf = "unverified (could not resolve --aip)"
            else:
                _act = _aip_template_source(_p)
                if not _act:
                    _conf = "unverified (no template_source stamp)"
                elif _norm_template(_act) == _norm_template(_exp):
                    _conf = f"OK (expected={_norm_template(_exp)} actual={_norm_template(_act)})"
                else:
                    _conf = f"MISMATCH (expected={_norm_template(_exp)} actual={_norm_template(_act)})"
        else:
            _conf = "(n/a — no aip_template or no driving AIP)"
        pol_block = (
            "- **aip_driven: true** — this agent runs ONLY under a driving AIP (`/create-aip` → `/run-aip`).\n"
            f"- driving AIP: {aip or '(none — the run should have been refused)'}\n"
            f"- aip_template: {pol.get('aip_template') or '(none)'}\n"
            f"- template_conformance: {_conf}\n"
            "- This run is ONE step of that AIP; record findings as AIP step evidence."
        )
    else:
        pol_block = "- aip_driven: false / unset — no AIP gate; standard single-shot run."

    # CR-AIWS-2026-06-057 — when this run REUSES the driving AIP's Task Workspace, the run-folder IS that
    # TW (not an in-instance RUN folder). Reflect that in §1 and route captures to the project capture
    # channel (08_capture_inbox.jsonl per CR-042 C1), NOT a run-local learning_candidates.jsonl.
    if task_workspace is not None:
        tw_note = (f"\n- **task workspace (CR-AIWS-2026-06-057):** this run REUSES the driving AIP's Task "
                   f"Workspace at `{_rel(task_workspace)}` — outputs/state materialize THERE, not in a "
                   f"separate in-instance run-folder. The instance keeps a `run_index.jsonl` back-pointer.")
        capture_line = ("- Capture >=1 learning candidate to THIS Task Workspace's `08_capture_inbox.jsonl` "
                        "(the single project capture channel; applied CR-042 C1) — no auto-confirm.")
    else:
        tw_note = ""
        capture_line = ("- Capture >=1 learning candidate (status=candidate) to `learning_candidates.jsonl` "
                        "(no auto-confirm).")

    arc = f"""---
artifact_type: active_run_context
run_id: {run_id}
agent_instance_id: {instance}
status: active
created_at: "{_today()}"
---

# Active Run Context (ARC) — {instance}

> Read surface for the AI to **act as this agent** for one task. Materialized by `run_agent.py`.
> The tool prepared this; the AI does the task. No auto-run, no auto-promotion, HUMAN-gated.

## 1. Run identity
- run_id: {run_id}
- instance: {instance}  ·  status: active (see `run_state.yaml`){tw_note}

## 2. Task request (from HUMAN)
{task if task else "(no --task provided — HUMAN states the task in-session)"}

## 3. Agent definition
- blueprint: {bp_line}
  - `blueprint.yaml` (mission · responsibilities · **non_responsibilities** · input/output_contract · memory_policy · human_gate_policy)
  - `skills/skill_index.yaml` · `profile.md` · `output_templates/` · `checklists/`
- **process (AP-CR-31):** follow {proc_ptr}
- **Honor `non_responsibilities`**: this agent reviews/advises/plans only — it does NOT approve, edit, auto-update Wiki/memory, or run other agents.

## 4. Context (read from instance `context/`)
- `{_rel(inst_dir / 'context' / 'wiki_references.yaml')}` — Wiki/index entries (Wiki-first, NOT Wiki-only) + `lookup_intents` (process intent -> index/source binding; resolve via `.ai-work/tooling/lookup_wiki_source.py`, pointers first)
- `{_rel(inst_dir / 'context' / 'source_references.yaml')}` — source areas to verify against
- `{_rel(inst_dir / 'context' / 'source_priority.yaml')}` — which area to weigh first
- `{_rel(inst_dir / 'context' / 'working_inventory.yaml')}` — non-wiki / not-yet-indexed files (instance-owned)
- `{_rel(inst_dir / 'context' / 'ignored_paths.yaml')}` — exclusions

## 4A. Reference resolution & run rationale (AI fills as it works — CR-AIWS-AGENT-FRAMEWORK-002 D7)
> The tool prepared this scaffold; YOU (the agent) fill it as you select context and execute.
> Purpose: bounded context (no overflow), a traceable record of WHY each reference was used or excluded, and an audit trail.
> Resolve `wiki_references.yaml::lookup_intents` via `.ai-work/tooling/lookup_wiki_source.py` (pointers first; load full only when needed; pass `--system <id>` when multi_system; default scope `project,aiws` — `local`/raw search are authorization-gated, CR-AIWS-2026-06-052).

### Process Interpretation
(how you read the instance process for THIS task; which `lookup_intents` apply; what you will and will not do)

### Selected References
| Intent | Selected source (id/path) | Reason | Load mode (pointer/full) |
|---|---|---|---|
| (fill) | | | |

### Excluded References
| Candidate | Reason excluded |
|---|---|
| (fill) | |

### Reference Gaps
- (intents/needs with no resolvable source — apply the intent `fallback`: report_reference_gap / ask_human_if_required / continue_with_limitation)

### Assumptions
- (assumptions made for this run)

### Limitations
- (what this run did NOT cover; confidence caveats)

## 5. Confirmed memory (HUMAN-approved; relevance-scoped — AP-CR-26)

### 5.1 Loaded (always-on + task-relevant; load confirmed-only)
```jsonl
{loaded_block}
```

### 5.2 Index — ALL confirmed memory ({mem_note})
{index_block}

- also: `{_rel(inst_dir / 'memory' / 'lessons_learned.md')}` · `{_rel(inst_dir / 'memory' / 'local_guidelines.md')}`

## 6. Output contract
- Write outputs to `output/` in this run-folder (use the blueprint's `output_templates/`).
{capture_line}
- Update `run_state.yaml` `progress` as you work; set `status: completed` when done (or leave `incomplete` if you stop).

## 7. Guardrails
- Wiki-first NOT Wiki-only · no auto-promotion (output=evidence, learning=candidate) · HUMAN-gated · honor non_responsibilities.

## 8. Run policy (AP-CR-25)
{pol_block}
"""
    p = run_dir / "00_active_run_context.md"
    _write(p, arc)
    return p


def _scaffold_run(inst_dir: Path, run_id: str) -> Path:
    run_dir = inst_dir / "workspace" / "active_runs" / run_id
    _ensure_inside(run_dir, "run-folder")
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    # copy Phase C run templates if present
    if RUN_TEMPLATES.is_dir():
        for f in sorted(RUN_TEMPLATES.glob("*")):
            if f.is_file() and f.name != "README.md" and ".example." not in f.name:  # skip docs + *.example.* (AP-CR-39)
                dst = run_dir / f.name
                if not dst.exists():
                    shutil.copyfile(f, dst)
    # ensure the core evidence files exist even if templates missing
    for name in ("run_log.jsonl", "learning_candidates.jsonl", "human_feedback.md"):
        p = run_dir / name
        if not p.exists():
            _write(p, "")
    return run_dir


def _iter_runs(inst_dir: Path):
    for sub in ("active_runs", "completed_runs"):
        base = inst_dir / "workspace" / sub
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name.startswith("RUN-"):
                    yield sub, d


def _find_run(inst_dir: Path, run_id: str) -> Path:
    for _sub, d in _iter_runs(inst_dir):
        if d.name == run_id:
            return d
    # CR-AIWS-2026-06-057 — not an in-instance run-folder; consult the run_index back-pointer
    # (aip_driven runs that materialize INTO the driving AIP's Task Workspace).
    for r in _read_run_index(inst_dir):
        if r.get("run_id") == run_id:
            rel = (r.get("task_workspace") or "").replace("\\", "/")
            if not rel:
                _die(f"run_index entry for {run_id} has no task_workspace path")
            tw = (_PROJECT_ROOT / rel).resolve()
            if tw.is_dir():
                _allow_root(tw)
                return tw
            _die(f"run {run_id} maps to a missing Task Workspace: {tw}")
    _die(f"run not found in instance: {run_id}")


def _reconcile(inst_dir: Path) -> "list[str]":
    """Move active_runs whose status is completed/stopped → completed_runs."""
    moved = []
    base = inst_dir / "workspace" / "active_runs"
    done_dir = inst_dir / "workspace" / "completed_runs"
    if not base.is_dir():
        return moved
    for d in sorted(base.iterdir()):
        if d.is_dir() and d.name.startswith("RUN-") and _read_status(d) in ("completed", "stopped"):
            done_dir.mkdir(parents=True, exist_ok=True)
            dst = done_dir / d.name
            if not dst.exists():
                shutil.move(str(d), str(dst))
                moved.append(d.name)
    return moved


# --- AP-CR-27/28: instance lifecycle (upgrade-reconcile + clone) ------------
def _derive_id(display: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (display or "").lower()).strip("_")
    return base[:79] or "agent_clone"


def _copy_tree_guarded(src: Path, dst: Path, exclude_dirs: set) -> int:
    """Recursive copy src→dst, skipping any directory whose name is in exclude_dirs (e.g. run-history).
    Every destination is boundary-checked (_ensure_inside). Stdlib-only. Returns files copied."""
    n = 0
    for child in sorted(src.iterdir()):
        if child.name in exclude_dirs:
            continue
        target = dst / child.name
        if child.is_dir():
            n += _copy_tree_guarded(child, target, exclude_dirs)
        elif child.is_file():
            _ensure_inside(target, "clone-copy")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(child, target)
            n += 1
    return n


def _resolve_process_files(bp: "Path | None") -> "list[Path]":
    """AP-CR-31 — the blueprint's EFFECTIVE process file set: the `process_docs` targets declared in
    blueprint.yaml (resolved relative to the blueprint) + any *.md directly under `bp/process/`
    (excluding a pointer README). Stdlib-only; returns existing files, de-duped, sorted by basename."""
    if bp is None:
        return []
    found = {}
    m = re.search(r"(?ms)^process_docs:\s*\n(.*?)(?=^\S|\Z)", _read(bp / "blueprint.yaml"))
    if m:
        for rel in re.findall(r":\s*(\S+\.md)\s*$", m.group(1), re.M):
            p = (bp / rel).resolve()
            if p.is_file():
                found[p.name] = p
    pdir = bp / "process"
    if pdir.is_dir():
        for child in sorted(pdir.iterdir()):
            if (child.is_file() and child.suffix == ".md"
                    and not child.name.lower().startswith("readme")
                    and child.name not in found):
                found[child.name] = child
    return [found[k] for k in sorted(found)]


def _process_changed(inst_dir: Path, bp: Path) -> bool:
    """AP-CR-31 — True when the base process changed since the instance's process snapshot.
    Compares `.blueprint_snapshot/process/*.md` content to the current resolved base process.
    No snapshot yet → not flagged (like [no-baseline]); captured on first upgrade."""
    snap = inst_dir / ".blueprint_snapshot" / "process"
    if not snap.is_dir():
        return False
    cur = {p.name: _read(p) for p in _resolve_process_files(bp)}
    snp = {p.name: _read(p) for p in sorted(snap.iterdir())
           if p.is_file() and p.suffix == ".md"}
    return cur != snp


def _snapshot_blueprint(inst_dir: Path, bp: Path) -> int:
    """AP-CR-27 — capture a light blueprint snapshot (blueprint.yaml + index files) into
    instances/<id>/.blueprint_snapshot/ as the reconcile baseline (OQ-2 default: light).
    AP-CR-31 — also snapshot the resolved process set into `.blueprint_snapshot/process/`."""
    snap = inst_dir / ".blueprint_snapshot"
    n = 0
    for rel in ("blueprint.yaml", "default_tools/tool_index.yaml", "skills/skill_index.yaml"):
        s = bp / rel
        if s.is_file():
            d = snap / rel
            _ensure_inside(d, "snapshot")
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, d)
            n += 1
    for src in _resolve_process_files(bp):
        d = snap / "process" / src.name
        _ensure_inside(d, "snapshot")
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, d)
        n += 1
    _write(snap / "SNAPSHOT_INFO.txt",
           f"blueprint snapshot of {_rel(bp)}\n"
           f"captured_at: {_today()}\n"
           f"blueprint_version: {_yaml_get(_read(bp / 'blueprint.yaml'), 'blueprint_version')}\n")
    return n


def _drift(inst_dir: Path, bp: Path) -> "tuple[bool, str]":
    """AP-CR-27 drift signal: version-pin mismatch [outdated], snapshot≠current [drift], or no baseline."""
    pinned = _yaml_get(_read(inst_dir / "blueprint_ref.yaml"), "blueprint_version")
    current = _yaml_get(_read(bp / "blueprint.yaml"), "blueprint_version")
    if pinned and current and pinned != current:
        return True, f"[outdated] pinned {pinned} != current {current}"
    snap_bp = inst_dir / ".blueprint_snapshot" / "blueprint.yaml"
    if not snap_bp.exists():
        return True, "[no-baseline] no .blueprint_snapshot yet — run upgrade once to capture"
    if _read(snap_bp) != _read(bp / "blueprint.yaml"):
        return True, "[drift] snapshot blueprint.yaml differs from current"
    if _process_changed(inst_dir, bp):
        return True, "[process-drift] base process changed since snapshot — reconcile instance process (§6D)"
    return False, ""


def _drift_marker(inst_dir: Path) -> str:
    """Short marker for `list` — only GENUINE drift ([outdated]/[drift]). Empty when in sync, custom
    (no blueprint), or merely not-yet-baselined ([no-baseline] is normal, not an alarm)."""
    bp = _blueprint_dir(inst_dir)
    if bp is None:
        return ""
    drift, reason = _drift(inst_dir, bp)
    if not drift or reason.startswith("[no-baseline]"):
        return ""
    return "  " + reason.split("]")[0].lstrip("[").join(("[", "]"))


def _rewrite_instance_identity(dst_dir: Path, new_id: str, display: str) -> None:
    p = dst_dir / "instance.yaml"
    txt = _read(p)
    disp_line = f'display_name: "{display}"'
    txt = re.sub(r"(?m)^instance_id:.*$", lambda m: f"instance_id: {new_id}", txt, count=1)
    if re.search(r"(?m)^display_name:", txt):
        txt = re.sub(r"(?m)^display_name:.*$", lambda m: disp_line, txt, count=1)
    else:
        txt = re.sub(r"(?m)^(instance_id:.*)$", lambda m: m.group(1) + "\n" + disp_line, txt, count=1)
    if re.search(r"(?m)^created_at:", txt):
        txt = re.sub(r"(?m)^created_at:.*$", lambda m: f'created_at: "{_today()}"', txt, count=1)
    if re.search(r"(?m)^last_reviewed_at:", txt):
        txt = re.sub(r"(?m)^last_reviewed_at:.*$", lambda m: "last_reviewed_at: null", txt, count=1)
    _write(p, txt)


def _flag_cloned_memory(dst_dir: Path, src_id: str) -> int:
    """AP-CR-28 — mark each copied confirmed-memory entry clone_review:pending + cloned_from
    (malformed lines kept verbatim, NOT flagged). HUMAN keeps/prunes via /aiws-agent-review-learning."""
    p = dst_dir / "memory" / "confirmed_memory.jsonl"
    if not p.exists():
        return 0
    out, n = [], 0
    for line in _read(p).splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            e = json.loads(s)
        except Exception:
            out.append(line)  # malformed → verbatim, not flagged
            continue
        e["clone_review"] = "pending"
        e["cloned_from"] = src_id
        out.append(json.dumps(e, ensure_ascii=False))
        n += 1
    _write(p, ("\n".join(out) + "\n") if out else "")
    return n


def _write_clone_lineage(dst_dir: Path, src_id: str, why: str) -> None:
    why = (why or f"cloned from {src_id}").replace("\n", " ")
    ref = dst_dir / "blueprint_ref.yaml"
    rtxt = _read(ref)
    for k in ("cloned_from", "cloned_at", "clone_why"):
        rtxt = re.sub(rf"(?m)^{k}:.*$\n?", "", rtxt)
    lineage = (f"cloned_from: {src_id}\n"
               f'cloned_at: "{_today()}"\n'
               f"clone_why: {why}\n")
    if rtxt.strip():
        _write(ref, rtxt.rstrip("\n") + "\n# clone lineage (AP-CR-28)\n" + lineage)
    else:
        _write(ref, "# blueprint_ref.yaml (clone — AP-CR-28)\n" + lineage)
    cl = dst_dir / "changelog.md"
    ctxt = _read(cl)
    entry = (f"## {_today()} — cloned from {src_id} (AIP-EXEC-146 / AP-CR-28)\n"
             f"- layer: override\n"
             f"- affects: instance identity + full instance-owned layer\n"
             f"- why: {why}\n"
             f"- source: HUMAN-feedback\n"
             f"- confirmed_memory entries flagged `clone_review: pending` for HUMAN keep/prune\n\n")
    if ctxt.strip().startswith("#"):
        nl = ctxt.find("\n")
        head, rest = (ctxt[:nl + 1], ctxt[nl + 1:]) if nl != -1 else (ctxt + "\n", "")
        _write(cl, head + "\n" + entry + rest.lstrip("\n"))
    else:
        _write(cl, f"# Changelog — clone of {src_id}\n\n" + entry + ctxt)


def _repin_version(inst_dir: Path, to_v: str) -> None:
    p = inst_dir / "blueprint_ref.yaml"
    txt = _read(p)
    if re.search(r"(?m)^blueprint_version:", txt):
        _write(p, re.sub(r"(?m)^blueprint_version:.*$", lambda m: f'blueprint_version: "{to_v}"', txt, count=1))


def _append_reconcile_log(inst_dir: Path, from_v: str, to_v: str, decisions: str) -> None:
    p = inst_dir / "blueprint_ref.yaml"
    txt = _read(p)
    entry = (f'  - reconciled_at: "{_today()}"\n'
             f'    from_version: "{from_v}"\n'
             f'    to_version: "{to_v}"\n'
             f"    decisions: {decisions}\n"
             f"    by: HUMAN")
    if re.search(r"(?m)^reconcile_log:[ \t]*\[\][ \t]*$", txt):
        _write(p, re.sub(r"(?m)^reconcile_log:[ \t]*\[\][ \t]*$", lambda m: "reconcile_log:\n" + entry, txt, count=1))
    elif re.search(r"(?m)^reconcile_log:[ \t]*$", txt):
        _write(p, re.sub(r"(?m)^(reconcile_log:[ \t]*)$", lambda m: m.group(1) + "\n" + entry, txt, count=1))
    else:
        _write(p, txt.rstrip("\n") + "\nreconcile_log:\n" + entry + "\n")


def _append_instance_changelog_reconcile(inst_dir: Path, from_v: str, to_v: str, decisions: str) -> None:
    cl = inst_dir / "changelog.md"
    ctxt = _read(cl)
    entry = (f"## {_today()} — reconcile blueprint {from_v}->{to_v} (AIP-EXEC-146 / AP-CR-27)\n"
             f"- layer: override\n"
             f"- affects: blueprint-derived fields (HUMAN-confirmed)\n"
             f"- why: {decisions}\n"
             f"- source: HUMAN-feedback\n\n")
    if ctxt.strip().startswith("#"):
        nl = ctxt.find("\n")
        head, rest = (ctxt[:nl + 1], ctxt[nl + 1:]) if nl != -1 else (ctxt + "\n", "")
        _write(cl, head + "\n" + entry + rest.lstrip("\n"))
    else:
        _write(cl, entry + ctxt)


# --- AP-CR-30: instance rename (in-place identity change + previous_ids alias) ----
def _accumulate_previous_ids(txt: str, old_id: str) -> str:
    """AP-CR-30 — append old_id to instance.yaml `previous_ids` (inline-flow), preserving prior aliases
    (no cap — OP-1). Replaces an existing inline/block form, else inserts the line after
    display_name / instance_name / instance_id."""
    existing = _previous_ids_from_text(txt)
    if old_id not in existing:
        existing.append(old_id)
    line = "previous_ids: [" + ", ".join(existing) + "]"
    if re.search(r"(?m)^previous_ids:[ \t]*\[[^\]]*\][ \t]*$", txt):
        return re.sub(r"(?m)^previous_ids:[ \t]*\[[^\]]*\][ \t]*$", lambda m: line, txt, count=1)
    block = re.search(r"(?m)^previous_ids:[ \t]*$\n(?:[ \t]+-[ \t]*\S.*\n?)+", txt)
    if block:
        return txt[:block.start()] + line + "\n" + txt[block.end():]
    for anchor in (r"(?m)^display_name:.*$", r"(?m)^instance_name:.*$", r"(?m)^instance_id:.*$"):
        if re.search(anchor, txt):
            return re.sub(anchor, lambda m: m.group(0) + "\n" + line, txt, count=1)
    return txt.rstrip("\n") + "\n" + line + "\n"


def _rewrite_rename_identity(dst_dir: Path, old_id: str, new_id: str,
                             new_name: str = "", new_display: str = "") -> None:
    """AP-CR-30 — rewrite instance.yaml identity for a rename: instance_id -> new_id, optional
    instance_name/display_name, and accumulate old_id into previous_ids. Unlike clone, this is the SAME
    instance — created_at / last_reviewed_at are left untouched (no reset)."""
    p = dst_dir / "instance.yaml"
    txt = _read(p)
    txt = re.sub(r"(?m)^instance_id:.*$", lambda m: f"instance_id: {new_id}", txt, count=1)
    if new_name:
        nm = f"instance_name: {new_name.replace(chr(10), ' ').strip()}"
        if re.search(r"(?m)^instance_name:", txt):
            txt = re.sub(r"(?m)^instance_name:.*$", lambda m: nm, txt, count=1)
        else:
            txt = re.sub(r"(?m)^(instance_id:.*)$", lambda m: m.group(1) + "\n" + nm, txt, count=1)
    if new_display:
        disp = f'display_name: "{new_display.replace(chr(34), "").strip()}"'
        if re.search(r"(?m)^display_name:", txt):
            txt = re.sub(r"(?m)^display_name:.*$", lambda m: disp, txt, count=1)
        else:
            anchor = r"(?m)^instance_name:.*$" if re.search(r"(?m)^instance_name:", txt) else r"(?m)^instance_id:.*$"
            txt = re.sub(anchor, lambda m: m.group(0) + "\n" + disp, txt, count=1)
    txt = _accumulate_previous_ids(txt, old_id)
    _write(p, txt)


def _rewrite_own_run_history(inst_dir: Path, new_id: str) -> int:
    """AP-CR-30 — repoint the renamed instance's OWN run-records to the new id: `agent_instance_id` in
    each run's run_state.yaml + run_request.yaml (active + completed). NO cross-instance rewrite.
    Returns the number of runs touched."""
    n = 0
    for _sub, run_dir in _iter_runs(inst_dir):
        touched = False
        for fname in ("run_state.yaml", "run_request.yaml"):
            p = run_dir / fname
            if not p.exists():
                continue
            txt = _read(p)
            new = re.sub(r"(?m)^(agent_instance_id:[ \t]*).*$", lambda m: m.group(1) + new_id, txt)
            if new != txt:
                _write(p, new)
                touched = True
        if touched:
            n += 1
    return n


def _append_rename_changelog(inst_dir: Path, old_id: str, new_id: str, why: str) -> None:
    why = (why or f"renamed {old_id} -> {new_id}").replace("\n", " ")
    cl = inst_dir / "changelog.md"
    ctxt = _read(cl)
    entry = (f"## {_today()} — renamed instance_id {old_id} -> {new_id} (AIP-EXEC-147 / AP-CR-30)\n"
             f"- layer: override\n"
             f"- affects: instance identity (instance_id + folder + own run-history; previous_ids alias)\n"
             f"- why: {why}\n"
             f"- source: HUMAN-feedback\n"
             f"- old id retained in `previous_ids` so prior references (cloned_from / run-history / typed old id) still resolve\n\n")
    if ctxt.strip().startswith("#"):
        nl = ctxt.find("\n")
        head, rest = (ctxt[:nl + 1], ctxt[nl + 1:]) if nl != -1 else (ctxt + "\n", "")
        _write(cl, head + "\n" + entry + rest.lstrip("\n"))
    else:
        _write(cl, f"# Changelog — {new_id}\n\n" + entry + ctxt)


# --- subcommands ------------------------------------------------------------
def cmd_start(a) -> None:
    inst_dir = _instance_dir(a.instance)
    instance = inst_dir.name  # canonical id (fuzzy token resolved)
    _check_run_policy(inst_dir, instance, a.aip, a.strict_template)  # AP-CR-25/41: gate BEFORE scaffolding (no orphan run-folder)
    run_id = f"RUN-{_now_id()}-{_slug(a.slug or a.task or 'run')}"

    # CR-AIWS-2026-06-057 — an aip_driven run whose driving AIP has a resolvable Task Workspace
    # materializes INTO that TW (single workspace), with an instance-local run_index back-pointer.
    pol = _instance_run_policy(inst_dir)
    tw = _resolve_task_workspace(a.aip) if (a.aip and pol.get("aip_driven", "").lower() in ("true", "yes")) else None
    if tw is not None:
        _allow_root(tw)
        run_dir = tw
        (tw / "output").mkdir(parents=True, exist_ok=True)
        rl = tw / "run_log.jsonl"
        if not rl.exists():
            _write(rl, "")  # NOTE: no learning_candidates.jsonl in the TW — captures go to 08_capture_inbox.jsonl (CR-042 C1)
        _seed_related_aip(tw, a.aip)
        _write_run_state(tw, run_id, instance, "active", a.task or "")
        arc = _materialize_arc(tw, instance, inst_dir, run_id, a.task or "", a.aip, task_workspace=tw)
        _upsert_run_index(inst_dir, run_id, _tw_rel(tw), a.aip, "active")
        print(f"run started: {run_id}")
        print(f"  REUSES AIP Task Workspace (CR-AIWS-2026-06-057): {_rel(tw)}")
        print(f"  ARC:        {_rel(arc)}")
        print(f"  status:     active  ({_rel(_run_state_path(tw))})")
        print(f"  back-pointer: {_rel(_run_index_path(inst_dir))}  (run_index → {_tw_rel(tw)})")
        print("Next: AI reads 00_active_run_context.md and ACTS AS the agent (HUMAN-prompted).")
        print("      Captures go to the Task Workspace's 08_capture_inbox.jsonl (single project channel).")
        print("      Tool does NOT run the task. No auto-promotion; learning = candidate only.")
        return

    if a.aip and pol.get("aip_driven", "").lower() in ("true", "yes"):
        print(f"  [warn] AIP '{a.aip}' has no resolvable runtime_workspace (run /run-aip start on it first) — run stays in-instance.")
    run_dir = _scaffold_run(inst_dir, run_id)
    if a.aip:
        _seed_related_aip(run_dir, a.aip)  # AP-CR-25: record driving AIP into run_request.yaml
    _write_run_state(run_dir, run_id, instance, "active", a.task or "")
    arc = _materialize_arc(run_dir, instance, inst_dir, run_id, a.task or "", a.aip)
    print(f"run started: {run_id}")
    print(f"  run-folder: {_rel(run_dir)}")
    print(f"  ARC:        {_rel(arc)}")
    print(f"  status:     active  ({_rel(_run_state_path(run_dir))})")
    print("Next: AI reads 00_active_run_context.md and ACTS AS the agent (HUMAN-prompted).")
    print("      Tool does NOT run the task. No auto-promotion; learning = candidate only.")


def cmd_resume(a) -> None:
    inst_dir = _instance_dir(a.instance)
    run_dir = _find_run(inst_dir, a.run_id)
    st = _read_status(run_dir)
    if st in ("completed", "stopped"):
        _die(f"run {a.run_id} is {st} — cannot resume (start a new run)")
    aip = _yaml_get(_read(run_dir / "run_request.yaml"), "related_aip")  # AP-CR-25: keep driving AIP in ARC §8
    # CR-AIWS-2026-06-057 — if this run lives in an AIP Task Workspace (under <project>/.ai-work/workspaces/),
    # keep the capture target pointed at the TW (08_capture_inbox.jsonl), not a run-local learning file.
    _tw = None
    try:
        run_dir.resolve().relative_to((_PROJECT_ROOT / ".ai-work" / "workspaces").resolve())
        _tw = run_dir
    except ValueError:
        _tw = None
    arc = _materialize_arc(run_dir, inst_dir.name, inst_dir, a.run_id,
                           "(resume — see run-so-far in this folder)", aip, task_workspace=_tw)
    print(f"run resumed: {a.run_id}  (status: {st})")
    print(f"  ARC refreshed: {_rel(arc)}")
    print(f"  run_state:     {_rel(_run_state_path(run_dir))}")
    print("Next: AI reloads ARC + run-so-far (output/, run_log.jsonl, progress) and continues.")


def cmd_status(a) -> None:
    inst_dir = _instance_dir(a.instance)
    moved = _reconcile(inst_dir)
    if moved:
        print(f"(reconciled → completed_runs: {', '.join(moved)})")
    if a.run_id:
        run_dir = _find_run(inst_dir, a.run_id)
        print(f"run: {a.run_id}  status: {_read_status(run_dir)}  ({_rel(run_dir)})")
        print("--- run_state.yaml ---")
        print(_read(_run_state_path(run_dir)).rstrip() or "(no run_state.yaml — treated as completed)")
        return
    rows = [(sub, d.name, _read_status(d)) for sub, d in _iter_runs(inst_dir)]
    # CR-AIWS-2026-06-057 — also enumerate TW-backed runs recorded in the run_index back-pointer.
    idx_rows = []
    for r in _read_run_index(inst_dir):
        rid = r.get("run_id")
        rel = (r.get("task_workspace") or "").replace("\\", "/")
        if not rid or not rel:
            continue
        tw = (_PROJECT_ROOT / rel).resolve()
        st = _read_status(tw) if tw.is_dir() else (r.get("status") or "unknown")
        idx_rows.append((rid, st, rel, tw.is_dir()))
    if not rows and not idx_rows:
        print(f"no runs for instance {a.instance}")
        return
    print(f"runs for {a.instance}:")
    for sub, name, st in rows:
        print(f"  [{st:10}] {name}   ({sub})")
    for rid, st, rel, ok in idx_rows:
        print(f"  [{st:10}] {rid}   (task_workspace → {rel}{'' if ok else ' — MISSING'})")


def cmd_stop(a) -> None:
    inst_dir = _instance_dir(a.instance)
    run_dir = _find_run(inst_dir, a.run_id)
    reason = (a.reason or "stopped by HUMAN").replace("\n", " ")
    _set_status(run_dir, "stopped", reason=reason)
    # CR-AIWS-2026-06-057 — keep the run_index back-pointer in sync for TW-backed runs (they do not
    # move under completed_runs; _reconcile only relocates in-instance active_runs).
    idx = _read_run_index(inst_dir)
    rec = next((r for r in idx if r.get("run_id") == a.run_id), None)
    if rec is not None:
        _upsert_run_index(inst_dir, a.run_id, rec.get("task_workspace", ""), rec.get("related_aip", ""), "stopped")
    moved = _reconcile(inst_dir)
    print(f"run stopped: {a.run_id}  reason: {reason}")
    if rec is not None:
        print(f"  run_index updated → stopped  ({_rel(_run_index_path(inst_dir))})")
    if moved:
        print(f"  moved → completed_runs: {', '.join(moved)}")


# --- AP-CR-41: template-conformance gate (consumes CR-AIWS-2026-06-050 `template_source`) -----
_AIP_TEMPLATE_ALIASES = {
    "exec": "aip_exec_template", "plan": "aip_plan_template", "local": "aip_local_template",
    "dd_review": "aip_exec_dd_review_template", "dd-review": "aip_exec_dd_review_template",
    "bd_review": "aip_exec_bd_review_template", "bd-review": "aip_exec_bd_review_template",
    "apply_cr": "aip_exec_apply_cr_template",
}


def _norm_template(value: str) -> str:
    """AP-CR-41 — normalize a template reference (full ID, short alias, OR full path; `.md` optional)
    to one canonical key for conformance comparison. `run_policy.aip_template` may be specified any of
    these ways — this collapses them. Case-insensitive; alias-aware."""
    s = (value or "").strip().strip('"').strip("'").replace("\\", "/")
    s = s.rsplit("/", 1)[-1]                    # basename (drops dirs → handles a full path)
    if s.lower().endswith(".md"):
        s = s[:-3]                              # drop extension
    key = s.lower()
    return _AIP_TEMPLATE_ALIASES.get(key, key)  # short alias → canonical id; else the basename itself


def _resolve_aip_path(aip_id: str):
    """AP-CR-41 — resolve a driving --aip id to its file under <project>/.ai-work/aip/ (the run flow
    carries no account_id → glob across account/kind dirs). Returns (path, count): unique→(p,1);
    none→(None,0); >1→(None,n) ambiguous."""
    tok = (aip_id or "").strip()
    if not tok:
        return (None, 0)
    aip_root = DEV_ROOT.parent.parent / ".ai-work" / "aip"
    if not aip_root.is_dir():
        return (None, 0)
    matches = [p for p in aip_root.glob("**/*.md") if tok in p.stem]
    if len(matches) == 1:
        return (matches[0], 1)
    return (None, len(matches))


def _aip_template_source(aip_path: Path) -> str:
    """AP-CR-41 — read the AIP's write-once `template_source` front-matter (CR-AIWS-2026-06-050). '' if absent."""
    return _yaml_get(_read(aip_path), "template_source")


def _check_run_policy(inst_dir: Path, instance: str, aip: str, strict_template: bool = False) -> None:
    """AP-CR-25 — refuse an aip_driven start without a driving --aip (presence, stage 1).
    AP-CR-41 — then verify TEMPLATE CONFORMANCE: the driving AIP's `template_source` must match the
    instance's `run_policy.aip_template` (basename-normalized → handles id / alias / full path).
    Both stages run INSIDE the aip_driven guard, BEFORE scaffolding (no orphan run-folder)."""
    pol = _instance_run_policy(inst_dir)
    if pol.get("aip_driven", "").lower() not in ("true", "yes"):
        return  # not aip_driven → no gate (backward-compatible)
    aip = (aip or "").strip()
    # --- stage 1: presence (AP-CR-25; unchanged) ---
    if not aip:
        _die(
            f"instance '{instance}' declares run_policy.aip_driven=true — a driving AIP is required.\n"
            "  Follow the flow:\n"
            "    1) /create-aip                      (create the driving AIP for this task)\n"
            "    2) /run-aip                         (work the AIP; agent runs are its steps)\n"
            f"    3) py run_agent.py start {instance} --aip <AIP-ID> --task \"...\"\n"
            "  (no run-folder was created.)"
        )
    # --- stage 2: template conformance (AP-CR-41) ---
    expected = (pol.get("aip_template") or "").strip()
    if not expected:
        return  # no declared template → nothing to conform to
    exp = _norm_template(expected)
    path, n = _resolve_aip_path(aip)
    if n > 1:
        _die(f"AP-CR-41: --aip '{aip}' is ambiguous ({n} AIP files match) — pass a fuller id. (no run-folder created.)")
    if path is None:
        print(f"  [warn] AP-CR-41: could not resolve --aip '{aip}' under .ai-work/aip/ — "
              f"template conformance UNVERIFIED (expected '{exp}'). Proceeding.")
        return
    actual_raw = _aip_template_source(path)
    if not actual_raw:
        msg = (f"AP-CR-41: AIP '{aip}' carries no `template_source` stamp (pre-CR-050 / hand-authored) — "
               f"conformance UNVERIFIED (expected '{exp}').")
        if strict_template:
            _die(msg + "\n  --strict-template set → refusing. (no run-folder created.)")
        print(f"  [warn] {msg} Proceeding (pass --strict-template to enforce).")
        return
    if _norm_template(actual_raw) != exp:
        _die(
            f"AP-CR-41: WRONG TEMPLATE. instance '{instance}' run_policy.aip_template expects '{exp}', "
            f"but AIP '{aip}' was instantiated from '{_norm_template(actual_raw)}' (template_source: {actual_raw}).\n"
            "  Re-create the driving AIP from the right template:\n"
            f"    /create-aip --template {expected}\n"
            "  (no run-folder created.)"
        )
    # match → proceed (silent)


def _seed_related_aip(run_dir: Path, aip: str) -> None:
    """AP-CR-25 — record the driving AIP into run_request.yaml → related_aip."""
    p = run_dir / "run_request.yaml"
    txt = _read(p)
    line = f"related_aip: {aip}"
    if not txt.strip():
        _write(p, f"# run_request.yaml\n{line}\n")
    elif re.search(r"(?m)^related_aip:", txt):
        _write(p, re.sub(r"(?m)^related_aip:.*$", line, txt))
    else:
        _write(p, txt.rstrip("\n") + f"\n{line}\n")


def cmd_list(a) -> None:
    """AP-CR-22 — list instances (id · display_name · blueprint · status) so HUMAN need not memorize ids."""
    insts = _all_instances()
    if not insts:
        print("no instances")
        return
    print("instances:")
    for d in insts:
        bp = _instance_field(d, "blueprint_id") or "(custom)"
        st = _instance_field(d, "status") or "?"
        pol = _instance_run_policy(d)
        gate = "  [aip_driven]" if pol.get("aip_driven", "").lower() in ("true", "yes") else ""
        drift = _drift_marker(d)  # AP-CR-27: [outdated]/[drift]/[no-baseline] vs the blueprint
        print(f"  {d.name}")
        print(f"      display: {_instance_display(d)}  ·  blueprint: {bp}  ·  status: {st}{gate}{drift}")


def cmd_memory(a) -> None:
    """AP-CR-22 — inspect an instance's confirmed memory (first CLI memory surface). Read-only."""
    inst_dir = _instance_dir(a.instance)
    mem = inst_dir / "memory"
    entries = _mem_entries(inst_dir)
    n_cand = len([ln for ln in _read(mem / "candidate_queue.jsonl").splitlines() if ln.strip()])
    print(f"memory — {_instance_display(inst_dir)}  ({inst_dir.name})")
    print(f"  confirmed_memory.jsonl: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}")
    print(f"  candidate_queue.jsonl:  {n_cand} pending candidate(s)")
    prof = [f for f in _memory_profile_files(inst_dir) if f != "confirmed_memory.jsonl"]
    if not prof:  # custom no-Blueprint / no profile → enumerate whatever the instance materialized
        prof = sorted(p.name for p in mem.glob("*")
                      if p.is_file() and p.name not in ("confirmed_memory.jsonl", "candidate_queue.jsonl"))
    for f in prof:
        p = mem / f
        sz = len(_read(p).strip()) if p.exists() else None
        print(f"  {f}: {'MISSING' if sz is None else ('(empty)' if sz == 0 else str(sz) + ' chars')}")
    if a.full:
        print("--- confirmed_memory.jsonl (full) ---")
        for e in entries:
            print(e["_raw"] if "_raw" in e else json.dumps(e, ensure_ascii=False))
    elif entries:
        print("  index (id · type · tags) — use --full to dump:")
        for e in entries:
            if "_raw" in e:
                print(f"    (raw) {e['_raw'][:70]}")
                continue
            eid = e.get("id") or e.get("cm_id") or "?"
            typ = e.get("type") or e.get("kind") or "memory"
            tags = ", ".join(str(t) for t in (e.get("scope_tags") or [])) or "-"
            print(f"    [{eid}] {typ} · {tags}")


def cmd_upgrade(a) -> None:
    """AP-CR-27 — present blueprint↔instance drift for HUMAN per-change reconcile. Thin: it PRESENTS,
    never auto-applies, and NEVER writes the instance-learned layer (FR-AI-09). `--reconcile` records a
    HUMAN-confirmed decision (re-pin version + refresh snapshot + append reconcile_log + changelog)."""
    inst_dir = _instance_dir(a.instance)
    instance = inst_dir.name
    bp = _blueprint_dir(inst_dir)
    if bp is None:
        _die(f"instance '{instance}' is custom (no blueprint) — nothing to reconcile against.")
    pinned = _yaml_get(_read(inst_dir / "blueprint_ref.yaml"), "blueprint_version")
    current = _yaml_get(_read(bp / "blueprint.yaml"), "blueprint_version")
    print(f"upgrade — {instance}")
    print(f"  blueprint: {_rel(bp)}")
    print(f"  pinned blueprint_version: {pinned or '(none)'}   current: {current or '(none)'}")
    # establish the reconcile baseline if this instance was never snapshotted (setup, NOT a reconcile).
    if not (inst_dir / ".blueprint_snapshot" / "blueprint.yaml").exists():
        print(f"  (no baseline snapshot — captured {_snapshot_blueprint(inst_dir, bp)} file(s) now)")
    drift, reason = _drift(inst_dir, bp)
    if not drift:
        print("  in sync — no drift. Nothing to reconcile.")
        return
    print(f"  DRIFT {reason}")
    if not a.reconcile:
        print("--- PRESENT for HUMAN per-change reconcile (tool does NOT auto-apply — FR-AI-09) ---")
        print(f"  blueprint changelog: {_rel(bp / 'changelog.md')}")
        bcl = _read(bp / "changelog.md").rstrip()
        print(bcl if bcl else "  (blueprint has no changelog.md)")
        print(f"  instance changelog:  {_rel(inst_dir / 'changelog.md')}")
        ref = _read(inst_dir / "blueprint_ref.yaml")
        m = re.search(r"(?ms)^customization_summary:.*?(?=^\S|\Z)", ref)
        print("  instance customization_summary (blueprint_ref.yaml):")
        print("    " + ((m.group(0).strip() if m else "(none)")).replace("\n", "\n    "))
        print("--- ownership invariant (FR-AI-09): instance-learned layer "
              "(memory/ training/ context/ local_guidelines) is NEVER auto-overwritten ---")
        # AP-CR-31: process is an instance-owned override asset — present the 3-way for HUMAN merge.
        inst_proc = inst_dir / "process"
        if inst_proc.is_dir():
            snap_proc = inst_dir / ".blueprint_snapshot" / "process"
            print("--- process (AP-CR-31 §6D): instance OWNS its process — 3-way present, HUMAN merges per file ---")
            print(f"  base@pinned:  {_rel(snap_proc)}"
                  + ("" if snap_proc.is_dir() else "  (no process baseline yet — captured on confirm)"))
            print(f"  base@current: {_rel(bp / 'process')}  (resolved via process_docs)")
            print(f"  instance:     {_rel(inst_proc)}")
            print("  Merge adopted base-process changes into the instance process yourself "
                  "(HUMAN-gated); keep governance_invariant steps.")
        print("  After deciding which blueprint changes to adopt, record the reconcile:")
        print(f'    py run_agent.py upgrade {instance} --reconcile --to-version "{current}" --decisions "adopted X, skipped Y"')
        return
    to_v = (a.to_version or current).strip()
    decisions = (a.decisions or "see instance changelog").replace("\n", " ")
    _append_reconcile_log(inst_dir, pinned or "?", to_v, decisions)
    _repin_version(inst_dir, to_v)
    cnt = _snapshot_blueprint(inst_dir, bp)
    _append_instance_changelog_reconcile(inst_dir, pinned or "?", to_v, decisions)
    print(f"  reconcile recorded: re-pinned {pinned or '?'}->{to_v}; snapshot refreshed ({cnt} file(s)); "
          "reconcile_log + instance changelog appended.")
    print("  NOTE: the instance-learned layer was NOT touched. Apply any adopted blueprint changes to the "
          "instance-override layer yourself (HUMAN-gated).")


def cmd_clone(a) -> None:
    """AP-CR-28 — create a NEW instance from an existing one: full-copy of the instance-owned layer
    EXCEPT run-history; new identity; copied confirmed memory auto-flagged clone_review:pending + cloned_from;
    candidate_queue reset; lineage recorded. Does NOT auto-run; does NOT modify the source."""
    src_dir = _instance_dir(a.source)
    src_id = src_dir.name
    display = (a.as_name or "").strip()
    if not display:
        _die('clone requires --as "<display_name>"')
    new_id = (a.new_id or "").strip() or _derive_id(display)
    if not _ID_RE.match(new_id):
        _die(f"invalid new instance id '{new_id}' (letters/digits/_/-, <=80 chars)")
    base, i = new_id, 2
    while (INSTANCES / new_id).exists():
        new_id = f"{base}_{i}"
        i += 1
        if not _ID_RE.match(new_id):
            _die(f"cannot derive a free id from '{base}'")
    dst_dir = INSTANCES / new_id
    _ensure_inside(dst_dir, "clone-target")
    # 1) full-copy instance-owned layer, EXCLUDING run-history + triage state
    copied = _copy_tree_guarded(src_dir, dst_dir, {"workspace", "training"})
    # 2) recreate EMPTY workspace + training skeleton (no run-history; candidate_queue reset)
    for sub in ("workspace/active_runs", "workspace/completed_runs",
                "workspace/handoff_artifacts", "workspace/step_outputs"):
        (dst_dir / sub).mkdir(parents=True, exist_ok=True)
    _write(dst_dir / "training" / "candidate_queue.jsonl", "")
    _write(dst_dir / "training" / "feedback_log.jsonl", "")
    _write(dst_dir / "training" / "periodic_review_log.md",
           f"# Periodic Improvement Review — {display}\n\n(cloned from {src_id} on {_today()}; no reviews yet)\n")
    # 3) new identity (instance_id + display_name + reset created_at/last_reviewed_at)
    _rewrite_instance_identity(dst_dir, new_id, display)
    # 4) auto-flag-review copied confirmed memory
    flagged = _flag_cloned_memory(dst_dir, src_id)
    # 5) lineage (blueprint_ref + changelog)
    _write_clone_lineage(dst_dir, src_id, a.why or "")
    print(f"cloned: {src_id} -> {new_id}  (display: {display})")
    print(f"  copied {copied} file(s) of the instance-owned layer (run-history NOT copied; candidate_queue reset)")
    print(f"  confirmed_memory: {flagged} entr{'y' if flagged == 1 else 'ies'} flagged clone_review:pending (+cloned_from)")
    print("  lineage recorded in blueprint_ref.yaml + changelog.md")
    print(f"  next: review carried-over memory for the new project →  py run_agent.py memory {new_id}   then  /aiws-agent-review-learning")
    print("  (clone does NOT run the agent; source instance unchanged.)")


def cmd_rename(a) -> None:
    """AP-CR-30 — controlled rename of an instance's machine identity. Validates the new id, hard-moves
    the folder, rewrites instance.yaml identity (+ optional names) and the instance's OWN run-history,
    and records the old id in `previous_ids` (accumulating alias) so old references still resolve via the
    alias-aware resolver. No cross-instance rewrite, no auto-run, no source duplication. Supersedes the
    AP-CR-23 id-immutability rule (rename only via this command)."""
    src_dir = _instance_dir(a.source)
    old_id = src_dir.name
    new_id = (a.to_id or "").strip()
    if not new_id:
        _die('rename requires --to <new_id>')
    if not _ID_RE.match(new_id):
        _die(f"invalid new instance id '{new_id}' (letters/digits/_/-, <=80 chars)")
    if new_id == old_id:
        _die(f"no-op: --to '{new_id}' equals the current id")
    if (INSTANCES / new_id).exists():
        _die(f"target id already exists: {new_id} (collision with a current instance id). Pick another --to.")
    for d in _all_instances():  # OQ-2 = refuse: keep alias resolution unambiguous
        if d.name == old_id:
            continue
        if new_id in _instance_previous_ids(d):
            _die(f"--to '{new_id}' is already an alias (previous_id) of instance '{d.name}'. Pick another.")
    dst_dir = INSTANCES / new_id
    _ensure_inside(dst_dir, "rename-target")
    # validated → now hard-move + repoint identity (same instance, in place)
    shutil.move(str(src_dir), str(dst_dir))
    _rewrite_rename_identity(dst_dir, old_id, new_id, a.name, a.as_name)
    n_runs = _rewrite_own_run_history(dst_dir, new_id)
    _append_rename_changelog(dst_dir, old_id, new_id, a.why or "")
    print(f"renamed: {old_id} -> {new_id}")
    if a.name or a.as_name:
        bits = []
        if a.name:
            bits.append(f'instance_name="{a.name}"')
        if a.as_name:
            bits.append(f'display_name="{a.as_name}"')
        print(f"  names updated: {', '.join(bits)}")
    print(f"  folder moved; previous_ids += {old_id}  (old id still resolves via the alias-aware resolver)")
    print(f"  run-history repointed: {n_runs} run(s) updated (agent_instance_id)")
    print("  changelog.md entry appended (WHY).  (rename does NOT run the agent; no cross-instance rewrite.)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="run_agent.py", description="Agent Runtime orchestrator (thin)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="create run + ARC")
    s.add_argument("instance")
    s.add_argument("--task", default="", help="HUMAN task prompt (embedded in ARC)")
    s.add_argument("--slug", default="", help="short slug for the run id")
    s.add_argument("--aip", default="", help="driving AIP id (required when instance run_policy.aip_driven=true)")
    s.add_argument("--strict-template", action="store_true",
                   help="AP-CR-41: refuse if the driving AIP lacks a template_source stamp (default: warn)")
    s.set_defaults(fn=cmd_start)

    r = sub.add_parser("resume", help="refresh ARC + show run_state")
    r.add_argument("instance")
    r.add_argument("run_id")
    r.set_defaults(fn=cmd_resume)

    st = sub.add_parser("status", help="show one run or list runs")
    st.add_argument("instance")
    st.add_argument("run_id", nargs="?", default="")
    st.set_defaults(fn=cmd_status)

    sp = sub.add_parser("stop", help="mark stopped + move to completed_runs")
    sp.add_argument("instance")
    sp.add_argument("run_id")
    sp.add_argument("--reason", default="")
    sp.set_defaults(fn=cmd_stop)

    ls = sub.add_parser("list", help="list instances (id · display_name · blueprint · status)")
    ls.set_defaults(fn=cmd_list)

    m = sub.add_parser("memory", help="show an instance's confirmed memory (+ lessons/candidate counts)")
    m.add_argument("instance")
    m.add_argument("--full", action="store_true", help="dump all confirmed_memory entries")
    m.set_defaults(fn=cmd_memory)

    up = sub.add_parser("upgrade", help="present blueprint drift; record a HUMAN reconcile (AP-CR-27)")
    up.add_argument("instance")
    up.add_argument("--reconcile", action="store_true", help="record a HUMAN-confirmed reconcile (re-pin + snapshot + log)")
    up.add_argument("--to-version", default="", help="blueprint_version to re-pin to (default: current)")
    up.add_argument("--decisions", default="", help="one-line summary of which blueprint changes were adopted/skipped")
    up.set_defaults(fn=cmd_upgrade)

    cl = sub.add_parser("clone", help="create a new instance from an existing one (AP-CR-28)")
    cl.add_argument("source", help="source instance (fuzzy id / role word / display_name)")
    cl.add_argument("--as", dest="as_name", default="", help="display_name for the new instance (required)")
    cl.add_argument("--id", dest="new_id", default="", help="explicit new instance_id (default: derived from --as)")
    cl.add_argument("--why", default="", help="why this clone (recorded in lineage + changelog)")
    cl.set_defaults(fn=cmd_clone)

    rn = sub.add_parser("rename", help="rename an instance's machine id (+folder) with a previous_ids alias (AP-CR-30)")
    rn.add_argument("source", help="source instance (fuzzy id / role word / display_name / previous id)")
    rn.add_argument("--to", dest="to_id", default="", help="new instance_id (required; validated + collision-checked)")
    rn.add_argument("--name", dest="name", default="", help="new instance_name (optional)")
    rn.add_argument("--as", dest="as_name", default="", help="new display_name (optional)")
    rn.add_argument("--why", default="", help="why this rename (recorded in changelog)")
    rn.set_defaults(fn=cmd_rename)

    a = p.parse_args(argv)
    a.fn(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
