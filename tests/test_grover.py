"""Grover powers A·Q^k (QC-04..QC-06): sin^2 sweep, transpile-once safety, budget, resource table."""
from __future__ import annotations

import math

from qiskit.quantum_info import Statevector

from neutron_qae.exact import transmission_within
from neutron_qae.grover import max_controls, power_circuit, transpile_once
from neutron_qae.kernels import build_kernels
from neutron_qae.oracle import make_problem
from neutron_qae.problem import sparc_first_wall

K = build_kernels(sparc_first_wall())
T0 = transmission_within(K, 0)
T1 = transmission_within(K, 1)
SWEEP_TOL = 1e-11


def _p_flag(tc, flag):
    return float(Statevector(tc).probabilities([flag])[1])


def test_a_q1_transpiled_once_amplifies_flag():
    pr = make_problem("Q1")
    k = 1
    tc = transpile_once(power_circuit(pr.A, pr.flag, k, measure="none"))
    theta = math.asin(math.sqrt(T1))
    assert abs(_p_flag(tc, pr.flag) - math.sin((2 * k + 1) * theta) ** 2) <= SWEEP_TOL
    assert max_controls(tc) <= 7
