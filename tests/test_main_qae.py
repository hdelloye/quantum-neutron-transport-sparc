"""Phase 4 Qollab entry (QAE-02, QC-06, PD-19, PD-23): main() in QAE mode on an injected backend.

Built-in path: one list job over k = 0, 1, 2, 4, the vendored MLAE and a QAE_REPORT= line.
IonQ path (tests/ionq_fakes.FakeIonQSimulator): exactly one bare circuit, one IONQ_RECORD= line.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from ionq_fakes import FakeIonQSimulator
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator  # tests are allow-listed

from neutron_qae import runners
from neutron_qae.grover import check_ionq_safe
from neutron_qae.oracle import make_problem
from neutron_qae.runners import IonQRunner, validate_ionq_record

ROOT = Path(__file__).resolve().parents[1]
SIGNATURE = 'def main(mode: str = "qae", k: int = 1, shots: int = 1000, ideal_mode: str = "set_options", model: str = "Q1"):'


def _entry(monkeypatch, be):
    """Import main.py the way Qollab runs it: project root as cwd, `backend` injected as a global."""
    monkeypatch.chdir(ROOT)
    import main as entry
    monkeypatch.setattr(entry, "backend", be, raising=False)
    return entry


def _lines(capsys, prefix):
    out = capsys.readouterr().out
    lines = out.splitlines()
    return out, lines, [ln for ln in lines if ln.startswith(prefix)]


def test_main_signature_is_the_phase4_form():
    lines = [ln for ln in (ROOT / "main.py").read_text(encoding="utf-8").splitlines() if ln.startswith("def main(")]
    assert lines == [SIGNATURE]


def test_main_qae_builtin_seeded(monkeypatch, capsys):
    be = BasicSimulator()
    be.set_options(seed_simulator=2026)
    entry = _entry(monkeypatch, be)
    report = entry.main()
    qae = report["qae"]
    assert report["mode"] == "qae"
    assert report["backend"]["is_ionq"] is False
    assert qae["schedule"] == [0, 1, 2, 4]
    assert qae["hits"] == [262, 1000, 277, 997]
    assert qae["n_A"] == 18000
    assert abs(qae["a_hat"] - 0.245094) < 5e-7, qae["a_hat"]
    assert qae["contract"]["abs_diff"] <= 1e-12
    assert qae["ionq_records"] is None            # the committed data/ionq_runs.json is empty
    out, lines, rep = _lines(capsys, "QAE_REPORT=")
    assert len(rep) == 1, out[-800:]
    assert json.loads(rep[0].split("=", 1)[1]) == qae
    assert lines[-1] == "QAE RUN COMPLETED"
    assert "IonQ records: none yet" in out


def test_main_qae_ionq_sends_one_bare_circuit(monkeypatch, capsys):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=3)
    entry = _entry(monkeypatch, fake)
    report = entry.main(mode="qae", k=1, shots=200, ideal_mode="set_options", model="Q1")
    assert len(fake.calls) == 1
    sent = fake.calls[0]
    assert isinstance(sent, QuantumCircuit) and not isinstance(sent, (list, tuple))
    assert sent.num_qubits == 12 and sent.num_clbits == 12
    check_ionq_safe(sent)
    out, lines, rec_lines = _lines(capsys, "IONQ_RECORD=")
    assert len(rec_lines) == 1, out[-800:]
    rec = validate_ionq_record(json.loads(rec_lines[0].split("=", 1)[1]))
    assert (rec["model"], rec["k"], rec["shots"], rec["n_A"], rec["cx"]) == ("Q1", 1, 200, 600, 1503)
    assert rec["sampled"] is True and rec["noise_model"] == "ideal"
    assert rec == report["ionq"]
    assert "qae" not in report                    # the Built-in list job is never built on IonQ
    assert lines[-1] == "IONQ RUN ACCEPTED"


# ---- Task 2: IonQ protocol edges, PD-23 validation, failures, IonQ records on the Built-in path ----

def _record_line(lines):
    rec_lines = [ln for ln in lines if ln.startswith("IONQ_RECORD=")]
    assert len(rec_lines) == 1, lines[-5:]
    return validate_ionq_record(json.loads(rec_lines[0].split("=", 1)[1]))


def test_ionq_noisy_record_is_unsampled(monkeypatch, capsys):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=5)
    entry = _entry(monkeypatch, fake)
    report = entry.main("qae", 0, 300, "none", "Q1")          # Qollab passes form values positionally
    out, lines, _ = _lines(capsys, "")
    rec = _record_line(lines)
    assert len(fake.calls) == 1
    assert rec["sampled"] is False and rec["noise_model"] == "forte-1" and rec["ideal_mode"] == "none"
    assert report["ionq"]["accepted"] is True
    assert not any(ln.startswith("MLAE") for ln in lines), out
    assert lines[-1] == "IONQ RUN ACCEPTED"


def test_ionq_k0_prints_single_record_estimate(monkeypatch, capsys):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=11)
    entry = _entry(monkeypatch, fake)
    entry.main(mode="qae", k=0, shots=1000, ideal_mode="set_options", model="Q1")
    out, lines, mlae_lines = _lines(capsys, "MLAE (this record alone, k = 0)")
    rec = _record_line(lines)
    assert rec["sampled"] is True and rec["k"] == 0 and rec["n_A"] == 1000
    assert len(mlae_lines) == 1, out
    assert f"hits/shots = {rec['hits']}/1000 = {rec['hits'] / 1000:.6f}, N_A = 1000" in mlae_lines[0]
    assert lines[-1] == "IONQ RUN ACCEPTED"


def test_ionq_q1lite_record(monkeypatch, capsys):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=2)
    entry = _entry(monkeypatch, fake)
    entry.main(mode="qae", k=1, shots=200, ideal_mode="set_options", model="Q1lite")
    _, lines, _ = _lines(capsys, "")
    rec = _record_line(lines)
    assert len(fake.calls) == 1 and fake.calls[0].num_qubits == 8
    assert (rec["model"], rec["qubits"], rec["flag"], rec["cx"]) == ("Q1lite", 8, 7, 399)
    assert {len(key) for key in rec["counts"]} == {8}
    assert lines[-1] == "IONQ RUN ACCEPTED"


@pytest.mark.parametrize("kwargs", [
    {"mode": "bogus"}, {"mode": 1}, {"model": "Q2"}, {"model": "q1"},
    {"k": -1}, {"k": 9}, {"k": True}, {"k": 1.5}, {"k": "1"}, {"k": None},
    {"shots": 1}, {"shots": 10_001}, {"shots": False}, {"shots": 100.5},
    {"ideal_mode": "kwarg"}, {"ideal_mode": "bogus"}, {"ideal_mode": None},
    {"mode": "smoke", "ideal_mode": "bogus"}, {"mode": "smoke", "shots": 0},
], ids=lambda kw: ",".join(f"{k}={v!r}" for k, v in kw.items()))
def test_invalid_form_values_send_no_job(monkeypatch, kwargs):
    fake = FakeIonQSimulator()
    entry = _entry(monkeypatch, fake)
    with pytest.raises(ValueError):
        entry.main(**kwargs)
    assert fake.calls == []


def test_integral_float_form_values_are_accepted(monkeypatch, capsys):
    """Qollab can pass form numbers as floats; k = 1.0 and shots = 100.0 mean 1 and 100."""
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=1)
    entry = _entry(monkeypatch, fake)
    report = entry.main(mode="qae", k=1.0, shots=100.0)
    assert len(fake.calls) == 1
    assert (report["ionq"]["k"], report["ionq"]["shots"]) == (1, 100)
    assert type(report["ionq"]["k"]) is int and type(report["ionq"]["shots"]) is int
    assert capsys.readouterr().out.splitlines()[-1] == "IONQ RUN ACCEPTED"


def test_failed_ionq_submission_is_reported(monkeypatch, capsys):
    fake = FakeIonQSimulator(fail=RuntimeError("Circuit size is too large, please try running a smaller "
                                               "circuit (less gates)"))
    entry = _entry(monkeypatch, fake)
    report = entry.main(mode="qae", k=2, shots=1000)
    assert len(fake.calls) == 1                     # exactly one attempt, no retry
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[-1].startswith("IONQ RUN FAILED: RuntimeError"), lines[-1]
    assert "Circuit size is too large" in lines[-1]
    assert report["ionq"]["accepted"] is False
    assert sum(ln.startswith("IONQ_RECORD=") for ln in lines) == 1


def _fake_record_file(path):
    problem = make_problem("Q1")
    recs = []
    for k in (0, 1, 2):
        fake = FakeIonQSimulator()
        fake.set_options(seed_simulator=k)
        recs.append(IonQRunner(fake, problem).run_point(k, 1000))
    path.write_text(json.dumps(recs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return recs


def test_builtin_prints_ionq_estimate_when_records_exist(monkeypatch, capsys, tmp_path):
    runs = tmp_path / "ionq_runs.json"
    _fake_record_file(runs)
    monkeypatch.setattr(runners, "IONQ_RUNS_FILE", str(runs))
    be = BasicSimulator()
    be.set_options(seed_simulator=1)
    entry = _entry(monkeypatch, be)
    report = entry.main(shots=200)
    ionq = report["qae"]["ionq_records"]
    assert ionq["n_A"] == 9000 and ionq["ks"] == [0, 1, 2] and ionq["models"] == ["Q1"]
    assert abs(ionq["abs_err"] - abs(ionq["a_hat"] - make_problem("Q1").reference)) < 1e-15
    out = capsys.readouterr().out
    assert "IonQ Forte 1 records (ideal, sampled): k=[0, 1, 2] -> a_hat=" in out and "N_A=9000" in out
    assert out.splitlines()[-1] == "QAE RUN COMPLETED"


def test_builtin_survives_corrupt_records_file(monkeypatch, capsys, tmp_path):
    runs = tmp_path / "ionq_runs.json"
    runs.write_text("{", encoding="utf-8")
    monkeypatch.setattr(runners, "IONQ_RUNS_FILE", str(runs))
    be = BasicSimulator()
    be.set_options(seed_simulator=1)
    entry = _entry(monkeypatch, be)
    report = entry.main(shots=100)
    assert "error" in report["qae"]["ionq_records"]
    out = capsys.readouterr().out
    assert "IonQ records: invalid (" in out
    assert out.splitlines()[-1] == "QAE RUN COMPLETED"
