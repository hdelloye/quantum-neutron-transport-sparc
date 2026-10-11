"""Quantum oracles A for the frozen Kernels contract: Q0, Q1 and the Q1lite fallback (QC-01..QC-03).

Every random choice of the K = 1 lattice model gets its own fresh register, and qubit i is
bit i of exact.py's string ``s = x | a << 5 | phi << 6 | e << 10`` (``REGISTER_LAYOUT``,
little-endian, so Qiskit qubit i = bit i of s). The flag T is always the highest qubit.

======== ======= ========= ========================================================
Model    Qubits  Flag      Registers (qubit indices)
======== ======= ========= ========================================================
Q0       5       4         x(0-4): first-collision column, x = 16 means uncollided
Q1       12      11        x(0-4) a(5) phi(6-9) e(10) T(11)
Q1lite   8       7         x(0-4) a(5) e(6) T(7), escape angle averaged over phi
======== ======= ========= ========================================================

- x: one ``StatePreparation`` of sqrt(first_collision) padded to 32 amplitudes (x = 17..31
  carry amplitude 0). a: ``UCRYGate`` with angle 2 asin sqrt(scatter_ratio[j]) controlled on
  x[0:4]. phi: Hadamards (16 uniform direction bins). e: ``UCRYGate`` with angle
  2 asin sqrt(flight[j, b, BACK]) controlled on x[0:4] then phi, angle index j + 16 b
  (controls least-significant first). T = x4 OR (NOT x4 AND a AND e).
- x = 16 rule: the rotations controlled on x[0:4] see 0000 for x = 16, so the uncollided
  branch rotates a and e exactly like column 0. That is exact.py's ``col = x % nx``
  convention, and it is harmless because T = 1 whenever x4 = 1.
- No measurement, reset or ``initialize()`` appears in A (``initialize`` would add a reset and
  break A^-1), so A is a unitary and the Grover operator can use A^-1.
- Q1lite exists only as the IonQ size-ladder fallback (PD-15). Its flag probability is the
  exact T1 too, but its strings carry no direction bin, so Phase 3's ``sample_exit_rows``
  cannot consume them; Q1 keeps phi for that reason.
- Contract gate (ROADMAP SC1): ``make_problem`` computes the Statevector flag probability and
  raises ``ContractError`` unless it equals ``exact.transmission_within(kernels, K)`` within
  ``CONTRACT_TOL = 1e-12`` (K = 0 for Q0, 1 for Q1 and Q1lite). Runners and main.py take every
  circuit from ``make_problem``.
- Budget: Q1 uses 12 of the 24 qubits allowed (``MAX_QUBITS``); no phase-estimation, ancilla or
  step-counter register is added.

This module imports only the stdlib, numpy, qiskit and neutron_qae; it never constructs a
backend (Pyodide-safe for the Qollab path).
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation, UCRYGate
from qiskit.quantum_info import Statevector

from neutron_qae.exact import A_BITS, N_BITS, PHI_BITS, X_BITS, transmission_within
from neutron_qae.kernels import BACK, Kernels, build_kernels
from neutron_qae.problem import sparc_first_wall

__all__ = [
    "CONTRACT_TOL",
    "MAX_QUBITS",
    "MODELS",
    "MODEL_FLAG",
    "MODEL_K",
    "MODEL_QUBITS",
    "ContractError",
    "OracleProblem",
    "build_q0",
    "build_q1",
    "check_contract",
    "flag_probability",
    "make_problem",
    "x_amplitudes",
]

MODELS = ("Q0", "Q1", "Q1lite")
MODEL_QUBITS = {"Q0": 5, "Q1": 12, "Q1lite": 8}
MODEL_FLAG = {"Q0": 4, "Q1": 11, "Q1lite": 7}
MODEL_K = {"Q0": 0, "Q1": 1, "Q1lite": 1}
MAX_QUBITS = 24
CONTRACT_TOL = 1e-12

_NCOL = 2 ** (X_BITS - 1)        # 16 columns addressed by x[0:4]
_NDIR = 2 ** PHI_BITS            # 16 direction bins


def _check_layout(kernels) -> None:
    if not isinstance(kernels, Kernels):
        raise TypeError(f"kernels must be a neutron_qae.kernels.Kernels, got {type(kernels).__name__}")
    nx, nd_ = kernels.spec.nx, kernels.spec.n_dir
    if nx != _NCOL or nd_ != _NDIR:
        raise ValueError(f"the 11-bit register layout needs nx == {_NCOL} and n_dir == {_NDIR}; "
                         f"got nx={nx}, n_dir={nd_}")


def x_amplitudes(kernels: Kernels) -> np.ndarray:
    """sqrt(first_collision) padded to 2**X_BITS = 32 amplitudes (x = 17..31 have amplitude 0)."""
    a = np.zeros(2 ** X_BITS)
    a[:kernels.spec.nx + 1] = np.sqrt(kernels.first_collision)
    return a


def build_q0(kernels: Kernels) -> tuple[QuantumCircuit, int]:
    """Q0: 5 qubits, flag = qubit 4 (x == 16, uncollided). Returns (A, flag)."""
    _check_layout(kernels)
    qc = QuantumCircuit(X_BITS, name="A_Q0")
    qc.append(StatePreparation(x_amplitudes(kernels)), range(X_BITS))
    return qc, X_BITS - 1


def build_q1(kernels: Kernels, direction: bool = True) -> tuple[QuantumCircuit, int]:
    """Q1 (12 qubits, flag 11) or, with direction=False, Q1lite (8 qubits, flag 7). Returns (A, flag)."""
    _check_layout(kernels)
    X, A_ = list(range(X_BITS)), X_BITS
    if direction:
        PH = list(range(X_BITS + A_BITS, X_BITS + A_BITS + PHI_BITS))
        E, T = X_BITS + A_BITS + PHI_BITS, N_BITS
        qc = QuantumCircuit(N_BITS + 1, name="A_Q1")
    else:
        E, T = X_BITS + A_BITS, X_BITS + A_BITS + 1
        qc = QuantumCircuit(T + 1, name="A_Q1lite")
    qc.append(StatePreparation(x_amplitudes(kernels)), X)
    qc.append(UCRYGate([float(2 * np.arcsin(np.sqrt(c))) for c in kernels.scatter_ratio]), [A_] + X[:4])
    if direction:
        qc.h(PH)                                                     # 16 uniform direction bins
        ang = [float(2 * np.arcsin(np.sqrt(kernels.flight[j, b, BACK])))
               for b in range(_NDIR) for j in range(_NCOL)]          # angle index j + 16 b
        qc.append(UCRYGate(ang), [E] + X[:4] + PH)                   # first control = LSB
    else:
        ang = [float(2 * np.arcsin(np.sqrt(kernels.flight[j, :, BACK].mean()))) for j in range(_NCOL)]
        qc.append(UCRYGate(ang), [E] + X[:4])
    qc.cx(X[4], T); qc.x(X[4]); qc.mcx([X[4], A_, E], T); qc.x(X[4])   # T = x4 OR (NOT x4 AND a AND e)
    return qc, T


def flag_probability(A: QuantumCircuit, flag: int) -> float:
    """P(flag = 1) of A|0...0> from qiskit's exact Statevector."""
    return float(Statevector(A).probabilities([flag])[1])


class ContractError(RuntimeError):
    """The circuit's flag probability differs from the frozen exact reference."""


def check_contract(A: QuantumCircuit, flag: int, reference: float, tol: float = CONTRACT_TOL) -> float:
    """Return the flag probability of A; raise ContractError if it differs from reference by more than tol."""
    p = flag_probability(A, flag)
    d = abs(p - float(reference))
    if not d <= tol:
        raise ContractError(f"{A.name}: flag P {p!r} != exact reference {float(reference)!r} "
                            f"(|d| = {d:.3e} > tol {tol:.1e})")
    return p


@dataclass(frozen=True, eq=False)
class OracleProblem:
    """A contract-checked oracle: A, its flag qubit, K, the flag probability p and the exact T_K."""

    model: str
    A: QuantumCircuit
    flag: int
    K: int
    p: float
    reference: float
    kernels: Kernels

    @property
    def theta(self) -> float:
        """Grover angle: P(flag) after A Q^k is sin^2((2k + 1) theta)."""
        return math.asin(math.sqrt(self.p))

    @property
    def qubits(self) -> int:
        return self.A.num_qubits


@functools.lru_cache(maxsize=1)
def _default_kernels() -> Kernels:
    return build_kernels(sparc_first_wall())     # Kernels is immutable; circuits are never cached


def make_problem(model: str = "Q1", kernels: Kernels | None = None, tol: float = CONTRACT_TOL) -> OracleProblem:
    """Build model's A from kernels (default: the frozen SPARC first wall) behind the contract gate."""
    if not isinstance(model, str) or model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {', '.join(MODELS)}")
    if kernels is None:
        kernels = _default_kernels()
    _check_layout(kernels)
    A, flag = build_q0(kernels) if model == "Q0" else build_q1(kernels, direction=(model == "Q1"))
    if A.num_qubits > MAX_QUBITS:
        raise ValueError(f"{model} needs {A.num_qubits} qubits, above the {MAX_QUBITS}-qubit budget")
    K = MODEL_K[model]
    reference = transmission_within(kernels, K)
    p = check_contract(A, flag, reference, tol)
    return OracleProblem(model=model, A=A, flag=flag, K=K, p=p, reference=reference, kernels=kernels)
