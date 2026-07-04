"""
roundtrip.py
Full Excel roundtrip -4 steps in one command.

  Step 1: convert_xlsx_styled.py     → _data.md + _styles.json + _images/
  Step 2: apply_style_guide.py       → _reconstructed.xlsx
  Step 3: reconstruct_xlsx_images.py → _final.<ext>
  Step 4: apply_layout_from_original.py → _patched.<ext>

Usage:
    python roundtrip.py <input.xlsx> [--out-dir <folder>] [--from-step N]

Examples:
    python roundtrip.py report.xlsm
    python roundtrip.py report.xlsm --out-dir C:/Users/me/Downloads/test_out
    python roundtrip.py report.xlsm --from-step 3   # resume after step 2 already ran
"""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent


def run_step(cmd: list, label: str) -> None:
    print(f"\n{'='*60}", flush=True)
    print(f"  {label}", flush=True)
    print(f"{'='*60}", flush=True)
    result = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"\nERROR: step failed (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)


def require(path: Path, missing_msg: str) -> None:
    if not path.exists():
        print(f"ERROR: {missing_msg}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Full Excel roundtrip: extract -> reconstruct -> images -> layout (4 steps)"
    )
    parser.add_argument("input", help="Input .xlsx or .xlsm file")
    parser.add_argument(
        "--out-dir",
        help="Output folder. Default: <input parent>/<stem>_roundtrip/",
    )
    parser.add_argument(
        "--from-step", type=int, default=1, choices=[1, 2, 3, 4],
        metavar="N",
        help="Resume from step N (1-4). Assumes prior steps' outputs already exist.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    stem = input_path.stem
    ext  = input_path.suffix  # preserve .xlsm vs .xlsx

    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
    else:
        out_dir = input_path.parent / f"{stem}_roundtrip"

    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Intermediate paths ────────────────────────────────────────────────────
    data_md       = out_dir / f"{stem}_data.md"
    styles_json   = out_dir / f"{stem}_styles.json"
    images_dir    = out_dir / f"{stem}_images"
    reconstructed = out_dir / f"{stem}_reconstructed.xlsx"
    final_file    = out_dir / f"{stem}_final{ext}"
    patched_file  = out_dir / f"{stem}_patched{ext}"

    py = sys.executable

    print(f"Input:    {input_path.name}", flush=True)
    print(f"Out dir:  {out_dir}", flush=True)
    if args.from_step > 1:
        print(f"Resuming from step {args.from_step}", flush=True)

    # ── Step 1 ────────────────────────────────────────────────────────────────
    if args.from_step <= 1:
        run_step(
            [py, str(SCRIPTS / "convert_xlsx_styled.py"),
             str(input_path), "--out", str(data_md)],
            "STEP 1/4 -Extract MD + style guide + images",
        )

    # ── Step 2 ────────────────────────────────────────────────────────────────
    if args.from_step <= 2:
        require(data_md,     f"missing {data_md.name} -run from step 1")
        require(styles_json, f"missing {styles_json.name} -run from step 1")
        run_step(
            [py, str(SCRIPTS / "apply_style_guide.py"),
             str(data_md), str(styles_json), "--out", str(reconstructed)],
            "STEP 2/4 -Reconstruct styled Excel",
        )

    # ── Step 3 ────────────────────────────────────────────────────────────────
    if args.from_step <= 3:
        require(reconstructed, f"missing {reconstructed.name} -run from step 2")
        require(images_dir,    f"missing {images_dir.name}/ -run from step 1")
        run_step(
            [py, str(SCRIPTS / "reconstruct_xlsx_images.py"),
             str(images_dir), str(input_path),
             "--reconstructed", str(reconstructed),
             "--out", str(final_file)],
            "STEP 3/4 -Splice images back",
        )

    # ── Step 4 ────────────────────────────────────────────────────────────────
    if args.from_step <= 4:
        require(final_file, f"missing {final_file.name} -run from step 3")
        run_step(
            [py, str(SCRIPTS / "apply_layout_from_original.py"),
             str(input_path), str(final_file), "--out", str(patched_file)],
            "STEP 4/4 -Copy layout from original",
        )

    print(f"\n{'='*60}")
    print(f"  ROUNDTRIP COMPLETE")
    print(f"  {patched_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
