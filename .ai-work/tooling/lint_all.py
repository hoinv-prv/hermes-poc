#!/usr/bin/env python3
"""Run all MVP lints (AIP, workspaces, wiki) and aggregate results.

This is a convenience driver. It runs the individual linters in-process
and combines their findings into a single report.

v0.9.16: workspace lint includes Active Step Context and
Step Output / Decision Discussion Trace checks.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    LintReport, apply_lint_accept, emit_report, find_ai_work_root,
)

import lint_aip  # noqa: E402
import lint_wiki  # noqa: E402
import lint_workspace  # noqa: E402
from _common import parse_frontmatter, read_text  # noqa: E402


WS_MARKERS = ("00_task_brief.md", ".current_step.json")
_AIP_KINDS = ("exec", "plans", "local")
ARCHIVE_NAMES = {"done", "archive"}  # CAP-015: done/ archive handling is a separate deferred CR


def _iter_aip_files(ai_work: Path):
    """Yield every real AIP file under aip/ — RECURSIVE over per-account folders
    (aip/<account_id>/<kind>/) + legacy flat (aip/<kind>/), excluding templates, readme, and
    done/ archives (CR-AIWS-2026-06-015 v2; done/ deferred per CAP-015)."""
    aip_root = ai_work / "aip"
    if not aip_root.is_dir():
        return
    for f in sorted(aip_root.rglob("*.md")):
        rel = f.relative_to(aip_root).parts
        if f.name.lower() == "readme.md" or "templates" in rel or any(p in ARCHIVE_NAMES for p in rel):
            continue
        yield f


def _aip_scope(f: Path, ai_work: Path) -> str:
    """Account namespace of an AIP path ('(legacy)' for flat aip/<kind>/)."""
    parts = f.relative_to(ai_work / "aip").parts
    if not parts or parts[0] in _AIP_KINDS:
        return "(legacy)"
    return parts[0]


def _is_workspace(d) -> bool:
    return any((d / m).exists() for m in WS_MARKERS)


def _discover_workspaces(ws_root) -> list:
    """Discover workspaces by marker (CR-015 v2): a marker-bearing dir is a workspace; a dir
    without a marker is a CONTAINER (per-account folder <account_id>/) → recurse ONE level.
    Archive containers (done/) are skipped — deferred per CAP-015."""
    found: list = []
    for entry in sorted(ws_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in ARCHIVE_NAMES:
            continue
        if _is_workspace(entry):
            found.append(entry)
            continue
        for sub in sorted(entry.iterdir()):
            if (sub.is_dir() and not sub.name.startswith(".")
                    and sub.name not in ARCHIVE_NAMES and _is_workspace(sub)):
                found.append(sub)
    return found


def _check_duplicate_artifact_ids(ai_work: Path, report: LintReport) -> None:
    """Cross-file uniqueness check for AIP artifact_id, ACCOUNT-SCOPED (CR-015 v2).

    Recurses per-account folders + legacy flat (via _iter_aip_files). A bare AIP-<KIND>-NNN may
    legitimately recur across account folders (the folder is the namespace), so a collision is
    only flagged WITHIN the same (account, id) scope. Added after FND-030/031 caught a silent
    duplicate that slipped past per-file lint.
    """
    by_key: dict[tuple[str, str], list[Path]] = {}
    for f in _iter_aip_files(ai_work):
        meta, _ = parse_frontmatter(read_text(f))
        aid = meta.get("artifact_id")
        if aid:
            by_key.setdefault((_aip_scope(f, ai_work), aid), []).append(f)
    root_aip = ai_work / "truth" / "AIP_ROOT.md"
    if root_aip.exists():
        meta, _ = parse_frontmatter(read_text(root_aip))
        aid = meta.get("artifact_id")
        if aid:
            by_key.setdefault(("(legacy)", aid), []).append(root_aip)

    for (scope, aid), paths in by_key.items():
        if len(paths) > 1:
            joined = ", ".join(str(p) for p in paths)
            report.error(
                "duplicate_artifact_id",
                f"artifact_id '{aid}' used by {len(paths)} files in account scope '{scope}': {joined}",
                path=str(paths[0]),
            )


def main() -> int:
    p = argparse.ArgumentParser(description="Run AIP + workspace + wiki lints")
    p.add_argument("--project-root")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--show-accepted", action="store_true",
                   help="list lint_accept-muted findings instead of just tallying them")
    ns = p.parse_args()

    root = Path(ns.project_root).resolve() if ns.project_root else find_ai_work_root(Path.cwd())
    ai_work = root / ".ai-work"
    aggregate = LintReport(target=str(ai_work))

    # AIP (recursive: per-account folders + legacy flat, excl. templates + done/) — CR-015 v2
    for f in _iter_aip_files(ai_work):
        lint_aip._lint_file(f, ai_work, aggregate)
    root_aip = ai_work / "truth" / "AIP_ROOT.md"
    if root_aip.exists():
        lint_aip._lint_file(root_aip, ai_work, aggregate)

    # Cross-file AIP-ID uniqueness (FND-030 / FND-031 remediation)
    _check_duplicate_artifact_ids(ai_work, aggregate)

    # Wiki entries
    wiki_root = ai_work / "wiki"
    if wiki_root.is_dir():
        for f in sorted(wiki_root.rglob("*.md")):
            if f.name.lower() == "readme.md":
                continue
            lint_wiki._lint_wiki_entry(f, aggregate)

    # Wiki sources
    meta_root = ai_work / "wiki_sources" / "meta"
    if meta_root.is_dir():
        for f in sorted(meta_root.rglob("*.md")):
            lint_wiki._lint_source_meta(f, aggregate)
    for idx_name in ("index.jsonl", "index.local.jsonl"):
        index_path = ai_work / "wiki_sources" / idx_name
        if index_path.exists():
            lint_wiki._lint_source_index(index_path, aggregate)
    for rel_name in ("relations.jsonl", "relations.local.jsonl"):
        rel_path = ai_work / "wiki_sources" / rel_name
        if rel_path.exists():
            idx_for = ai_work / "wiki_sources" / ("index.local.jsonl" if "local" in rel_name else "index.jsonl")
            lint_wiki._lint_relations(rel_path, idx_for, ai_work / "wiki_sources" / "meta", aggregate)

    # Repo-structure anti-KO guards (two-kind node model, CR-023 INV-1/INV-8)
    lint_wiki._lint_object_node_invariants(ai_work, aggregate)
    # Object-node golden-fixture regression guard (CR-AIWS-2026-06-004 C5)
    lint_wiki._lint_object_golden_fixtures(ai_work, aggregate)

    # Workspaces — CR-015 v2: discover by marker so per-account containers
    # (.ai-work/workspaces/<account_id>/) are recursed into, not mis-linted as workspaces.
    ws_root = ai_work / "workspaces"
    if ws_root.is_dir():
        for ws_dir in _discover_workspaces(ws_root):
            sub = LintReport(target=str(ws_dir))
            lint_workspace.lint_workspace_dir(ws_dir, sub)
            aggregate.findings.extend(sub.findings)

    # Agent lint (CR-AIWS-2026-06-049 T1): fold the AI Agents Pack lint into /lint-all when the
    # pack runtime subtree exists. No-op (zero added output) when .ai-work/agents/ is absent —
    # a pack-less project lints exactly as before. Runs the pack-internal lint_agents.py as an
    # isolated subprocess; a structural-defect exit (≠0) becomes one aggregate error. Degrades
    # gracefully — an invocation failure is reported, never crashes the aggregate.
    agents_lint = ai_work / "agents" / "tooling" / "lint_agents.py"
    if agents_lint.exists():
        import subprocess  # stdlib
        try:
            proc = subprocess.run(
                [sys.executable, str(agents_lint)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            )
            if proc.returncode != 0:
                aggregate.error(
                    "agent_lint",
                    "lint_agents.py reported structural defects:\n"
                    + ((proc.stdout or "") + (proc.stderr or "")).strip(),
                    path=str(agents_lint),
                )
        except Exception as e:  # never let agent lint break the aggregate
            aggregate.error(
                "agent_lint_invoke",
                f"could not run lint_agents.py: {e}",
                path=str(agents_lint),
            )

    apply_lint_accept(aggregate, ai_work)
    return emit_report(aggregate, ns.format, ns.strict, ns.show_accepted)


if __name__ == "__main__":
    raise SystemExit(main())
