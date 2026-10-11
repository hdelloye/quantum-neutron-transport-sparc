"""Grover powers A·Q^k (QC-04..QC-06): sin^2 sweep, transpile-once safety, budget, resource table."""
from __future__ import annotations

import ast
import math
import os
from pathlib import Path

import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

from neutron_qae.exact import transmission_within
from neutron_qae.grover import (
    ALLOWED_OPS,
    BASIS,
    check_ionq_safe,
    format_resource_table,
    grover,
    max_controls,
    power_circuit,
    resource_table,
    transpile_once,
)
from neutron_qae.kernels import build_kernels
from neutron_qae.oracle import MODELS, make_problem
from neutron_qae.problem import sparc_first_wall

ROOT = Path(__file__).resolve().parents[1]
K = build_kernels(sparc_first_wall())
T0 = transmission_within(K, 0)
T1 = transmission_within(K, 1)
SWEEP_TOL = 1e-11

# Planner-measured (qiskit 2.5.2, seed_transpiler=1): model, k, qubits, cx, depth, size, max_controls
RESOURCE_ROWS = [
    ("Q0", 0, 5, 26, 82, 89, 1), ("Q0", 1, 5, 100, 270, 304, 1), ("Q0", 2, 5, 174, 458, 519, 1),
    ("Q1", 0, 12, 313, 518, 543, 1), ("Q1", 1, 12, 1503, 2532, 3001, 1), ("Q1", 2, 12, 2693, 4546, 5459, 1),
    ("Q1lite", 0, 8, 73, 166, 187, 1), ("Q1lite", 1, 8, 399, 757, 996, 1), ("Q1lite", 2, 8, 725, 1348, 1805, 1),
]


@pytest.fixture(scope="module")
def problems():
    return {m: make_problem(m) for m in MODELS}


def _p_flag(tc, flag):
    return float(Statevector(tc).probabilities([flag])[1])


def _expected(theta, k):
    return math.sin((2 * k + 1) * theta) ** 2


def _aer_p_flag(tc, flag):
    aer_mod = pytest.importorskip("qiskit_aer")
    tc = tc.copy()
    tc.save_statevector()
    sv = aer_mod.AerSimulator(method="statevector").run(tc).result().get_statevector()
    return float(sv.probabilities([flag])[1])


def test_a_q1_transpiled_once_amplifies_flag():
    pr = make_problem("Q1")
    k = 1
    tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="none"))
    theta = math.asin(math.sqrt(T1))
    assert abs(_p_flag(tc, pr.flag) - _expected(theta, k)) <= SWEEP_TOL
    assert max_controls(tc) <= 7


def test_grover_powers_follow_sin2(problems):
    pr = problems["Q1"]
    theta = math.asin(math.sqrt(T1))
    for k in (0, 1, 2, 3, 4, 8, 16):
        tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="none"))
        assert abs(_p_flag(tc, pr.flag) - _expected(theta, k)) <= SWEEP_TOL, k


def test_q0_grover_powers_up_to_64(problems):
    pr = problems["Q0"]
    theta = math.asin(math.sqrt(T0))
    for k in (0, 1, 2, 4, 8, 16, 32, 64):
        tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="none"))
        assert abs(_p_flag(tc, pr.flag) - _expected(theta, k)) <= SWEEP_TOL, k


def test_q1_grover_powers_32_64_on_aer(problems):
    pytest.importorskip("qiskit_aer")
    pr = problems["Q1"]
    theta = math.asin(math.sqrt(T1))
    for k in (32, 64):
        tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="none"))
        assert abs(_aer_p_flag(tc, pr.flag) - _expected(theta, k)) <= SWEEP_TOL, k


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("NEUTRON_QAE_SLOW") != "1",
                    reason="k = 32, 64 on qiskit's Statevector; run with NEUTRON_QAE_SLOW=1 -m slow")
def test_q1_grover_powers_32_64_statevector_slow(problems):
    pr = problems["Q1"]
    theta = math.asin(math.sqrt(T1))
    for k in (32, 64):
        tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="none"))
        assert abs(_p_flag(tc, pr.flag) - _expected(theta, k)) <= SWEEP_TOL, k


def test_grover_uses_function_api():
    tree = ast.parse((ROOT / "neutron_qae" / "grover.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "grover_operator"]
    assert calls, "grover.py must call grover_operator()"
    for n in ast.walk(tree):
        assert not (isinstance(n, ast.Name) and n.id == "GroverOperator")
        assert not (isinstance(n, ast.Attribute) and n.attr == "GroverOperator")
        if isinstance(n, ast.ImportFrom):
            assert "GroverOperator" not in {a.name for a in n.names}


def test_stitched_transpile_is_wrong(problems):
    """RESEARCH Pitfall 1: transpiling A and Q separately and stitching breaks the amplitudes."""
    pr = problems["Q1"]
    tA = transpile(pr.A, basis_gates=BASIS, optimization_level=1)
    tG = transpile(grover(pr.A, pr.flag), basis_gates=BASIS, optimization_level=1)
    stitched = tA.copy()
    stitched.compose(tG, inplace=True)
    theta = math.asin(math.sqrt(T1))
    assert abs(_p_flag(stitched, pr.flag) - _expected(theta, 1)) > 1e-3     # measured 0.95787 vs 0.99941


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("k", [0, 1, 2])
def test_transpiled_circuits_are_ionq_safe(problems, model, k):
    pr = problems[model]
    tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="all"))
    assert check_ionq_safe(tc) is tc
    assert max_controls(tc) == 1
    ops = tc.count_ops()
    assert set(ops) <= ALLOWED_OPS, set(ops)
    assert ops["measure"] == pr.qubits
    if k == 1:
        with pytest.raises(ValueError, match="not IonQ-safe"):
            check_ionq_safe(power_circuit(pr.A, pr.flag, 1, measure="all"))


def test_max_controls_threshold():
    c7 = QuantumCircuit(9)
    c7.mcx(list(range(7)), 7)
    c8 = QuantumCircuit(9)
    c8.mcx(list(range(8)), 8)
    assert max_controls(c7) == 7
    assert max_controls(c8) == 8
    assert max_controls(QuantumCircuit(3)) == 0
    for c in (c7, c8):
        with pytest.raises(ValueError, match="mcx"):
            check_ionq_safe(c)
    with pytest.raises(ValueError, match="8 controls"):
        check_ionq_safe(c8)


def test_qubit_budget_boundary():
    assert transpile_once(QuantumCircuit(24)).num_qubits == 24
    with pytest.raises(ValueError, match="24"):
        transpile_once(QuantumCircuit(25))
    with pytest.raises(ValueError, match="24"):
        check_ionq_safe(QuantumCircuit(25))


def test_power_circuit_validation(problems):
    pr = problems["Q1"]
    for bad in (-1, 1.5, True):
        with pytest.raises(ValueError):
            power_circuit(pr.A, pr.flag, bad)
    with pytest.raises(ValueError):
        power_circuit(pr.A, pr.flag, 1, measure="bogus")
    c0 = power_circuit(pr.A, pr.flag, 0, measure="none")
    assert c0 is not pr.A and c0.name == "AQ0"
    assert [i.operation.name for i in c0.data] == [i.operation.name for i in pr.A.data]
    assert c0.num_clbits == 0
    cf = power_circuit(pr.A, pr.flag, 0, measure="flag")
    assert cf.num_clbits == 1 and [r.name for r in cf.cregs] == ["flag"]
    ca = power_circuit(pr.A, pr.flag, 0, measure="all")
    assert ca.num_clbits == pr.qubits and [r.name for r in ca.cregs] == ["meas"]
    assert "barrier" not in ca.count_ops()
    meas = [(ca.find_bit(i.qubits[0]).index, ca.find_bit(i.clbits[0]).index)
            for i in ca.data if i.operation.name == "measure"]
    assert meas == [(q, q) for q in range(pr.qubits)]


def test_resource_table_values():
    rows = resource_table()
    got = [(r["model"], r["k"], r["qubits"], r["cx"], r["depth"], r["size"], r["max_controls"]) for r in rows]
    assert got == RESOURCE_ROWS
    assert all(r["qubits"] <= 24 for r in rows)
    assert resource_table() == rows
    pr = make_problem("Q1")
    c7 = transpile_once(power_circuit(pr.A, pr.flag, 2, measure="none"), seed=7)
    assert c7.count_ops()["cx"] == 2693 and c7.depth() == 4546
    text = format_resource_table(rows)
    assert "| Q1 | A·Q^1 | 12 | 1503 | 2532 | 3001 | 1 |" in text.splitlines()
    assert text.splitlines()[0] == "| Model | Circuit | Qubits | CX | Depth | Size | Max controls |"
