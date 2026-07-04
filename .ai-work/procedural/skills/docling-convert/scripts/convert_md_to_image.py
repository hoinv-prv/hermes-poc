"""
convert_md_to_image.py
Convert Markdown to PNG image(s) using Pillow.

Requires:
    pip install Pillow

Japanese font auto-detected from system fonts (same priority as convert_md_to_pdf.py):
  Windows: Meiryo, Yu Gothic, MS Gothic
  macOS  : Hiragino, Noto Sans CJK
  Fallback: PIL default bitmap font (ASCII-only; Japanese renders as boxes)

Output: A4-proportioned PNG pages.
  Single page  → output.png
  Multi-page   → output_page_001.png, output_page_002.png, ...

Usage:
    python convert_md_to_image.py input.md [--out output.png] [--width 1240] [--dpi 150]
"""
import argparse
import re
import sys
from pathlib import Path

# A4 at 150 DPI: 1240 × 1754 px
_DEFAULT_WIDTH = 1240
_DEFAULT_DPI   = 150
_A4_RATIO      = 297 / 210  # height / width

# ── Font detection ────────────────────────────────────────────────────────────

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/meiryo.ttc",  "C:/Windows/Fonts/meiryob.ttc",  0),
    ("C:/Windows/Fonts/YuGothM.ttc", "C:/Windows/Fonts/YuGothB.ttc",  0),
    ("C:/Windows/Fonts/msgothic.ttc", "C:/Windows/Fonts/msgothic.ttc", 0),
    ("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
     "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
     "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf", 0),
]


def _load_font(path: str, size: int, idx: int = 0):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(path, size=size, index=idx)
    except Exception:
        return None


def _find_fonts(base_size: int) -> dict:
    """Return dict of {style: ImageFont}. Falls back to default bitmap font."""
    from PIL import ImageFont

    for reg, bold, idx in _FONT_CANDIDATES:
        if not Path(reg).exists():
            continue
        f_reg = _load_font(reg, base_size, idx)
        if f_reg is None:
            continue
        bp = bold if bold and Path(bold).exists() else reg
        f_bold = _load_font(bp, base_size, idx) or f_reg
        print(f"  Font: {Path(reg).name}")
        return {
            "h1":   _load_font(bp, int(base_size * 2.0), idx) or f_bold,
            "h2":   _load_font(bp, int(base_size * 1.6), idx) or f_bold,
            "h3":   _load_font(bp, int(base_size * 1.3), idx) or f_bold,
            "h4":   _load_font(bp, int(base_size * 1.1), idx) or f_bold,
            "body": f_reg,
            "bold": f_bold,
            "code": _load_font("C:/Windows/Fonts/cour.ttf", int(base_size * 0.85))
                    or _load_font("/usr/share/fonts/truetype/freefont/FreeMono.ttf", int(base_size * 0.85))
                    or f_reg,
        }

    print("  Warning: no TTF font found — Japanese text may render as boxes.", file=sys.stderr)
    default = ImageFont.load_default()
    return {k: default for k in ("h1", "h2", "h3", "h4", "body", "bold", "code")}


# ── Text wrapping ─────────────────────────────────────────────────────────────

def _wrap(text: str, font, max_px: int, draw) -> list[str]:
    """Wrap text to fit within max_px width. Handles CJK (char-level) + ASCII (word-level)."""
    if not text:
        return [""]

    def text_width(s: str) -> int:
        try:
            bbox = draw.textbbox((0, 0), s, font=font)
            return bbox[2] - bbox[0]
        except Exception:
            return len(s) * 10  # rough fallback

    # Detect if text is mostly CJK → use char-level wrapping
    cjk_chars = sum(1 for c in text if ord(c) > 0x2E7F)
    use_char_wrap = cjk_chars > len(text) * 0.3

    if use_char_wrap:
        lines = []
        current = ""
        for ch in text:
            test = current + ch
            if text_width(test) > max_px:
                if current:
                    lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)
        return lines or [""]
    else:
        # Word-level wrapping for ASCII/mixed
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip() if current else word
            if text_width(test) > max_px and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines or [""]


# ── Element rendering ─────────────────────────────────────────────────────────

class PageRenderer:
    """Renders MD elements onto A4-proportioned pages."""

    def __init__(self, width: int, fonts: dict):
        from PIL import Image, ImageDraw

        self.width = width
        self.page_height = int(width * _A4_RATIO)
        self.margin = int(width * 0.06)
        self.content_w = width - 2 * self.margin
        self.fonts = fonts
        self.pages: list = []
        self._new_page()

    def _new_page(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (self.width, self.page_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        self.pages.append(img)
        self._draw = draw
        self._y = self.margin

    @property
    def _remaining(self) -> int:
        return self.page_height - self.margin - self._y

    def _ensure_space(self, needed: int):
        if needed > self._remaining:
            self._new_page()

    def _line_height(self, font) -> int:
        try:
            bbox = self._draw.textbbox((0, 0), "Ag", font=font)
            return (bbox[3] - bbox[1]) + 4
        except Exception:
            return 20

    def _draw_text_line(self, text: str, font, color=(30, 30, 30), x_offset=0):
        lh = self._line_height(font)
        self._ensure_space(lh)
        self._draw.text((self.margin + x_offset, self._y), text, font=font, fill=color)
        self._y += lh

    def _draw_wrapped(self, text: str, font, color=(30, 30, 30), x_offset=0, indent=0):
        max_w = self.content_w - x_offset - indent
        for line in _wrap(text, font, max_w, self._draw):
            self._draw_text_line(line, font, color, x_offset + indent)

    def spacer(self, px: int = 8):
        self._y += px
        if self._y > self.page_height - self.margin:
            self._new_page()

    def heading(self, text: str, level: int):
        key = f"h{min(level, 4)}"
        font = self.fonts[key]
        lh = self._line_height(font)
        self._ensure_space(lh + 6)
        self.spacer(max(4, 14 - level * 2))
        self._draw_wrapped(text, font, color=(20, 20, 80))
        self.spacer(4)

    def paragraph(self, text: str):
        self._draw_wrapped(text, self.fonts["body"])
        self.spacer(4)

    def bullet(self, text: str, symbol: str = "•"):
        # Prefix the symbol inline — avoids page-break positioning bugs
        self._draw_wrapped(f"{symbol}  {text}", self.fonts["body"], x_offset=8)
        self.spacer(2)

    def numbered(self, text: str, n: int):
        self._draw_wrapped(f"{n}.  {text}", self.fonts["body"], x_offset=8)
        self.spacer(2)

    def code_block(self, lines_text: list[str]):
        font = self.fonts["code"]
        lh = self._line_height(font)
        for cl in lines_text:
            self._ensure_space(lh + 2)
            self._draw.rectangle(
                [self.margin - 4, self._y - 2,
                 self.margin + self.content_w + 4, self._y + lh + 2],
                fill=(242, 242, 242)
            )
            self._draw.text(
                (self.margin + 6, self._y),
                cl[:120],  # truncate very long lines
                font=font,
                fill=(60, 60, 60),
            )
            self._y += lh + 2
        self.spacer(6)

    def hr(self):
        self._ensure_space(12)
        self._draw.line(
            [(self.margin, self._y + 6), (self.margin + self.content_w, self._y + 6)],
            fill=(180, 180, 180), width=1
        )
        self._y += 12

    def table(self, rows: list[list[str]], has_header: bool):
        if not rows:
            return
        font = self.fonts["body"]
        bold = self.fonts["bold"]
        lh = self._line_height(font) + 6
        n_cols = max(len(r) for r in rows)
        col_w = self.content_w // n_cols

        for r_idx, row in enumerate(rows):
            row_h = lh
            is_hdr = has_header and r_idx == 0
            self._ensure_space(row_h)

            for c_idx in range(n_cols):
                cx = self.margin + c_idx * col_w
                # Cell background
                bg = (220, 232, 255) if is_hdr else (255, 255, 255)
                self._draw.rectangle([cx, self._y, cx + col_w - 1, self._y + row_h - 1], fill=bg)
                # Cell border
                self._draw.rectangle([cx, self._y, cx + col_w - 1, self._y + row_h - 1],
                                       outline=(160, 160, 160), width=1)
                # Cell text (truncated to fit)
                cell_text = row[c_idx] if c_idx < len(row) else ""
                f = bold if is_hdr else font
                # Simple truncation for cells
                max_chars = col_w // 9
                if len(cell_text) > max_chars:
                    cell_text = cell_text[:max_chars - 1] + "…"
                self._draw.text(
                    (cx + 4, self._y + 3), cell_text,
                    font=f, fill=(20, 20, 20)
                )
            self._y += row_h
        self.spacer(8)


# ── Parse and render ──────────────────────────────────────────────────────────

def _strip_inline(text: str) -> str:
    """Strip markdown inline markers → plain text for image rendering."""
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)   # links
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)         # images
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _parse_table_rows(table_lines: list[str]) -> tuple[list[list[str]], bool]:
    """Returns (rows, has_header)."""
    rows = []
    has_header = False
    is_first = True
    for line in table_lines:
        s = line.strip()
        if re.match(r"^\|[-| :]+\|$", s):
            has_header = True
            is_first = False
            continue
        inner = s[1:] if s.startswith("|") else s
        if inner.endswith("|"):
            inner = inner[:-1]
        cells = [_strip_inline(c.strip()) for c in inner.split("|")]
        rows.append(cells)
    return rows, has_header


def render(text: str, width: int, fonts: dict) -> list:
    """Render markdown text → list of PIL Images (pages)."""
    r = PageRenderer(width, fonts)
    lines = text.splitlines()
    i = 0
    in_code = False
    in_comment = False
    code_buf: list[str] = []
    table_buf: list[str] = []
    list_counter = 0

    def flush_table():
        if table_buf:
            rows, has_hdr = _parse_table_rows(table_buf)
            r.table(rows, has_hdr)
        table_buf.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Multi-line comment
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
                r.code_block(code_buf)
                code_buf = []
                in_code = False
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

        # Image line — skip
        if stripped.startswith("!["):
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            list_counter = 0
            r.heading(_strip_inline(m.group(2)), len(m.group(1)))
            i += 1
            continue

        # HR
        if re.match(r"^[-*_]{3,}$", stripped):
            r.hr()
            i += 1
            continue

        # Bullet
        m = re.match(r"^[-*+]\s+(.+)$", stripped)
        if m:
            r.bullet(_strip_inline(m.group(1)))
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if m:
            r.numbered(_strip_inline(m.group(2)), int(m.group(1)))
            i += 1
            continue

        # Empty
        if not stripped:
            r.spacer(6)
            i += 1
            continue

        # Normal paragraph
        r.paragraph(_strip_inline(stripped))
        i += 1

    if in_code and code_buf:
        r.code_block(code_buf)
    if table_buf:
        flush_table()

    return r.pages


def convert(input_path: Path, output_path: Path, width: int):
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    base_font_size = max(12, width // 78)
    fonts = _find_fonts(base_font_size)
    text = input_path.read_text(encoding="utf-8")
    pages = render(text, width, fonts)

    if len(pages) == 1:
        pages[0].save(str(output_path))
        print(f"Saved: {output_path}")
    else:
        stem = output_path.stem
        suffix = output_path.suffix or ".png"
        parent = output_path.parent
        for n, page in enumerate(pages, 1):
            p = parent / f"{stem}_page_{n:03d}{suffix}"
            page.save(str(p))
            print(f"  Saved: {p}")
        print(f"Done. {len(pages)} pages.")


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to PNG image(s)")
    parser.add_argument("input", help="Input .md file")
    parser.add_argument("--out", help="Output .png path (default: same dir, .png extension)")
    parser.add_argument("--width", type=int, default=_DEFAULT_WIDTH,
                        help=f"Image width in pixels (default: {_DEFAULT_WIDTH})")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.out) if args.out else input_path.with_suffix(".png")
    print(f"Converting {input_path.name} → {output_path.name} (width={args.width}px)...")
    convert(input_path, output_path, args.width)


if __name__ == "__main__":
    main()
