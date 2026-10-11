"""LOCAL ONLY: run main.py the way Qollab does, with an injected backend.

Allow-listed in tests/compliance_checks.py: the only place a backend is constructed.

    scripts/run_local.py                         # QAE mode with main()'s defaults (Built-in path)
    scripts/run_local.py --seed 2026             # reproducible Built-in counts
    scripts/run_local.py --mode smoke            # the Phase 1 smoke test (SMOKE TEST PASSED)
    scripts/run_local.py --backend fake-ionq --k 1 --shots 200 --seed 3   # IonQ path, one circuit
    scripts/run_local.py --backend aer           # needs qiskit-aer (local dev install)

Only the options you give are passed to main(), so main()'s own defaults apply otherwise,
exactly like an untouched Qollab Run settings form.
"""
import argparse
import os
import pathlib
import sys

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
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", default="basic", choices=["basic", "aer", "fake-ionq"])
    ap.add_argument("--mode", default=None)
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--shots", type=int, default=None)
    ap.add_argument("--ideal-mode", dest="ideal_mode", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    kwargs = {name: getattr(a, name) for name in ("mode", "k", "shots", "ideal_mode", "model")
              if getattr(a, name) is not None}
    os.chdir(ROOT)  # Qollab: project root is the working directory
    import main as entry
    entry.backend = make_backend(a.backend, a.seed)   # mimic Qollab's injected global
    entry.main(**kwargs)
