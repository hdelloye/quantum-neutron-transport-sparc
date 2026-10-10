"""PHYS-02 (code half): ENDF/B-VIII.0 provenance, atom densities, macroscopic values, input edges."""
import math
import re

import pytest

from neutron_qae import nuclear_data as nd
from neutron_qae.problem import atom_densities, one_group, sparc_first_wall


def test_provenance_covers_every_isotope():
    elements = set(nd.MICRO_14MEV)
    assert len(elements) == 10
    for table in (nd.PROVENANCE, nd.ABUNDANCE, nd.ATOMIC_WEIGHT, nd.ATOMIC_NUMBER, nd.SIGMA_N2N_14MEV):
        assert set(table) == elements
    rows = [(el, r) for el, rs in nd.PROVENANCE.items() for r in rs]
    assert len(rows) == 36
    for el, rs in nd.PROVENANCE.items():
        masses = set()
        for label, mat, evaluation, date in rs:
            sym, mass = label.split("-")
            assert sym == el
            masses.add(int(mass))
        assert masses == set(nd.ABUNDANCE[el])
    mats = [r[1] for _, r in rows]
    assert len(set(mats)) == 36
    for el, (label, mat, evaluation, date) in rows:
        assert isinstance(mat, int) and not isinstance(mat, bool)
        assert mat // 100 == nd.ATOMIC_NUMBER[el], label
        assert evaluation and "|" not in evaluation, label
        assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", date), label
        assert date[:7] <= "2018-02", label       # every evaluation predates the 2018-02-02 release


def test_library_and_material_sources_cited():
    assert nd.LIBRARY["name"] == "ENDF/B-VIII.0"
    assert nd.LIBRARY["release_date"] == "2018-02-02"
    assert "Nucl. Data Sheets 148, 1 (2018)" in nd.LIBRARY["reference"]
    assert nd.LIBRARY["source"].startswith("https://www.nndc.bnl.gov/")
    assert "arXiv:2603.03893" in nd.MATERIAL_SOURCES["WHA_97W"]
    assert "PNNL-15870" in nd.MATERIAL_SOURCES["SS316"]
    assert nd.WHA_97W == (18.5, {"W": 0.97, "Ni": 0.02, "Fe": 0.01})
    assert nd.SS316[0] == 8.00


def test_abundances_sum_to_one():
    for el, iso in nd.ABUNDANCE.items():
        assert math.fsum(iso.values()) == pytest.approx(1.0, abs=1e-4), el


def test_ss316_atom_densities_match_pnnl():
    n = atom_densities(*nd.SS316)
    for el, ref in {"Fe": 0.056373, "Cr": 0.015751, "Ni": 0.009850, "Mo": 0.001255, "Mn": 0.001754, "Si": 0.001715}.items():
        assert n[el] == pytest.approx(ref, abs=1e-6)
    assert sum(n.values()) == pytest.approx(8.713e-2, rel=1e-3)


def test_wha_atom_densities():
    n = atom_densities(*nd.WHA_97W)
    for el, ref in {"W": 0.058783, "Ni": 0.003796, "Fe": 0.001995}.items():
        assert n[el] == pytest.approx(ref, abs=1e-6)
    assert sum(n.values()) == pytest.approx(0.06457, rel=1e-3)


def test_macroscopic_cross_sections_match_research():
    raw = sparc_first_wall("isotropic_raw")
    assert raw.front.sigma_t == pytest.approx(0.33089, rel=1e-4)
    assert raw.back.sigma_t == pytest.approx(0.22287, rel=1e-4)
    assert raw.front.sigma_s == pytest.approx(0.17416, rel=1e-4)
    assert raw.back.sigma_s == pytest.approx(0.10141, rel=1e-4)
    assert 1 / raw.front.sigma_t == pytest.approx(3.022, rel=1e-3)
    assert 1 / raw.back.sigma_t == pytest.approx(4.487, rel=1e-3)
    tc = sparc_first_wall("transport_corrected")
    assert tc.front.sigma_t == pytest.approx(0.171276, rel=1e-5)
    assert tc.back.sigma_t == pytest.approx(0.139503, rel=1e-5)
    assert tc.front.sigma_s == pytest.approx(0.014547, rel=1e-4)
    assert tc.back.sigma_s == pytest.approx(0.018036, rel=1e-4)
    assert tc.front.scatter_ratio == pytest.approx(0.084936, rel=1e-4)
    assert tc.back.scatter_ratio == pytest.approx(0.129285, rel=1e-4)


def test_removal_is_identical_in_both_models():
    tc, raw = sparc_first_wall("transport_corrected"), sparc_first_wall("isotropic_raw")
    assert tc.front.sigma_a == pytest.approx(raw.front.sigma_a, rel=1e-12)
    assert tc.back.sigma_a == pytest.approx(raw.back.sigma_a, rel=1e-12)
    assert tc.front.sigma_a == pytest.approx(0.15673, rel=1e-4)
    assert tc.back.sigma_a == pytest.approx(0.12147, rel=1e-4)


@pytest.mark.parametrize("rho, wfrac, model", [
    (18.5, {}, "transport_corrected"),
    (18.5, {"Xx": 1.0}, "transport_corrected"),
    (0.0, {"W": 1.0}, "transport_corrected"),
    (18.5, {"W": -0.1, "Ni": 1.1}, "transport_corrected"),
    (18.5, {"W": 0.5}, "transport_corrected"),
    (18.5, {"W": 1.0}, "raw"),
])
def test_one_group_input_edges(rho, wfrac, model):
    with pytest.raises(ValueError):
        one_group("bad", rho, wfrac, model=model)


def test_single_element_composition():
    m = one_group("W", 19.3, {"W": 1.0}, model="isotropic_raw")
    expect = 19.3 * 1.0 * nd.AVOGADRO / nd.ATOMIC_WEIGHT["W"] * nd.BARN_CM2 * 5.367
    assert m.sigma_t == pytest.approx(expect, rel=1e-15)


def test_one_group_is_deterministic():
    a, b = sparc_first_wall(), sparc_first_wall()
    for m1, m2 in ((a.front, b.front), (a.back, b.back)):
        assert m1.sigma_t == m2.sigma_t and m1.sigma_s == m2.sigma_s
