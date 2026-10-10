"""Exact lattice solver (PHYS-06): tracer reference values and K = 0 / K = 1 edge tests."""
import math

import numpy as np
import pytest

from neutron_qae.exact import (
    N_BITS,
    REGISTER_LAYOUT,
    bitstring_probabilities_k1,
    exit_row_distribution_k1,
    transmission_within,
)
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


# --- PHYS-06 edges -------------------------------------------------------------------------


def _decode(s):
    return s & 31, (s >> 5) & 1, (s >> 6) & 15, (s >> 10) & 1


def test_bit_layout_little_endian_and_ordered():
    assert N_BITS == 11
    assert "x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10" in REGISTER_LAYOUT
    entries = bitstring_probabilities_k1(K)
    ss = [s for s, _, _ in entries]
    assert all(b > a for a, b in zip(ss, ss[1:]))
    assert set(ss) == {s for s in range(2048) if s & 31 <= 16}
    for s, _, t in entries:
        x, a, _, e = _decode(s)
        assert t == (x == 16 or (a == 1 and e == 1))


def test_uncollided_mirrors_column_0():
    unc = [(s, p, t) for s, p, t in bitstring_probabilities_k1(K) if _decode(s)[0] == 16]
    total = math.fsum(p for _, p, _ in unc)
    assert abs(total - K.first_collision[16]) < 1e-16
    a1 = math.fsum(p for s, p, _ in unc if _decode(s)[1] == 1)
    assert a1 / total == pytest.approx(K.scatter_ratio[0], rel=1e-12)
    assert all(t for _, _, t in unc)


@pytest.mark.parametrize("bad_k", [-1, 2, 3, 1.5])
def test_K_outside_contract_v1_is_rejected(bad_k):
    with pytest.raises(ValueError, match="contract v1"):
        transmission_within(K, bad_k)


@pytest.mark.parametrize("overrides", [{"nx": 8}, {"n_dir": 8}])
def test_register_layout_requires_16_columns_and_bins(overrides):
    k = build_kernels(sparc_first_wall(**overrides))
    with pytest.raises(ValueError):
        transmission_within(k, 1)
    assert isinstance(transmission_within(k, 0), float)


def test_fsum_is_order_independent():
    trans = [p for _, p, t in bitstring_probabilities_k1(K) if t]
    assert math.fsum(reversed(trans)) == transmission_within(K, 1)


def test_exit_row_distribution_k1():
    rows = exit_row_distribution_k1(K)
    assert rows.shape == (16,) and rows.dtype == np.float64
    assert abs(rows.sum() - transmission_within(K, 1)) < 1e-13
    scattered = rows.copy()
    scattered[8] -= K.first_collision[16]
    assert np.abs(scattered - scattered[::-1]).max() < 1e-14
