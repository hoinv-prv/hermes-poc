"""
screenshot_sheets.py
Screenshot each sheet of an Excel file as PNG using Excel's own renderer.

Requires:
    pip install pywin32 pymupdf

Usage:
    python screenshot_sheets.py input.xlsx [--out OUTPUT_DIR] [--dpi 150]
"""
import argparse
import sys
from pathlib import Path


def _safe_name(sheet_name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in sheet_name)


def screenshot_xlsx(xlsx_path: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    """
    Open xlsx in Excel, export each sheet as PDF, convert to PNG.
    Returns list of saved PNG paths.
    """
    try:
        import win32com.client
    except ImportError:
        print("ERROR: pywin32 not installed. Run: pip install pywin32", file=sys.stderr)
        sys.exit(1)

    try:
        import fitz
    except ImportError:
        print("ERROR: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    png_paths: list[Path] = []
    excel = None
    wb = None

    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False

        wb = excel.Workbooks.Open(str(xlsx_path.resolve()))

        for i in range(1, wb.Sheets.Count + 1):
            sheet = wb.Sheets(i)
            name = sheet.Name
            safe = _safe_name(name)

            # Fit sheet to 1 page wide so content isn't cut horizontally
            ps = sheet.PageSetup
            ps.Zoom = False
            ps.FitToPagesWide = 1
            ps.FitToPagesTall = False

            pdf_path = out_dir / f"sheet_{i:02d}_{safe}.pdf"
            try:
                sheet.ExportAsFixedFormat(
                    Type=0,          # xlTypePDF
                    Filename=str(pdf_path.resolve()),
                    Quality=0,       # xlQualityStandard
                    IncludeDocProperties=False,
                    IgnorePrintAreas=False,
                    OpenAfterPublish=False,
                )
            except Exception as e:
                # Empty/blank sheets fail to export — skip silently
                print(f"  [{i}/{wb.Sheets.Count}] {name} -> skipped (empty or unprintable: {e})")
                continue

            # PDF → PNG
            scale = dpi / 96.0
            mat = fitz.Matrix(scale, scale)
            doc = fitz.open(str(pdf_path))
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(matrix=mat)
                suffix = f"_p{page_num + 1}" if len(doc) > 1 else ""
                png_path = out_dir / f"sheet_{i:02d}_{safe}{suffix}.png"
                pix.save(str(png_path))
                png_paths.append(png_path)
                print(f"  [{i}/{wb.Sheets.Count}] {name}{suffix} -> {png_path.name}")
            doc.close()
            pdf_path.unlink(missing_ok=True)

    finally:
        if wb is not None:
            try:
                wb.Close(SaveChanges=False)
            except Exception:
                pass
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass

    return png_paths


def main():
    parser = argparse.ArgumentParser(description="Screenshot Excel sheets as PNG")
    parser.add_argument("input", help="Input .xlsx or .xlsm file")
    parser.add_argument("--out", help="Output folder (default: <stem>_screenshots)")
    parser.add_argument("--dpi", type=int, default=150, help="Resolution (default: 150)")
    args = parser.parse_args()

    xlsx_path = Path(args.input)
    if not xlsx_path.exists():
        print(f"ERROR: file not found: {xlsx_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out) if args.out else xlsx_path.with_name(xlsx_path.stem + "_screenshots")

    print(f"Screenshotting {xlsx_path.name} -> {out_dir.name}/")
    paths = screenshot_xlsx(xlsx_path, out_dir, dpi=args.dpi)
    print(f"\nDone. {len(paths)} screenshot(s) saved to: {out_dir}")


if __name__ == "__main__":
    main()
