"""PHYS-05: Kernels contract v1 shapes, conservation, symmetry, immutability, determinism, imports."""
import ast
import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from neutron_qae.kernels import BACK, Kernels, build_kernels
from neutron_qae.problem import sparc_first_wall

ROOT = Path(__file__).resolve().parents[1]
SPEC = sparc_first_wall()
K = build_kernels(SPEC)
TABLES = ("first_collision", "scatter_ratio", "flight", "back_exit_rows")


def test_table_shapes_and_dtype():
    expected = {"first_collision": (17,), "scatter_ratio": (16,), "flight": (16, 16, 4), "back_exit_rows": (16, 16, 16)}
    for name, shape in expected.items():
        arr = getattr(K, name)
        assert arr.shape == shape, name
        assert arr.dtype == np.float64, name


def test_probability_conserved():
    assert math.fsum(K.first_collision) == pytest.approx(1.0, abs=1e-14)
    assert np.all((K.scatter_ratio >= 0) & (K.scatter_ratio <= 1))
    assert np.abs(K.flight.sum(-1) - 1).max() < 1e-13
    assert np.abs(K.back_exit_rows.sum(-1) - K.flight[..., BACK]).max() < 1e-13
    for name in TABLES:
        assert np.all(getattr(K, name) >= 0), name


def test_backward_bins_never_reach_back_face():
    assert np.all(K.flight[:, 4:12, BACK] == 0)       # cos(phi) <= 0 bins
    assert np.all(K.flight[:, [0, 1, 14, 15], BACK] > 0)  # bins 2, 3, 12, 13 reach it only from deeper columns


def test_mirror_symmetry():
    assert np.abs(K.flight - K.flight[:, ::-1]).max() < 1e-14
    assert np.abs(K.back_exit_rows - K.back_exit_rows[:, ::-1, ::-1]).max() < 1e-14


def test_kernels_frozen_and_read_only():
    for name in TABLES:
        arr = getattr(K, name)
        with pytest.raises(ValueError):
            arr[(0,) * arr.ndim] = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        K.flight = np.zeros((16, 16, 4))
    src = [np.array(getattr(K, name)) for name in TABLES]   # writable copies
    k2 = Kernels(SPEC, *src)
    before = [np.array(getattr(k2, name)) for name in TABLES]
    for a in src:
        a[...] = -1.0
    for name, b in zip(TABLES, before):
        np.testing.assert_array_equal(getattr(k2, name), b)
    with pytest.raises(ValueError):
        Kernels(SPEC, src[0][:-1], *src[1:])
    with pytest.raises(ValueError):
        Kernels(SPEC, src[0], src[1], src[2][:, :8], src[3])


def test_build_kernels_is_deterministic():
    k2 = build_kernels(sparc_first_wall())
    for name in TABLES:
        assert np.array_equal(getattr(K, name), getattr(k2, name)), name


ALLOWED_TOP_LEVEL = {"__future__", "dataclasses", "hashlib", "json", "math", "numpy", "neutron_qae", "typing"}


def test_contract_modules_use_only_numpy_and_stdlib():
    for mod in ("nuclear_data", "problem", "kernels", "exact"):
        tree = ast.parse((ROOT / "neutron_qae" / f"{mod}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                tops = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"{mod}: relative import"
                tops = [node.module.split(".")[0]]
            else:
                continue
            for top in tops:
                assert top in ALLOWED_TOP_LEVEL, f"{mod} imports {top}"
