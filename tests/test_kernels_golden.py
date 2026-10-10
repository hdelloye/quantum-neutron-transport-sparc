"""Contract v1 freeze: rebuilt Kernels must match tests/golden/kernels_v1.json (rtol 1e-12, atol 1e-15).

Independent of scripts/freeze_kernels.py (never imports it): its own json.load and comparison helper.
"""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import compliance_checks as cc
from neutron_qae.exact import REGISTER_LAYOUT, exit_row_distribution_k1, transmission_within
from neutron_qae.kernels import KERNELS_CONTRACT_VERSION, N_PHI_NODES, N_X_NODES, build_kernels
from neutron_qae.problem import sparc_first_wall, spec_fingerprint

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden" / "kernels_v1.json"
TABLES = ("first_collision", "scatter_ratio", "flight", "back_exit_rows")
RTOL, ATOL = 1e-12, 1e-15

with GOLDEN.open(encoding="utf-8") as _fh:
    DOC = json.load(_fh)

SPEC = sparc_first_wall()
K = build_kernels(SPEC)


def _mismatches(k, doc) -> list[str]:
    out = []
    if doc.get("contract_version") != KERNELS_CONTRACT_VERSION:
        out.append(f"contract_version {doc.get('contract_version')!r} != {KERNELS_CONTRACT_VERSION!r}")
    if doc.get("spec_fingerprint") != spec_fingerprint(k.spec):
        out.append("spec_fingerprint differs")
    for name in TABLES:
        got, want = getattr(k, name), np.asarray(doc[name], dtype=float)
        if got.shape != want.shape:
            out.append(f"{name}: shape {got.shape} != golden {want.shape}")
        elif not np.allclose(got, want, rtol=RTOL, atol=ATOL):
            out.append(f"{name}: differs beyond rtol {RTOL} / atol {ATOL}")
    return out


def test_golden_metadata():
    assert DOC["contract_version"] == KERNELS_CONTRACT_VERSION == "1"
    assert DOC["model"] == "transport_corrected"
    assert DOC["spec_fingerprint"] == spec_fingerprint(sparc_first_wall())
    assert DOC["quadrature"] == {"n_x_nodes": N_X_NODES, "n_phi_nodes": N_PHI_NODES} == {"n_x_nodes": 24, "n_phi_nodes": 48}
    assert DOC["register_layout"] == REGISTER_LAYOUT


def test_rebuilt_kernels_match_golden():
    assert _mismatches(K, DOC) == []


def test_golden_exact_values():
    assert transmission_within(K, 0) == pytest.approx(DOC["T0"], rel=1e-12)
    assert transmission_within(K, 1) == pytest.approx(DOC["T1"], rel=1e-12)
    assert DOC["T0"] == pytest.approx(0.23256718303628812, rel=1e-9)
    assert DOC["T1"] == pytest.approx(0.24300446519524305, rel=1e-9)
    np.testing.assert_allclose(exit_row_distribution_k1(K), DOC["exit_rows_k1"], rtol=RTOL, atol=ATOL)


def test_tampered_golden_is_detected():
    bad = copy.deepcopy(DOC)
    bad["flight"][5][1][0] *= 1 + 1e-9
    assert _mismatches(K, bad) != []
    bad = copy.deepcopy(DOC)
    bad["spec_fingerprint"] = "0" * 64
    assert _mismatches(K, bad) != []
    bad = copy.deepcopy(DOC)
    bad["contract_version"] = "2"
    assert _mismatches(K, bad) != []


def test_golden_file_is_small_and_outside_data():
    assert GOLDEN.stat().st_size < cc.MAX_FILE_BYTES
    assert GOLDEN.resolve().parent == (ROOT / "tests" / "golden").resolve()
