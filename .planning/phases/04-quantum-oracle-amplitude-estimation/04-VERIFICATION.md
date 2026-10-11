---
phase: 04-quantum-oracle-amplitude-estimation
verified: 2026-10-11T00:00:00Z
status: passed
score: 6/6 must-haves verified (5 ROADMAP success criteria + the plan 04-04 IonQ-accuracy truth; the last carried as a human-accepted override, NOT met on the merits)
covered_files:
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-01-PLAN.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-01-SUMMARY.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-02-PLAN.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-02-SUMMARY.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-03-PLAN.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-03-SUMMARY.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-04-PLAN.md"
  - ".planning/phases/04-quantum-oracle-amplitude-estimation/04-04-SUMMARY.md"
  - "data/ionq_runs.json"
  - "docs/QOLLAB-RUNTIME.md"
  - "docs/QUANTUM.md"
  - "main.py"
  - "neutron_qae/grover.py"
  - "neutron_qae/mlae.py"
  - "neutron_qae/oracle.py"
  - "neutron_qae/runners.py"
  - "scripts/ingest_ionq_records.py"
  - "scripts/run_local.py"
  - "tests/test_grover.py"
  - "tests/test_ionq_records.py"
  - "tests/test_main_qae.py"
  - "tests/test_mlae.py"
  - "tests/test_oracle.py"
  - "tests/test_runners.py"
covered_digest: "v3:sha256:1598256f10d4d1cb6c63d25c86cd5c38b4bc4ff400daea6b07abe51fa94970a1"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "QAE-01 on IonQ data: the sampled records for k = 0, 1, 2 at 1000 shots parse into PowerResults that mlae.estimate accepts, and tests/test_ionq_records.py::test_ionq_only_estimate_within_4_sigma runs and passes with the IonQ-only a_hat within 4 Fisher sigma of T1 = 0.24300446519524305"
    reason: "Human-judgment-accepted deviation (option (a) at the plan 04-04 checkpoint). The real IonQ Forte 1 records give a_hat = 0.228671 +/- 0.00224, z = -6.38 (N_A = 9000). The IonQ half of success criterion 4 (execution proof: circuit runs on Qollab's IonQ simulator, counts come back, MLAE accepts them) is met; the IonQ-only ACCURACY truth is NOT met and its cause is OPEN. The 4-sigma assertion is not loosened; it is a strict xfail keyed to exactly these three records."
    accepted_by: "Hippolyte Delloye"
    accepted_at: "2026-10-11"
gaps: []
deferred: []
human_verification: []
---

# Phase 4: Quantum Oracle & Amplitude Estimation Verification Report

**Phase Goal:** A state-preparation circuit within 24 qubits, whose flag probability equals the exact lattice value, is wrapped in Grover powers and a vendored maximum-likelihood amplitude estimator, producing transmission estimates through analytic, Aer and IonQ runners with cost counted honestly as applications of A.
**Verified:** 2026-10-11
**Status:** passed, with ONE explicitly recorded human-accepted deviation (below)
**Re-verification:** No, initial verification

## Human-accepted deviation (read first)

The phase is `passed` only because the user explicitly accepted this deviation at the 04-04 checkpoint. On the merits it is a real, unresolved finding, not a pass.

- Plan 04-04 truth "QAE-01 on IonQ data" required the IonQ-only MLAE estimate to land within 4 Fisher sigma of T1. It does not. I recomputed it independently from `data/ionq_runs.json`: a_hat = 0.228671, se = 0.002245, N_A = 9000, z = -6.38 against T1 = 0.24300446519524305.
- Per-point residuals against sin^2((2k+1) theta), recomputed here: k = 0, 267 vs 243.0 expected (z = +1.77, consistent); k = 1, 988 vs 999.4 expected (z = -14.8, far beyond shot noise); k = 2, 349 vs 285.9 expected (z = +4.4). The three records are mutually inconsistent with any single amplitude (docs/QOLLAB-RUNTIME.md reports G = 14.6 on 2 dof).
- The circuit is not the cause as far as can be tested here. Locally, the same BASIS-transpiled circuits reproduce the exact probabilities: independent Aer statevector gives P(flag) = 0.24300, 0.99941, 0.28593 at k = 0, 1, 2. The docs record that IonQ's own "Probabilities" panel shows the same shifts, which places the deviation in IonQ's ideal cloud simulation or in qiskit-ionq 1.0.2 serialisation on Qollab. The rotation-angle-rounding hypothesis was tested locally and does not reproduce it. Cause: OPEN.
- What is NOT lost: ROADMAP success criterion 4 asks that an IonQ-runner job "completes on Qollab's IonQ simulator and yields counts the MLAE accepts". That holds (three accepted runs, schema-valid, `mlae.estimate` accepts them). It does not ask for IonQ accuracy. The 4-sigma accuracy requirement lives only in plan 04-04's must-haves, which is why an override is the correct instrument.
- Consequence for later phases: no IonQ-hardware-path accuracy can be claimed. Phase 5/6 narrative must use analytic/Aer evidence for the scaling curve and present the IonQ runs as an execution proof with a documented discrepancy (README already does; `No speedup is claimed`).
- Test integrity: `tests/test_ionq_records.py::test_ionq_only_estimate_within_4_sigma` is `xfail(strict=True)` keyed to the exact record set `KNOWN_4SIGMA_MISS`. The assertion is untouched (`abs(a_hat - t1) <= 4 * se`). Any change to the data file switches the xfail off, and the test would then pass or fail honestly. `test_known_4sigma_miss_matches_data` pins z = -6.38. I confirmed this in the suite output (`1 xfailed`).

## Goal Achievement

### Observable Truths (ROADMAP success criteria are the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Q0 flag P = e^{-tau}; Q1 flag P (fresh qubits, no measure/reset inside A, invertible) = exact lattice value to 1e-12; contract gates every QAE run | VERIFIED | Independent run: Q0 p = 0.23256718303629134 vs 0.23256718303628812 (d = 3.2e-15); Q1 p = 0.24300446519524654 vs T1 0.24300446519524305 (d = 3.5e-15). A raw-numpy re-sum of `Statevector(A)` amplitudes over flag=1 gives the same 3.4e-15. `make_problem` calls `check_contract` and raises `ContractError` beyond 1e-12 and is the only constructor used by runners/main.py. `build_q1` uses a distinct qubit per random choice (x5, a1, phi4, e1, T1 = 12) and no measure/reset (A is a pure gate circuit; invertibility test in suite). |
| 2 | Q^k from `grover_operator()` reproduces sin^2((2k+1)theta) for k up to 64 | VERIFIED | `grover()` calls `qiskit.circuit.library.grover_operator`. Independent Aer-statevector sweep of the transpiled-once A·Q^k: Q1 at k = 0,1,2,8,16,32,64 and Q0 at the same ks, worst |d| = 6.8e-13 (Q1 k = 64), all < 1e-11. `NEUTRON_QAE_SLOW=1 pytest -m slow`: 5 passed. |
| 3 | Vendored numpy MLAE on counts from one `backend.run([...])` of A·Q^k returns the same estimate as qiskit-algorithms MLAE on identical counts; cost = N_A = sum shots(2k+1), never raw shots or `num_oracle_queries` | VERIFIED | Spy backend around Aer: `BackendRunner.run([0,1,2,4,8], 200)` made exactly 1 `backend.run` call carrying 5 circuits. Vendored a_hat = 0.2413849 vs qiskit-algorithms `compute_mle` (default minimizer) a = 0.2413897, d = 4.8e-6 (plan tolerance 1e-4; with an identical minimizer parity is 1e-8, and with brute over the same likelihood 1e-12, both in suite). N_A reported 7000 = 200 * (1+3+5+9+17); qiskit's shots*sum(k) would be 3000. `MLAEResult` carries `n_A` and `shots_total`; `mlae.py` imports only numpy and stdlib. |
| 4 | Analytic, Aer and IonQ runners share one interface; analytic and Aer agree within statistical error on at least three (k, shots) points; an IonQ-runner job (<= 7 controls, transpiled once, `backend.run` + `get_counts`, no Sampler) completes on Qollab's IonQ simulator and yields counts MLAE accepts | VERIFIED (IonQ accuracy deviation recorded above) | Runners: `AnalyticRunner`, `BackendRunner`, `IonQRunner` all expose `name` and `run(ks, shots)`; compliance suite green (no backend constructed or aer/algorithms/ionq imported in package code; grep confirms only comments/strings mention them). Analytic (seed 404) vs Aer (seed_simulator 404) at 4000 shots: k = 0, 970 vs 973; k = 1, 3999 vs 3998; k = 2, 1164 vs 1178; k = 8, 1541 vs 1521, all well inside the 4 sigma plus 1 tolerance (differences 3, 1, 14, 20 vs bounds 154, 9.7, 163, 174). IonQ: three schema-valid records in `data/ionq_runs.json` (qiskit_ionq.ionq_backend.IonQSimulatorBackend, accepted, max_controls 1, sampled true, ideal via set_options), `load_ionq_records` + `ionq_estimate` accept them and `main.py` prints the estimate on the Built-in path. Execution happened on Qollab per the user-pasted console lines quoted verbatim in docs/QOLLAB-RUNTIME.md; I cannot re-run Qollab itself, so this part rests on those pasted records (validated by the schema checker and the docs-vs-data test). |
| 5 | Resource table lists qubits, CX count, depth for Q0 and Q1 after a single full-circuit transpile, within 24 qubits | VERIFIED | `resource_table()` regenerated: Q0 5q/26/100/174 CX at k = 0,1,2; Q1 12q/313/1503/2693 CX, depth 518/2532/4546; Q1lite 8q. All <= 12 qubits. Matches the plan's recorded numbers and docs/QUANTUM.md (a doc-drift test is in the suite). One `transpile_once` per circuit (explicit BASIS, level 1, seed 1); the stitched recipe negative test (P = 0.95787 vs 0.99941) is in `tests/test_grover.py`. |
| 6 | (Plan 04-04) IonQ-only MLAE estimate within 4 sigma of T1 | PASSED (override), NOT MET on the merits | See "Human-accepted deviation". a_hat = 0.228671, z = -6.38. Accepted by Hippolyte Delloye, option (a). |

**Score:** 6/6 (5 verified; 1 carried by a human-accepted override that is not a merits pass).

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `neutron_qae/oracle.py` | VERIFIED | Substantive (Q0/Q1/Q1lite builders, contract gate, `make_problem`), wired into runners and main.py, data flows from frozen `Kernels` tables. |
| `neutron_qae/grover.py` | VERIFIED | `grover_operator()`, `power_circuit`, `transpile_once`, `check_ionq_safe`, `resource_table`; used by runners. |
| `neutron_qae/mlae.py` | VERIFIED | Vendored MLE, Fisher se, `n_applications`. |
| `neutron_qae/runners.py` | VERIFIED | Three runners, `hits_from_counts`, record validation/loader, `ionq_estimate`. |
| `main.py`, `scripts/run_local.py`, `scripts/ingest_ionq_records.py` | VERIFIED | Tracer runs end to end (below). |
| `data/ionq_runs.json` | VERIFIED | 3 real records, 20,104 bytes (< 2 MB), referenced by literal path. |
| `docs/QUANTUM.md`, `docs/QOLLAB-RUNTIME.md` | VERIFIED | Resource table, `## Phase 4 IonQ runs`, verbatim lines, deviation analysis. |
| Tests (`test_oracle`, `test_grover`, `test_mlae`, `test_runners`, `test_ionq_records`, `test_main_qae`) | VERIFIED | Present and executed. |

### Key Link Verification

| From | To | Status | Details |
|------|----|--------|---------|
| oracle.py | exact.py / kernels.py | WIRED | `transmission_within(kernels, K)` is the contract reference; frozen tables supply all rotation angles. |
| grover.py | `grover_operator` / `transpile` | WIRED | Single `transpile(c, basis_gates=BASIS, optimization_level=1, seed_transpiler=seed)`. |
| runners.py | oracle/grover/mlae | WIRED | `OracleProblem`, `transpile_once`, `PowerResult`. |
| main.py | runners / oracle | WIRED | Tracer exercises `make_problem` -> `BackendRunner` -> `mlae.estimate`. |
| data/ionq_runs.json | main.py Built-in path | WIRED | `QAE_REPORT` includes `ionq_records` with a_hat 0.228671, n_A 9000. |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| QAE_REPORT a_hat | hits | live `BasicSimulator` job over A·Q^k circuits | yes | FLOWING |
| IonQ-only estimate | hits | `data/ionq_runs.json` real Qollab counts (hits recomputed from counts by validator) | yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Default suite | `.venv/bin/python -m pytest -q` | 337 passed, 5 skipped, 1 xfailed, 26.8 s | PASS |
| Slow set | `NEUTRON_QAE_SLOW=1 pytest -q -m slow` | 5 passed, 94 s | PASS |
| QAE tracer | `scripts/run_local.py --seed 2026` | hits [262, 1000, 277, 997], a_hat 0.245094, N_A 18000, contract |d| = 3.5e-15, `QAE RUN COMPLETED` | PASS |
| Smoke mode kept | `scripts/run_local.py --mode smoke` | `SMOKE TEST PASSED` | PASS |
| Frozen contract | `scripts/freeze_kernels.py` | `GOLDEN OK`; `git diff 55b334d HEAD` on kernels/exact/problem/nuclear_data/mc_*/random_source/tests/golden is empty | PASS |
| Bundle | `git archive HEAD` | 19 files (LICENSE, README, 2 data, main.py, 13 modules, requirements.txt) | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes exist or are declared by the plans. Step 7c: not applicable.

### Requirements Coverage

All ten IDs appear in plan frontmatter (04-01: QC-01..QC-06; 04-02: QAE-01..QAE-04; 04-03: QAE-02, QC-05, QC-06; 04-04: QAE-01, QAE-02, QC-06). REQUIREMENTS.md maps exactly these ten to Phase 4; no orphans.

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| QC-01 | 04-01 | SATISFIED | Q0 5 qubits, `StatePreparation`, p = e^{-tau} to 3.2e-15 |
| QC-02 | 04-01 | SATISFIED | Q1 12 qubits, fresh qubits, pure gates, invertibility test |
| QC-03 | 04-01 | SATISFIED | Q1 = T1 to 3.5e-15; `make_problem` gate |
| QC-04 | 04-01 | SATISFIED | `grover_operator()`; sweep to k = 64, max |d| 6.8e-13 |
| QC-05 | 04-01, 04-03 | SATISFIED | Resource table regenerated; doc-drift test |
| QC-06 | 04-01, 04-03, 04-04 | SATISFIED | max_controls 1; transpile once; real IonQ run accepted with one bare circuit |
| QAE-01 | 04-02, 04-04 | SATISFIED for the requirement text (vendored MLAE, one `backend.run([...])`, parity with qiskit-algorithms). The plan 04-04 IonQ-accuracy extension is the accepted deviation. |
| QAE-02 | 04-02, 04-03, 04-04 | SATISFIED | Three runners, one interface, `backend.run` + `get_counts`, no Sampler |
| QAE-03 | 04-02 | SATISFIED | N_A formula reproduced independently (7000 vs 3000 oracle queries) |
| QAE-04 | 04-02 | SATISFIED | Four matched points agree |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| TBD/FIXME/XXX | grep of phase files | none found in the phase's package code | none |
| `ruff check` | 42 findings, mostly tests/ and scripts/ (10 in `tests/test_mlae.py`, 1 in `tests/ionq_fakes.py`; the rest in Phase 2/3 files) | Info | Lint only; no behavior impact. A pre-existing TRY004 is logged in `deferred-items.md`. |

### Findings Classification

- BLOCKER: none.
- WARNING / carried risk: the IonQ accuracy deviation above (cause open, accepted by the user). It is not silently absorbed; it is the `overrides` entry and is documented in README, docs/QUANTUM.md and docs/QOLLAB-RUNTIME.md.
- Prohibitions: all test-tier prohibitions have enforcing tests in the green suite (no backend construction, no stitched transpile, 24-qubit budget, frozen files unchanged, noisy records excluded from the estimate, one circuit per IonQ run). Judgment-tier (no speedup claim; no loosened tolerance; IonQ job count): grep of README/docs/main/runners finds only "No speedup is claimed"; the 4-sigma assertion is untouched; exactly three IonQ jobs were run. These are non-authoritative judgments.

### Human Verification Required

None outstanding. (The Qollab runs were executed by the user; the deviation decision is already recorded.)

### Gaps Summary

No gaps block the phase goal. The goal (contract-exact oracle within 24 qubits, Grover powers, vendored MLAE, three runners, honest N_A) is achieved and independently reproduced. The single unmet item, IonQ-only estimate accuracy, is a documented, user-accepted deviation with an open cause. Recommend tracking it as a follow-up (for example a repeat run, or a check of IonQ's ideal simulation of the BASIS circuit) before any claim about the IonQ path's numerical fidelity.

---

_Verified: 2026-10-11_
_Verifier: Claude (gsd-verifier)_
