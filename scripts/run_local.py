"""LOCAL ONLY: run main.py the way Qollab does, with an injected backend.

Allow-listed in tests/compliance_checks.py: the only place a backend is constructed.
"""
import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def make_backend(kind: str):
    if kind == "basic":
        from qiskit.providers.basic_provider import BasicSimulator
        return BasicSimulator()
    if kind == "aer":
        from qiskit_aer import AerSimulator
        return AerSimulator()
    raise SystemExit(f"unknown backend {kind!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="basic", choices=["basic", "aer"])
    ap.add_argument("--shots", type=int, default=200)
    a = ap.parse_args()
    os.chdir(ROOT)  # Qollab: project root is the working directory
    import main as entry
    entry.backend = make_backend(a.backend)   # mimic Qollab's injected global
    entry.main(shots=a.shots)
