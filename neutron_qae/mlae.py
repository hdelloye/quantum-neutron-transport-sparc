"""Vendored maximum-likelihood amplitude estimation (MLAE) with the honest cost N_A (QAE-01, QAE-03).

Written for this project (no qiskit-algorithms source copied); it mirrors qiskit-algorithms
0.4.0's conventions so that the QAE-01 equality on identical counts is exact.

- Model: after A Q^k the flag reads 1 with probability sin^2((2k + 1) theta), a = sin^2 theta.
- Log-likelihood of records (k_i, n_i shots, h_i hits):
  L(theta) = sum_i [h_i log sin^2((2k_i + 1) theta) + (n_i - h_i) log cos^2((2k_i + 1) theta)]
  with 0 log 0 := 0 (``np.where`` guards), so no NaN ever reaches the argmax. Terms are added
  one k at a time, in qiskit-algorithms' order, so memory stays O(grid size).
- Maximiser: a grid of ``grid_size(ks) = max(10000, int(pi / 2 * 1000 * 2 * max(ks)))`` points on
  [EPS, pi/2 - EPS] with EPS = 1e-15 (qiskit-algorithms' default grid and search range), then a
  golden-section refinement inside the neighbouring grid points that is accepted only when its
  log-likelihood is at least as high as the grid maximum. qiskit-algorithms' default ``brute``
  + ``fmin`` finish can stop up to ~4e-5 in a short of the maximum; this one does not.
- Standard error: the asymptotic Fisher bound se_a = |sin(2 theta)| / sqrt(sum 4 n_k (2k + 1)^2).
- Cost (Suzuki et al. 2020, eq. 11): N_A = sum shots (2k + 1), computed from the records. A and
  A-dagger each count as one application, so one shot of A Q^k costs 2k + 1 and a shot of A alone
  (k = 0) costs 1, the same unit as one classical lattice history. qiskit-algorithms reports
  ``num_oracle_queries = shots x sum k``, which drops A and A-dagger and counts k = 0 as free;
  that figure is never used here.
- Records are sorted by (k, shots, hits, source) before evaluation, so the estimate does not
  depend on record order. Records labelled ``sampled=False`` (IonQ noise-model or run-kwarg
  counts, which are round(p shots), not Binomial samples) are refused.

Pyodide-safe: imports only numpy and the standard library.
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass

import numpy as np

__all__ = [
    "EPS",
    "MAX_POWER",
    "MLAEResult",
    "PowerResult",
    "estimate",
    "exponential_schedule",
    "fisher_se",
    "golden_max",
    "grid_size",
    "linear_schedule",
    "loglikelihood",
    "mle_theta",
    "n_applications",
]

EPS = 1e-15            # qiskit-algorithms' search range is [EPS, pi/2 - EPS]
MAX_POWER = 1024       # largest Grover power accepted; bounds the grid (about 3.2e6 points)


def _as_int(name: str, value) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{name} must be an integer, got {value!r}")  # noqa: TRY004 - plan: ValueError
    return int(value)


@dataclass(frozen=True)
class PowerResult:
    """One measured Grover power: ``hits`` flag = 1 outcomes out of ``shots`` after A Q^k."""

    k: int
    shots: int
    hits: int
    source: str = ""
    sampled: bool = True

    def __post_init__(self):
        k = _as_int("k", self.k)
        shots = _as_int("shots", self.shots)
        hits = _as_int("hits", self.hits)
        if not 0 <= k <= MAX_POWER:
            raise ValueError(f"k must be in 0..{MAX_POWER}, got {k}")
        if shots < 1:
            raise ValueError(f"shots must be >= 1, got {shots}")
        if not 0 <= hits <= shots:
            raise ValueError(f"hits must be in 0..shots ({shots}), got {hits}")
        if not isinstance(self.source, str):
            raise ValueError(f"source must be a str, got {self.source!r}")  # noqa: TRY004
        if not isinstance(self.sampled, bool):
            raise ValueError(f"sampled must be a bool, got {self.sampled!r}")  # noqa: TRY004
        object.__setattr__(self, "k", k)
        object.__setattr__(self, "shots", shots)
        object.__setattr__(self, "hits", hits)


def n_applications(records) -> int:
    """QAE-03 cost N_A = sum shots (2k + 1) over the records (0 for none)."""
    return int(sum(int(r.shots) * (2 * int(r.k) + 1) for r in records))


def grid_size(ks) -> int:
    """qiskit-algorithms' default grid size: max(10000, int(pi / 2 * 1000 * 2 * max(ks)))."""
    return max(10000, int(np.pi / 2 * 1000 * 2 * max(ks)))


def loglikelihood(theta, ks, hits, shots):
    """Log-likelihood at theta (scalar -> float, array -> array), 0 log 0 = 0."""
    th = np.asarray(theta, dtype=float)
    ll = np.zeros(th.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        for k, h, n in zip(ks, hits, shots):
            ang = (2 * int(k) + 1) * th
            h, miss = float(h), float(n) - float(h)
            ll += np.where(h > 0, h * np.log(np.sin(ang) ** 2), 0.0)
            ll += np.where(miss > 0, miss * np.log(np.cos(ang) ** 2), 0.0)
    return float(ll) if ll.ndim == 0 else ll


def golden_max(f, a: float, b: float, x0: float, f0: float) -> float:
    """Golden-section maximisation of f on [a, b]; the midpoint replaces x0 only if f(mid) >= f0."""
    g = (math.sqrt(5) - 1) / 2; c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(200):
        if b - a < 1e-15: break
        if fc > fd: b, d, fd = d, c, fc; c = b - g * (b - a); fc = f(c)
        else: a, c, fc = c, d, fd; d = a + g * (b - a); fd = f(d)
    m = 0.5 * (a + b)
    return float(m if f(m) >= f0 else x0)


def mle_theta(ks, hits, shots) -> float:
    """Maximum-likelihood theta: grid argmax on [EPS, pi/2 - EPS], then golden-section refinement."""
    ks, hits, shots = list(ks), list(hits), list(shots)
    if not ks or not len(ks) == len(hits) == len(shots):
        raise ValueError("ks, hits and shots must be non-empty and of equal length")
    grid = np.linspace(EPS, np.pi / 2 - EPS, grid_size(ks))
    ll = loglikelihood(grid, ks, hits, shots); i = int(np.argmax(ll))
    a, b = grid[max(i - 1, 0)], grid[min(i + 1, grid.size - 1)]
    return golden_max(lambda t: loglikelihood(t, ks, hits, shots), float(a), float(b), float(grid[i]), float(ll[i]))


def fisher_se(theta: float, ks, shots) -> float:
    """Asymptotic Fisher standard error of a = sin^2 theta; zero at a in {0, 1}."""
    info = sum(4 * int(n) * (2 * int(k) + 1) ** 2 for k, n in zip(ks, shots))
    return float(abs(math.sin(2 * theta)) / math.sqrt(info))


@dataclass(frozen=True)
class MLAEResult:
    """An MLAE estimate with its Fisher standard error and the honest cost N_A."""

    a_hat: float
    theta: float
    se: float
    n_A: int
    ks: tuple
    shots: tuple
    hits: tuple
    shots_total: int
    records: tuple

    def as_dict(self) -> dict:
        """JSON-ready plain types (records omitted; tuples become lists)."""
        return {"a_hat": float(self.a_hat), "theta": float(self.theta), "se": float(self.se),
                "n_A": int(self.n_A), "ks": list(self.ks), "shots": list(self.shots),
                "hits": list(self.hits), "shots_total": int(self.shots_total)}


def estimate(records) -> MLAEResult:
    """MLAE over PowerResult records (any order; same-k records combine additively)."""
    records = list(records)
    if not records:
        raise ValueError("estimate needs at least one PowerResult")
    for r in records:
        if not isinstance(r, PowerResult):
            raise TypeError(f"estimate takes PowerResult records, got {type(r).__name__}")
    unsampled = [r for r in records if not r.sampled]
    if unsampled:
        raise ValueError(f"{len(unsampled)} record(s) hold rounded counts (not Binomial samples), "
                         f"e.g. source {unsampled[0].source!r}; MLAE needs sampled counts")
    records = sorted(records, key=lambda r: (r.k, r.shots, r.hits, r.source))
    ks = tuple(r.k for r in records)
    shots = tuple(r.shots for r in records)
    hits = tuple(r.hits for r in records)
    theta = mle_theta(ks, hits, shots)
    return MLAEResult(a_hat=math.sin(theta) ** 2, theta=theta, se=fisher_se(theta, ks, shots),
                      n_A=n_applications(records), ks=ks, shots=shots, hits=hits,
                      shots_total=int(sum(shots)), records=tuple(records))


def _check_m(M) -> int:
    if isinstance(M, bool) or not isinstance(M, numbers.Integral) or M < 1:
        raise ValueError(f"M must be an integer >= 1, got {M!r}")
    return int(M)


def exponential_schedule(M: int) -> list[int]:
    """Headline schedule [0, 1, 2, 4, ..., 2^(M-2)] (M powers; M = 1 gives [0])."""
    return [0] + [2 ** j for j in range(_check_m(M) - 1)]


def linear_schedule(M: int) -> list[int]:
    """Comparison schedule [0, 1, ..., M - 1]."""
    return list(range(_check_m(M)))
