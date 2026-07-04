"""
convert_pdf_styled.py
Convert PDF → Markdown preserving style information.

Uses PyMuPDF to extract font size, bold/italic, colors, and layout.

Style → MD mapping:
  Font size relative to body size:
    ≥ 1.8x  → # H1
    ≥ 1.4x  → ## H2
    ≥ 1.15x → ### H3
  Bold font name → **text**
  Italic font name → *text*
  Text color (non-black) → noted as <!-- color:#rrggbb --> comment
  Multi-column layout → columns separated, left column first

Requires:
    pip install pymupdf

Usage:
    python convert_pdf_styled.py input.pdf [--out output.md] [--debug]
"""
import argparse
import re
import sys
from pathlib import Path


def rgb_to_hex(color_int: int) -> str:
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def is_bold(font_name: str) -> bool:
    n = font_name.lower()
    return any(x in n for x in ("bold", "heavy", "black", "semibold", "demi"))


def is_italic(font_name: str) -> bool:
    n = font_name.lower()
    return any(x in n for x in ("italic", "oblique", "slant"))


def detect_body_size(blocks: list) -> float:
    """Find the most common font size — that's the body size."""
    from collections import Counter
    sizes = []
    for b in blocks:
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                sizes.append(round(span["size"], 1))
    if not sizes:
        return 10.0
    return Counter(sizes).most_common(1)[0][0]


def heading_level(size: float, body_size: float) -> int | None:
    ratio = size / body_size if body_size else 1.0
    if ratio >= 1.8:
        return 1
    if ratio >= 1.4:
        return 2
    if ratio >= 1.15:
        return 3
    return None


def span_to_md(span: dict, body_size: float) -> str:
    text = span["text"].strip()
    if not text:
        return ""

    font = span.get("font", "")
    size = span.get("size", body_size)
    color = span.get("color", 0)

    bold = is_bold(font)
    italic = is_italic(font)

    # Apply inline formatting
    if bold and italic:
        text = f"***{text}***"
    elif bold:
        text = f"**{text}**"
    elif italic:
        text = f"*{text}*"

    # Non-black color annotation (skip near-black)
    if color not in (0, 0x000000) and color > 0x111111:
        hex_color = rgb_to_hex(color)
        text = f'<span style="color:{hex_color}">{text}</span>'

    return text


def blocks_to_md(page_dict: dict, body_size: float, debug: bool = False) -> list[str]:
    """Convert one page's blocks to MD lines."""
    lines_out = []
    page_width = page_dict["width"]

    # Collect text blocks only (type=0), sorted top→bottom, left→right
    blocks = [b for b in page_dict["blocks"] if b["type"] == 0]
    blocks.sort(key=lambda b: (round(b["bbox"][1] / 10) * 10, b["bbox"][0]))

    # Detect two-column layout: if blocks cluster into left/right halves
    mid_x = page_width / 2
    left_blocks = [b for b in blocks if b["bbox"][2] < mid_x * 1.1]
    right_blocks = [b for b in blocks if b["bbox"][0] > mid_x * 0.9]
    has_two_cols = (
        len(left_blocks) >= 2
        and len(right_blocks) >= 2
        and len(left_blocks) + len(right_blocks) > len(blocks) * 0.6
    )

    if has_two_cols and debug:
        print(f"  [2-column layout detected]", file=sys.stderr)

    prev_y = None

    for block in blocks:
        block_lines = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            line_text = ""
            line_size = max(s.get("size", body_size) for s in spans)

            for span in spans:
                line_text += span_to_md(span, body_size)

            line_text = line_text.strip()
            if not line_text:
                continue

            level = heading_level(line_size, body_size)
            if level:
                # Strip inline bold if already a heading
                clean = re.sub(r"\*+([^*]+)\*+", r"\1", line_text)
                block_lines.append(f"{'#' * level} {clean}")
            else:
                block_lines.append(line_text)

        if not block_lines:
            continue

        # Vertical gap → blank line separator
        block_top = block["bbox"][1]
        if prev_y is not None and (block_top - prev_y) > body_size * 1.8:
            lines_out.append("")

        lines_out.extend(block_lines)
        prev_y = block["bbox"][3]

    return lines_out


def convert(input_path: Path, output_path: Path, debug: bool = False):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip install pymupdf", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(str(input_path))
    all_lines: list[str] = []

    # First pass: detect global body size across all pages
    all_blocks = []
    for page in doc:
        d = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        all_blocks.extend([b for b in d["blocks"] if b["type"] == 0])
    body_size = detect_body_size(all_blocks)

    if debug:
        print(f"  Body font size: {body_size}pt", file=sys.stderr)

    for page_num, page in enumerate(doc, 1):
        if page_num > 1:
            all_lines.append(f"\n---\n")  # page break marker
        d = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        page_lines = blocks_to_md(d, body_size, debug)
        all_lines.extend(page_lines)

    doc.close()

    # Clean up: collapse 3+ blank lines → 2
    text = "\n".join(all_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    output_path.write_text(text, encoding="utf-8")
    print(f"Saved: {output_path} ({len(text)} bytes, {len(all_lines)} lines)")


def main():
    parser = argparse.ArgumentParser(description="PDF → Markdown with style preservation")
    parser.add_argument("input", help="Input .pdf file")
    parser.add_argument("--out", help="Output .md path (default: same dir, _styled.md)")
    parser.add_argument("--debug", action="store_true", help="Print style debug info")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.out:
        output_path = Path(args.out)
    else:
        output_path = input_path.with_name(input_path.stem + "_styled.md")

    print(f"Converting {input_path.name} → {output_path.name} (style-aware)...")
    convert(input_path, output_path, debug=args.debug)


if __name__ == "__main__":
    main()
