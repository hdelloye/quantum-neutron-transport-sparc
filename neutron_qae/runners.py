"""Runners that turn (ks, shots) into flag-hit records for the MLAE (QAE-02).

Every runner has ``run(ks, shots) -> list[PowerResult]`` (records in input order), so the analytic
emulator, an injected local simulator and the IonQ one-circuit path feed ``mlae.estimate`` the same
way. Circuits always come from a contract-checked ``OracleProblem`` (``oracle.make_problem``), are
built by ``grover.power_circuit`` and transpiled exactly once by ``grover.transpile_once``.

- ``BackendRunner(backend, problem)``: any injected local backend (Aer from tests and scripts,
  Qollab's Built-in ``BasicSimulator``). One ``backend.run(list_of_circuits)`` per distinct shots
  value; refuses an IonQ backend (Qollab's IonQ proxy accepts one bare circuit per run).
- ``AnalyticRunner(p, rng)``: no circuits; one ``rng.binomial(shots, sin^2((2k + 1) theta))`` per k in
  input order, theta = asin sqrt(p) from the contract-checked flag probability (Phase 5 sweeps).
- ``IonQRunner(backend, problem, ideal_mode)``: exactly ONE k per run, ONE bare circuit (every qubit
  measured) through ONE ``backend.run`` call, never a list and never a Sampler. With
  ``ideal_mode="set_options"`` it calls ``backend.set_options(noise_model="ideal")``, the only IonQ
  mode whose counts are Binomial samples; any other noise model (and the ``noise_model`` run kwarg)
  gives round(p shots) counts, so those records are labelled ``sampled: false`` and the MLAE refuses
  them. ``sampled`` is read back from the backend's own ``options.noise_model``.
- IonQ records (schema ``neutron_qae.ionq_record`` v1) are the dicts ``IonQRunner.run_point``
  returns; 04-03 prints them after ``IONQ_RECORD=`` and Hippolyte pastes them into
  ``data/ionq_runs.json``. ``validate_ionq_record`` re-derives everything checkable (widths, sums,
  hits, n_A, sampled) because that file is hand-pasted, untrusted JSON.
- Count keys are little-endian: with n classical bits the bit of qubit/clbit j is key character
  n - 1 - j, and with every qubit measured the flag (the top qubit) is key character 0.
  ``hits_from_counts`` validates width, characters, values and the total.

No backend is constructed here and nothing from qiskit_aer, qiskit_algorithms or qiskit_ionq is
imported; the backend is always a parameter (Phase 1 compliance gates).
"""
from __future__ import annotations

import json
import math
import numbers
import os
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

import numpy as np

from neutron_qae import mlae
from neutron_qae.exact import REGISTER_LAYOUT
from neutron_qae.grover import (
    TRANSPILE_SEED,
    check_ionq_safe,
    power_circuit,
    resources,
    transpile_once,
)
from neutron_qae.mlae import MAX_POWER, PowerResult
from neutron_qae.oracle import MODEL_FLAG, MODEL_QUBITS, MODELS, OracleProblem
from neutron_qae.smoke import is_ionq

__all__ = [
    "BODY_BYTES_PER_GATE",
    "IONQ_IDEAL_MODES",
    "IONQ_MAX_K",
    "IONQ_RUNS_FILE",
    "MAX_RECORDS_BYTES",
    "MAX_SHOTS",
    "MIN_SHOTS",
    "MODEL_LAYOUT",
    "RECORD_KEYS",
    "RECORD_SCHEMA",
    "RECORD_SCHEMA_VERSION",
    "AnalyticRunner",
    "BackendRunner",
    "IonQRunner",
    "Runner",
    "hits_from_counts",
    "ionq_estimate",
    "ionq_power_results",
    "load_ionq_records",
    "validate_ionq_record",
]

IONQ_RUNS_FILE = "data/ionq_runs.json"   # literal path: Qollab loads data files only by literal string
IONQ_MAX_K = 8                           # largest Grover power sent to IonQ in one run
MIN_SHOTS = 2
MAX_SHOTS = 10_000
MAX_RECORDS_BYTES = 2_000_000            # Qollab's per-file limit, decimal reading
IONQ_IDEAL_MODES = ("none", "set_options")
BODY_BYTES_PER_GATE = 56                 # measured request bytes per gate, qiskit-ionq 1.0.2
MODEL_LAYOUT = {
    "Q0": "x(5), flag = qubit 4 (x == 16)",
    "Q1": REGISTER_LAYOUT + " | T<<11",
    "Q1lite": "x(5) | a<<5 | e<<6 | T<<7",
}
RECORD_SCHEMA = "neutron_qae.ionq_record"
RECORD_SCHEMA_VERSION = 1
RECORD_KEYS = ("schema", "schema_version", "model", "layout", "qubits", "flag", "k", "shots", "hits",
               "p_flag", "p_expected", "noise_model", "ideal_mode", "sampled", "accepted", "error",
               "counts", "n_A", "cx", "depth", "size", "max_controls", "body_bytes_est",
               "backend_class", "backend_name", "qiskit", "qiskit_ionq", "run_s", "timestamp")


@runtime_checkable
class Runner(Protocol):
    """What every runner offers: a name and run(ks, shots) -> PowerResults in input order."""

    name: str

    def run(self, ks, shots) -> list[PowerResult]: ...


def _is_int(value) -> bool:
    return isinstance(value, numbers.Integral) and not isinstance(value, bool)


def _check_ks(ks, max_k: int = MAX_POWER) -> list[int]:
    if isinstance(ks, (str, bytes)) or not isinstance(ks, Sequence) or len(ks) == 0:
        raise ValueError(f"ks must be a non-empty sequence of Grover powers, got {ks!r}")
    out = []
    for k in ks:
        if not _is_int(k) or not 0 <= k <= max_k:
            raise ValueError(f"every k must be an integer in 0..{max_k}, got {k!r}")
        out.append(int(k))
    return out


def _check_shots(shots, n: int) -> list[int]:
    if _is_int(shots):
        values = [shots] * n
    elif isinstance(shots, Sequence) and not isinstance(shots, (str, bytes)):
        values = list(shots)
        if len(values) != n:
            raise ValueError(f"shots has {len(values)} entries for {n} powers")
    else:
        raise ValueError(f"shots must be an integer or a sequence of integers, got {shots!r}")
    for s in values:
        if not _is_int(s) or s < 1:
            raise ValueError(f"every shots value must be an integer >= 1, got {s!r}")
    return [int(s) for s in values]


def hits_from_counts(counts, flag_pos: int, n_clbits: int, shots: int | None = None) -> int:
    """Number of shots whose flag bit (clbit ``flag_pos`` of ``n_clbits``) reads 1.

    Spaces in keys (several classical registers) are stripped; every key must then have
    ``n_clbits`` characters, all 0 or 1; values must be non-negative integers; keys absent from
    ``counts`` count 0; when ``shots`` is given the values must sum to it. ValueError otherwise.
    """
    if not isinstance(counts, Mapping):
        raise ValueError(f"counts must be a mapping, got {type(counts).__name__}")  # noqa: TRY004 - untrusted input
    if not _is_int(n_clbits) or n_clbits < 1 or not _is_int(flag_pos) or not 0 <= flag_pos < n_clbits:
        raise ValueError(f"need 0 <= flag_pos < n_clbits, got flag_pos={flag_pos!r}, n_clbits={n_clbits!r}")
    idx = n_clbits - 1 - flag_pos
    hits = total = 0
    for key, value in counts.items():
        if not isinstance(key, str):
            raise ValueError(f"count key {key!r} is not a string")  # noqa: TRY004
        bits = key.replace(" ", "")
        if len(bits) != n_clbits or set(bits) - {"0", "1"}:
            raise ValueError(f"count key {key!r} is not a {n_clbits}-bit binary string")
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not float(value).is_integer() \
                or value < 0:
            raise ValueError(f"count for {key!r} must be a non-negative integer, got {value!r}")
        value = int(value)
        total += value
        if bits[idx] == "1":
            hits += value
    if shots is not None and total != shots:
        raise ValueError(f"counts sum to {total}, expected shots = {shots}")
    return hits


class BackendRunner:
    """A·Q^k list jobs on an injected local backend (Aer, BasicSimulator); never IonQ."""

    def __init__(self, backend, problem: OracleProblem, measure: str = "flag",
                 seed_transpiler: int = TRANSPILE_SEED, run_options: dict | None = None):
        if is_ionq(backend):
            raise ValueError("BackendRunner sends circuit lists; use IonQRunner for an IonQ backend "
                             "(one bare circuit per run)")
        if not isinstance(problem, OracleProblem):
            raise TypeError(f"problem must be an OracleProblem from make_problem, got {type(problem).__name__}")
        if measure not in ("flag", "all"):
            raise ValueError(f"measure must be 'flag' or 'all', got {measure!r}")
        run_options = dict(run_options or {})
        if "shots" in run_options:
            raise ValueError("pass shots to run(), not in run_options")
        self.backend = backend
        self.problem = problem
        self.measure = measure
        self.seed_transpiler = seed_transpiler
        self.run_options = run_options
        self.name = "backend:" + str(getattr(backend, "name", type(backend).__name__))
        self.last_counts: list[dict] = []
        self._cache: dict[int, object] = {}

    @property
    def _layout(self) -> tuple[int, int]:
        """(flag clbit, number of clbits) of the measured circuits."""
        if self.measure == "flag":
            return 0, 1
        return self.problem.flag, self.problem.qubits

    def circuits(self, ks) -> list:
        """Transpiled A·Q^k circuits (one transpile each, cached per k)."""
        out = []
        for k in _check_ks(ks):
            if k not in self._cache:
                self._cache[k] = transpile_once(
                    power_circuit(self.problem.A, self.problem.flag, k, measure=self.measure),
                    self.seed_transpiler)
            out.append(self._cache[k])
        return out

    def run(self, ks, shots) -> list[PowerResult]:
        """One backend.run(list) per distinct shots value; PowerResults in input order."""
        ks = _check_ks(ks)
        shots = _check_shots(shots, len(ks))
        circs = self.circuits(ks)
        groups: dict[int, list[int]] = {}
        for i, s in enumerate(shots):
            groups.setdefault(s, []).append(i)
        flag_pos, n_clbits = self._layout
        records: list = [None] * len(ks)
        counts_out: list = [None] * len(ks)
        for s, idx in groups.items():
            result = self.backend.run([circs[i] for i in idx], shots=s, **self.run_options).result()
            for j, i in enumerate(idx):
                counts = dict(result.get_counts(j))
                counts_out[i] = counts
                hits = hits_from_counts(counts, flag_pos, n_clbits, s)
                records[i] = PowerResult(ks[i], s, hits, source=self.name)
        self.last_counts = counts_out
        return records


class AnalyticRunner:
    """Binomial emulator of an ideal A·Q^k run: no circuits, exact sin^2((2k + 1) theta).

    Draw order (documented for Phase 5 reproducibility): one ``self.rng.binomial(shots_i, p_i)``
    per entry of ``ks``, in input order, with p_i = sin^2((2 k_i + 1) asin sqrt(p)).
    """

    name = "analytic"

    def __init__(self, p: float, rng=None):
        if isinstance(p, bool) or not isinstance(p, numbers.Real) or not 0.0 <= float(p) <= 1.0:
            raise ValueError(f"p must be a probability in [0, 1], got {p!r}")
        self.p = float(p)
        self.theta = math.asin(math.sqrt(self.p))
        self.rng = np.random.default_rng(rng)

    def run(self, ks, shots) -> list[PowerResult]:
        ks = _check_ks(ks)
        shots = _check_shots(shots, len(ks))
        out = []
        for k, n in zip(ks, shots):
            pk = math.sin((2 * k + 1) * self.theta) ** 2
            out.append(PowerResult(k, n, int(self.rng.binomial(int(n), float(pk))), source="analytic"))
        return out


def _is_record_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class IonQRunner:
    """One A·Q^k circuit per Qollab IonQ run: bare circuit, every qubit measured, one backend.run call."""

    name = "ionq"

    def __init__(self, backend, problem: OracleProblem, ideal_mode: str = "set_options", max_k: int = IONQ_MAX_K):
        if not is_ionq(backend):
            raise ValueError("IonQRunner needs an IonQ backend (qiskit_ionq); use BackendRunner for local simulators")
        if ideal_mode == "kwarg":
            raise ValueError("ideal_mode 'kwarg' (run(..., noise_model='ideal')) yields round(p shots) counts, "
                             "never statistics; use 'set_options' or 'none'")
        if ideal_mode not in IONQ_IDEAL_MODES:
            raise ValueError(f"ideal_mode must be one of {IONQ_IDEAL_MODES}, got {ideal_mode!r}")
        if not isinstance(problem, OracleProblem):
            raise TypeError(f"problem must be an OracleProblem from make_problem, got {type(problem).__name__}")
        if not _is_int(max_k) or not 0 <= max_k <= IONQ_MAX_K:
            raise ValueError(f"max_k must be an integer in 0..{IONQ_MAX_K}, got {max_k!r}")
        self.backend = backend
        self.problem = problem
        self.ideal_mode = ideal_mode
        self.max_k = int(max_k)
        self.last_record: dict | None = None

    def run_point(self, k, shots) -> dict:
        """Submit ONE circuit (A·Q^k, all qubits measured) and return the IonQ record dict.

        Inputs are validated before any job; the circuit is transpiled once and checked IonQ-safe;
        a failed set_options or submission yields ``accepted: False`` with the error, never a retry.
        """
        if not _is_int(k) or not 0 <= k <= self.max_k:
            raise ValueError(f"k must be an integer in 0..{self.max_k} on IonQ, got {k!r}")
        if not _is_int(shots) or not MIN_SHOTS <= shots <= MAX_SHOTS:
            raise ValueError(f"shots must be an integer in {MIN_SHOTS}..{MAX_SHOTS}, got {shots!r}")
        k, shots = int(k), int(shots)
        pr = self.problem
        tc = check_ionq_safe(transpile_once(power_circuit(pr.A, pr.flag, k, measure="all")))
        res = resources(tc)
        error = None
        if self.ideal_mode == "set_options":
            try:
                self.backend.set_options(noise_model="ideal")   # mutates the injected backend only
            except Exception as exc:  # noqa: BLE001 - record, never crash the run
                error = f"set_options(noise_model='ideal') failed: {type(exc).__name__}: {exc}"
        noise_model = getattr(getattr(self.backend, "options", None), "noise_model", None)
        noise_model = None if noise_model is None else str(noise_model)
        counts: dict = {}
        hits = None
        run_s = None
        if error is None:
            t0 = time.perf_counter()
            try:
                job = self.backend.run(tc, shots=shots)          # bare QuantumCircuit -> ionq.circuit.v1
                raw = dict(job.result().get_counts())
                hits = hits_from_counts(raw, pr.flag, pr.qubits, shots)
                counts = {str(key): int(v) for key, v in raw.items()}
            except Exception as exc:  # noqa: BLE001 - AttributeError inside qiskit-ionq masks an IonQ error
                error = f"{type(exc).__name__}: {exc}"
                hits = None
            run_s = round(time.perf_counter() - t0, 3)
        cls = type(self.backend)
        record = {
            "schema": RECORD_SCHEMA,
            "schema_version": RECORD_SCHEMA_VERSION,
            "model": pr.model,
            "layout": MODEL_LAYOUT[pr.model],
            "qubits": pr.qubits,
            "flag": pr.flag,
            "k": k,
            "shots": shots,
            "hits": hits,
            "p_flag": None if hits is None else hits / shots,
            "p_expected": math.sin((2 * k + 1) * pr.theta) ** 2,
            "noise_model": noise_model,
            "ideal_mode": self.ideal_mode,
            "sampled": noise_model == "ideal",
            "accepted": error is None,
            "error": error,
            "counts": counts,
            "n_A": shots * (2 * k + 1),
            "cx": res["cx"],
            "depth": res["depth"],
            "size": res["size"],
            "max_controls": res["max_controls"],
            "body_bytes_est": BODY_BYTES_PER_GATE * res["size"],
            "backend_class": f"{cls.__module__}.{cls.__qualname__}",
            "backend_name": str(getattr(self.backend, "name", None)),
            "qiskit": _qiskit_version(),
            "qiskit_ionq": getattr(sys.modules.get("qiskit_ionq"), "__version__", None),
            "run_s": run_s,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self.last_record = record
        return record

    def run(self, ks, shots) -> list[PowerResult]:
        """Runner interface; exactly one k (one circuit per Qollab IonQ run)."""
        ks = _check_ks(ks, self.max_k)
        if len(ks) != 1:
            raise ValueError(f"IonQRunner runs exactly one Grover power per run (one circuit per Qollab "
                             f"IonQ job), got {len(ks)}")
        if not _is_int(shots) and isinstance(shots, Sequence) and not isinstance(shots, (str, bytes)) \
                and len(shots) == 1:
            shots = shots[0]
        rec = self.run_point(ks[0], shots)
        if not rec["accepted"]:
            raise RuntimeError(f"IonQ run failed: {rec['error']}")
        return [PowerResult(rec["k"], rec["shots"], rec["hits"], source=f"ionq:{rec['noise_model']}",
                            sampled=rec["sampled"])]


def _qiskit_version() -> str | None:
    return getattr(sys.modules.get("qiskit"), "__version__", None)


def validate_ionq_record(rec) -> dict:
    """Check an IonQ record (untrusted, hand-pasted JSON); ValueError naming the field, else rec unchanged."""
    if not isinstance(rec, dict):
        raise ValueError(f"record must be a JSON object, got {type(rec).__name__}")  # noqa: TRY004
    missing = [key for key in RECORD_KEYS if key not in rec]
    if missing:
        raise ValueError(f"record lacks field(s): {', '.join(missing)}")

    def bad(field, why):
        return ValueError(f"record field {field!r} {why} (got {rec.get(field)!r})")

    if rec["schema"] != RECORD_SCHEMA:
        raise bad("schema", f"must be {RECORD_SCHEMA!r}")
    if not _is_record_int(rec["schema_version"]) or rec["schema_version"] != RECORD_SCHEMA_VERSION:
        raise bad("schema_version", f"must be {RECORD_SCHEMA_VERSION}")
    model = rec["model"]
    if not isinstance(model, str) or model not in MODELS:
        raise bad("model", f"must be one of {', '.join(MODELS)}")
    if rec["layout"] != MODEL_LAYOUT[model]:
        raise bad("layout", f"must be {model}'s layout")
    if not _is_record_int(rec["qubits"]) or rec["qubits"] != MODEL_QUBITS[model]:
        raise bad("qubits", f"must be {MODEL_QUBITS[model]} for {model}")
    if not _is_record_int(rec["flag"]) or rec["flag"] != MODEL_FLAG[model]:
        raise bad("flag", f"must be {MODEL_FLAG[model]} for {model}")
    k, shots = rec["k"], rec["shots"]
    if not _is_record_int(k) or not 0 <= k <= IONQ_MAX_K:
        raise bad("k", f"must be an integer in 0..{IONQ_MAX_K}")
    if not _is_record_int(shots) or not MIN_SHOTS <= shots <= MAX_SHOTS:
        raise bad("shots", f"must be an integer in {MIN_SHOTS}..{MAX_SHOTS}")
    if rec["accepted"] is not True:
        raise bad("accepted", "must be true (failed submissions are not results)")
    counts = rec["counts"]
    if not isinstance(counts, dict) or not counts:
        raise bad("counts", "must be a non-empty object")
    try:
        hits = hits_from_counts(counts, rec["flag"], rec["qubits"], shots)
    except ValueError as exc:
        raise ValueError(f"record field 'counts' is invalid: {exc}") from None
    if not _is_record_int(rec["hits"]) or rec["hits"] != hits:
        raise bad("hits", f"must equal the flag count recomputed from counts ({hits})")
    p_flag = rec["p_flag"]
    if isinstance(p_flag, bool) or not isinstance(p_flag, (int, float)) or abs(p_flag - hits / shots) > 1e-12:
        raise bad("p_flag", "must equal hits / shots")
    if not _is_record_int(rec["n_A"]) or rec["n_A"] != shots * (2 * k + 1):
        raise bad("n_A", f"must equal shots (2k + 1) = {shots * (2 * k + 1)}")
    if rec["ideal_mode"] not in IONQ_IDEAL_MODES:
        raise bad("ideal_mode", f"must be one of {IONQ_IDEAL_MODES}")
    noise_model = rec["noise_model"]
    if noise_model is not None and not isinstance(noise_model, str):
        raise bad("noise_model", "must be a string")
    if not isinstance(rec["sampled"], bool) or rec["sampled"] != (noise_model == "ideal"):
        raise bad("sampled", "must be true exactly when noise_model is 'ideal'")
    if not isinstance(rec["timestamp"], str) or not rec["timestamp"]:
        raise bad("timestamp", "must be a non-empty string")
    return rec


def load_ionq_records(path=None) -> list[dict]:
    """Validated IonQ records from ``path`` (default: ``IONQ_RUNS_FILE``, read at call time).

    A missing file is []; a file above MAX_RECORDS_BYTES, a non-list document, an invalid record
    (named by index) or a duplicate (timestamp, model, k, shots, ideal_mode) raises ValueError.
    """
    path = IONQ_RUNS_FILE if path is None else path
    try:
        size = os.path.getsize(path)
    except FileNotFoundError:
        return []
    if size > MAX_RECORDS_BYTES:
        raise ValueError(f"{path} is {size} bytes, above the {MAX_RECORDS_BYTES}-byte limit")
    with open(path, encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} is not valid JSON: {exc}") from None
    if not isinstance(data, list):
        raise ValueError(f"{path} must hold a JSON list of records, got {type(data).__name__}")  # noqa: TRY004
    seen = set()
    for i, rec in enumerate(data):
        try:
            validate_ionq_record(rec)
        except ValueError as exc:
            raise ValueError(f"{path} record {i}: {exc}") from None
        key = (rec["timestamp"], rec["model"], rec["k"], rec["shots"], rec["ideal_mode"])
        if key in seen:
            raise ValueError(f"{path} record {i} duplicates an earlier record {key}")
        seen.add(key)
    return data


def ionq_power_results(records, models=("Q1", "Q1lite")) -> list[PowerResult]:
    """PowerResults of the validated, sampled records whose model is in ``models`` (Q1 and Q1lite share T1)."""
    out = []
    for rec in records:
        validate_ionq_record(rec)
        if rec["sampled"] and rec["model"] in models:
            out.append(PowerResult(rec["k"], rec["shots"], rec["hits"], source=f"ionq:{rec['noise_model']}"))
    return out


def ionq_estimate(records=None, models=("Q1", "Q1lite")):
    """IonQ-only MLAE estimate, or None unless a sampled k = 0 record is present.

    A single k >= 1 power is ambiguous (sin^2((2k + 1) theta) has 2k + 1 maxima on [0, pi/2]).
    """
    if records is None:
        records = load_ionq_records()
    prs = ionq_power_results(records, models)
    if not any(r.k == 0 for r in prs):
        return None
    return mlae.estimate(prs)
