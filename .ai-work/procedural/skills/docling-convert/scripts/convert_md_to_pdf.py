"""
convert_md_to_pdf.py
Convert Markdown to PDF using reportlab.

Requires:
    pip install reportlab

Japanese font auto-detected from system fonts:
  Windows : Meiryo, Yu Gothic, MS Gothic
  macOS   : Hiragino, Noto Sans CJK
  Fallback: HeiseiKakuGo-W5 (CID font — most PDF viewers support it)
  Last resort: Helvetica (ASCII-only; Japanese renders as boxes)

Usage:
    python convert_md_to_pdf.py input.md [--out output.pdf]
"""
import argparse
import re
import sys
from pathlib import Path

# ── Font detection ────────────────────────────────────────────────────────────

_FONT_CANDIDATES = [
    # (regular_path, bold_path, subfont_index)
    ("C:/Windows/Fonts/meiryo.ttc",  "C:/Windows/Fonts/meiryob.ttc",  0),
    ("C:/Windows/Fonts/YuGothM.ttc", "C:/Windows/Fonts/YuGothB.ttc",  0),
    ("C:/Windows/Fonts/msgothic.ttc", "C:/Windows/Fonts/msgothic.ttc", 0),
    ("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
     "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
     "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf", 0),
]


def _setup_fonts() -> tuple[str, str]:
    """Register PDF fonts. Returns (regular_name, bold_name)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for reg, bold, idx in _FONT_CANDIDATES:
        if not Path(reg).exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("DocFont", reg, subfontIndex=idx))
            bp = bold if bold and Path(bold).exists() else reg
            pdfmetrics.registerFont(TTFont("DocFontBold", bp, subfontIndex=idx))
            print(f"  Font: {Path(reg).name}")
            return "DocFont", "DocFontBold"
        except Exception as e:
            print(f"  TTF failed ({Path(reg).name}): {e}", file=sys.stderr)

    # CID fallback — no bold variant, but Japanese works
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        print("  Font: HeiseiKakuGo-W5 (CID, no bold distinction)")
        return "HeiseiKakuGo-W5", "HeiseiKakuGo-W5"
    except Exception:
        pass

    print("  Warning: no Japanese font — Japanese text may render as boxes.", file=sys.stderr)
    return "Helvetica", "Helvetica-Bold"


# ── Style builder ─────────────────────────────────────────────────────────────

def _build_styles(reg: str, bold: str) -> dict:
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import black, Color

    def ps(name, **kw):
        cfg = dict(fontName=reg, fontSize=10, leading=15, textColor=black, spaceAfter=4)
        cfg.update(kw)
        return ParagraphStyle(name, **cfg)

    return {
        "h1": ps("h1", fontName=bold, fontSize=20, leading=26, spaceBefore=14, spaceAfter=8),
        "h2": ps("h2", fontName=bold, fontSize=16, leading=22, spaceBefore=10, spaceAfter=6),
        "h3": ps("h3", fontName=bold, fontSize=13, leading=18, spaceBefore=8,  spaceAfter=4),
        "h4": ps("h4", fontName=bold, fontSize=11, leading=16, spaceBefore=6,  spaceAfter=4),
        "body":   ps("body", spaceAfter=6),
        "code":   ps("code", fontName="Courier", fontSize=8, leading=11,
                     backColor=Color(0.95, 0.95, 0.95),
                     leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=6),
        "bullet": ps("bullet", leftIndent=20, firstLineIndent=-12, spaceAfter=3),
        "number": ps("number", leftIndent=28, firstLineIndent=-16, spaceAfter=3),
        "th":     ps("th", fontName=bold, fontSize=9, leading=12),
        "td":     ps("td", fontSize=9, leading=12),
    }


# ── Inline markup ─────────────────────────────────────────────────────────────

def _rl(text: str) -> str:
    """Convert inline MD to reportlab XML. Escapes special chars first."""
    # Escape XML
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Strip links: [text](url) → text
    out = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", out)
    # Strip images
    out = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", out)
    # Bold+italic → bold+italic
    out = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", out)
    # Bold
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    # Italic
    out = re.sub(r"\*(.+?)\*", r"<i>\1</i>", out)
    # Inline code
    out = re.sub(r"`(.+?)`", r'<font name="Courier" size="8">\1</font>', out)
    return out


# ── Table helper ──────────────────────────────────────────────────────────────

def _parse_table(table_lines: list[str], styles: dict) -> object | None:
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.colors import grey, Color

    rows_data = []
    is_header_row = True
    header_count = 0

    for line in table_lines:
        s = line.strip()
        if re.match(r"^\|[-| :]+\|$", s):
            is_header_row = False
            continue
        # Parse cells
        inner = s[1:] if s.startswith("|") else s
        if inner.endswith("|"):
            inner = inner[:-1]
        cells = [c.strip() for c in inner.split("|")]
        style = styles["th"] if is_header_row else styles["td"]
        rows_data.append(([Paragraph(_rl(c), style) for c in cells], is_header_row))
        if is_header_row:
            header_count += 1

    if not rows_data:
        return None

    n_cols = max(len(r[0]) for r in rows_data)
    td_style = styles["td"]
    table_rows = []
    for cells, _ in rows_data:
        row = list(cells)
        while len(row) < n_cols:
            row.append(Paragraph("", td_style))
        table_rows.append(row)

    tbl = Table(table_rows, repeatRows=header_count)
    tbl.setStyle(TableStyle([
        ("GRID",        (0, 0), (-1, -1), 0.5, grey),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND",  (0, 0), (-1, header_count - 1), Color(0.85, 0.90, 1.0)),
    ]))
    return tbl


# ── Main converter ────────────────────────────────────────────────────────────

def _to_flowables(text: str, styles: dict) -> list:
    from reportlab.platypus import Paragraph, Preformatted, Spacer, HRFlowable
    from reportlab.lib.units import cm
    from reportlab.lib.colors import grey

    lines = text.splitlines()
    flowables = []
    i = 0
    in_code = False
    in_comment = False
    code_buf: list[str] = []
    table_buf: list[str] = []

    def flush_code():
        nonlocal in_code, code_buf
        if code_buf:
            flowables.append(Preformatted("\n".join(code_buf), styles["code"]))
        code_buf = []
        in_code = False

    def flush_table():
        if table_buf:
            tbl = _parse_table(table_buf, styles)
            if tbl:
                flowables.append(tbl)
                flowables.append(Spacer(1, 0.2 * cm))
        table_buf.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Multi-line HTML comment
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            i += 1
            continue

        # Code block
        if stripped.startswith("```"):
            if table_buf:
                flush_table()
            if in_code:
                flush_code()
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Table
        if stripped.startswith("|"):
            table_buf.append(stripped)
            i += 1
            continue
        elif table_buf:
            flush_table()

        # HTML comment
        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_comment = True
            i += 1
            continue

        # Image lines (skip)
        if stripped.startswith("!["):
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            level = min(len(m.group(1)), 4)
            flowables.append(Paragraph(_rl(m.group(2)), styles[f"h{level}"]))
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}$", stripped):
            flowables.append(HRFlowable(width="100%", thickness=1, color=grey))
            flowables.append(Spacer(1, 0.15 * cm))
            i += 1
            continue

        # Bullet
        m = re.match(r"^[-*+]\s+(.+)$", stripped)
        if m:
            flowables.append(Paragraph(f"• {_rl(m.group(1))}", styles["bullet"]))
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m:
            flowables.append(Paragraph(f"{m.group(1)}. {_rl(m.group(2))}", styles["number"]))
            i += 1
            continue

        # Empty
        if not stripped:
            flowables.append(Spacer(1, 0.12 * cm))
            i += 1
            continue

        # Normal paragraph
        flowables.append(Paragraph(_rl(stripped), styles["body"]))
        i += 1

    # Flush any unclosed blocks
    if in_code:
        flush_code()
    if table_buf:
        flush_table()

    return flowables


def convert(input_path: Path, output_path: Path):
    try:
        from reportlab.platypus import SimpleDocTemplate
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
    except ImportError:
        print("ERROR: reportlab not installed. Run: pip install reportlab", file=sys.stderr)
        sys.exit(1)

    reg, bold = _setup_fonts()
    styles = _build_styles(reg, bold)
    text = input_path.read_text(encoding="utf-8")
    flowables = _to_flowables(text, styles)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=3.0 * cm,
        rightMargin=2.0 * cm,
    )
    doc.build(flowables)
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to PDF")
    parser.add_argument("input", help="Input .md file")
    parser.add_argument("--out", help="Output .pdf path (default: same dir, .pdf extension)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.out) if args.out else input_path.with_suffix(".pdf")
    print(f"Converting {input_path.name} → {output_path.name}...")
    convert(input_path, output_path)


if __name__ == "__main__":
    main()
