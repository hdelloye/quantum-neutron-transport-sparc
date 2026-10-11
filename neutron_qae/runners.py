"""Runners that turn (ks, shots) into flag-hit records for the MLAE (QAE-02).

Every runner has ``run(ks, shots) -> list[PowerResult]`` (records in input order), so the analytic
emulator, an injected local simulator and the IonQ one-circuit path feed ``mlae.estimate`` the same
way. Circuits always come from a contract-checked ``OracleProblem`` (``oracle.make_problem``), are
built by ``grover.power_circuit`` and transpiled exactly once by ``grover.transpile_once``.

- ``BackendRunner(backend, problem)``: any injected local backend (Aer from tests and scripts,
  Qollab's Built-in ``BasicSimulator``). One ``backend.run(list_of_circuits)`` per distinct shots
  value; refuses an IonQ backend (Qollab's IonQ proxy accepts one bare circuit per run).
- Count keys are little-endian: with n classical bits the bit of qubit/clbit j is key character
  n - 1 - j, and with every qubit measured the flag (the top qubit) is key character 0.
  ``hits_from_counts`` validates width, characters, values and the total.

No backend is constructed here and nothing from qiskit_aer, qiskit_algorithms or qiskit_ionq is
imported; the backend is always a parameter (Phase 1 compliance gates).
"""
from __future__ import annotations

import numbers
from collections.abc import Mapping, Sequence

from neutron_qae.grover import TRANSPILE_SEED, power_circuit, transpile_once
from neutron_qae.mlae import MAX_POWER, PowerResult
from neutron_qae.oracle import OracleProblem
from neutron_qae.smoke import is_ionq

__all__ = [
    "BODY_BYTES_PER_GATE",
    "IONQ_IDEAL_MODES",
    "IONQ_MAX_K",
    "IONQ_RUNS_FILE",
    "MAX_RECORDS_BYTES",
    "MAX_SHOTS",
    "MIN_SHOTS",
    "BackendRunner",
    "hits_from_counts",
]

IONQ_RUNS_FILE = "data/ionq_runs.json"   # literal path: Qollab loads data files only by literal string
IONQ_MAX_K = 8                           # largest Grover power sent to IonQ in one run
MIN_SHOTS = 2
MAX_SHOTS = 10_000
MAX_RECORDS_BYTES = 2_000_000            # Qollab's per-file limit, decimal reading
IONQ_IDEAL_MODES = ("none", "set_options")
BODY_BYTES_PER_GATE = 56                 # measured request bytes per gate, qiskit-ionq 1.0.2


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
