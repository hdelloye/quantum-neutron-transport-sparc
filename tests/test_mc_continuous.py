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
from random_doubles import HashCounterSource, ScriptedSource

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


def test_swap_source_without_engine_change():
    h = HashCounterSource()
    r = run_continuous(SPEC, 200_000, h)
    assert abs(_z(r.within(1), T1)) < Z
    assert h.drawn == 445_741          # pins the documented per-iteration draw order


def test_unseeded_default_source_runs():
    r = run_continuous(SPEC, 1000)
    assert r.fate_counts.sum() == 1000


X_FIRST_SCRIPTED = -math.log1p(-0.1) / SPEC.front.sigma_t   # 0.615 cm, inside WHA


@pytest.mark.parametrize("values, fate, ncol, yexit, consumed", [
    ([0.95], BACK, 0, 5.0, 1),                          # never collides, exits on the beam line
    ([0.10, 0.01, 0.0, 0.95], BACK, 1, 5.0, 4),         # scatter phi = 0, back exit on the beam line
    ([0.10, 0.01, 0.25, 0.95], LATERAL, 1, None, 4),    # phi = pi/2, leaves through the top face
    ([0.10, 0.01, 0.5, 0.95], FRONT, 1, None, 4),       # phi = pi, back out through the plasma face
    ([0.10, 0.5, 0.95], ABSORBED, 1, None, 2),          # absorbed: no direction uniform drawn
], ids=["uncollided", "scatter-forward", "lateral", "front", "absorbed"])
def test_scripted_histories(values, fate, ncol, yexit, consumed):
    src = ScriptedSource(values)
    r, h = run_continuous(SPEC, 1, src, histories=True)
    assert src.pos == consumed
    assert h.fate.tolist() == [fate] and h.ncol.tolist() == [ncol]
    assert r.fate_counts[fate] == 1 and r.fate_counts.sum() == 1
    if yexit is None:
        assert math.isnan(h.yexit[0])
    else:
        assert h.yexit[0] == yexit
    if ncol == 0:
        assert math.isnan(h.x_first[0])
        assert r.row_counts[8] == 1 and r.row_counts_le1[8] == 1
    else:
        assert abs(h.x_first[0] - X_FIRST_SCRIPTED) <= 1e-12
    if fate in (LATERAL, FRONT, ABSORBED):
        assert r.row_counts.sum() == 0 and r.row_counts_le1.sum() == 0


def test_bad_source_output_raises():
    class Ones:
        def random(self, size):
            return np.ones(size)

    class NaNs:
        def random(self, size):
            return np.full(size, np.nan)

    for src in (Ones(), NaNs()):
        with pytest.raises(ValueError):
            run_continuous(SPEC, 10, src)
    with pytest.raises(TypeError):
        run_continuous(SPEC, 10, object())
