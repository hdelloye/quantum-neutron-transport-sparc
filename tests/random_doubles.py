"""Test-only random sources and static RNG gates (never imported by the package).

- HashCounterSource: SHA-256 in counter mode, 53-bit uniforms; proves an engine runs on a
  non-numpy source with no code change (PHYS-08).
- ScriptedSource: replays fixed uniforms to pin single histories exactly.
- rng_violations(path): AST gate that an engine never owns randomness.
- foreign_imports(path): top-level imports outside numpy, neutron_qae and the stdlib.
"""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

import numpy as np

GENERATOR_NAMES = {"default_rng", "RandomState", "SeedSequence", "Generator",
                   "PCG64", "MT19937", "Philox", "SFC64"}
ALLOWED_THIRD_PARTY = {"numpy", "neutron_qae"}


class HashCounterSource:
    """Test double: SHA-256 in counter mode, 53-bit uniforms; not numpy's bit generator."""
    def __init__(self, key: bytes = b"neutron-qae"):
        self.key, self.counter, self.calls, self.drawn = key, 0, 0, 0
    def random(self, size: int) -> np.ndarray:
        self.calls += 1; self.drawn += size
        nblocks = (size + 3) // 4   # 4 x 64-bit words per 32-byte digest
        buf = b"".join(hashlib.sha256(self.key + (self.counter + i).to_bytes(8, "little")).digest() for i in range(nblocks))
        self.counter += nblocks
        w = np.frombuffer(buf, dtype="<u8")[:size]
        return (w >> np.uint64(11)).astype(np.float64) * 2.0 ** -53

class ScriptedSource:
    """Test double: replays a fixed list of uniforms; raises if exhausted."""
    def __init__(self, values):
        self.values, self.pos = np.asarray(values, dtype=np.float64), 0
    def random(self, size: int) -> np.ndarray:
        if self.pos + size > self.values.size:
            raise RuntimeError("ScriptedSource exhausted")
        out = self.values[self.pos:self.pos + size]; self.pos += size
        return out.copy()


def rng_violations(path) -> list[str]:
    """Every place in ``path`` where code could draw randomness without the injected source.

    Flags: ``import random`` / ``from random import``, any import of ``numpy.random`` or
    ``from numpy import random``, any attribute named ``random`` (engines reach the source
    only through ``random_source.draw``), and any name or attribute in GENERATOR_NAMES.
    """
    path = Path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random" or alias.name.split(".")[:2] == ["numpy", "random"]:
                    out.append(f"{path.name}:{line}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = {alias.name for alias in node.names}
            if mod == "random" or mod.split(".")[:2] == ["numpy", "random"] or (mod == "numpy" and "random" in names):
                out.append(f"{path.name}:{line}: from {mod} import {', '.join(sorted(names))}")
            for nm in sorted(names & GENERATOR_NAMES):
                out.append(f"{path.name}:{line}: imports generator name {nm}")
        elif isinstance(node, ast.Attribute):
            if node.attr == "random":
                out.append(f"{path.name}:{line}: attribute .random")
            elif node.attr in GENERATOR_NAMES:
                out.append(f"{path.name}:{line}: attribute .{node.attr}")
        elif isinstance(node, ast.Name) and node.id in GENERATOR_NAMES:
            out.append(f"{path.name}:{line}: name {node.id}")
    return out


def foreign_imports(path) -> set[str]:
    """Top-level names of absolute imports in ``path`` outside the stdlib, numpy and neutron_qae."""
    path = Path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            tops.add(node.module.split(".")[0])
    return {t for t in tops if t not in sys.stdlib_module_names and t not in ALLOWED_THIRD_PARTY}
