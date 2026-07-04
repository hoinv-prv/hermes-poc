# Known Pitfalls — Excel Roundtrip Reconstruction

Lessons learned from real failures. All fixes are already applied to the scripts.

---

### 1. `xmlns:r` missing in openpyxl worksheets

openpyxl generates `<worksheet xmlns="...">` with **no** `xmlns:r`. Injecting `<drawing r:id="rId1"/>` into such a file produces invalid XML — Excel refuses to open the sheet.

**Fix (in `reconstruct_xlsx_images.py`):** Before injecting any `r:` tag, patch the `<worksheet>` opening element to add:
```
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
```

---

### 2. Extension mismatch for .xlsm source

A `.xlsm` file contains `xl/vbaProject.bin` and its `[Content_Types].xml` declares macro-enabled content types. Saving that content as `.xlsx` causes Excel: *"file format or file extension is not valid"* — hard refusal.

**Fix (in `reconstruct_xlsx_images.py`):** Default output extension matches source (`.xlsm` → `_final.xlsm`). If user explicitly requests `.xlsx`, strip VBA content first.

---

### 3. Ghost fills from openpyxl theme placeholders

openpyxl represents "no fill" as `fill_type="solid", fgColor=type='theme', theme=0, tint=0.0`. Renders as white in Excel but black in naive reconstruction. Theme indices 0 (lt1) and 1 (dk1) at `tint=0` are always openpyxl default placeholders — never real style choices.

**Fix (in `convert_xlsx_styled.py`):** `_resolve_color` skips theme idx 0 and 1 at tint=0 for both fill and font.

---

### 4. Default black text stored as explicit font color

`FF000000` (opaque black) is Excel's default font color — not an intentional style. Storing it causes every default cell to get an explicit black font in the reconstruction, overriding inherited theme fonts.

**Fix (in `convert_xlsx_styled.py`):** `_resolve_color(..., for_font=True)` skips `FF000000`.

---

### 5. OOXML theme index order is the reverse of `clrScheme` XML child order

The `clrScheme` element in `theme1.xml` lists colors as `dk1, lt1, dk2, lt2, accent1...`. A naive implementation maps index 0 → dk1. **This is wrong.**

Excel's cell `theme` attribute mapping:
- `theme="0"` = **lt1** (background, typically white `#FFFFFF`)
- `theme="1"` = **dk1** (text, typically black `#000000`)
- `theme="2"` = lt2, `theme="3"` = dk2, accent1–6 unchanged

A cell with `theme=0, tint=-0.15` resolves to `#FFFFFF` darkened 15% = `#D8D8D8` (light grey). With wrong mapping: `#000000` darkened 15% = still black. This is how grey header cells appear solid black.

**Fix (in `convert_xlsx_styled.py`):** `_THEME_SLOTS` = `["lt1", "dk1", ...]` not `["dk1", "lt1", ...]`.

---

### 6. Missing namespace declarations when injecting oleObjects / legacyDrawing

Sheets with OLE-embedded objects contain `<mc:AlternateContent>`, `<xdr:...>` anchors, etc. These require `xmlns:mc`, `xmlns:xdr`, `xmlns:x14` on the `<worksheet>` root. openpyxl only generates `xmlns="..."`. Injecting those elements without declaring their prefixes produces `HRESULT 0x808c0002` XML errors.

**Fix (in `reconstruct_xlsx_images.py`):** `_inject_sheet_extras(reconstructed_xml, extras, orig_xml)` — passing `orig_xml` copies ALL missing `xmlns:*` declarations from the original worksheet root, plus `mc:Ignorable` (required for `mc:AlternateContent` validity).
