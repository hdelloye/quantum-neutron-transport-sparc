"""The committed IonQ records file (data/ionq_runs.json) is valid, real and statistically sane (PD-20).

The 4-sigma test skips (never fails) until plan 04-04 ingests sampled Q1/Q1lite records with k = 0
and some k >= 1.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from neutron_qae.oracle import make_problem
from neutron_qae.runners import (
    IONQ_RUNS_FILE,
    MAX_RECORDS_BYTES,
    ionq_estimate,
    load_ionq_records,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / IONQ_RUNS_FILE
MODELS = ("Q1", "Q1lite")


def test_committed_ionq_records_file_is_valid():
    assert RUNS.is_file()
    assert os.path.getsize(RUNS) <= MAX_RECORDS_BYTES
    records = load_ionq_records(RUNS)
    for rec in records:
        assert rec["backend_class"].startswith("qiskit_ionq."), rec["backend_class"]
        assert "Fake" not in rec["backend_class"]


def test_ionq_only_estimate_within_4_sigma():
    records = load_ionq_records(RUNS)
    used = [r for r in records if r["sampled"] and r["model"] in MODELS]
    ks = {r["k"] for r in used}
    if 0 not in ks or not any(k >= 1 for k in ks):
        pytest.skip(f"{IONQ_RUNS_FILE} has no sampled Q1/Q1lite records with k = 0 and some k >= 1 yet "
                    f"(plan 04-04 ingests them); sampled ks present: {sorted(ks)}")
    res = ionq_estimate(records, MODELS)
    t1 = make_problem("Q1").reference
    z = (res.a_hat - t1) / res.se
    assert res.n_A == sum(r["shots"] * (2 * r["k"] + 1) for r in used)
    assert abs(res.a_hat - t1) <= 4 * res.se, f"a_hat={res.a_hat:.6f} se={res.se:.2e} z={z:+.2f} T1={t1:.6f}"
