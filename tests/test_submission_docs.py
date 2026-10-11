"""Phase 6 submission docs (DOCS-03, DOCS-04, DOCS-05, DOCS-08): pure string checks on README.md,
HANDOFF.md and docs/, so the judge-facing claims cannot drift. No subprocess, no qiskit import."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
RESULTS = ROOT / "docs" / "RESULTS.md"
HANDOFF = ROOT / "HANDOFF.md"

NARROWED_CLAIM = ("first end-to-end QAE estimate of a neutron transport tally through a two-material "
                  "fusion first wall, with measured error-versus-oracle-query scaling against a matched "
                  "classical baseline.")
# PROJECT.md "Do NOT claim" list: this phrase must never appear, not even negated.
BANNED_NOVELTY = "first quantum neutron transport"
LIMITATION_LEADS = (
    "**One-group physics.**",
    "**K-collision truncation.**",
    "**Ideal-simulator scaling plot.**",
    "**Noise on IonQ simulators.**",
    "**Open IonQ ideal-simulator discrepancy.**",
    "**No wall-clock speedup claim.**",
    "**Sampling-complexity argument only.**",
)
LIMITATION_PHRASES = (
    ("14.1 MeV",),
    ("99.7",),
    ("analytic", "Aer"),
    ("noise model",),
    ("6.4 sigma", "open"),
    ("wall-clock",),
    ("sqrt(N)",),
)


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _section(text: str, heading: str, name: str = "README.md") -> str:
    """Body of `heading` up to the next heading of the same or a higher level."""
    lines = text.splitlines()
    assert heading in lines, f"{name} has no {heading} section"
    level = len(heading) - len(heading.lstrip("#"))
    start = lines.index(heading) + 1
    body = []
    for line in lines[start:]:
        if line.startswith("#"):
            hashes = len(line) - len(line.lstrip("#"))
            if hashes <= level and line[hashes:hashes + 1] == " ":
                break
        body.append(line)
    assert any(line.strip() for line in body), f"{heading} is empty"
    return "\n".join(body)


def _bullets(body: str) -> list[str]:
    """Top-level `- ` bullets with their continuation lines."""
    bullets: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            bullets.append(line[2:])
        elif bullets and line.startswith("  "):
            bullets[-1] += " " + line.strip()
    return bullets


def test_novelty_prior_art_and_narrowed_claim():
    body = _section(_readme(), "### Novelty")
    for needle in ("arXiv:2410.19489", "Olivier", "Nowak", "116001", "arXiv:2502.14374",
                   "arXiv:2607.10772", "Miao", "Sone", NARROWED_CLAIM):
        assert needle in body, f"### Novelty is missing {needle!r}"
    assert "To our knowledge, this is the " + NARROWED_CLAIM in body


@pytest.mark.parametrize("path", [README, HANDOFF, RESULTS], ids=["README.md", "HANDOFF.md", "RESULTS.md"])
def test_banned_novelty_phrases_absent(path):
    if not path.exists():
        pytest.skip(f"{path.name} not written yet")
    assert BANNED_NOVELTY not in path.read_text(encoding="utf-8").lower(), f"banned claim in {path.name}"


def test_limitations_section():
    text = _readme()
    body = _section(text, "## Limitations")
    bullets = _bullets(body)
    assert len(bullets) >= len(LIMITATION_LEADS), f"## Limitations has {len(bullets)} bullets"
    for bullet in bullets:
        assert bullet.strip(), "## Limitations has an empty bullet"
        assert sum(lead in bullet for lead in LIMITATION_LEADS) <= 1, f"two leads in one bullet: {bullet[:80]}"
    positions = [body.find(lead) for lead in LIMITATION_LEADS]
    assert all(p >= 0 for p in positions), [lead for lead, p in zip(LIMITATION_LEADS, positions) if p < 0]
    assert positions == sorted(positions), "## Limitations leads are out of order"
    for lead, phrases in zip(LIMITATION_LEADS, LIMITATION_PHRASES):
        bullet = next(b for b in bullets if lead in b)
        for phrase in phrases:
            assert phrase in bullet, f"{lead} bullet is missing {phrase!r}"
    lines = text.splitlines()
    assert lines.index("### Documentation") < lines.index("## Limitations") < lines.index("## Repository layout")


def test_ionq_estimate_always_has_caveat():
    lines = [line for line in _readme().splitlines() if "0.228671" in line]
    assert lines, "README never shows the IonQ-only estimate"
    for line in lines:
        assert "6.4 sigma" in line, f"IonQ estimate without its 6.4 sigma caveat: {line[:100]}"


@pytest.mark.parametrize("path", [README, RESULTS], ids=["README.md", "RESULTS.md"])
def test_phase5_review_wording_fixed(path):
    """Phase 5 review WR-03/WR-04/WR-05: no unmeasured MLAE cost law, no SE reading of the fit scatter."""
    text = path.read_text(encoding="utf-8")
    squeezed = re.sub(r"\s+", "", text)
    for phrase in ("1/(epssqrt(T))", "1/(ε√T)"):
        assert phrase not in squeezed, f"{path.name} still states the MLAE cost law {phrase}"
    assert "within one standard error" not in text, f"{path.name} reads the fit scatter as a standard error"
    assert "fit scatter" in text, f"{path.name} does not label the slope +- values as fit scatter"


README_HEADINGS = (
    "# Quantum Neutron Transport: SPARC First Wall",
    "## What it does",
    "## The problem",
    "## Run it on Qollab",
    "## Run it locally",
    "## Replicate the results",
    "## Results",
    "## Judging criteria",
    "### Novelty",
    "### Technical execution",
    "### Impact",
    "### Documentation",
    "## Limitations",
    "## Repository layout",
    "## Rules every module follows",
    "## Libraries, tools and licenses (disclosure)",
    "## License",
)
GITHUB_URL = "https://github.com/hdelloye/quantum-neutron-transport-sparc"
IMAGE = re.compile(r"!\[([^\]]*)\]\((data/fig_[^)\s]+\.png)\)")


def test_readme_headings_in_order():
    lines = _readme().splitlines()
    missing = [h for h in README_HEADINGS if h not in lines]
    assert not missing, f"README.md is missing headings {missing}"
    positions = [lines.index(h) for h in README_HEADINGS]
    assert positions == sorted(positions), "README.md headings are out of order"


def test_readme_documents_quick_mode_from_code():
    defs = [line for line in (ROOT / "main.py").read_text(encoding="utf-8").splitlines()
            if line.startswith("def main(")]
    assert len(defs) == 1, "main.py must have exactly one one-line def main(...)"
    m = re.search(r'\bmode: str = "([a-z]+)"', defs[0])
    assert m, defs[0]
    text = _readme()
    assert f"`mode` (default `{m.group(1)}`)" in text, f"README does not document mode default {m.group(1)!r}"
    for needle in ("QUICK_REPORT=", "QUICK MODE OK", "CAVEAT", "CR-01", "--figure-dir",
                   "NEUTRON_QAE_SLOW=1", GITHUB_URL):
        assert needle in text, f"README.md is missing {needle!r}"


def test_readme_figures_have_alt_text():
    images = IMAGE.findall(_readme())
    targets = {target for _, target in images}
    assert len(targets) >= 4, f"README embeds {sorted(targets)}"
    for alt, target in images:
        assert len(alt.strip()) >= 15, f"alt text too short for {target}: {alt!r}"


def test_wr01_wording_removed():
    for path in (README, ROOT / "docs" / "QUANTUM.md", ROOT / "docs" / "QOLLAB-RUNTIME.md"):
        assert "same transpiled circuit" not in path.read_text(encoding="utf-8").lower(), path.name
    quantum = (ROOT / "docs" / "QUANTUM.md").read_text(encoding="utf-8")
    assert "one gate per" in quantum or "one extra gate per" in quantum


def test_criteria_sections_non_empty():
    text = _readme()
    for heading in ("### Novelty", "### Technical execution", "### Impact", "### Documentation"):
        body = _section(text, heading)
        assert sum(1 for line in body.splitlines() if line.strip()) >= 2, f"{heading} is too thin"
