"""Test double for Qollab's injected IonQ backend (never imported by the package).

``FakeIonQSimulator`` is a BasicSimulator whose class claims the ``qiskit_ionq.ionq_backend``
module (so ``smoke.is_ionq`` is true), whose options carry ``noise_model`` (default "forte-1",
like Qollab's Forte 1 entry; ``set_options(noise_model="ideal")`` works and reads back), and whose
``run`` refuses a list or tuple exactly like Qollab's IonQ proxy (HTTP 400 "Only job type
ionq.circuit.v1 is supported"). It records every run input in ``calls`` and can be told to raise
``fail`` on submission.

It is ALWAYS an ideal sampling simulator, even when its option reads forte-1: only the labelling
logic (noise_model -> sampled) and the one-bare-circuit protocol are under test, not IonQ's noise.
"""
from __future__ import annotations

from qiskit.providers.basic_provider import BasicSimulator


class FakeIonQSimulator(BasicSimulator):
    """BasicSimulator posing as qiskit-ionq's backend (module name, noise_model option, no lists)."""

    def __init__(self, *args, fail: BaseException | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls: list = []
        self.fail = fail

    @classmethod
    def _default_options(cls):
        options = super()._default_options()
        options.update_options(noise_model="forte-1")
        return options

    def run(self, run_input, **options):
        self.calls.append(run_input)
        if isinstance(run_input, (list, tuple)):
            raise RuntimeError("Only job type ionq.circuit.v1 is supported")   # Qollab's HTTP 400
        if self.fail is not None:
            raise self.fail
        return super().run(run_input, **options)


FakeIonQSimulator.__module__ = "qiskit_ionq.ionq_backend"
