#!/usr/bin/env python3
"""One-shot driver: build Wiki Source Metas for any adopted canonical package.

Walks every *.md under a package root directory and creates a primary
Wiki Source Meta per file. Source ids are stable:

    <prefix>-<version>-<relative-slug>-<short-hash>

Default `--source-type` is `methodology_spec` and default `--id-prefix`
is `SRC-METHOD` so that legacy invocations for the methodology tree
keep working unchanged. Pass `--source-type` / `--id-prefix` to target
a different canonical package (e.g. wiki_guideline / SRC-WIKIGUIDE).

Run (methodology example):
    python .ai-work/tooling/build_canonical_package_metas.py \
        --root .ai-work/truth/canonical/methodology/ai_work_system_v0_3 \
        --profile .ai-work/wiki_sources/profiles/methodology_spec.yml

Run (wiki guideline example):
    python .ai-work/tooling/build_canonical_package_metas.py \
        --root .ai-work/truth/canonical/wiki_guidelines/Wiki_Guideline_Package_MVP_v0_1 \
        --profile .ai-work/wiki_sources/profiles/wiki_guideline.yml \
        --meta-dir .ai-work/wiki_sources/meta/wiki_guidelines \
        --source-type wiki_guideline \
        --id-prefix SRC-WIKIGUIDE
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_ai_work_root  # noqa: E402

SLUG_RE = re.compile(r"[^A-Za-z0-9]+")


def slugify(text: str, fallback: str = "x") -> str:
    s = SLUG_RE.sub("-", text).strip("-").lower()
    return s or fallback


def short_hash(text: str, length: int = 4) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def build_source_id(version: str, rel_path: Path, prefix: str = "SRC-METHOD") -> str:
    slug = slugify(str(rel_path).replace("\\", "/"))
    h = short_hash(str(rel_path))
    ver = slugify(version)
    return f"{prefix}-{ver}-{slug}-{h}"[:150]


def main() -> int:
    p = argparse.ArgumentParser(
        description="Build Wiki Source Metas for a methodology-like tree "
                    "(methodology spec, wiki guideline package, etc.)"
    )
    p.add_argument("--root", required=True, help="package root directory")
    p.add_argument("--profile", required=True)
    p.add_argument("--meta-dir", help="Override meta output dir")
    p.add_argument("--source-type", default="methodology_spec",
                   help="Source type to record in each meta (default: methodology_spec)")
    p.add_argument("--id-prefix", default="SRC-METHOD",
                   help="Source id prefix (default: SRC-METHOD)")
    p.add_argument("--with-related-sources", action="store_true",
                   help="Emit the '## Related Sources' scaffold per meta (opt-in). "
                        "Default: suppressed, so bulk reference-doc registration is "
                        "lint-clean (no meta_related_sources_todo warnings) without a "
                        "post-build strip (CAP-091-01).")
    ns = p.parse_args()

    root = Path(ns.root).resolve()
    profile = Path(ns.profile).resolve()
    if not root.is_dir():
        print(f"error: root not found: {root}", file=sys.stderr)
        return 2
    if not profile.exists():
        print(f"error: profile not found: {profile}", file=sys.stderr)
        return 2

    ai_work = find_ai_work_root(profile) / ".ai-work"
    version = root.name
    meta_dir = (
        Path(ns.meta_dir).resolve()
        if ns.meta_dir
        else ai_work / "wiki_sources" / "meta" / "methodology"
    )
    meta_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(root.rglob("*.md"))
    print(f"found {len(files)} md files under {root}")

    builder = Path(__file__).resolve().parent / "build_wiki_source_meta.py"
    count = 0
    for md_file in files:
        rel = md_file.relative_to(root)
        sid = build_source_id(version, rel, prefix=ns.id_prefix)
        title = f"{version} / {rel.as_posix()}"
        out_path = meta_dir / f"{sid}.md"
        cmd = [
            sys.executable, str(builder),
            "--artifact", str(md_file),
            "--source-id", sid,
            "--source-type", ns.source_type,
            "--profile", str(profile),
            "--title", title,
            "--out", str(out_path),
            "--mode", "refresh",
        ]
        # CAP-091-01: suppress the '## Related Sources' TODO scaffold by default so bulk
        # reference-doc registration is lint-clean; pass --with-related-sources to opt back in.
        if not ns.with_related_sources:
            cmd.append("--no-related-sources")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(f"error on {md_file}: {r.stderr or r.stdout}", file=sys.stderr)
            return 2
        count += 1

    print(f"primary metas: {count}")
    print(f"output dir:    {meta_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
