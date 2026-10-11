"""LOCAL ONLY: shared plumbing for the Phase 5 sweep scripts (argument parser, provenance, finish).

Each sweep script selects matplotlib's Agg backend before importing ``neutron_qae.figures``,
puts the repo root on sys.path and works from the repo root (``os.chdir(ROOT)``), so the
literal ``data/...`` paths resolve exactly as they do on Qollab.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import platform
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from neutron_qae import artifacts, figures

DEFAULT_SEED = 2026


def base_parser(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help="root SeedSequence seed (default 2026)")
    ap.add_argument("--profile", choices=["quick", "full"], default="full", help="sweep size (default full)")
    ap.add_argument("--out-dir", default=str(ROOT / "data"), help="output directory (default data/)")
    ap.add_argument("--dpi", type=int, default=figures.DEFAULT_DPI, help="PNG dpi (default 110)")
    return ap


def git_state() -> tuple[str, bool]:
    """(HEAD commit, dirty) where dirty means any uncommitted change under neutron_qae/, scripts/ or main.py."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--",
                             "neutron_qae", "scripts", "main.py"], cwd=ROOT, check=True, capture_output=True,
                            text=True).stdout
    dirty = any(line and "__pycache__" not in line for line in status.splitlines())
    return head, dirty


def versions() -> dict:
    import matplotlib
    import numpy
    import qiskit

    out = {"python": platform.python_version(), "numpy": numpy.__version__, "qiskit": qiskit.__version__,
           "matplotlib": matplotlib.__version__}
    try:
        import qiskit_aer

        out["qiskit_aer"] = qiskit_aer.__version__
    except ImportError:
        pass
    return out


def provenance(seed: int, script: str, argv, timings: dict) -> dict:
    head, dirty = git_state()
    return {
        "seed": int(seed),
        "git_head": head,
        "git_dirty": bool(dirty),
        "script": script,
        "argv": [str(a) for a in argv],
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "versions": versions(),
        "platform": platform.platform(),
        "timings_s": {k: round(float(v), 2) for k, v in timings.items()},
    }


def finish(doc: dict, kind: str, out_dir, dpi: int) -> tuple[dict, dict]:
    """Write the artifact JSON, render its PNG from that file, print WROTE / RENDERED lines."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_rel, png_rel = artifacts.ARTIFACTS[kind]
    json_path = out_dir / os.path.basename(json_rel)
    png_path = out_dir / os.path.basename(png_rel)
    n = artifacts.write_artifact(doc, json_path)
    info_json = {"path": str(json_path), "bytes": n}
    print(f"WROTE {json_path.name} {n}B", flush=True)
    info_png = figures.render_file(kind, json_path, png_path, dpi)
    print(f"RENDERED {png_path.name} {info_png['width']}x{info_png['height']} {info_png['bytes']}B", flush=True)
    return info_json, info_png
