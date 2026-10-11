"""LOCAL ONLY: run main.py the way Qollab does, with an injected backend.

Allow-listed in tests/compliance_checks.py: the only place a backend is constructed.

    scripts/run_local.py                         # quick mode (main()'s default): live MLAE + four figures
    scripts/run_local.py --seed 2026 --figure-dir /tmp/q   # reproducible; PNGs into /tmp/q
    scripts/run_local.py --mode qae --seed 2026  # reproduces the Phase 4 QAE run (k = 0, 1, 2, 4)
    scripts/run_local.py --mode smoke            # the Phase 1 smoke test (SMOKE TEST PASSED)
    scripts/run_local.py --backend fake-ionq --k 1 --shots 200 --seed 3   # IonQ path, one circuit
    scripts/run_local.py --backend aer           # needs qiskit-aer (local dev install)

Only the options you give are passed to main(), so main()'s own defaults apply otherwise,
exactly like an untouched Qollab Run settings form. Quick-mode figures are written to
--figure-dir (default: a fresh temp directory), never into the repository.
"""
import argparse
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def make_backend(kind: str, seed=None):
    if kind == "basic":
        from qiskit.providers.basic_provider import BasicSimulator
        be = BasicSimulator()
        if seed is not None:
            be.set_options(seed_simulator=seed)
        return be
    if kind == "aer":
        from qiskit_aer import AerSimulator
        return AerSimulator() if seed is None else AerSimulator(seed_simulator=seed)
    if kind == "fake-ionq":
        sys.path.insert(0, str(ROOT / "tests"))
        from ionq_fakes import FakeIonQSimulator
        be = FakeIonQSimulator()
        if seed is not None:
            be.set_options(seed_simulator=seed)
        return be
    raise SystemExit(f"unknown backend {kind!r}")


if __name__ == "__main__":
    import matplotlib

    matplotlib.use("Agg")   # local-only script (as scripts/render_figures.py); main.py never selects one
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", default="basic", choices=["basic", "aer", "fake-ionq"])
    ap.add_argument("--mode", default=None)
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--shots", type=int, default=None)
    ap.add_argument("--ideal-mode", dest="ideal_mode", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--figure-dir", dest="figure_dir", default=None,
                    help="where quick mode saves its PNGs (default: a fresh temp directory)")
    a = ap.parse_args()
    figure_dir = a.figure_dir or tempfile.mkdtemp(prefix="neutron_qae_quick_")
    print(f"run_local: quick-mode figures go to {figure_dir}", flush=True)
    kwargs = {name: getattr(a, name) for name in ("mode", "k", "shots", "ideal_mode", "model")
              if getattr(a, name) is not None}
    os.chdir(ROOT)  # Qollab: project root is the working directory
    import main as entry
    entry.backend = make_backend(a.backend, a.seed)   # mimic Qollab's injected global
    entry.FIGURE_DIR = figure_dir
    entry.main(**kwargs)
