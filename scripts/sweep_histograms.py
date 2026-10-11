"""LOCAL ONLY: matched exit-row histograms, lattice MC vs Q1 direct sampling (PD-27) -> data/exit_histograms.json + PNG.

    scripts/sweep_histograms.py --profile quick --seed 2026   # 100,000 samples each
    scripts/sweep_histograms.py --seed 2026                   # full profile, 1,000,000 each (the artifact)

Classical: ``run_lattice`` on S histories. Quantum: S shots of the transpiled Q1 circuit at
k = 0 (A only, every qubit measured) on ``AerSimulator(method="statevector")``; each 12-bit key
becomes exact.py's 11-bit string and goes through the same ``mc_lattice.sample_exit_rows``.
Agreement is judged by chi-square sums over 17 categories (16 rows + no back-face exit).
Circuit validation, not speedup evidence: both histograms converge as 1 / sqrt(N).
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

from neutron_qae import analysis, artifacts, exact, oracle

SCRIPT = "scripts/sweep_histograms.py"
PROFILES = {"quick": {"shots": 100_000}, "full": {"shots": 1_000_000}}
NOTES = [
    ("the quantum histogram samples A directly (k = 0); like the classical one it converges as 1/sqrt(N): "
     "it validates that the circuit encodes the same physics and is not speedup evidence"),
    "agreement is judged by chi-square sums over 17 categories; per-row z-scores are not used",
    ("both samples go through the same mc_lattice.sample_exit_rows: the lattice engine's 11-bit strings and "
     "the Q1 count keys (int(key, 2) & 0x7FF, key character 0 = flag qubit 11)"),
    ("outside_support counts shots on zero-amplitude strings and flag_mismatch shots whose flag disagrees with "
     "the string's transmitted predicate; both are 0 for an ideal simulator"),
    ("chi-square: two-sample sum (c - q)^2 / (c + q) for equal totals; goodness of fit sum (c - S p)^2 / (S p) "
     "against exact.exit_row_distribution_k1; acceptance bound dof + 5 sqrt(2 dof)"),
    "sampling complexity only: this figure makes no speedup or wall-clock claim",
]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = sweep_common.base_parser(__doc__.splitlines()[0])
    args = ap.parse_args(argv)
    os.chdir(sweep_common.ROOT)
    shots = PROFILES[args.profile]["shots"]
    timings = {}
    t_all = time.perf_counter()

    t = time.perf_counter()
    problem = oracle.make_problem("Q1")          # contract gate: |p - T1| <= 1e-12
    kernels = problem.kernels
    timings["make_problem"] = time.perf_counter() - t
    ss_classical, ss_rows, ss_aer = np.random.SeedSequence(args.seed).spawn(3)

    t = time.perf_counter()
    classical = analysis.classical_exit_rows(kernels, shots, ss_classical)
    timings["classical"] = time.perf_counter() - t

    from qiskit_aer import AerSimulator  # local only; never reachable from main.py

    backend = AerSimulator(method="statevector")
    aer_seed = int(ss_aer.generate_state(1, dtype=np.uint32)[0])
    t = time.perf_counter()
    quantum = analysis.quantum_exit_rows(backend, problem, shots, aer_seed, ss_rows)
    timings["quantum"] = time.perf_counter() - t

    p_rows = exact.exit_row_distribution_k1(kernels)
    t1 = float(problem.reference)
    p_none = 1.0 - t1
    probs = [float(x) for x in p_rows] + [p_none]
    c_cat = classical["row_counts"] + [classical["no_back_exit"]]
    q_cat = quantum["row_counts"] + [quantum["no_back_exit"]]
    chi2 = {
        "classical_vs_quantum": analysis.chi2_two_sample(c_cat, q_cat),
        "classical_vs_exact": analysis.chi2_goodness(c_cat, probs),
        "quantum_vs_exact": analysis.chi2_goodness(q_cat, probs),
    }
    timings["total"] = time.perf_counter() - t_all
    parameters = {
        "model": "Q1",
        "k": 0,
        "shots": shots,
        "rows": int(kernels.spec.ny),
        "width_x_cm": float(kernels.spec.width_x),
        "backend": "AerSimulator(method=statevector)",
        "aer_seed_simulator": aer_seed,
        "categories": "16 back-face rows + no back-face exit (17)",
        "seeding": ("root = SeedSequence(seed); classical, rows, aer = root.spawn(3); classical = run_lattice("
                    "kernels, S, classical); quantum rows = sample_exit_rows(kernels, strings, rows) with the Aer "
                    "count keys sorted ascending and expanded by np.repeat; seed_simulator = "
                    "aer.generate_state(1, uint32)[0]"),
    }
    results = {
        "classical": classical,
        "quantum": quantum,
        "exact": {"row_probabilities": [float(x) for x in p_rows], "no_back_exit_probability": p_none, "T1": t1},
        "chi2": chi2,
        "label": artifacts.HISTOGRAM_LABEL,
    }
    doc = {
        "schema": "neutron_qae.artifact",
        "schema_version": 1,
        "kind": "exit_histograms",
        "profile": args.profile,
        "provenance": sweep_common.provenance(args.seed, SCRIPT, argv, timings),
        "parameters": parameters,
        "results": results,
        "notes": list(NOTES),
    }
    sweep_common.finish(doc, "exit_histograms", args.out_dir, args.dpi)
    print(f"SWEEP exit_histograms profile={args.profile} seed={args.seed} "
          f"chi2_cq={chi2['classical_vs_quantum']['value']:.2f} chi2_c={chi2['classical_vs_exact']['value']:.2f} "
          f"chi2_q={chi2['quantum_vs_exact']['value']:.2f} bound={chi2['classical_vs_quantum']['bound']:.2f} "
          f"outside={quantum['outside_support']} mismatch={quantum['flag_mismatch']} "
          f"total_s={timings['total']:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
