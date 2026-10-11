"""Helper and loader edges (ANLY-05 probes, PD-24, PD-30, PD-31): fits, target crossing, series
guards, size boundary, NaN/Infinity, missing or bool seed, duplicates, empty series, dpi bounds,
atomic writes and the quick profile with null Aer and IonQ. Micro configurations only.
"""
import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

from neutron_qae import analysis, artifacts
from neutron_qae.oracle import make_problem

ROOT = Path(__file__).resolve().parents[1]
SCALING = ROOT / artifacts.SCALING_FILE


@pytest.fixture(scope="module")
def doc():
    return artifacts.load_artifact(SCALING, "scaling_rmse")


def _raises_naming(field, fn, *args, **kwargs):
    with pytest.raises(ValueError) as exc:
        fn(*args, **kwargs)
    assert field in str(exc.value), (field, str(exc.value))


# ---------------------------------------------------------------- fits and targets

def test_loglog_fit_recovers_power_law():
    cost = [10, 100, 1000, 10000]
    fit = analysis.loglog_fit(cost, [3 * c ** -0.5 for c in cost])
    assert fit["slope"] == pytest.approx(-0.5, abs=1e-12)
    assert fit["intercept"] == pytest.approx(math.log10(3), abs=1e-12)
    assert fit["slope_se"] < 1e-12
    assert (fit["points"], fit["cost_min"], fit["cost_max"]) == (4, 10, 10000)


@pytest.mark.parametrize("cost, rmse", [
    ([10, 100], [0.1, 0.01]),                         # 2 points
    ([100, 100, 1000], [0.1, 0.05, 0.01]),            # duplicate cost
    ([1000, 100, 10], [0.01, 0.05, 0.1]),             # descending cost
    ([10, 100, 1000], [0.1, 0.0, 0.01]),              # zero rmse
    ([10, 100, 1000], [0.1, -0.05, 0.01]),            # negative rmse
    ([10, 100, 1000], [0.1, float("nan"), 0.01]),     # NaN
])
def test_loglog_fit_rejects_bad_input(cost, rmse):
    with pytest.raises(ValueError):
        analysis.loglog_fit(cost, rmse)


def test_cost_at_target_cases():
    cost, rmse = [100, 1000, 10000], [0.1, 0.01, 0.001]
    # between points: on this exact power law, target 0.003 sits at cost 10^(log10(1000) + log10(0.01/0.003))
    want = 10 ** (3 + math.log10(0.01 / 0.003))
    assert analysis.cost_at_target(cost, rmse, 0.003) == pytest.approx(want, rel=1e-9)
    assert analysis.cost_at_target(cost, rmse, 0.01) == 1000.0                 # exact hit
    assert analysis.cost_at_target(cost, rmse, 0.2) is None                    # first point already below
    assert analysis.cost_at_target(cost, rmse, 0.0001) is None                 # never reached
    # non-monotone: the first crossing of 0.02 is between 100 and 1000, not after the bump
    first = analysis.cost_at_target([100, 1000, 10000, 100000], [0.1, 0.01, 0.05, 0.001], 0.02)
    assert 100 < first < 1000
    with pytest.raises(ValueError):
        analysis.cost_at_target([100], [0.1], 0.01)
    with pytest.raises(ValueError):
        analysis.cost_at_target([1000, 100], [0.1, 0.01], 0.05)
    with pytest.raises(ValueError):
        analysis.cost_at_target([100, 1000], [0.1, 0.0], 0.05)
    with pytest.raises(ValueError):
        analysis.cost_at_target(cost, rmse, 0.0)


# ---------------------------------------------------------------- series

def test_summarize_errors_and_reps_guard():
    s = analysis.summarize_errors([0.1, -0.1, 0.2, -0.2])
    assert s["rmse"] == pytest.approx(math.sqrt(0.025), abs=1e-15)
    assert s["mean_error"] == pytest.approx(0.0, abs=1e-15)
    a = np.abs([0.1, -0.1, 0.2, -0.2])
    assert s["abs_err_q16"] == pytest.approx(np.quantile(a, 0.16))
    assert s["abs_err_q84"] == pytest.approx(np.quantile(a, 0.84))
    with pytest.raises(ValueError):
        analysis.summarize_errors([0.1])
    with pytest.raises(ValueError):
        analysis.summarize_errors([0.1, float("inf")])
    p = make_problem("Q0")
    with pytest.raises(ValueError):
        analysis.classical_rmse_series(p.kernels, p.reference, (10, 100), 1, np.random.SeedSequence(1))
    with pytest.raises(ValueError):
        analysis.mlae_rmse_series(p.p, p.reference, 2, 10, 0, np.random.SeedSequence(1))
    with pytest.raises(ValueError):
        analysis.backend_rmse_series(None, p, p.reference, 2, 10, 1, 7)


def test_micro_series_are_deterministic():
    q1 = make_problem("Q1")
    a = analysis.classical_rmse_series(q1.kernels, q1.reference, (10, 100), 3, np.random.SeedSequence(5))
    b = analysis.classical_rmse_series(q1.kernels, q1.reference, (10, 100), 3, np.random.SeedSequence(5))
    assert a == b
    assert a["cost"] == [10, 100] and all(r > 0 for r in a["rmse"])
    m = analysis.mlae_rmse_series(q1.p, q1.reference, 2, 10, 3, np.random.SeedSequence(5))
    assert m["cost"] == [10, 40] and m["M"] == [1, 2] and m["runner"] == "analytic"
    aer_mod = pytest.importorskip("qiskit_aer")
    q0 = make_problem("Q0")
    s = analysis.backend_rmse_series(aer_mod.AerSimulator(method="statevector"), q0, q0.reference, 2, 10, 3, 7)
    assert s["cost"] == [10, 40] and s["runner"] == "aer" and s["repetitions"] == 3


# ---------------------------------------------------------------- loader and validator

def test_size_cap_boundary(tmp_path):
    text = SCALING.read_text(encoding="utf-8")
    pad = artifacts.MAX_ARTIFACT_BYTES - len(text.encode("utf-8"))
    ok = tmp_path / "ok.json"
    ok.write_text(text + " " * pad, encoding="utf-8")
    assert ok.stat().st_size == 2_000_000
    assert artifacts.load_artifact(ok, "scaling_rmse")["kind"] == "scaling_rmse"
    big = tmp_path / "big.json"
    big.write_text(text + " " * (pad + 1), encoding="utf-8")
    assert big.stat().st_size == 2_000_001
    _raises_naming("2000000", artifacts.load_artifact, big)
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        artifacts.load_artifact(empty)


def _with_token(doc, token, tmp_path):
    d = copy.deepcopy(doc)
    d["results"]["series"]["classical_lattice"]["rmse"][0] = 0.123456789
    text = json.dumps(d, sort_keys=True, indent=1).replace("0.123456789", token)
    path = tmp_path / f"{token.strip('-')}.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_loader_rejects_nan_and_missing_seed(doc, tmp_path):
    for token in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            artifacts.load_artifact(_with_token(doc, token, tmp_path))
    d = copy.deepcopy(doc)
    del d["provenance"]["seed"]
    _raises_naming("provenance.seed", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["provenance"]["seed"] = True
    _raises_naming("provenance.seed", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["schema_version"] = 2
    _raises_naming("schema_version", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["kind"] = "unknown"
    _raises_naming("kind", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["results"]["series"]["mlae_analytic"]["mean_error"][0] = float("nan")
    with pytest.raises(ValueError):
        artifacts.dumps_artifact(d)


def test_validator_rejects_duplicates_and_empty_series(doc):
    d = copy.deepcopy(doc)
    c = d["results"]["series"]["classical_lattice"]["cost"]
    c[1] = c[0]
    _raises_naming("classical_lattice.cost", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["results"]["series"]["mlae_analytic"]["rmse"] = []
    _raises_naming("mlae_analytic.rmse", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    aer = d["results"]["series"]["mlae_aer"]
    for key in ("cost", "rmse", "mean_error", "abs_err_q16", "abs_err_q84", "M"):
        aer[key] = aer[key][:3]
    aer["fit"].update(points=2, cost_min=aer["cost"][1], cost_max=aer["cost"][2])
    d["parameters"]["aer_M_max"] = 3
    _raises_naming("mlae_aer.fit.points", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["results"]["series"]["mlae_aer"] = None
    _raises_naming("mlae_aer", artifacts.validate_artifact, d)
    d = copy.deepcopy(doc)
    d["results"]["ionq_marker"]["in_fit"] = True
    _raises_naming("ionq_marker.in_fit", artifacts.validate_artifact, d)


def _quick(doc):
    d = copy.deepcopy(doc)
    d["profile"] = "quick"
    d["results"]["series"]["mlae_aer"] = None
    d["parameters"]["aer_M_max"] = None
    d["results"]["ionq_marker"] = None
    return d


def test_write_artifact_is_atomic(doc, tmp_path):
    out = tmp_path / "a.json"
    n = artifacts.write_artifact(doc, out)
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]
    assert out.stat().st_size == n
    bad = copy.deepcopy(doc)
    bad["schema"] = "other"
    with pytest.raises(ValueError):
        artifacts.write_artifact(bad, tmp_path / "b.json")
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]


# ---------------------------------------------------------------- rendering

def test_quick_profile_with_null_aer_renders(doc):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from neutron_qae import figures

    d = artifacts.validate_artifact(_quick(doc), "scaling_rmse")
    fig = figures.render_scaling(d)
    try:
        assert fig.axes
    finally:
        plt.close(fig)


def test_render_dpi_bounds(doc, tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from neutron_qae import figures

    small = tmp_path / "small.json"
    artifacts.write_artifact(_quick(doc), small)     # quick doc: fewer artists, faster renders
    for dpi in (50, 200):
        info = figures.render_file("scaling_rmse", small, tmp_path / f"f{dpi}.png", dpi=dpi)
        assert info["width"] == round(figures.FIGSIZE_ONE[0] * dpi), (dpi, info)
    for dpi in (49, 201, True):
        with pytest.raises(ValueError):
            figures.render_file("scaling_rmse", small, tmp_path / "never.png", dpi=dpi)
    assert not (tmp_path / "never.png").exists()
