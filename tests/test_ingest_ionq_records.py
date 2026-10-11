"""scripts/ingest_ionq_records.py: verbatim, validated, idempotent paste -> records file (PD-20, T-04-13).

Every output goes under tmp_path; the repo's data/ionq_runs.json is never written.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from ionq_fakes import FakeIonQSimulator

from neutron_qae.oracle import make_problem
from neutron_qae.runners import IONQ_RUNS_FILE, IonQRunner

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ingest_ionq_records.py"
TOO_LARGE = "Circuit size is too large, please try running a smaller circuit (less gates)"


def _line(rec: dict) -> str:
    return "IONQ_RECORD=" + json.dumps(rec, sort_keys=True, separators=(",", ":"))


@pytest.fixture(scope="module")
def fake_records():
    """Fake IonQ records: ideal k = 0, 1, 2 x 1000, a noisy k = 0, and one failed attempt."""
    problem = make_problem("Q1")
    ok = []
    for k in (0, 1, 2):
        fake = FakeIonQSimulator()
        fake.set_options(seed_simulator=k)
        ok.append(IonQRunner(fake, problem, ideal_mode="set_options").run_point(k, 1000))
    noisy_be = FakeIonQSimulator()
    noisy_be.set_options(seed_simulator=7)
    ok.append(IonQRunner(noisy_be, problem, ideal_mode="none").run_point(0, 1000))
    failed = IonQRunner(FakeIonQSimulator(fail=RuntimeError(TOO_LARGE)), problem).run_point(2, 1000)
    assert all(r["accepted"] for r in ok) and not failed["accepted"]
    return ok, failed


@pytest.fixture
def paste(tmp_path, fake_records):
    ok, failed = fake_records
    lines = ["=== Neutron transport QAE (Phase 4) mode=qae model=Q1 backend=simulator k=0 ===",
             "contract: Q1 flag probability ...", _line(ok[0]), "IONQ RUN ACCEPTED",
             "[console] " + _line(ok[1]), "IONQ RUN ACCEPTED", "", _line(failed),
             f"IONQ RUN FAILED: RuntimeError: {TOO_LARGE}", "  " + _line(ok[2]) + "  ", _line(ok[3]),
             "IONQ RUN ACCEPTED"]
    p = tmp_path / "paste.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _ingest(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=ROOT, capture_output=True, check=False,
                          text=True, timeout=120)


def test_ingest_stores_records_verbatim(tmp_path, paste, fake_records):
    ok, _ = fake_records
    out = tmp_path / "runs.json"
    r = _ingest(paste, "--out", out, "--allow-fake")
    assert r.returncode == 0, r.stderr
    stored = json.loads(out.read_text(encoding="utf-8"))
    assert len(stored) == 4
    parsed = [json.loads(_line(rec).split("=", 1)[1]) for rec in ok]
    for rec in parsed:
        assert rec in stored
    for rec in stored:
        assert rec in parsed
    stamps = [rec["timestamp"] for rec in stored]
    assert stamps == sorted(stamps)
    assert "FAILED ATTEMPT model=Q1 k=2 error=RuntimeError: " + TOO_LARGE in r.stdout
    assert "INGESTED 4 new, 0 duplicate, 1 failed attempt(s); 4 records (3 sampled)" in r.stdout
    assert "IONQ ESTIMATE a=" in r.stdout and "N_A=9000" in r.stdout, r.stdout


def test_ingest_is_idempotent(tmp_path, paste):
    out = tmp_path / "runs.json"
    assert _ingest(paste, "--out", out, "--allow-fake").returncode == 0
    before = out.read_bytes()
    r = _ingest(paste, "--out", out, "--allow-fake")
    assert r.returncode == 0, r.stderr
    assert "INGESTED 0 new, 4 duplicate" in r.stdout
    assert out.read_bytes() == before


def test_ingest_rejects_malformed_and_tampered(tmp_path, paste, fake_records):
    ok, _ = fake_records
    out = tmp_path / "runs.json"
    assert _ingest(paste, "--out", out, "--allow-fake").returncode == 0
    before = out.read_bytes()
    truncated = tmp_path / "truncated.txt"
    truncated.write_text("noise\n" + _line(ok[1])[:-40] + "\n", encoding="utf-8")
    r = _ingest(truncated, "--out", out, "--allow-fake")
    assert r.returncode != 0 and "line 2" in r.stderr, r.stderr
    assert out.read_bytes() == before
    tampered_rec = dict(ok[1], hits=ok[1]["hits"] - 1, timestamp="2026-10-11T09:00:00+00:00")
    tampered = tmp_path / "tampered.txt"
    tampered.write_text(_line(tampered_rec) + "\n", encoding="utf-8")
    r = _ingest(tampered, "--out", out, "--allow-fake")
    assert r.returncode != 0 and "hits" in r.stderr, r.stderr
    assert out.read_bytes() == before


def test_ingest_requires_real_ionq_backend(tmp_path, paste):
    out = tmp_path / "runs.json"
    r = _ingest(paste, "--out", out)
    assert r.returncode != 0
    assert "not a real qiskit-ionq backend" in r.stderr, r.stderr
    assert not out.exists()


def test_allow_fake_never_targets_repo_data(paste):
    repo_file = ROOT / IONQ_RUNS_FILE
    before = repo_file.read_bytes()
    r = _ingest(paste, "--out", repo_file, "--allow-fake")
    assert r.returncode != 0
    assert "--allow-fake never writes" in r.stderr, r.stderr
    assert repo_file.read_bytes() == before


def test_conflicting_duplicate_is_rejected(tmp_path, paste, fake_records):
    ok, _ = fake_records
    out = tmp_path / "runs.json"
    assert _ingest(paste, "--out", out, "--allow-fake").returncode == 0
    before = out.read_bytes()
    conflicting = dict(ok[0], run_s=(ok[0]["run_s"] or 0) + 1.0)   # same key, still a valid record
    p = tmp_path / "conflict.txt"
    p.write_text(_line(conflicting) + "\n", encoding="utf-8")
    r = _ingest(p, "--out", out, "--allow-fake")
    assert r.returncode != 0 and "already stored" in r.stderr, r.stderr
    assert out.read_bytes() == before
