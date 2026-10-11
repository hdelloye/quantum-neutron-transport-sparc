"""LOCAL ONLY: wall-thickness rare-event study (PD-29) -> data/thickness_study.json + PNG.

    scripts/sweep_thickness.py --profile quick --seed 2026   # walls 10, 20, 30 cm, R = 20
    scripts/sweep_thickness.py --seed 2026                   # full profile, walls 6-30 cm, R = 100

For each wall (2.0 cm W, steel grows, 16 x 16 grid, Q1 stays 12 qubits) the headline comparison
is repeated: classical lattice MC (cost = histories) versus analytic MLAE (cost = applications
of A) against the exact T1, and the cost to reach 1% relative RMSE is read off each measured
curve by log-log interpolation (never extrapolated). Every wall passes the underflow guard
(``analysis.check_transmission``) before any sweep starts: a wall too thin in T1 for the
classical grid aborts the run with exit code 2 and writes nothing.
"""
from __future__ import annotations

import itertools
import math
import os
import sys
import time

import matplotlib

matplotlib.use("Agg")

import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import sweep_common

from neutron_qae import analysis, oracle
from neutron_qae.exact import transmission_within
from neutron_qae.kernels import build_kernels
from neutron_qae.problem import sparc_first_wall

SCRIPT = "scripts/sweep_thickness.py"
SHOTS_PER_POWER = 300
FIT_MIN_M = 2
TARGET_REL = 0.01
TARGET_ABS = 1e-3
MIN_EVENTS = 1000
PROFILES = {
    "quick": {"widths": (10.0, 20.0, 30.0), "repetitions": 20,
              "classical_N": (100, 1000, 10000, 100000, 1000000), "mlae_M_max": 6},
    "full": {"widths": (6.0, 10.0, 15.0, 20.0, 30.0), "repetitions": 100,
             "classical_N": (100, 215, 464, 1000, 2154, 4642, 10000, 21544, 46416, 100000, 215443, 464159,
                             1000000),
             "mlae_M_max": 9},
}
NOTES = [
    ("the growth is a relative-error statement: at a fixed relative RMSE classical Monte Carlo needs about "
     "(1 - T) / (T eps^2) histories while MLAE needs about 1 / (eps sqrt(T)) applications of A, so the ratio "
     "grows as T falls"),
    "at a fixed absolute RMSE the ratio shrinks with thickness (also reported)",
    "costs at target are interpolated in log-log between measured points, never extrapolated",
    ("thicker walls keep 2.0 cm W and add steel with the 10 cm lateral extent unchanged: a rare-event "
     "parameter sweep, not a SPARC design variant"),
    ("cost: classical lattice MC = histories N; MLAE = applications of A, N_A = sum shots (2k + 1); MLAE uses "
     "the analytic runner (exact theta, Binomial draws); every wall's Q1 oracle passes the statevector contract"),
    "sampling complexity only: no wall-clock or quantum-advantage claim",
]


def _attach_fit(series, min_M):
    series["fit"] = analysis.fit_series(series, min_M)
    return series


def _target(classical, mlae_series, rmse_target):
    nc = analysis.cost_at_target(classical["cost"], classical["rmse"], rmse_target)
    nm = analysis.cost_at_target(mlae_series["cost"], mlae_series["rmse"], rmse_target)
    bracketed = nc is not None and nm is not None
    return {"rmse": rmse_target, "n_classical": nc, "n_mlae": nm, "ratio": nc / nm if bracketed else None,
            "bracketed": bracketed}


def _parse_widths(raw):
    widths = []
    for w in raw:
        try:
            v = float(w)
        except (TypeError, ValueError):
            raise ValueError(f"wall width {w!r} is not a number") from None
        if not math.isfinite(v) or not v > 2.0:
            raise ValueError(f"wall width {v!r} cm must be a finite number > 2.0 (the W layer)")
        widths.append(v)
    if any(b <= a for a, b in itertools.pairwise(widths)):
        raise ValueError(f"wall widths must be strictly ascending, got {widths}")
    return widths


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = sweep_common.base_parser(__doc__.splitlines()[0])
    ap.add_argument("--widths", nargs="+", default=None, help="override the wall list (cm, ascending, > 2.0)")
    args = ap.parse_args(argv)
    os.chdir(sweep_common.ROOT)
    prof = PROFILES[args.profile]
    classical_n = prof["classical_N"]
    reps = prof["repetitions"]
    m_max = prof["mlae_M_max"]
    timings = {}
    t_all = time.perf_counter()

    # Validate every wall and run the underflow guard BEFORE any sweep starts (T-05-06).
    try:
        widths = _parse_widths(args.widths if args.widths is not None else prof["widths"])
        prepared = []
        for w in widths:
            kernels = build_kernels(sparc_first_wall(width_x=w))
            t1 = float(transmission_within(kernels, 1))
            try:
                analysis.check_transmission(t1, max(classical_n), min_events=MIN_EVENTS)
            except ValueError as exc:
                raise ValueError(f"wall {w:g} cm refused by the underflow guard: {exc}") from None
            prepared.append((w, kernels, float(transmission_within(kernels, 0)), t1))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 2

    walls = []
    for (w, kernels, t0, t1), child in zip(prepared, np.random.SeedSequence(args.seed).spawn(len(prepared)),
                                           strict=True):
        t = time.perf_counter()
        problem = oracle.make_problem("Q1", kernels)       # contract gate: |p - T1| <= 1e-12
        ss_classical, ss_analytic = child.spawn(2)
        classical = _attach_fit(analysis.classical_rmse_series(kernels, t1, classical_n, reps, ss_classical), None)
        analytic = _attach_fit(analysis.mlae_rmse_series(problem.p, t1, m_max, SHOTS_PER_POWER, reps, ss_analytic),
                               FIT_MIN_M)
        target_rel = _target(classical, analytic, TARGET_REL * t1)
        target_rel["n_classical_theory"] = (1.0 - t1) / (t1 * TARGET_REL ** 2)
        walls.append({
            "width_cm": float(w), "T0": t0, "T1": t1, "contract_abs_diff": abs(float(problem.p) - t1),
            "series": {"classical_lattice": classical, "mlae_analytic": analytic},
            "target_rel": target_rel, "target_abs": _target(classical, analytic, TARGET_ABS),
        })
        timings[f"wall_{w:g}cm"] = time.perf_counter() - t
        print(f"wall {w:g} cm T1={t1:.5f} ratio_rel={target_rel['ratio']} "
              f"({timings[f'wall_{w:g}cm']:.1f} s)", flush=True)

    ratios = [x["target_rel"]["ratio"] for x in walls]
    t1s = [x["T1"] for x in walls]
    all_rel = all(r is not None for r in ratios)
    monotone = all_rel and all(b > a for a, b in itertools.pairwise(ratios)) \
        and all(b < a for a, b in itertools.pairwise(t1s))
    slope = None
    if all_rel and len(walls) >= 2:
        slope = float(np.polyfit(np.log10(t1s), np.log10(ratios), 1)[0])
    trend = {"ratio_increases_as_T1_falls": bool(monotone),
             "ratio_span": (max(ratios) / min(ratios)) if all_rel else None,
             "loglog_slope_ratio_vs_T1": slope}
    timings["total"] = time.perf_counter() - t_all
    parameters = {
        "model": "Q1",
        "widths_cm": [float(w) for w in widths],
        "boundary_x_cm": 2.0,
        "target_rel_rmse": TARGET_REL,
        "target_abs_rmse": TARGET_ABS,
        "repetitions": reps,
        "classical_N": list(classical_n),
        "mlae_M_max": m_max,
        "shots_per_power": SHOTS_PER_POWER,
        "schedule": "exponential",
        "fit_min_M": FIT_MIN_M,
        "min_expected_events": MIN_EVENTS,
        "seeding": ("child_i = SeedSequence(seed).spawn(n_walls)[i]; classical, analytic = child_i.spawn(2); "
                    "repetition r uses <stage>.spawn(R)[r]"),
    }
    doc = {
        "schema": "neutron_qae.artifact",
        "schema_version": 1,
        "kind": "thickness_study",
        "profile": args.profile,
        "provenance": sweep_common.provenance(args.seed, SCRIPT, argv, timings),
        "parameters": parameters,
        "results": {"walls": walls, "trend": trend},
        "notes": list(NOTES),
    }
    sweep_common.finish(doc, "thickness_study", args.out_dir, args.dpi)
    shown = [None if r is None else round(r, 2) for r in ratios]
    print(f"SWEEP thickness_study profile={args.profile} seed={args.seed} ratios={shown} monotone={monotone} "
          f"total_s={timings['total']:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
