"""Vendored MLAE (neutron_qae/mlae.py): QAE-01 parity, QAE-03 cost and the probe edges.

qiskit-algorithms and qiskit-aer are local dev extras only (importorskip); the package module
itself imports numpy and the stdlib alone.
"""
from __future__ import annotations

import itertools
import math
import time
from pathlib import Path

import numpy as np
import pytest
import random_doubles
from qiskit import QuantumCircuit

from neutron_qae.mlae import (
    EPS,
    MAX_POWER,
    MLAEResult,
    PowerResult,
    estimate,
    exponential_schedule,
    golden_max,
    grid_size,
    linear_schedule,
    loglikelihood,
    mle_theta,
    n_applications,
)

ROOT = Path(__file__).resolve().parents[1]
T1 = 0.24300446519524305                       # frozen exact T1 (scripts/freeze_kernels.py)
TH1 = math.asin(math.sqrt(T1))


def _single_qubit_cases():
    """6 seeded binomial cases on a one-qubit A = RY(2 theta_T1): (ks, hits, shots)."""
    rng = np.random.default_rng(7)
    cases = []
    for M in (1, 2, 3):
        ks = exponential_schedule(M)
        for s in (10, 1000):
            hits = [int(rng.binomial(s, math.sin((2 * k + 1) * TH1) ** 2)) for k in ks]
            cases.append((ks, hits, [s] * len(ks)))
    return cases


def _one_qubit_problem():
    from qiskit_algorithms import EstimationProblem

    A = QuantumCircuit(1)
    A.ry(2 * TH1, 0)
    return EstimationProblem(A, objective_qubits=[0])


def _counts(hits, shots):
    return [{"1": h, "0": n - h} for h, n in zip(hits, shots)]


@pytest.fixture(scope="module")
def aer_case():
    """ks [0, 1, 2, 4, 8] x 200 shots on Q1 from ONE Aer list job (seed_simulator 5)."""
    pytest.importorskip("qiskit_aer")
    pytest.importorskip("qiskit_algorithms")
    from qiskit_aer import AerSimulator
    from qiskit_algorithms import EstimationProblem

    from neutron_qae.oracle import make_problem
    from neutron_qae.runners import BackendRunner

    problem = make_problem("Q1")
    runner = BackendRunner(AerSimulator(method="statevector"), problem, run_options={"seed_simulator": 5})
    ks = [0, 1, 2, 4, 8]
    recs = runner.run(ks, 200)
    hits = [r.hits for r in recs]
    return ks, hits, [200] * len(ks), runner.last_counts, EstimationProblem(problem.A, objective_qubits=[problem.flag])


def _all_cases(aer_case):
    ks, hits, shots, counts, prob = aer_case
    out = [(ks, hits, shots, counts, prob)]
    p1 = _one_qubit_problem()
    out += [(k, h, s, _counts(h, s), p1) for k, h, s in _single_qubit_cases()]
    return out


# --- tracer edge -------------------------------------------------------------------------------

def test_k0_only_estimate_is_hit_fraction():
    r = estimate([PowerResult(0, 100, 37)])
    assert abs(r.a_hat - 0.37) <= 1e-7, r.a_hat
    se = math.sqrt(0.37 * 0.63 / 100)
    assert abs(r.se - se) <= 1e-6 * se, (r.se, se)
    assert r.n_A == 100 and r.shots_total == 100


# --- QAE-01 parity -----------------------------------------------------------------------------

def test_brute_on_our_likelihood_equals_qiskit_compute_mle(aer_case):
    from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation
    from scipy.optimize import brute

    assert aer_case[1] == [40, 200, 70, 199, 80], aer_case[1]
    for ks, hits, shots, counts, prob in _all_cases(aer_case):
        theta_q = MaximumLikelihoodAmplitudeEstimation(ks).compute_mle(counts, prob)
        theta_b = brute(lambda t, ks=ks, hits=hits, shots=shots: -loglikelihood(np.atleast_1d(t)[0], ks, hits, shots),
                        [[EPS, math.pi / 2 - EPS]], Ns=grid_size(ks))[0]
        assert abs(theta_b - theta_q) <= 1e-12, (ks, hits, shots, theta_b, theta_q)
    ks, hits, shots, counts, prob = aer_case
    theta_q = MaximumLikelihoodAmplitudeEstimation(ks).compute_mle(counts, prob)
    assert abs(math.sin(theta_q) ** 2 - 0.2413897286) < 1e-9, math.sin(theta_q) ** 2


def _our_minimizer(ks):
    """qiskit-algorithms minimizer (fun, bounds) -> theta: our grid argmin + golden_max refinement."""
    def minimizer(fun, bounds):
        lo, hi = bounds[0]
        grid = np.linspace(lo, hi, grid_size(ks))
        vals = np.asarray(fun(grid), dtype=float)
        i = int(np.argmin(vals))
        a, b = grid[max(i - 1, 0)], grid[min(i + 1, grid.size - 1)]
        return golden_max(lambda t: -float(fun(t)), float(a), float(b), float(grid[i]), -float(vals[i]))
    return minimizer


def test_qiskit_with_our_minimizer_equals_estimate(aer_case):
    from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation

    worst = 0.0
    for ks, hits, shots, counts, prob in _all_cases(aer_case):
        theta_q = MaximumLikelihoodAmplitudeEstimation(ks, minimizer=_our_minimizer(ks)).compute_mle(counts, prob)
        theta_v = mle_theta(ks, hits, shots)
        assert abs(theta_q - theta_v) <= 1e-8, (ks, hits, theta_q, theta_v)
        records = [PowerResult(k, n, h) for k, h, n in zip(ks, hits, shots)]
        assert abs(estimate(records).theta - theta_v) <= 1e-15
        worst = max(worst, abs(theta_q - theta_v))
    assert worst <= 1e-8, worst


def test_vendored_beats_or_matches_qiskit_default(aer_case):
    from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation

    for ks, hits, shots, counts, prob in _all_cases(aer_case):
        theta_q = MaximumLikelihoodAmplitudeEstimation(ks).compute_mle(counts, prob)
        theta_v = mle_theta(ks, hits, shots)
        da = math.sin(theta_v) ** 2 - math.sin(theta_q) ** 2
        assert abs(da) <= 1e-4, (ks, hits, da)
        assert loglikelihood(theta_v, ks, hits, shots) >= loglikelihood(theta_q, ks, hits, shots) - 1e-9


# --- QAE-03 cost -------------------------------------------------------------------------------

@pytest.mark.filterwarnings("ignore::DeprecationWarning")   # qiskit-algorithms builds GroverOperator
def test_cost_is_applications_not_oracle_queries():
    pytest.importorskip("qiskit_algorithms")
    from qiskit.primitives import StatevectorSampler
    from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation

    ks = [0, 1, 2, 4]
    result = MaximumLikelihoodAmplitudeEstimation(ks, sampler=StatevectorSampler(default_shots=100, seed=1)) \
        .estimate(_one_qubit_problem())
    assert result.num_oracle_queries == 700          # shots x sum k: drops A, A-dagger and k = 0
    records = []
    for k, c in zip(ks, result.circuit_results):
        assert set(c) <= {"0", "1"}, c
        records.append(PowerResult(k, sum(c.values()), c.get("1", 0)))
    assert n_applications(records) == 1800           # sum shots (2k + 1)
    assert estimate(records).n_A == 1800
    assert n_applications([PowerResult(0, 1000, 1), PowerResult(1, 1000, 1), PowerResult(2, 1000, 1)]) == 9000
    assert n_applications([]) == 0
    fields = set(MLAEResult.__dataclass_fields__)
    assert {"n_A", "shots_total"} <= fields
    assert not [f for f in fields if "quer" in f.lower()]


# --- QAE-01 probe edges ------------------------------------------------------------------------

def test_boundary_estimates():
    zero = estimate([PowerResult(k, 100, 0) for k in (0, 1, 2)])
    assert zero.a_hat < 1e-12, zero.a_hat
    one = estimate([PowerResult(0, 100, 100)])
    assert one.a_hat > 1 - 1e-12, one.a_hat
    ends = loglikelihood(np.array([EPS, math.pi / 2 - EPS]), [0, 1], [0, 5], [5, 5])
    assert np.isfinite(ends).all(), ends


def test_same_k_records_merge():
    split = estimate([PowerResult(0, 100, 24), PowerResult(1, 100, 99), PowerResult(1, 100, 100)])
    merged = estimate([PowerResult(0, 100, 24), PowerResult(1, 200, 199)])
    assert abs(split.a_hat - merged.a_hat) <= 1e-9, (split.a_hat, merged.a_hat)
    assert abs(merged.a_hat - 0.2303832230732557) <= 1e-9, merged.a_hat
    assert split.n_A == merged.n_A == 700


def test_empty_and_invalid_records():
    with pytest.raises(ValueError):
        estimate([])
    with pytest.raises(TypeError):
        estimate([object()])
    for kwargs in (dict(k=0, shots=0, hits=0), dict(k=0, shots=100, hits=101), dict(k=0, shots=100, hits=-1),
                   dict(k=-1, shots=10, hits=1), dict(k=MAX_POWER + 1, shots=10, hits=1),
                   dict(k=True, shots=10, hits=1), dict(k=1.5, shots=10, hits=1),
                   dict(k=0, shots=10.0, hits=1), dict(k=0, shots=10, hits=False),
                   dict(k=0, shots=10, hits=1, sampled=1)):
        with pytest.raises(ValueError):
            PowerResult(**kwargs)
    r = PowerResult(np.int64(2), np.int64(10), np.int64(3))
    assert (type(r.k), type(r.shots), type(r.hits)) == (int, int, int)
    assert (r.k, r.shots, r.hits) == (2, 10, 3)


def test_estimate_is_order_invariant():
    records = [PowerResult(4, 50, 49, "b"), PowerResult(0, 100, 23, "a"), PowerResult(1, 100, 99),
               PowerResult(2, 80, 25), PowerResult(1, 60, 60)]
    fwd, rev = estimate(records), estimate(list(reversed(records)))
    assert fwd.a_hat == rev.a_hat and fwd.theta == rev.theta and fwd.ks == rev.ks
    assert fwd.ks == (0, 1, 1, 2, 4)
    assert fwd.shots == (100, 60, 100, 80, 50) and fwd.hits == (23, 60, 99, 25, 49)


def test_no_nan_anywhere():
    ks = [0, 1, 2, 4]
    grid = np.linspace(EPS, math.pi / 2 - EPS, grid_size(ks))
    for hits in itertools.product((0, 10), repeat=len(ks)):
        ll = loglikelihood(grid, ks, hits, [10] * len(ks))
        assert not np.isnan(ll).any(), hits
        a = estimate([PowerResult(k, 10, h) for k, h in zip(ks, hits)]).a_hat
        assert math.isfinite(a) and 0.0 <= a <= 1.0, (hits, a)


def test_unsampled_records_are_rejected():
    with pytest.raises(ValueError, match="rounded counts"):
        estimate([PowerResult(0, 100, 24), PowerResult(1, 100, 99, source="ionq:forte-1", sampled=False)])


def test_schedules():
    assert exponential_schedule(1) == [0]
    assert exponential_schedule(5) == [0, 1, 2, 4, 8]
    assert linear_schedule(4) == [0, 1, 2, 3]
    for bad in (0, -1, True, 2.0):
        with pytest.raises(ValueError):
            exponential_schedule(bad)
        with pytest.raises(ValueError):
            linear_schedule(bad)


def test_mlae_is_numpy_only():
    assert random_doubles.foreign_imports(ROOT / "neutron_qae" / "mlae.py") == set()


def test_large_power_is_fast_and_capped():
    t = time.perf_counter()
    theta = mle_theta([0, 1, 2, 4, 8, 16, 32, 64], [24] * 8, [100] * 8)
    assert time.perf_counter() - t < 1.0
    assert math.isfinite(theta)
    with pytest.raises(ValueError):
        PowerResult(2048, 10, 1)


def test_as_dict_is_plain_json():
    import json

    r = estimate([PowerResult(0, 100, 24), PowerResult(1, 100, 99)])
    d = r.as_dict()
    assert json.loads(json.dumps(d)) == d
    assert set(d) == {"a_hat", "theta", "se", "n_A", "ks", "shots", "hits", "shots_total"}
