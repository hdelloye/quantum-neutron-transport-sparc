"""Matched discrete lattice MC on Kernels v1 (PHYS-07) - prototype."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from random_source import as_source, draw
BACK = 0

@dataclass(frozen=True, eq=False)
class LatticeResult:
    n: int
    transmitted: int
    row_counts: np.ndarray
    bitstrings: np.ndarray | None
    @property
    def mean(self): return self.transmitted / self.n
    @property
    def se(self): p = self.mean; return float(np.sqrt(p * (1 - p) / self.n))

def run_lattice(k, n, source=None, *, chunk=1 << 20, return_bitstrings=False, return_hits=False):
    src = as_source(source)
    sp = k.spec; nx, nd = sp.nx, sp.n_dir
    cdf_x = np.cumsum(k.first_collision); cdf_x[-1] = 1.0
    q = k.flight[..., BACK]
    rc = np.cumsum(k.back_exit_rows, axis=-1)
    tot, rows, bits, hits = 0, np.zeros(sp.ny, np.int64), [], []
    done = 0
    while done < n:
        m = min(chunk, n - done); done += m
        x = np.minimum(np.searchsorted(cdf_x, draw(src, m), side="right"), nx)
        col = x % nx
        a = (draw(src, m) < k.scatter_ratio[col]).astype(np.int64)
        phi = np.minimum((draw(src, m) * nd).astype(np.int64), nd - 1)
        e = (draw(src, m) < q[col, phi]).astype(np.int64)
        t = (x == nx) | ((a == 1) & (e == 1))
        tot += int(t.sum())
        # exit row: uncollided -> row_of(beam_y); scattered+escaped -> sample back_exit_rows[col,phi,:]/q
        r = np.full(m, -1, np.int64); r[x == nx] = sp.row_of(sp.beam_y)
        se_ = np.nonzero((x < nx) & (a == 1) & (e == 1))[0]
        u = draw(src, se_.size) * q[col[se_], phi[se_]]
        cr = rc[col[se_], phi[se_]]
        r[se_] = np.minimum((cr <= u[:, None]).sum(axis=1), sp.ny - 1)
        rows += np.bincount(r[r >= 0], minlength=sp.ny)
        if return_bitstrings: bits.append(x | (a << 5) | (phi << 6) | (e << 10))
        if return_hits: hits.append(t)
    res = LatticeResult(n, tot, rows, np.concatenate(bits) if return_bitstrings else None)
    return (res, np.concatenate(hits)) if return_hits else res
