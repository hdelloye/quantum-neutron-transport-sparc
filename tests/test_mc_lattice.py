"""Matched lattice MC (PHYS-07, PHYS-08 lattice half): tracer, distributions, hooks, edges.

The lattice engine samples the frozen Kernels tables register by register, so its
bit-string distribution must equal ``exact.bitstring_probabilities_k1``, its exit rows
``exact.exit_row_distribution_k1`` and its mean the exact T1. Validation compares sums
only (PD-11): fixed seeds, |z| < 4, chi2 < dof + 5 sqrt(2 dof).
"""
import ast
import math
from pathlib import Path

import numpy as np
import pytest

from neutron_qae.exact import (
    N_BITS,
    bitstring_probabilities_k1,
    exit_row_distribution_k1,
    transmission_within,
)
from neutron_qae.kernels import build_kernels
from neutron_qae.mc_lattice import LatticeResult, run_lattice
from neutron_qae.problem import sparc_first_wall
from random_doubles import HashCounterSource, ScriptedSource, foreign_imports, rng_violations

ENGINE = Path(__file__).resolve().parents[1] / "neutron_qae" / "mc_lattice.py"

SPEC = sparc_first_wall()
K = build_kernels(SPEC)
T1 = transmission_within(K, 1)
Z = 4.0
ROW_CHI2_BOUND = 16 + 5 * math.sqrt(32)        # 44.28 for the 16 exit rows


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


# --- Task 2: distributions equal the enumeration, swapped source, gates, validation ---

def test_bitstring_distribution_matches_enumeration():
    n = 4 * 10**6
    r = run_lattice(K, n, np.random.default_rng(3), return_bitstrings=True)
    P = np.zeros(2 ** N_BITS)
    for s, p, _ in bitstring_probabilities_k1(K):
        P[s] = p
    counts = np.bincount(r.bitstrings, minlength=2 ** N_BITS)
    support = P > 0
    assert int(support.sum()) == 728
    assert int(counts[~support].sum()) == 0
    dof = int(support.sum()) - 1
    expected = n * P[support]
    chi2 = float(np.sum((counts[support] - expected) ** 2 / expected))
    assert chi2 < dof + 5 * math.sqrt(2 * dof), chi2


def test_exit_rows_match_exact_distribution():
    n = 10**6
    r = run_lattice(K, n, np.random.default_rng(4))
    expected = n * exit_row_distribution_k1(K)
    chi2 = float(np.sum((r.row_counts - expected) ** 2 / expected))
    assert chi2 < ROW_CHI2_BOUND, chi2
    assert int(r.row_counts.sum()) == r.transmitted


def test_rmse_tracks_one_over_sqrt_n():
    children = np.random.SeedSequence(2026).spawn(200)
    for n, kids in ((1000, children[:100]), (10_000, children[100:])):
        est = np.array([run_lattice(K, n, np.random.default_rng(c)).mean for c in kids])
        rmse = float(np.sqrt(np.mean((est - T1) ** 2)))
        assert abs(rmse / math.sqrt(T1 * (1 - T1) / n) - 1) < 0.3, (n, rmse)


def test_swap_source_without_engine_change():
    h = HashCounterSource(b"x")
    n = 200_000
    r = run_lattice(K, n, h, return_bitstrings=True)
    assert abs((r.mean - T1) / r.se) < Z
    x, a, _, e = _decode(r.bitstrings)
    escaped = int(((x < 16) & (a == 1) & (e == 1)).sum())
    assert h.drawn == 4 * n + escaped          # one flight per history (WR-08)
    assert h.drawn == 802_076


FORBIDDEN_NAMES = {"sigma_t", "sigma_s", "tau_x", "material_at", "column_segments", "build_kernels",
                   "bitstring_probabilities_k1", "transmission_within"}
LAYOUT_NAMES = {"X_BITS", "A_BITS", "PHI_BITS", "E_BITS", "N_BITS"}


def test_lattice_static_gates():
    assert rng_violations(ENGINE) == []
    assert foreign_imports(ENGINE) == set()
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    from_exact = set()
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "neutron_qae.exact":
            from_exact |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            used |= {alias.name for alias in node.names}
        elif isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    assert from_exact and from_exact <= LAYOUT_NAMES, from_exact
    assert not used & FORBIDDEN_NAMES, used & FORBIDDEN_NAMES


def test_same_seed_reproduces_bitstrings():
    a = run_lattice(K, 50_000, np.random.default_rng(5), return_bitstrings=True)
    b = run_lattice(K, 50_000, np.random.default_rng(5), return_bitstrings=True)
    assert np.array_equal(a.bitstrings, b.bitstrings)
    c = run_lattice(K, 50_000, np.random.default_rng(5), return_bitstrings=True, chunk=10_000)
    assert not np.array_equal(a.bitstrings, c.bitstrings)     # draw order depends on chunk (PD-12)
    assert abs((c.mean - T1) / c.se) < Z


def test_unseeded_default_source_runs():
    r = run_lattice(K, 1000)
    assert r.n == 1000 and 0 <= r.transmitted <= 1000


class _OneSource:
    def random(self, size):
        return np.ones(size)


@pytest.mark.parametrize("kwargs, exc", [
    (dict(n=0), ValueError),
    (dict(n=-1), ValueError),
    (dict(n=1.5), ValueError),
    (dict(n=True), ValueError),
    (dict(chunk=0), ValueError),
    (dict(chunk=True), ValueError),
    (dict(k="k"), TypeError),
    (dict(source=object()), TypeError),
    (dict(source=_OneSource()), ValueError),
])
def test_lattice_input_validation(kwargs, exc):
    args = dict(k=K, n=10, source=np.random.default_rng(0), chunk=1 << 16)
    args.update(kwargs)
    with pytest.raises(exc):
        run_lattice(args["k"], args["n"], args["source"], chunk=args["chunk"])


def test_wrong_layout_raises():
    k8 = build_kernels(sparc_first_wall(nx=8))
    with pytest.raises(ValueError, match="11-bit register layout"):
        run_lattice(k8, 10)
