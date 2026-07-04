"""
build_image_index.py
Build an image index for a docling-converted Excel file.
Maps every embedded image to its sheet name, with surrounding context.

Outputs:
  <stem>_image_index.json  — machine-readable (for scripts)
  <stem>_image_index.md    — human/AI-readable navigation table

Usage:
    python build_image_index.py \
        --orig-md output/<file>.md \
        --sheets-md output/<file>_sheets.md \
        [--out-dir output/]

The AI agent workflow:
  1. build_image_index  → produces image_index.md
  2. Read image_index.md → find target image by sheet + context
  3. extract_sheet_image --n <N> → extract and display the image
"""
import argparse
import base64
import json
import re
import sys
from pathlib import Path


# ── Anchor extraction (same logic as extract_sheet_image.py) ─────────────────

def get_sheet_sections(sheets_md: str) -> list[dict]:
    """Return list of {name, section_text} for every sheet."""
    headers = list(re.finditer(r"^# Sheet: (.+)$", sheets_md, re.MULTILINE))
    sections = []
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(sheets_md)
        sections.append({
            "name": m.group(1).strip(),
            "section_text": sheets_md[m.start():end],
        })
    return sections


def extract_anchors(section_text: str, sheet_name: str) -> list[str]:
    """Extract text anchors from a sheet section (free text + table cells)."""
    anchors = []
    # Pass 1: free-text lines
    for line in section_text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("<!--") or s.startswith("-"):
            continue
        if not s.startswith("|") and len(s) >= 6:
            anchors.append(s)
    if anchors:
        return anchors[:5]
    # Pass 2: table cell content
    for line in section_text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if re.match(r"^\|[-| :]+\|$", s):
            continue
        cells = [c.strip() for c in s.split("|") if c.strip()]
        for cell in cells:
            if len(cell) >= 6 and not re.match(r"^[-\d\s\.]+$", cell):
                anchors.append(cell)
        if len(anchors) >= 3:
            break
    return anchors[:5]


def find_sheet_pos_in_orig(orig_md: str, anchors: list[str]) -> int:
    """Find best position in orig_md where anchors cluster (window-based)."""
    if not anchors:
        return -1
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
    window = 120_000
    best_pos, best_count = all_hits[0][0], 0
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


# ── Context extraction ────────────────────────────────────────────────────────

def extract_context(orig_lines: list[str], img_line_idx: int) -> str:
    """Scan lines before/after an image line for readable text or table cells."""

    def line_to_text(line: str) -> str | None:
        s = line.strip()
        if not s or s.startswith("![Image]") or "data:image" in s:
            return None
        if re.match(r"^\|[-| :]+\|$", s):  # separator row
            return None
        if s.startswith("|"):
            # Extract non-empty, non-numeric cells
            cells = [c.strip() for c in s.split("|") if c.strip()]
            meaningful = [c for c in cells if len(c) >= 3 and not re.match(r"^[\d\s\.]+$", c)]
            if meaningful:
                return " / ".join(meaningful[:3])
            return None
        if s.startswith("<!--") or s.startswith("#"):
            return None
        return s[:80]

    # Scan backwards
    before = []
    for i in range(img_line_idx - 1, max(-1, img_line_idx - 40), -1):
        t = line_to_text(orig_lines[i])
        if t:
            before.append(t[:80])
            if len(before) == 2:
                break
    before.reverse()

    # Scan forwards
    after = []
    for i in range(img_line_idx + 1, min(len(orig_lines), img_line_idx + 40)):
        t = line_to_text(orig_lines[i])
        if t:
            after.append(t[:80])
            if len(after) == 2:
                break

    parts = before + (["→"] if before and after else []) + after
    result = " / ".join(parts)
    return result if result else "(no text context)"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build image index for docling Excel MD")
    parser.add_argument("--orig-md", required=True, help="Original single-pass docling MD")
    parser.add_argument("--sheets-md", required=True, help="Per-sheet MD from convert_sheets.py")
    parser.add_argument("--out-dir", help="Output directory (default: same as orig-md)")
    args = parser.parse_args()

    orig_path = Path(args.orig_md)
    sheets_path = Path(args.sheets_md)
    out_dir = Path(args.out_dir) if args.out_dir else orig_path.parent

    print(f"Reading orig MD ({orig_path.stat().st_size // 1024} KB)...")
    with open(orig_path, encoding="utf-8") as f:
        orig_md = f.read()

    print(f"Reading sheets MD...")
    with open(sheets_path, encoding="utf-8") as f:
        sheets_md = f.read()

    # ── 1. Find all images in orig MD ─────────────────────────────────────────
    orig_lines = orig_md.splitlines()
    img_pattern = re.compile(
        r"!\[Image\]\(data:image/png;base64,([A-Za-z0-9+/=]+)\)"
    )
    # Map char position → line index for context lookup
    line_start_positions = []
    pos = 0
    for line in orig_lines:
        line_start_positions.append(pos)
        pos += len(line) + 1  # +1 for \n

    def char_pos_to_line(char_pos: int) -> int:
        lo, hi = 0, len(line_start_positions) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_start_positions[mid] <= char_pos:
                lo = mid
            else:
                hi = mid - 1
        return lo

    all_images = [(m.start(), m.group(1)) for m in img_pattern.finditer(orig_md)]
    print(f"Total images in orig MD: {len(all_images)}")

    # ── 2. Locate each sheet in orig MD ───────────────────────────────────────
    print("Locating sheets in orig MD...")
    sheet_sections = get_sheet_sections(sheets_md)
    sheet_positions = []  # (orig_pos, sheet_name)

    for sec in sheet_sections:
        anchors = extract_anchors(sec["section_text"], sec["name"])
        pos = find_sheet_pos_in_orig(orig_md, anchors) if anchors else -1
        sheet_positions.append((pos, sec["name"]))
        status = f"pos={pos}" if pos != -1 else "NOT LOCATED"
        print(f"  {sec['name']}: {status}")

    # Sort by position; sheets not located (-1) go to end
    sheet_positions.sort(key=lambda x: x[0] if x[0] != -1 else float("inf"))

    # ── 3. Assign each image to a sheet ───────────────────────────────────────
    def get_sheet_for_pos(img_pos: int) -> str:
        assigned = "unknown"
        for i, (sheet_start, sheet_name) in enumerate(sheet_positions):
            if sheet_start == -1:
                continue
            next_start = next(
                (sp for sp, _ in sheet_positions[i + 1:] if sp != -1),
                len(orig_md)
            )
            if sheet_start <= img_pos < next_start:
                assigned = sheet_name
                break
        return assigned

    # ── 4. Build index ─────────────────────────────────────────────────────────
    index = []
    sheet_counters: dict[str, int] = {}

    for global_n, (img_pos, b64) in enumerate(all_images, 1):
        sheet_name = get_sheet_for_pos(img_pos)
        sheet_counters[sheet_name] = sheet_counters.get(sheet_name, 0) + 1
        sheet_img_n = sheet_counters[sheet_name]

        img_bytes = len(base64.b64decode(b64))
        img_line = char_pos_to_line(img_pos)
        context = extract_context(orig_lines, img_line)

        index.append({
            "sheet": sheet_name,
            "sheet_image_n": sheet_img_n,
            "global_image_n": global_n,
            "orig_md_pos": img_pos,
            "size_bytes": img_bytes,
            "context": context[:150],
        })

    # ── 5. Write JSON ──────────────────────────────────────────────────────────
    stem = orig_path.stem
    json_path = out_dir / f"{stem}_image_index.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # ── 6. Write Markdown table ────────────────────────────────────────────────
    md_path = out_dir / f"{stem}_image_index.md"
    lines = [
        f"# Image Index — {orig_path.name}",
        "",
        f"Total images: {len(index)}  |  Source: `{orig_path.name}`",
        "",
        "To extract an image: `python -X utf8 extract_sheet_image.py --orig-md <orig> --sheets-md <sheets> --sheet \"<Sheet>\" --n <#> --out <out.png>`",
        "",
        "| Sheet | # | Size | Context |",
        "|---|---|---|---|",
    ]
    for entry in index:
        size_kb = entry["size_bytes"] // 1024
        ctx = entry["context"].replace("|", "｜")
        lines.append(
            f"| {entry['sheet']} | {entry['sheet_image_n']} | {size_kb} KB | {ctx} |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nDone.")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")

    # Summary
    sheet_summary = {}
    for e in index:
        sheet_summary[e["sheet"]] = sheet_summary.get(e["sheet"], 0) + 1
    print(f"\nImages per sheet:")
    for sheet, count in sheet_summary.items():
        print(f"  {sheet}: {count}")


if __name__ == "__main__":
    main()
