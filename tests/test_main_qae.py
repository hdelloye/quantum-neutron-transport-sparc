"""Phase 4 Qollab entry (QAE-02, QC-06, PD-19, PD-23): main() in QAE mode on an injected backend.

Built-in path: one list job over k = 0, 1, 2, 4, the vendored MLAE and a QAE_REPORT= line.
IonQ path (tests/ionq_fakes.FakeIonQSimulator): exactly one bare circuit, one IONQ_RECORD= line.
"""
from __future__ import annotations

import json
from pathlib import Path

from ionq_fakes import FakeIonQSimulator
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator  # tests are allow-listed

from neutron_qae.grover import check_ionq_safe
from neutron_qae.runners import validate_ionq_record

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
