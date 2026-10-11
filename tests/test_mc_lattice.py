"""Matched lattice MC (PHYS-07, PHYS-08 lattice half): tracer, distributions, hooks, edges.

The lattice engine samples the frozen Kernels tables register by register, so its
bit-string distribution must equal ``exact.bitstring_probabilities_k1``, its exit rows
``exact.exit_row_distribution_k1`` and its mean the exact T1. Validation compares sums
only (PD-11): fixed seeds, |z| < 4, chi2 < dof + 5 sqrt(2 dof).
"""
import ast
import math
import os
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
import neutron_qae.mc_lattice as mc_lattice
from neutron_qae.mc_lattice import LatticeResult, run_lattice, sample_exit_rows
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


# --- Task 3: Phase 5 hooks (checkpoints, shared row sampler, cost) and edges ---

def test_checkpoints_are_prefix_counts():
    n = 10_000
    r = run_lattice(K, n, np.random.default_rng(9), chunk=4096, return_bitstrings=True,
                    checkpoints=(10_000, 1, 2500, 2500))
    assert r.checkpoints == (1, 2500, 10_000)
    x, a, _, e = _decode(r.bitstrings)
    ct = np.cumsum((x == 16) | ((a == 1) & (e == 1)))
    expected = ct[[0, 2499, 9999]]
    assert np.array_equal(r.checkpoint_counts, expected)
    assert list(r.checkpoint_counts) == [1, 584, 2429]
    assert int(r.checkpoint_counts[-1]) == r.transmitted
    Ns, means, ses = r.prefix_estimates()
    assert list(Ns) == [1, 2500, 10_000]
    np.testing.assert_allclose(means, expected / Ns, rtol=1e-15)
    np.testing.assert_allclose(ses, np.sqrt(means * (1 - means) / Ns), rtol=1e-15)


@pytest.mark.parametrize("cps", [(0,), (10_001,), (1.5,), (True,)])
def test_checkpoint_validation(cps):
    with pytest.raises(ValueError):
        run_lattice(K, 10_000, np.random.default_rng(0), checkpoints=cps)


def test_empty_checkpoints():
    r = run_lattice(K, 1000, np.random.default_rng(0), checkpoints=())
    assert r.checkpoints == () and r.checkpoint_counts.shape == (0,)
    Ns, means, ses = r.prefix_estimates()
    assert Ns.size == means.size == ses.size == 0


S_UNC = 16 | (8 << 6)                              # x = 16, uncollided -> row 8
S_ABSORBED = 3                                     # x = 3, a = 0
S_BACKWARD = 0 | (1 << 5) | (8 << 6) | (0 << 10)   # scattered, flight did not reach the back face
S_OUT = 20                                         # x = 20: zero amplitude in the ideal circuit
S_ESCAPED = 0 | (1 << 5) | (0 << 6) | (1 << 10)    # 1056: column 0, phi bin 0, escaped


def test_sample_exit_rows_contract():
    src = ScriptedSource([])
    rows = sample_exit_rows(K, [S_UNC, S_ABSORBED, S_BACKWARD, S_OUT], src)
    assert rows.dtype == np.int64 and list(rows) == [8, -1, -1, -1]
    assert src.pos == 0
    empty = sample_exit_rows(K, [], ScriptedSource([]))
    assert empty.dtype == np.int64 and empty.shape == (0,)


@pytest.mark.parametrize("bad", [[-1], [2048], [1.5], [[1056]], [True]])
def test_sample_exit_rows_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        sample_exit_rows(K, bad, np.random.default_rng(0))


def test_sample_exit_rows_wrong_kernels():
    with pytest.raises(TypeError):
        sample_exit_rows("k", [S_UNC])
    with pytest.raises(ValueError, match="11-bit register layout"):
        sample_exit_rows(build_kernels(sparc_first_wall(nx=8)), [S_UNC])


def test_sample_exit_rows_row_edges():
    pos = np.nonzero(K.back_exit_rows[0, 0])[0]
    assert (pos.min(), pos.max()) == (8, 14)
    assert list(sample_exit_rows(K, [S_ESCAPED], ScriptedSource([0.0]))) == [pos.min()]
    assert list(sample_exit_rows(K, [S_ESCAPED], ScriptedSource([np.nextafter(1.0, 0.0)]))) == [pos.max()]
    src = ScriptedSource([np.nextafter(1.0, 0.0), 0.0])
    assert list(sample_exit_rows(K, [S_ESCAPED, S_ESCAPED], src)) == [14, 8]
    assert src.pos == 2


def test_sample_exit_rows_never_zero_mass():
    tot = K.back_exit_rows.sum(axis=-1)
    col, phi = np.meshgrid(np.arange(16), np.arange(16), indexing="ij")
    s = (col | (1 << 5) | (phi << 6) | (1 << 10)).ravel()
    s = np.repeat(s, 50)
    rows = sample_exit_rows(K, s, np.random.default_rng(21))
    c, p = s & 31, (s >> 6) & 15
    live = tot[c, p] > 0
    assert int((~live).sum()) == 168 * 50
    assert np.all(rows[~live] == -1)               # zero-amplitude strings from noisy counts
    assert np.all((rows[live] >= 0) & (rows[live] < 16))
    assert np.all(K.back_exit_rows[c[live], p[live], rows[live]] > 0)


def test_run_lattice_uses_shared_row_sampler(monkeypatch):
    calls = []
    original = mc_lattice.sample_exit_rows

    def spy(k, bitstrings, source=None):
        out = original(k, bitstrings, source)
        calls.append((len(bitstrings), out.shape))
        return out

    monkeypatch.setattr(mc_lattice, "sample_exit_rows", spy)
    r = mc_lattice.run_lattice(K, 1000, np.random.default_rng(1))
    assert len(calls) >= 1 and calls[0] == (1000, (1000,))
    assert int(r.row_counts.sum()) == r.transmitted


def test_cost_is_histories():
    assert run_lattice(K, 12_345, np.random.default_rng(2)).cost == 12_345


@pytest.mark.parametrize("width", [6.0, 15.0, 20.0])
def test_other_wall_thicknesses_match_exact(width):
    k = build_kernels(sparc_first_wall(width_x=width))
    t1 = transmission_within(k, 1)
    r = run_lattice(k, 10**6, np.random.default_rng(32))
    assert abs((r.mean - t1) / r.se) < Z


@pytest.mark.parametrize("n, chunk", [(100_003, 1 << 16), (3, 1)])
def test_partial_chunks_lattice(n, chunk):
    r = run_lattice(K, n, np.random.default_rng(6), chunk=chunk)
    assert r.n == n and int(r.row_counts.sum()) == r.transmitted


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("NEUTRON_QAE_SLOW") != "1",
                    reason="1e8-history check; run with NEUTRON_QAE_SLOW=1 -m slow")
def test_slow_1e8_lattice():
    n = 10**8
    r = run_lattice(K, n, np.random.default_rng(12))
    assert abs((r.mean - T1) / r.se) < Z
    expected = n * exit_row_distribution_k1(K)
    chi2 = float(np.sum((r.row_counts - expected) ** 2 / expected))
    print(f"lattice 1e8: mean={r.mean:.7f} z={(r.mean - T1) / r.se:+.2f} row_chi2={chi2:.1f}")
    assert chi2 < ROW_CHI2_BOUND, chi2
