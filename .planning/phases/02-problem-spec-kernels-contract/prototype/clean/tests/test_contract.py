import math
import numpy as np
import pytest
from neutron_qae.problem import sparc_first_wall, atom_densities
from neutron_qae import nuclear_data as nd
from neutron_qae.kernels import build_kernels, BACK
from neutron_qae.exact import transmission_within, bitstring_probabilities_k1

SPEC = sparc_first_wall()
K = build_kernels(SPEC)

def test_ss316_atom_densities_match_pnnl():
    n = atom_densities(*nd.SS316)
    for el, ref in {"Fe": 0.056373, "Cr": 0.015751, "Ni": 0.009850, "Mo": 0.001255, "Mn": 0.001754, "Si": 0.001715}.items():
        assert n[el] == pytest.approx(ref, abs=1e-6)
    assert sum(n.values()) == pytest.approx(8.713e-2, rel=1e-3)

def test_mean_free_paths_sanity():
    raw = sparc_first_wall("isotropic_raw")
    assert 2.8 < 1 / raw.front.sigma_t < 3.3 and 4.2 < 1 / raw.back.sigma_t < 4.8

def test_boundary_inside_column_3_not_snapped():
    seg = SPEC.column_segments(3)
    assert [(a, b) for a, b, _ in seg] == [(1.875, 2.0), (2.0, 2.5)]
    tau3 = SPEC.tau_x(2.5) - SPEC.tau_x(1.875)
    W, S = SPEC.front.sigma_t, SPEC.back.sigma_t
    assert tau3 == pytest.approx(0.125 * W + 0.5 * S, rel=1e-14)
    assert abs(tau3 - 0.625 * W) > 1e-3 and abs(tau3 - 0.625 * S) > 1e-3
    assert K.first_collision[3] == pytest.approx(math.exp(-SPEC.tau_x(1.875)) * (1 - math.exp(-tau3)), rel=1e-13)
    cw, cs = SPEC.front.scatter_ratio, SPEC.back.scatter_ratio
    a = 0.125 * W
    expect = (cw * (1 - math.exp(-a)) + cs * math.exp(-a) * (1 - math.exp(-0.5 * S))) / (1 - math.exp(-tau3))
    assert K.scatter_ratio[3] == pytest.approx(expect, rel=1e-13)
    assert min(cw, cs) < K.scatter_ratio[3] < max(cw, cs)

def test_probability_conserved():
    assert math.fsum(K.first_collision) == pytest.approx(1.0, abs=1e-14)
    assert np.all((K.scatter_ratio >= 0) & (K.scatter_ratio <= 1))
    assert np.abs(K.flight.sum(-1) - 1).max() < 1e-13
    assert np.abs(K.back_exit_rows.sum(-1) - K.flight[..., BACK]).max() < 1e-13
    assert math.fsum(p for _, p, _ in bitstring_probabilities_k1(K)) == pytest.approx(1.0, abs=1e-14)

def test_mirror_symmetry_and_backward_bins():
    assert np.abs(K.flight - K.flight[:, ::-1]).max() < 1e-14
    assert np.all(K.flight[:, 4:12, BACK] == 0)       # cos(phi) <= 0 bins never reach the back face

def test_frozen():
    with pytest.raises(Exception):
        K.flight[0, 0, 0] = 1.0
    with pytest.raises(Exception):
        K.spec = None

def test_exact_values():
    assert transmission_within(K, 0) == pytest.approx(math.exp(-SPEC.tau_x(10.0)), rel=1e-14)
    closed = K.first_collision[-1] + float(np.sum(K.first_collision[:-1] * K.scatter_ratio * K.flight[:, :, BACK].mean(1)))
    assert transmission_within(K, 1) == pytest.approx(closed, rel=1e-14)
    assert transmission_within(K, 1) == pytest.approx(0.24300446519524305, rel=1e-9)
