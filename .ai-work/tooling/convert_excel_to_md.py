#!/usr/bin/env python3
"""
Excel (.xlsx / .xls) -> per-sheet Markdown using the `markitdown` library.

Strategy:
    1. Use markitdown to convert the whole workbook to a single markdown blob.
       markitdown emits each sheet as a top-level `## <SheetName>` section.
    2. Split that blob on `## ` headings into one chunk per sheet.
    3. Write each chunk as `<sheet_name>.md` into the resolved output directory.

Output path rules (mirrors the legacy script's contract):
    File source, no --output       : <source_parent>/markdown/<stem>/<sheet>.md
    File source, with --output DIR : <DIR>/<sheet>.md
    Folder source, no --output     : <each_xlsx_parent>/markdown/<stem>/<sheet>.md
    Folder source, with --output   : <DIR>/<stem>/<sheet>.md

Dependencies (see requirements.txt):
    markitdown[xlsx,xls]
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("convert_excel_to_md")

MARKDOWN_FOLDER_NAME = "markdown"
EXCEL_SUFFIXES = {".xlsx", ".xls"}
INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
SHEET_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
NAN_CELL_RE = re.compile(r"(?<=\| )NaN(?= \|)")
UNNAMED_COL_RE = re.compile(r"Unnamed: (\d+)")


def sanitize_filename(name: str) -> str:
    cleaned = INVALID_FS_CHARS.sub("_", name).strip(" .")
    return cleaned or "sheet"


def col_index_to_excel_letter(n: int) -> str:
    if n < 0:
        return ""
    letters = ""
    while n >= 0:
        letters = chr(n % 26 + ord("A")) + letters
        n = n // 26 - 1
    return letters


def postprocess_markdown(text: str, keep_nan: bool) -> str:
    """Clean pandas/markitdown artifacts in the rendered table.

    - Blank Excel cells render as `NaN`; replace with empty unless --keep-nan.
    - Auto-generated headers `Unnamed: N` (N is 0-indexed column position) are
      renamed to `Noname:<excel_letter>` (1->B, 2->C, ..., 26->AA).
    """
    if not keep_nan:
        text = NAN_CELL_RE.sub("", text)
    text = UNNAMED_COL_RE.sub(
        lambda m: f"Noname:{col_index_to_excel_letter(int(m.group(1)))}",
        text,
    )
    return text


def parse_skip_list(arg: Optional[str]) -> set[str]:
    if not arg:
        return set()
    return {s.strip() for s in arg.split(",") if s.strip()}


def split_by_sheets(markdown_text: str) -> list[tuple[str, str]]:
    """
    Split markitdown output into (sheet_name, sheet_markdown_chunk) pairs
    using top-level `## <name>` headings as boundaries.

    If no heading is found, returns a single ("", text) pair so the caller
    can still write something out (named "sheet.md").
    """
    matches = list(SHEET_HEADING_RE.finditer(markdown_text))
    if not matches:
        body = markdown_text.strip()
        return [("", body)] if body else []

    chunks: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        sheet_name = m.group(1).strip()
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown_text)
        chunk = markdown_text[start:end].strip()
        chunks.append((sheet_name, chunk))
    return chunks


def convert_workbook(source: Path) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency `markitdown`. Install with:\n"
            "  pip install 'markitdown[xlsx,xls]'"
        ) from exc

    md = MarkItDown()
    result = md.convert(str(source))
    return getattr(result, "text_content", "") or ""


def write_sheets(
    chunks: list[tuple[str, str]],
    output_dir: Path,
    skip_sheets: set[str],
) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    seen_names: dict[str, int] = {}

    for sheet_name, body in chunks:
        if not body.strip():
            continue
        if sheet_name and sheet_name in skip_sheets:
            logger.info("[skip] sheet %r matched --skip-sheets", sheet_name)
            skipped += 1
            continue

        base = sanitize_filename(sheet_name or "sheet")
        count = seen_names.get(base, 0)
        seen_names[base] = count + 1
        suffix = f"_{count + 1}" if count else ""
        out_file = output_dir / f"{base}{suffix}.md"
        out_file.write_text(body + "\n", encoding="utf-8")
        logger.debug("[write] %s", out_file)
        written += 1

    return written, skipped


def resolve_output_dir(
    source: Path,
    folder_mode: bool,
    output_override: Optional[Path],
    excel_stem: str,
) -> Path:
    if output_override:
        return output_override / excel_stem if folder_mode else output_override
    parent = source.parent
    return parent / MARKDOWN_FOLDER_NAME / excel_stem


def convert_one(
    source: Path,
    output_dir: Path,
    skip_sheets: set[str],
    keep_nan: bool = False,
) -> tuple[int, int]:
    logger.info("[convert] %s", source.name)
    md_text = convert_workbook(source)
    md_text = postprocess_markdown(md_text, keep_nan=keep_nan)
    chunks = split_by_sheets(md_text)
    if not chunks:
        logger.warning("[empty] markitdown returned no content for %s", source.name)
        return 0, 0
    written, skipped = write_sheets(chunks, output_dir, skip_sheets)
    logger.info(
        "[done] %s -> %s (%d written, %d skipped)",
        source.name,
        output_dir,
        written,
        skipped,
    )
    return written, skipped


def iter_excel_files(folder: Path) -> Iterable[Path]:
    for p in sorted(folder.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in EXCEL_SUFFIXES:
            continue
        if p.name.startswith("~$"):  # Excel lock file
            continue
        yield p


def clean_default_markdown(folder: Path) -> None:
    target = folder / MARKDOWN_FOLDER_NAME
    if target.exists():
        logger.info("[clean] removing %s", target)
        shutil.rmtree(target)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert Excel (.xlsx / .xls) to per-sheet Markdown using markitdown.",
    )
    p.add_argument("--source", required=True, help="Path to .xlsx/.xls file or a directory.")
    p.add_argument("--output", help="Output directory. See header docstring for path rules.")
    p.add_argument(
        "--skip-sheets",
        help='Comma-separated sheet names to skip, e.g. "Cover,Index".',
    )
    p.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing target output directory(ies) before writing.",
    )
    p.add_argument(
        "--keep-nan",
        action="store_true",
        help="Keep `NaN` markers for blank cells instead of rendering as empty.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging.")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    source = Path(args.source).resolve()
    if not source.exists():
        logger.error("Path not found: %s", source)
        return 2

    output_override = Path(args.output).resolve() if args.output else None
    skip_sheets = parse_skip_list(args.skip_sheets)

    if source.is_file():
        if source.suffix.lower() not in EXCEL_SUFFIXES:
            logger.error("Source must be .xlsx or .xls: %s", source)
            return 2
        out_dir = resolve_output_dir(source, False, output_override, source.stem)
        if args.clean and out_dir.exists():
            logger.info("[clean] removing %s", out_dir)
            shutil.rmtree(out_dir)
        try:
            convert_one(source, out_dir, skip_sheets, keep_nan=args.keep_nan)
        except Exception as exc:
            logger.error("Conversion failed for %s: %s", source.name, exc)
            return 1
        return 0

    if args.clean and output_override is None:
        clean_default_markdown(source)

    files = list(iter_excel_files(source))
    if not files:
        logger.warning("No .xlsx/.xls files found in %s", source)
        return 0

    failed = 0
    for f in files:
        out_dir = resolve_output_dir(f, True, output_override, f.stem)
        if args.clean and output_override is not None and out_dir.exists():
            shutil.rmtree(out_dir)
        try:
            convert_one(f, out_dir, skip_sheets, keep_nan=args.keep_nan)
        except Exception as exc:
            logger.error("Failed %s: %s", f.name, exc)
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
