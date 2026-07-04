"""
inject_section_markers.py
Inject <!-- Section N --> markers before each H1 heading in a docling PPTX→MD output.

Usage:
    python inject_section_markers.py <input_md> [output_md]

If output_md is omitted, writes to <input_stem>_sections.md alongside the input.
"""
import re
import sys
from pathlib import Path


def inject(input_path: Path, output_path: Path) -> int:
    with open(input_path, encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    n = 0
    for line in lines:
        if re.match(r"^# ", line):
            n += 1
            out.append(f"<!-- Section {n} -->\n")
        out.append(line)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(out)

    return n


def main():
    if len(sys.argv) < 2:
        print("Usage: inject_section_markers.py <input_md> [output_md]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_name(input_path.stem + "_sections.md")

    n = inject(input_path, output_path)
    print(f"Done. {n} section markers injected → {output_path}")


if __name__ == "__main__":
    main()
