"""Continuous delta-tracking MC (PHYS-03/04): tracer, tallies, reproducibility, edges.

Validation compares sums only (PD-11, WR-07): within(0) with e^{-tau}, within(1) with the
exact T1, the at-most-one-collision row histogram and the first-collision column
histogram. The full (all-order) transmission is never compared with T1, and no individual
Kernels table entry is compared with continuous output. Fixed seeds, |z| < 4.
"""
import math
import os

import numpy as np
import pytest

from neutron_qae.exact import exit_row_distribution_k1, transmission_within
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
from neutron_qae.problem import Material, ProblemSpec, sparc_first_wall
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


def _chi2(counts, expected):
    counts = np.asarray(counts, dtype=np.float64)
    return float(np.sum((counts - expected) ** 2 / expected))


def _chi2_bound(dof):
    return dof + 5 * math.sqrt(2 * dof)


def test_pure_absorber_two_layer():
    spec = ProblemSpec(front=Material("A", SPEC.front.sigma_t, 0.0), back=Material("B", SPEC.back.sigma_t, 0.0))
    r = run_continuous(spec, 400_000, np.random.default_rng(1))
    ref = math.exp(-float(spec.tau_x(10.0)))
    assert abs((r.transmission - ref) / r.transmission_se) < Z
    assert r.fate_counts[FRONT] == 0 and r.fate_counts[LATERAL] == 0
    assert r.reflection_se == 0.0 and r.leakage_lateral_se == 0.0    # zero count -> SE exactly 0
    assert r.fate_counts.sum() == 400_000


def test_pure_scatterer_conserves():
    spec = ProblemSpec(front=Material("A", SPEC.front.sigma_t, SPEC.front.sigma_t),
                       back=Material("B", SPEC.back.sigma_t, SPEC.back.sigma_t))
    r = run_continuous(spec, 200_000, np.random.default_rng(1))
    assert r.fate_counts[ABSORBED] == 0 and r.absorption_se == 0.0
    assert r.fate_counts.sum() == 200_000
    assert r.iterations <= 100


def test_isotropic_raw_matches_exact():
    raw = sparc_first_wall("isotropic_raw")
    kr = build_kernels(raw)
    r = run_continuous(raw, 10**6, np.random.default_rng(2))
    assert abs(_z(r.within(1), transmission_within(kr, 1))) < Z
    assert abs(_z(r.within(0), float(kr.first_collision[-1]))) < Z


@pytest.mark.parametrize("width", [6.0, 15.0, 20.0])
def test_other_wall_thicknesses_match_exact(width):
    spec = sparc_first_wall(width_x=width)
    kw = build_kernels(spec)
    r = run_continuous(spec, 10**6, np.random.default_rng(31))
    assert abs(_z(r.within(0), float(kw.first_collision[-1]))) < Z
    assert abs(_z(r.within(1), transmission_within(kw, 1))) < Z


@pytest.fixture(scope="module")
def marginal_run():
    return run_continuous(SPEC, 10**6, np.random.default_rng(99), histories=True)


def test_marginal_sums_match_kernels(marginal_run):
    # Sums only (WR-07): individual flight / back_exit_rows entries carry up to a few percent
    # relative quadrature error, so per-entry and per-row z comparisons are out of scope.
    r, h = marginal_run
    n = r.n
    assert _chi2(r.row_counts_le1, n * exit_row_distribution_k1(K)) < _chi2_bound(16)
    col = np.where(np.isnan(h.x_first), SPEC.nx,
                   np.minimum(np.floor(np.nan_to_num(h.x_first) / SPEC.dx).astype(int), SPEC.nx - 1))
    cols = np.bincount(col, minlength=SPEC.nx + 1)
    assert cols.shape == (17,)
    assert _chi2(cols, n * K.first_collision) < _chi2_bound(17)


def test_rows_come_from_spec_row_of(marginal_run):
    r, h = marginal_run
    back = h.fate == BACK
    y = h.yexit[back]
    assert np.all((y >= 0.0) & (y <= 10.0))
    assert np.all(np.isnan(h.yexit[~back]))
    assert np.array_equal(r.row_counts, np.bincount(SPEC.row_of(y), minlength=16))
    assert np.array_equal(r.row_counts_le1, np.bincount(SPEC.row_of(y[h.ncol[back] <= 1]), minlength=16))
    assert SPEC.row_of(np.array([0.0, 10.0])).tolist() == [0, 15]


@pytest.mark.parametrize("n, chunk", [(100_003, 1 << 16), (1, 1 << 16), (3, 1), (1000, 10**7)])
def test_partial_chunks(n, chunk):
    r = run_continuous(SPEC, n, np.random.default_rng(3), chunk=chunk)
    assert r.fate_counts.sum() == n and r.chunk == chunk


def test_chunk_size_changes_histories_not_statistics():
    # PD-12: the vectorized draw order depends on the chunk, so same seed + different chunk
    # gives different (equally valid) histories. This is the stated non-guarantee.
    ra, ha = run_continuous(SPEC, 50_000, np.random.default_rng(5), histories=True)
    rb, hb = run_continuous(SPEC, 50_000, np.random.default_rng(5), histories=True, chunk=10_000)
    assert not all(np.array_equal(a, b, equal_nan=True) for a, b in zip(ha, hb))
    assert abs(_z(ra.within(1), T1)) < Z and abs(_z(rb.within(1), T1)) < Z


def test_max_order_zero(tracer_run):
    r = run_continuous(SPEC, 1000, np.random.default_rng(0), max_order=0)
    assert r.order_counts.shape == (2,) and r.max_order == 0
    assert r.order_counts.sum() == r.fate_counts[BACK]
    r.within(0)
    with pytest.raises(ValueError):
        r.within(1)
    for bad in (-1, True, 1.0, 9):
        with pytest.raises(ValueError):
            tracer_run.within(bad)


def test_max_iter_guard():
    with pytest.raises(RuntimeError):
        run_continuous(SPEC, 1000, np.random.default_rng(0), max_iter=1)


@pytest.mark.parametrize("kwargs", [
    {"n": 0}, {"n": -1}, {"n": 1.5}, {"n": True}, {"n": "10"},
    {"chunk": 0}, {"chunk": -4}, {"chunk": True}, {"chunk": 2.0},
    {"max_order": -1}, {"max_order": True},
    {"max_iter": 0},
], ids=lambda kw: "-".join(f"{k}={v!r}" for k, v in kw.items()))
def test_input_validation(kwargs):
    args = {"n": 10, **kwargs}
    n = args.pop("n")
    with pytest.raises(ValueError):
        run_continuous(SPEC, n, np.random.default_rng(0), **args)


def test_non_spec_raises_type_error():
    with pytest.raises(TypeError):
        run_continuous("spec", 10)


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("NEUTRON_QAE_SLOW") != "1",
                    reason="1e8-history check; run with NEUTRON_QAE_SLOW=1 -m slow")
def test_slow_1e8_continuous():
    n = 10**8
    r = run_continuous(SPEC, n, np.random.default_rng(11))
    z1, z0 = _z(r.within(1), T1), _z(r.within(0), T0)
    chi2 = _chi2(r.row_counts_le1, n * exit_row_distribution_k1(K))
    sep = (r.transmission - T1) / r.transmission_se
    print(f"SLOW 1e8 z1={z1:+.2f} z0={z0:+.2f} row_chi2={chi2:.1f} separation={sep:.1f} SE")
    assert abs(z1) < Z and abs(z0) < Z
    assert chi2 < _chi2_bound(16)
    assert sep > 8          # K = 1 truncation bias resolved: transmission is never tested against T1
