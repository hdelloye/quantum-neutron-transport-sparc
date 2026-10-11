"""Runners (neutron_qae/runners.py): QAE-02 interface, QAE-04 agreement, IonQ one-circuit path.

Backends are constructed only here (BasicSimulator, AerSimulator via importorskip, and the
FakeIonQSimulator double from tests/ionq_fakes.py); the package never builds one.
"""
from __future__ import annotations

import copy
import json
import math
import os

import numpy as np
import pytest
from ionq_fakes import FakeIonQSimulator
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator

from neutron_qae import mlae, runners
from neutron_qae.grover import check_ionq_safe
from neutron_qae.oracle import make_problem
from neutron_qae.runners import (
    AnalyticRunner,
    BackendRunner,
    IonQRunner,
    Runner,
    hits_from_counts,
    ionq_estimate,
    ionq_power_results,
    load_ionq_records,
    validate_ionq_record,
)

SLOW = pytest.mark.skipif(os.environ.get("NEUTRON_QAE_SLOW") != "1",
                          reason="Aer MLAE repetitions; run with NEUTRON_QAE_SLOW=1 -m slow")


class _RunSpy:
    """Wraps a backend and records every run() input; everything else passes through."""

    def __init__(self, inner):
        self._inner = inner
        self.calls = []

    def run(self, run_input, **options):
        self.calls.append((run_input, options))
        return self._inner.run(run_input, **options)

    def __getattr__(self, name):
        return getattr(self._inner, name)


@pytest.fixture(scope="module")
def problem():
    return make_problem("Q1")


@pytest.fixture(scope="module")
def ionq_records(problem):
    """Fake-IonQ records: k = 0, 1, 2 ideal (1000 shots, seeds 0, 1, 2) and one noisy k = 0."""
    recs = {}
    for k in (0, 1, 2):
        fake = FakeIonQSimulator()
        fake.set_options(seed_simulator=k)
        recs[k] = IonQRunner(fake, problem).run_point(k, 1000)
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=10)
    recs["noisy0"] = IonQRunner(fake, problem, ideal_mode="none").run_point(0, 1000)
    return recs


# --- tracer ------------------------------------------------------------------------------------

def test_builtin_list_job_to_mlae_estimate(problem):
    b = BasicSimulator()
    b.set_options(seed_simulator=2026)
    spy = _RunSpy(b)
    recs = BackendRunner(spy, problem).run([0, 1, 2, 4], 1000)
    assert len(spy.calls) == 1
    run_input, options = spy.calls[0]
    assert isinstance(run_input, list) and len(run_input) == 4
    assert all(isinstance(c, QuantumCircuit) for c in run_input)
    assert options == {"shots": 1000}
    hits = [r.hits for r in recs]
    assert hits == [262, 1000, 277, 997], hits
    assert [r.k for r in recs] == [0, 1, 2, 4]
    r = mlae.estimate(recs)
    assert abs(r.a_hat - 0.245094) < 5e-7, r.a_hat
    assert abs(r.a_hat - problem.reference - 2.09e-3) < 5e-6, r.a_hat - problem.reference
    assert r.n_A == 18000
    assert abs(r.se - 1.26e-3) < 1e-5, r.se


# --- QAE-02 interface --------------------------------------------------------------------------

def test_runners_share_one_interface(problem):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=1)
    all_runners = [AnalyticRunner(problem.p, np.random.default_rng(1)),
                   BackendRunner(BasicSimulator(), problem),
                   IonQRunner(fake, problem)]
    for r in all_runners:
        assert isinstance(r, Runner), r
        out = r.run([1], 100)
        assert len(out) == 1 and isinstance(out[0], mlae.PowerResult), out
        assert (out[0].k, out[0].shots) == (1, 100)
        assert out[0].sampled is True
    assert [r.name for r in all_runners] == ["analytic", "backend:basic_simulator", "ionq"]
    assert len(fake.calls) == 1 and isinstance(fake.calls[0], QuantumCircuit)


def test_analytic_draw_order_is_documented(problem):
    out = AnalyticRunner(problem.p, np.random.default_rng(404)).run([0, 1, 2, 8], 4000)
    rng = np.random.default_rng(404)
    expected = [int(rng.binomial(4000, math.sin((2 * k + 1) * problem.theta) ** 2)) for k in (0, 1, 2, 8)]
    assert [r.hits for r in out] == expected
    assert [r.source for r in out] == ["analytic"] * 4
    with pytest.raises(ValueError):
        AnalyticRunner(1.5)
    with pytest.raises(ValueError):
        AnalyticRunner(True)
    with pytest.raises(ValueError):
        AnalyticRunner(0.2).run([], 10)
    with pytest.raises(ValueError):
        AnalyticRunner(0.2).run([0, 1], [10])


# --- QAE-04 analytic vs Aer --------------------------------------------------------------------

def test_analytic_and_aer_agree(problem):
    pytest.importorskip("qiskit_aer")
    from qiskit_aer import AerSimulator

    ks, shots = [0, 1, 2, 8], 4000
    h_aer = [r.hits for r in BackendRunner(AerSimulator(method="statevector"), problem,
                                           run_options={"seed_simulator": 404}).run(ks, shots)]
    h_an = [r.hits for r in AnalyticRunner(problem.p, np.random.default_rng(404)).run(ks, shots)]
    msg = f"Aer {h_aer} vs analytic {h_an}"
    for k, ha, hn in zip(ks, h_aer, h_an):
        pk = math.sin((2 * k + 1) * problem.theta) ** 2
        sig = math.sqrt(shots * pk * (1 - pk))
        assert abs(ha - hn) <= 4 * math.sqrt(2) * sig + 1, (k, msg)
        assert abs(ha - shots * pk) <= 4 * sig + 1, (k, msg)
        assert abs(hn - shots * pk) <= 4 * sig + 1, (k, msg)
    assert h_aer == [973, 3998, 1178, 1521], msg
    assert h_an == [970, 3999, 1164, 1541], msg


def _rmse_slope(problem, est_fn, Ms=(3, 5, 7)):
    xs, ys = [], []
    for M in Ms:
        ks = mlae.exponential_schedule(M)
        est = np.array(est_fn(M, ks))
        xs.append(100 * sum(2 * k + 1 for k in ks))
        ys.append(float(np.sqrt(np.mean((est - problem.reference) ** 2))))
    return xs, ys, float(np.polyfit(np.log(xs), np.log(ys), 1)[0])


def _analytic_estimates(problem, M, ks, R, seed):
    runner = AnalyticRunner(problem.p, np.random.default_rng(seed))
    return [mlae.estimate(runner.run(ks, 100)).a_hat for _ in range(R)]


def test_mlae_scaling_smoke(problem):
    xs, ys, slope = _rmse_slope(problem, lambda M, ks: _analytic_estimates(problem, M, ks, 50, 2026 + M))
    msg = f"N_A {xs} RMSE {[f'{y:.3e}' for y in ys]} slope {slope:.3f}"
    assert xs == [900, 3500, 13300], msg
    assert -1.15 <= slope <= -0.75, msg
    T = problem.reference
    for na, y in zip(xs[1:], ys[1:]):
        assert y < math.sqrt(T * (1 - T) / na), msg
    assert np.allclose(ys, [8.08e-3, 2.19e-3, 6.43e-4], rtol=5e-3), msg
    assert abs(slope - (-0.940)) < 5e-3, msg


def _aer_estimates(problem, M, ks, R):
    from qiskit_aer import AerSimulator

    runner = BackendRunner(AerSimulator(method="statevector"), problem)
    out = []
    for r in range(R):
        runner.run_options = {"seed_simulator": 1000 * M + r}
        out.append(mlae.estimate(runner.run(ks, 100)).a_hat)
    return out


@pytest.mark.slow
@SLOW
def test_mlae_scaling_on_aer_slow(problem):
    pytest.importorskip("qiskit_aer")
    xs, ys, slope = _rmse_slope(problem, lambda M, ks: _aer_estimates(problem, M, ks, 20))
    msg = f"Aer N_A {xs} RMSE {[f'{y:.3e}' for y in ys]} slope {slope:.3f}"
    print(msg)
    assert -1.2 <= slope <= -0.7, msg


@pytest.mark.slow
@SLOW
def test_aer_rmse_matches_analytic_slow(problem):
    pytest.importorskip("qiskit_aer")
    rows = []
    for M in (3, 5):
        ks = mlae.exponential_schedule(M)
        aer = np.array(_aer_estimates(problem, M, ks, 30)) - problem.reference
        ana = np.array(_analytic_estimates(problem, M, ks, 400, 7000 + M)) - problem.reference
        r_aer, r_an = float(np.sqrt(np.mean(aer ** 2))), float(np.sqrt(np.mean(ana ** 2)))
        rows.append((M, r_aer, r_an))
    msg = f"(M, Aer RMSE R=30, analytic RMSE R=400): {rows}"
    print(msg)
    for _, r_aer, r_an in rows:
        assert abs(r_aer - r_an) <= 0.3 * r_an, msg


# --- BackendRunner -----------------------------------------------------------------------------

def test_backend_runner_refuses_ionq_and_groups_shots(problem):
    with pytest.raises(ValueError, match="IonQRunner"):
        BackendRunner(FakeIonQSimulator(), problem)
    with pytest.raises(ValueError):
        BackendRunner(BasicSimulator(), problem, measure="none")
    with pytest.raises(ValueError):
        BackendRunner(BasicSimulator(), problem, run_options={"shots": 5})
    b = BasicSimulator()
    b.set_options(seed_simulator=9)
    spy = _RunSpy(b)
    runner = BackendRunner(spy, problem)
    recs = runner.run([0, 1, 2], [100, 200, 100])
    assert len(spy.calls) == 2
    assert [len(c) for c, _ in spy.calls] == [2, 1]
    assert [r.k for r in recs] == [0, 1, 2]
    assert [r.shots for r in recs] == [100, 200, 100]
    assert [sum(c.values()) for c in runner.last_counts] == [100, 200, 100]
    for bad_ks, bad_shots in (([], 10), ([0, True], 10), ([-1], 10), ([0], 0), ([0, 1], [10]), ([0], 1.5)):
        with pytest.raises(ValueError):
            runner.run(bad_ks, bad_shots)


def test_backend_runner_measure_all_reads_flag_from_key_index_0(problem):
    b = BasicSimulator()
    b.set_options(seed_simulator=2026)
    runner = BackendRunner(b, problem, measure="all")
    recs = runner.run([0, 1], 500)
    assert all(len(key) == problem.qubits for c in runner.last_counts for key in c)
    for r, c in zip(recs, runner.last_counts):
        assert r.hits == sum(v for key, v in c.items() if key[0] == "1")


# --- IonQRunner --------------------------------------------------------------------------------

def test_ionq_runner_sends_one_bare_circuit(problem):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=3)
    rec = IonQRunner(fake, problem).run_point(1, 200)
    assert len(fake.calls) == 1
    sent = fake.calls[0]
    assert isinstance(sent, QuantumCircuit) and not isinstance(sent, (list, tuple))
    assert sent.num_qubits == 12 and sent.num_clbits == 12
    check_ionq_safe(sent)
    assert rec["accepted"] is True and rec["error"] is None
    assert rec["sampled"] is True and rec["noise_model"] == "ideal"
    assert rec["hits"] >= 190
    assert rec["cx"] == 1503
    assert rec["n_A"] == 600
    assert rec["body_bytes_est"] == 56 * rec["size"]
    assert rec["max_controls"] <= 7
    assert all(len(key) == 12 for key in rec["counts"])
    assert tuple(rec) == runners.RECORD_KEYS
    assert json.loads(json.dumps(rec)) == rec
    assert validate_ionq_record(rec) is rec


def test_ionq_runner_labels_noisy_runs_unsampled(problem):
    fake = FakeIonQSimulator()
    fake.set_options(seed_simulator=4)
    runner = IonQRunner(fake, problem, ideal_mode="none")
    out = runner.run([0], 100)
    assert runner.last_record["noise_model"] == "forte-1"
    assert runner.last_record["sampled"] is False
    assert out[0].sampled is False and out[0].source == "ionq:forte-1"
    with pytest.raises(ValueError, match="rounded counts"):
        mlae.estimate(out)


def test_ionq_runner_rejects_bad_inputs_before_any_job(problem):
    fake = FakeIonQSimulator()
    runner = IonQRunner(fake, problem)
    for k, shots in ((-1, 100), (9, 100), (0, 1), (0, 10_001), (True, 100), (0, 100.0)):
        with pytest.raises(ValueError):
            runner.run_point(k, shots)
    with pytest.raises(ValueError, match="exactly one"):
        runner.run([0, 1], 100)
    with pytest.raises(ValueError, match="round"):
        IonQRunner(fake, problem, ideal_mode="kwarg")
    with pytest.raises(ValueError):
        IonQRunner(fake, problem, ideal_mode="ideal")
    with pytest.raises(ValueError):
        IonQRunner(BasicSimulator(), problem)
    assert fake.calls == []
    assert fake.options.noise_model == "forte-1"       # set_options never reached either


def test_ionq_runner_reports_submission_failure(problem):
    fake = FakeIonQSimulator(fail=RuntimeError("Circuit size is too large, please try running a smaller "
                                               "circuit (less gates)"))
    runner = IonQRunner(fake, problem)
    rec = runner.run_point(1, 100)
    assert len(fake.calls) == 1
    assert rec["accepted"] is False and rec["hits"] is None and rec["p_flag"] is None
    assert "Circuit size is too large" in rec["error"]
    with pytest.raises(ValueError, match="accepted"):
        validate_ionq_record(rec)
    with pytest.raises(RuntimeError, match="Circuit size is too large"):
        runner.run([1], 100)
    assert len(fake.calls) == 2                         # one per run, never a retry


def test_ionq_runner_records_set_options_failure_without_running(problem):
    class NoOptions(FakeIonQSimulator):
        def set_options(self, **fields):
            raise AttributeError("no noise_model here")

    NoOptions.__module__ = "qiskit_ionq.ionq_backend"
    fake = NoOptions()
    rec = IonQRunner(fake, problem).run_point(0, 100)
    assert fake.calls == []
    assert rec["accepted"] is False and "set_options" in rec["error"]


# --- count parsing -----------------------------------------------------------------------------

def test_hits_from_counts_edges():
    assert hits_from_counts({"1 0": 3, "0 1": 2}, flag_pos=1, n_clbits=2) == 3
    assert hits_from_counts({"1 0": 3, "0 1": 2}, flag_pos=0, n_clbits=2, shots=5) == 2
    assert hits_from_counts({"1": 100}, 0, 1, shots=100) == 100            # Aer omits zero keys
    assert hits_from_counts({"0": 7}, 0, 1) == 0
    assert hits_from_counts({}, 0, 1) == 0
    assert hits_from_counts({"100": 4, "011": 6}, flag_pos=2, n_clbits=3, shots=10) == 4
    assert hits_from_counts({"1": np.int64(3), "0": 2.0}, 0, 1, shots=5) == 3
    for counts, kw in (({"10": 1}, {}),                    # wrong width
                       ({"2": 1}, {}),                     # not binary
                       ({"x": 1}, {}),
                       ({"1": -1}, {}),                    # negative
                       ({"1": 1.5}, {}),                   # non-integer
                       ({"1": True}, {}),
                       ({"1": "3"}, {}),
                       ({1: 3}, {}),                       # non-string key
                       ({"1": 3, "0": 2}, {"shots": 6}),   # total != shots
                       ([("1", 3)], {})):                  # not a mapping
        with pytest.raises(ValueError):
            hits_from_counts(counts, 0, 1, **kw)
    for flag_pos, n in ((1, 1), (-1, 1), (0, 0)):
        with pytest.raises(ValueError):
            hits_from_counts({"1": 1}, flag_pos, n)


# --- IonQ records ------------------------------------------------------------------------------

def _mutate_counts_sum(rec):
    key = next(iter(rec["counts"]))
    rec["counts"][key] += 1


def _mutate_bad_key(rec):
    key = next(iter(rec["counts"]))
    rec["counts"]["01x" + "0" * 9] = rec["counts"].pop(key)


def _mutate_q1lite(rec):
    rec.update(model="Q1lite", qubits=8, flag=7, layout=runners.MODEL_LAYOUT["Q1lite"])


TAMPERING = {
    "schema": lambda r: r.update(schema="neutron_qae.other"),
    "schema_version": lambda r: r.update(schema_version=2),
    "model_Q2": lambda r: r.update(model="Q2"),
    "q1lite_with_12_bit_keys": _mutate_q1lite,
    "qubits": lambda r: r.update(qubits=11),
    "k_9": lambda r: r.update(k=9),
    "k_bool": lambda r: r.update(k=True),
    "shots_1": lambda r: r.update(shots=1),
    "hits_off_by_one": lambda r: r.update(hits=r["hits"] + 1),
    "counts_sum": _mutate_counts_sum,
    "bad_key": _mutate_bad_key,
    "n_A": lambda r: r.update(n_A=r["n_A"] + 1),
    "sampled_but_noisy": lambda r: r.update(noise_model="forte-1"),
    "unsampled_but_ideal": lambda r: r.update(sampled=False),
    "accepted_false": lambda r: r.update(accepted=False),
    "p_flag": lambda r: r.update(p_flag=0.5),
    "ideal_mode_kwarg": lambda r: r.update(ideal_mode="kwarg"),
    "missing_field": lambda r: r.pop("timestamp"),
    "not_a_dict": None,
}


@pytest.mark.parametrize("name", sorted(TAMPERING))
def test_record_validation_rejects_tampering(ionq_records, name):
    rec = copy.deepcopy(ionq_records[1])
    validate_ionq_record(rec)
    if TAMPERING[name] is None:
        rec = [rec]
    else:
        TAMPERING[name](rec)
    with pytest.raises(ValueError):
        validate_ionq_record(rec)


def test_noisy_record_is_valid_but_unsampled(ionq_records):
    rec = ionq_records["noisy0"]
    assert validate_ionq_record(rec) is rec
    assert rec["sampled"] is False and rec["noise_model"] == "forte-1" and rec["ideal_mode"] == "none"


def test_load_ionq_records_file_rules(tmp_path, monkeypatch, ionq_records):
    assert load_ionq_records(tmp_path / "missing.json") == []
    good = tmp_path / "runs.json"
    good.write_text(json.dumps([ionq_records[0], ionq_records[1]]), encoding="utf-8")
    assert load_ionq_records(good) == [ionq_records[0], ionq_records[1]]
    dup = tmp_path / "dup.json"
    dup.write_text(json.dumps([ionq_records[0], ionq_records[0]]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_ionq_records(dup)
    obj = tmp_path / "obj.json"
    obj.write_text(json.dumps({"records": [ionq_records[0]]}), encoding="utf-8")
    with pytest.raises(ValueError, match="list"):
        load_ionq_records(obj)
    bad = tmp_path / "bad.json"
    broken = dict(ionq_records[1], hits=0)
    bad.write_text(json.dumps([ionq_records[0], broken]), encoding="utf-8")
    with pytest.raises(ValueError, match="record 1"):
        load_ionq_records(bad)
    big = tmp_path / "big.json"
    big.write_bytes(b" " * 2_000_001)
    with pytest.raises(ValueError, match="2000000"):
        load_ionq_records(big)
    notjson = tmp_path / "notjson.json"
    notjson.write_text("IONQ_RECORD={...}", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON"):
        load_ionq_records(notjson)
    assert runners.IONQ_RUNS_FILE == "data/ionq_runs.json"
    monkeypatch.setattr(runners, "IONQ_RUNS_FILE", str(good))
    assert load_ionq_records() == [ionq_records[0], ionq_records[1]]
    monkeypatch.setattr(runners, "IONQ_RUNS_FILE", str(tmp_path / "absent.json"))
    assert load_ionq_records() == []
    assert ionq_estimate() is None


def test_ionq_estimate_needs_k0_and_skips_noisy(problem, ionq_records):
    records = [ionq_records[0], ionq_records[1], ionq_records[2], ionq_records["noisy0"]]
    prs = ionq_power_results(records)
    assert [p.k for p in prs] == [0, 1, 2] and all(p.sampled for p in prs)
    est = ionq_estimate(records)
    assert est.n_A == 9000 and est.ks == (0, 1, 2)
    assert abs(est.a_hat - problem.reference) <= 4 * est.se, (est.a_hat, est.se)
    assert ionq_estimate([ionq_records[1]]) is None                  # one k >= 1 power is ambiguous
    assert ionq_estimate([ionq_records["noisy0"], ionq_records[1]]) is None
    assert ionq_power_results(records, models=("Q0",)) == []
