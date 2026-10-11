"""Random-source protocol (PHYS-08): conformance, coercion, draw validation, engine RNG gate."""
import ast
import math
from pathlib import Path

import numpy as np
import pytest

from neutron_qae.random_source import RandomSource, as_source, draw
from random_doubles import HashCounterSource, foreign_imports, rng_violations

ROOT = Path(__file__).resolve().parents[1]


class _Fixed:
    """Inline source returning whatever ``make(size)`` builds."""

    def __init__(self, make):
        self.make = make

    def random(self, size):
        return self.make(size)


def test_generator_satisfies_protocol():
    g = np.random.default_rng(1)
    assert isinstance(g, RandomSource)
    assert as_source(g) is g
    h = HashCounterSource()
    assert isinstance(h, RandomSource) and as_source(h) is h


def test_as_source_coercions():
    assert isinstance(as_source(None), np.random.Generator)
    assert isinstance(as_source(), np.random.Generator)
    ref = np.random.default_rng(7).random(5)
    for seed in (7, np.int64(7), np.random.SeedSequence(7)):
        g = as_source(seed)
        assert isinstance(g, np.random.Generator)
        assert np.array_equal(g.random(5), ref)
    for bad in (True, 1.5, "7", object()):
        with pytest.raises(TypeError):
            as_source(bad)


@pytest.mark.parametrize("make", [
    lambda size: np.full(size + 1, 0.5),            # wrong length
    lambda size: np.full((size, 1), 0.5),           # wrong shape
    lambda size: np.ones(size),                     # 1.0 is outside [0, 1)
    lambda size: np.full(size, -0.1),               # negative
    lambda size: np.full(size, np.nan),             # NaN
], ids=["length", "shape", "one", "negative", "nan"])
def test_draw_validates_shape_and_range(make):
    with pytest.raises(ValueError):
        draw(_Fixed(make), 4)


def test_draw_zero_size_skips_source():
    h = HashCounterSource()
    u = draw(h, 0)
    assert u.dtype == np.float64 and u.shape == (0,)
    assert h.calls == 0 and h.drawn == 0
    u = draw(h, 3)
    assert u.shape == (3,) and h.calls == 1 and h.drawn == 3


def test_engines_never_own_randomness():
    engines = sorted((ROOT / "neutron_qae").glob("mc_*.py"))
    assert "mc_continuous.py" in {p.name for p in engines}
    for p in engines:
        assert rng_violations(p) == [], (p.name, rng_violations(p))
    for p in [ROOT / "neutron_qae" / "random_source.py", *engines]:
        assert foreign_imports(p) == set(), (p.name, foreign_imports(p))


def test_rng_gate_has_teeth(tmp_path):
    bad = tmp_path / "mc_bad.py"
    bad.write_text(
        "import random\n"
        "import numpy as np\n"
        "def f(n):\n"
        "    a = np.random.uniform(size=n)\n"
        "    g = default_rng(1)\n"
        "    return a, g, random.random()\n",
        encoding="utf-8",
    )
    assert len(rng_violations(bad)) >= 3
    other = tmp_path / "mc_imports.py"
    other.write_text("import scipy\nfrom numpy import random\nfrom os import path\n", encoding="utf-8")
    assert foreign_imports(other) == {"scipy"}
    assert rng_violations(other)


def test_only_as_source_constructs_a_generator():
    path = ROOT / "neutron_qae" / "random_source.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "as_source")
    refs = [n.lineno for n in ast.walk(tree)
            if (isinstance(n, ast.Attribute) and n.attr == "default_rng")
            or (isinstance(n, ast.Name) and n.id == "default_rng")]
    assert refs
    assert all(fn.lineno <= line <= fn.end_lineno for line in refs), (refs, fn.lineno, fn.end_lineno)


def test_hash_double_is_a_valid_uniform_source():
    n = 100_000
    u = HashCounterSource().random(n)
    assert u.dtype == np.float64 and u.shape == (n,)
    assert u.min() >= 0.0 and u.max() < 1.0
    scaled = u * 2.0**53
    assert np.array_equal(scaled, np.floor(scaled))
    assert abs(u.mean() - 0.5) < 4 * math.sqrt(1 / 12 / n)
