"""PHYS-01: geometry, the column-4 interface, the row rule, validation and the spec fingerprint."""
import dataclasses
import math

import numpy as np
import pytest

from neutron_qae.kernels import build_kernels
from neutron_qae.problem import Material, sparc_first_wall, spec_fingerprint

SPEC = sparc_first_wall()
K = build_kernels(SPEC)


def test_sparc_first_wall_geometry():
    s = SPEC
    assert (s.width_x, s.height_y, s.nx, s.ny, s.boundary_x, s.beam_y, s.n_dir) == (10.0, 10.0, 16, 16, 2.0, 5.0, 16)
    assert s.front.name == "WHA 97W-2Ni-1Fe" and s.back.name == "SS316"
    assert s.dx == s.dy == 0.625
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.nx = 8


def test_boundary_inside_roadmap_column_4_is_not_snapped():
    """0-based column index 3 = the ROADMAP's 1-based column 4: it holds the 2.0 cm interface
    and is integrated exactly over its WHA and SS316 sub-segments, never snapped."""
    seg = SPEC.column_segments(3)
    assert [(a, b) for a, b, _ in seg] == [(1.875, 2.0), (2.0, 2.5)]
    assert seg[0][2] is SPEC.front and seg[1][2] is SPEC.back
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


def test_material_at_half_open_interface():
    assert SPEC.material_at(2.0) is SPEC.back
    assert SPEC.material_at(1.9999) is SPEC.front
    assert SPEC.material_at(0.0) is SPEC.front
    assert SPEC.material_at(10.0) is SPEC.back


def test_columns_beside_interface_are_single_material():
    for j in range(3):
        seg = SPEC.column_segments(j)
        assert len(seg) == 1 and seg[0][2] is SPEC.front
    for j in range(4, 16):
        seg = SPEC.column_segments(j)
        assert len(seg) == 1 and seg[0][2] is SPEC.back


def test_interface_on_column_edge_has_no_zero_width_segment():
    spec = sparc_first_wall(boundary_x=1.875)
    for j in range(spec.nx):
        seg = spec.column_segments(j)
        assert len(seg) == 1
        assert all(b > a for a, b, _ in seg)
    assert spec.column_segments(2)[0][2] is spec.front
    assert spec.column_segments(3)[0][2] is spec.back
    assert math.fsum(build_kernels(spec).first_collision) == pytest.approx(1.0, abs=1e-14)


def test_row_rule_uses_floor():
    assert SPEC.row_of(5.0) == 8
    assert SPEC.row_of(4.9999) == 7
    assert SPEC.row_of(10.0) == 15
    assert SPEC.row_of(0.0) == 0
    assert isinstance(SPEC.row_of(5.0), int)
    rows = SPEC.row_of(np.array([0.0, 4.9999, 5.0, 10.0]))
    assert rows.dtype.kind == "i"
    np.testing.assert_array_equal(rows, [0, 7, 8, 15])


@pytest.mark.parametrize("overrides", [
    {"boundary_x": 0.0}, {"boundary_x": 10.0}, {"boundary_x": -1.0},
    {"beam_y": 0.0}, {"beam_y": 10.0},
    {"nx": 0}, {"ny": 0}, {"n_dir": 0},
    {"height_y": 0.0}, {"width_x": -10.0}, {"nx": True}, {"nx": 16.0},
])
def test_spec_validation_rejects_degenerate_geometry(overrides):
    with pytest.raises(ValueError):
        sparc_first_wall(**overrides)


@pytest.mark.parametrize("sigma_t, sigma_s", [(0.0, 0.0), (0.1, 0.2), (0.1, -0.01), (float("nan"), 0.0)])
def test_material_validation(sigma_t, sigma_s):
    with pytest.raises(ValueError):
        Material("bad", sigma_t, sigma_s)


def test_spec_fingerprint_stable_and_sensitive():
    f1, f2 = spec_fingerprint(sparc_first_wall()), spec_fingerprint(sparc_first_wall())
    assert f1 == f2
    assert len(f1) == 64 and all(c in "0123456789abcdef" for c in f1)
    assert spec_fingerprint(sparc_first_wall("isotropic_raw")) != f1
    assert spec_fingerprint(sparc_first_wall(width_x=20.0)) != f1


def test_isotropic_raw_selectable_with_one_argument():
    raw = sparc_first_wall("isotropic_raw")
    assert raw.front.sigma_t == pytest.approx(0.3308900275980838, rel=1e-12)
    assert raw.back.sigma_t == pytest.approx(0.2228736475733168, rel=1e-12)
    assert raw.front.sigma_s == pytest.approx(0.1741611144365387, rel=1e-12)
    assert raw.back.sigma_s == pytest.approx(0.10140642019174056, rel=1e-12)
