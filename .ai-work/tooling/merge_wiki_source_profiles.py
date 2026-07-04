#!/usr/bin/env python3
"""Merge canonical wiki_source_profiles into a project's profiles dir WITHOUT overwriting.

CR-AIWS-2026-06-047: wiki_source_profiles are PROJECT-OWNED. Installs/updates must never
clobber a project's profiles or its project-generic stopwords. This tool does a content-level,
comment-preserving merge per profile:

  - Project lacks the profile        -> copy the canonical profile verbatim.
  - Project already has the profile  -> ADD only the canonical top-level keys the project is
                                        missing (appended, attached doc-comment included); every
                                        existing project line (values, comments, extra_stopwords)
                                        is left untouched. No project key is removed/overwritten.
  - project_stopwords.yml            -> NEVER written/created (project authors it; the stopword
                                        mechanism reads it if present).
  - non-profile files (e.g. README.md) -> add-only: copied if absent, never overwritten.

Top-level-key parsing is textual (no YAML round-trip) so profile comments/formatting survive.
Deterministic output. Python stdlib only (cp932-safe stdout via _common when co-located).

Usage:
    python merge_wiki_source_profiles.py --from <canonical_profiles_dir> \\
        --into <project_profiles_dir> [--apply]

Without --apply: dry-run (prints per-profile plan, writes nothing).
Exit codes: 0 OK, 2 error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:  # side effect: forces UTF-8 stdout (cp932-safe) when _common is co-located in tooling/
    from _common import today  # noqa: F401
except Exception:  # standalone (e.g. unit test off-tree) — stdlib is enough
    pass

# project_stopwords.yml is project-authored term-data — NEVER shipped or written (CR-047 Change C).
NEVER_WRITE = frozenset({"project_stopwords.yml"})

_TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:")


def _top_level_keys(text: str) -> list[tuple[str, int]]:
    """Ordered (key_name, line_index) for every top-level (column-0) `key:` line."""
    out: list[tuple[str, int]] = []
    for i, line in enumerate(text.splitlines()):
        m = _TOP_KEY_RE.match(line)
        if m:
            out.append((m.group(1), i))
    return out


def _doc_comment_start(lines: list[str], key_line: int) -> int:
    """Walk upward from key_line over a contiguous run of comment lines (no blank gap) so a
    key's doc-comment travels with it. Returns the first line index of the attached block."""
    j = key_line
    while j - 1 >= 0 and lines[j - 1].strip().startswith("#"):
        j -= 1
    return j


def split_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (preamble, [(key, block_text), ...]). Each block = the key's attached doc-comment +
    key line + its body, up to (excluding) the next key's attached doc-comment. `preamble` is the
    file-level header before the first key's block."""
    lines = text.splitlines()
    keys = _top_level_keys(text)
    if not keys:
        return text, []
    starts = [_doc_comment_start(lines, kl) for (_, kl) in keys]
    preamble = "\n".join(lines[: starts[0]])
    blocks: list[tuple[str, str]] = []
    for idx, (name, _) in enumerate(keys):
        beg = starts[idx]
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        blocks.append((name, "\n".join(lines[beg:end])))
    return preamble, blocks


def _ensure_nl(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def merge_profile_text(canonical: str, project: str) -> str:
    """Append canonical top-level keys missing from `project`; preserve all project lines.
    Deterministic. Returns project unchanged (newline-normalised) when nothing is missing."""
    proj_keys = {k for (k, _) in _top_level_keys(project)}
    _, can_blocks = split_blocks(canonical)
    missing = [block for (name, block) in can_blocks if name not in proj_keys]
    if not missing:
        return _ensure_nl(project)
    base = project.rstrip("\n")
    added = "\n\n".join(b.rstrip("\n") for b in missing)
    return base + "\n\n" + added + "\n"


def merge_dir(src: Path, dst: Path, apply: bool) -> tuple[int, list[tuple[str, str]]]:
    """Merge every canonical profile in `src` into `dst`. Returns (rc, report) where report is a
    list of (filename, action). Writes only when apply=True."""
    report: list[tuple[str, str]] = []
    if not src.is_dir():
        print(f"error: --from is not a directory: {src}", file=sys.stderr)
        return 2, report
    if apply:
        dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.iterdir()):
        if not f.is_file():
            continue
        name = f.name
        if name in NEVER_WRITE:
            report.append((name, "skip (project-owned — never written)"))
            continue
        target = dst / name
        if f.suffix in (".yml", ".yaml"):
            canonical = f.read_text(encoding="utf-8", errors="replace")
            if not target.exists():
                report.append((name, "add (new — verbatim)"))
                if apply:
                    target.write_text(_ensure_nl(canonical), encoding="utf-8")
            else:
                project = target.read_text(encoding="utf-8", errors="replace")
                merged = merge_profile_text(canonical, project)
                proj_keys = {k for (k, _) in _top_level_keys(project)}
                added_keys = [k for (k, _) in _top_level_keys(canonical) if k not in proj_keys]
                if not added_keys:
                    report.append((name, "merge (no missing keys — preserved)"))
                else:
                    report.append((name, f"merge (+keys: {', '.join(added_keys)})"))
                    if apply and merged != project:
                        target.write_text(merged, encoding="utf-8")
        else:
            # non-profile (e.g. README.md): add-only, never overwrite a project file
            if not target.exists():
                report.append((name, "add (new — verbatim)"))
                if apply:
                    target.write_text(f.read_text(encoding="utf-8", errors="replace"),
                                      encoding="utf-8")
            else:
                report.append((name, "keep (exists — not overwritten)"))
    return 0, report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="src", required=True,
                   help="Canonical profiles dir (e.g. <pkg>/payload/wiki_source_profiles)")
    p.add_argument("--into", dest="dst", required=True,
                   help="Project profiles dir (e.g. .ai-work/wiki_sources/profiles)")
    p.add_argument("--apply", action="store_true",
                   help="Write the merge (default: dry-run — print plan, write nothing)")
    args = p.parse_args(argv)

    src, dst = Path(args.src), Path(args.dst)
    rc, report = merge_dir(src, dst, args.apply)
    if rc != 0:
        return rc
    mode = "apply" if args.apply else "dry-run"
    print(f"merge_wiki_source_profiles [{mode}]  {src}  ->  {dst}")
    for name, action in report:
        print(f"  {name:28} {action}")
    if not report:
        print("  (no profile files found in --from)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
