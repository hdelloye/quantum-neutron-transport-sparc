"""Runners (neutron_qae/runners.py): QAE-02 interface, QAE-04 agreement, IonQ one-circuit path."""
from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator

from neutron_qae import mlae
from neutron_qae.oracle import make_problem
from neutron_qae.runners import BackendRunner


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


def test_builtin_list_job_to_mlae_estimate():
    b = BasicSimulator()
    b.set_options(seed_simulator=2026)
    spy = _RunSpy(b)
    problem = make_problem("Q1")
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
