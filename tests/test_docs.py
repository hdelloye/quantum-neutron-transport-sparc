"""Docs compliance tests (PLAT-03 LICENSE/attribution half, DOCS-06 disclosure).

A missing attribution line or an undisclosed library/AI tool can disqualify the submission,
so these checks fail loudly when the README or LICENSE drift.
"""
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
