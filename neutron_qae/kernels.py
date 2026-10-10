"""Kernels: the frozen classical/quantum contract v1 (PHYS-05).

`build_kernels(sparc_first_wall())` is the single source of the tables that the classical
Monte Carlo (Phase 3) samples and the quantum oracle (Phase 4) encodes. Contract v1 is frozen
in tests/golden/kernels_v1.json; changing any table, the quadrature or the outcome order is
a contract change that bumps KERNELS_CONTRACT_VERSION and regenerates the golden file with
`scripts/freeze_kernels.py --write --force`.
"""
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
    """Frozen one-group lattice kernels for a ProblemSpec (contract v1).

    Fields (nx columns, n_dir direction bins, ny rows; every table float64, read-only):

    - first_collision, shape (nx + 1,): first_collision[j] = P(first collision in column j)
      for the normally incident beam; first_collision[nx] = P(uncollided to the back face).
      Sums to 1.
    - scatter_ratio, shape (nx,): scatter_ratio[j] = P(scatter | collision in column j);
      in the mixed interface column it is the collision-weighted average of the two
      materials' ratios over the column's two sub-segments.
    - flight, shape (nx, n_dir, 4): flight[j, b, o] = P(outcome o | scattered in column j,
      new direction in bin b), o in (BACK, FRONT, LATERAL, COLLIDE) = (0, 1, 2, 3). These are
      conditional averages over the scatter-site density inside column j and over phi
      uniform inside bin b (RESEARCH Pattern 4). Each flight[j, b, :] sums to 1.
    - back_exit_rows, shape (nx, n_dir, ny): back_exit_rows[j, b, i] = P(leave the back
      face in row i | j, b), rows by ProblemSpec.row_of; sums over i to flight[j, b, BACK].

    Construction takes private float64 copies of the four tables, checks their shapes
    against spec and marks them read-only; the dataclass is frozen and eq=False (default
    eq would compare arrays elementwise and raise).
    """

    spec: ProblemSpec
    first_collision: np.ndarray   # (nx+1,)  [j] = P(first collision in column j); [nx] = P(uncollided -> back face)
    scatter_ratio: np.ndarray     # (nx,)    P(scatter | collision in column j)
    flight: np.ndarray            # (nx, n_dir, 4) P(outcome | scattered in column j, direction bin b)
    back_exit_rows: np.ndarray    # (nx, n_dir, ny) P(leave back face in row i | j, b); sums over i to flight[..., BACK]

    def __post_init__(self):
        sp = self.spec
        shapes = {
            "first_collision": (sp.nx + 1,),
            "scatter_ratio": (sp.nx,),
            "flight": (sp.nx, sp.n_dir, 4),
            "back_exit_rows": (sp.nx, sp.n_dir, sp.ny),
        }
        for name, shape in shapes.items():
            arr = np.array(getattr(self, name), dtype=np.float64, copy=True)
            if arr.shape != shape:
                raise ValueError(f"Kernels.{name} has shape {arr.shape}, expected {shape} for this spec")
            arr.setflags(write=False)
            object.__setattr__(self, name, arr)

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
            row = spec.row_of(spec.beam_y + s * sy)
            np.add.at(rows[j, bb], row[hit], (W * esc)[hit])
    return Kernels(spec, first, ratio, flight, rows)
