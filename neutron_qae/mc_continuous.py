"""Continuous 2D Woodcock delta-tracking Monte Carlo: the physics reference (PHYS-03/04).

Scope
-----
`run_continuous(spec, n, source)` follows ``n`` neutrons of the normally incident pencil
beam through the frozen :class:`~neutron_qae.problem.ProblemSpec` slab (x = depth,
y = lateral) and tallies integer counts: fates (back-face transmission, front reflection,
lateral leakage, absorption), the transmitted collision-order breakdown and the back-face
exit-row histogram (all orders and at most one collision). Every fraction on
:class:`ContinuousResult` has a binomial standard error ``sqrt(p (1 - p) / n)`` computed
once from int64 counts (PHYS-03). Cross sections come from ``spec.front`` / ``spec.back``,
never from ``Kernels``.

Delta-tracking rules (PD-09)
----------------------------
- Majorant ``Sigma_maj = max(spec.front.sigma_t, spec.back.sigma_t)`` (the WHA
  transport-corrected value under the default model; steel accepts 81.4% of tentative
  collisions there).
- Flight ``d = -log1p(-u) / Sigma_maj``. The exit test comes before the collision: if
  ``d >= distance to the box`` the history leaves through the face it hits first; at a
  corner tie the x face wins (same rule as ``kernels.py``). A back exit records
  ``y_exit``; front and lateral exits never enter the row tallies.
- Otherwise the neutron moves to the tentative site and one uniform ``u * Sigma_maj``
  partitions the event using the material at the *new* position (half-open rule
  ``x < boundary_x`` -> front, as ``ProblemSpec.material_at``): ``< Sigma_s`` real
  isotropic 2D scatter (phi = 2 pi u'), ``< Sigma_t`` real absorption, else virtual
  (same direction). Only real collisions count in ``ncol``.
- Rows come only from ``spec.row_of`` (floor, clipped to [0, ny - 1]).
- A ``max_iter`` guard on the per-chunk loop raises RuntimeError.

Draw order and reproducibility (PD-12)
--------------------------------------
Histories are processed in chunks of ``chunk`` (default 2^16: fastest and about 13 MB
peak). Within a chunk, each loop iteration draws, in this order: one flight uniform per
active history, then one collision-type uniform per non-exiting history, then one
direction uniform per scattered history (none when no history scatters). Every uniform
arrives through ``random_source.draw`` from the injected source.

Reproducibility contract: same source state + same ``n`` + same ``chunk`` + same numpy
version and platform -> identical per-history arrays. A different ``chunk`` gives
different, equally valid histories (the vectorized draw order depends on it); libm
``log1p``/``cos``/``sin`` may differ in the last ulp across platforms.

The three transmissions (do not confuse them)
---------------------------------------------
- ``transmission``: all collision orders, the physical reference (ANLY-03 truncation bias).
- ``within(0)``: uncollided transmission, equal in expectation to e^{-tau} of the *model*
  optical depth ``spec.tau_x(spec.width_x)`` (transport-corrected; not the physical
  e^{-tau_t}).
- ``within(1)``: at most one collision, equal in expectation to the exact T1
  (``exact.transmission_within(k, 1)``) because normal incidence puts every first
  collision on y = beam_y.
``transmission`` must never be tested against T1: the K = 1 truncation bias (~7e-4) is
resolved at large n.

Memory: ``histories=True`` stores 32 bytes per history (fate, ncol, yexit, x_first).
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import NamedTuple
import numpy as np
from neutron_qae.problem import ProblemSpec
from neutron_qae.random_source import as_source, draw

__all__ = ["BACK", "FRONT", "LATERAL", "ABSORBED", "FATES", "ContinuousResult",
           "ContinuousHistories", "run_continuous"]

BACK, FRONT, LATERAL, ABSORBED = 0, 1, 2, 3
FATES = ("back", "front", "lateral", "absorbed")


def _frac_se(count, n):
    """Fraction p = count / n and its binomial SE sqrt(p (1 - p) / n) (0.0 for a zero count)."""
    p = np.asarray(count, dtype=np.float64) / n
    return p, np.sqrt(p * (1.0 - p) / n)


def _check_int(name, v, minimum):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or v < minimum:
        raise ValueError(f"{name} must be an int >= {minimum}, got {v!r}")
    return int(v)


class ContinuousHistories(NamedTuple):
    """Per-history arrays (length n) returned with ``histories=True``."""
    fate: np.ndarray        # int64 BACK / FRONT / LATERAL / ABSORBED
    ncol: np.ndarray        # int64 number of real collisions
    yexit: np.ndarray       # float64 back-face exit height, NaN unless fate == BACK
    x_first: np.ndarray     # float64 depth of the first real collision, NaN if never collided


@dataclass(frozen=True, eq=False)
class ContinuousResult:
    """Integer tallies of one run; fractions and SEs are derived properties."""
    n: int
    fate_counts: np.ndarray          # (4,) int64, indexed by BACK / FRONT / LATERAL / ABSORBED
    order_counts: np.ndarray         # (max_order + 2,) transmitted with 0..max_order collisions, last = overflow
    row_counts: np.ndarray           # (ny,) back-face exit rows, all orders
    row_counts_le1: np.ndarray       # (ny,) back-face exit rows, at most one collision
    iterations: int                  # largest loop-iteration count over chunks
    chunk: int

    def __post_init__(self):
        for name in ("fate_counts", "order_counts", "row_counts", "row_counts_le1"):
            arr = np.array(getattr(self, name), dtype=np.int64)
            arr.setflags(write=False)
            object.__setattr__(self, name, arr)

    def _fate(self, f):
        p, se = _frac_se(self.fate_counts[f], self.n)
        return float(p), float(se)

    @property
    def transmission(self) -> float:
        """Back-face transmission, all collision orders (not T1; see within(1))."""
        return self._fate(BACK)[0]

    @property
    def transmission_se(self) -> float:
        return self._fate(BACK)[1]

    @property
    def absorption(self) -> float:
        return self._fate(ABSORBED)[0]

    @property
    def absorption_se(self) -> float:
        return self._fate(ABSORBED)[1]

    @property
    def reflection(self) -> float:
        """Front-face (plasma side) reflection."""
        return self._fate(FRONT)[0]

    @property
    def reflection_se(self) -> float:
        return self._fate(FRONT)[1]

    @property
    def leakage_lateral(self) -> float:
        return self._fate(LATERAL)[0]

    @property
    def leakage_lateral_se(self) -> float:
        return self._fate(LATERAL)[1]

    @property
    def max_order(self) -> int:
        return len(self.order_counts) - 2

    @property
    def order_fractions(self) -> np.ndarray:
        """Fraction of all n histories transmitted with 0..max_order collisions, last = overflow."""
        return _frac_se(self.order_counts, self.n)[0]

    @property
    def order_se(self) -> np.ndarray:
        return _frac_se(self.order_counts, self.n)[1]

    def within(self, K) -> tuple[float, float]:
        """(p, se) of transmission with at most K real collisions, 0 <= K <= max_order."""
        if isinstance(K, (bool, np.bool_)) or not isinstance(K, (int, np.integer)) or not 0 <= K <= self.max_order:
            raise ValueError(f"K must be an int in [0, {self.max_order}], got {K!r}")
        p, se = _frac_se(int(self.order_counts[:int(K) + 1].sum()), self.n)
        return float(p), float(se)

    def row_fractions(self, le1: bool = False) -> np.ndarray:
        """Back-face exit-row fractions of all n histories (le1: at most one collision)."""
        return _frac_se(self.row_counts_le1 if le1 else self.row_counts, self.n)[0]

    def row_se(self, le1: bool = False) -> np.ndarray:
        return _frac_se(self.row_counts_le1 if le1 else self.row_counts, self.n)[1]


def run_continuous(spec, n, source=None, *, chunk=1 << 16, max_order=8, max_iter=100_000, histories=False):
    """Run n delta-tracking histories on ``spec`` with uniforms from ``source``.

    ``source``: None (fresh unseeded numpy Generator), an int / np.integer / SeedSequence
    seed, or any RandomSource (see ``random_source.as_source``). Returns a
    :class:`ContinuousResult`, or ``(result, ContinuousHistories)`` with ``histories=True``.
    Raises TypeError for a non-ProblemSpec spec or a bad source, ValueError for bad counts or
    bad source output, RuntimeError if a chunk exceeds ``max_iter`` loop iterations.
    """
    if not isinstance(spec, ProblemSpec):
        raise TypeError(f"spec must be a ProblemSpec, got {type(spec).__name__}")
    n = _check_int("n", n, 1)
    chunk = _check_int("chunk", chunk, 1)
    max_order = _check_int("max_order", max_order, 0)
    max_iter = _check_int("max_iter", max_iter, 1)
    src = as_source(source)
    fW, fS = spec.front, spec.back
    smaj = max(fW.sigma_t, fS.sigma_t)
    L, H, xb = spec.width_x, spec.height_y, spec.boundary_x
    fate_c = np.zeros(4, np.int64); ord_c = np.zeros(max_order + 2, np.int64)
    rows = np.zeros(spec.ny, np.int64); rows1 = np.zeros(spec.ny, np.int64)
    it_max = 0; hist = []
    done = 0
    while done < n:
        m = min(chunk, n - done); done += m
        x = np.zeros(m); y = np.full(m, spec.beam_y); ux = np.ones(m); uy = np.zeros(m)
        fcx = np.full(m, np.nan); ncol = np.zeros(m, np.int64); fate = np.full(m, -1, np.int64); yexit = np.full(m, np.nan)
        act = np.arange(m)
        it = 0
        while act.size:
            it += 1
            if it > max_iter: raise RuntimeError("delta tracking did not terminate")
            xa, ya, cx, sy = x[act], y[act], ux[act], uy[act]
            d = -np.log1p(-draw(src, act.size)) / smaj
            with np.errstate(divide="ignore", invalid="ignore"):
                sx = np.where(cx > 0, (L - xa) / cx, np.where(cx < 0, -xa / cx, np.inf))
                sl = np.where(sy > 0, (H - ya) / sy, np.where(sy < 0, -ya / sy, np.inf))
            s = np.minimum(sx, sl)
            out = d >= s
            face = np.where(sx <= sl, np.where(cx > 0, BACK, FRONT), LATERAL)
            eo = act[out]; fate[eo] = face[out]
            yexit[eo] = np.where(face[out] == BACK, ya[out] + sx[out] * sy[out], np.nan)
            stay = ~out; ai = act[stay]; dd = d[stay]
            xn = xa[stay] + dd * cx[stay]; yn = ya[stay] + dd * sy[stay]
            x[ai] = xn; y[ai] = yn
            front = xn < xb
            st = np.where(front, fW.sigma_t, fS.sigma_t); ss = np.where(front, fW.sigma_s, fS.sigma_s)
            u = draw(src, ai.size) * smaj
            scat = u < ss; absb = (u >= ss) & (u < st)
            real = ai[scat | absb]; first = real[ncol[real] == 0]; fcx[first] = x[first]
            ncol[real] += 1
            fate[ai[absb]] = ABSORBED
            sc = ai[scat]
            phi = 2.0 * math.pi * draw(src, sc.size)
            ux[sc] = np.cos(phi); uy[sc] = np.sin(phi)
            act = ai[~absb]
        it_max = max(it_max, it)
        fate_c += np.bincount(fate, minlength=4)
        tb = fate == BACK
        ord_c += np.bincount(np.minimum(ncol[tb], max_order + 1), minlength=max_order + 2)
        r = spec.row_of(yexit[tb]); rows += np.bincount(r, minlength=spec.ny)
        rows1 += np.bincount(r[ncol[tb] <= 1], minlength=spec.ny)
        if histories: hist.append((fate, ncol, yexit, fcx))
    res = ContinuousResult(n, fate_c, ord_c, rows, rows1, it_max, chunk)
    if histories:
        return res, ContinuousHistories(*(np.concatenate(a) for a in zip(*hist)))
    return res
