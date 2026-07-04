#!/usr/bin/env python3
"""Build an installable package for AI Work System MVP.

Copies 10 payload sections (methodology, wiki guidelines, skills, tooling,
AIP templates, workspace template, preset knowledge, procedural,
truth templates, guidelines) from a source project rooted at `.ai-work/`
into a versioned output folder,
then generates README, MANIFEST, install_guide, CLAUDE_SLIM_TEMPLATE, and
optional CHANGELOG (when --prev points to a previous package).

Python stdlib only. Safe to re-run (refuses to overwrite existing output).

The package version is NOT supplied on the command line — it is read from
`product/aiws_version.md` (single source of truth) so every build produces the
same version regardless of who runs it. To cut a new release, bump that file.

Usage:
    # Official build — version comes from product/aiws_version.md:
    python build_aiws_install_package.py

    # Trial/ephemeral build (quick_install only) — override the pinned version:
    python build_aiws_install_package.py --override-version trial-2026-06-05 \\
        --output /tmp/pkg --no-prev

Exit codes: 0 OK, 2 error.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _common import find_ai_work_root, parse_frontmatter, read_text, today


# ---------- Version pin (single source of truth) ----------
# The package version lives in product/aiws_version.md, NOT in a CLI flag, so the
# build is deterministic across people. Bumping the version is a deliberate edit
# to that file — separate from running the build.
VERSION_PIN_REL = "product/aiws_version.md"


def read_pinned_version(project_root: Path) -> tuple[str, str | None]:
    """Read (aiws_version, release_date) from product/aiws_version.md frontmatter.

    release_date is optional (None when absent/blank). Raises SystemExit with a
    clear message if the pin file is missing or has no aiws_version.
    """
    pin = project_root / VERSION_PIN_REL
    if not pin.exists():
        raise SystemExit(
            f"error: version pin file not found: {pin}\n"
            f"       create it with frontmatter:  aiws_version: v1.0"
        )
    meta, _ = parse_frontmatter(read_text(pin))
    version = str(meta.get("aiws_version", "")).strip()
    if not version:
        raise SystemExit(
            f"error: 'aiws_version' is missing or empty in {pin}"
        )
    release_date = str(meta.get("release_date", "")).strip() or None
    return version, release_date


# ---------- Payload section mapping ----------
# All source paths are relative to project root.
# Principle: everything shipped must live under product/ first.

@dataclass
class Section:
    name: str
    src_rel: str
    dst_rel: str
    description: str
    # Subdirectory names (relative to src_rel) to skip during copy — internal/design content
    exclude_subdirs: frozenset = field(default_factory=frozenset)
    # File names (relative to src_rel) to skip during copy — project-owned data that must never ship
    exclude_files: frozenset = field(default_factory=frozenset)


PAYLOAD_SECTIONS: list[Section] = [
    Section(
        "methodology",
        "product/methodology/ai_work_system",
        "payload/methodology",
        "AI Work System methodology (specs, guides — no brainstorming/design/delta-tracking)",
        # Exclude internal design artefacts — not needed to run skills/tools, reveals design rationale
        frozenset({"00_brainstorming", "10_design", "90_delta_tracking"}),
    ),
    Section(
        "wiki_guidelines",
        "product/wiki_guidelines",
        "payload/wiki_guidelines",
        "Wiki Guideline Package (core + install + rollout + upgrade)",
    ),
    Section(
        "skills",
        "product/skills",
        "payload/skills",
        "Claude Code user-invocable skills",
        frozenset({"quick-install-aiws"}),  # dev-only — never ship (CR-026)
    ),
    Section(
        "commands",
        "product/commands",
        "payload/commands",
        "Claude Code slash commands (build-project-wiki, …)",
    ),
    Section(
        "tooling",
        "product/tooling",
        "payload/tooling",
        "Python stdlib tooling (no pip install)",
        # dev-only — never ship: quick-install (CR-026) is a maintenance TOOL that lives in
        # tooling but must not reach adopters. The dev regression TESTS + the wiki_corpus fixture
        # were consolidated to .ai-work/tests/ (2026-06-20) — that dir is not a build payload
        # source, so they need no exclude entry here.
        frozenset({"quick_install_aiws.py"}),
    ),
    Section(
        "aip_templates",
        "product/aip_templates",
        "payload/aip_templates",
        "AIP ROOT/PLAN/EXEC/LOCAL templates",
        frozenset({"tracking"}),
    ),
    Section(
        "workspace_templates",
        "product/workspace_templates",
        "payload/workspace_templates",
        "Task workspace skeleton",
    ),
    Section(
        "preset_knowledge",
        "product/preset_knowledge",
        "payload/preset_knowledge",
        "Preset AIP exec templates, samples, selection guides",
    ),
    Section(
        "procedural",
        "product/procedural",
        "payload/procedural",
        "Playbooks, modes, queue/capture rules, lint policy",
        frozenset({"skills/quick-install-aiws"}),  # dev-only — never ship (CR-026)
    ),
    Section(
        "truth_templates",
        "product/truth_templates",
        "payload/truth_templates",
        "Starter SOP templates (SOP_MASTER, SOP_DevelopmentTasks) for target project Truth zone",
    ),
    Section(
        "guidelines",
        "product/guidelines",
        "payload/guidelines",
        "Operational guidelines (onboarding, day-to-day usage) for adopters",
    ),
    Section(
        "wiki_source_profiles",
        "product/wiki_source_profiles",
        "payload/wiki_source_profiles",
        "Canonical-tooling wiki source profiles the builders require (java_class, knowledge_object) "
        "+ README; MERGED into the project at install, never overwritten (CR-AIWS-2026-06-047)",
        # project-owned term-data — never ship/overwrite a project's stopwords (CR-047 Change C)
        exclude_files=frozenset({"project_stopwords.yml"}),
    ),
    Section(
        "agents",
        "product/agents",
        "payload/agents",
        "AI Agents Pack — self-contained package (blueprints, templates, tooling, tools, docs, "
        "router skill + verb commands). Ships whole to .ai-work/agents/; the pack's .claude/ surfaces "
        "(verb commands + aiws-agent router skill) are ALSO wired to .claude/ by wire_agent_pack_claude "
        "(CR-AIWS-2026-06-051); agent lint wired into /lint-all by CR-AIWS-2026-06-049. Optional section: "
        "absent product/agents/ → skipped, default build unchanged (CR-AIWS-2026-06-055).",
        # runtime instances + dev fixtures/process docs never ship (defensive — product/agents/ is already clean)
        exclude_subdirs=frozenset({"agents/instances", "sample_project_package"}),
        exclude_files=frozenset({"assistant_to_agent_mapping.md", "parity_verification_report.md"}),
    ),
]

EXTRA_SINGLE_FILES: list[tuple[str, str]] = []


# ---------- Design-doc strip-and-copy ----------
# 10_design/ files contain a mix of operational knowledge (useful for adopters) and
# AIWS-internal design rationale (explains WHY specs are what they are).
# These files are excluded from the main section copy (via exclude_subdirs) but then
# copied here with the internal sections removed.

# Per-file: top-level headings whose entire section should be removed in the package copy.
DESIGN_STRIP_HEADINGS: dict[str, list[str]] = {
    "product/methodology/ai_work_system/10_design/Architecture_Design_MVP.md": [
        "# 2. Why the architecture needs to evolve",
        "# 13. Proposed merged content summary",
        "# 14. Delta status",
    ],
    "product/methodology/ai_work_system/10_design/Basic_Design_MVP.md": [
        "# 2. Why the Basic Design needs to be refactored",
        "# 14. Impact note for canonical Basic Design refactor",
        "# 15. Proposed merged content summary",
        "# 16. Delta status",
    ],
    "product/methodology/ai_work_system/10_design/Methodology_Design_MVP.md": [
        "# 4. Design phase sequence",
        "# 5. Boundary của từng phase",
        "# 17. Deliverables của phase Methodology Design",
        "# 18. Definition of Done cho phase Methodology Design",
    ],
    # Conceptual_Design_MVP.md: no sections to strip — keep fully
}

# Files from 10_design/ to include in the package (stripped). Detail_Design is omitted.
DESIGN_DOCS_STRIP_COPY: list[str] = [
    "product/methodology/ai_work_system/10_design/Architecture_Design_MVP.md",
    "product/methodology/ai_work_system/10_design/Basic_Design_MVP.md",
    "product/methodology/ai_work_system/10_design/Conceptual_Design_MVP.md",
    "product/methodology/ai_work_system/10_design/Methodology_Design_MVP.md",
]


def strip_design_sections(content: str, headings_to_remove: list[str]) -> str:
    """Remove markdown sections (and their subsections) matching the given headings.

    Removes the preceding horizontal rule separator as well so the document
    stays clean. Works for any heading depth — stops skipping when a heading
    of equal or lesser depth is encountered.
    """
    if not headings_to_remove:
        return content
    lines = content.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        heading = lines[i].rstrip()
        if heading in headings_to_remove:
            level = len(heading) - len(heading.lstrip("#"))
            # Drop the preceding blank lines + '---' separator
            while result and result[-1].strip() == "":
                result.pop()
            if result and result[-1].strip() == "---":
                result.pop()
            while result and result[-1].strip() == "":
                result.pop()
            # Skip this section until a heading of equal or lesser depth
            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip()
                if nxt.startswith("#"):
                    curr_level = len(nxt) - len(nxt.lstrip("#"))
                    if curr_level <= level:
                        break  # hand off to outer loop without incrementing
                i += 1
        else:
            result.append(lines[i])
            i += 1
    text = "\n".join(result)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"


# ---------- AIWS wiki bundle (CR-AIWS-2026-06-040) ----------
# Ship the curated AIWS source metas (methodology + wiki_guidelines + preset_knowledge),
# path-rebased for the target install layout, as a dedicated `aiws` namespace. The metas
# live in .ai-work/wiki_sources/meta/ (a projection of the product docs), not under product/,
# so they are generated into the package at BUILD time (like the design-doc strip-copy), then
# the index (index.aiws.jsonl) is rebuilt from them at INSTALL time. Only artifact_locator is
# rewritten; meta_locator is not carried (the index is rebuilt locally). See CR-040.

AIWS_WIKI_META_GROUPS = ["methodology", "wiki_guidelines", "preset_knowledge"]

# Rebase: dev-repo meta artifact_locator (project-root-relative) -> target install locator.
# Ordered longest-prefix-first; mirrors PAYLOAD_SECTIONS + the install_guide payload mapping.
AIWS_WIKI_REBASE: list[tuple[str, str]] = [
    ("product/methodology/ai_work_system/", ".ai-work/truth/canonical/methodology/"),
    ("product/wiki_guidelines/", ".ai-work/truth/canonical/wiki_guidelines/"),
    ("product/preset_knowledge/", ".ai-work/preset_knowledge/"),
]


def _aiws_meta_source_shipped(locator: str) -> bool:
    """A meta is shippable only if its source artifact is actually shipped.

    The methodology payload section excludes 00_brainstorming/10_design/90_delta_tracking
    (10_design's 4 design docs are re-added stripped; Detail_Design is omitted). A shipped
    index must never point at a missing file.
    """
    if "/00_brainstorming/" in locator or "/90_delta_tracking/" in locator:
        return False
    if locator.endswith("10_design/Detail_Design_MVP_Core_Artifacts.md"):
        return False
    return True


def _aiws_rebase_locator(locator: str) -> str | None:
    """Rewrite a dev-repo artifact_locator to its target install locator, or None if it
    falls outside the three shipped groups (caller skips)."""
    for old, new in AIWS_WIKI_REBASE:
        if locator.startswith(old):
            return new + locator[len(old):]
    return None


def build_aiws_wiki_bundle(project_root: Path, output: Path,
                           file_section_map: dict[str, str]) -> int:
    """Ship the curated AIWS metas into payload/aiws_wiki/ (CR-040).

    PREFERRED source: pre-built, install-layout metas under
    `.ai-work/wiki_sources/aiws_meta/{group}/` whose `artifact_locator` ALREADY points
    at the target layout (`.ai-work/truth/canonical/...` + `.ai-work/preset_knowledge/...`).
    These are shipped VERBATIM — no rebase, no source-shipped filter — because the dir is
    itself the curated, install-layout, already-filtered set (built by generating metas over
    an installed package). This avoids the fragile product/->target string-rebase and the
    OS-dependent source_id churn of regenerating the dev `meta/` tree.

    FALLBACK (legacy CR-040 path, used only when `aiws_meta/` is absent): rebase the dev
    metas under `.ai-work/wiki_sources/meta/{group}/` from their product/ artifact_locator,
    dropping metas whose source isn't shipped. Returns files written.
    """
    prebuilt = project_root / ".ai-work" / "wiki_sources" / "aiws_meta"
    if prebuilt.is_dir():
        written = 0
        for group in AIWS_WIKI_META_GROUPS:
            gdir = prebuilt / group
            if not gdir.is_dir():
                print(f"  ! aiws_wiki: meta group missing ({gdir})")
                continue
            for meta in sorted(gdir.rglob("*.md")):
                rel = meta.relative_to(prebuilt)
                dst = output / "payload" / "aiws_wiki" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(meta.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
                file_section_map[dst.relative_to(output).as_posix()] = "aiws_wiki"
                written += 1
        print(f"  [aiws_wiki            ] {written} metas (shipped verbatim from aiws_meta/; target-layout)")
        return written

    src_root = project_root / ".ai-work" / "wiki_sources" / "meta"
    written = 0
    skipped = 0
    for group in AIWS_WIKI_META_GROUPS:
        gdir = src_root / group
        if not gdir.is_dir():
            print(f"  ! aiws_wiki: meta group missing ({gdir})")
            continue
        for meta in sorted(gdir.rglob("*.md")):
            raw = meta.read_text(encoding="utf-8", errors="replace")
            fm, _ = parse_frontmatter(raw)
            loc = str(fm.get("artifact_locator", "")).strip()
            if not loc or not _aiws_meta_source_shipped(loc):
                skipped += 1
                continue
            new_loc = _aiws_rebase_locator(loc)
            if new_loc is None:
                skipped += 1
                continue
            rebased = raw.replace(loc, new_loc)  # rewrites frontmatter + ## Artifact Reference body line
            rel = meta.relative_to(src_root)
            dst = output / "payload" / "aiws_wiki" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(rebased, encoding="utf-8")
            file_section_map[dst.relative_to(output).as_posix()] = "aiws_wiki"
            written += 1
    print(f"  [aiws_wiki            ] {written} metas (rebased; {skipped} skipped — source not shipped)")
    return written


# ---------- Exclusions ----------

EXCLUDE_DIR_NAMES = {
    "__pycache__", ".DS_Store", ".pytest_cache", ".mypy_cache",
    "node_modules", ".git",
}

EXCLUDE_GLOB_PATTERNS = [
    "*.pyc", "*.pyo", "*.bak-*", "*.preview",
    "*.local.md", ".DS_Store",
]


def is_excluded(path: Path) -> bool:
    name = path.name
    if name in EXCLUDE_DIR_NAMES:
        return True
    for pat in EXCLUDE_GLOB_PATTERNS:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


# ---------- Copy helper ----------

def copy_tree_filtered(
    src: Path, dst: Path, exclude_abs: frozenset | None = None
) -> tuple[int, int]:
    """Recursively copy src → dst skipping excluded names/paths. Returns (files, dirs)."""
    files_copied = 0
    dirs_created = 0
    if not src.exists():
        raise SystemExit(f"error: source not found: {src}")
    if src.is_file():
        if is_excluded(src):
            return (0, 0)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return (1, 0)
    dst.mkdir(parents=True, exist_ok=True)
    dirs_created += 1
    for child in sorted(src.iterdir()):
        if is_excluded(child):
            continue
        if exclude_abs and child in exclude_abs:
            continue
        sub_dst = dst / child.name
        if child.is_dir():
            f, d = copy_tree_filtered(child, sub_dst, exclude_abs)
            files_copied += f
            dirs_created += d
        else:
            shutil.copy2(child, sub_dst)
            files_copied += 1
    return (files_copied, dirs_created)


# ---------- AI Agents Pack .claude wiring (CR-AIWS-2026-06-051) ----------

def wire_agent_pack_claude(project_root: Path, output: Path,
                           file_section_map: dict[str, str]) -> int:
    """Wire the AI Agents Pack's `.claude/` surfaces (CR-AIWS-2026-06-051).

    The agents package (product/agents/) ships whole to .ai-work/agents/ via the `agents`
    PAYLOAD_SECTION, but its slash-command + router-skill surfaces must ALSO reach the target's
    `.claude/`. Rather than a separate target, copy them into the existing payload/commands/ +
    payload/skills/ trees so the standard payload→.claude wiring carries them — nothing
    hand-copied, nothing to miss. A smoke-check fails the build if any pack verb is unwired.

    No-op (returns 0) when product/agents/ is absent — default build unchanged.
    """
    pack = project_root / "product" / "agents"
    if not pack.is_dir():
        return 0
    written = 0
    expected: list[str] = []
    # verb commands → payload/commands/ (→ target .claude/commands/)
    cmd_src = pack / "commands"
    if cmd_src.is_dir():
        cmd_dst = output / "payload" / "commands"
        cmd_dst.mkdir(parents=True, exist_ok=True)
        for md in sorted(cmd_src.glob("*.md")):
            if is_excluded(md):
                continue
            dst = cmd_dst / md.name
            shutil.copy2(md, dst)
            file_section_map[dst.relative_to(output).as_posix()] = "commands"
            expected.append(md.name)
            written += 1
    # router skill(s) → payload/skills/ (→ target .claude/skills/)
    sk_src = pack / "skills"
    if sk_src.is_dir():
        sk_dst = output / "payload" / "skills"
        for skill_dir in sorted(sk_src.iterdir()):
            if skill_dir.is_dir() and not is_excluded(skill_dir):
                f, _ = copy_tree_filtered(skill_dir, sk_dst / skill_dir.name)
                written += f
                for fp in walk_files(sk_dst / skill_dir.name):
                    file_section_map[fp.relative_to(output).as_posix()] = "skills"
    # smoke-check: every pack verb command must have landed a .claude wrapper
    wired = {p.name for p in (output / "payload" / "commands").glob("*.md")}
    missing = [c for c in expected if c not in wired]
    if missing:
        raise SystemExit(
            f"error: agent-pack wiring smoke-check failed — unwired verb commands: {missing}"
        )
    if expected:
        print(f"  [agent-pack wiring     ] {written} files → .claude (commands + router skill); "
              f"{len(expected)} verbs wired")
    return written


# ---------- Manifest / Changelog ----------

def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def walk_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out.append(p)
    return out


def build_manifest_text(payload_root: Path, version: str, date_str: str,
                        file_section_map: dict[str, str] | None = None) -> str:
    files = walk_files(payload_root)
    lines = [
        f"# MANIFEST — AI Work System MVP Install Package",
        f"**Version:** {version}",
        f"**Build date:** {date_str}",
        f"**Total files:** {len(files)}",
        "",
        "| File | Section | Lines |",
        "|------|---------|------:|",
    ]
    for f in files:
        rel = f.relative_to(payload_root.parent).as_posix()
        section = (file_section_map or {}).get(rel, "—")
        n = count_lines(f) if f.suffix in {".md", ".py", ".yml", ".yaml", ".jsonl", ".txt"} else 0
        lines.append(f"| {rel} | {section} | {n if n else '-'} |")
    return "\n".join(lines) + "\n"


def parse_manifest_file_list(manifest_path: Path) -> dict[str, tuple[str, int]]:
    """Extract {path: (section, lines)} from a MANIFEST.md built by this tool.
    Handles both old 2-column format (File, Lines) and new 3-column (File, Section, Lines).
    """
    out: dict[str, tuple[str, int]] = {}
    if not manifest_path.exists():
        return out
    in_table = False
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| File |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 3:
                path, section = parts[0], parts[1]
                lines_str = parts[2]
            elif len(parts) == 2:
                path, section = parts[0], "—"
                lines_str = parts[1]
            else:
                continue
            try:
                lines_n = int(lines_str) if lines_str not in ("-", "") else 0
            except ValueError:
                lines_n = 0
            out[path] = (section, lines_n)
        elif in_table and not line.strip():
            break
    return out


def _section_summary(data: dict[str, tuple[str, int]]) -> dict[str, set[str]]:
    """Group file paths by section name."""
    result: dict[str, set[str]] = {}
    for path, (section, _) in data.items():
        result.setdefault(section, set()).add(path)
    return result


def build_changelog_text(prev_pkg: Path, curr_pkg: Path, version: str) -> str:
    prev_manifest = parse_manifest_file_list(prev_pkg / "MANIFEST.md")
    curr_manifest = parse_manifest_file_list(curr_pkg / "MANIFEST.md")
    prev_files = set(prev_manifest.keys())
    curr_files = set(curr_manifest.keys())
    added = sorted(curr_files - prev_files)
    removed = sorted(prev_files - curr_files)
    updated = sorted(
        f for f in (curr_files & prev_files)
        if curr_manifest[f][1] != prev_manifest[f][1]
    )
    lines = [
        f"# CHANGELOG — AI Work System MVP Install Package",
        f"**New version:** {version}",
        f"**Previous package:** {prev_pkg.name}",
        "",
        f"## Summary",
        f"- Added:   {len(added)}",
        f"- Updated: {len(updated)}",
        f"- Removed: {len(removed)}",
        "",
    ]

    # Section-level summary
    prev_by_section = _section_summary(prev_manifest)
    curr_by_section = _section_summary(curr_manifest)
    all_sections = sorted(prev_by_section.keys() | curr_by_section.keys())
    if all_sections:
        lines.append("## Section Summary")
        lines.append("")
        lines.append("| Section | Added | Updated | Removed | Unchanged |")
        lines.append("|---------|------:|--------:|--------:|----------:|")
        for sec in all_sections:
            p = prev_by_section.get(sec, set())
            c = curr_by_section.get(sec, set())
            sec_added = len(c - p)
            sec_removed = len(p - c)
            sec_updated = sum(
                1 for f in (c & p)
                if curr_manifest[f][1] != prev_manifest[f][1]
            )
            sec_unchanged = len(c & p) - sec_updated
            lines.append(f"| {sec} | {sec_added} | {sec_updated} | {sec_removed} | {sec_unchanged} |")
        lines.append("")

    if added:
        lines.append("## Added")
        for f in added:
            lines.append(f"- `{f}` ({curr_manifest[f][1]} lines)")
        lines.append("")
    if updated:
        lines.append("## Updated")
        for f in updated:
            lines.append(f"- `{f}` ({prev_manifest[f][1]} → {curr_manifest[f][1]} lines)")
        lines.append("")
    if removed:
        lines.append("## Removed")
        for f in removed:
            lines.append(f"- `{f}` (was {prev_manifest[f][1]} lines)")
        lines.append("")
    if not (added or updated or removed):
        lines.append("_No file-level changes detected vs previous package._")
    return "\n".join(lines) + "\n"


# ---------- Generated docs ----------

README_TEMPLATE = """---
name: AI Work System MVP — Installable Package
version: {version}
package_date: {date}
target: any project adopting AI Work System MVP
---

# AI Work System MVP — Installable Package ({version})

Một package "drop-in" để cài **AI Work System MVP {version}** sang một dự
án khác. Bao gồm methodology spec, wiki operational guidance, các Claude
Code skill cho AIP/Wiki, cùng tooling Python (stdlib only) và templates
cần thiết để thực thi.

## Package layout

```
AI_Work_System_MVP_{version}_{date}/
├── README.md                   # file này
├── MANIFEST.md                 # file list + line counts (base cho changelog)
├── CHANGELOG.md                # có khi build với --prev
├── install_guide.md            # hướng dẫn Claude tự cài đặt
├── CLAUDE_SLIM_TEMPLATE.md     # slim CLAUDE.md template (~60 dòng) để wire vào dự án đích
└── payload/
    ├── methodology/            → .ai-work/truth/canonical/methodology/
    ├── wiki_guidelines/        → .ai-work/truth/canonical/wiki_guidelines/
    ├── skills/                 → .claude/skills/
    ├── commands/               → .claude/commands/
    ├── tooling/                → .ai-work/tooling/
    ├── aip_templates/          → .ai-work/aip/templates/
    ├── workspace_templates/    → .ai-work/workspace_templates/
    ├── preset_knowledge/       → .ai-work/preset_knowledge/
    ├── procedural/             → .ai-work/procedural/
    ├── truth_templates/        → .ai-work/truth/templates/
    ├── guidelines/             → .ai-work/guidelines/
    ├── aiws_wiki/              → .ai-work/wiki_sources/aiws_meta/ (+ index.aiws.jsonl at install)
    └── agents/                 → .ai-work/agents/ (+ .claude/ wrappers via agent-pack wiring; only if shipped)
```

## Cách dùng

Mở Claude Code tại dự án đích, rồi nói:

> "Hãy cài AI Work System MVP {version} vào dự án này theo
> `<đường-dẫn>/install_guide.md`."

Claude sẽ đọc `install_guide.md` và tự thực hiện các bước (pre-flight →
copy payload → init Truth placeholder → wire CLAUDE.md/CLAUDE.local.md
với slim template → smoke test → report).

## Những thứ KHÔNG nằm trong package (cố ý loại bỏ)

- `.ai-work/wiki/` — Wiki nội dung là tài sản dự án đích
- `.ai-work/wiki_sources/meta/` — Meta của artifact dự án nguồn
- `.ai-work/aip/exec|plans|local/`, `workspaces/`, `history/` — Runtime của dự án nguồn
- Truth files (SOP_MASTER / AI_WORK_CONTRACT / AIP_ROOT) — Phải do dự án đích tự viết
- `releases/`, `installable_packages/` — tránh recursive bloat
- Personal `*.local.md` files, backups, caches
- `methodology/00_brainstorming/` — brainstorming internal của AIWS project
- `methodology/90_delta_tracking/` — sprint backlogs, reviews, closure records — internal only
- `methodology/10_design/Detail_Design_MVP_Core_Artifacts.md` — excluded (internal only)
- `methodology/10_design/` (4 files còn lại) — **included nhưng stripped**: sections giải thích lý do thiết kế và AIWS design phases đã được loại bỏ; chỉ giữ lại operational conceptual/methodology/component knowledge
- `aip_templates/tracking/` — internal tracking files

## Yêu cầu hệ thống ở dự án đích
- Python 3.8+ (stdlib)
- Claude Code
- Không cần internet, không cần pip

## Build info
Package này được sinh tự động bởi `build_aiws_install_package.py` từ dự
án nguồn. Xem `MANIFEST.md` cho danh sách file + line counts.
"""


INSTALL_GUIDE_TEMPLATE = """---
name: AI Work System MVP {version} — Install Guide
audience: Claude Code (or any AI assistant) executing the install
target_layout: project root with `.ai-work/` and `.claude/skills/` + `.claude/commands/`
---

# Install Guide — AI Work System MVP {version}

> **Đọc kỹ trước khi chạy.** Đây là hướng dẫn để **bạn (Claude)** tự cài
> package này vào dự án đích. Người dùng chỉ cần trỏ bạn đến file này
> và xác nhận target project root.

## 0. Pre-conditions

Hỏi user **đúng 2 thứ** — không hỏi thêm gì khác:

1. **Target project root** — thư mục dự án đích (sẽ chứa `.ai-work/` và `.claude/`)
2. **Project name** — tên ngắn của dự án (dùng để điền `<PROJECT_NAME>` trong `CLAUDE_SLIM_TEMPLATE.md`)

**Mặc định — không hỏi user, xử lý tự động:**

| Tình huống | Hành động mặc định |
|---|---|
| `.ai-work/` hoặc `.claude/skills/` đã tồn tại | **Abort** — báo rõ path conflict, đợi user chỉ định |
| CLAUDE.md target | Dùng `CLAUDE.local.md` (personal, gitignored; an toàn cho member mới) |
| Wiki registration mode | Quick pointer — thêm block vào `CLAUDE.local.md`, không hỏi |

Yêu cầu môi trường:
- Python 3.8+ (kiểm tra ở Step 1)
- Quyền tạo folder trong target root

## 1. Pre-flight check

**Windows — refresh PATH trước khi check Python** (tránh false-negative sau khi mới cài Python chưa restart shell):

```powershell
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
python --version
```

Nếu Python không tìm thấy → báo user cài Python 3.8+ từ python.org rồi thử lại. Không tiếp tục.

Kiểm tra project root và conflict:

```bash
pwd   # phải là target project root
ls -la .ai-work 2>/dev/null && echo "EXISTS: .ai-work"
ls -la .claude/skills 2>/dev/null && echo "EXISTS: .claude/skills"
ls -la CLAUDE.md CLAUDE.local.md 2>/dev/null
```

Nếu có conflict → STOP, báo rõ, đợi user.

## 2. Payload mapping

| # | Source (trong package) | Destination (target project) |
|---|---|---|
| 1 | `payload/methodology/` | `.ai-work/truth/canonical/methodology/` |
| 2 | `payload/wiki_guidelines/` | `.ai-work/truth/canonical/wiki_guidelines/` |
| 3 | `payload/skills/` | `.claude/skills/` |
| 4 | `payload/tooling/` | `.ai-work/tooling/` |
| 5 | `payload/aip_templates/` | `.ai-work/aip/templates/` |
| 6 | `payload/workspace_templates/` | `.ai-work/workspace_templates/` |
| 7 | `payload/preset_knowledge/` | `.ai-work/preset_knowledge/` |
| 8 | `payload/procedural/` | `.ai-work/procedural/` |
| 9 | `payload/truth_templates/` | `.ai-work/truth/templates/` |
| 10 | `payload/guidelines/` | `.ai-work/guidelines/` |
| 11 | `payload/wiki_source_profiles/` | `.ai-work/wiki_sources/profiles/` **(MERGE — never overwrite project profiles; see §3 note)** |
| 12 | `payload/commands/` | `.claude/commands/` |
| 13 | `payload/aiws_wiki/` | `.ai-work/wiki_sources/aiws_meta/` (rồi build `index.aiws.jsonl` — Step 4) |
| 14 | `payload/agents/` | `.ai-work/agents/` **(chỉ khi package có `agents/`; + wire `.claude/commands/aiws-agent-*` + `.claude/skills/aiws-agent/` đã nằm sẵn trong `payload/commands` + `payload/skills`)** |

## 3. Install — copy payload

> **Tip:** Thay vì chạy thủ công, hãy dùng skill `/init-project` trong package
> (`payload/skills/init-project/SKILL.md`) — skill sẽ tự động thực hiện tất cả
> các bước bên dưới và wire CLAUDE.local.md.

```bash
PKG="<absolute-path-to-this-package>"
DEST="$(pwd)"

mkdir -p "$DEST/.ai-work/truth/canonical/methodology"
mkdir -p "$DEST/.ai-work/truth/canonical/wiki_guidelines"
mkdir -p "$DEST/.ai-work/tooling"
mkdir -p "$DEST/.ai-work/aip/templates"
mkdir -p "$DEST/.ai-work/aip/plans"
mkdir -p "$DEST/.ai-work/aip/exec"
mkdir -p "$DEST/.ai-work/aip/local"
mkdir -p "$DEST/.ai-work/workspace_templates"
mkdir -p "$DEST/.ai-work/workspaces"
mkdir -p "$DEST/.ai-work/procedural"
mkdir -p "$DEST/.ai-work/preset_knowledge"
mkdir -p "$DEST/.ai-work/truth/templates"
mkdir -p "$DEST/.ai-work/guidelines"
mkdir -p "$DEST/.ai-work/wiki_sources"
mkdir -p "$DEST/.ai-work/wiki_sources/aiws_meta"
mkdir -p "$DEST/.ai-work/wiki"
mkdir -p "$DEST/.ai-work/history/trail"
mkdir -p "$DEST/.ai-work/history/evidence"
mkdir -p "$DEST/.ai-work/history/archive"
mkdir -p "$DEST/.claude/skills"
mkdir -p "$DEST/.claude/commands"
[ -d "$PKG/payload/agents" ] && mkdir -p "$DEST/.ai-work/agents"

cp -r "$PKG/payload/methodology/."          "$DEST/.ai-work/truth/canonical/methodology/"
cp -r "$PKG/payload/wiki_guidelines/."      "$DEST/.ai-work/truth/canonical/wiki_guidelines/"
cp -r "$PKG/payload/skills/."               "$DEST/.claude/skills/"
cp -r "$PKG/payload/commands/."             "$DEST/.claude/commands/"
cp -r "$PKG/payload/tooling/."              "$DEST/.ai-work/tooling/"
cp -r "$PKG/payload/aip_templates/."        "$DEST/.ai-work/aip/templates/"
cp -r "$PKG/payload/workspace_templates/."  "$DEST/.ai-work/workspace_templates/"
cp -r "$PKG/payload/preset_knowledge/."     "$DEST/.ai-work/preset_knowledge/"
cp -r "$PKG/payload/procedural/."           "$DEST/.ai-work/procedural/"
cp -r "$PKG/payload/truth_templates/."      "$DEST/.ai-work/truth/templates/"
cp -r "$PKG/payload/guidelines/."           "$DEST/.ai-work/guidelines/"
cp -r "$PKG/payload/aiws_wiki/."              "$DEST/.ai-work/wiki_sources/aiws_meta/"
# AI Agents Pack (only if shipped) — body → .ai-work/agents/; its .claude wrappers + router skill
# already ride payload/commands/ + payload/skills/ above (wired at build by wire_agent_pack_claude).
[ -d "$PKG/payload/agents" ] && cp -r "$PKG/payload/agents/."  "$DEST/.ai-work/agents/"

# wiki_source_profiles are PROJECT-OWNED — content-level MERGE (never overwrite); skips project_stopwords.yml (CR-AIWS-2026-06-047)
python "$DEST/.ai-work/tooling/merge_wiki_source_profiles.py" --from "$PKG/payload/wiki_source_profiles" --into "$DEST/.ai-work/wiki_sources/profiles" --apply
```

> **wiki_source_profiles are project-owned (CR-AIWS-2026-06-047).** They are **merged**, not
> `cp -r`-overwritten: a profile the project already customized keeps its values / comments /
> `extra_stopwords`; only canonical top-level keys it is **missing** are added. `project_stopwords.yml`
> is **project-authored** — neither shipped nor written by the install. The merge is done by the
> shipped `merge_wiki_source_profiles.py` (run above, after `tooling/` is copied).

## 4. Init Truth placeholders

```bash
touch "$DEST/.ai-work/truth/SOP_MASTER.md"
touch "$DEST/.ai-work/truth/AI_WORK_CONTRACT.md"
touch "$DEST/.ai-work/truth/AIP_ROOT.md"
: > "$DEST/.ai-work/wiki_sources/index.jsonl"
echo "[]" > "$DEST/.ai-work/wiki_sources/index.local.sources.json"

# Build the pre-built AIWS wiki index (searchable `aiws` namespace) from the shipped, rebased metas.
# Run from $DEST so build_wiki_source_index.py resolves the project root correctly.
( cd "$DEST" && python .ai-work/tooling/build_wiki_source_index.py --scope project \
    --meta-dir .ai-work/wiki_sources/aiws_meta \
    --out .ai-work/wiki_sources/index.aiws.jsonl )
```

> `index.jsonl` (dự án tự) để rỗng — sẽ đầy khi chạy `/build-project-wiki`. `index.aiws.jsonl`
> (kiến thức AIWS) build sẵn ngay → AI tra cứu được ngay sau cài (default scope `project,aiws` đã gồm aiws).

Hỏi user: muốn Claude draft 3 file Truth từ AIP templates trong
`.ai-work/aip/templates/` không? **KHÔNG tự bịa nội dung Truth.**

## 5. Wire CLAUDE.md / CLAUDE.local.md (SLIM mode)

**Phương châm: slim** — chỉ giữ rules hot và common. Chi tiết → pointers.

### 5.1. Xác định target file
- Dựa theo quyết định ở Pre-conditions: `CLAUDE.md` hoặc `CLAUDE.local.md` (default local).
- Nếu file đã tồn tại:
  1. `grep -q "AI Work System MVP" <file>` → nếu có → hỏi: replace / skip / abort
  2. Backup: `cp <file> "<file>.bak-$(date +%Y%m%d-%H%M%S)"`
  3. **Append** slim block ở cuối file (không ghi đè nội dung cũ)
- Nếu chưa tồn tại: tạo mới với slim block

### 5.2. Substitute + inject
Đọc `CLAUDE_SLIM_TEMPLATE.md` ở root package, thay placeholder:

| Placeholder | Giá trị |
|---|---|
| `<PROJECT_NAME>` | tên dự án đích (hỏi user) |
| `<YYYY-MM-DD>` | ngày hôm nay |

Ghi vào target file.

### 5.3. Verify
```bash
grep -n "AI Work System MVP" <file>   # ≥ 1 match
```

## 5.5 — Đăng ký AIWS knowledge vào wiki (Quick pointer — mặc định tự động)

Thêm block sau vào cuối `CLAUDE.local.md` — **không hỏi user, thực hiện luôn**:

```markdown
## AIWS Knowledge Sources (installed)

Khi user hỏi về AI Work System hoặc cần tạo AIP template → tìm trong các source sau:

- **Methodology** — `.ai-work/truth/canonical/methodology/`
  Dùng khi: câu hỏi về AIWS design, spec, khái niệm, SOP flow
- **Wiki Guidelines** — `.ai-work/truth/canonical/wiki_guidelines/`
  Dùng khi: câu hỏi về Knowledge Hub, wiki source, wiki meta, canonical guideline
- **Preset Knowledge** — `.ai-work/preset_knowledge/`
  Dùng khi: tạo AIP mới — tìm AIP exec template hoặc sample phù hợp
  Nav: `aip_exec/` (exec templates), `aip_samples/` (samples), `AIP_SELECTION_GUIDE.md`
```

> **Searchable wiki AIWS đã có sẵn:** Step 4 đã build `index.aiws.jsonl` từ các meta AIWS
> ship kèm → AI tra cứu ngay bằng `python .ai-work/tooling/lookup_wiki_source.py --query <kw>`
> (default scope = `project,aiws` → aiws reachable mặc định, không cần `--scope`; CR-AIWS-2026-06-052).
> `local` index là opt-in + authorization-gated (`--scope project,local --authorized human`, rule #11).
> Block pointer ở trên chỉ là fallback dễ đọc cho người — không còn phải chạy
> `/build-wiki-source-meta` thủ công cho kiến thức AIWS.

---

## 6. Smoke test

```bash
python .ai-work/tooling/lint_all.py --help
python .ai-work/tooling/lookup_wiki_source.py --query methodology || true
ls .claude/skills/
```

## 7. Report

```
✅ AI Work System MVP {version} installed at: <DEST>

Copied:
- methodology → .ai-work/truth/canonical/methodology/
- wiki_guidelines → .ai-work/truth/canonical/wiki_guidelines/
- skills (N) → .claude/skills/
- commands → .claude/commands/
- tooling → .ai-work/tooling/
- aip_templates → .ai-work/aip/templates/
- workspace_templates → .ai-work/workspace_templates/
- preset_knowledge → .ai-work/preset_knowledge/
- procedural → .ai-work/procedural/
- aiws_wiki → .ai-work/wiki_sources/aiws_meta/ (+ index.aiws.jsonl built)

Wired:
- <CLAUDE.md | CLAUDE.local.md> → <created | appended>

Empty placeholders (you must fill):
- .ai-work/truth/SOP_MASTER.md
- .ai-work/truth/AI_WORK_CONTRACT.md
- .ai-work/truth/AIP_ROOT.md

AIWS knowledge: searchable by default (scope project,aiws; index.aiws.jsonl built) + CLAUDE.local.md pointer fallback

Smoke test: <PASS | WARN: ...>

Next:
  1. Viết Truth → /create-aip → /run-aip → /lint-all
  2. (nếu chưa wire knowledge) xem Step 5.5 trong install_guide.md
```

## 8. Rules cho install AI

- **KHÔNG ghi đè** file đã tồn tại mà chưa hỏi user
- **KHÔNG sửa** nội dung methodology hoặc wiki_guidelines khi copy
- **KHÔNG tự bịa** Truth (SOP/Contract/AIP_ROOT)
- **KHÔNG copy** workspaces/, history/, wiki/ (không có sẵn, cố ý)
- **Stop và hỏi** khi gặp conflict, ambiguity, hoặc pre-flight fail
- Sau install, gợi ý user chạy `/lint-all` để verify
"""


START_HERE_TEMPLATE = """# START HERE — AI Work System MVP {version}

Tham khảo file này để cài đặt hoặc nâng cấp AI Work System nhanh nhất.

---

## Cài mới (fresh project)

Mở **Claude Code** tại project đích, paste prompt sau:

```
Hãy cài AI Work System MVP {version} vào dự án này.
Package nằm tại: <điền đường dẫn tuyệt đối đến folder này>
Đọc install_guide.md và làm theo từng bước.
```

## Nâng cấp (đã có AIWS)

```
Hãy nâng cấp AI Work System lên {version}.
Package mới nằm tại: <điền đường dẫn tuyệt đối đến folder này>
Dùng skill /update-aiws-package.
```

---

**Files trong package:**
- `install_guide.md` — hướng dẫn chi tiết từng bước cài mới
- `CLAUDE_SLIM_TEMPLATE.md` — template CLAUDE.local.md cho project mới
- `MANIFEST.md` — danh sách đầy đủ tất cả file trong payload
- `CHANGELOG.md` — thay đổi so với bản trước (nếu có)
- `payload/` — toàn bộ nội dung cần cài

**Skills trong package:** skills/ (17 skills — xem payload/skills/)
"""


CLAUDE_SLIM_TEMPLATE = """# CLAUDE.md — <PROJECT_NAME>

Persistent project context. Read first in a new session.

## What this project is
<1-2 câu mô tả project — điền sau khi install>. Adopted **AI Work System MVP {version}** as working methodology (since <YYYY-MM-DD>). Live tree ở `.ai-work/` tại project root.

## Adopted canonical knowledge

- **Methodology:** [AI Work System MVP](.ai-work/truth/canonical/methodology/) — `source_of_truth`, `authoritative`. Override mọi `curated`/`reference`/`history` trên conflict.
- **Wiki operational guidance:** [Wiki Guideline Package + deltas](.ai-work/truth/canonical/wiki_guidelines/) — complement methodology. Trên conflict với spec, **spec wins**. Nav: [.ai-work/wiki/reference/wiki-guidelines.md](.ai-work/wiki/reference/wiki-guidelines.md).
- **Project Truth:** [SOP_MASTER](.ai-work/truth/SOP_MASTER.md), [AI_WORK_CONTRACT](.ai-work/truth/AI_WORK_CONTRACT.md), [AIP_ROOT](.ai-work/truth/AIP_ROOT.md).

Rule mơ hồ → spec wins trừ khi có Approved Deviation trong `AI_WORK_CONTRACT.md`.

## Core concepts
- **Truth** (`.ai-work/truth/`) — authoritative, no silent rewrite.
- **AIP** (`.ai-work/aip/` — ROOT/PLAN/EXEC/LOCAL) — **stable macro-control**, không phải runtime notebook.
- **Workspace** (`.ai-work/workspaces/<task-id>/`) — runtime execution memory (findings, draft, capture, final output).
- **Wiki** (`.ai-work/wiki/`) — curated knowledge (domain/function/module/data/pattern/reference).
- **History** (`.ai-work/history/`) — trail/evidence/archive.

**Precedence:** Truth → Project Wiki → Local Wiki → Common Wiki → History (content) · SOP → Contract → AIP_ROOT → AIP_PLAN/EXEC → Guidelines → Skills → Wiki → Workspace (artifact). Knowledge classes: `source_of_truth` → `curated` → `reference` → `history`.

## Hot operational rules (MUST follow)

1. **Wiki Source lookup FIRST** — khi user hỏi về concept thuộc canonical knowledge của dự án: chạy `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>` trước, đọc primary MD meta, mở chapter/spec nếu cần.
   - **Match need → tool (3 shapes):** FIND 1 doc = `lookup --query`; ENUMERATE one kind (mọi function/table) = `lookup --source-type <type> --slim`; TRAVERSE ("node liên quan gì / ai phụ thuộc") = `wiki_relations.py --relations <id>`. **Chain rule:** `wiki_relations` cần `source_id` (output của `lookup`) — không bắt đầu ở relations khi chưa có id.
   - ❌ **Đừng `Read` nguyên `index.jsonl`/`relations.jsonl`** để enumerate — dùng `--source-type --slim` / `wiki_relations` / grep.
   - **Index miss → bắt buộc escalate:** retry `--mode semantic`, rồi raw Glob/Grep trong artifact dirs tool hint chỉ ra; không im lặng báo "không tìm thấy" sau 1 lần fail.
2. **Never read PDF/DOCX binaries** — follow `companion_of` pointer trong meta về primary MD.
3. **Runtime state lives in Workspace**, không bao giờ trong AIP body (findings/metrics/progress/decisions/draft → workspace files, không phải AIP sections).
4. **No silent drift from AIP** — đổi scope/output/objective phải thêm dated entry vào Re-plan Log; không edit earlier sections silently.
5. **No silent rewrite of Truth hoặc official Wiki** — candidate → review → apply.
6. **Capture first, curate later** — unknowns đi vào `08_capture_inbox.jsonl`, không đi thẳng vào wiki.
7. **SOP first** — task ngoài scope SOP/AIP_ROOT phải confirm với user.
8. **Lint là guardrail, không phải reviewer** — không ask tools auto-fix wiki/truth.
9. **`wiki_first` là default behavior**, không bắt buộc. Override chỉ qua explicit HUMAN/rule/AIP instruction; ambiguous → **clarify, không tự suy đoán**. Chi tiết + conflict rules: [wiki-guidelines.md](.ai-work/wiki/reference/wiki-guidelines.md).

## AIP stability rules (CRITICAL)

AIP là stable control artifact (AIP_Detail_Spec §2.3/§10/§11). Vi phạm biến AIP thành live working file — explicitly forbidden.

- ❌ **Never tick `[x]` trong Done Criteria** — declarative criteria, không phải progress checklist.
- ❌ **Never embed runtime metrics** trong AIP (counts, findings, decisions discovered during execution). Thuộc về `04_findings.md`.
- ❌ **Never silently edit earlier sections** để phản ánh scope change. Append Re-plan Log entry TRƯỚC khi edit.
- ❌ **`updated_at` không phải last-touched timestamp** — chỉ bump khi update-by-exception thực sự (§10.1).
- ✅ Allowed updates: objective / scope / expected outputs / major assumptions / explicit re-plan — mỗi update bắt buộc có Re-plan Log entry.
- Linter (`lint_aip.py`) bắt `live_working_file`, `runtime_metric_in_aip`, missing sections. **Treat warnings as errors during review.**

## Execution protocol

Trước khi thực hiện bất kỳ non-trivial task nào (review, analysis, implementation, investigation...) — nếu chưa có AIP, phải chạy `/create-aip` trước. Sau đó `/run-aip` để wire workspace. Không được làm thẳng trong chat. Làm việc trong workspace files, KHÔNG trong AIP. `/lint-all` trước khi finalize. Flow chi tiết: [.claude/skills/run-aip/SKILL.md](.claude/skills/run-aip/SKILL.md).

**Không cần AIP:** Ad hoc Q&A, câu hỏi đơn lẻ, tra cứu nhanh, research ngắn → trả lời thẳng trong chat.

## Tooling & Skills — pointers

- **Tooling** [.ai-work/tooling/](.ai-work/tooling/) — Python stdlib, no `pip install`. Full catalog: [README](.ai-work/tooling/README.md).
  - Find a document: `python .ai-work/tooling/lookup_wiki_source.py --query <keyword>`.
  - Find a source's relations (declared edges — one-hop, out + IN): `python .ai-work/tooling/wiki_relations.py --relations <id>`.
- **Skills** [.claude/skills/](.claude/skills/) — `/create-aip`, `/run-aip`, `/init-workspace`, `/init-project`, `/point-step`, `/build-active-step-context`, `/build-wiki-source-meta`, `/lookup-wiki-source`, `/refresh-wiki-source-meta`, `/lint-all`. Mỗi skill có SKILL.md riêng.
- **Spec reference:** [Methodology](.ai-work/truth/canonical/methodology/) · [Wiki Guidelines](.ai-work/truth/canonical/wiki_guidelines/).

## Notes
- Python stdlib only. No `pip install`.
- Windows: tools force UTF-8 stdout (cp932-safe).
- User language: <điền preference — mặc định Vietnamese + English mixed>.
- Always work from project root (nơi `.ai-work/` sits).
"""


# ---------- Main ----------


def _release_sort_key(name: str) -> tuple:
    """Sort key for release folder names AI_Work_System_MVP_<version>_<YYYY-MM-DD>.
    Orders by SEMANTIC version, with the date as tiebreak. A plain name sort ranks
    'v0.9_...' ABOVE 'v0.9.26_...' because '_' (0x5F) > '.' (0x2E), which made
    prev auto-detect pick a stale release. Handles letter-suffixed patches (v0.9.23b)."""
    stem = name[len("AI_Work_System_MVP_"):] if name.startswith("AI_Work_System_MVP_") else name
    m = re.match(r"^v?(.+?)_(\d{4}-\d{2}-\d{2})$", stem)
    ver_str, date_str = (m.group(1), m.group(2)) if m else (stem.lstrip("v"), "")
    comps: list[tuple] = []
    for part in ver_str.split("."):
        pm = re.match(r"^(\d+)([A-Za-z]*)$", part)
        comps.append((int(pm.group(1)), pm.group(2)) if pm else (0, part))
    return (comps, date_str)


def build(version: str, output: Path, prev: Path | None, project_root: Path,
          date_str: str) -> int:
    if output.exists():
        print(f"error: output already exists: {output}", file=sys.stderr)
        return 2

    print(f"building AI Work System MVP install package")
    print(f"  version: {version}")
    print(f"  project root: {project_root}")
    print(f"  output: {output}")

    output.mkdir(parents=True)
    payload_root = output / "payload"
    payload_root.mkdir()

    total_files = 0
    section_report: list[tuple[str, int]] = []
    file_section_map: dict[str, str] = {}

    for sec in PAYLOAD_SECTIONS:
        src = project_root / sec.src_rel
        dst = output / sec.dst_rel
        if not src.exists():
            print(f"  ! skip {sec.name}: source missing ({src})")
            section_report.append((sec.name, 0))
            continue
        exclude_names = sec.exclude_subdirs | sec.exclude_files
        exclude_abs = frozenset(src / nm for nm in exclude_names) if exclude_names else None
        files, _ = copy_tree_filtered(src, dst, exclude_abs)
        total_files += files
        section_report.append((sec.name, files))
        print(f"  [{sec.name:22}] {files:4} files")
        # Record section for each copied file (for MANIFEST Section column)
        if dst.exists():
            for f in walk_files(dst):
                rel = f.relative_to(output).as_posix()
                file_section_map[rel] = sec.name

    # Strip-and-copy design docs: 10_design/ is excluded from the main loop but
    # selected files are copied here with AIWS-internal sections removed.
    stripped_count = 0
    for src_rel in DESIGN_DOCS_STRIP_COPY:
        src = project_root / src_rel
        if not src.exists():
            print(f"  ! skip design strip-copy: source missing ({src_rel})")
            continue
        rel_under_methodology = Path(src_rel).relative_to(
            "product/methodology/ai_work_system"
        )
        dst = output / "payload" / "methodology" / rel_under_methodology
        dst.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding="utf-8", errors="replace")
        headings = DESIGN_STRIP_HEADINGS.get(src_rel, [])
        stripped = strip_design_sections(content, headings)
        dst.write_text(stripped, encoding="utf-8")
        file_section_map[dst.relative_to(output).as_posix()] = "methodology"
        total_files += 1
        stripped_count += 1
    if stripped_count:
        print(f"  [design docs (stripped)] {stripped_count} files (internal sections removed)")

    # Ship the pre-built AIWS wiki bundle (rebased metas) as the `aiws` namespace (CR-040).
    total_files += build_aiws_wiki_bundle(project_root, output, file_section_map)

    # Wire the AI Agents Pack .claude surfaces (CR-AIWS-2026-06-051) — no-op if product/agents/ absent.
    total_files += wire_agent_pack_claude(project_root, output, file_section_map)

    for src_rel, dst_rel in EXTRA_SINGLE_FILES:
        src = project_root / src_rel
        if src.exists():
            dst = output / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            total_files += 1

    start_here_path = output / "START_HERE.md"
    start_here_path.write_text(
        START_HERE_TEMPLATE.format(version=version),
        encoding="utf-8",
    )

    readme_path = output / "README.md"
    readme_path.write_text(
        README_TEMPLATE.format(version=version, date=date_str),
        encoding="utf-8",
    )

    guide_path = output / "install_guide.md"
    guide_path.write_text(
        INSTALL_GUIDE_TEMPLATE.format(version=version),
        encoding="utf-8",
    )

    slim_path = output / "CLAUDE_SLIM_TEMPLATE.md"
    slim_path.write_text(CLAUDE_SLIM_TEMPLATE.format(version=version), encoding="utf-8")

    manifest_path = output / "MANIFEST.md"
    manifest_path.write_text(
        build_manifest_text(payload_root, version, date_str, file_section_map),
        encoding="utf-8",
    )

    if prev is not None:
        if not (prev / "MANIFEST.md").exists():
            print(f"  ! prev package has no MANIFEST.md, skipping changelog: {prev}")
        else:
            changelog_path = output / "CHANGELOG.md"
            changelog_path.write_text(
                build_changelog_text(prev, output, version),
                encoding="utf-8",
            )
            print(f"  [changelog           ] written vs {prev.name}")

    print(f"\n  total payload files: {total_files}")
    print(f"  package root:        {output}")
    print(f"  START_HERE.md, README.md, MANIFEST.md, install_guide.md, CLAUDE_SLIM_TEMPLATE.md written")

    # Guard: warn if any output file has a name that may cause unzip errors on Windows
    long_name_files = [f for f in walk_files(output) if len(f.name) > 100]
    if long_name_files:
        print(f"\n  WARNING: {len(long_name_files)} file(s) with filename > 100 chars (may cause Windows unzip errors):")
        for f in long_name_files[:5]:
            print(f"    {f.relative_to(output).as_posix()} ({len(f.name)} chars)")
        if len(long_name_files) > 5:
            print(f"    ... and {len(long_name_files) - 5} more")

    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--override-version", help="Override the pinned version — TRIAL/EPHEMERAL builds only "
                                              "(quick_install). Official builds omit this and read "
                                              "product/aiws_version.md.")
    p.add_argument("--output", help="Output folder (default: releases/AI_Work_System_MVP_<version>_<date>)")
    p.add_argument("--prev", help="Previous package folder for changelog (auto-detected from releases/ if omitted)")
    p.add_argument("--no-prev", action="store_true", help="Skip changelog even if a previous package is found")
    p.add_argument("--project-root", help="Project root (default: auto-detect ancestor with .ai-work/)")
    args = p.parse_args(argv)

    start = Path(args.project_root) if args.project_root else Path.cwd()
    try:
        project_root = find_ai_work_root(start)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    # Version is pinned in product/aiws_version.md (single source of truth) so
    # every official build is identical. --override-version is the trial-only escape.
    if args.override_version:
        version, date_str = args.override_version, today()
    else:
        try:
            version, pinned_date = read_pinned_version(project_root)
        except SystemExit as e:
            print(str(e), file=sys.stderr)
            return 2
        date_str = pinned_date or today()

    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = project_root / output
    else:
        output = project_root / "releases" / f"AI_Work_System_MVP_{version}_{date_str}"

    prev = None
    if args.prev:
        prev = Path(args.prev)
        if not prev.is_absolute():
            prev = project_root / prev
        if not prev.is_dir():
            print(f"error: --prev not found: {prev}", file=sys.stderr)
            return 2
    elif not args.no_prev:
        # Auto-detect: find latest AI_Work_System_MVP_* folder in releases/
        releases_dir = project_root / "releases"
        if releases_dir.is_dir():
            candidates = sorted(
                [d for d in releases_dir.iterdir()
                 if d.is_dir() and d.name.startswith("AI_Work_System_MVP_") and d != output],
                key=lambda d: _release_sort_key(d.name),
            )
            if candidates:
                prev = candidates[-1]
                print(f"  (auto-detected previous package: {prev.name})")

    # Official (pinned) build whose folder already exists = the pinned version is
    # already released. Point the user at the fix instead of a bare "already exists".
    if not args.override_version and output.exists():
        print(f"  hint: {version} ({date_str}) is already released. Bump 'aiws_version' "
              f"(and 'release_date') in {VERSION_PIN_REL} to cut a new version.",
              file=sys.stderr)

    return build(version, output, prev, project_root, date_str)


if __name__ == "__main__":
    sys.exit(main())
