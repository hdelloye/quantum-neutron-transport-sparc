"""Quantum oracle A (QC-01..QC-03): contract gate, layout, support, invertibility, Aer, edges."""
from __future__ import annotations

from neutron_qae.exact import transmission_within
from neutron_qae.kernels import build_kernels
from neutron_qae.oracle import make_problem
from neutron_qae.problem import sparc_first_wall

K = build_kernels(sparc_first_wall())
T0 = transmission_within(K, 0)
T1 = transmission_within(K, 1)


def test_q1_flag_probability_equals_exact_T1():
    pr = make_problem("Q1")
    assert pr.qubits == 12 and pr.A.num_qubits == 12
    assert pr.flag == 11 and pr.K == 1 and pr.model == "Q1"
    assert pr.reference == T1
    assert abs(pr.p - T1) <= 1e-12
