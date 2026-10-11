"""Continuous 2D Woodcock delta-tracking MC (PHYS-03/04) - prototype."""
from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np
from random_source import as_source, draw

BACK, FRONT, LATERAL, ABSORBED = 0, 1, 2, 3
FATES = ("back", "front", "lateral", "absorbed")

def _se(count, n):
    p = count / n
    return np.sqrt(p * (1 - p) / n)

@dataclass(frozen=True, eq=False)
class ContinuousResult:
    n: int
    fate_counts: np.ndarray          # (4,) int64
    order_counts: np.ndarray         # (max_order+2,) transmitted with 0..max_order collisions, last = overflow
    row_counts: np.ndarray           # (ny,) back-face exit rows, all orders
    row_counts_le1: np.ndarray       # (ny,) back-face exit rows, <=1 collision
    iterations: int
    @property
    def transmission(self): return self.fate_counts[BACK] / self.n
    @property
    def transmission_se(self): return float(_se(self.fate_counts[BACK], self.n))
    @property
    def absorption(self): return self.fate_counts[ABSORBED] / self.n
    def within(self, K):
        c = int(self.order_counts[:K + 1].sum()); return c / self.n, float(_se(c, self.n))

def run_continuous(spec, n, source=None, *, chunk=1 << 20, max_order=8, max_iter=100_000, histories=False):
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
    res = ContinuousResult(n, fate_c, ord_c, rows, rows1, it_max)
    if histories:
        return res, tuple(np.concatenate(a) for a in zip(*hist))
    return res
