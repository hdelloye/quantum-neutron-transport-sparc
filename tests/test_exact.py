"""Exact lattice solver (PHYS-06): tracer reference values and K = 0 / K = 1 edge tests."""
import math

import numpy as np
import pytest

from neutron_qae.exact import bitstring_probabilities_k1, transmission_within
from neutron_qae.kernels import BACK, build_kernels
from neutron_qae.problem import sparc_first_wall

SPEC = sparc_first_wall()
K = build_kernels(SPEC)

T0_REF = 0.23256718303628812
T1_REF = 0.24300446519524305


def test_reference_values_match_research():
    assert transmission_within(K, 0) == pytest.approx(T0_REF, rel=1e-9)
    assert transmission_within(K, 1) == pytest.approx(T1_REF, rel=1e-9)
    assert float(SPEC.tau_x(10.0)) == pytest.approx(1.4585761363995597, rel=1e-12)
    assert K.scatter_ratio[3] == pytest.approx(0.11850355190070459, rel=1e-9)


def test_T0_is_exp_minus_model_tau():
    assert transmission_within(K, 0) == pytest.approx(math.exp(-SPEC.tau_x(10.0)), rel=1e-14)


def test_T1_equals_closed_form():
    closed = K.first_collision[-1] + float(np.sum(K.first_collision[:-1] * K.scatter_ratio * K.flight[:, :, BACK].mean(1)))
    assert transmission_within(K, 1) == pytest.approx(closed, rel=1e-14)


def test_enumeration_conserves_probability():
    entries = bitstring_probabilities_k1(K)
    assert len(entries) == 1088
    assert math.fsum(p for _, p, _ in entries) == pytest.approx(1.0, abs=1e-14)


def test_isotropic_raw_reference():
    k = build_kernels(sparc_first_wall("isotropic_raw"))
    assert transmission_within(k, 0) == pytest.approx(0.08674615049972412, rel=1e-9)
    assert transmission_within(k, 1) == pytest.approx(0.11006367028977174, rel=1e-9)
