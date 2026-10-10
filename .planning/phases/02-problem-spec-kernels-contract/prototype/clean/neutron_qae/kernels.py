"""Kernels: the frozen classical/quantum contract (PHYS-05)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from neutron_qae.problem import ProblemSpec

KERNELS_CONTRACT_VERSION = "1"
BACK, FRONT, LATERAL, COLLIDE = 0, 1, 2, 3
OUTCOMES = ("back", "front", "lateral", "collide")
N_X_NODES, N_PHI_NODES = 24, 48     # Gauss-Legendre nodes per material sub-segment / per direction bin


@dataclass(frozen=True, eq=False)
class Kernels:
    spec: ProblemSpec
    first_collision: np.ndarray   # (nx+1,)  [j] = P(first collision in column j); [nx] = P(uncollided -> back face)
    scatter_ratio: np.ndarray     # (nx,)    P(scatter | collision in column j)
    flight: np.ndarray            # (nx, n_dir, 4) P(outcome | scattered in column j, direction bin b)
    back_exit_rows: np.ndarray    # (nx, n_dir, ny) P(leave back face in row i | j, b); sums over i to flight[..., BACK]

    def __post_init__(self):
        for a in (self.first_collision, self.scatter_ratio, self.flight, self.back_exit_rows):
            a.setflags(write=False)

    @property
    def escape_back(self) -> np.ndarray:
        return self.flight[..., BACK]


def build_kernels(spec: ProblemSpec, n_x_nodes: int = N_X_NODES, n_phi_nodes: int = N_PHI_NODES) -> Kernels:
    nx, nd_, ny = spec.nx, spec.n_dir, spec.ny
    edges = np.exp(-spec.tau_x(np.arange(nx + 1) * spec.dx))
    first = np.empty(nx + 1)
    first[:nx] = edges[:-1] - edges[1:]
    first[nx] = edges[-1]
    ratio = np.empty(nx)
    flight = np.zeros((nx, nd_, 4))
    rows = np.zeros((nx, nd_, ny))
    gx, gwx = np.polynomial.legendre.leggauss(n_x_nodes)
    gp, gwp = np.polynomial.legendre.leggauss(n_phi_nodes)
    dphi = 2.0 * math.pi / nd_
    for j in range(nx):
        scat, xs, ws = 0.0, [], []
        for a, b, m in spec.column_segments(j):
            scat += m.scatter_ratio * (math.exp(-spec.tau_x(a)) - math.exp(-spec.tau_x(b)))
            xn = 0.5 * (b - a) * gx + 0.5 * (a + b)
            xs.append(xn)
            ws.append(0.5 * (b - a) * gwx * m.sigma_s * np.exp(-spec.tau_x(xn)))  # scatter-site density
        ratio[j] = scat / first[j]
        xs, ws = np.concatenate(xs), np.concatenate(ws)
        ws = ws / ws.sum()
        for bb in range(nd_):
            phi = (bb + 0.5 * (gp + 1.0)) * dphi
            X, P = np.meshgrid(xs, phi, indexing="ij")
            W = np.outer(ws, 0.5 * gwp)
            cx, sy = np.cos(P), np.sin(P)       # Gauss nodes never hit cos=0 or sin=0 exactly
            sx = np.where(cx > 0, (spec.width_x - X) / cx, -X / cx)
            sl = np.where(sy > 0, (spec.height_y - spec.beam_y) / sy, -spec.beam_y / sy)
            s = np.minimum(sx, sl)
            x_end = X + s * cx
            esc = np.exp(-np.abs(spec.tau_x(x_end) - spec.tau_x(X)) / np.abs(cx))
            face = np.where(sx <= sl, np.where(cx > 0, BACK, FRONT), LATERAL)
            for f in (BACK, FRONT, LATERAL):
                flight[j, bb, f] = np.sum(W * esc * (face == f))
            flight[j, bb, COLLIDE] = np.sum(W * (1.0 - esc))
            hit = face == BACK
            row = np.clip(((spec.beam_y + s * sy) / spec.dy).astype(int), 0, ny - 1)
            np.add.at(rows[j, bb], row[hit], (W * esc)[hit])
    return Kernels(spec, first, ratio, flight, rows)
