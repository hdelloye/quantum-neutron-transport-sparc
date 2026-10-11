"""docs/RESULTS.md is generated from data (PD-32): the tables and the headline sentence must be
the verbatim output of artifacts.format_markdown / headline_sentence on the committed JSON."""
import copy
from pathlib import Path

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
