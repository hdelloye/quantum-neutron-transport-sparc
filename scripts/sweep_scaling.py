"""LOCAL ONLY: headline RMSE-versus-cost sweep (PD-25, PD-26) -> data/scaling_rmse.json + PNG.

    scripts/sweep_scaling.py --profile quick --seed 2026     # tracer, under a second of compute
    scripts/sweep_scaling.py --seed 2026                     # full profile, the committed artifact

Matched classical lattice Monte Carlo (cost = histories) versus MLAE on the exponential schedule
(cost = applications of A, N_A = sum shots (2k + 1)), both against the exact lattice T1 of the
10 cm SPARC wall. The IonQ estimate appears as one labelled marker and is never in a fit.
Sampling complexity only: no wall-clock or quantum-advantage claim.
"""
from __future__ import annotations

import os
import sys
import time

import matplotlib

matplotlib.use("Agg")

import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import sweep_common

from neutron_qae import analysis, oracle, runners

SCRIPT = "scripts/sweep_scaling.py"
SHOTS_PER_POWER = 300
FIT_MIN_M = 2
PROFILES = {
    "quick": {"classical_N": (100, 1000, 10000, 100000), "repetitions": 20, "mlae_M_max": 6, "aer_M_max": None},
    "full": {"classical_N": (100, 215, 464, 1000, 2154, 4642, 10000, 21544, 46416, 100000, 215443, 464159,
                             1000000),
             "repetitions": 100, "mlae_M_max": 11, "aer_M_max": 9},
}
IONQ_LABEL = ("IonQ Forte 1, ideal noise model, k = 0, 1, 2 x 1000 shots: |error| of one estimate; "
              "execution proof, 6.4 sigma off T1, cause open; not in any fit")
NOTES = [
    ("cost: classical lattice MC = histories N (LatticeResult.cost); MLAE = applications of A, "
     "N_A = sum over the schedule of shots (2k + 1) (MLAEResult.n_A); never shots or circuits"),
    ("MLAE series use the analytic runner (exact theta, Binomial draws); the Aer series simulates the "
     "transpiled Q1 circuits"),
    ("nested repetitions: each repetition is one experiment observed at increasing cost (classical "
     "checkpoints within one run; MLAE on the first M records of one schedule run)"),
    "RMSE = sqrt(mean(err^2)) against the exact lattice T1; band = 16th-84th percentile of |err|",
    ("fits: OLS of log10 RMSE on log10 cost, slope SE sqrt(SSR / (n - 2) / Sxx); classical over all points, "
     "MLAE over M >= 2 (at least one Grover power)"),
    "the IonQ marker is a single estimate's |error|, not an RMSE, and is not in any fit",
    "sampling complexity only: no wall-clock or quantum-advantage claim",
]


def _ionq_marker(t1):
    res = runners.ionq_estimate(runners.load_ionq_records())
    if res is None:
        return None
    return {"label": IONQ_LABEL, "n_A": int(res.n_A), "a_hat": float(res.a_hat), "se": float(res.se),
            "abs_err": abs(float(res.a_hat) - t1), "z": (float(res.a_hat) - t1) / float(res.se),
            "ks": [int(k) for k in res.ks], "in_fit": False}


def _attach_fit(series, min_M):
    fit = analysis.fit_series(series, min_M)
    expected = len(series["cost"]) if min_M is None else sum(1 for M in series["M"] if M >= min_M)
    assert fit["points"] == expected, (fit["points"], expected)
    series["fit"] = fit
    return series


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = sweep_common.base_parser(__doc__.splitlines()[0])
    args = ap.parse_args(argv)
    os.chdir(sweep_common.ROOT)
    prof = PROFILES[args.profile]
    timings = {}
    t_all = time.perf_counter()

    t = time.perf_counter()
    problem = oracle.make_problem("Q1")          # contract gate: |p - T1| <= 1e-12
    t1 = float(problem.reference)
    timings["make_problem"] = time.perf_counter() - t
    ss_classical, ss_analytic, ss_aer = np.random.SeedSequence(args.seed).spawn(3)
    reps = prof["repetitions"]

    t = time.perf_counter()
    classical = analysis.classical_rmse_series(problem.kernels, t1, prof["classical_N"], reps, ss_classical)
    timings["classical"] = time.perf_counter() - t
    _attach_fit(classical, None)

    t = time.perf_counter()
    analytic = analysis.mlae_rmse_series(problem.p, t1, prof["mlae_M_max"], SHOTS_PER_POWER, reps, ss_analytic)
    timings["mlae_analytic"] = time.perf_counter() - t
    _attach_fit(analytic, FIT_MIN_M)

    aer = None
    parameters = {
        "model": "Q1",
        "width_x_cm": float(problem.kernels.spec.width_x),
        "reference_T1": t1,
        "repetitions": reps,
        "shots_per_power": SHOTS_PER_POWER,
        "schedule": "exponential",
        "classical_N": list(prof["classical_N"]),
        "mlae_M_max": prof["mlae_M_max"],
        "aer_M_max": None,
        "fit_min_M": FIT_MIN_M,
        "seeding": "root = SeedSequence(seed); classical, analytic, aer = root.spawn(3); "
                   "repetition r uses <stage>.spawn(R)[r]",
    }
    marker = _ionq_marker(t1)
    timings["total"] = time.perf_counter() - t_all
    doc = {
        "schema": "neutron_qae.artifact",
        "schema_version": 1,
        "kind": "scaling_rmse",
        "profile": args.profile,
        "provenance": sweep_common.provenance(args.seed, SCRIPT, argv, timings),
        "parameters": parameters,
        "results": {"series": {"classical_lattice": classical, "mlae_analytic": analytic, "mlae_aer": aer},
                    "ionq_marker": marker},
        "notes": list(NOTES),
    }
    sweep_common.finish(doc, "scaling_rmse", args.out_dir, args.dpi)
    aer_slope = "none" if aer is None else f"{aer['fit']['slope']:.4f}"
    print(f"SWEEP scaling_rmse profile={args.profile} seed={args.seed} "
          f"classical_slope={classical['fit']['slope']:.4f} mlae_slope={analytic['fit']['slope']:.4f} "
          f"aer_slope={aer_slope} total_s={timings['total']:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
