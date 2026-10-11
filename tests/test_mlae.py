"""Vendored MLAE (neutron_qae/mlae.py): QAE-01 parity, QAE-03 cost and the probe edges."""
from __future__ import annotations

import math

from neutron_qae.mlae import PowerResult, estimate


def test_k0_only_estimate_is_hit_fraction():
    r = estimate([PowerResult(0, 100, 37)])
    assert abs(r.a_hat - 0.37) <= 1e-7, r.a_hat
    se = math.sqrt(0.37 * 0.63 / 100)
    assert abs(r.se - se) <= 1e-6 * se, (r.se, se)
    assert r.n_A == 100 and r.shots_total == 100
