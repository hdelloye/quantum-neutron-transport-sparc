"""Quantum oracle A (QC-01..QC-03): contract gate, layout, support, invertibility, Aer, edges."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from qiskit.quantum_info import Operator, Statevector, state_fidelity
from random_doubles import foreign_imports

from neutron_qae.exact import bitstring_probabilities_k1, transmission_within
from neutron_qae.kernels import BACK, build_kernels
from neutron_qae.oracle import MODELS, ContractError, check_contract, make_problem
from neutron_qae.problem import sparc_first_wall

ROOT = Path(__file__).resolve().parents[1]
K = build_kernels(sparc_first_wall())
T0 = transmission_within(K, 0)
T1 = transmission_within(K, 1)
ZERO = 1e-15                       # "no amplitude" threshold for a probability


@pytest.fixture(scope="module")
def q1():
    return make_problem("Q1")


@pytest.fixture(scope="module")
def q1_probs(q1):
    """Full 4096-entry probability vector of Q1's A|0>."""
    return Statevector(q1.A).probabilities()


def test_q1_flag_probability_equals_exact_T1():
    pr = make_problem("Q1")
    assert pr.qubits == 12 and pr.A.num_qubits == 12
    assert pr.flag == 11 and pr.K == 1 and pr.model == "Q1"
    assert pr.reference == T1
    assert abs(pr.p - T1) <= 1e-12


def test_q0_flag_probability_equals_exp_minus_tau():
    pr = make_problem("Q0")
    assert pr.qubits == 5 and pr.flag == 4 and pr.K == 0
    assert abs(pr.p - math.exp(-float(K.spec.tau_x(K.spec.width_x)))) <= 1e-12
    assert abs(pr.p - T0) <= 1e-12
    assert pr.reference == T0


def test_q1_bitstring_probabilities_match_enumeration(q1, q1_probs):
    low = Statevector(q1.A).probabilities(list(range(11)))
    ent = bitstring_probabilities_k1(K)
    ref = np.zeros(2 ** 11)
    for s, p, _ in ent:
        ref[s] = p
    assert np.abs(low - ref).max() <= 1e-13
    # the flag carries exactly the transmitted predicate, string by string
    on = 1 << q1.flag
    mismatches = 0
    for s, p, t in ent:
        if p > ZERO:
            other = q1_probs[s] if t else q1_probs[s | on]
            if other > 1e-14:
                mismatches += 1
    assert mismatches == 0
    # x = 16 (uncollided) takes column 0's rotations and is always flagged
    s16 = 16 | (3 << 6)
    p16 = {s: p for s, p, _ in ent}[s16]
    assert p16 > 0
    assert abs(q1_probs[s16 | on] - p16) <= 1e-13
    assert q1_probs[s16] <= 1e-14


def test_q1_support_is_the_enumeration(q1):
    low = Statevector(q1.A).probabilities(list(range(11)))
    for s in range(2 ** 11):
        if s & 31 > 16:
            assert low[s] <= ZERO, s
    zero_bins = 0
    for x in range(16):
        for phi in range(16):
            if K.flight[x, phi, BACK] == 0:
                zero_bins += 1
                s = x | 1 << 5 | phi << 6 | 1 << 10
                assert low[s] <= ZERO, s
    assert zero_bins == 168
    positive = sum(1 for _, p, _ in bitstring_probabilities_k1(K) if p > 0)
    assert positive == 728
    assert int((low > ZERO).sum()) == positive


def test_q1lite_flag_probability_equals_T1():
    pr = make_problem("Q1lite")
    assert pr.qubits == 8 and pr.flag == 7 and pr.K == 1
    assert abs(pr.p - T1) <= 1e-12


@pytest.mark.parametrize("model", MODELS)
def test_state_preparation_is_unitary_without_measure_or_reset(model):
    A = make_problem(model).A
    ops = {i.operation.name for i in A.decompose(reps=6).data}
    assert ops <= {"cx", "u"}, ops
    assert not ops & {"measure", "reset", "initialize"}
    back = Statevector(A).evolve(A.inverse())
    assert state_fidelity(back, Statevector.from_label("0" * A.num_qubits)) >= 1 - 1e-12


def test_q0_operator_identity():
    A = make_problem("Q0").A            # 32 x 32 only; never the 4096 x 4096 Q1 operator (Pitfall 10)
    ident = Operator(A).compose(Operator(A.inverse()))
    assert np.allclose(ident.data, np.eye(32), atol=1e-10, rtol=0)


def test_contract_gate_raises_on_mismatch(q1):
    with pytest.raises(ContractError, match="exact reference"):
        check_contract(q1.A, q1.flag, T1 + 1e-9)
    assert check_contract(q1.A, q1.flag, T1) == q1.p
    with pytest.raises(ValueError) as e:
        make_problem("Q2")
    assert all(m in str(e.value) for m in ("Q0", "Q1", "Q1lite"))
    with pytest.raises(ValueError, match="11-bit register layout"):
        make_problem("Q1", build_kernels(sparc_first_wall(nx=8)))
    with pytest.raises(TypeError):
        make_problem("Q1", object())


@pytest.mark.parametrize("width", [6.0, 15.0, 20.0])
def test_contract_holds_at_other_wall_widths(width):
    kk = build_kernels(sparc_first_wall(width_x=width))
    p0 = make_problem("Q0", kk)
    p1 = make_problem("Q1", kk)
    assert p0.reference == transmission_within(kk, 0) and p1.reference == transmission_within(kk, 1)
    assert abs(p0.p - p0.reference) <= 1e-12
    assert abs(p1.p - p1.reference) <= 1e-12


def test_aer_statevector_contract():
    aer_mod = pytest.importorskip("qiskit_aer")
    from neutron_qae.grover import transpile_once
    sim = aer_mod.AerSimulator(method="statevector")
    for model, ref in (("Q1", T1), ("Q0", T0)):
        pr = make_problem(model)
        tc = transpile_once(pr.A)
        tc.save_statevector()
        sv = sim.run(tc).result().get_statevector()
        assert abs(float(sv.probabilities([pr.flag])[1]) - ref) <= 1e-12, model


def test_oracle_imports_stay_pyodide_safe():
    for name in ("oracle.py", "grover.py"):
        path = ROOT / "neutron_qae" / name
        foreign = foreign_imports(path)
        assert foreign <= {"qiskit"}, (name, foreign)
        assert not foreign & {"qiskit_aer", "qiskit_algorithms", "qiskit_ionq"}
