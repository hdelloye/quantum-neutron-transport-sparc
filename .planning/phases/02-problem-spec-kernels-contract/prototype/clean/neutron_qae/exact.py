"""Exact lattice solver: enumerate every random-bit string of the K=1 model (PHYS-06)."""
from __future__ import annotations

import math

from neutron_qae.kernels import BACK, Kernels

X_BITS, A_BITS, PHI_BITS, E_BITS = 5, 1, 4, 1     # Q1 register order, little-endian: x | a<<5 | phi<<6 | e<<10


def bitstring_probabilities_k1(k: Kernels) -> list[tuple[int, float, bool]]:
    nx, nd_ = k.spec.nx, k.spec.n_dir
    assert nx == 2 ** (X_BITS - 1) and nd_ == 2 ** PHI_BITS
    out = []
    for s in range(2 ** (X_BITS + A_BITS + PHI_BITS + E_BITS)):
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
    if K == 0:
        return float(k.first_collision[-1])
    if K == 1:
        return math.fsum(p for _, p, t in bitstring_probabilities_k1(k) if t)
    raise ValueError("contract v1 supports K in {0, 1}; K=2 is a contract change (QC-08, v2)")
