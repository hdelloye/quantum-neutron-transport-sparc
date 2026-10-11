"""RandomSource protocol: the only randomness an engine sees (PHYS-08).

Contract
--------
A random source is any object with one method, ``random(size)``, returning a float64
array of shape ``(size,)`` whose values lie in [0, 1). Engines (``neutron_qae/mc_*.py``)
draw every uniform they use through :func:`draw`, never from numpy directly, so the
source can be swapped (seeded numpy Generator, a SHA-256 counter source, a scripted
replay in tests) with no engine change.

- A ``numpy.random.Generator`` satisfies the protocol unwrapped (its ``random`` method
  has the right shape and range), so ``as_source(g) is g``.
- 53-bit uniforms (Generator.random produces multiples of 2**-53) avoid the coarse-u
  tail bias of the exponential flight ``-log1p(-u)``; a coarse source would truncate
  the long-flight tail.
- Seeding is the caller's job. For independent repetitions use
  ``np.random.SeedSequence(seed).spawn(R)`` and pass each child to :func:`as_source`.
- :func:`as_source` is the only place in the package that constructs a numpy Generator
  (an AST test enforces that no engine does).
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
import numpy as np

__all__ = ["RandomSource", "as_source", "draw"]


@runtime_checkable
class RandomSource(Protocol):
    def random(self, size: int) -> np.ndarray:
        """size float64 uniforms in [0, 1)."""
        ...


def as_source(source=None) -> RandomSource:
    """Coerce ``source`` to a RandomSource.

    None -> fresh unseeded numpy Generator; int / np.integer / SeedSequence ->
    ``np.random.default_rng(source)``; any object with ``.random`` -> returned unchanged
    (identity); bool or anything else -> TypeError.
    """
    if isinstance(source, (bool, np.bool_)):
        raise TypeError("random source must not be a bool (bool is not a seed)")
    if source is None or isinstance(source, (int, np.integer, np.random.SeedSequence)):
        return np.random.default_rng(source)
    if not isinstance(source, RandomSource):
        raise TypeError(f"random source must have .random(size); got {type(source).__name__}")
    return source


def draw(source: RandomSource, size: int) -> np.ndarray:
    """``size`` validated uniforms from ``source``: float64, shape (size,), every value in [0, 1).

    ``size == 0`` returns an empty float64 array without calling the source. A wrong shape,
    a value outside [0, 1) or NaN raises ValueError (comparisons with NaN are false).
    """
    if size == 0:
        return np.empty(0, dtype=np.float64)
    u = np.asarray(source.random(size), dtype=np.float64)
    if u.shape != (size,):
        raise ValueError(f"random source returned shape {u.shape}, expected ({size},)")
    if not (u.min() >= 0.0 and u.max() < 1.0):
        raise ValueError("random source must return uniforms in [0, 1)")
    return u
