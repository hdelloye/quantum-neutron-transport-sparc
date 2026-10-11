"""Matched lattice MC (PHYS-07, PHYS-08 lattice half): tracer, distributions, hooks, edges.

The lattice engine samples the frozen Kernels tables register by register, so its
bit-string distribution must equal ``exact.bitstring_probabilities_k1``, its exit rows
``exact.exit_row_distribution_k1`` and its mean the exact T1. Validation compares sums
only (PD-11): fixed seeds, |z| < 4, chi2 < dof + 5 sqrt(2 dof).
"""
import numpy as np
import pytest

from neutron_qae.exact import N_BITS, transmission_within
from neutron_qae.kernels import build_kernels
from neutron_qae.mc_lattice import LatticeResult, run_lattice
from neutron_qae.problem import sparc_first_wall
from random_doubles import ScriptedSource

SPEC = sparc_first_wall()
K = build_kernels(SPEC)
T1 = transmission_within(K, 1)
Z = 4.0


def _decode(s):
    s = np.asarray(s, dtype=np.int64)
    return s & 31, (s >> 5) & 1, (s >> 6) & 15, (s >> 10) & 1


@pytest.mark.parametrize("n", [10**3, 10**4, 10**5, 10**6])
def test_lattice_converges_to_exact_T1(n):
    r = run_lattice(K, n, np.random.default_rng(2026))
    assert abs((r.mean - T1) / r.se) < Z


def test_scripted_uncollided_history():
    src = ScriptedSource([0.99, 0.5, 0.5, 0.5])
    r = run_lattice(K, 1, src, return_bitstrings=True)
    assert r.transmitted == 1
    assert r.row_counts[8] == 1 and r.row_counts.sum() == 1
    assert int(r.bitstrings[0]) == 528           # x = 16, a = 0, phi = 8, e = 0
    assert src.pos == 4


def test_bitstring_layout_matches_exact():
    r = run_lattice(K, 100_000, np.random.default_rng(7), return_bitstrings=True)
    s = r.bitstrings
    assert s.shape == (100_000,)
    assert s.min() >= 0 and s.max() < 2 ** N_BITS
    x, a, phi, e = _decode(s)
    assert x.max() <= 16
    t = (x == 16) | ((a == 1) & (e == 1))
    assert int(t.sum()) == r.transmitted


def test_result_carries_se_and_cost():
    n = 50_000
    r = run_lattice(K, n, np.random.default_rng(11), return_bitstrings=True)
    assert isinstance(r, LatticeResult)
    p = r.transmitted / n
    assert r.se == pytest.approx(np.sqrt(p * (1 - p) / n), rel=1e-12)
    assert r.mean == pytest.approx(p, rel=1e-15)
    assert r.cost == n
    assert int(r.row_counts.sum()) == r.transmitted
    assert r.row_counts.dtype == np.int64 and r.checkpoint_counts.dtype == np.int64
    for arr in (r.row_counts, r.checkpoint_counts, r.bitstrings):
        assert not arr.flags.writeable
    np.testing.assert_allclose(r.row_fractions, r.row_counts / n, rtol=1e-15)
    np.testing.assert_allclose(r.row_se, np.sqrt(r.row_fractions * (1 - r.row_fractions) / n), rtol=1e-12)
    assert r.chunk == 1 << 16 and r.checkpoints == ()
