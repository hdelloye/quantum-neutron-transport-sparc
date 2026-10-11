"""RMSE-versus-cost series and log-log fits for the Phase 5 scaling study (PD-25, PD-26).

PD-25 (headline design): the matched classical lattice Monte Carlo (cost N = histories) is
compared with MLAE on the exponential schedule (cost N_A = sum shots (2k + 1), i.e.
applications of A; never shots and never qiskit-algorithms num_oracle_queries), both measured
against the exact T1. Each point is an RMSE over R independent repetitions in a nested design:
one repetition is one experiment observed at increasing cost (classical checkpoints within one
run; MLAE estimates on the first M records of one schedule run). RMSE = sqrt(mean(err^2)); the
band is the 16th-84th percentile of |err|. Fits are OLS of log10 RMSE on log10 cost with slope
SE sqrt(SSR / (n - 2) / Sxx); classical over all points, MLAE over M >= 2.

PD-26 (reproducibility): every series takes a ``numpy.random.SeedSequence`` and spawns one child
per repetition, so the same seed, code and numpy (and qiskit-aer) versions give the same numbers.

Nothing here constructs a backend (the Aer backend is injected by the sweep script) and nothing
runs at import time. Per-run Wald SEs are never used: they collapse at small N and at a in {0, 1}.
"""
from __future__ import annotations

import itertools
import math
import numbers

import numpy as np

from neutron_qae import mlae
from neutron_qae.mc_lattice import run_lattice
from neutron_qae.runners import AnalyticRunner, BackendRunner


def _is_int(v) -> bool:
    return isinstance(v, numbers.Integral) and not isinstance(v, bool)


def _check_int(name, v, minimum):
    if not _is_int(v) or v < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {v!r}")
    return int(v)


def summarize_errors(errors) -> dict:
    """rmse, mean_error and the 16th/84th percentiles of |error| over repetitions."""
    err = np.asarray(errors, dtype=np.float64).ravel()
    if err.size < 2:
        raise ValueError(f"summarize_errors needs at least 2 errors, got {err.size}")
    if not np.all(np.isfinite(err)):
        raise ValueError("summarize_errors got a non-finite error")
    a = np.abs(err)
    return {"rmse": float(np.sqrt(np.mean(err ** 2))), "mean_error": float(err.mean()),
            "abs_err_q16": float(np.quantile(a, 0.16)), "abs_err_q84": float(np.quantile(a, 0.84))}


def _columns(E, cost) -> dict:
    cols = [summarize_errors(E[:, j]) for j in range(E.shape[1])]
    out = {"cost": [int(c) for c in cost]}
    for key in ("rmse", "mean_error", "abs_err_q16", "abs_err_q84"):
        out[key] = [c[key] for c in cols]
    return out


def classical_rmse_series(kernels, reference, n_grid, reps, seed_seq) -> dict:
    """Classical lattice MC: one run of n_grid[-1] histories per repetition, read at the checkpoints."""
    n_grid = tuple(n_grid)
    if not n_grid or not all(_is_int(n) and n >= 1 for n in n_grid):
        raise ValueError(f"n_grid must be a non-empty sequence of integers >= 1, got {n_grid!r}")
    if any(b <= a for a, b in itertools.pairwise(n_grid)):
        raise ValueError(f"n_grid must be strictly ascending, got {n_grid!r}")
    reps = _check_int("reps", reps, 2)
    n_grid = tuple(int(n) for n in n_grid)
    E = np.empty((reps, len(n_grid)))
    for r, child in enumerate(seed_seq.spawn(reps)):
        res = run_lattice(kernels, n_grid[-1], child, checkpoints=n_grid)
        E[r] = res.prefix_estimates()[1] - reference
    out = _columns(E, n_grid)
    out.update({"repetitions": reps, "cost_unit": "histories", "runner": "lattice"})
    return out


def _mlae_rows(records_per_rep, reference, m_max):
    """Errors (reps x m_max) and the common cost N_A of the first M records, M = 1..m_max."""
    E = np.empty((len(records_per_rep), m_max))
    cost = None
    for r, records in enumerate(records_per_rep):
        row_cost = []
        for M in range(1, m_max + 1):
            res = mlae.estimate(records[:M])
            E[r, M - 1] = res.a_hat - reference
            row_cost.append(int(res.n_A))
        if cost is None:
            cost = row_cost
        elif row_cost != cost:
            raise AssertionError(f"MLAE cost differs between repetitions: {row_cost} vs {cost}")
    return E, cost


def _mlae_series(E, cost, reps, shots, runner) -> dict:
    out = _columns(E, cost)
    out.update({"repetitions": reps, "cost_unit": "applications of A", "runner": runner,
                "M": list(range(1, len(cost) + 1)), "shots_per_power": shots, "schedule": "exponential"})
    return out


def mlae_rmse_series(p, reference, m_max, shots, reps, seed_seq) -> dict:
    """Analytic MLAE (exact theta, Binomial draws): one schedule run per repetition, nested prefixes."""
    m_max = _check_int("m_max", m_max, 1)
    shots = _check_int("shots", shots, 1)
    reps = _check_int("reps", reps, 2)
    schedule = mlae.exponential_schedule(m_max)
    runs = [AnalyticRunner(p, child).run(schedule, shots) for child in seed_seq.spawn(reps)]
    E, cost = _mlae_rows(runs, reference, m_max)
    return _mlae_series(E, cost, reps, shots, "analytic")


def backend_rmse_series(backend, problem, reference, m_max, shots, reps, seed_simulator) -> dict:
    """MLAE on an injected local backend (Aer): ONE job, repetitions read as blocks of shot memory.

    The circuits for ``exponential_schedule(m_max)`` come from ``BackendRunner(backend,
    problem).circuits`` (contract-checked problem, transpiled once) and are submitted in one
    ``backend.run(circuits, shots=reps * shots, memory=True, seed_simulator=...)``. Repetition r
    reads shots [shots r, shots (r + 1)) of every circuit. Shots of one fixed circuit are iid, so
    these blocks are statistically identical to separately seeded jobs of ``shots`` shots each.
    The rejected alternative, ``BackendRunner.run`` once per repetition, measured 1.7 s per
    repetition at M = 7 and 3.4 s at M = 8 (86 s and 171 s for 50 repetitions).
    """
    m_max = _check_int("m_max", m_max, 1)
    shots = _check_int("shots", shots, 1)
    reps = _check_int("reps", reps, 2)
    ks = mlae.exponential_schedule(m_max)
    circuits = BackendRunner(backend, problem).circuits(ks)
    total = reps * shots
    result = backend.run(circuits, shots=total, memory=True, seed_simulator=seed_simulator).result()
    hits = np.empty((len(ks), reps), dtype=np.int64)
    for i in range(len(ks)):
        memory = result.get_memory(i)
        if len(memory) != total:
            raise ValueError(f"circuit {i}: expected {total} memory entries, got {len(memory)}")
        if not set(memory) <= {"0", "1"}:
            raise ValueError(f"circuit {i}: memory entries must be '0' or '1', got {sorted(set(memory))[:3]}")
        bits = np.fromiter((b == "1" for b in memory), dtype=np.int64, count=total)
        hits[i] = bits.reshape(reps, shots).sum(axis=1)
    runs = [[mlae.PowerResult(k, shots, int(hits[i, r]), source="aer") for i, k in enumerate(ks)]
            for r in range(reps)]
    E, cost = _mlae_rows(runs, reference, m_max)
    return _mlae_series(E, cost, reps, shots, "aer")


def loglog_fit(cost, rmse) -> dict:
    """OLS of log10 rmse on log10 cost: slope, intercept (log10 RMSE at cost 1), slope_se, range."""
    c = np.asarray(cost, dtype=np.float64)
    y = np.asarray(rmse, dtype=np.float64)
    if c.ndim != 1 or c.shape != y.shape:
        raise ValueError("cost and rmse must be 1-D sequences of equal length")
    if c.size < 3:
        raise ValueError(f"loglog_fit needs at least 3 points, got {c.size}")
    if not (np.all(np.isfinite(c)) and np.all(np.isfinite(y))):
        raise ValueError("loglog_fit got a non-finite cost or rmse")
    if not (np.all(c > 0) and np.all(y > 0)):
        raise ValueError("loglog_fit needs positive cost and rmse")
    if not np.all(np.diff(c) > 0):
        raise ValueError("loglog_fit needs strictly ascending cost (no duplicate cost values)")
    x = np.log10(c)
    ly = np.log10(y)
    xm, ym = x.mean(), ly.mean()
    sxx = float(((x - xm) ** 2).sum())
    slope = float(((x - xm) * (ly - ym)).sum() / sxx)
    intercept = float(ym - slope * xm)
    resid = ly - (intercept + slope * x)
    slope_se = math.sqrt(float((resid ** 2).sum()) / (c.size - 2) / sxx)
    out_cost = [int(v) if float(v).is_integer() else float(v) for v in (c[0], c[-1])]
    return {"slope": slope, "intercept": intercept, "slope_se": float(slope_se), "points": int(c.size),
            "cost_min": out_cost[0], "cost_max": out_cost[1]}


def fit_series(series, min_M=None) -> dict:
    """loglog_fit over the series points with M >= min_M (MLAE) or over all points (min_M None)."""
    cost, rmse = series["cost"], series["rmse"]
    if min_M is None:
        idx = list(range(len(cost)))
    else:
        idx = [i for i, M in enumerate(series["M"]) if M >= min_M]
    return loglog_fit([cost[i] for i in idx], [rmse[i] for i in idx])


def cost_at_target(cost, rmse, target):
    """Cost at which the RMSE curve first reaches ``target`` (log-log interpolation), or None.

    Scans ascending cost for the first point with rmse <= target and interpolates linearly in
    log10-log10 between it and the previous point; an exact hit returns that cost exactly. None
    when the first point is already at or below the target (not bracketed) or it is never reached.
    """
    c = np.asarray(cost, dtype=np.float64)
    y = np.asarray(rmse, dtype=np.float64)
    if c.ndim != 1 or c.shape != y.shape or c.size < 2:
        raise ValueError("cost_at_target needs at least 2 points of equal-length cost and rmse")
    if not (np.all(np.isfinite(c)) and np.all(np.isfinite(y)) and np.all(c > 0) and np.all(y > 0)):
        raise ValueError("cost_at_target needs finite positive cost and rmse")
    if not np.all(np.diff(c) > 0):
        raise ValueError("cost_at_target needs strictly ascending cost")
    if isinstance(target, bool) or not isinstance(target, numbers.Real) or not math.isfinite(target) \
            or target <= 0:
        raise ValueError(f"target must be a finite positive number, got {target!r}")
    if y[0] <= target:
        return None
    lt = math.log10(target)
    for i in range(1, c.size):
        if y[i] == target:
            return float(c[i])
        if y[i] < target:
            lc0, lc1 = math.log10(c[i - 1]), math.log10(c[i])
            ly0, ly1 = math.log10(y[i - 1]), math.log10(y[i])
            f = (lt - ly0) / (ly1 - ly0)
            return float(10 ** (lc0 + f * (lc1 - lc0)))
    return None
