"""
extract_sheet_image.py
Extract the Nth image from a specific Excel sheet using the original
single-pass docling MD (which has base64 images) and a per-sheet MD
(which has text content but <!-- image --> placeholders).

Strategy:
  1. Read the per-sheet MD to get unique text from the target sheet section.
  2. Find that text in the original single-pass MD to locate the sheet boundary.
  3. Count forward to the Nth image and extract its base64 data.

This workaround is needed because docling drops images when converting
per-sheet xlsx files split by openpyxl.

Usage:
    python extract_sheet_image.py \\
        --orig-md <original_single_pass.md> \\
        --sheets-md <sheets_output.md> \\
        --sheet <sheet_name> \\
        --n <image_number_1_based> \\
        --out <output.png>

Example:
    python extract_sheet_image.py \\
        --orig-md output/file.md \\
        --sheets-md output/file_sheets.md \\
        --sheet "1.4.店長確認" \\
        --n 1 \\
        --out output/sheet_14_img1.png
"""
import argparse
import base64
import re
import sys
from pathlib import Path


def get_sheet_text_anchors(sheets_md: str, sheet_name: str) -> list[str]:
    """Extract text anchors from the sheet section in per-sheet MD.
    Tries free-text lines first; falls back to table cell content."""
    pattern = re.compile(
        r"^# Sheet: " + re.escape(sheet_name) + r"\s*$",
        re.MULTILINE,
    )
    m = pattern.search(sheets_md)
    if not m:
        return []

    next_sheet = re.search(r"^# Sheet:", sheets_md[m.end():], re.MULTILINE)
    end = m.end() + next_sheet.start() if next_sheet else len(sheets_md)
    section = sheets_md[m.start():end]

    # Pass 1: free-text lines (not table rows, not headers, not comments)
    anchors = []
    for line in section.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith("<!--") or s.startswith("-"):
            continue
        if not s.startswith("|") and len(s) >= 6:
            anchors.append(s)

    if anchors:
        return anchors

    # Pass 2: extract cell content from table rows
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        # Skip separator rows (|---|---|)
        if re.match(r"^\|[-| :]+\|$", s):
            continue
        cells = [c.strip() for c in s.split("|") if c.strip()]
        for cell in cells:
            if len(cell) >= 6 and not re.match(r"^[-\d\s\.]+$", cell):
                anchors.append(cell)
        if len(anchors) >= 3:
            break

    return anchors


def find_sheet_start_in_orig(orig_md: str, anchors: list[str]) -> int:
    """Find the position in orig_md where the most anchors cluster together.
    Uses a sliding window to find the region where multiple anchors co-occur,
    handling repeated template text that appears across many sheets."""
    if not anchors:
        return -1

    # Collect all occurrences of every anchor
    all_hits: list[tuple[int, str]] = []
    for anchor in anchors:
        pos = 0
        while True:
            idx = orig_md.find(anchor, pos)
            if idx == -1:
                break
            all_hits.append((idx, anchor))
            pos = idx + 1

    if not all_hits:
        return -1

    all_hits.sort()

    # Sliding window: find the start position where most distinct anchors cluster
    window = 120_000  # ~120k chars ≈ one large sheet
    best_pos = all_hits[0][0]
    best_count = 0

    for i, (pos, _) in enumerate(all_hits):
        seen = set()
        for j in range(i, len(all_hits)):
            if all_hits[j][0] - pos > window:
                break
            seen.add(all_hits[j][1])
        if len(seen) > best_count:
            best_count = len(seen)
            best_pos = pos

    return best_pos


def extract_nth_image(orig_md: str, start_pos: int, n: int) -> bytes | None:
    """Extract the Nth base64 PNG image (1-based) found after start_pos."""
    pattern = re.compile(
        r"!\[Image\]\(data:image/png;base64,([A-Za-z0-9+/=]+)\)"
    )
    count = 0
    for m in pattern.finditer(orig_md, start_pos):
        count += 1
        if count == n:
            return base64.b64decode(m.group(1))
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract Nth image from a specific Excel sheet via docling MD"
    )
    parser.add_argument("--orig-md", required=True, help="Original single-pass docling MD (has base64 images)")
    parser.add_argument("--sheets-md", required=True, help="Per-sheet MD from convert_sheets.py (has text, no images)")
    parser.add_argument("--sheet", required=True, help="Sheet name exactly as it appears in the workbook")
    parser.add_argument("--n", type=int, default=1, help="Image number (1-based, default: 1)")
    parser.add_argument("--out", required=True, help="Output PNG path")
    args = parser.parse_args()

    orig_path = Path(args.orig_md)
    sheets_path = Path(args.sheets_md)

    if not orig_path.exists():
        print(f"Error: orig-md not found: {orig_path}")
        sys.exit(1)
    if not sheets_path.exists():
        print(f"Error: sheets-md not found: {sheets_path}")
        sys.exit(1)

    print(f"Reading orig MD: {orig_path.name}")
    with open(orig_path, encoding="utf-8") as f:
        orig_md = f.read()

    print(f"Reading sheets MD: {sheets_path.name}")
    with open(sheets_path, encoding="utf-8") as f:
        sheets_md = f.read()

    # --- Get text anchors from per-sheet MD ---
    anchors = get_sheet_text_anchors(sheets_md, args.sheet)
    if not anchors:
        print(f"Error: sheet '{args.sheet}' not found in sheets MD.")
        print("Available sheets:")
        for h in re.findall(r"^# Sheet: .+", sheets_md, re.MULTILINE):
            print(f"  {h}")
        sys.exit(1)

    print(f"Text anchors found: {len(anchors)}")
    print(f"Using: {anchors[0][:60]!r}")

    # --- Locate sheet region in orig MD ---
    start_pos = find_sheet_start_in_orig(orig_md, anchors)
    if start_pos == -1:
        print("Error: could not locate sheet content in original MD.")
        print("Tried anchors:")
        for a in anchors[:5]:
            print(f"  {a[:60]!r}")
        sys.exit(1)

    print(f"Sheet region starts at orig MD position: {start_pos}")

    # --- Find next sheet boundary in orig MD (approximate) ---
    # Use remaining anchors from the NEXT sheet to bound the search.
    # Simpler: just search from start_pos forward — images will be in order.

    # --- Extract Nth image ---
    data = extract_nth_image(orig_md, start_pos, args.n)
    if data is None:
        # Count total images in region for diagnostics
        total = len(re.findall(
            r"!\[Image\]\(data:image/png;base64,[A-Za-z0-9+/=]+\)",
            orig_md[start_pos:]
        ))
        print(f"Error: image {args.n} not found. Total images from this position: {total}")
        sys.exit(1)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    print(f"Saved image {args.n} ({len(data):,} bytes) → {out_path}")


if __name__ == "__main__":
    main()
