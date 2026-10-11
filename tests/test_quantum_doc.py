"""QC-05 docs gate: docs/QUANTUM.md and README.md describe what the Phase 4 code actually does.

The resource table in the doc must equal ``format_resource_table(resource_table())`` (and the
output of ``scripts/qae_local.py resources``), so code and doc cannot drift.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from neutron_qae.grover import format_resource_table, resource_table
from neutron_qae.runners import IONQ_RUNS_FILE, load_ionq_records

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "QUANTUM.md"
HEADINGS = (
    "# Quantum oracle and amplitude estimation (Phase 4)",
    "## Register layout",
    "## Contract gate",
    "## Resource table",
    "## Grover powers and the transpile-once rule",
    "## Maximum-likelihood amplitude estimation",
    "## Cost: applications of A",
    "## Runners",
    "## IonQ protocol on Qollab",
    "## IonQ results",
    "## What this evidence does and does not show",
)


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def table() -> str:
    return format_resource_table(resource_table())


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = lines.index(heading) + 1
    out = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        out.append(line)
    return "\n".join(out)


def test_quantum_doc_sections():
    lines = _doc().splitlines()
    positions = [lines.index(h) for h in HEADINGS]          # ValueError names a missing heading
    assert positions == sorted(positions), "docs/QUANTUM.md headings are out of order"


def test_resource_table_in_doc_matches_code(table):
    assert table in _doc()


def test_qae_local_resources_output_matches(table):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "qae_local.py"), "resources"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == table.strip()


def test_quantum_doc_names_layout_and_cost():
    text = _doc()
    for needle in ("exact.REGISTER_LAYOUT", "N_A", "num_oracle_queries", "transpile_once", "IONQ_RECORD=",
                   "data/ionq_runs.json", "scripts/ingest_ionq_records.py"):
        assert needle in text, f"docs/QUANTUM.md missing {needle!r}"
    from neutron_qae.exact import REGISTER_LAYOUT

    assert REGISTER_LAYOUT in text


def test_readme_documents_phase4():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("docs/QUANTUM.md", "ideal_mode", "IONQ_RECORD=", "QAE RUN COMPLETED", "--mode smoke",
                   "docs/PHYSICS.md", "KERNELS_CONTRACT_VERSION", "tests/golden/"):
        assert needle in text, f"README.md missing {needle!r}"


def test_ionq_results_section_matches_records_state():
    section = _section(_doc(), "## IonQ results")
    if load_ionq_records(ROOT / IONQ_RUNS_FILE):
        assert "No IonQ records yet" not in section
    else:
        assert "No IonQ records yet" in section


def test_ionq_records_in_docs_match_data():
    """docs/QOLLAB-RUNTIME.md quotes exactly the accepted records stored in data/ionq_runs.json."""
    text = (ROOT / "docs" / "QOLLAB-RUNTIME.md").read_text(encoding="utf-8")
    quoted = [json.loads(line.split("=", 1)[1]) for line in text.splitlines() if line.startswith("IONQ_RECORD=")]
    stored = load_ionq_records(ROOT / IONQ_RUNS_FILE)
    doc_set = {json.dumps(r, sort_keys=True) for r in quoted if r.get("accepted") is True}
    data_set = {json.dumps(r, sort_keys=True) for r in stored}
    assert len(data_set) == len(stored), "duplicate records in data/ionq_runs.json"
    assert doc_set == data_set, (f"docs quote {len(doc_set)} accepted records, data holds {len(data_set)}; "
                                 f"only in docs: {len(doc_set - data_set)}, only in data: {len(data_set - doc_set)}")
