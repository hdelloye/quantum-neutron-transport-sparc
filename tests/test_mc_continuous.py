"""Continuous delta-tracking MC (PHYS-03/04): tracer, tallies, reproducibility, edges.

Validation compares sums only (PD-11, WR-07): within(0) with e^{-tau}, within(1) with the
exact T1, the at-most-one-collision row histogram and the first-collision column
histogram. The full (all-order) transmission is never compared with T1, and no individual
Kernels table entry is compared with continuous output. Fixed seeds, |z| < 4.
"""
import math

import numpy as np
import pytest

from neutron_qae.exact import transmission_within
from neutron_qae.kernels import build_kernels
from neutron_qae.mc_continuous import (
    ABSORBED,
    BACK,
    FRONT,
    LATERAL,
    ContinuousHistories,
    ContinuousResult,
    run_continuous,
)
from neutron_qae.problem import sparc_first_wall

SPEC = sparc_first_wall()
K = build_kernels(SPEC)
T1 = transmission_within(K, 1)
T0 = float(K.first_collision[-1])
Z = 4.0


@pytest.fixture(scope="module")
def tracer_run():
    return run_continuous(SPEC, 10**6, np.random.default_rng(2026))


def _z(p_se, ref):
    p, se = p_se
    return (p - ref) / se


def test_uncollided_matches_exp_minus_tau(tracer_run):
    exp_tau = math.exp(-float(SPEC.tau_x(SPEC.width_x)))
    assert abs(exp_tau - T0) <= 1e-15
    assert abs(_z(tracer_run.within(0), exp_tau)) < Z


def test_le1_transmission_matches_exact_T1(tracer_run):
    assert abs(_z(tracer_run.within(1), T1)) < Z


def test_same_seed_reproduces_histories():
    _, ha = run_continuous(SPEC, 50_000, np.random.default_rng(5), histories=True)
    _, hb = run_continuous(SPEC, 50_000, np.random.default_rng(5), histories=True)
    _, hc = run_continuous(SPEC, 50_000, 5, histories=True)
    assert isinstance(ha, ContinuousHistories)
    for name in ContinuousHistories._fields:
        a, b, c = getattr(ha, name), getattr(hb, name), getattr(hc, name)
        assert a.shape == (50_000,)
        assert np.array_equal(a, b, equal_nan=True), name
        assert np.array_equal(a, c, equal_nan=True), name


def test_tallies_and_standard_errors(tracer_run):
    r = tracer_run
    n = r.n
    assert isinstance(r, ContinuousResult) and n == 10**6
    assert r.fate_counts.shape == (4,) and r.fate_counts.sum() == n
    assert r.order_counts.shape == (r.max_order + 2,) and r.max_order == 8
    assert r.order_counts.sum() == r.fate_counts[BACK]
    assert r.row_counts.shape == (SPEC.ny,) and r.row_counts.sum() == r.fate_counts[BACK]
    assert r.row_counts_le1.sum() == r.order_counts[0] + r.order_counts[1]
    for arr in (r.fate_counts, r.order_counts, r.row_counts, r.row_counts_le1):
        assert arr.dtype == np.int64 and not arr.flags.writeable

    def se(c):
        p = c / n
        return math.sqrt(p * (1 - p) / n)

    pairs = [
        ("transmission", BACK), ("absorption", ABSORBED),
        ("reflection", FRONT), ("leakage_lateral", LATERAL),
    ]
    for name, f in pairs:
        p = getattr(r, name)
        assert p == r.fate_counts[f] / n
        assert getattr(r, name + "_se") == pytest.approx(se(int(r.fate_counts[f])), rel=1e-12)
        assert getattr(r, name + "_se") > 0
    assert sum(getattr(r, name) for name, _ in pairs) == pytest.approx(1.0, abs=1e-12)
    np.testing.assert_allclose(r.order_fractions, r.order_counts / n, rtol=1e-12)
    np.testing.assert_allclose(r.order_se, [se(int(c)) for c in r.order_counts], rtol=1e-12)
    for le1, counts in ((False, r.row_counts), (True, r.row_counts_le1)):
        np.testing.assert_allclose(r.row_fractions(le1), counts / n, rtol=1e-12)
        np.testing.assert_allclose(r.row_se(le1), [se(int(c)) for c in counts], rtol=1e-12)
    for k in range(r.max_order + 1):
        p, s = r.within(k)
        c = int(r.order_counts[:k + 1].sum())
        assert p == c / n and s == pytest.approx(se(c), rel=1e-12)
    assert r.chunk == 1 << 16 and r.iterations >= 1
