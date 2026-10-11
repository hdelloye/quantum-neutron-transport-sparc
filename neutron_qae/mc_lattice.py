"""Matched discrete lattice Monte Carlo on the frozen Kernels v1 tables (PHYS-07).

Matched mode (PD-10)
--------------------
`run_lattice(k, n, source)` samples exactly the K = 1 model that the Q1 circuit encodes and
that ``exact.bitstring_probabilities_k1`` enumerates: per history it draws the same four
random registers, with the same conditional structure, sequentially from the frozen tables.

=========  ====  ===========================================================================
register   bits  sample
=========  ====  ===========================================================================
x          5     inverse CDF over ``first_collision`` (17 outcomes, ``cdf[-1] = 1.0`` forced,
                 clamped to nx); ``x == nx`` (16) means uncollided to the back face
a          1     ``u < scatter_ratio[x % nx]`` (1 = scatter)
phi        4     ``min(floor(n_dir * u), n_dir - 1)``, uniform over the 16 direction bins
e          1     ``u < flight[x % nx, phi, BACK]`` (1 = the flight reaches the back face)
=========  ====  ===========================================================================

``x == nx`` shares the low bits 0000 with column 0, so its a and e draws use column 0
(``col = x % nx``), exactly like ``exact.py`` and the circuit's uniformly controlled
rotations. The bit string is ``x | a << 5 | phi << 6 | e << 10`` (``exact.REGISTER_LAYOUT``,
built from ``exact.X_BITS``, ``A_BITS``, ``PHI_BITS``). Transmitted means ``x == nx`` or
``(a == 1 and e == 1)``, the predicate of the enumeration.

Sequential, not categorical: a categorical draw over the 2^11 enumerated probabilities
would be the exact solver in disguise and make convergence a tautology. This engine imports
only the register-layout constants from ``exact.py`` and reads only ``first_collision``,
``scatter_ratio``, ``flight[..., BACK]`` and ``back_exit_rows`` from the Kernels, plus nx,
ny, n_dir, beam_y and ``row_of`` from the spec. It never touches a cross section, an
optical depth or the geometry.

Exit rows: an uncollided history leaves in ``spec.row_of(spec.beam_y)`` (row 8). A
scattered-and-escaped history (x < nx, a = 1, e = 1) draws one more uniform and picks its
row by inverse CDF of ``back_exit_rows[col, phi, :]`` scaled by that row's own total
(the last cumulative entry, equal to ``flight[col, phi, BACK]`` within 1.2e-15), so a
uniform below 1 can never land past the last positive-mass row; the index is also clamped
to ny - 1. The row tally goes through :func:`sample_exit_rows`, the same public helper
Phase 5 uses on Q1 measurement strings.

WR-08 caveat (one flight per history)
-------------------------------------
``flight`` and ``back_exit_rows`` are conditional on a scatter site on the beam line
y = beam_y, which holds only for the first collision of the normally incident pencil beam.
They are valid for K <= 1 only. This engine samples one flight per history and must never
chain ``flight[..., COLLIDE]`` into a second flight: once the neutron has left the beam
line, the tables no longer describe it. Each history consumes exactly four register
uniforms, plus one row uniform only when it scattered and escaped.

Draw order and reproducibility (PD-12)
--------------------------------------
Histories run in chunks of ``chunk`` (default 2^16). Per chunk of m histories the engine
draws m uniforms for x, then m for a, then m for phi, then m for e, then one row uniform
per scattered-and-escaped history in history order. Every uniform arrives through
``random_source.draw`` from the injected source. Reproducibility contract: same source
state + same ``n`` + same ``chunk`` + same numpy version and platform give identical bit
strings. A different ``chunk`` gives different, equally valid histories, because the
vectorized draw order depends on it. Checkpoints draw nothing and never change the stream.

Classical cost (PD-13)
----------------------
One lattice history is one sample of the K = 1 model: the classical counterpart of one
k = 0 application of A measured once. The classical cost is N = histories
(``LatticeResult.cost``), compared against the quantum N_A = sum over schedule of
shots * (2k + 1). It is never counted in uniforms, chunks or wall-clock time. The
expected RMSE is sqrt(T1 (1 - T1) / N) = 0.4289 / sqrt(N).

Phase 5 hooks
-------------
- ``checkpoints=(1000, 10000, ...)`` records cumulative transmitted counts at those N
  inside one run, without storing per-history flags; ``LatticeResult.prefix_estimates()``
  returns ``(Ns, means, ses)``. Prefix estimates within one run are nested and therefore
  correlated across N; for RMSE over independent repetitions, seed each repetition from
  ``np.random.SeedSequence(seed).spawn(R)``.
- ``return_bitstrings=True`` stores every 11-bit string (8 bytes per history).
- :func:`sample_exit_rows` turns bit strings (for instance Q1 counts) into exit rows with
  the engine's own code.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from neutron_qae.exact import X_BITS, A_BITS, PHI_BITS, E_BITS, N_BITS
from neutron_qae.kernels import BACK, Kernels
from neutron_qae.random_source import as_source, draw

__all__ = ["LatticeResult", "run_lattice", "sample_exit_rows"]

_A_SHIFT = X_BITS
_PHI_SHIFT = X_BITS + A_BITS
_E_SHIFT = X_BITS + A_BITS + PHI_BITS
assert _E_SHIFT + E_BITS == N_BITS


def _is_int(v) -> bool:
    return isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_))


def _check_int(name, v, minimum):
    if not _is_int(v) or v < minimum:
        raise ValueError(f"{name} must be an int >= {minimum}, got {v!r}")
    return int(v)


def _check_kernels(k):
    """TypeError unless ``k`` is a Kernels; ValueError unless it fits the 11-bit register layout."""
    if not isinstance(k, Kernels):
        raise TypeError(f"k must be a Kernels, got {type(k).__name__}")
    nx, nd = k.spec.nx, k.spec.n_dir
    if nx != 2 ** (X_BITS - 1) or nd != 2 ** PHI_BITS:
        raise ValueError(f"the 11-bit register layout needs nx == {2 ** (X_BITS - 1)} and n_dir == {2 ** PHI_BITS}; "
                         f"got nx={nx}, n_dir={nd}")


def _frac_se(count, n):
    """Fraction p = count / n and its binomial SE sqrt(p (1 - p) / n)."""
    p = np.asarray(count, dtype=np.float64) / n
    return p, np.sqrt(p * (1.0 - p) / n)


@dataclass(frozen=True, eq=False)
class LatticeResult:
    """Integer tallies of one lattice run; fractions and SEs are derived properties."""
    n: int
    transmitted: int
    row_counts: np.ndarray                # (ny,) int64 back-face exit rows of transmitted histories
    bitstrings: np.ndarray | None         # (n,) int64 11-bit strings, or None
    checkpoints: tuple                    # sorted unique N values (tuple of int)
    checkpoint_counts: np.ndarray         # int64 cumulative transmitted count at each checkpoint
    chunk: int

    def __post_init__(self):
        for name in ("row_counts", "checkpoint_counts"):
            arr = np.array(getattr(self, name), dtype=np.int64)
            arr.setflags(write=False)
            object.__setattr__(self, name, arr)
        if self.bitstrings is not None:
            arr = np.array(self.bitstrings, dtype=np.int64)
            arr.setflags(write=False)
            object.__setattr__(self, "bitstrings", arr)
        object.__setattr__(self, "checkpoints", tuple(int(c) for c in self.checkpoints))

    @property
    def mean(self) -> float:
        """Transmission estimate transmitted / n (the K = 1 transmission T1)."""
        return float(self.transmitted / self.n)

    @property
    def se(self) -> float:
        """Binomial standard error sqrt(p (1 - p) / n)."""
        return float(_frac_se(self.transmitted, self.n)[1])

    @property
    def cost(self) -> int:
        """Classical cost in histories (= n): one k = 0 application of A measured once each."""
        return self.n

    @property
    def row_fractions(self) -> np.ndarray:
        """Fraction of all n histories leaving the back face in each row."""
        return _frac_se(self.row_counts, self.n)[0]

    @property
    def row_se(self) -> np.ndarray:
        return _frac_se(self.row_counts, self.n)[1]

    def prefix_estimates(self):
        """(Ns, means, ses) at the checkpoints, as numpy arrays (empty without checkpoints).

        The prefixes are nested within one run, so the estimates are correlated across N.
        """
        Ns = np.array(self.checkpoints, dtype=np.int64)
        if Ns.size == 0:
            return Ns, np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)
        means, ses = _frac_se(self.checkpoint_counts, Ns)
        return Ns, means, ses


def sample_exit_rows(k, bitstrings, source=None) -> np.ndarray:
    """Back-face exit row (int64, same length) for each 11-bit string; -1 = no back-face exit.

    Strings follow ``exact.REGISTER_LAYOUT``: x = s & 31, a = bit 5, phi = bits 6-9,
    e = bit 10. Qiskit count keys convert with ``int(key, 2)`` because bit i is qubit i.

    - x == nx (uncollided): row ``spec.row_of(spec.beam_y)``, no uniform drawn.
    - x < nx with a == 1 and e == 1 (scattered and escaped): one uniform per such string,
      in input order, picks the row by inverse CDF of ``back_exit_rows[x, phi, :]`` scaled by
      its own total, clamped to ny - 1 (never a zero-mass row past the last positive one).
    - any other x <= nx string (absorbed, or scattered but not escaped): -1.
    - zero-amplitude strings, mapped to -1 without drawing so noisy hardware counts never crash
      and never land in a zero-mass row (callers should report how many there were, not drop
      them silently): x > nx, and x < nx with a == 1, e == 1 in a bin whose
      ``back_exit_rows[x, phi]`` has no mass (``flight[x, phi, BACK] == 0``; 168 of the 256
      bins). The engine never produces either kind.

    ``source`` is coerced with ``as_source`` only when at least one uniform is needed, so empty
    or row-free input draws nothing. Raises TypeError for a non-Kernels ``k``, ValueError for
    the wrong layout, a non-1-D or non-integer input, or a value outside [0, 2 ** 11).
    """
    _check_kernels(k)
    s = np.asarray(bitstrings)
    if s.ndim != 1:
        raise ValueError(f"bitstrings must be 1-D, got shape {s.shape}")
    if s.size == 0:
        return np.empty(0, dtype=np.int64)
    if not np.issubdtype(s.dtype, np.integer):
        raise ValueError(f"bitstrings must have an integer dtype, got {s.dtype}")
    if s.min() < 0 or s.max() >= 2 ** N_BITS:
        raise ValueError(f"bitstrings must lie in [0, {2 ** N_BITS})")
    s = s.astype(np.int64)
    sp = k.spec; nx = sp.nx
    x = s & ((1 << X_BITS) - 1)
    a = (s >> _A_SHIFT) & 1
    phi = (s >> _PHI_SHIFT) & ((1 << PHI_BITS) - 1)
    e = (s >> _E_SHIFT) & 1
    col = x % nx
    r = np.full(s.size, -1, np.int64); r[x == nx] = sp.row_of(sp.beam_y)
    se_ = np.nonzero((x < nx) & (a == 1) & (e == 1))[0]
    cr = np.cumsum(k.back_exit_rows, axis=-1)[col[se_], phi[se_]]
    live = cr[:, -1] > 0                 # e = 1 in a bin with no back-face mass: zero amplitude -> -1
    se_, cr = se_[live], cr[live]
    if se_.size:
        src = as_source(source)
        u = draw(src, se_.size) * cr[:, -1]
        r[se_] = np.minimum((cr <= u[:, None]).sum(axis=1), sp.ny - 1)
    return r


def run_lattice(k, n, source=None, *, chunk=1 << 16, return_bitstrings=False, checkpoints=()):
    """Run n matched lattice histories on the frozen Kernels ``k`` with uniforms from ``source``.

    ``source``: None (fresh unseeded numpy Generator), an int / np.integer / SeedSequence seed,
    or any RandomSource (see ``random_source.as_source``). ``checkpoints``: N values in [1, n]
    (sorted and de-duplicated) at which the cumulative transmitted count is recorded.
    Returns a :class:`LatticeResult`. Raises TypeError for a non-Kernels ``k`` or a bad source,
    ValueError for the wrong register layout, bad n / chunk / checkpoints or bad source output.
    """
    _check_kernels(k)
    n = _check_int("n", n, 1)
    chunk = _check_int("chunk", chunk, 1)
    cps = tuple(checkpoints)
    for c in cps:
        if not _is_int(c) or not 1 <= c <= n:
            raise ValueError(f"checkpoints must be ints in [1, {n}], got {c!r}")
    cps = tuple(sorted({int(c) for c in cps}))
    src = as_source(source)
    sp = k.spec; nx, nd = sp.nx, sp.n_dir
    cdf_x = np.cumsum(k.first_collision); cdf_x[-1] = 1.0
    q = k.flight[..., BACK]
    tot, rows, bits_all = 0, np.zeros(sp.ny, np.int64), []
    cp_counts = np.zeros(len(cps), np.int64); ci = 0
    done = 0
    while done < n:
        m = min(chunk, n - done); before = done; done += m
        x = np.minimum(np.searchsorted(cdf_x, draw(src, m), side="right"), nx)
        col = x % nx
        a = (draw(src, m) < k.scatter_ratio[col]).astype(np.int64)
        phi = np.minimum((draw(src, m) * nd).astype(np.int64), nd - 1)
        e = (draw(src, m) < q[col, phi]).astype(np.int64)
        t = (x == nx) | ((a == 1) & (e == 1))
        bits = x | (a << _A_SHIFT) | (phi << _PHI_SHIFT) | (e << _E_SHIFT)
        if ci < len(cps) and cps[ci] <= done:
            ct = np.cumsum(t)
            while ci < len(cps) and cps[ci] <= done:
                cp_counts[ci] = tot + int(ct[cps[ci] - before - 1]); ci += 1
        tot += int(t.sum())
        r = sample_exit_rows(k, bits, src)
        rows += np.bincount(r[r >= 0], minlength=sp.ny)
        if return_bitstrings: bits_all.append(bits)
    return LatticeResult(n, tot, rows, np.concatenate(bits_all) if return_bitstrings else None,
                         cps, cp_counts, chunk)
