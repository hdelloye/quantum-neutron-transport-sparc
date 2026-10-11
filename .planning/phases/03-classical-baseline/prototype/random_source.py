"""RandomSource protocol: the only randomness an engine sees (PHYS-08)."""
from __future__ import annotations
import hashlib
from typing import Protocol, runtime_checkable
import numpy as np

@runtime_checkable
class RandomSource(Protocol):
    def random(self, size: int) -> np.ndarray:
        """size float64 uniforms in [0, 1)."""
        ...

def as_source(source=None) -> RandomSource:
    """None -> fresh numpy Generator (unseeded); int/SeedSequence -> default_rng(seed); else must be a RandomSource."""
    if source is None or isinstance(source, (int, np.integer, np.random.SeedSequence)):
        return np.random.default_rng(source)
    if not isinstance(source, RandomSource):
        raise TypeError(f"random source must have .random(size); got {type(source).__name__}")
    return source

def draw(source: RandomSource, size: int) -> np.ndarray:
    u = np.asarray(source.random(size), dtype=np.float64)
    if u.shape != (size,):
        raise ValueError(f"random source returned shape {u.shape}, expected ({size},)")
    if size and not (u.min() >= 0.0 and u.max() < 1.0):
        raise ValueError("random source must return uniforms in [0, 1)")
    return u

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
