"""LOCAL ONLY: the only writer of the frozen Kernels golden file; regenerating it is an explicit contract change.

Usage:
    python scripts/freeze_kernels.py                  # check mode: rebuild and compare with the golden (exit 0/1)
    python scripts/freeze_kernels.py --write          # create the golden; refuses (exit 2) if it already exists
    python scripts/freeze_kernels.py --write --force  # overwrite: a contract change (bump KERNELS_CONTRACT_VERSION)

The golden file is written with the stdlib json module (floats as repr, so every value
round-trips exactly) and read back with json.load; nothing here uses pickle.
"""
import argparse
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neutron_qae.exact import REGISTER_LAYOUT, exit_row_distribution_k1, transmission_within  # noqa: E402
from neutron_qae.kernels import (  # noqa: E402
    KERNELS_CONTRACT_VERSION,
    N_PHI_NODES,
    N_X_NODES,
    OUTCOMES,
    build_kernels,
)
from neutron_qae.problem import DEFAULT_MODEL, sparc_first_wall, spec_fingerprint  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / f"kernels_v{KERNELS_CONTRACT_VERSION}.json"
RTOL, ATOL = 1e-12, 1e-15
EXACT_KEYS = ("contract_version", "model", "spec_fingerprint", "quadrature", "register_layout")
NUMERIC_KEYS = ("T0", "T1", "first_collision", "scatter_ratio", "flight", "back_exit_rows", "exit_rows_k1")


def golden_document() -> dict:
    spec = sparc_first_wall(DEFAULT_MODEL)
    k = build_kernels(spec)
    return {
        "contract_version": KERNELS_CONTRACT_VERSION,
        "model": DEFAULT_MODEL,
        "spec_fingerprint": spec_fingerprint(spec),
        "spec": dataclasses.asdict(spec),
        "quadrature": {"n_x_nodes": N_X_NODES, "n_phi_nodes": N_PHI_NODES},
        "register_layout": REGISTER_LAYOUT,
        "outcomes": list(OUTCOMES),
        "T0": transmission_within(k, 0),
        "T1": transmission_within(k, 1),
        "first_collision": k.first_collision.tolist(),
        "scatter_ratio": k.scatter_ratio.tolist(),
        "flight": k.flight.tolist(),
        "back_exit_rows": k.back_exit_rows.tolist(),
        "exit_rows_k1": exit_row_distribution_k1(k).tolist(),
    }


def compare(doc: dict, golden: dict) -> list[str]:
    problems = []
    for key in EXACT_KEYS:
        if golden.get(key) != doc[key]:
            problems.append(f"{key}: golden {golden.get(key)!r} != rebuilt {doc[key]!r}")
    for key in NUMERIC_KEYS:
        if key not in golden:
            problems.append(f"{key}: missing from golden")
            continue
        a, b = np.asarray(doc[key], dtype=float), np.asarray(golden[key], dtype=float)
        if a.shape != b.shape:
            problems.append(f"{key}: shape {b.shape} in golden != rebuilt {a.shape}")
        elif not np.allclose(a, b, rtol=RTOL, atol=ATOL):
            problems.append(f"{key}: max abs diff {np.max(np.abs(a - b))!r} exceeds rtol {RTOL} / atol {ATOL}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write the golden file (refuses to overwrite without --force)")
    ap.add_argument("--force", action="store_true", help="with --write: overwrite an existing golden (contract change)")
    args = ap.parse_args(argv)
    rel = GOLDEN.relative_to(ROOT).as_posix()

    if args.write:
        if GOLDEN.exists() and not args.force:
            print(f"refusing to overwrite {rel}: regenerating the golden file is a contract change; "
                  "bump KERNELS_CONTRACT_VERSION or pass --force, then re-run the Phase 3 and Phase 4 "
                  "contract tests (see docs/PHYSICS.md)", file=sys.stderr)
            return 2
        doc = golden_document()
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"WROTE {rel} T0={doc['T0']!r} T1={doc['T1']!r}")
        return 0

    if not GOLDEN.exists():
        print(f"golden file {rel} is missing; create it with --write")
        return 1
    with GOLDEN.open(encoding="utf-8") as fh:
        golden = json.load(fh)
    doc = golden_document()
    problems = compare(doc, golden)
    for p in problems:
        print(f"MISMATCH {p}")
    if problems:
        return 1
    print(f"GOLDEN OK {GOLDEN.name} T1={golden['T1']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
