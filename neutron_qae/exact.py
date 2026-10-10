"""Exact lattice solver: enumerate every random-bit string of the K=1 model (PHYS-06).

The reference T_K is the math.fsum over a literal enumeration of the 2^11 bit strings of
the Q1 register (never sampled, never taken from the closed form alone). Contract v1
supports K in {0, 1} (PD-04).
"""
from __future__ import annotations

import math

import numpy as np

from neutron_qae.kernels import BACK, Kernels

X_BITS, A_BITS, PHI_BITS, E_BITS = 5, 1, 4, 1     # Q1 register order, little-endian: x | a<<5 | phi<<6 | e<<10
N_BITS = X_BITS + A_BITS + PHI_BITS + E_BITS     # 11
REGISTER_LAYOUT = "x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10, little-endian (bit i = Qiskit qubit i)"


def bitstring_probabilities_k1(k: Kernels) -> list[tuple[int, float, bool]]:
    """All (s, probability, transmitted) for the K=1 model, s strictly increasing.

    Bit string s encodes REGISTER_LAYOUT: x = s & 31 (first-collision column, x = nx means
    uncollided), a = bit 5 (1 = scatter), phi = bits 6-9 (direction bin), e = bit 10
    (1 = flight reaches the back face). Strings with x > nx have amplitude 0 and are skipped
    (1088 of 2048 kept). x = nx shares low bits 0000 with column 0, so its a and e branches
    use scatter_ratio[0] and flight[0, phi, BACK], exactly like the circuit's uniformly
    controlled rotations; every x = nx string counts as transmitted. Transmitted means
    x == nx or (a == 1 and e == 1).
    """
    nx, nd_ = k.spec.nx, k.spec.n_dir
    if nx != 2 ** (X_BITS - 1) or nd_ != 2 ** PHI_BITS:
        raise ValueError(f"the 11-bit register layout needs nx == {2 ** (X_BITS - 1)} and n_dir == {2 ** PHI_BITS}; "
                         f"got nx={nx}, n_dir={nd_}")
    out = []
    for s in range(2 ** N_BITS):
        x, a, phi, e = s & 0b11111, (s >> 5) & 1, (s >> 6) & 0b1111, (s >> 10) & 1
        if x > nx:
            continue                      # amplitude 0 in the circuit
        col = x % nx                      # x = nx (uncollided) has low bits 0000: rotations of column 0
        c = float(k.scatter_ratio[col])
        q = float(k.flight[col, phi, BACK])
        p = float(k.first_collision[x]) * (c if a else 1.0 - c) / nd_ * (q if e else 1.0 - q)
        out.append((s, p, x == nx or (a == 1 and e == 1)))
    return out


def transmission_within(k: Kernels, K: int) -> float:
    """Exact probability of leaving the back face within K collisions (K in {0, 1})."""
    if K == 0:
        return float(k.first_collision[-1])
    if K == 1:
        return math.fsum(p for _, p, t in bitstring_probabilities_k1(k) if t)
    raise ValueError("contract v1 supports K in {0, 1}; K=2 is a contract change (QC-08, v2)")


def exit_row_distribution_k1(k: Kernels) -> np.ndarray:
    """Exact K = 1 back-face exit histogram over rows, shape (ny,), float64; sums to T1.

    Scattered part sum_j first_collision[j] * scatter_ratio[j] * mean_b back_exit_rows[j, b, :]
    plus the uncollided mass first_collision[nx] in row spec.row_of(spec.beam_y) (row 8).
    """
    sp = k.spec
    out = np.zeros(sp.ny, dtype=np.float64)
    for j in range(sp.nx):
        out += k.first_collision[j] * k.scatter_ratio[j] * k.back_exit_rows[j].mean(axis=0)
    out[sp.row_of(sp.beam_y)] += k.first_collision[sp.nx]
    return out
