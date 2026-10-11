"""Qollab entry point - Phase 4 QAE mode plus the Phase 1 smoke mode.

`backend` is a global that Qollab creates from the Select QPU dialog before this file runs.
Never create or assign it here. Qollab appends a call to main(<form values>) after this
file, so this file must not call main() itself and must not use a __name__ guard.

- mode="qae" on the Built-in simulator (the judged, logged-out path): the contract-checked Q1
  oracle, one list job over Grover powers k = 0, 1, 2, 4 with `shots` each, the vendored MLAE,
  a `QAE_REPORT=` line, the IonQ-only estimate from data/ionq_runs.json, `QAE RUN COMPLETED`.
- mode="qae" on an IonQ backend: exactly ONE A·Q^k circuit in ONE job (Qollab's IonQ proxy accepts
  one bare circuit per run), one `IONQ_RECORD=` line, `IONQ RUN ACCEPTED` or `IONQ RUN FAILED: ...`.
- mode="smoke": the Phase 1 smoke test (GHZ on 6 qubits, 12-qubit perf probe, SMOKE TEST PASSED).

Form values are validated before any job is sent and rejected with ValueError, never clamped.
`k` and `ideal_mode` apply to IonQ runs only.
"""
import json
import numbers
import time

from neutron_qae import mlae, oracle, runners
from neutron_qae.exact import transmission_within
from neutron_qae.smoke import (
    IDEAL_MODES,
    backend_report,
    is_ionq,
    perf_probe,
    run_toy,
    runtime_report,
)

MODES = ("qae", "smoke")
BUILTIN_SCHEDULE = (0, 1, 2, 4)
SMOKE_GHZ_QUBITS = 6
SMOKE_PERF_QUBITS = 12


def _as_int(name, value, lo, hi):
    """Integer form value in lo..hi; ints and integral floats pass, bools and anything else raise."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} must be an integer in {lo}..{hi}, got {value!r}")  # noqa: TRY004 - PD-23
    if not isinstance(value, numbers.Integral) and not float(value).is_integer():
        raise ValueError(f"{name} must be an integer in {lo}..{hi}, got {value!r}")
    out = int(value)
    if not lo <= out <= hi:
        raise ValueError(f"{name} must be an integer in {lo}..{hi}, got {value!r}")
    return out


def _as_choice(name, value, choices):
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}, got {value!r}")
    return value


def _check_inputs(mode, k, shots, ideal_mode, model):
    """PD-23: validate every form value before any job; return the normalised values."""
    mode = _as_choice("mode", mode, MODES)
    model = _as_choice("model", model, oracle.MODELS)
    k = _as_int("k", k, 0, runners.IONQ_MAX_K)
    shots = _as_int("shots", shots, runners.MIN_SHOTS, runners.MAX_SHOTS)
    if mode == "qae":
        if ideal_mode == "kwarg":
            raise ValueError("ideal_mode 'kwarg' gives round(p shots) counts on IonQ, never samples; "
                             "use 'set_options' or 'none'")
        ideal_mode = _as_choice("ideal_mode", ideal_mode, runners.IONQ_IDEAL_MODES)
    else:
        ideal_mode = _as_choice("ideal_mode", ideal_mode, IDEAL_MODES)
    return mode, k, shots, ideal_mode, model


def _send_file(name, payload):
    try:
        from js import sendFile  # exists only inside Qollab's runtime

        sendFile(name, "application/json", payload)
    except ImportError:
        pass


def _run_smoke(be, shots, ideal_mode):
    """The Phase 1 smoke test, unchanged in behaviour (GHZ 6 qubits, perf probe 12 qubits)."""
    t0 = time.perf_counter()
    print("=== Qollab smoke test (Phase 1) ===", flush=True)
    report = {"mode": "smoke", "runtime": runtime_report(), "backend": backend_report(be)}
    print(json.dumps(report, indent=1), flush=True)
    report["toy"] = run_toy(be, shots=shots, n=SMOKE_GHZ_QUBITS, ideal_mode=ideal_mode)
    report["perf"] = perf_probe(be, qubits=SMOKE_PERF_QUBITS)
    report["wall_clock_s"] = round(time.perf_counter() - t0, 3)
    print("QOLLAB_RUNTIME_REPORT=" + json.dumps(report), flush=True)
    _send_file("qollab_runtime_report.json", json.dumps(report, indent=1))
    print("SMOKE TEST " + ("PASSED" if report["toy"]["accepted"] else "FAILED"), flush=True)
    return report


def _backend_name(be):
    return str(getattr(be, "name", type(be).__name__))


def _contract(problem):
    """Print and return the contract gate result (make_problem already enforced it)."""
    d = abs(problem.p - problem.reference)
    print(f"contract: {problem.model} flag probability {problem.p!r} vs exact T{problem.K} "
          f"{problem.reference!r} (|d| = {d:.1e} <= {oracle.CONTRACT_TOL:.0e})", flush=True)
    return {"p_flag": problem.p, "reference": problem.reference, "abs_diff": d, "tol": oracle.CONTRACT_TOL}


def _ionq_summary(t1):
    """IonQ-only MLAE estimate from data/ionq_runs.json: a dict, None, or {"error": ...}."""
    models = ("Q1", "Q1lite")                       # both have flag probability T1
    try:
        records = runners.load_ionq_records()
        res = runners.ionq_estimate(records, models)
    except (ValueError, OSError) as exc:
        return {"error": str(exc)}
    if res is None:
        return None
    used = sorted({rec["model"] for rec in records if rec["sampled"] and rec["model"] in models})
    return {"a_hat": res.a_hat, "abs_err": abs(res.a_hat - t1), "se": res.se, "n_A": res.n_A,
            "ks": list(res.ks), "shots": list(res.shots), "hits": list(res.hits), "models": used}


def _run_qae_builtin(be, model, shots):
    """Built-in (judged) path: one list job over BUILTIN_SCHEDULE, live MLAE, IonQ records summary."""
    t0 = time.perf_counter()
    name = _backend_name(be)
    print(f"=== Neutron transport QAE (Phase 4) mode=qae model={model} backend={name} ===", flush=True)
    problem = oracle.make_problem(model)            # contract gate: raises unless |p - T_K| <= 1e-12
    contract = _contract(problem)
    print(f"note: k and ideal_mode apply to IonQ runs only; this run uses Grover powers "
          f"{list(BUILTIN_SCHEDULE)} with {shots} shots each in one job", flush=True)
    records = runners.BackendRunner(be, problem).run(list(BUILTIN_SCHEDULE), shots)
    res = mlae.estimate(records)
    t1 = problem.reference if problem.K == 1 else transmission_within(problem.kernels, 1)
    ionq = _ionq_summary(t1)
    qae = {
        "model": model,
        "backend": name,
        "contract": contract,
        "schedule": list(BUILTIN_SCHEDULE),
        "shots_per_power": shots,
        "hits": [r.hits for r in records],
        "a_hat": res.a_hat,
        "theta": res.theta,
        "se": res.se,
        "abs_err": abs(res.a_hat - problem.reference),
        "reference": problem.reference,
        "n_A": res.n_A,
        "ionq_records": ionq,
        "note": "k and ideal_mode apply to IonQ runs only",
        "wall_clock_s": round(time.perf_counter() - t0, 3),
    }
    print("QAE_REPORT=" + json.dumps(qae, sort_keys=True), flush=True)
    print(f"MLAE a_hat={res.a_hat:.6f} |a_hat - T{problem.K}|={qae['abs_err']:.2e} se={res.se:.2e} "
          f"N_A={res.n_A} schedule={list(BUILTIN_SCHEDULE)} shots/power={shots}", flush=True)
    if ionq is None:
        print("IonQ records: none yet (data/ionq_runs.json has no sampled k = 0 record)", flush=True)
    elif "error" in ionq:
        print(f"IonQ records: invalid ({ionq['error']})", flush=True)
    else:
        print(f"IonQ Forte 1 records (ideal, sampled): k={ionq['ks']} -> a_hat={ionq['a_hat']:.6f}, "
              f"|a_hat - T1|={ionq['abs_err']:.2e}, se={ionq['se']:.2e}, N_A={ionq['n_A']}", flush=True)
    print("QAE RUN COMPLETED", flush=True)
    return qae


def _run_qae_ionq(be, model, k, shots, ideal_mode):
    """IonQ path: exactly one A·Q^k circuit in one job; never raises on a submission failure."""
    name = _backend_name(be)
    print(f"=== Neutron transport QAE (Phase 4) mode=qae model={model} backend={name} k={k} shots={shots} "
          f"ideal_mode={ideal_mode} ===", flush=True)
    problem = oracle.make_problem(model)            # contract gate runs locally before any job
    _contract(problem)
    record = runners.IonQRunner(be, problem, ideal_mode=ideal_mode).run_point(k, shots)
    p_meas = "n/a" if record["p_flag"] is None else f"{record['p_flag']:.4f}"
    print(f"IonQ run: model={model} k={k} shots={shots} noise_model={record['noise_model']} "
          f"sampled={record['sampled']} P(flag) measured {p_meas} vs expected {record['p_expected']:.4f} "
          f"cx={record['cx']} request~{record['body_bytes_est'] / 1000:.0f} KB", flush=True)
    print("IONQ_RECORD=" + json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)
    if record["accepted"] and record["sampled"] and k == 0:
        print(f"MLAE (this record alone, k = 0): a_hat = hits/shots = {record['hits']}/{shots} = "
              f"{record['hits'] / shots:.6f}, N_A = {shots}", flush=True)
    _send_file(f"ionq_record_{model}_k{k}_{ideal_mode}.json", json.dumps(record, sort_keys=True, indent=1))
    if record["accepted"]:
        print("IONQ RUN ACCEPTED", flush=True)
    else:
        print(f"IONQ RUN FAILED: {record['error']}", flush=True)
    return record


def main(mode: str = "qae", k: int = 1, shots: int = 1000, ideal_mode: str = "set_options", model: str = "Q1"):
    mode, k, shots, ideal_mode, model = _check_inputs(mode, k, shots, ideal_mode, model)
    if mode == "smoke":
        return _run_smoke(backend, shots, ideal_mode)  # noqa: F821
    report = {"mode": mode, "backend": backend_report(backend)}  # noqa: F821
    if is_ionq(backend):  # noqa: F821
        report["ionq"] = _run_qae_ionq(backend, model, k, shots, ideal_mode)  # noqa: F821
    else:
        report["qae"] = _run_qae_builtin(backend, model, shots)  # noqa: F821
    return report
