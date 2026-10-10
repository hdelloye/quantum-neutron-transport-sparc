"""Phase 1 smoke test: runtime probe + one IonQ-safe job on an INJECTED backend.

Nothing here creates a backend. Every function that needs one takes it as a parameter.
"""
from __future__ import annotations

import json
import sys
import time

PROBE_FILE = "data/smoke_probe.json"  # literal path: Qollab loads only files named by a literal string
IDEAL_MODES = ("none", "kwarg", "set_options")


def _version(mod_name: str, dist_name: str | None = None) -> str:
    try:
        mod = __import__(mod_name)
    except Exception as exc:  # noqa: BLE001 - record, never crash the smoke run
        return f"not importable ({type(exc).__name__})"
    v = getattr(mod, "__version__", None)
    if v:
        return str(v)
    try:
        from importlib.metadata import version

        return version(dist_name or mod_name)
    except Exception as exc:  # noqa: BLE001
        return f"unknown ({type(exc).__name__})"


def runtime_report() -> dict:
    rep = {
        "python": sys.version.split()[0],
        "python_full": sys.version,
        "platform": sys.platform,  # "emscripten" on Qollab/Pyodide
        "numpy": _version("numpy"),
        "qiskit": _version("qiskit"),
        "scipy": _version("scipy"),
        "qiskit_ionq": _version("qiskit_ionq", "qiskit-ionq"),  # installed by Qollab only for IonQ runs
    }
    try:
        import pyodide  # type: ignore[import-not-found]

        rep["pyodide"] = getattr(pyodide, "__version__", "?")
    except ImportError:
        rep["pyodide"] = None
    try:
        with open(PROBE_FILE, encoding="utf-8") as fh:
            rep["data_file_literal_path"] = json.load(fh)["probe"]
    except OSError as exc:
        rep["data_file_literal_path"] = f"FAILED: {exc}"
    return rep


def backend_report(backend) -> dict:
    cls = type(backend)
    opts = getattr(backend, "options", None)
    return {
        "class": f"{cls.__module__}.{cls.__qualname__}",
        "name": getattr(backend, "name", None),
        "options_noise_model": getattr(opts, "noise_model", None),
        "options_shots": getattr(opts, "shots", None),
        "is_ionq": is_ionq(backend),
    }


def is_ionq(backend) -> bool:
    """Detect qiskit-ionq without importing it (it is absent on the built-in simulator)."""
    return type(backend).__module__.startswith("qiskit_ionq")


def ghz(n: int):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, n, name=f"ghz{n}")
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n), range(n))
    return qc


def run_toy(backend, shots: int = 200, n: int = 6, ideal_mode: str = "none") -> dict:
    """ONE backend.run call carrying ONE circuit (a GHZ state), on every backend.

    Qollab allows one job per run on IonQ, and its IonQ proxy accepts only job type
    ionq.circuit.v1. qiskit-ionq sends a list or tuple (even of length one) as
    ionq.multi-circuit.v1, which Qollab rejects with HTTP 400, so the circuit is passed
    as a bare QuantumCircuit, never wrapped in a list.
    """
    from qiskit import transpile

    shots = max(2, min(int(shots), 10_000))
    n = max(2, min(int(n), 20))
    if ideal_mode not in IDEAL_MODES:
        raise ValueError(f"ideal_mode must be one of {IDEAL_MODES}, got {ideal_mode!r}")
    run_kwargs: dict = {"shots": shots}
    applied = "n/a (local ideal simulator)"
    if is_ionq(backend) and ideal_mode == "kwarg":
        run_kwargs["noise_model"] = "ideal"
        applied = "run(..., noise_model='ideal')"
    elif is_ionq(backend) and ideal_mode == "set_options":
        backend.set_options(noise_model="ideal")  # mutates the injected backend; does not create one
        applied = "backend.set_options(noise_model='ideal')"
    elif is_ionq(backend):
        applied = "none (dialog's noise model)"

    t0 = time.perf_counter()
    tcirc = transpile(ghz(n), backend, optimization_level=1)  # one QuantumCircuit in, one out
    t_transpile = time.perf_counter() - t0

    out = {"ideal_mode": ideal_mode, "applied": applied, "run_kwargs": run_kwargs, "n": n,
           "circuits_per_job": 1}
    t0 = time.perf_counter()
    try:
        job = backend.run(tcirc, **run_kwargs)  # the ONLY job this run sends; bare circuit, not a list
        counts = dict(job.result().get_counts())
        out.update(accepted=True, error=None, counts=counts)
    except Exception as exc:  # noqa: BLE001 - AttributeError inside qiskit-ionq masks an IonQ error
        out.update(accepted=False, error=f"{type(exc).__name__}: {exc}", counts={})
    out["transpile_s"] = round(t_transpile, 3)
    out["run_s"] = round(time.perf_counter() - t0, 3)

    if out["counts"]:
        ghz_counts = out["counts"]
        ideal_keys = {"0" * n, "1" * n}
        total = sum(ghz_counts.values())
        off = sum(v for k, v in ghz_counts.items() if k not in ideal_keys)
        exact_half = ghz_counts.get("0" * n) == total / 2 == ghz_counts.get("1" * n)
        out["ghz_off_ideal_fraction"] = round(off / total, 4)
        out["noise_verdict"] = (
            "noisy" if off else "ideal, exact round(p*shots) (no shot noise)" if exact_half else "ideal, sampled"
        )
    return out


def perf_probe(backend, qubits: int = 12, depth: int = 20, shots: int = 1000) -> dict:
    """Pyodide speed probe. LOCAL backends only: IonQ allows one job per run."""
    if is_ionq(backend) or qubits <= 0:
        return {"skipped": "IonQ backend (one job per run) or qubits <= 0"}
    from qiskit import QuantumCircuit, transpile

    qubits = min(int(qubits), 24)
    qc = QuantumCircuit(qubits)
    for layer in range(int(depth)):
        for q in range(qubits):
            qc.ry(0.1 * (layer + 1) + 0.01 * q, q)
        for q in range(qubits - 1):
            qc.cx(q, q + 1)
    qc.measure_all()
    t0 = time.perf_counter()
    tqc = transpile(qc, backend, optimization_level=1)
    t1 = time.perf_counter()
    backend.run(tqc, shots=int(shots)).result()
    t2 = time.perf_counter()
    return {"qubits": qubits, "depth": int(depth), "cx": tqc.count_ops().get("cx", 0),
            "transpile_s": round(t1 - t0, 3), "run_s": round(t2 - t1, 3)}
