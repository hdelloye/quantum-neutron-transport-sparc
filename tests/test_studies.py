"""Committed-artifact science gates and helper edges for the 05-02 studies (PD-27, PD-28, PD-29).

Exit histograms (ANLY-02): matched 1e6-sample classical lattice MC vs Q1 direct sampling on Aer,
judged by chi-square sums only (never per-row z-scores), labelled circuit validation.

These tests read the committed data/ files only; they never run a sweep.
"""
import itertools
import math
from pathlib import Path

import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from neutron_qae import analysis, artifacts, figures
from neutron_qae.exact import exit_row_distribution_k1
from neutron_qae.kernels import build_kernels
from neutron_qae.problem import sparc_first_wall

ROOT = Path(__file__).resolve().parents[1]
LABEL = "circuit validation, not speedup evidence"


def _load(kind):
    return artifacts.load_artifact(ROOT / artifacts.ARTIFACTS[kind][0], kind)


_KERNELS = {}


def _kernels(model="transport_corrected", width=10.0):
    """Cached kernels per (model, wall): built once per test session."""
    key = (model, float(width))
    if key not in _KERNELS:
        _KERNELS[key] = build_kernels(sparc_first_wall(model, width_x=float(width)))
    return _KERNELS[key]


@pytest.fixture(scope="module")
def histograms():
    return _load("exit_histograms")


# ---------------------------------------------------------------- exit histograms (ANLY-02)

def test_exit_histograms_agree(histograms):
    d = histograms
    assert d["profile"] == "full"
    r = d["results"]
    cl, q = r["classical"], r["quantum"]
    assert d["parameters"]["shots"] == cl["shots"] == q["shots"] == 1_000_000
    for key in ("classical_vs_quantum", "classical_vs_exact", "quantum_vs_exact"):
        c = r["chi2"][key]
        assert c["dof"] == 16, (key, c)
        assert c["bound"] == pytest.approx(16 + 5 * math.sqrt(32), abs=1e-12)
        assert c["value"] < c["bound"], (key, c)
    assert q["outside_support"] == 0 and q["flag_mismatch"] == 0, q
    assert sum(q["row_counts"]) == q["flag_hits"]
    assert sum(cl["row_counts"]) == cl["shots"] - cl["no_back_exit"] == cl["transmitted"]
    exact_rows = exit_row_distribution_k1(_kernels())
    assert np.max(np.abs(np.asarray(r["exact"]["row_probabilities"]) - exact_rows)) <= 1e-15
    # chi-square values are recomputable from the stored counts (sums only, no per-row z-scores)
    c_cat = cl["row_counts"] + [cl["no_back_exit"]]
    q_cat = q["row_counts"] + [q["no_back_exit"]]
    probs = list(r["exact"]["row_probabilities"]) + [r["exact"]["no_back_exit_probability"]]
    assert analysis.chi2_two_sample(c_cat, q_cat)["value"] == pytest.approx(
        r["chi2"]["classical_vs_quantum"]["value"], rel=1e-12)
    assert analysis.chi2_goodness(q_cat, probs)["value"] == pytest.approx(
        r["chi2"]["quantum_vs_exact"]["value"], rel=1e-12)


def test_exit_histogram_is_labelled_validation(histograms):
    import matplotlib.pyplot as plt

    assert histograms["results"]["label"] == LABEL
    fig = figures.render_exit_histograms(histograms)
    try:
        assert LABEL in fig.axes[0].get_title()
    finally:
        plt.close(fig)


def test_chi2_helpers():
    a = [5, 0, 7, 3]
    two = analysis.chi2_two_sample(a, a)
    assert two["value"] == 0.0 and two["dof"] == 2          # the empty category is skipped
    assert analysis.chi2_goodness([10, 20, 30, 40], [0.1, 0.2, 0.3, 0.4])["value"] == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(ValueError, match="equal totals"):
        analysis.chi2_two_sample([1, 2, 3], [1, 2, 4])
    with pytest.raises(ValueError, match="probability 0"):
        analysis.chi2_goodness([1, 2, 3], [0.5, 0.5, 0.0])
    with pytest.raises(ValueError, match="sum to 1"):
        analysis.chi2_goodness([1, 2, 3], [0.5, 0.3, 0.1])
    assert analysis.chi2_bound(16) == pytest.approx(16 + 5 * math.sqrt(32), abs=1e-12)
    with pytest.raises(ValueError):
        analysis.chi2_bound(0)


def test_histogram_validator_rejects_bad_label_and_unmatched_shots(histograms):
    import copy

    bad = copy.deepcopy(histograms)
    bad["results"]["label"] = "speedup evidence"
    with pytest.raises(ValueError, match="results.label"):
        artifacts.validate_artifact(bad)
    bad = copy.deepcopy(histograms)
    bad["results"]["quantum"]["shots"] = 999_999
    with pytest.raises(ValueError, match="results.quantum.shots"):
        artifacts.validate_artifact(bad)


# ---------------------------------------------------------------- truncation bias (ANLY-03)

@pytest.fixture(scope="module")
def truncation():
    return _load("truncation_bias")


def test_truncation_bias_disclosed(truncation):
    from neutron_qae.exact import transmission_within

    d = truncation
    assert d["profile"] == "full"
    assert d["parameters"]["histories_per_case"] == 20_000_000
    cases = d["results"]["cases"]
    assert [(c["model"], c["width_cm"]) for c in cases] == [
        ("transport_corrected", 6.0), ("transport_corrected", 10.0), ("transport_corrected", 15.0),
        ("transport_corrected", 20.0), ("transport_corrected", 30.0), ("isotropic_raw", 10.0)]
    for c in cases:
        k = _kernels(c["model"], c["width_cm"])
        assert abs(c["T0"] - transmission_within(k, 0)) <= 1e-15, c
        assert abs(c["T1"] - transmission_within(k, 1)) <= 1e-15, c
        assert abs(c["within0"] - c["T0"]) / c["within0_se"] < 4, c
        assert abs(c["within1"] - c["T1"]) / c["within1_se"] < 4, c
    tc = [c for c in cases if c["model"] == "transport_corrected"]
    widths = [c["width_cm"] for c in tc]
    assert widths == sorted(widths) and len(set(widths)) == len(widths)
    for c in tc:
        assert c["bias_z"] >= 3, c
        assert c["coverage"] >= 0.98, c
    c10 = next(c for c in tc if c["width_cm"] == 10.0)
    assert 0.995 <= c10["coverage"] <= 0.999, c10
    iso = [c for c in cases if c["model"] == "isotropic_raw"]
    assert len(iso) == 1 and 0.88 <= iso[0]["coverage"] <= 0.92, iso


def test_truncation_never_equates_full_with_T1(truncation):
    import copy

    for c in truncation["results"]["cases"]:
        if c["model"] != "transport_corrected":
            continue
        assert c["bias"] == c["T_full"] - c["T1"]
        assert c["bias"] > 0 and c["T_full"] != c["T1"], c
        assert c["coverage"] < 1.0, c
    bad = copy.deepcopy(truncation)
    bad["results"]["cases"][1]["bias"] = 0.0          # pretending T_full == T1 is rejected
    with pytest.raises(ValueError, match="bias"):
        artifacts.validate_artifact(bad)
    bad = copy.deepcopy(truncation)
    bad["results"]["cases"][1]["coverage"] = 1.0
    with pytest.raises(ValueError, match="coverage"):
        artifacts.validate_artifact(bad)


def test_artifact_model_literals_match_problem():
    from neutron_qae.problem import MODELS

    assert artifacts.CROSS_SECTION_MODELS == tuple(MODELS)


# ---------------------------------------------------------------- wall thickness (ANLY-04)

@pytest.fixture(scope="module")
def thickness():
    return _load("thickness_study")


def test_thickness_ratio_grows_as_transmission_falls(thickness):
    d = thickness
    assert d["profile"] == "full"
    walls = d["results"]["walls"]
    assert [w["width_cm"] for w in walls] == [6.0, 10.0, 15.0, 20.0, 30.0]
    t1 = [w["T1"] for w in walls]
    assert all(b < a for a, b in itertools.pairwise(t1)), t1
    eps = d["parameters"]["target_rel_rmse"]
    assert eps == 0.01
    ratios = []
    for w in walls:
        tr = w["target_rel"]
        assert tr["bracketed"] is True, w["width_cm"]
        assert w["contract_abs_diff"] <= 1e-12
        assert tr["rmse"] == pytest.approx(eps * w["T1"], rel=1e-15)
        theory = (1 - w["T1"]) / (w["T1"] * eps ** 2)
        assert tr["n_classical_theory"] == pytest.approx(theory, rel=1e-12)
        assert theory / 1.5 <= tr["n_classical"] <= 1.5 * theory, (w["width_cm"], tr)
        c, m = w["series"]["classical_lattice"], w["series"]["mlae_analytic"]
        assert analysis.cost_at_target(c["cost"], c["rmse"], tr["rmse"]) == pytest.approx(tr["n_classical"], rel=1e-12)
        assert analysis.cost_at_target(m["cost"], m["rmse"], tr["rmse"]) == pytest.approx(tr["n_mlae"], rel=1e-12)
        ratios.append(tr["ratio"])
    assert all(b > a for a, b in itertools.pairwise(ratios)), ratios
    assert ratios[-1] / ratios[0] >= 4, ratios
    assert d["results"]["trend"]["ratio_increases_as_T1_falls"] is True


def test_thickness_absolute_target_disclosed(thickness):
    walls = thickness["results"]["walls"]
    ab = [w["target_abs"] for w in walls]
    assert all(t["bracketed"] for t in ab), ab
    assert all(t["rmse"] == thickness["parameters"]["target_abs_rmse"] == 1e-3 for t in ab)
    assert ab[-1]["ratio"] < ab[0]["ratio"], [t["ratio"] for t in ab]
    notes = " ".join(thickness["notes"]).lower()
    assert "relative" in notes and "absolute" in notes


def test_check_transmission_boundary():
    from neutron_qae.exact import transmission_within

    assert analysis.check_transmission(1e-3, 1_000_000) == 1e-3          # 1000 events exactly: accepted
    for t1, n in ((0.999999e-3, 1_000_000), (0.0, 1e6), (float("nan"), 1e6), (-0.1, 1e6), (1.0, 1e6)):
        with pytest.raises(ValueError):
            analysis.check_transmission(t1, n)
    t50 = transmission_within(_kernels("transport_corrected", 50.0), 1)
    t40 = transmission_within(_kernels("transport_corrected", 40.0), 1)
    with pytest.raises(ValueError, match="1000"):
        analysis.check_transmission(t50, 1_000_000)
    assert analysis.check_transmission(t40, 1_000_000) == t40


def test_thickness_script_refuses_underflow_wall(tmp_path, monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    monkeypatch.chdir(ROOT)
    import sweep_thickness

    rc = sweep_thickness.main(["--profile", "quick", "--widths", "10", "50", "--out-dir", str(tmp_path)])
    out = capsys.readouterr()
    assert rc == 2
    assert "50 cm" in out.err + out.out
    assert list(tmp_path.iterdir()) == []
