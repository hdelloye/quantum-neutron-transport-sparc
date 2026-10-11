"""Committed-artifact science gates and helper edges for the 05-02 studies (PD-27, PD-28, PD-29).

Exit histograms (ANLY-02): matched 1e6-sample classical lattice MC vs Q1 direct sampling on Aer,
judged by chi-square sums only (never per-row z-scores), labelled circuit validation.

These tests read the committed data/ files only; they never run a sweep.
"""
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
