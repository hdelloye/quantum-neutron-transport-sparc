"""Committed-artifact gates (PD-24, PD-25, PD-26, PD-30): budgets, schema, provenance, slopes,
Aer cross-check, the honest cost axis, the IonQ marker's exclusion and re-rendering from JSON.

These tests read the committed data/ files only; they never run a sweep.
"""
import ast
import os
import re
import time
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from neutron_qae import analysis, artifacts, figures, mlae

ROOT = Path(__file__).resolve().parents[1]
FULL_N = [100, 215, 464, 1000, 2154, 4642, 10000, 21544, 46416, 100000, 215443, 464159, 1000000]
SHOTS = 300
REPS = 100


def _load(kind):
    return artifacts.load_artifact(ROOT / artifacts.ARTIFACTS[kind][0], kind)


@pytest.fixture(scope="module")
def scaling():
    return _load("scaling_rmse")


def test_registered_artifacts_exist_within_budgets():
    for kind, (json_rel, png_rel) in artifacts.ARTIFACTS.items():
        j, p = ROOT / json_rel, ROOT / png_rel
        assert j.is_file(), json_rel
        assert j.stat().st_size <= artifacts.JSON_BUDGET_BYTES, (json_rel, j.stat().st_size)
        assert p.is_file(), png_rel
        assert p.stat().st_size <= artifacts.PNG_BUDGET_BYTES, (png_rel, p.stat().st_size)
        w, h = artifacts.png_dimensions(p)
        assert 300 <= w <= 1200 and 200 <= h <= 800, (kind, w, h)


def test_artifacts_load_and_are_byte_stable():
    for kind, (json_rel, _) in artifacts.ARTIFACTS.items():
        path = ROOT / json_rel
        doc = artifacts.load_artifact(path, kind)
        assert doc["profile"] == "full", kind
        assert artifacts.dumps_artifact(doc) == path.read_text(encoding="utf-8"), kind


def test_full_profile_provenance():
    for kind, (json_rel, _) in artifacts.ARTIFACTS.items():
        text = (ROOT / json_rel).read_text(encoding="utf-8")
        prov = _load(kind)["provenance"]
        assert type(prov["seed"]) is int and prov["seed"] == 2026, prov["seed"]
        assert re.fullmatch(r"[0-9a-f]{40}", prov["git_head"]), prov["git_head"]
        assert prov["git_dirty"] is False
        assert prov["script"].startswith("scripts/")
        assert prov["created_utc"].endswith("Z")
        assert "/Users/" not in text and "\\Users\\" not in text, kind


def test_headline_slopes_and_cross_check(scaling):
    series = scaling["results"]["series"]
    for name, min_M in (("classical_lattice", None), ("mlae_analytic", 2), ("mlae_aer", 2)):
        s = series[name]
        refit = analysis.fit_series(s, min_M)
        for key in ("slope", "intercept", "slope_se"):
            assert refit[key] == pytest.approx(s["fit"][key], abs=1e-12), (name, key)
        assert refit["points"] == s["fit"]["points"], name
        assert s["repetitions"] == REPS, name
    assert scaling["parameters"]["repetitions"] == REPS
    assert -0.55 <= series["classical_lattice"]["fit"]["slope"] <= -0.45
    assert -1.10 <= series["mlae_analytic"]["fit"]["slope"] <= -0.90
    assert -1.15 <= series["mlae_aer"]["fit"]["slope"] <= -0.85
    assert series["classical_lattice"]["cost"] == FULL_N
    aer, ana = series["mlae_aer"], series["mlae_analytic"]
    assert len(aer["cost"]) >= 3
    by_M = dict(zip(ana["M"], ana["rmse"]))
    ratios = [r / by_M[M] for M, r in zip(aer["M"], aer["rmse"])]
    assert all(0.6 <= q <= 1.6 for q in ratios), ratios


def test_mlae_cost_is_applications_of_A(scaling):
    for name in ("mlae_analytic", "mlae_aer"):
        s = scaling["results"]["series"][name]
        assert s["cost_unit"] == "applications of A"
        for M, cost in zip(s["M"], s["cost"]):
            recs = [mlae.PowerResult(k, SHOTS, 0) for k in mlae.exponential_schedule(M)]
            assert cost == SHOTS * (2 ** M + M - 2) == mlae.n_applications(recs), (name, M, cost)
    assert scaling["results"]["series"]["classical_lattice"]["cost_unit"] == "histories"


def test_ionq_marker_is_labelled_and_never_fitted(scaling):
    m = scaling["results"]["ionq_marker"]
    assert m is not None
    assert m["in_fit"] is False
    assert "execution proof" in m["label"] and "not in any fit" in m["label"]
    assert m["n_A"] == 9000
    assert abs(m["z"] + 6.38) < 0.01, m["z"]


def test_notes_state_sampling_complexity_only():
    for kind in artifacts.ARTIFACTS:
        notes = [n.lower() for n in _load(kind)["notes"]]
        assert any("sampling complexity" in n for n in notes), kind
        for n in notes:
            for hit in re.finditer("speedup", n):
                before = n[max(0, hit.start() - 40):hit.start()]
                assert "no " in before or "not " in before, (kind, n)


# Moved behind `slow` in 05-02 (default suite > 28.5 s with four figures; orchestrator rule): the
# four-figure re-render runs under NEUTRON_QAE_SLOW=1 and as `scripts/render_figures.py --check`;
# tests/test_studies.py::test_exit_histogram_is_labelled_validation stays as the fast smoke render.
@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("NEUTRON_QAE_SLOW") != "1",
                    reason="four-figure DPI-60 re-render; run with NEUTRON_QAE_SLOW=1 -m slow")
def test_figures_render_from_committed_json(tmp_path):
    t0 = time.perf_counter()
    for kind, (json_rel, png_rel) in artifacts.ARTIFACTS.items():
        out = tmp_path / Path(png_rel).name
        info = figures.render_file(kind, ROOT / json_rel, out, dpi=60)
        w, h = artifacts.png_dimensions(out)
        cw, ch = artifacts.png_dimensions(ROOT / png_rel)
        assert (info["width"], info["height"]) == (w, h)
        assert (w, h) == (round(cw * 60 / figures.DEFAULT_DPI), round(ch * 60 / figures.DEFAULT_DPI)), (kind, w, h)
    assert time.perf_counter() - t0 < 5.0


STDLIB_ALLOWED = {"__future__", "json", "math", "numbers", "os", "struct", "tempfile"}
MPL_ALLOWED = {"subplots", "close", "loglog", "plot", "errorbar", "fill_between", "step", "bar", "set_xscale",
               "set_yscale", "set_xlabel", "set_ylabel", "set_title", "legend", "grid", "text", "axhline",
               "set_xticks", "set_xlim", "set_ylim", "tight_layout", "suptitle", "savefig"}


def _tree(rel):
    return ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)


def test_artifacts_module_is_stdlib_only():
    tops = set()
    for node in ast.walk(_tree("neutron_qae/artifacts.py")):
        if isinstance(node, ast.Import):
            tops.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "artifacts.py must not use relative imports"
            tops.add(node.module.split(".")[0])
    assert tops <= STDLIB_ALLOWED, tops - STDLIB_ALLOWED


def test_figures_use_only_long_standing_matplotlib_api():
    tree = _tree("neutron_qae/figures.py")
    receiver = re.compile(r"(plt|fig|ax)[A-Za-z0-9]*")
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name) and receiver.fullmatch(owner.id) and node.func.attr not in MPL_ALLOWED:
                bad.append(f"{owner.id}.{node.func.attr} (line {node.lineno})")
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in {"use", "show"}:
                bad.append(f"{name}() call (line {node.lineno})")
    for node in tree.body:
        if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "matplotlib" for a in node.names):
            bad.append(f"module-level import matplotlib (line {node.lineno})")
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "matplotlib":
            bad.append(f"module-level from matplotlib import (line {node.lineno})")
    assert not bad, bad


def test_package_constructs_no_backend_for_sweeps():
    import compliance_checks

    assert (ROOT / "neutron_qae" / "analysis.py").is_file()
    assert compliance_checks.backend_constructions(ROOT) == []
