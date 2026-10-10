"""docs/PHYSICS.md must match the code it cites (PHYS-02 docs half, PHYS-05 contract record).

Every cross section, every isotope's ENDF/B-VIII.0 provenance, the model values, T0/T1 and
the contract strings are recomputed from neutron_qae and looked up in the doc, so a doc that
drifts from the code (or a code change that is not documented) fails here.
"""
from pathlib import Path

from neutron_qae import exact
from neutron_qae import nuclear_data as nd
from neutron_qae.kernels import build_kernels
from neutron_qae.problem import sparc_first_wall

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "PHYSICS.md"
SECTIONS = (
    "## Problem geometry and indexing",
    "## Nuclear data (ENDF/B-VIII.0, 14.1 MeV)",
    "## One-group model",
    "## Kernels contract v1",
    "## Changing the contract",
    "## Derivation and replication",
    "## Approximations disclosed",
)


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def _row(key: str) -> list[str]:
    """Stripped cells of the first doc line starting with `| key |`."""
    prefix = f"| {key} |"
    for line in _doc().splitlines():
        if line.startswith(prefix):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError(f"docs/PHYSICS.md has no table row starting with {prefix!r}")


def test_physics_doc_sections():
    lines = _doc().splitlines()
    positions = []
    for heading in SECTIONS:
        assert heading in lines, f"docs/PHYSICS.md missing section {heading!r}"
        positions.append(lines.index(heading))
    assert positions == sorted(positions), "docs/PHYSICS.md sections are out of order"


def test_library_and_material_citations():
    text = _doc()
    for needle in (nd.LIBRARY["name"], nd.LIBRARY["release_date"], "Nucl. Data Sheets 148, 1 (2018)",
                   nd.LIBRARY["source"], "arXiv:2603.03893", "PNNL-15870", "14.1 MeV",
                   "18.5 g/cm3", "8.00 g/cm3"):
        assert needle in text, f"docs/PHYSICS.md missing citation {needle!r}"


def test_every_cross_section_value_is_in_doc():
    for el, (sigma_t, sigma_el, mubar) in nd.MICRO_14MEV.items():
        cells = _row(el)
        for value in (sigma_t, sigma_el, nd.SIGMA_N2N_14MEV[el], mubar):
            assert str(value) in cells, f"{el}: {value!r} not in its PHYSICS.md row {cells}"


def test_every_isotope_provenance_is_in_doc():
    count = 0
    for rows in nd.PROVENANCE.values():
        for isotope, mat, evaluation, date in rows:
            cells = _row(isotope)
            for value in (str(mat), evaluation, date):
                assert value in cells, f"{isotope}: {value!r} not in its PHYSICS.md row {cells}"
            count += 1
    assert count == 36
    rows_in_doc = [line for line in _doc().splitlines()
                   if any(line.startswith(f"| {r[0]} |") for rows in nd.PROVENANCE.values() for r in rows)]
    assert len(rows_in_doc) == 36, f"expected 36 isotope rows, found {len(rows_in_doc)}"


def test_model_values_and_honest_labels():
    text = _doc()
    spec = sparc_first_wall()
    raw = sparc_first_wall("isotropic_raw")
    expected = []
    for m in (spec.front, spec.back):
        expected += [f"{m.sigma_t:.6f}", f"{m.sigma_s:.6f}", f"{m.scatter_ratio:.6f}", f"{m.sigma_a:.5f}"]
    for m in (raw.front, raw.back):
        expected += [f"{m.sigma_t:.5f}", f"{m.sigma_a:.5f}"]
    k = build_kernels(spec)
    k_raw = build_kernels(raw)
    expected += [f"{exact.transmission_within(k, 0):.10f}", f"{exact.transmission_within(k, 1):.10f}",
                 f"{exact.transmission_within(k_raw, 0):.4f}"]
    expected += ["model uncollided transmission", "physical uncollided transmission",
                 "0.2290", "0.2437", "0.1224", "0.997", "0.899"]
    for needle in expected:
        assert needle in text, f"docs/PHYSICS.md missing {needle!r}"
    assert f"{exact.transmission_within(k_raw, 0):.4f}" == "0.0867"


def test_contract_section_names_layout_and_procedure():
    text = _doc()
    for needle in (exact.REGISTER_LAYOUT, "KERNELS_CONTRACT_VERSION", "scripts/freeze_kernels.py --write --force",
                   "tests/golden/kernels_v1.json", "column 4", "row_of"):
        assert needle in text, f"docs/PHYSICS.md missing {needle!r}"


def test_readme_points_to_physics_and_contract():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("docs/PHYSICS.md", "KERNELS_CONTRACT_VERSION", "tests/golden/"):
        assert needle in text, f"README.md missing {needle!r}"
