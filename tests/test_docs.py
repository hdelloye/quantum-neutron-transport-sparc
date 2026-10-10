"""Docs compliance tests (PLAT-03 LICENSE/attribution half, DOCS-06 disclosure).

A missing attribution line or an undisclosed library/AI tool can disqualify the submission,
so these checks fail loudly when the README or LICENSE drift.
"""
import json
from pathlib import Path

import compliance_checks as cc

ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTION = "This effort is supported by Qollab & IonQ."
DISCLOSURE_HEADING = "## Libraries, tools and licenses (disclosure)"
SEPARATOR_CHARS = set("|-: ")


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _disclosure_rows() -> list[list[str]]:
    """Body rows of the disclosure table, each split into stripped cells."""
    lines = _readme().splitlines()
    start = lines.index(DISCLOSURE_HEADING) + 1
    section = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        section.append(line)
    table = [line.strip() for line in section if line.strip().startswith("|")]
    assert table, "disclosure section has no table"
    body = [line for line in table[1:] if not set(line) <= SEPARATOR_CHARS]
    rows = []
    for line in body:
        inner = line
        if inner.startswith("|"):
            inner = inner[1:]
        if inner.endswith("|"):
            inner = inner[:-1]
        rows.append([cell.strip() for cell in inner.split("|")])
    return rows


def test_mit_license_present():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Copyright (c) 2026" in text
    assert "Permission is hereby granted, free of charge" in text


def test_readme_attribution_and_disclosure():
    text = _readme()
    assert ATTRIBUTION in text
    for needle in ("Qiskit", "Apache-2.0", "NumPy", "BSD-3-Clause", "Claude Code", "GSD", "MIT",
                   "Pyodide", "qiskit-ionq"):
        assert needle in text, f"disclosure missing {needle}"


def test_disclosure_table_has_no_empty_cells():
    rows = _disclosure_rows()
    assert len(rows) >= 9, f"expected at least 9 disclosure rows, got {len(rows)}"
    for row in rows:
        assert len(row) == 4, f"row does not have 4 cells: {row}"
        for cell in row:
            assert cell, f"empty cell in disclosure row: {row}"


def test_disclosure_one_row_per_component():
    rows = _disclosure_rows()
    names = [row[0] for row in rows]
    assert len(names) == len(set(names)), f"duplicate disclosure rows: {names}"
    ionq = [row for row in rows if row[0].startswith("qiskit-ionq")]
    assert len(ionq) == 1
    row_text = " | ".join(ionq[0])
    assert "1.0.2" in row_text and "1.1.1" in row_text


def test_license_and_readme_ship_to_qollab():
    assert {"LICENSE", "README.md"} <= set(cc.qollab_upload_files(ROOT))


def test_readme_fits_qollab_writeup():
    assert len(_readme()) < 65_000


RUNTIME_SECTIONS = (
    "## Static facts (read from Qollab's runtime code, 2026-10-10)",
    "## Empirical runs",
    "## Raw reports",
    "## Conclusions for later phases",
)


def test_runtime_record_has_sections():
    path = ROOT / "docs" / "QOLLAB-RUNTIME.md"
    assert path.is_file()
    lines = path.read_text(encoding="utf-8").splitlines()
    for heading in RUNTIME_SECTIONS:
        assert heading in lines, f"docs/QOLLAB-RUNTIME.md missing section {heading!r}"


REPORT_PREFIX = "QOLLAB_RUNTIME_REPORT="
PUBLIC_URL_PREFIX = "https://qollab.xyz/u/"


def test_runtime_findings_recorded():
    """The runtime record must hold real Qollab reports, not the 01-02 template placeholders."""
    text = (ROOT / "docs" / "QOLLAB-RUNTIME.md").read_text(encoding="utf-8")
    reports = [json.loads(line.split("=", 1)[1])
               for line in text.splitlines() if line.startswith(REPORT_PREFIX)]
    assert reports, "no QOLLAB_RUNTIME_REPORT= lines recorded"
    for report in reports:
        assert {"runtime", "backend", "toy"} <= set(report), sorted(report)
    assert any(not r["backend"]["is_ionq"] and r["toy"]["accepted"] for r in reports), \
        "no accepted Built-in simulator run recorded"
    assert any(r["backend"]["is_ionq"] for r in reports), "no IonQ run recorded"
    assert any(r["backend"]["is_ionq"] and r["toy"]["accepted"] for r in reports), \
        "no accepted IonQ run recorded"
    assert PUBLIC_URL_PREFIX in text, "published Qollab URL missing"
    assert "ACCEPTED / REJECTED" not in text, "template placeholder left in the conclusions"
    assert "Phase 4 IonQ path should use" in text
