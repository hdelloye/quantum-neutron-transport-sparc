"""LOCAL ONLY: Phase 4 quantum tools (may import qiskit_aer; never reachable from main.py).

    scripts/qae_local.py resources                          # the docs/QUANTUM.md resource table
    scripts/qae_local.py aer-mlae --M 5 --shots 100 --seed 1
    scripts/qae_local.py analytic --M 5 --shots 100 --reps 50 --seed 2026

``resources`` prints ``format_resource_table(resource_table())`` exactly (tests/test_quantum_doc.py
checks that docs/QUANTUM.md holds the same text). ``aer-mlae`` runs one MLAE estimate of Q1 on Aer
over ``exponential_schedule(M)``. ``analytic`` prints the MLAE RMSE over ``reps`` analytic runs next
to the classical standard error sqrt(T1 (1 - T1) / N_A) at the same N_A.
"""
import argparse
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from neutron_qae import mlae
from neutron_qae.grover import format_resource_table, resource_table
from neutron_qae.oracle import make_problem
from neutron_qae.runners import AnalyticRunner, BackendRunner


def cmd_resources(_args) -> None:
    print(format_resource_table(resource_table()))


def cmd_aer_mlae(args) -> None:
    from qiskit_aer import AerSimulator

    problem = make_problem("Q1")
    ks = mlae.exponential_schedule(args.M)
    backend = AerSimulator(method="statevector", seed_simulator=args.seed)
    res = mlae.estimate(BackendRunner(backend, problem).run(ks, args.shots))
    print(f"Aer MLAE Q1 ks={ks} shots/power={args.shots} hits={list(res.hits)}")
    print(f"a_hat={res.a_hat:.6f} |a_hat - T1|={abs(res.a_hat - problem.reference):.2e} "
          f"se={res.se:.2e} N_A={res.n_A}")


def cmd_analytic(args) -> None:
    problem = make_problem("Q1")
    t1 = problem.reference
    ks = mlae.exponential_schedule(args.M)
    runner = AnalyticRunner(problem.p, np.random.default_rng(args.seed))
    est = np.array([mlae.estimate(runner.run(ks, args.shots)).a_hat for _ in range(args.reps)])
    n_a = args.shots * sum(2 * k + 1 for k in ks)
    rmse = float(np.sqrt(np.mean((est - t1) ** 2)))
    classical = math.sqrt(t1 * (1 - t1) / n_a)
    print(f"analytic MLAE Q1 ks={ks} shots/power={args.shots} reps={args.reps} seed={args.seed}")
    print(f"N_A={n_a} RMSE={rmse:.3e} classical sqrt(T1 (1 - T1) / N_A)={classical:.3e} "
          f"ratio={classical / rmse:.2f}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resources", help="print the resource table").set_defaults(fn=cmd_resources)
    p = sub.add_parser("aer-mlae", help="one MLAE estimate of Q1 on Aer")
    p.add_argument("--M", type=int, default=5)
    p.add_argument("--shots", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(fn=cmd_aer_mlae)
    p = sub.add_parser("analytic", help="analytic MLAE RMSE vs the classical standard error")
    p.add_argument("--M", type=int, default=5)
    p.add_argument("--shots", type=int, default=100)
    p.add_argument("--reps", type=int, default=50)
    p.add_argument("--seed", type=int, default=2026)
    p.set_defaults(fn=cmd_analytic)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
