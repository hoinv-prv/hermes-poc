"""
convert_to_md.py
Universal document ->Markdown converter.

Dispatches to the right pipeline per format:
  PDF, DOCX   ->docling ->MD + section markers
  PPTX        ->docling ->MD + section markers  (inject_section_markers.py)
  XLSX, XLSM  ->docling ->orig MD
                         + convert_sheets.py (per-sheet MD)
                         + build_image_index.py (image index)
  PNG/JPG/JPEG/TIFF/BMP/WEBP  ->docling OCR ->MD

Usage:
    python convert_to_md.py <input_file> [--out-dir output/] [--no-section-markers]

Outputs (by format):
  All      ->output/<stem>.md
  PPTX/DOCX/PDF with headings
           ->output/<stem>_sections.md  (section-marked version)
  XLSX/XLSM
           ->output/<stem>_sheets.md    (per-sheet MD)
           ->output/<stem>_image_index.md / .json
"""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp", ".gif"}


def run_script(script_name: str, args: list[str], utf8: bool = False):
    cmd = [sys.executable]
    if utf8:
        cmd += ["-X", "utf8"]
    cmd += [str(SCRIPTS_DIR / script_name)] + args
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        sys.exit(result.returncode)


def convert_with_docling(input_path: Path, out_dir: Path) -> Path:
    """Use docling DocumentConverter to convert input ->MD. Returns output path."""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        print("ERROR: docling not installed. Run: pip install docling", file=sys.stderr)
        sys.exit(1)

    print(f"Converting {input_path.name} with docling...")
    converter = DocumentConverter()
    result = converter.convert(str(input_path))
    md_text = result.document.export_to_markdown()

    out_path = out_dir / (input_path.stem + ".md")
    out_path.write_text(md_text, encoding="utf-8")
    print(f"  ->{out_path} ({len(md_text) // 1024} KB)")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Universal document ->Markdown converter")
    parser.add_argument("input", help="Input file")
    parser.add_argument("--out-dir", default="output", help="Output directory (default: output/)")
    parser.add_argument(
        "--no-section-markers",
        action="store_true",
        help="Skip section marker injection for PPTX/DOCX/PDF",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = input_path.suffix.lower()

    # ── XLSX / XLSM -full 3-step pipeline ───────────────────────────────────
    if suffix in (".xlsx", ".xlsm"):
        print("Format: XLSX/XLSM -running full pipeline (orig MD + sheets + image index)")
        orig_md = convert_with_docling(input_path, out_dir)

        sheets_md = out_dir / (input_path.stem + "_sheets.md")
        print(f"\nStep 2: per-sheet conversion ->{sheets_md.name}")
        run_script("convert_sheets.py", [str(input_path), "--out", str(sheets_md)])

        print(f"\nStep 3: building image index...")
        run_script(
            "build_image_index.py",
            ["--orig-md", str(orig_md), "--sheets-md", str(sheets_md), "--out-dir", str(out_dir)],
            utf8=True,
        )
        print(f"\nDone. Files in {out_dir}/:")
        print(f"  {orig_md.name}  (orig MD -all base64 images)")
        print(f"  {sheets_md.name}  (per-sheet MD with # Sheet: Name headers)")
        print(f"  {input_path.stem}_image_index.md  (image navigation index)")
        print(f"  {input_path.stem}_image_index.json")

    # ── PPTX ─────────────────────────────────────────────────────────────────
    elif suffix == ".pptx":
        print("Format: PPTX")
        orig_md = convert_with_docling(input_path, out_dir)
        if not args.no_section_markers:
            sections_md = out_dir / (input_path.stem + "_sections.md")
            print(f"Injecting section markers ->{sections_md.name}")
            run_script("inject_section_markers.py", [str(orig_md), str(sections_md)])
            print(f"\nDone. Files in {out_dir}/:")
            print(f"  {orig_md.name}  (orig MD)")
            print(f"  {sections_md.name}  (with <!-- Section N --> markers)")
        else:
            print(f"\nDone: {orig_md}")

    # ── PDF / DOCX -optional section markers ────────────────────────────────
    elif suffix in (".pdf", ".docx", ".doc"):
        fmt = suffix.upper().lstrip(".")
        print(f"Format: {fmt}")
        orig_md = convert_with_docling(input_path, out_dir)
        if not args.no_section_markers:
            import re
            md_text = orig_md.read_text(encoding="utf-8")
            has_headings = bool(re.search(r"^#{1,6} ", md_text, re.MULTILINE))
            if has_headings:
                sections_md = out_dir / (input_path.stem + "_sections.md")
                print(f"Headings found -injecting section markers ->{sections_md.name}")
                run_script("inject_section_markers.py", [str(orig_md), str(sections_md)])
                print(f"\nDone. Files in {out_dir}/:")
                print(f"  {orig_md.name}")
                print(f"  {sections_md.name}  (with <!-- Section N --> markers)")
            else:
                print("No headings found -skipping section markers.")
                print(f"\nDone: {orig_md}")
        else:
            print(f"\nDone: {orig_md}")

    # ── Images -OCR via docling ──────────────────────────────────────────────
    elif suffix in IMAGE_EXTS:
        print(f"Format: image ({suffix}) -OCR via docling")
        orig_md = convert_with_docling(input_path, out_dir)
        print(f"\nDone: {orig_md}")

    else:
        print(f"Unsupported format: {suffix}", file=sys.stderr)
        print(f"Supported: .pdf .docx .pptx .xlsx .xlsm .png .jpg .jpeg .gif .tiff .bmp .webp", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
