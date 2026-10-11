# Phase 4: Quantum Oracle & Amplitude Estimation - Research

**Researched:** 2026-10-10 (evening, ET)
**Domain:** Qiskit 2.5.2 state preparation, Grover powers, maximum-likelihood amplitude estimation, Qollab/IonQ submission
**Confidence:** HIGH. Every circuit number below was measured in a scratch venv with the real frozen `Kernels` v1 tables: qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-algorithms 0.4.0, and qiskit-ionq 1.0.2 (Qollab's version) plus 1.1.1. The IonQ request-body limit is the one item still unverified.

<user_constraints>
## User Constraints (no CONTEXT.md; ROADMAP, PROJECT.md Key Decisions and the Phase 2 contract stand in for it)

### Locked decisions
- ROADMAP Phase 4 goal: "A state-preparation circuit within 24 qubits, whose flag probability equals the exact lattice value, is wrapped in Grover powers and a vendored maximum-likelihood amplitude estimator, producing transmission estimates through analytic, Aer and IonQ runners with cost counted honestly as applications of A."
- SC1: "On an Aer statevector, Q0's flag probability equals e^{-τ}, and Q1's flag probability (fresh qubits for every random choice, no measurement or reset inside A, invertible) equals the exact lattice solver value to 1e-12; this contract test gates every QAE run."
- SC2: "Powers Q^k of the Grover operator built with `grover_operator()` reproduce sin²((2k+1)θ) on a statevector for k up to 64."
- SC3: "The vendored numpy MLAE, given counts from one `backend.run([...])` job of A·Q^k circuits, returns the same estimate as qiskit-algorithms MLAE on identical counts, and every estimate reports its cost as N_A = Σ shots·(2k+1), never raw shots or `num_oracle_queries`."
- SC4: "The analytic, Aer and IonQ runners share one interface; analytic and Aer agree within statistical error on at least three (k, shots) points, and an IonQ-runner job (decomposed to at most 7 controls per gate, transpiled once as a whole circuit, `backend.run` + `get_counts`, no Sampler) completes on Qollab's IonQ simulator and yields counts the MLAE accepts."
- SC5: "A resource table lists qubits, CX count and depth for Q0 and Q1 after a single full-circuit transpile, all within the 24-qubit budget."
- PROJECT.md Key Decisions:
  - "One quantum step = one collision, fresh qubits per random choice".
  - "MLAE (vendored) as the estimator, cost counted as N_A = Σ shots·(2k+1)".
  - "2026-10-10 note (01-03): MLAE on Qollab IonQ cannot be one multi-circuit job ... an IonQ Run carries exactly one circuit; the MLAE row above holds for local/Built-in runs only. Ideal IonQ runs via `set_options(noise_model="ideal")` (sampled)".
- STATE.md decisions:
  - "Qollab IonQ accepts only ionq.circuit.v1 and one job per Run, so an IonQ Run carries exactly one circuit".
  - "Ideal IonQ runs use backend.set_options(noise_model='ideal') (ideal, sampled); the run kwarg gives exact round(p*shots) with no shot noise and is never used for statistics".
  - "Logged-out IonQ run (R8) refused by Qollab".
- Phase 2 contract: PD-04 "Kernels contract v1 supports K in {0, 1}"; PD-06 "Kernels contract v1 frozen in tests/golden/kernels_v1.json (T1=0.24300446519524305) ... main.py unchanged".
- Timeline: IonQ cloud runs finish before ~hour 36 (Oct 11 ~7:00 AM ET); final deadline Oct 11 7:00 PM ET.

### Claude's discretion (researched below)
- Q0/Q1 construction details, module names, runner interface, MLAE schedule and refinement, the IonQ protocol under the one-circuit rule, and test layout.

### Deferred (out of scope)
- QC-07 Q1-Y (16 qubits), QC-08 K=2, QAE-05 noisy IonQ MLAE at k ≤ 8, ANLY-06, UI-01. The ANLY-* figures belong to Phase 5. This phase only produces their inputs.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QC-01 | Q0 with `StatePreparation` and a flag; flag P = e^{-τ} | Q0 = 5 qubits: the 17-outcome first-collision `StatePreparation`, with flag = x[4]. Measured flag P − T0 = 3.2e-15 (Statevector) and −1.4e-16 (Aer). Pattern 1 |
| QC-02 | Q1 with fresh qubits, no measure/reset, invertible | Q1 = 12 qubits, x(5) a(1) φ(4) e(1) T(1). Decomposes only to `cx`, `u`. `Operator(A)·Operator(A⁻¹) = I` checked. Pattern 1 |
| QC-03 | Q1 flag P on Aer statevector = T1 to 1e-12 | Measured differences: 3.5e-15 (Statevector) and 4.4e-16 (Aer). Per-bit-string max difference vs `bitstring_probabilities_k1` is 6.0e-15, with 0 flag mismatches. Pattern 2 |
| QC-04 | `grover_operator()` powers give sin²((2k+1)θ), k ≤ 64 | Max error 7.6e-13 over k ∈ {0,1,2,3,4,8,16,32,64} when transpiled once. k=64 costs 76,473 CX, 0.65 s transpile + 5.5 s Statevector, or 1.7 s on Aer. Pattern 3 |
| QC-05 | Resource table after one full transpile | Resource Table (measured) |
| QC-06 | ≤7 controls per gate, transpiled once | Transpiling to `["cx","rz","ry","rx","h","x","sx"]` gives max 1 control. `transpile(c, ionq_backend)` leaves an **11-control mcx** (measured), so never pass the IonQ backend. Pattern 5 |
| QAE-01 | Vendored numpy MLAE = qiskit-algorithms MLAE on the same counts | Same likelihood with qiskit's default minimizer gives Δθ = 0 exactly. The vendored precise maximizer differs from qiskit's default by ≤ 3.6e-5 in a, always at higher likelihood. Pattern 4 and Pitfall 4 |
| QAE-02 | Three runners, one interface; `backend.run` + `get_counts` | `AnalyticRunner`, `BackendRunner` (with Aer/BasicSimulator injected), and `IonQRunner` (one bare circuit). Pattern 5 |
| QAE-03 | N_A = Σ shots·(2k+1) | qiskit-algorithms reports `num_oracle_queries = shots * sum(k)` (mlae.py:337). Compute N_A from the records. Pattern 4 |
| QAE-04 | Analytic ≈ Aer at ≥3 (k, shots) points | Aer MLAE RMSE equals analytic RMSE at N_A = 900 / 3,500 / 13,300 (7.9e-3 vs 7.8e-3, 2.37e-3 vs 2.23e-3, 5.6e-4 vs 5.6e-4). Validation design in Pattern 6 |
</phase_requirements>

## Project Constraints (from .claude/CLAUDE.md and the Phase 1/2 gates)

- Python 3.14, `qiskit==2.5.2` pinned. Qollab runs Pyodide 314.0.7 with numpy 2.4.6 and scipy 1.18.0. Avoid numpy 2.5-only APIs. [VERIFIED: docs/QOLLAB-RUNTIME.md "Runtime versions"]
- Flat package `neutron_qae/` next to `main.py`. `pyproject.toml:19` reads `packages = ["neutron_qae"]`, so add flat modules only (no subpackage). [VERIFIED: pyproject.toml:19]
- `tests/compliance_checks.py:11`: `FORBIDDEN_REACHABLE = {"qiskit_aer", "qiskit_algorithms", "qiskit_ionq", "qiskit_ibm_runtime"}`. The walker scans **every node** of every module reachable from `main.py`, including function-body imports and try/except. [VERIFIED: tests/compliance_checks.py:1-3,11]
- `tests/compliance_checks.py:14-17`: `BACKEND_CONSTRUCTORS = {"AerSimulator", "BasicSimulator", "IonQProvider", "QiskitRuntimeService", "BraketLocalBackend", "BraketProvider", "GenericBackendV2", "StatevectorSimulator"}`, `BACKEND_FACTORY_ATTRS = {"get_backend", "backends"}`, `ALLOWLIST_DIRS = ("tests", "scripts")`. **No `AerSimulator(...)` call may appear anywhere in `neutron_qae/`**, even in a module `main.py` never imports. [VERIFIED: tests/compliance_checks.py:14-17]
- Every file under `data/` must be referenced by a literal `"data/..."` string from main-reachable code (tests/test_compliance.py `test_every_data_file_is_referenced_by_literal_path`). [VERIFIED: tests/test_compliance.py, read this session]
- `backend` must be a function parameter inside the package, never a free global (`package_uses_global_backend`). [VERIFIED: tests/compliance_checks.py, read this session]
- `def main(` sits on one line with int/float/str/bool annotations and literal defaults, with no `__name__` guard and no module-level `main()` call. [VERIFIED: tests/compliance_checks.py `main_signature_problems`]
- Dev extras are already declared: `dev = ["pytest>=9", "ruff==0.16.10", "qiskit-aer==0.17.2", "qiskit-algorithms==0.4.0"]`. pytest markers: `markers = ["slow: long-running"]`. [VERIFIED: pyproject.toml:16,25]
- `is_ionq(backend)` exists: `return type(backend).__module__.startswith("qiskit_ionq")`. Reuse it. [VERIFIED: neutron_qae/smoke.py:69]
- Do not import qiskit into `kernels.py`, `problem.py` or `exact.py` (Phase 2 rule; Phase 3 stays qiskit-free).
- Scaling honesty: claim only sampling complexity (1/N_A vs 1/√N), never a wall-clock speedup.
- GSD workflow: edits go through `/gsd-execute-phase`. **Phase 3 is executing in parallel in the same repo** (commits `b281f8a`..`bfc51e5` added `random_source.py`, `mc_continuous.py`, `mc_lattice.py`). Phase 4 must not touch those files.

## Summary

The Q1 oracle from the original research works unchanged on the real frozen tables:

- **Size and accuracy.** 12 qubits with layout x(5) a(1) φ(4) e(1) T(1), which matches `exact.py`'s little-endian bit strings exactly. The flag probability equals T1 = 0.24300446519524305 to 3.5e-15.
- **Cost.** After one transpile to `[cx, rz, ry, rx, h, x, sx]`: 313 CX in A, 1,188 CX per Grover step, 1,503 CX for A·Q¹.
- **Q0** is the same 17-outcome `StatePreparation` alone (5 qubits, 26 CX, flag = x[4]). Its flag probability equals e^{-τ} = T0 to 3e-15.
- **Grover powers.** `grover_operator(oracle=Z on flag, state_preparation=A)` reproduces sin²((2k+1)θ) to 7.6e-13 for k ≤ 64, provided the logical circuit A·Q^k is **composed first and transpiled once**.
- **Stitching fails.** Transpiling A and Q separately and then stitching them gives 0.958 instead of 0.9994 at k=1. Measured, so this is a real trap.
- **Keep the direction register.** Dropping φ (a "Q1-lite", 8 qubits, 73 CX in A) keeps T1 exact. But Phase 3's `sample_exit_rows` and ANLY-02 consume full 11-bit strings including φ. Keep φ in the headline Q1 and hold Q1-lite only as an IonQ size fallback.

The MLAE is a ~60-line numpy module:

- **Algorithm.** A grid log-likelihood over θ ∈ [ε, π/2−ε] with qiskit's grid size `max(10000, int(π/2·1000·2·k_max))`, then golden-section refinement between neighbouring grid points.
- **Match against qiskit-algorithms.** Fed to qiskit's default minimizer (`scipy.optimize.brute` + `fmin`), our likelihood gives a **bit-identical θ** to `MaximumLikelihoodAmplitudeEstimation.compute_mle` on identical counts.
- **Better than the default.** Our refined maximizer always has a higher likelihood than qiskit's default, which stops up to 3.6e-5 in *a* short of the MLE (fmin xtol = 1e-4). This matters for the RMSE floor at large N_A.
- **Scaling.** The exponential schedule k = 0, 1, 2, 4, …, 2^(M−1) with 100 shots per power gives a fitted RMSE slope of **−0.90** over N_A = 100 … 51,900 (13× below classical at N_A ≈ 5×10⁴). The linear schedule gives −0.74.
- **Aer agrees.** Aer shot-based MLAE matches the analytic emulator's RMSE at three N_A points.

The IonQ path must live with one circuit per Qollab Run. Recommendation:

- **Runner.** An `IonQRunner` sends one bare, explicitly decomposed A·Q^k circuit per Run, with k and shots taken from `main()` form fields. Ideal mode uses `backend.set_options(noise_model="ideal")`, all 12 qubits are measured, and each Run prints a machine-readable `IONQ_RECORD=` line.
- **Protocol.** Hippolyte runs k = 0, 1, 2 signed in (3 Runs ≈ 45 s). The three records give an IonQ-only MLAE estimate with an honest N_A.
- **Why at least two Runs.** A single k ≥ 1 point is ambiguous: sin²(3θ) has 3 maxima in [0, π/2]. So "counts the MLAE accepts" means each Run's counts parse into an MLAE record, and the k = 0, 1, 2 aggregate yields the IonQ estimate.
- **Size risk.** Request bodies are 31 KB (k=0), 168 KB (k=1) and 305 KB (k=2). Qollab's proxy rejects "request body too large" at an unknown limit. Submit k=0 first.

**Primary recommendation:** Build `oracle.py` → `grover.py` → `mlae.py` → `runners.py` in that order, gated by a runtime contract check (Statevector flag probability vs `exact.transmission_within(K, 1)` to 1e-12). Transpile every A·Q^k once to an explicit basis, never to a backend target. Inject Aer only from `tests/` and `scripts/`. Ship an interim `main.py` QAE mode tonight so the IonQ Runs happen before 7 AM ET.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Probability tables, exact T1 | `kernels.py` / `exact.py` (frozen, numpy) | — | Phase 2 contract; Phase 4 only reads them |
| State preparation A (Q0, Q1) | `neutron_qae/oracle.py` (qiskit only) | — | Pure circuit construction from `Kernels`; Pyodide-safe |
| Grover powers, transpile-once, resources | `neutron_qae/grover.py` (qiskit only) | — | One place enforces the transpile-once and ≤7-control rules |
| MLE, N_A accounting, schedules | `neutron_qae/mlae.py` (numpy only) | — | Must run in Pyodide and in Phase 5 sweeps; no qiskit needed |
| Execution (analytic / any backend / IonQ) | `neutron_qae/runners.py` | `tests/`, `scripts/` inject Aer/BasicSimulator | Backends are injected; the package never constructs one (compliance gate) |
| Qollab entry, form fields, IonQ record printing | `main.py` (interim QAE mode) | `neutron_qae/runners.py` | Only `main.py` sees the global `backend` |
| Local sweeps, resource table, Aer cross-checks | `scripts/qae_local.py` (new) | `tests/` | Allowed to import qiskit_aer / qiskit_algorithms |
| IonQ run records | `data/ionq_runs.json` (hand-pasted) | literal path in `runners.py` | Data gate requires a literal path from main-reachable code |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qiskit | 2.5.2 (pinned) | `StatePreparation`, `UCRYGate`, `grover_operator`, `transpile`, `Statevector`, `BasicSimulator` (tests) | Qollab's only qiskit build. [VERIFIED: scratch venv `pip list`; docs/QOLLAB-RUNTIME.md] |
| numpy | 2.x (Pyodide 2.4.6) | MLAE likelihood, analytic runner (`np.random.Generator.binomial`) | Already used everywhere |

### Supporting (local/dev only, never main-reachable)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit-aer | 0.17.2 | `AerSimulator(method="statevector")` for QC-03, QC-04 and QAE-04 | Tests and scripts, with `pytest.importorskip("qiskit_aer")` |
| qiskit-algorithms | 0.4.0 | `MaximumLikelihoodAmplitudeEstimation.compute_mle` equality test (QAE-01) | Tests only, with `importorskip` |
| qiskit-ionq | 1.0.2 (Qollab) / 1.1.1 (latest) | Optional local test that `qiskit_to_ionq` serializes our circuits and to measure payload bytes | Tests only, `importorskip`; never main-reachable |
| scipy | 1.18 | Not needed by the vendored MLAE (golden section is numpy) | Only via qiskit-algorithms in tests |

**Installation (already approved in the Phase 1 dependency checkpoint):**
```bash
cd "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon" && .venv/bin/pip install -e ".[dev]"
```
`.venv` currently has qiskit 2.5.2, numpy 2.5.3, scipy 1.18.1 and pytest 9.1.1, with **no** qiskit-aer or qiskit-algorithms. [VERIFIED: `.venv/bin/pip list` this session] qiskit-ionq is optional and not in the dev extras. Only add it if the planner wants the serialization test (`pip install qiskit-ionq==1.0.2` matches Qollab).

**Aer on Python 3.14.8:** Aer installed and ran in the scratch venv. One segfault was traced to an untranspiled `multiplexer` instruction (Pitfall 2), not to the Python version. [VERIFIED: scratch run]

## Package Legitimacy Audit

No new packages are introduced. qiskit-aer 0.17.2 and qiskit-algorithms 0.4.0 are already pinned in `pyproject.toml:16` and were human-approved in the Phase 1 dependency checkpoint. qiskit-ionq 1.0.2 is optional (test-only) and is the version Qollab itself installs (docs/QOLLAB-RUNTIME.md "Qollab /py index: ... qiskit-ionq 1.0.2").

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| qiskit-aer | PyPI | multi-year | high | github.com/Qiskit/qiskit-aer | previously approved | Approved (Phase 1) |
| qiskit-algorithms | PyPI | multi-year | high | github.com/qiskit-community/qiskit-algorithms | previously approved | Approved (Phase 1) |
| qiskit-ionq (optional, tests) | PyPI | multi-year | moderate | github.com/qiskit-community/qiskit-ionq | not re-run this session | Optional. If added, gate the install behind a human-verify checkpoint |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
(The gsd-tools legitimacy seam was not re-run because no new package enters the project's required set.)

## Architecture Patterns

### System Architecture Diagram

```
ProblemSpec ─► build_kernels ─► Kernels v1 (frozen) ─┬─► exact.transmission_within(K,1) = T1 ───────────┐
                                                      │                                                  │
                                                      └─► oracle.build_q1(K) ─► A (12q, unitary)         │
                                                                 │                                       │
                                     oracle.check_contract(A, flag, T1, 1e-12)  ◄────────────────────────┘
                                     (Statevector, ~20 ms; raises → no QAE run)
                                                                 │
                         grover.power_circuit(A, flag, k, measure) = A·Q^k  (logical, composed)
                                                                 │
                         grover.transpile_once(c, BASIS)  (≤1 control per gate; resources logged)
                                                                 │
            ┌──────────────────────────────┬──────────────────────┴─────────────────────────┐
            ▼                              ▼                                                ▼
  AnalyticRunner(p=sv flag prob)   BackendRunner(backend injected:              IonQRunner(backend injected, is_ionq):
  Binomial(shots, sin²((2k+1)θ))   Aer from tests/scripts,                      ONE bare circuit per Run,
  (no circuits)                    BasicSimulator on Qollab Built-in)           set_options(noise_model="ideal"),
            │                      one backend.run([list]) job, get_counts(i)   measure_all, get_counts + probabilities
            │                              │                                                │
            └──────────── list[PowerResult(k, shots, hits, source)] ◄───────────────────────┘
                                           │                     (IonQ: IONQ_RECORD= line → data/ionq_runs.json)
                                           ▼
                         mlae.estimate(records) → MLAEResult(a_hat, theta, n_A = Σ shots(2k+1), schedule)
                                           │
                                           ▼
                       Phase 5 sweeps (RMSE vs N_A), Phase 6 main.py quick mode
```

### Recommended Project Structure
```
neutron_qae/
├── oracle.py      # x_amplitudes, build_q0, build_q1(direction=True), flag_probability, check_contract, Q*_FLAG
├── grover.py      # grover(A, flag), power_circuit, transpile_once, BASIS, max_controls, resources
├── mlae.py        # PowerResult, loglikelihood, mle_theta, estimate, n_applications, exponential/linear schedules
└── runners.py     # Runner protocol, AnalyticRunner, BackendRunner, IonQRunner, hits_from_counts, IONQ_RUNS_FILE
main.py            # interim QAE mode (Built-in: live MLAE; IonQ: one circuit, prints IONQ_RECORD=)
scripts/qae_local.py     # resource table (QC-05), Aer cross-checks, ad-hoc sweeps (may import qiskit_aer)
tests/test_oracle.py     # QC-01/02/03 (Statevector always; Aer variant importorskip)
tests/test_grover.py     # QC-04 (fast k≤16; slow k=32,64), QC-06 (max controls, basis), stitching negative test
tests/test_mlae.py       # QAE-01 (importorskip qiskit_algorithms), QAE-03, edge cases
tests/test_runners.py    # QAE-02/04, fake IonQ one-circuit test, BasicSimulator list job
data/ionq_runs.json      # filled after the IonQ Runs; referenced by literal path in runners.py
```

### Pattern 1: Q0 and Q1 state preparation (exact `exact.py` layout)
**What:** Each random choice gets a fresh register. Qubit i = bit i of `exact.py`'s string `x | a<<5 | phi<<6 | e<<10`, and the flag T sits on qubit 11.

```python
# Source: measured in scratch (scripts/build.py); constants from neutron_qae/exact.py:15
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation, UCRYGate
from neutron_qae.kernels import BACK

def x_amplitudes(k):                       # 17 outcomes in 5 qubits; x = 17..31 amplitude 0
    a = np.zeros(32); a[:17] = np.sqrt(k.first_collision); return a

def build_q0(k):                           # 5 qubits, flag = x[4] (x == 16 ⇔ uncollided)
    qc = QuantumCircuit(5, name="A_Q0")
    qc.append(StatePreparation(x_amplitudes(k)), range(5))
    return qc, 4

def build_q1(k, direction=True):           # 12 qubits (direction) or 8 (Q1-lite fallback)
    X, A_ = [0, 1, 2, 3, 4], 5
    if direction:
        qc = QuantumCircuit(12, name="A_Q1"); PH, E, T = [6, 7, 8, 9], 10, 11
    else:
        qc = QuantumCircuit(8, name="A_Q1lite"); E, T = 6, 7
    qc.append(StatePreparation(x_amplitudes(k)), X)
    qc.append(UCRYGate([float(2 * np.arcsin(np.sqrt(c))) for c in k.scatter_ratio]), [A_] + X[:4])
    if direction:
        qc.h(PH)                            # 16 uniform direction bins
        ang = [float(2 * np.arcsin(np.sqrt(k.flight[j, b, BACK]))) for b in range(16) for j in range(16)]
        qc.append(UCRYGate(ang), [E] + X[:4] + PH)    # angle index j + 16*b: first control = LSB
    else:
        ang = [float(2 * np.arcsin(np.sqrt(k.flight[j, :, BACK].mean()))) for j in range(16)]
        qc.append(UCRYGate(ang), [E] + X[:4])
    qc.cx(X[4], T); qc.x(X[4]); qc.mcx([X[4], A_, E], T); qc.x(X[4])   # T = x4 OR (¬x4 ∧ a ∧ e)
    return qc, T
```
- The UCRY controlled on x[0:4] sees 0000 for x = 16, so the uncollided branch rotates a and e like column 0. This is exactly `exact.py`'s convention (`col = x % nx`, [VERIFIED: neutron_qae/exact.py:40]: `col = x % nx                      # x = nx (uncollided) has low bits 0000: rotations of column 0`). It is harmless because T = 1 whenever x4 = 1.
- **Measured:** Q0 flag − T0 = 3.2e-15. Q1 flag − T1 = 3.5e-15 (Statevector) and 4.4e-16 (Aer). Max |P(s) − exact P(s)| over the 11 low bits is 6.0e-15. The flag predicate agrees on all 1,088 nonzero strings. Q1-lite flag − T1 = 3.5e-15. [VERIFIED: scratch proto1/proto2]
- **Invertibility (QC-02):** `A.decompose(reps=6)` contains only `cx` and `u` (no `measure`, `reset` or `initialize`), and `Operator(A)·Operator(A.inverse()) ≈ I` for Q0 and Q1. Do not put the 12-qubit `Operator` check in the fast test suite: a 4096×4096 complex compose is slow (it stalled a scratch script). Use Q0 (32×32), or assert on the op set plus `Statevector(A).evolve(A.inverse())` ≈ |0⟩. [VERIFIED: scratch]
- **What `StatePreparation` compiles to:** Isometry-based synthesis (the decomposition shows `isometry_to_uncompute`), 26 CX for 5 qubits. It is a `Gate`, so `.inverse()` works. `initialize()` would add a reset and break A†. [VERIFIED: scratch, G.decompose() op names]

### Pattern 2: Contract check that gates every QAE run
```python
from qiskit.quantum_info import Statevector
from neutron_qae.exact import transmission_within

class ContractError(RuntimeError): ...

def flag_probability(A, flag) -> float:
    return float(Statevector(A).probabilities([flag])[1])

def check_contract(A, flag, k, K=1, tol=1e-12) -> float:
    p, ref = flag_probability(A, flag), transmission_within(k, K)
    if abs(p - ref) > tol:
        raise ContractError(f"flag P {p!r} != exact T{K} {ref!r} (|d|={abs(p-ref):.2e} > {tol})")
    return p
```
- Call it inside the problem factory (for example `oracle.q1_problem(K)` returns `(A, flag, p)`) so no runner can start without it. A 12-qubit Statevector costs about 20 ms natively, which is cheap in Pyodide too.
- The pytest version (QC-03 wording "on the Aer statevector") adds an Aer variant: `pytest.importorskip("qiskit_aer")`, transpile to `BASIS`, `save_statevector()`. The Statevector variant always runs, so CI without Aer stays green.

### Pattern 3: Grover powers, composed then transpiled once
```python
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.circuit.library import grover_operator

BASIS = ["cx", "rz", "ry", "rx", "h", "x", "sx"]   # every name is in qiskit-ionq 1.0.2 ionq_basis_gates

def grover(A, flag):
    oracle = QuantumCircuit(A.num_qubits); oracle.z(flag)        # S_chi = Z on the flag
    return grover_operator(oracle, state_preparation=A)          # function form (class deprecated 2.1)

def power_circuit(A, flag, k, measure="flag"):
    G, c = grover(A, flag), A.copy()
    for _ in range(k):
        c.compose(G, inplace=True)                               # logical composition first
    if measure == "flag":
        cr = ClassicalRegister(1, "flag"); c.add_register(cr); c.measure(flag, cr[0])
    elif measure == "all":
        c.measure_all()
    c.name = f"AQ{k}"
    return c

def transpile_once(c, seed=1):
    return transpile(c, basis_gates=BASIS, optimization_level=1, seed_transpiler=seed)
```
**Measured on Q1 (P(flag) after transpile-once vs sin²((2k+1)θ), θ = asin√T1 = 0.5155):**

| k | CX | P measured | diff | transpile | Statevector |
|---|----|-----------|------|-----------|-------------|
| 0 | 313 | 0.243004465195243 | 1.7e-16 | 0.01 s | 0.02 s |
| 1 | 1,503 | 0.999407272408953 | −3.3e-14 | 0.02 s | 0.11 s |
| 2 | 2,693 | 0.285928265994703 | −1.8e-14 | 0.02 s | 0.19 s |
| 4 | 5,073 | 0.994673880172840 | −1.2e-13 | 0.05 s | 0.36 s |
| 16 | 19,353 | 0.929964730663734 | −4.6e-13 | 0.16 s | 1.39 s |
| 64 | 76,473 | 0.250187271117170 | −4.9e-13 | 0.65 s | 5.52 s |

- Aer (BASIS-transpiled) at k=64: diff −2.3e-13 in 1.7 s. A logical, untranspiled Statevector at k=64 also works: −4.8e-14 in 6.9 s. [VERIFIED: scratch proto2/proto3]
- `grover_operator` returns `global_phase = π`. This does not affect probabilities, so do not "fix" it.
- Test tolerance: 1e-11 for the k ≤ 64 sweep, since the measured max is 7.6e-13. Keep 1e-12 only for the A contract (QC-03).

### Pattern 4: Vendored MLAE (numpy only) and honest cost
```python
# Source: prototype mlae_proto.py; likelihood identical to qiskit_algorithms 0.4.0 mlae.py:252-262
import math
from dataclasses import dataclass
import numpy as np

EPS = 1e-15

@dataclass(frozen=True)
class PowerResult:
    k: int; shots: int; hits: int; source: str = ""

def n_applications(records) -> int:           # QAE-03: Suzuki eq. 11; A and A† each count 1
    return sum(r.shots * (2 * r.k + 1) for r in records)

def grid_size(ks) -> int:                     # same as qiskit-algorithms default (mlae.py:103)
    return max(10000, int(np.pi / 2 * 1000 * 2 * max(ks)))

def loglikelihood(theta, ks, hits, shots):
    th = np.asarray(theta, float)[..., None]
    ang = (2 * np.asarray(ks) + 1) * th
    h, n = np.asarray(hits, float), np.asarray(shots, float)
    s2, c2 = np.sin(ang) ** 2, np.cos(ang) ** 2
    with np.errstate(divide="ignore"):
        t1 = np.where(h > 0, h * np.log(s2), 0.0)            # 0·log0 := 0 (never NaN)
        t0 = np.where(n - h > 0, (n - h) * np.log(c2), 0.0)
    return np.sum(t1 + t0, axis=-1)

def mle_theta(ks, hits, shots) -> float:
    grid = np.linspace(EPS, np.pi / 2 - EPS, grid_size(ks))
    ll = loglikelihood(grid, ks, hits, shots); i = int(np.argmax(ll))
    a, b = grid[max(i - 1, 0)], grid[min(i + 1, grid.size - 1)]
    g = (math.sqrt(5) - 1) / 2; c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = loglikelihood(c, ks, hits, shots), loglikelihood(d, ks, hits, shots)
    for _ in range(200):                                      # golden section, bracket from the grid
        if b - a < 1e-15: break
        if fc > fd: b, d, fd = d, c, fc; c = b - g * (b - a); fc = loglikelihood(c, ks, hits, shots)
        else:       a, c, fc = c, d, fd; d = a + g * (b - a); fd = loglikelihood(d, ks, hits, shots)
    m = 0.5 * (a + b)
    return float(m if loglikelihood(m, ks, hits, shots) >= ll[i] else grid[i])
```
- `estimate(records)` returns `a_hat = sin²θ`, `theta`, `n_A = n_applications(records)`, the schedule, the records and `shots_total`. It never exposes a "queries" figure computed any other way.
- **qiskit-algorithms counts differently:** `result.num_oracle_queries = result.shots * sum(k for k in result.evaluation_schedule)`. That is Grover calls only, with k = 0 counted as zero. [VERIFIED: qiskit_algorithms/amplitude_estimators/mlae.py:337, read this session]
- **Schedules:** `exponential(M) = [0] + [2**j for j in range(M-1)]` (the headline) and `linear(M) = list(range(M))` (comparison).
- **Prototype numbers** (analytic runner, 100 shots per power, R = 200 repetitions, T1 = 0.24300):

| M | k_max | N_A | MLAE RMSE | classical √(p(1−p)/N_A) | ratio |
|---|-------|-----|-----------|-------------------------|-------|
| 1 | 0 | 100 | 3.84e-2 | 4.29e-2 | 1.1 |
| 3 | 2 | 900 | 7.83e-3 | 1.43e-2 | 1.8 |
| 5 | 8 | 3,500 | 2.23e-3 | 7.25e-3 | 3.3 |
| 7 | 32 | 13,300 | 5.63e-4 | 3.72e-3 | 6.6 |
| 8 | 64 | 26,200 | 3.08e-4 | 2.65e-3 | 8.6 |
| 9 | 128 | 51,900 | 1.40e-4 | 1.88e-3 | 13.4 |

  - Fitted slope: **−0.903** for the exponential schedule, −0.741 for the linear one. [VERIFIED: scratch scaling_proto.py] Expect a non-monotone wiggle at k_max = 4 (seen at M = 4); Phase 5 should use R ≥ 50, as ANLY-01 requires.
- **Aer shot-based MLAE** (BASIS-transpiled list job, 100 shots per power): RMSE 7.90e-3 (N_A 900, R=30), 2.37e-3 (3,500, R=30), 5.61e-4 (13,300, R=20). These match the analytic column. Time per estimate: 0.10 s, 0.43 s, 1.71 s. One sample estimate: 0.242335 at N_A = 13,300. [VERIFIED: scratch aer_mlae.py]
- **QAE-01 equality design (both directions, on identical counts):**
  1. **Likelihood identity:** `scipy.optimize.brute(lambda t: -loglikelihood(t, ...), [[EPS, π/2−EPS]], Ns=grid_size(ks))[0]` equals `MaximumLikelihoodAmplitudeEstimation(ks).compute_mle(counts, EstimationProblem(A, objective_qubits=[flag]))` **exactly** (Δθ = 0 in all 24 prototype cases).
  2. **Minimizer injection:** `MaximumLikelihoodAmplitudeEstimation(ks, minimizer=lambda f, b: mle_theta(...))` must reproduce `mlae.estimate` exactly. Alternatively assert the converse: our estimate's log-likelihood is ≥ qiskit's and |Δa| ≤ 1e-4.
  3. The counts come from **one** Aer `backend.run([A·Q^k list])` job. `compute_mle` accepted the 1-clbit counts dicts directly (default `is_good_state` = all objective bits '1'). Measured: qiskit 0.241390 vs vendored 0.241385 (exact 0.243004) for ks = [0,1,2,4,8] at 200 shots.

### Pattern 5: Runners with one interface
```python
from typing import Protocol, Sequence

class Runner(Protocol):
    name: str
    def run(self, ks: Sequence[int], shots: int | Sequence[int]) -> list["PowerResult"]: ...
```
The planner's suggested `run(circuits, shots) -> counts` cannot serve the analytic runner, which has no circuits. Use `(ks, shots) → PowerResult` records instead. Backend runners build the circuits internally from `(A, flag)`, and every record carries `k`, `shots` and `hits`, which is all MLAE and N_A need.

- **AnalyticRunner(p, rng: np.random.Generator):** `hits = rng.binomial(shots, sin²((2k+1)·asin√p))`. Construct it with `p = check_contract(...)` (the Statevector flag probability), so the emulator's θ is the circuit's θ. That value equals T1 to 1e-12 by the gate. No qiskit is needed at sampling time, so it is safe for Phase 5's large sweeps.
- **BackendRunner(backend, A, flag, measure="flag"):**
  - Builds `power_circuit` for every k, `transpile_once` for each, then makes **one** `backend.run(list, shots=…)` call and reads `hits_from_counts(result.get_counts(i), …)`.
  - Use it with Aer from tests/scripts (`BackendRunner(AerSimulator(method="statevector"), …)`) and with Qollab's Built-in `BasicSimulator` (list jobs work: ks = [0,1,2,4,8] at 200 shots in 1.61 s native, so about 3 s in Pyodide).
  - If `is_ionq(backend)`, raise and point to `IonQRunner`.
  - Per-k shots need a list input. Aer/BasicSimulator take a single `shots`, so group by shots value or issue one job per distinct shots value (local backends allow many jobs).
- **IonQRunner(backend, A, flag):**
  - `run([k], shots)` accepts exactly **one** k and raises `ValueError` on more.
  - Applies the ideal mode (`backend.set_options(noise_model="ideal")` by default; `"none"` keeps the dialog's noise model).
  - Builds `power_circuit(A, flag, k, measure="all")`, `transpile_once`s it, and asserts `max_controls(tc) <= 7` and op names ⊆ BASIS ∪ {measure, barrier}.
  - Calls `backend.run(tc, shots=…)` with a **bare circuit, never a list** (Phase 1: any list → `ionq.multi-circuit.v1` → HTTP 400), then `job.result().get_counts()`.
  - Records `PowerResult(k, shots, hits, source="ionq:<noise_model>")`, plus the IonQ exact probabilities when present (`result.data(0).get("probabilities")`, or `job.get_probabilities()` inside try/except) and the 11-bit histogram (`int(key, 2) & 0x7FF`) for ANLY-02.
  - Wrap the submission in try/except. Phase 1 notes that an `AttributeError` inside qiskit-ionq masks an IonQ error.
- **hits_from_counts(counts, flag_pos, n_clbits):**
  - Keys are little-endian, so the flag is the character at `n_clbits − 1 − flag_pos`.
  - Use `counts.get(...)`, because missing keys mean zero (Aer returned `{'1': 100}` at k=1).
  - Assert `sum(counts.values()) == shots`.
  - Strip spaces from multi-register keys.

**Why measure all 12 qubits on IonQ:** It matches the Phase 1 path that already succeeded (GHZ, all qubits measured). It yields Q1 11-bit strings for Phase 3's `sample_exit_rows(k, bitstrings, source=None)` ([VERIFIED: neutron_qae/mc_lattice.py:177-180] "Back-face exit row (int64, same length) for each 11-bit string ... x = s & 31, a = bit 5, phi = bits 6-9"). The IonQ payload barely changes (12 measure entries are not gates).

### Pattern 6: QAE-04 analytic vs Aer agreement test
- Points (k, shots): (0, 4000), (2, 4000), (8, 4000) on Q1, plus (1, 4000) as a near-1 probability edge.
- Use a seeded Aer run (`seed_simulator=…`) and a seeded analytic run (`np.random.default_rng(…)`).
- Assert per point `|h_aer − h_an| ≤ 4·sqrt(2·shots·p_k(1−p_k)) + 1`, plus `|h_aer/shots − p_k| ≤ 4σ` against the exact `p_k = sin²((2k+1)θ)`.
- Deterministic with seeds; about 0.3 s total on Aer.
- Optional slow test: RMSE over R = 30 MLAE repetitions, Aer vs analytic, at N_A ∈ {900, 3,500}, within 30%.

### Anti-Patterns to Avoid
- **Transpiling A and Q separately, then stitching:** k=1 gives 0.95787 instead of 0.99941, at both opt-level 0 and 1 (measured). Always transpile the composed A·Q^k once (QC-06 requires this anyway). Pitfall 1 explains why.
- **`transpile(c, ionq_backend)` or `transpile(c, AerSimulator())`:** the IonQ target leaves `mcx` with **11 controls** (measured on qiskit-ionq 1.0.2). The Aer target leaves `multiplexer` and `mcx` instructions, and running them segfaulted Aer at k=16. Always use `basis_gates=BASIS`.
- **Using `num_oracle_queries` or raw shots as cost:** use `n_applications(records)`.
- **Using IonQ noisy-model counts as Binomial samples:** with any non-"ideal" `backend.options.noise_model`, qiskit-ionq builds counts as `round(prob * shots)` (deterministic). The same happens with the `noise_model="ideal"` run kwarg. Pitfall 6.
- **One MLAE point at k ≥ 1:** sin²((2k+1)θ) has 2k+1 maxima in [0, π/2], so a single-k MLE is ambiguous. Always include k = 0.
- **Calling `AerSimulator()` inside `neutron_qae/`:** this trips `backend_constructions` even in a module `main.py` never imports.

## Resource Table (QC-05, measured: `transpile(basis=[cx,rz,ry,rx,h,x,sx], optimization_level=1, seed_transpiler=1|7)`, single full-circuit transpile)

| Circuit | Qubits | CX | Depth | Size | IonQ request body (qiskit-ionq 1.0.2, 1000 shots) |
|---------|--------|----|-------|------|-----------------------------------------------|
| Q0 A | 5 | 26 | 82 | 89 | 5.9 KB |
| Q0 Q (one Grover step) | 5 | 88 | 237 | 265 | — |
| Q0 A·Q¹ | 5 | 100 | 270 | 304 | 18.4 KB |
| Q0 A·Q² | 5 | 174 | 458 | 519 | 30.9 KB |
| **Q1 A** | **12** | **313** | **518** | 543 | **31.0 KB** |
| Q1 Q (one Grover step) | 12 | 1,188 | 2,016 | 2,463 | — |
| **Q1 A·Q¹** | 12 | **1,503** | 2,532 | 3,001 | **168 KB** |
| **Q1 A·Q²** | 12 | **2,693** | 4,546 | 5,459 | **305 KB** |
| Q1 A·Q⁴ | 12 | 5,073 | — | 10,375 gates | 579 KB |
| Q1 A·Q⁸ | 12 | 9,833 | — | 20,207 gates | 1.13 MB |
| Q1-lite A (no φ) | 8 | 73 | 166 | 187 | 11.4 KB |
| Q1-lite A·Q¹ | 8 | 399 | 757 | 996 | 57 KB |
| Q1-lite A·Q² | 8 | 725 | 1,348 | 1,805 | 103 KB |

[VERIFIED: scratch proto1.py and proto5.py with qiskit-ionq 1.0.2 `qiskit_to_ionq`; max controls = 1 in every row]

- Everything fits in 24 qubits.
- **Where the CX go:**
  - The 8-control escape multiplexer is 256 CX of Q1's 313.
  - The zero reflection S₀ is an ancilla-free **11-control MCX, 564 CX on its own**, about 47% of every Grover step.
  - 168 of the 256 escape angles are zero (backward bins), but `UCRYGate` still pays 2⁸ CX.
- **Phase 2 note on dropping φ.** T1 stays exact without φ and Q1-lite is 4× cheaper. However, ANLY-02 ("direct sampling of Q1") and Phase 3's shared `sample_exit_rows` need φ to resolve exit rows by direction bin. **Keep φ in Q1.** Build Q1-lite via `build_q1(K, direction=False)` only as the IonQ fallback if the 168 KB k=1 body is rejected.

## IonQ Path Under One-Circuit-per-Run (recommendation)

**Recommended: the multi-Run protocol, with every Run self-contained.**
1. The interim `main.py` exposes `def main(mode: str = "qae", k: int = 1, shots: int = 1000, ideal_mode: str = "set_options", model: str = "Q1"):` (one line, literal defaults). `mode="smoke"` keeps the Phase 1 smoke path.
2. **On IonQ** (`is_ionq(backend)`): one `IonQRunner.run([k], shots)` call per Run. It prints a summary and one line `IONQ_RECORD={"model","k","shots","hits","noise_model","ideal_mode","counts11","probabilities_flag","n_A","cx","body_bytes","qiskit_ionq","timestamp"}`, plus the single-record MLAE result where k = 0.
3. **On Built-in** (`BasicSimulator`; logged-out judges): live MLAE through `BackendRunner` over `exponential(4)` = [0,1,2,4] with `shots` per power, in one list job, printing `a_hat`, |a_hat − T1| and N_A. This is the judged path.
4. **Tonight, signed in, IonQ Forte 1 entry, `ideal_mode=set_options`:** Hippolyte runs k = 0, then 1, then 2, at shots = 1000 each. That is about 3 × 13 s, and N_A = 1000·(1+3+5) = 9,000. He pastes the three `IONQ_RECORD` lines into `data/ionq_runs.json`. Optionally he adds k = 0 and k = 1 with `ideal_mode=none` (forte-1 noise) as the honest noisy comparison; those carry probabilities, not samples.
5. `runners.load_ionq_records()` reads `IONQ_RUNS_FILE = "data/ionq_runs.json"` (a literal, so the data gate passes). A test asserts `mlae.estimate(records)` accepts them and that the IonQ estimate lies within 4σ (Fisher) of T1.

**What SC4 means under this protocol:**
- At least one Qollab IonQ Run executes one Q1 A·Q^k circuit: transpiled once to BASIS (max 1 control ≤ 7), sent bare via `backend.run`, read via `get_counts`, with no Sampler.
- Its counts parse via `hits_from_counts` into a `PowerResult` that `mlae.estimate` accepts.
- The k = 0, 1, 2 records together give a three-power IonQ-only MLAE estimate with N_A reported.
- The full 1/N_A curve comes from the analytic and Aer runners (QAE-04 validates the emulator). Say so in docs (DOCS-05).

**Why not a single Run with mixed sources:** combining one IonQ point with in-browser analytic points would be honest only if labelled. It also blurs the "IonQ estimate" claim. The 3-Run protocol costs Hippolyte under a minute.

**Size ladder:** submit k=0 (31 KB) first, then k=1 (168 KB), then k=2 (305 KB).
- If Qollab answers "Circuit size is too large, please try running a smaller circuit (less gates)" (its rewrite of a 400 "request body too large", per 01-RESEARCH.md R11), switch to `model="Q1lite"` (k=1 57 KB, k=2 103 KB) and record that.
- IonQ's documented per-gate limit is "We support up to 7 controls per gate", and its multi-circuit limit is "at most 150,000 gates" [CITED: docs.ionq.com/api-reference/v0.3/jobs/create-a-job.md]. Our circuits have 1 control and ≤ 5.5k gates.
- Expected round trip: about 11.5 s for a GHZ (measured). Larger circuits should be similar on the ideal simulator [ASSUMED].

**Why k = 1 is a good live demo:** amplitude amplification lifts P(flag) from 0.243 (k=0) to **0.9994** (k=1) and drops it back to 0.286 (k=2). That is visible at a glance in IonQ counts. Under forte-1 noise, ~1.5k two-qubit gates should wash this out toward 0.5. That is the honest noise story (DOCS-05).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Amplitude loading of the 17-outcome x distribution | Manual RY tree | `StatePreparation(amps)` | Invertible Gate, 26 CX, exact to 3e-15 |
| Multiplexed rotations | Hand-built controlled-RY ladders | `UCRYGate(angles)`, qubits `[target] + controls`, first control = LSB | Verified bit-exact against `exact.py` |
| Grover operator | Manual S₀ / A† assembly | `qiskit.circuit.library.grover_operator(oracle, state_preparation=A)` | The function form is required; the class is deprecated |
| MCX decomposition for IonQ | Custom ≤7-control ladders | `transpile(basis_gates=BASIS)` | Gives 1-control gates; size is within limits |
| MLE grid size and likelihood convention | New conventions | Mirror qiskit-algorithms (`grid_size`, ε = 1e-15, θ ∈ [ε, π/2−ε]) | Makes the QAE-01 equality exact |
| Exit-row assignment from Q1 strings | A second row sampler | Phase 3 `mc_lattice.sample_exit_rows` | One row rule for both histograms (ANLY-02) |

## Common Pitfalls

### Pitfall 1: Stitching separately transpiled A and Q gives wrong amplitudes
**What goes wrong:** `transpile(A)` + `transpile(G)` composed gives P = 0.95787 at k=1, against 0.99941 (measured, opt 0 and 1).
**Why it happens:** Individually, `StatePreparation` and `UCRY` transpile consistently with their inverses (checked: transpiled(sp)·transpiled(sp†) = I). The likely cause is that the standalone G synthesizes the `mcx`/zero-reflection using qubits that are idle at G's start (for example φ) as clean ancillas, which is false mid-circuit [ASSUMED mechanism]. Building G from an already BASIS-transpiled A, then stitching, was exact (k=16 diff 4.6e-13).
**How to avoid:** Compose the logical A·Q^k, then `transpile_once`. Add a negative test that asserts the stitched k=1 deviates by more than 1e-3, so the trap stays documented.
**Warning signs:** k ≥ 1 probabilities off by percent while k = 0 is exact.

### Pitfall 2: Aer segfault on untranspiled multiplexers
**What goes wrong:** `transpile(c, AerSimulator())` keeps `multiplexer` (5), `mcx` (4), `rxx` and `cp`. `aer.run` on Q^16·A then crashed with SIGSEGV in `AER::Circuit::multiplexer` (exit 139, faulthandler trace). [VERIFIED: scratch]
**How to avoid:** Always `transpile(..., basis_gates=BASIS)` before Aer. Run Aer tests with `-X faulthandler` in CI so a crash is diagnosable.

### Pitfall 3: Little-endian keys and missing count keys
- Qiskit count keys put qubit 0 rightmost. With `measure_all` on Q1 the flag is `key[0]` and `int(key, 2) & 0x7FF` is `exact.py`'s s.
- With the 1-clbit register the keys are `'0'`/`'1'`.
- Aer omits zero-count keys (`{'1': 100}`). Always use `.get(key, 0)` and check the total.

### Pitfall 4: qiskit-algorithms' default MLE is not the MLE
**What goes wrong:** `compute_mle` uses `brute(..., Ns)` with scipy's default `finish=fmin` (xtol 1e-4). In 24 cases it landed up to 3.6e-5 in *a* away from the true maximizer, always at lower likelihood (for example 0.200025 vs the closed-form 0.2 for 2/10 hits at k=0). [VERIFIED: scratch mlae_proto.py]
**How to avoid:** Use the vendored golden-section refinement for all reported numbers. In the QAE-01 test, prove equality via the shared likelihood plus the same minimizer, not via raw default outputs. Mention it in the README as a technical-execution detail.

### Pitfall 5: NaN in the likelihood
**What goes wrong:** `h * log(sin²)` with h = 0 and sin = 0 gives `0 * -inf = NaN`, and `np.argmax` returns the NaN index.
**How to avoid:** Use `np.where(h > 0, …, 0)` as in Pattern 4, and test hits = 0 and hits = shots at each k.

### Pitfall 6: IonQ counts that are not samples
**What goes wrong:** qiskit-ionq 1.0.2 `_build_counts` samples only when `backend.options.noise_model == "ideal"` (`use_sampler=is_ideal_sim`). Otherwise `cnt = round(prob * shots)`. Noisy forte-1 runs and the `noise_model="ideal"` run kwarg therefore both give deterministic counts. [VERIFIED: venv102 qiskit_ionq/ionq_job.py `_build_counts` and `_format_result`, read this session; consistent with Phase 1 R4/R5/R6]
**How to avoid:** Use `set_options(noise_model="ideal")` for statistics. Tag noisy records `sampled=False` and exclude them from MLAE (report their probabilities instead). Optionally pass `sampler_seed` for reproducible ideal sampling.

### Pitfall 7: Request-body size on Qollab's proxy
**What goes wrong:** Qollab rewrites a 400 "request body too large" to "Circuit size is too large". The limit is unknown, while k=1 is 168 KB and k=2 is 305 KB.
**How to avoid:** Follow the size ladder (k=0 first). Keep Q1-lite as a fallback. Print `body_bytes` (computed via `len(json.dumps(...))`, or estimated as about 56 bytes × gate count) in `IONQ_RECORD` so the limit gets bracketed empirically.

### Pitfall 8: The compliance gates and the Aer runner
**What goes wrong:** Any `from qiskit_aer import …` in a main-reachable module, or any `AerSimulator(` call inside `neutron_qae/`, fails `tests/test_compliance.py`.
**How to avoid:** Keep one generic `BackendRunner`, inject Aer from `tests/` and `scripts/` only, and use `pytest.importorskip("qiskit_aer")` / `("qiskit_algorithms")` in tests.

### Pitfall 9: Changing main.py breaks Phase 1 smoke tests
**What goes wrong:** `tests/test_smoke.py` calls `entry.main(shots=200, ghz_qubits=4, ideal_mode="none", perf_qubits=4)` and asserts `report["toy"]`.
**How to avoid:** When main.py gains the QAE mode, update test_smoke in the same plan. Keep `run_toy` reachable via `mode="smoke"` and keep the fake-IonQ "exactly one bare circuit" test, re-pointed at the QAE path.

### Pitfall 10: Slow tests
- k=64 Statevector takes about 6 s and the 12-qubit `Operator` identity check can stall.
- Mark the k ∈ {32, 64} sweep and the Aer RMSE repetitions `@pytest.mark.slow`.
- The fast suite should be k ≤ 16 (about 3 s), Q0 operator identity, and Q1 statevector round trip.

## Code Examples

### IonQ single-circuit run (the one call the IonQ path makes)
```python
def run_ionq_point(backend, A, flag, k, shots, ideal_mode="set_options"):
    if ideal_mode == "set_options":
        backend.set_options(noise_model="ideal")          # mutates injected backend, never creates one
    tc = transpile_once(power_circuit(A, flag, k, measure="all"))
    assert max_controls(tc) <= 7 and set(tc.count_ops()) <= set(BASIS) | {"measure", "barrier"}
    job = backend.run(tc, shots=int(shots))               # bare QuantumCircuit -> ionq.circuit.v1
    counts = dict(job.result().get_counts())
    hits = sum(v for key, v in counts.items() if key.replace(" ", "")[0] == "1")  # flag = qubit 11 = leftmost
    return PowerResult(k, int(shots), hits, source=f"ionq:{getattr(backend.options, 'noise_model', '?')}"), counts
```
`max_controls(c) = max((getattr(i.operation, "num_ctrl_qubits", 0) for i in c.data), default=0)`.

### Resource row
```python
def resources(tc):
    ops = tc.count_ops()
    return {"qubits": tc.num_qubits, "cx": ops.get("cx", 0), "depth": tc.depth(), "size": tc.size(),
            "max_controls": max_controls(tc)}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `GroverOperator` class | `grover_operator()` function | Qiskit 2.1 (class removed in 3.0) | Use the function |
| Multi-circuit MLAE job on IonQ | One circuit per Qollab Run, multi-Run aggregate | Phase 1 finding, 2026-10-10 | IonQ estimate needs ≥ 2 Runs (k = 0 plus higher) |
| QPE-based AE | MLAE (Suzuki et al. 2020) | — | Zero extra qubits |

**Prior art for the README (DOCS-04 input).**

Lee, Lee and Kim (Phys. Rev. D 111, 116001, 2025; arXiv:2502.14374) [CITED: arxiv.org/html/2502.14374v1] simulate 10 MeV photons in water:
- 1D depth in 1 cm steps, with 15- and 31-step runs.
- Compton scattering only, treated as a binary interact/survive coin per step with p = 1 − e^{−μΔx}.
- Built as a discrete-time quantum walk U = S(C⊗I) with position-controlled coins and no resets.
- Estimated with **iterative** QAE (ε = 0.01, 95% confidence, 30 shots per iteration) on IBM's Qiskit simulator ("a 32-qubit simulator"). Memory limits restricted IQAE to the 15-step case.
- They report error falling as O(1/N_q) against a GEANT4 O(1/√N_q) reference. They state limitations of a single channel, complete absorption and simulator-only results.

Our design differs on four axes:
1. **One quantum step per collision event,** with collision-to-collision kernels precomputed from ENDF/B-VIII.0 cross sections. Every random choice gets a fresh register: first-collision column (17 outcomes), scatter/absorb, 16 direction bins, flight outcome. This reaches a 2D, two-material (WHA/316 SS) wall in 12 qubits instead of a step-by-step walk.
2. **Ground truth from an exact enumeration of the same discrete model** (T1 to 1e-12), with a matched lattice Monte Carlo baseline estimating the identical quantity. They compare to GEANT4 (a different model), so they cannot separate truncation bias from sampling error.
3. **Non-adaptive MLAE** with cost counted as applications of A, N_A = Σ shots·(2k+1), rather than Qiskit's `num_oracle_queries`.
4. **Execution of A·Q^k on IonQ's cloud simulator via Qollab** with an explicit one-circuit-per-Run protocol.

Their qubit counts per run are not stated explicitly in the fetched text, so do not quote one. Olivier & Nowak (arXiv:2410.19489) and Miao/Jin/Sone (arXiv:2607.10772) are as summarized in PROJECT.md (not re-fetched).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Qollab's proxy accepts request bodies of at least 168 KB (Q1 k=1) | IonQ Path | k=1 rejected. Fall back to Q1-lite (57 KB) or k=0; SC4 still met with k=0 + Q1-lite k=1/2 |
| A2 | IonQ ideal-simulator round trip for a 3k-gate, 12-qubit circuit is about the 11.5 s measured for GHZ | IonQ Path | Longer Runs; still minutes total |
| A3 | Stitching failure mechanism = clean-ancilla assumption in standalone G synthesis | Pitfall 1 | None. The rule (transpile once) is verified empirically either way |
| A4 | qiskit-ionq 1.0.2 returns well-formed 12-bit count keys for `measure_all` circuits on Qollab | Pattern 5 | Parse failure. `hits_from_counts` validates totals; Phase 1 GHZ path (all qubits measured) worked |
| A5 | Forte-1 noise drives Q1 A·Q¹ toward P ≈ 0.5 | IonQ Path | Narrative only; report whatever is measured |
| A6 | Lee/Lee/Kim details (as fetched from arXiv HTML v1; the published PRD may differ slightly) | Prior art | Wording in README; cite arXiv version |

## Open Questions (RESOLVED — Q1 size ladder PD-21; Q2 Phase 4 owns the interim QAE main.py PD-19; Q3 noisy records kept as sampled:false PD-20; Q4 one late human checkpoint PD-22)

1. **Qollab request-body limit.**
   - What we know: oversized bodies get "Circuit size is too large". Bodies are 31 KB, 168 KB and 305 KB for k = 0, 1, 2.
   - What's unclear: the threshold.
   - Recommendation: run the ladder tonight and record `body_bytes`. Switch to Q1-lite on the first rejection.
2. **Where the interim QAE main.py lives relative to Phase 6.**
   - Recommendation: Phase 4 owns the minimal QAE mode (needed for SC4 before 7 AM). Phase 6 extends it with precomputed figures. Update `tests/test_smoke.py` in the same plan.
3. **Should IonQ records include the noisy forte-1 runs?**
   - Recommendation: yes, as `sampled: false` records with probabilities, excluded from MLAE. They are useful for DOCS-05's noise discussion.
4. **Human checkpoint.** The IonQ Runs need Hippolyte signed in on Qollab: upload a new bundle, run k = 0, 1, 2 and paste the records. Plan this as a `checkpoint:human-action` with exact form values, scheduled before ~7 AM ET.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | all | ✓ | 3.14.8 | — |
| qiskit | all circuits | ✓ (.venv) | 2.5.2 | — |
| numpy / scipy | MLAE, kernels | ✓ | 2.5.3 / 1.18.1 | — |
| pytest | tests | ✓ | 9.1.1 | — |
| qiskit-aer | QC-03 Aer variant, QC-04 slow, QAE-04 | ✗ in .venv (✓ in scratch) | 0.17.2 | `pip install -e ".[dev]"`; tests skip without it |
| qiskit-algorithms | QAE-01 equality test | ✗ in .venv | 0.4.0 | same install; test skips without it |
| qiskit-ionq | optional serialization/payload test | ✗ in .venv | 1.0.2 (Qollab) | skip; Qollab installs it for IonQ runs |
| Qollab IonQ Forte 1 (signed in) | SC4 | ✓ (Phase 1 R4-R6) | qiskit-ionq 1.0.2 | Q1-lite if the body is too large |

**Missing dependencies with no fallback:** none.
**Missing with fallback:** Aer and qiskit-algorithms. The dev-extras install is already approved; until it runs, those tests skip.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Qollab handles sign-in; no keys in code) | never embed IonQ keys; backend injected |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Clamp `main()` form inputs: `model ∈ {"Q0","Q1","Q1lite"}`, `0 ≤ k ≤ 8` on IonQ (≤ 64 local), `2 ≤ shots ≤ 10_000`, `ideal_mode ∈ {"none","set_options"}` (reject `kwarg` for statistics); validate `data/ionq_runs.json` records (ints, k ≥ 0, 0 ≤ hits ≤ shots) on load |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Oversized job from form fields (cost/queue abuse, proxy rejection) | DoS | k/shots clamps; one job per Run |
| Tampered `ionq_runs.json` inflating results | Tampering | Schema validation; records carry probabilities and timestamps; README states they were hand-pasted from console |
| Credential leakage | Info disclosure | No tokens anywhere; `IonQProvider` never constructed in the package (gate) |

## Sources

### Primary (HIGH)
- Scratch measurements this session (qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-algorithms 0.4.0, qiskit-ionq 1.0.2 and 1.1.1, Python 3.14.8; scripts in the session scratchpad `phase4/scripts/`): flag probabilities, Grover sweep, resources, payload sizes, stitching failure, Aer segfault, MLAE comparisons, RMSE scaling, Aer MLAE, BasicSimulator list job.
- In-repo files read this session: `neutron_qae/exact.py`, `kernels.py`, `problem.py`, `smoke.py`, `mc_lattice.py`, `main.py`, `pyproject.toml`, `tests/compliance_checks.py`, `tests/test_compliance.py`, `tests/test_smoke.py`, `tests/golden/kernels_v1.json`, `docs/QOLLAB-RUNTIME.md`, Phase 1/2 summaries and research, `.planning/research/{STACK,ARCHITECTURE,PITFALLS}.md`.
- Library source read this session: `qiskit_algorithms/amplitude_estimators/mlae.py` (lines 100-106, 229-264, 337, 567-590), `estimation_problem.py`; `qiskit_ionq` 1.0.2 `helpers.py` (`ionq_basis_gates`, `qiskit_circ_to_ionq_circ`, `qiskit_to_ionq`), `ionq_backend.py` (`run`, `IonQSimulatorBackend`), `ionq_job.py` (`_build_counts`, `_format_result`, `get_probabilities`).

### Secondary (MEDIUM)
- IonQ API v0.3 create-a-job (7 controls per gate; 150,000 gates per multi-circuit job): https://docs.ionq.com/api-reference/v0.3/jobs/create-a-job.md
- Lee, Lee & Kim, arXiv:2502.14374 (HTML v1): https://arxiv.org/html/2502.14374v1 ; abstract https://arxiv.org/abs/2502.14374v1 ; PRD 111, 116001 per https://ir.ymlib.yonsei.ac.kr/handle/22282913/207874

### Tertiary (LOW)
- Qollab proxy body-size threshold: not documented; inferred from the 01-RESEARCH.md R11 rewrite rule only.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Versions are pinned and were exercised.
- Circuit design and resources: HIGH. Measured on the frozen tables.
- MLAE and scaling: HIGH. Prototyped, and cross-checked against qiskit-algorithms and Aer.
- IonQ path: MEDIUM. Serialization and gate rules are verified; body-size limit and runtime are unverified until tonight's Runs.

**Research date:** 2026-10-10
**Valid until:** end of hackathon (2026-10-11 19:00 ET); re-check the Qollab qiskit/qiskit-ionq versions before the final publish.
