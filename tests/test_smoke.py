"""PLAT-02 local mirror: main.main(mode="smoke") runs the Phase 1 smoke test end-to-end with an
injected BasicSimulator (GHZ on 6 qubits and the 12-qubit perf probe are fixed since Phase 4)."""
import os
from pathlib import Path

import pytest
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator  # tests are allow-listed

ROOT = Path(__file__).resolve().parents[1]


def test_main_runs_with_injected_basic_simulator(monkeypatch):
    monkeypatch.chdir(ROOT)                     # Qollab: project root is the cwd
    import main as entry
    monkeypatch.setattr(entry, "backend", BasicSimulator(), raising=False)
    report = entry.main(mode="smoke", shots=200, ideal_mode="none")
    assert report["toy"]["accepted"]
    assert report["toy"]["ghz_off_ideal_fraction"] == 0.0     # ideal simulator
    assert report["toy"]["circuits_per_job"] == 1
    assert set(report["toy"]["counts"]) <= {"000000", "111111"}  # one circuit -> one counts dict
    assert report["mode"] == "smoke"
    assert report["perf"]["qubits"] == 12
    assert report["runtime"]["data_file_literal_path"].startswith("data file")


def test_package_imports_without_qiskit_extras():
    import neutron_qae.smoke  # noqa: F401
    assert os.path.isfile(ROOT / "neutron_qae" / "smoke.py")


@pytest.mark.parametrize("mode", ["none", "kwarg"])
def test_ionq_like_backend_sends_exactly_one_job(monkeypatch, mode):
    """PLAT-04: on an IonQ backend one main() call sends exactly one backend.run call
    carrying ONE bare QuantumCircuit, and the perf probe is skipped. Qollab's IonQ proxy
    accepts only job type ionq.circuit.v1; qiskit-ionq turns any list or tuple (even of
    length one) into ionq.multi-circuit.v1, which Qollab rejects with HTTP 400 (observed
    in plan 01-03 run R4). The fake mirrors that rejection. "set_options" is not exercised
    here because BasicSimulator rejects that option; plan 01-03 exercises it on Qollab."""
    calls = {"run": 0, "inputs": []}

    class FakeIonQSimulator(BasicSimulator):
        def run(self, run_input, **options):
            calls["run"] += 1
            calls["inputs"].append(run_input)
            if isinstance(run_input, (list, tuple)):
                raise RuntimeError("Only job type ionq.circuit.v1 is supported")  # Qollab's 400
            return super().run(run_input, **options)

    FakeIonQSimulator.__module__ = "qiskit_ionq.ionq_backend"

    monkeypatch.chdir(ROOT)
    import main as entry
    monkeypatch.setattr(entry, "backend", FakeIonQSimulator(), raising=False)
    report = entry.main(mode="smoke", shots=50, ideal_mode=mode)
    assert calls["run"] == 1
    assert len(calls["inputs"]) == 1
    assert isinstance(calls["inputs"][0], QuantumCircuit)
    assert not isinstance(calls["inputs"][0], (list, tuple))
    assert report["backend"]["is_ionq"] is True
    assert report["toy"]["accepted"] is True, report["toy"]["error"]
    assert report["toy"]["circuits_per_job"] == 1
    assert report["toy"]["n"] == 6
    assert "skipped" in report["perf"]
