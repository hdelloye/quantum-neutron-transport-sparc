"""docs/RESULTS.md is generated from data (PD-32): the tables and the headline sentence must be
the verbatim output of artifacts.format_markdown / headline_sentence on the committed JSON."""
import copy
import re
import subprocess
from pathlib import Path

import pytest

from neutron_qae import artifacts

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs" / "RESULTS.md"


def _results_text() -> str:
    return RESULTS.read_text(encoding="utf-8")


def _scaling_doc() -> dict:
    return artifacts.load_artifact(ROOT / artifacts.SCALING_FILE, "scaling_rmse")


def test_results_doc_embeds_headline():
    doc = _scaling_doc()
    text = _results_text()
    assert artifacts.headline_sentence(doc) in text, "headline sentence drifted from data/scaling_rmse.json"
    assert artifacts.format_markdown(doc) in text, "scaling table drifted from data/scaling_rmse.json"


def test_format_markdown_handles_quick_profile():
    doc = copy.deepcopy(_scaling_doc())
    doc["profile"] = "quick"
    doc["parameters"]["aer_M_max"] = None
    doc["results"]["series"]["mlae_aer"] = None
    doc["results"]["ionq_marker"] = None
    table = artifacts.format_markdown(doc)
    assert "Aer" not in table and "IonQ" not in table
    assert "| Classical lattice MC |" in table and "| MLAE, analytic runner |" in table
    assert not table.endswith("\n")
    sentence = artifacts.headline_sentence(doc)
    assert "Aer" not in sentence and sentence.endswith("M = 2..11).")


README = ROOT / "README.md"
RESULTS_SECTIONS = (
    "## Headline: RMSE versus cost",
    "## Exit-position histograms (circuit validation, not speedup evidence)",
    "## Truncation bias of the K = 1 estimand",
    "## Wall-thickness rare-event study",
    "## Reproduce",
    "## Limits of this evidence",
)
RESULTS_PHRASES = ("circuit validation, not speedup evidence", "sampling complexity", "execution proof",
                   "6.4 sigma", "99.7", "not in any fit")
CLAIM = re.compile(r"speedup|quantum[ -]advantage")
LINK = re.compile(r"\]\(([^)\s]+)\)")


@pytest.mark.parametrize("kind", sorted(artifacts.ARTIFACTS))
def test_results_doc_embeds_every_artifact_table(kind):
    doc = artifacts.load_artifact(ROOT / artifacts.ARTIFACTS[kind][0], kind)
    assert artifacts.format_markdown(doc) in _results_text(), f"{kind} table drifted from its JSON"


def test_readme_carries_headline_sentence():
    assert artifacts.headline_sentence(_scaling_doc()) in README.read_text(encoding="utf-8")


def test_figure_links_resolve():
    committed = set(subprocess.run(["git", "ls-files", "data"], cwd=ROOT, capture_output=True, text=True,
                                   check=True).stdout.split())
    for path, base, prefix in ((README, ROOT, "data/"), (RESULTS, ROOT / "docs", "../data/")):
        targets = [t for t in LINK.findall(path.read_text(encoding="utf-8")) if t.endswith(".png")]
        assert targets, f"{path.name} links no figure"
        for target in targets:
            assert not target.lower().startswith("http"), f"{path.name}: remote image {target}"
            assert target.startswith(prefix) and ".." not in target[len(prefix):], f"{path.name}: {target}"
            resolved = (base / target).resolve()
            rel = resolved.relative_to(ROOT).as_posix()
            assert resolved.is_file() and rel.startswith("data/") and rel in committed, f"{path.name}: {target}"


def test_results_doc_sections_and_caveats():
    text = _results_text()
    lines = text.splitlines()
    for heading in RESULTS_SECTIONS:
        assert heading in lines, f"docs/RESULTS.md missing section {heading!r}"
    for phrase in RESULTS_PHRASES:
        assert phrase in text, f"docs/RESULTS.md missing {phrase!r}"
    readme = README.read_text(encoding="utf-8")
    assert "## Results" in readme.splitlines() and "(docs/RESULTS.md)" in readme


@pytest.mark.parametrize("path", [README, RESULTS], ids=["README.md", "RESULTS.md"])
def test_no_unnegated_speedup_claims(path):
    text = path.read_text(encoding="utf-8").lower()
    bad = []
    for m in CLAIM.finditer(text):
        before = text[max(0, m.start() - 40):m.start()]
        if "no " not in before and "not " not in before:
            bad.append(text[max(0, m.start() - 40):m.end()])
    assert not bad, f"un-negated claims in {path.name}: {bad}"
