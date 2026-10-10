"""PLAT-02 local mirror: main.main() runs end-to-end with an injected BasicSimulator."""
import os
from pathlib import Path

import pytest
from qiskit.providers.basic_provider import BasicSimulator  # tests are allow-listed

ROOT = Path(__file__).resolve().parents[1]


def test_main_runs_with_injected_basic_simulator(monkeypatch):
    monkeypatch.chdir(ROOT)                     # Qollab: project root is the cwd
    import main as entry
    monkeypatch.setattr(entry, "backend", BasicSimulator(), raising=False)
    report = entry.main(shots=200, ghz_qubits=4, ideal_mode="none", perf_qubits=4)
    assert report["toy"]["accepted"]
    assert report["toy"]["ghz_off_ideal_fraction"] == 0.0     # ideal simulator
    assert report["toy"]["ones_fraction"] == 1.0
    assert report["runtime"]["data_file_literal_path"].startswith("data file")


def test_package_imports_without_qiskit_extras():
    import neutron_qae.smoke  # noqa: F401
    assert os.path.isfile(ROOT / "neutron_qae" / "smoke.py")


@pytest.mark.parametrize("mode", ["none", "kwarg"])
def test_ionq_like_backend_sends_exactly_one_job(monkeypatch, mode):
    """PLAT-04: on an IonQ backend one main() call sends exactly one backend.run call
    (two circuits in one job) and the perf probe is skipped. "set_options" is not exercised
    here because BasicSimulator rejects that option; plan 01-03 exercises it on Qollab."""
    calls = {"run": 0}

    class FakeIonQSimulator(BasicSimulator):
        def run(self, run_input, **options):
            calls["run"] += 1
            return super().run(run_input, **options)

    FakeIonQSimulator.__module__ = "qiskit_ionq.ionq_backend"

    monkeypatch.chdir(ROOT)
    import main as entry
    monkeypatch.setattr(entry, "backend", FakeIonQSimulator(), raising=False)
    report = entry.main(shots=50, ghz_qubits=3, ideal_mode=mode, perf_qubits=4)
    assert calls["run"] == 1
    assert report["backend"]["is_ionq"] is True
    assert report["toy"]["accepted"] is True
    assert "skipped" in report["perf"]
