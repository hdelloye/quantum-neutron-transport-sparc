"""LOCAL ONLY: re-render every registered figure from its committed JSON (ANLY-05), no sweep.

    scripts/render_figures.py                     # re-render all figures into data/
    scripts/render_figures.py --only scaling_rmse # one kind (repeatable)
    scripts/render_figures.py --check             # render into a temp dir, compare with the committed PNGs

``--check`` never writes under data/: it confirms each committed PNG's dimensions and the PNG budget.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from neutron_qae import artifacts, figures


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", metavar="KIND", help="render only this kind (repeatable)")
    ap.add_argument("--out-dir", default=str(ROOT / "data"), help="output directory (default data/)")
    ap.add_argument("--dpi", type=int, default=figures.DEFAULT_DPI, help="PNG dpi (default 110)")
    ap.add_argument("--check", action="store_true",
                    help="render into a temporary directory and compare with the committed PNGs")
    args = ap.parse_args(argv)
    os.chdir(ROOT)
    kinds = args.only or list(artifacts.ARTIFACTS)
    unknown = [k for k in kinds if k not in artifacts.ARTIFACTS or k not in figures.RENDERERS]
    if unknown:
        print(f"unknown kind(s) {unknown}; registered: {sorted(artifacts.ARTIFACTS)}", file=sys.stderr)
        return 2

    if not args.check:
        out_dir = pathlib.Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for kind in kinds:
            json_rel, png_rel = artifacts.ARTIFACTS[kind]
            info = figures.render_file(kind, json_rel, out_dir / os.path.basename(png_rel), args.dpi)
            print(f"RENDERED {kind} {os.path.basename(png_rel)} {info['width']}x{info['height']} {info['bytes']}B")
        return 0

    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        for kind in kinds:
            json_rel, png_rel = artifacts.ARTIFACTS[kind]
            info = figures.render_file(kind, json_rel, pathlib.Path(tmp) / os.path.basename(png_rel),
                                       figures.DEFAULT_DPI)
            committed = artifacts.png_dimensions(png_rel)
            if (info["width"], info["height"]) != committed:
                problems.append(f"MISMATCH {kind}: rendered {info['width']}x{info['height']}, "
                                f"committed {committed[0]}x{committed[1]}")
            if info["bytes"] > artifacts.PNG_BUDGET_BYTES:
                problems.append(f"MISMATCH {kind}: rendered {info['bytes']}B above the "
                                f"{artifacts.PNG_BUDGET_BYTES}B PNG budget")
    for line in problems:
        print(line)
    if problems:
        return 1
    print(f"RENDER CHECK OK {len(kinds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
