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
from neutron_qae.exact import N_BITS, bitstring_probabilities_k1
from neutron_qae.mc_lattice import run_lattice, sample_exit_rows
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


# ---------------------------------------------------------------- exit histograms (PD-27, ANLY-02)

def classical_exit_rows(kernels, shots, seed_seq) -> dict:
    """Back-face exit-row counts of ``shots`` lattice histories (``run_lattice``)."""
    shots = _check_int("shots", shots, 1)
    res = run_lattice(kernels, shots, seed_seq)
    rows = [int(c) for c in res.row_counts]
    transmitted = int(res.transmitted)
    if sum(rows) != transmitted:
        raise AssertionError(f"classical row counts sum to {sum(rows)}, transmitted is {transmitted}")
    return {"row_counts": rows, "no_back_exit": shots - transmitted, "transmitted": transmitted, "shots": shots}


def quantum_exit_rows(backend, problem, shots, seed_simulator, row_source) -> dict:
    """Back-face exit-row counts from ``shots`` direct samples of A (k = 0, every qubit measured).

    One ``backend.run`` of the transpiled A circuit (``BackendRunner(..., measure="all")``).
    Every count key must be a binary string of ``problem.qubits`` characters and the counts must
    sum to ``shots`` (ValueError otherwise). Key character 0 is the flag; ``int(key, 2) & 0x7FF``
    is exact.py's 11-bit string s. Keys are sorted ascending, expanded with ``np.repeat`` and fed
    to the same ``mc_lattice.sample_exit_rows`` the lattice engine uses, with ``row_source``.
    ``outside_support`` counts shots on zero-amplitude strings (sample_exit_rows maps them to -1,
    indistinguishable from no back-face exit, so they are counted against the exact support);
    ``flag_mismatch`` counts shots whose flag disagrees with the string's transmitted predicate.
    """
    shots = _check_int("shots", shots, 1)
    n_bits = problem.qubits
    if n_bits != N_BITS + 1:
        raise ValueError(f"quantum_exit_rows needs the Q1 layout ({N_BITS + 1} qubits), got {n_bits}")
    circuit = BackendRunner(backend, problem, measure="all").circuits([0])[0]
    counts = dict(backend.run(circuit, shots=shots, seed_simulator=seed_simulator).result().get_counts(0))
    total = 0
    for key, value in counts.items():
        if not isinstance(key, str) or len(key) != n_bits or set(key) - {"0", "1"}:
            raise ValueError(f"count key {key!r} is not a {n_bits}-character binary string")
        if not _is_int(value) or value < 0:
            raise ValueError(f"count for {key!r} must be a non-negative integer, got {value!r}")
        total += int(value)
    if total != shots:
        raise ValueError(f"counts sum to {total}, expected shots = {shots}")
    keys = sorted(counts)
    vals = np.array([int(counts[key]) for key in keys], dtype=np.int64)
    full = np.array([int(key, 2) for key in keys], dtype=np.int64)
    s = full & ((1 << N_BITS) - 1)
    flag = (full >> N_BITS) & 1
    table = {int(sv): (p, bool(t)) for sv, p, t in bitstring_probabilities_k1(problem.kernels)}
    outside = mismatch = 0
    for sv, f, v in zip(s.tolist(), flag.tolist(), vals.tolist()):
        p, t = table.get(sv, (0.0, False))
        if p <= 0.0:
            outside += v
        if bool(f) != t:
            mismatch += v
    rows = sample_exit_rows(problem.kernels, np.repeat(s, vals), row_source)
    ny = problem.kernels.spec.ny
    row_counts = [int(c) for c in np.bincount(rows[rows >= 0], minlength=ny)]
    return {"row_counts": row_counts, "no_back_exit": shots - sum(row_counts),
            "flag_hits": int(vals[flag == 1].sum()), "outside_support": int(outside),
            "flag_mismatch": int(mismatch), "distinct_strings": len(keys), "shots": shots}


def chi2_bound(dof) -> float:
    """The project's chi-square acceptance bound dof + 5 sqrt(2 dof) (Phase 3 convention)."""
    dof = _check_int("dof", dof, 1)
    return float(dof + 5.0 * math.sqrt(2.0 * dof))


def _counts_array(name, v):
    a = np.asarray(v)
    if a.ndim != 1 or a.size < 2 or not np.issubdtype(a.dtype, np.integer) or np.any(a < 0):
        raise ValueError(f"{name} must be a 1-D sequence of at least 2 non-negative integer counts")
    return a.astype(np.int64)


def chi2_two_sample(a, b) -> dict:
    """Two-sample chi-square for equal totals: sum (a - b)^2 / (a + b) over categories with a + b > 0."""
    a, b = _counts_array("a", a), _counts_array("b", b)
    if a.shape != b.shape:
        raise ValueError(f"a and b must have the same number of categories, got {a.size} and {b.size}")
    if int(a.sum()) != int(b.sum()):
        raise ValueError(f"chi2_two_sample needs equal totals, got {int(a.sum())} and {int(b.sum())}")
    used = (a + b) > 0
    dof = int(used.sum()) - 1
    if dof < 1:
        raise ValueError("chi2_two_sample needs at least 2 non-empty categories")
    d = (a - b)[used].astype(np.float64)
    value = float(np.sum(d * d / (a + b)[used]))
    return {"value": value, "dof": dof, "bound": chi2_bound(dof)}


def chi2_goodness(counts, probs) -> dict:
    """Goodness of fit sum (c - S p)^2 / (S p) over categories with p > 0; dof = those - 1."""
    c = _counts_array("counts", counts)
    p = np.asarray(probs, dtype=np.float64)
    if p.shape != c.shape:
        raise ValueError(f"probs must have {c.size} entries, got {p.size}")
    if not np.all(np.isfinite(p)) or np.any(p < 0):
        raise ValueError("probs must be finite and non-negative")
    if abs(math.fsum(p.tolist()) - 1.0) > 1e-12:
        raise ValueError(f"probs must sum to 1 within 1e-12, got {math.fsum(p.tolist())!r}")
    if np.any(c[p == 0] > 0):
        raise ValueError("a category with probability 0 has counts")
    n = int(c.sum())
    if n < 1:
        raise ValueError("chi2_goodness needs at least one count")
    used = p > 0
    dof = int(used.sum()) - 1
    if dof < 1:
        raise ValueError("chi2_goodness needs at least 2 categories with p > 0")
    e = n * p[used]
    value = float(np.sum((c[used] - e) ** 2 / e))
    return {"value": value, "dof": dof, "bound": chi2_bound(dof)}


# ---------------------------------------------------------------- thickness study (PD-29, ANLY-04)

def check_transmission(T1, n_max, min_events=1000) -> float:
    """Underflow guard for a rare-event wall: return T1 or raise ValueError.

    The classical grid must observe at least ``min_events`` transmitted histories at its largest
    N (expected count ``T1 * n_max``, inclusive) or its RMSE curve cannot reach a 1% relative
    target; T1 must be a finite number in (0, 1).
    """
    if isinstance(T1, bool) or not isinstance(T1, numbers.Real) or not math.isfinite(T1) or not 0.0 < T1 < 1.0:
        raise ValueError(f"T1 must be a finite number in (0, 1), got {T1!r}")
    if isinstance(n_max, bool) or not isinstance(n_max, numbers.Real) or not math.isfinite(n_max) or n_max <= 0:
        raise ValueError(f"n_max must be a finite positive number, got {n_max!r}")
    expected = float(T1) * float(n_max)
    if not expected >= min_events:
        raise ValueError(f"expected {expected:.1f} transmitted histories at N = {n_max:g} (T1 = {float(T1):.3e}), "
                         f"below the {min_events}-event limit: the classical curve cannot reach the target")
    return float(T1)
