"""Grover powers A Q^k, composed logically and transpiled once to an IonQ-safe basis (QC-04..QC-06).

- Q = ``grover_operator(oracle, state_preparation=A)`` with oracle = Z on the flag (the function;
  the ``GroverOperator`` class is deprecated since Qiskit 2.1). Its global phase pi is left alone:
  it does not change any probability. P(flag) after A Q^k is sin^2((2k + 1) theta), theta = asin sqrt(p).
- Transpile-once rule (PD-16): build the logical A Q^k first (``power_circuit``), including its
  measurements, then call ``transpile_once`` exactly once with ``basis_gates=BASIS``,
  ``optimization_level=1`` and a fixed ``seed_transpiler``. Every gate in the result has at most
  one control, far below IonQ's 7-control limit.
- Never transpile A and Q separately and stitch them: measured at k = 1 that gives
  P(flag) = 0.95787 instead of 0.99941 (RESEARCH Pitfall 1; the standalone Q synthesis treats
  qubits idle at its start as clean ancillas, which is false mid-circuit).
- Never ``transpile(c, backend)``: the IonQ target leaves an 11-control ``mcx`` that IonQ
  rejects, and the Aer target leaves ``multiplexer`` instructions that segfault Aer at k = 16
  (RESEARCH Pitfall 2). The explicit BASIS works for Aer, BasicSimulator and IonQ alike.

This module imports only qiskit and neutron_qae and never constructs a backend.
"""
from __future__ import annotations

import numbers

from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.circuit.library import grover_operator

from neutron_qae.oracle import MAX_QUBITS

__all__ = [
    "ALLOWED_OPS",
    "BASIS",
    "MAX_CONTROLS",
    "TRANSPILE_SEED",
    "grover",
    "max_controls",
    "power_circuit",
    "transpile_once",
]

BASIS = ["cx", "rz", "ry", "rx", "h", "x", "sx"]     # every name is in qiskit-ionq's basis
ALLOWED_OPS = frozenset(BASIS) | {"measure"}
MAX_CONTROLS = 7                                    # IonQ TooManyControls limit
TRANSPILE_SEED = 1
MEASURE_MODES = ("none", "flag", "all")


def grover(A: QuantumCircuit, flag: int) -> QuantumCircuit:
    """The Grover operator Q = A S_0 A^-1 S_chi with S_chi = Z on the flag."""
    oracle = QuantumCircuit(A.num_qubits)
    oracle.z(flag)
    return grover_operator(oracle, state_preparation=A)


def power_circuit(A: QuantumCircuit, flag: int, k: int, measure: str = "flag") -> QuantumCircuit:
    """Logical A Q^k (A copied, Q composed k times) plus measurements; untranspiled.

    measure = "none" adds nothing; "flag" adds ClassicalRegister(1, "flag") measuring the flag
    (count keys '0'/'1'); "all" adds ClassicalRegister(n, "meas") measuring qubit i into bit i
    with no barrier (n-bit keys, the flag, the top qubit, at key index 0).
    """
    if isinstance(k, bool) or not isinstance(k, numbers.Integral) or k < 0:
        raise ValueError(f"k must be an integer >= 0, got {k!r}")
    if measure not in MEASURE_MODES:
        raise ValueError(f"measure must be one of {', '.join(MEASURE_MODES)}, got {measure!r}")
    k = int(k)
    c = A.copy()
    if k:
        G = grover(A, flag)
        for _ in range(k):
            c.compose(G, inplace=True)
    if measure == "flag":
        cr = ClassicalRegister(1, "flag")
        c.add_register(cr)
        c.measure(flag, cr[0])
    elif measure == "all":
        n = A.num_qubits
        cr = ClassicalRegister(n, "meas")
        c.add_register(cr)
        c.measure(range(n), cr)
    c.name = f"AQ{k}"
    return c


def transpile_once(c: QuantumCircuit, seed: int = TRANSPILE_SEED) -> QuantumCircuit:
    """The single transpile every executed circuit gets: explicit BASIS, opt level 1, fixed seed."""
    if c.num_qubits > MAX_QUBITS:
        raise ValueError(f"circuit has {c.num_qubits} qubits, above the {MAX_QUBITS}-qubit budget")
    return transpile(c, basis_gates=BASIS, optimization_level=1, seed_transpiler=seed)


def max_controls(c: QuantumCircuit) -> int:
    """Largest num_ctrl_qubits over the circuit's instructions (0 for an empty circuit)."""
    return max((int(getattr(i.operation, "num_ctrl_qubits", 0) or 0) for i in c.data), default=0)
