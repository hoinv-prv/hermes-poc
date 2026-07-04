---
name: docling-convert
description: >
  Convert documents to/from Markdown and perform Excel roundtrip reconstruction.
  Use this skill whenever the user wants to: convert any file (PDF, DOCX, PPTX, XLSX, XLSM, PNG/JPG) to Markdown;
  convert Markdown to Word (.docx), PDF, PNG, or Excel (.xlsx); extract images from Excel or PowerPoint;
  reconstruct a styled Excel file from extracted content (roundtrip); extract styled text from PDF; or do OCR on images.
  Trigger even if the user just says "convert this file", "extract content", "rebuild the Excel",
  "convert MD to Excel", "make a Word doc from this MD", or mentions docling.
user-invocable: true
---

# SKILL: docling-convert

## Purpose
Convert documents to/from structured Markdown via docling, with format-aware post-processing.

**Input → MD:** PDF, DOCX, PPTX, XLSX/XLSM, PNG/JPG/JPEG/TIFF — all via docling
**MD → Output:** DOCX (python-docx). PDF: open .docx in Word → File > Export.

Structured extras:
- PPTX / DOCX / PDF: `<!-- Section N -->` markers before each heading
- XLSX/XLSM: per-sheet `# Sheet: Name` headers + image index

## Prerequisites

```
pip install docling          # required for all input conversions
pip install python-docx      # required for MD → DOCX output only
```

`docling` pulls openpyxl, python-pptx, torch, etc. automatically.

---

## Scripts

All scripts are at `.claude/skills/docling-convert/scripts/`. Run from project root.

| Script | Purpose |
|---|---|
| `convert_to_md.py` | **Universal input converter** — any format (PDF/DOCX/PPTX/XLSX/XLSM/images) → MD; auto-routes to right pipeline |
| `convert_xlsx_styled.py` | **Excel → MD (styled)** — extracts cell data + styles.json guide; two modes: extract / roundtrip |
| `apply_style_guide.py` | **styles.json + data.md → Excel** — reconstructs a styled .xlsx from the roundtrip pair |
| `reconstruct_xlsx_images.py` | **Merge cell data + images** — splices reconstructed cell data into original's drawing infrastructure |
| `apply_layout_from_original.py` | **Copy layout from original** — copies column widths, row heights, page setup from original to final (Step 4) |
| `roundtrip.py` | **Full roundtrip orchestrator** — runs all 4 steps in sequence; supports `--from-step N` to resume |
| `screenshot_sheets.py` | **Screenshot Excel sheets** — uses win32com + PyMuPDF; one PNG per sheet for visual verification |
| `convert_md_to_docx.py` | **MD → DOCX** — headings, tables, lists, inline formatting via python-docx |
| `convert_md_to_pdf.py` | **MD → PDF** — A4 PDF with Japanese font auto-detect via reportlab |
| `convert_md_to_image.py` | **MD → PNG** — A4-paged PNG(s) with Japanese font via Pillow |
| `inject_section_markers.py` | Add `<!-- Section N -->` before every H1 in a PPTX-converted MD |
| `convert_sheets.py` | Split XLSX/XLSM by sheet, convert each, merge with `# Sheet: Name` headers |
| `extract_sheet_image.py` | Extract Nth image from a named sheet using the original single-pass MD |
| `build_image_index.py` | Map all images in an XLSX MD to sheet name + index + context; produces JSON + MD index |
| `convert_styled_md_to_xlsx.py` | **Styled MD → Excel** — reconstructs `.xlsx` from a styled MD (produced by `convert_xlsx_styled.py`): cell values, fill colors, font, merged cells, column widths, borders |
| `convert_pdf_styled.py` | **PDF → styled MD** — extracts font size/bold/italic/color via PyMuPDF; maps to H1–H3 headings, `**bold**`, `*italic*`, color comments |

---

## Universal Converter (any format → MD)

Single command for any input type. Auto-detects format and runs the right pipeline.

```
python .claude/skills/docling-convert/scripts/convert_to_md.py <input_file> [--out-dir output/]
```

| Input | What happens |
|---|---|
| `.pdf` | docling → MD + section markers (if headings exist) |
| `.docx` / `.doc` | docling → MD + section markers (if headings exist) |
| `.pptx` | docling → MD + section markers |
| `.xlsx` / `.xlsm` | docling → orig MD + per-sheet MD + image index (full 3-step pipeline) |
| `.png` / `.jpg` / `.jpeg` / `.tiff` | docling OCR → MD (text extraction) |

Add `--no-section-markers` to skip section injection for PDF/DOCX/PPTX.

---

## MD → DOCX

```
pip install python-docx   # one-time
python .claude/skills/docling-convert/scripts/convert_md_to_docx.py input.md [--out output.docx]
```

Supports: H1–H4, paragraphs, **bold**, *italic*, `inline code`, links (text only), tables, bullet/numbered lists, code blocks, HR. Base64 image blobs stripped.

---

## MD → PDF

```
pip install reportlab     # one-time
python .claude/skills/docling-convert/scripts/convert_md_to_pdf.py input.md [--out output.pdf]
```

A4 PDF. Japanese font auto-detected: Meiryo → Yu Gothic → MS Gothic → HeiseiKakuGo-W5 (CID fallback) → Helvetica (ASCII-only last resort). Same element support as MD → DOCX.

---

## MD → PNG

```
pip install Pillow        # one-time
python .claude/skills/docling-convert/scripts/convert_md_to_image.py input.md [--out output.png] [--width 1240]
```

Outputs A4-proportioned PNG pages at 150 DPI equivalent.
- Single page → `output.png`
- Multi-page → `output_page_001.png`, `output_page_002.png`, ...

Japanese font auto-detected (same priority as PDF). Default width: 1240 px (A4 at 150 DPI).

---

## PPTX Workflow

### Step 1 — Convert with docling CLI

```
docling <file.pptx> --to md --output output/
```

### Step 2 — Inject section markers

```
python .claude/skills/docling-convert/scripts/inject_section_markers.py \
  output/<file>.md \
  output/<file>_sections.md
```

Output: `<!-- Section N -->` injected before every `# Heading` in document order.

### Known limitations (PPTX)

- **H1 = one slide** — docling emits one H1 per slide that has a title. Image-only or section-divider slides produce no H1 and are silently skipped.
- **Section count ≠ slide count** — PPTX with 110 slides may yield 88 H1s. Section numbers are sequential within the MD, not PPTX slide numbers.
- **Matching PPTX slide numbers to sections is unreliable** — many PPTX files have repeated slide titles (e.g., 14 slides all titled "一般衛生管理計画"). Title-based matching breaks when duplicates exist. The sequential H1 approach is the reliable fallback.
- **Images** — embedded as `![Image](data:image/png;base64,...)` blobs. Self-contained but large. Extract with PowerShell or Python base64 decode.

---

## XLSX / XLSM Workflow

### Step 1 — Convert full file with docling (single pass, keeps images)

```
docling <file.xlsm> --to md --output output/
```

This is the **origin MD** — keep it. It contains all base64 images but no sheet labels.

### Step 2 — Per-sheet conversion (adds sheet labels, loses images)

```
python .claude/skills/docling-convert/scripts/convert_sheets.py \
  <file.xlsm> \
  --out output/<file>_sheets.md
```

Output: one `# Sheet: Name` header per sheet, followed by that sheet's table content.

### Step 3 — Build image index (recommended before extracting)

```
python -X utf8 .claude/skills/docling-convert/scripts/build_image_index.py \
  --orig-md output/<file>.md \
  --sheets-md output/<file>_sheets.md \
  --out-dir output/
```

Outputs:
- `<stem>_image_index.json` — machine-readable (for scripts)
- `<stem>_image_index.md` — navigation table: sheet name, image number, size, surrounding text context

AI agent workflow:
1. Read `_image_index.md` → find target image by sheet + context keywords
2. Call `extract_sheet_image.py --n <N>` with the correct sheet + image number
3. Read extracted PNG → display or analyze

### Step 4 — Extract image from a specific sheet (when needed)

Images show as `<!-- image -->` in the per-sheet MD because openpyxl cannot faithfully round-trip Excel drawings into new workbooks. Use the original single-pass MD for image extraction.

```
python -X utf8 .claude/skills/docling-convert/scripts/extract_sheet_image.py \
  --orig-md output/<file>.md \
  --sheets-md output/<file>_sheets.md \
  --sheet "1.4.店長確認" \
  --n 1 \
  --out output/sheet_1_4_img1.png
```

> **Windows note:** Use `python -X utf8` (or set `PYTHONUTF8=1`) when `--sheet` contains non-ASCII characters. Without it, cp932 console encoding corrupts the argument.

The script:
1. Reads unique text from the named sheet in the per-sheet MD
2. Locates that text in the original MD to anchor the sheet boundary
3. Extracts the Nth base64 PNG from that position forward

### Known limitations (XLSX/XLSM)

- **Sheet names not in original MD** — docling flattens the entire workbook. No sheet separators exist in the single-pass output.
- **Per-sheet images lost** — openpyxl cannot reliably copy Excel drawings (drawio objects, embedded images with complex anchor types) to new workbooks. The per-sheet xlsx files will have `<!-- image -->` placeholders.
- **Merged cells expand** — docling expands merged cells into duplicate column values. Tables can be very wide and noisy.
- **Empty sheets** — sheets with no cell content (only images) produce `_(empty sheet)_` in the per-sheet MD. Their images are still accessible via `extract_sheet_image.py` using text from nearby sheets.
- **Image-to-sheet mapping** — images in the original MD appear in workbook order. The text-anchor strategy works for sheets with unique text. If a sheet has no unique text, try anchoring from the previous sheet's last known text and counting images from there.

---

## Image Extraction — Quick Reference

**From PPTX MD (base64 blobs)**:
```python
import re, base64
with open("file.md", encoding="utf-8") as f:
    content = f.read()
imgs = re.findall(r"!\[Image\]\(data:image/png;base64,([A-Za-z0-9+/=]+)\)", content)
# imgs[0] = first image, imgs[N-1] = Nth image
with open("output.png", "wb") as f:
    f.write(base64.b64decode(imgs[0]))
```

**From XLSX MD — use extract_sheet_image.py** (see Step 3 above).

---

## Output Path Behavior

Scripts do not hardcode output paths. When a user provides a file to convert:
- If they specify an output path or folder → use it
- If they mention context ("save to Downloads", "put it next to the source") → follow that
- Otherwise → infer from context (same folder as input, or a test/output folder if one exists nearby)

Never default to the source file's directory without checking where it lives — source files may be on network drives (Google Drive, SharePoint). Output should go somewhere local and writable (e.g. `C:\Users\...\Downloads\`).

Images folder from `convert_xlsx_styled.py` goes in the **same directory as the output `.md`**, not next to the source file.

---

## Decision Guide

| Input | Goal | Use |
|---|---|---|
| Any format | Convert to MD (one command) | `convert_to_md.py <file>` |
| PDF | Convert to readable MD | `convert_to_md.py file.pdf` |
| DOCX | Convert to readable MD | `convert_to_md.py file.docx` |
| PPTX | Convert to readable MD with slide context | `convert_to_md.py file.pptx` |
| XLSX/XLSM | Convert with sheet labels + image index | `convert_to_md.py file.xlsm` |
| XLSX/XLSM | Find which sheet an image belongs to | build_image_index.py → read `_image_index.md` |
| XLSX/XLSM | View image from specific sheet | `extract_sheet_image.py` |
| XLSX/XLSM | Read text content of specific sheet | Per-sheet MD → `# Sheet: Name` section |
| PNG/JPG/JPEG | Extract text via OCR | `convert_to_md.py file.png` |
| MD | Produce Word document | `convert_md_to_docx.py file.md` |
| MD | Produce PDF | `convert_md_to_pdf.py file.md` |
| MD | Produce PNG image(s) | `convert_md_to_image.py file.md` |
| Styled MD (from roundtrip extract) | Reconstruct Excel with full styling | `convert_styled_md_to_xlsx.py file.md` |
| PDF | Extract text + headings + bold/italic/colors | `convert_pdf_styled.py file.pdf` |

---

## Excel Roundtrip Workflow (styled reconstruction)

Use this when you need to reproduce a styled Excel from extracted content — or apply existing styles to new content.

### Prerequisites

```
pip install openpyxl pywin32 pymupdf   # pywin32 + pymupdf for screenshots (Windows only)
```

### One-command roundtrip

```
python .claude/skills/docling-convert/scripts/roundtrip.py input.xlsm [--out-dir C:\path\to\output\]
```

Runs all 4 steps. Output folder defaults to `<input parent>/<stem>_roundtrip/`.
Use `--from-step N` to resume after a failed step without re-running earlier ones.

**Final output:** `<stem>_patched<ext>` — styled + images + layout from original.

---

### Step 1 — Extract MD + style guide

```
python .claude/skills/docling-convert/scripts/convert_xlsx_styled.py input.xlsm
```

Mode is chosen once (`~/.docling_convert_config.json`) — use `--reset` to change.

- **extract**: `_data.md` only (fast, LLM-readable)
- **roundtrip**: `_data.md` + `_styles.json` + `_images/` folder + auto-screenshots for AI style verification

### Step 2 — (Roundtrip only) Reconstruct styled Excel

```
python .claude/skills/docling-convert/scripts/apply_style_guide.py \
  input_data.md input_styles.json [--out output.xlsx]
```

Produces a styled `.xlsx`. Cell data comes from the MD, styling from the JSON.
**This file has NO images yet.**

### Step 3 — (Roundtrip only) Splice images back

```
python .claude/skills/docling-convert/scripts/reconstruct_xlsx_images.py \
  input_images/ input.xlsm \
  --reconstructed output_from_guide.xlsx \
  --out final.xlsm
```

Merges:
- Cell data from `--reconstructed` (openpyxl output)
- Drawing XMLs, sheet rels, media files from `original.xlsm`

**Output extension must match the original** (`.xlsm` → `.xlsm`). See Known Pitfalls.

### Step 4 — (Roundtrip only) Apply layout from original

```
python .claude/skills/docling-convert/scripts/apply_layout_from_original.py \
  input.xlsm final.xlsm [--out patched.xlsm]
```

Copies per-sheet from original → final:
- All custom column widths + `defaultColWidth` (openpyxl only captures explicitly-set columns; default width is silently wrong otherwise)
- All row heights + `defaultRowHeight`
- Page setup: margins, orientation, paper size, fitToPage/fitToWidth/fitToHeight, print area, freeze panes

**Why needed:** `apply_style_guide.py` only applies column widths that were explicitly captured in `_styles.json`. Sheets where most columns use the sheet's default width (e.g. `defaultColWidth=14.43`) look squished until this step runs.

### Decision table

| Goal | Use |
|---|---|
| Read/edit cell content only | extract mode → `_data.md` |
| Reproduce original styling | roundtrip → all 4 steps |
| Apply template style to new content | roundtrip extract + edit `_data.md` + steps 2–4 |

---

## Known Pitfalls (image reconstruction)

See [`references/pitfalls.md`](references/pitfalls.md) for full details on all 6 known failure modes. Summary:

1. `xmlns:r` missing → inject namespace before adding `r:id` drawing tags
2. `.xlsm` → `.xlsx` extension mismatch → always match source extension
3. Ghost fills from openpyxl theme placeholders (theme 0/1 at tint=0) → skip them
4. `FF000000` stored as explicit font color → skip it (it's Excel's default)
5. OOXML theme index 0 = lt1 (white), NOT dk1 — opposite of `clrScheme` XML order
6. Missing `xmlns:mc/xdr/x14` when injecting oleObjects → copy all ns from original root

**Read `references/pitfalls.md` when:** a script produces an Excel file Excel refuses to open, colours look wrong, or you're modifying any of the reconstruction scripts.

---

## Verified Environment

- Windows 11, Python 3.13.3
- docling 2.92.0, torch 2.11.0+cpu (CPU-only, no CUDA)
- openpyxl 3.x, python-pptx (bundled via docling deps)
- First run downloads AI models (~GB) — internet required
