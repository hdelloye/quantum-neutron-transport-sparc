"""Qollab entry point - Phase 1 smoke test.

`backend` is a global that Qollab creates from the Select QPU dialog before this file runs.
Never create or assign it here. Qollab appends a call to main(<form values>) after this
file, so this file must not call main() itself and must not use a __name__ guard.
"""
import json
import time

from neutron_qae.smoke import backend_report, perf_probe, run_toy, runtime_report


def main(shots: int = 200, ghz_qubits: int = 6, ideal_mode: str = "none", perf_qubits: int = 12):
    t0 = time.perf_counter()
    print("=== Qollab smoke test (Phase 1) ===", flush=True)
    report = {"runtime": runtime_report(), "backend": backend_report(backend)}  # noqa: F821
    print(json.dumps(report, indent=1), flush=True)
    report["toy"] = run_toy(backend, shots=int(shots), n=int(ghz_qubits), ideal_mode=str(ideal_mode))  # noqa: F821
    report["perf"] = perf_probe(backend, qubits=int(perf_qubits))  # noqa: F821
    report["wall_clock_s"] = round(time.perf_counter() - t0, 3)
    print("QOLLAB_RUNTIME_REPORT=" + json.dumps(report), flush=True)
    try:
        from js import sendFile  # exists only inside Qollab's runtime

        sendFile("qollab_runtime_report.json", "application/json", json.dumps(report, indent=1))
    except ImportError:
        pass
    print("SMOKE TEST " + ("PASSED" if report["toy"]["accepted"] else "FAILED"), flush=True)
    return report
