"""Phase 6 quick mode (DOCS-01, PD-33, PD-35): main() with an untouched Run settings form.

Default tests stay cheap (model Q0, at most one rendered figure); the four-figure run is `slow`.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from ionq_fakes import FakeIonQSimulator  # noqa: E402
from qiskit import QuantumCircuit  # noqa: E402
from qiskit.providers.basic_provider import BasicSimulator  # noqa: E402 - tests are allow-listed

from neutron_qae import artifacts, runners  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _entry(monkeypatch, be, figure_dir, quick_figures=None):
    """Import main.py the way Qollab runs it; FIGURE_DIR and QUICK_FIGURES patched for the test."""
    monkeypatch.chdir(ROOT)
    import main as entry
    monkeypatch.setattr(entry, "backend", be, raising=False)
    monkeypatch.setattr(entry, "FIGURE_DIR", str(figure_dir))
    if quick_figures is not None:
        monkeypatch.setattr(entry, "QUICK_FIGURES", tuple(quick_figures))
    return entry


def _histogram_only(entry):
    return tuple(item for item in entry.QUICK_FIGURES if item[0] == "exit_histograms")


def _report_line(out):
    rep = [ln for ln in out.splitlines() if ln.startswith("QUICK_REPORT=")]
    assert len(rep) == 1, out[-800:]
    return json.loads(rep[0].split("=", 1)[1])


def test_quick_is_the_default_mode(monkeypatch, capsys, tmp_path):
    be = BasicSimulator()
    be.set_options(seed_simulator=1)
    monkeypatch.chdir(ROOT)
    import main as entry
    entry = _entry(monkeypatch, be, tmp_path, _histogram_only(entry))
    report = entry.main(shots=200, model="Q0")
    quick = report["quick"]
    assert report["mode"] == "quick" and quick["mode"] == "quick"
    live = quick["live"]
    assert live["schedule"] == [0, 1, 2] and live["n_A"] == 1800 and live["shots_per_power"] == 200
    assert live["contract"]["abs_diff"] <= 1e-12
    out = capsys.readouterr().out
    assert _report_line(out) == quick
    pngs = sorted(tmp_path.iterdir())
    assert [p.name for p in pngs] == ["quick_fig_exit_histograms.png"]
    assert pngs[0].read_bytes()[:8] == PNG_SIGNATURE
    assert artifacts.png_dimensions(pngs[0]) == (630, 414)
    assert quick["figures_ok"] == 1
    assert out.splitlines()[-1] == "QUICK MODE OK"
    # IonQ caveat (folded in to keep the suite cheap): same line as the estimate, committed data
    committed = runners.ionq_estimate(runners.load_ionq_records(ROOT / runners.IONQ_RUNS_FILE))
    ion = [ln for ln in out.splitlines() if ln.startswith("IonQ Forte 1 records")]
    if committed is not None:
        assert len(ion) == 1 and "CAVEAT:" in ion[0] and "6.4 sigma" in ion[0], ion
        assert quick["ionq_records"]["caveat"] in ion[0]


def test_quick_on_ionq_sends_one_bare_circuit(monkeypatch, capsys, tmp_path):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=3)
    entry = _entry(monkeypatch, fake, tmp_path, ())
    report = entry.main(model="Q0")
    assert len(fake.calls) == 1
    sent = fake.calls[0]
    assert isinstance(sent, QuantumCircuit) and sent.num_qubits == 5
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert sum(ln.startswith("IONQ_RECORD=") for ln in lines) == 1
    assert "IONQ RUN ACCEPTED" in lines
    assert report["quick"]["live"]["accepted"] is True
    assert _report_line(out) == report["quick"]
    assert lines[-1] == "QUICK MODE OK"


# ---- Task 3: figure-failure isolation, reachability, slow four-figure timing ----

def test_corrupt_artifact_gives_incomplete_not_a_crash(monkeypatch, capsys, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    be = BasicSimulator()
    be.set_options(seed_simulator=1)
    entry = _entry(monkeypatch, be, tmp_path / "figs",
                   [("exit_histograms", str(bad), "quick_fig_exit_histograms.png")])
    report = entry.main(shots=50, model="Q0")
    (fig,) = report["quick"]["figures"]
    assert fig["ok"] is False and fig["error"].startswith("ValueError"), fig
    last = capsys.readouterr().out.splitlines()[-1]
    assert last.startswith("QUICK MODE INCOMPLETE: live run ok, 0 of 1 figures rendered"), last


def test_one_failing_renderer_does_not_stop_the_others(monkeypatch, capsys, tmp_path):
    import matplotlib.pyplot as plt

    from neutron_qae import figures

    be = BasicSimulator()
    be.set_options(seed_simulator=1)
    monkeypatch.chdir(ROOT)
    import main as entry
    items = [it for it in entry.QUICK_FIGURES if it[0] in ("scaling_rmse", "exit_histograms")]
    entry = _entry(monkeypatch, be, tmp_path, items)

    def broken(doc):
        plt.subplots()                              # a figure is open when the renderer fails
        raise RuntimeError("renderer broke")

    monkeypatch.setitem(figures.RENDERERS, "scaling_rmse", broken)
    before = len(plt.get_fignums())
    report = entry.main(shots=50, model="Q0")
    figs = {f["kind"]: f for f in report["quick"]["figures"]}
    assert figs["scaling_rmse"]["ok"] is False and figs["scaling_rmse"]["error"].startswith("RuntimeError")
    assert figs["exit_histograms"]["ok"] is True
    last = capsys.readouterr().out.splitlines()[-1]
    assert last == "QUICK MODE INCOMPLETE: live run ok, 1 of 2 figures rendered", last
    assert [p.name for p in tmp_path.iterdir()] == ["quick_fig_exit_histograms.png"]
    assert len(plt.get_fignums()) <= before + 1     # the broken renderer's stray figure at most


def test_figures_module_is_reachable_and_imports_stay_clean():
    import compliance_checks as cc

    paths, _ = cc.reachable_modules(ROOT)
    assert ROOT / "neutron_qae" / "figures.py" in {Path(p).resolve() for p in paths}
    assert cc.forbidden_imports(ROOT) == set()


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("NEUTRON_QAE_SLOW") != "1",
                    reason="four-figure quick run; run with NEUTRON_QAE_SLOW=1 -m slow")
def test_quick_full_defaults_four_figures_under_5s(monkeypatch, capsys, tmp_path):
    be = BasicSimulator()
    be.set_options(seed_simulator=2026)
    entry = _entry(monkeypatch, be, tmp_path)
    t0 = time.perf_counter()
    report = entry.main()
    dt = time.perf_counter() - t0
    quick = report["quick"]
    assert quick["live"]["hits"] == [262, 1000, 277] and quick["figures_ok"] == 4
    sizes = [artifacts.png_dimensions(tmp_path / name) for _, _, name in entry.QUICK_FIGURES]
    assert sizes == [(630, 414), (630, 414), (810, 360), (810, 360)], sizes
    assert capsys.readouterr().out.splitlines()[-1] == "QUICK MODE OK"
    assert dt < 5.0, dt
