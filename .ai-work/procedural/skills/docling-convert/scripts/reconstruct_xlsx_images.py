"""
reconstruct_xlsx_images.py
Reconstruct an xlsx by merging cell data + drawing infrastructure.

Two modes:

  WITH original (default):
    Base = original file. Cell data swapped from --reconstructed.
    Drawing refs injected from original worksheet XMLs.

  WITHOUT original (--no-original):
    Base = --reconstructed file. Drawing infrastructure added entirely
    from manifest.json (drawings, rels, sheet rels, content types).
    Original file not needed at all.

Usage:
    # Standard (original available):
    python reconstruct_xlsx_images.py <images_folder> <original.xlsx> \\
        --reconstructed <reconstructed.xlsx> [--out output.xlsx]

    # Self-contained (original not needed):
    python reconstruct_xlsx_images.py <images_folder> \\
        --no-original --reconstructed <reconstructed.xlsx> [--out output.xlsx]

    # Legacy (no cell swap):
    python reconstruct_xlsx_images.py <images_folder> <original.xlsx>
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_TAKE_FROM_RECO = {"xl/styles.xml", "xl/sharedStrings.xml"}
_SHEET_RE = re.compile(r"^xl/worksheets/(sheet\d+\.xml)$")

_EXTRA_TAGS = [
    re.compile(r'<drawing\b[^>]*/>',           re.DOTALL),
    re.compile(r'<legacyDrawing\b[^>]*/>',     re.DOTALL),
    re.compile(r'<oleObjects\b.*?</oleObjects>',re.DOTALL),
    re.compile(r'<tableParts\b[^>]*/>',        re.DOTALL),
    re.compile(r'<picture\b[^>]*/>',           re.DOTALL),
]

_R_NS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

_NS_DECL_RE = re.compile(r'xmlns:(\w+)="([^"]*)"')
_WORKSHEET_TAG_RE = re.compile(r'(<worksheet\b[^>]*>)', re.DOTALL)
_MC_IGNORABLE_RE = re.compile(r'\bmc:Ignorable="([^"]*)"')


def _extract_ns_map(xml_text: str) -> dict:
    """Return {prefix: uri} for all xmlns:* declarations on the worksheet root element."""
    m = _WORKSHEET_TAG_RE.search(xml_text)
    if not m:
        return {}
    return dict(_NS_DECL_RE.findall(m.group(1)))


def _extract_sheet_extras(worksheet_xml: bytes) -> str:
    text = worksheet_xml.decode("utf-8", errors="replace")
    found = []
    for pat in _EXTRA_TAGS:
        for m in pat.finditer(text):
            tag = m.group(0).strip()
            if tag not in found:
                found.append(tag)
    return "\n  ".join(found)


def _inject_sheet_extras(reconstructed_xml: bytes, extras: str,
                         orig_xml: "bytes | None" = None) -> bytes:
    """Insert extra elements before </worksheet>.

    When orig_xml is provided, copies ALL missing xmlns:* declarations from the
    original worksheet root plus mc:Ignorable — both are required for
    mc:AlternateContent/oleObjects to work correctly in Excel.
    """
    if not extras:
        return reconstructed_xml
    text = reconstructed_xml.decode("utf-8", errors="replace")
    to_add: list[str] = []

    if orig_xml:
        orig_text = orig_xml.decode("utf-8", errors="replace")
        orig_ns = _extract_ns_map(orig_text)
        # Copy ALL namespace declarations from original root that are missing
        for prefix, uri in orig_ns.items():
            if f'xmlns:{prefix}=' not in text:
                to_add.append(f'xmlns:{prefix}="{uri}"')
        # Also carry over mc:Ignorable — required for mc:AlternateContent validity
        mi = _MC_IGNORABLE_RE.search(orig_text[:2000])  # only in root element
        if mi and 'mc:Ignorable=' not in text:
            to_add.append(f'mc:Ignorable="{mi.group(1)}"')
    else:
        # Fallback: at minimum ensure xmlns:r is present
        if "r:" in extras and "xmlns:r=" not in text:
            to_add.append(_R_NS)

    if to_add:
        additions = " ".join(to_add)
        text = text.replace("<worksheet ", f"<worksheet {additions} ", 1)

    text = text.replace("</worksheet>", f"\n  {extras}\n</worksheet>", 1)
    return text.encode("utf-8")


def _drawing_tags_from_sheet_rels(rels_xml: str) -> str:
    """Parse a sheet rels XML and return <drawing r:id="..."/> tags for each drawing rel."""
    try:
        root = ET.fromstring(rels_xml)
    except ET.ParseError:
        return ""
    tags = []
    for rel in root:
        rel_type = rel.get("Type", "")
        if "/drawing" in rel_type and "vml" not in rel_type.lower():
            rid = rel.get("Id", "")
            if rid:
                tags.append(f'<drawing r:id="{rid}"/>')
    return "\n  ".join(tags)


# ── Mode 1: original file available ──────────────────────────────────────────

def reconstruct_with_original(
    images_dir: Path,
    original_path: Path,
    output_path: Path,
    reconstructed_path: "Path | None",
    manifest: dict,
):
    registered_images: set = set(manifest.get("images", []))
    drawing_overrides: dict = manifest.get("drawings", {})

    reco_files: dict = {}
    if reconstructed_path:
        with zipfile.ZipFile(str(reconstructed_path), "r") as rz:
            for name in rz.namelist():
                if name in _TAKE_FROM_RECO or _SHEET_RE.match(name):
                    reco_files[name] = rz.read(name)
        print(f"Base:        {original_path.name}")
        print(f"Cell data:   {reconstructed_path.name} ({len(reco_files)} file(s))")
    else:
        print(f"Base:        {original_path.name}  (legacy - no cell data swap)")

    print(f"Images:      {images_dir.name}/ ({len(registered_images)} registered)")
    print(f"Drawings:    {len(drawing_overrides)} XML override(s)\n")

    orig_sheets: dict = {}
    if reco_files:
        with zipfile.ZipFile(str(original_path), "r") as oz:
            for name in oz.namelist():
                if _SHEET_RE.match(name):
                    orig_sheets[name] = oz.read(name)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(str(original_path), "r") as src_zip:
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as dst_zip:
            for item in src_zip.infolist():
                name = item.filename
                stem = Path(name).name

                if name in reco_files:
                    data = reco_files[name]
                    if _SHEET_RE.match(name) and name in orig_sheets:
                        orig_xml = orig_sheets[name]
                        extras = _extract_sheet_extras(orig_xml)
                        data = _inject_sheet_extras(data, extras, orig_xml)
                        label = f"merged ({stem})" + (" +drawing" if extras else "")
                    else:
                        label = name
                    print(f"  Cell data:  {label}")
                    dst_zip.writestr(item, data)
                    continue

                if name.startswith("xl/media/") and stem in registered_images:
                    replacement = images_dir / stem
                    if replacement.exists():
                        dst_zip.write(str(replacement), name)
                        print(f"  Img swap:   {stem}")
                        continue

                if "drawings/" in name and name.endswith(".xml") and stem in drawing_overrides:
                    dst_zip.writestr(item, drawing_overrides[stem].encode("utf-8"))
                    print(f"  Drawing:    {stem}")
                    continue

                dst_zip.writestr(item, src_zip.read(name))

    print(f"\nSaved: {output_path}")


# ── Mode 2: no original — build entirely from manifest + reconstructed ────────

def reconstruct_from_manifest(
    images_dir: Path,
    reconstructed_path: Path,
    output_path: Path,
    manifest: dict,
):
    registered_images: set = set(manifest.get("images", []))
    drawing_overrides: dict = manifest.get("drawings", {})
    drawing_rels: dict = manifest.get("drawing_rels", {})
    sheet_rels_map: dict = manifest.get("sheet_rels", {})
    ct_overrides: list = manifest.get("content_type_overrides", [])

    # Map sheet XML path → drawing tags to inject
    # sheet_rels key: "sheet1.xml.rels" → derive "xl/worksheets/sheet1.xml"
    sheet_drawing_tags: dict = {}
    for rels_filename, rels_content in sheet_rels_map.items():
        sheet_xml_name = rels_filename[:-5]  # strip ".rels"
        sheet_path = f"xl/worksheets/{sheet_xml_name}"
        tags = _drawing_tags_from_sheet_rels(rels_content)
        if tags:
            sheet_drawing_tags[sheet_path] = tags

    if not drawing_overrides:
        print("WARNING: manifest has no drawings — output will have no images.")

    print(f"Mode:        manifest-only (no original file)")
    print(f"Cell data:   {reconstructed_path.name}")
    print(f"Images:      {images_dir.name}/ ({len(registered_images)} registered)")
    print(f"Drawings:    {len(drawing_overrides)} XMLs, "
          f"{len(drawing_rels)} rels, "
          f"{len(sheet_rels_map)} sheet rels\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(str(reconstructed_path), "r") as src_zip:
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as dst_zip:

            for item in src_zip.infolist():
                name = item.filename
                data = src_zip.read(name)

                # Patch Content_Types to include drawing + media entries
                if name == "[Content_Types].xml" and ct_overrides:
                    xml_text = data.decode("utf-8")
                    inject = "\n  ".join(ct_overrides)
                    xml_text = xml_text.replace("</Types>", f"  {inject}\n</Types>")
                    data = xml_text.encode("utf-8")
                    print(f"  CT patched: +{len(ct_overrides)} entries")

                # Inject drawing refs into worksheet XMLs
                elif _SHEET_RE.match(name) and name in sheet_drawing_tags:
                    data = _inject_sheet_extras(data, sheet_drawing_tags[name])
                    print(f"  Sheet:      {Path(name).name} +drawing")

                dst_zip.writestr(item, data)

            # Add drawing XMLs
            for filename, content in drawing_overrides.items():
                dst_zip.writestr(f"xl/drawings/{filename}", content.encode("utf-8"))
                print(f"  Drawing:    {filename}")

            # Add drawing rels
            for filename, content in drawing_rels.items():
                dst_zip.writestr(f"xl/drawings/_rels/{filename}", content.encode("utf-8"))
                print(f"  Drw rel:    {filename}")

            # Add sheet rels (sheet → drawing links)
            for filename, content in sheet_rels_map.items():
                dst_zip.writestr(f"xl/worksheets/_rels/{filename}", content.encode("utf-8"))
                print(f"  Sheet rel:  {filename}")

            # Add media files
            for stem in registered_images:
                img_file = images_dir / stem
                if img_file.exists():
                    dst_zip.write(str(img_file), f"xl/media/{stem}")
                    print(f"  Image:      {stem}")

    print(f"\nSaved: {output_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Merge reconstructed cell data + drawing infrastructure"
    )
    parser.add_argument("images_dir",      help="Folder with manifest.json + images")
    parser.add_argument("original",        nargs="?", default=None,
                        help="Original .xlsx/.xlsm  (drawing source; omit with --no-original)")
    parser.add_argument("--no-original",   action="store_true",
                        help="Build entirely from manifest — original file not needed")
    parser.add_argument("--reconstructed", help="apply_style_guide.py output (cell data)")
    parser.add_argument("--out",           help="Output path")
    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    if not images_dir.exists():
        print(f"ERROR: not found: {images_dir}", file=sys.stderr)
        sys.exit(1)

    manifest_path = images_dir / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: manifest.json not found. Re-run in roundtrip mode.", file=sys.stderr)
        sys.exit(1)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    no_original = args.no_original or args.original is None

    if no_original:
        if not args.reconstructed:
            print("ERROR: --reconstructed required with --no-original.", file=sys.stderr)
            sys.exit(1)
        reco_path = Path(args.reconstructed)
        if not reco_path.exists():
            print(f"ERROR: not found: {reco_path}", file=sys.stderr)
            sys.exit(1)
        out = Path(args.out) if args.out else reco_path.with_name(
            re.sub(r"_reconstructed$|_from_guide$", "", reco_path.stem) + "_final" + reco_path.suffix
        )
        print(f"Reconstructing -> {out.name} ...\n")
        reconstruct_from_manifest(images_dir, reco_path, out, manifest)

    else:
        original_path = Path(args.original)
        if not original_path.exists():
            print(f"ERROR: not found: {original_path}", file=sys.stderr)
            sys.exit(1)
        reco_path = None
        if args.reconstructed:
            reco_path = Path(args.reconstructed)
            if not reco_path.exists():
                print(f"ERROR: not found: {reco_path}", file=sys.stderr)
                sys.exit(1)
        out = Path(args.out) if args.out else original_path.with_name(
            original_path.stem + "_final" + original_path.suffix
        )
        print(f"Reconstructing -> {out.name} ...\n")
        reconstruct_with_original(images_dir, original_path, out, reco_path, manifest)


if __name__ == "__main__":
    main()
