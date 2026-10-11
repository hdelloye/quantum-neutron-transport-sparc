---
phase: 04-quantum-oracle-amplitude-estimation
plan: 02
subsystem: quantum
tags: [amplitude-estimation, mlae, maximum-likelihood, qiskit-algorithms, qiskit-aer, basic-simulator, ionq, runners, fisher-information]

# Dependency graph
requires:
  - phase: 04-quantum-oracle-amplitude-estimation (04-01)
    provides: "make_problem / OracleProblem (contract-checked A, flag, p, reference, theta, qubits), power_circuit, transpile_once, check_ionq_safe, resources, MODELS / MODEL_QUBITS / MODEL_FLAG"
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "smoke.is_ionq, compliance gates (no backend construction in the package, no qiskit_aer/algorithms/ionq reachable from main.py), Qollab IonQ facts (one bare circuit per run, set_options ideal = sampled)"
  - phase: 03-classical-baseline
    provides: "random_doubles.foreign_imports AST gate, NEUTRON_QAE_SLOW slow-test convention, LatticeResult.cost unit (one history = one A application)"
provides:
  - "neutron_qae/mlae.py: numpy-only MLAE. PowerResult(k, shots, hits, source='', sampled=True); estimate(records) -> MLAEResult(a_hat, theta, se, n_A, ks, shots, hits, shots_total, records) with as_dict(); n_applications, grid_size, loglikelihood, golden_max, mle_theta, fisher_se, exponential_schedule, linear_schedule; EPS = 1e-15, MAX_POWER = 1024"
  - "neutron_qae/runners.py: Runner protocol; AnalyticRunner(p, rng); BackendRunner(backend, problem, measure='flag', seed_transpiler=1, run_options=None) with circuits(ks) and last_counts; IonQRunner(backend, problem, ideal_mode='set_options', max_k=8) with run_point(k, shots) -> record dict and last_record; hits_from_counts; IonQ record schema v1 (RECORD_KEYS, RECORD_SCHEMA, MODEL_LAYOUT), validate_ionq_record, load_ionq_records, ionq_power_results, ionq_estimate; IONQ_RUNS_FILE = 'data/ionq_runs.json'"
  - "tests/ionq_fakes.py: FakeIonQSimulator(fail=None) with calls (qiskit_ionq module name, noise_model option default forte-1, rejects lists like Qollab's proxy)"
  - "tests/test_mlae.py (15 tests) and tests/test_runners.py (35 default + 2 slow)"
affects: [04-03, 04-04, phase-5, anly-01, anly-02, docs-quantum]

# Actuals (#2632)
actuals:
  tokens: 15647       # chars/4 over the five files created (62,586 chars)
  tasks: 3
  commits: 3
plan_head_before: 603333d0a7b1b78b5f9fbcd57951256ac5294ee6
plan_head_after: 318fadb8cb0edad90411907363d60a90c78b20b5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One runner interface run(ks, shots) -> list[PowerResult] in input order for analytic, local-backend and IonQ runners"
    - "Cost is only ever N_A = sum shots (2k + 1), computed from the records"
    - "Records carry sampled: bool; MLAE refuses unsampled (round(p shots)) counts"
    - "IonQ submissions: validate inputs, transpile once, check_ionq_safe, set_options(noise_model='ideal'), ONE backend.run(bare circuit), record failures without retry"
    - "Untrusted IonQ records re-derive everything checkable (counts width and sum, hits, p_flag, n_A, sampled) on load"

key-files:
  created:
    - neutron_qae/mlae.py
    - neutron_qae/runners.py
    - tests/test_mlae.py
    - tests/test_runners.py
    - tests/ionq_fakes.py
  modified: []

key-decisions:
  - "PD-17 (locked, research): vendored numpy MLAE. Likelihood sum_k [h_k log sin^2((2k+1) theta) + (n_k - h_k) log cos^2((2k+1) theta)] with 0 log 0 = 0; grid np.linspace(EPS, pi/2 - EPS, grid_size(ks)) with grid_size = max(10000, int(pi/2 * 1000 * 2 * max(ks))) and EPS = 1e-15 (qiskit-algorithms' conventions, so the QAE-01 equality is exact); golden-section refinement inside the neighbouring grid points, accepted only if not worse; records sorted before evaluation; Fisher se_a = sin(2 theta) / sqrt(sum 4 n_k (2k+1)^2); cost N_A = sum shots (2k + 1) from our own records (Suzuki et al. 2020, eq. 11), never qiskit's num_oracle_queries. Headline schedule exponential_schedule(M) = [0] + [2**j for j in range(M - 1)]; linear_schedule(M) = list(range(M)). MAX_POWER = 1024 bounds the grid."
  - "PD-18 (locked, research): one runner interface run(ks, shots) -> list[PowerResult]. AnalyticRunner(p, rng); one generic BackendRunner(backend, problem, ...) with the backend injected (Aer from tests/scripts, BasicSimulator on Qollab's Built-in); IonQRunner(backend, problem, ideal_mode) sends one bare circuit per run. Aer and BasicSimulator are constructed only under tests/ and scripts/."
  - "PD-20 (locked, orchestrator): IonQ record schema {schema: 'neutron_qae.ionq_record', schema_version: 1, ...} printed as one IONQ_RECORD= line per Qollab run (04-03) and stored in data/ionq_runs.json (literal IONQ_RUNS_FILE in runners.py); records validated on load; noisy runs (ideal_mode 'none') kept as sampled: false and excluded from the MLAE; sampled is read from the backend's actual options.noise_model after the ideal-mode step."
  - "validate_ionq_record requires every RECORD_KEYS field and also checks layout and p_flag = hits / shots (stricter than the plan's list; the file is hand-pasted)."
  - "QAE-04 slow RMSE agreement compares Aer (R = 30) with an analytic reference at R = 400, so the 30% bound is not eaten by the reference's own sampling noise."

patterns-established:
  - "FakeIonQSimulator from tests/ionq_fakes.py is the shared IonQ double for 04-03 and 04-04"
  - "pytest.importorskip for qiskit_aer / qiskit_algorithms; @pytest.mark.slow + NEUTRON_QAE_SLOW skipif for Aer repetitions"

requirements-completed: [QAE-01, QAE-02, QAE-03, QAE-04]

coverage:
  - id: D1
    description: "Tracer: one BasicSimulator list job of 4 A·Q^k circuits (seed 2026, 1000 shots) gives hits [262, 1000, 277, 997] and an MLAE estimate a = 0.245094, se = 1.26e-3, N_A = 18,000"
    requirement: QAE-01
    verification:
      - kind: integration
        ref: "tests/test_runners.py#test_builtin_list_job_to_mlae_estimate"
        status: pass
    human_judgment: false
  - id: D2
    description: "QAE-01 parity: brute over our likelihood equals qiskit-algorithms compute_mle exactly (|d theta| = 0) on one Aer list job (hits [40, 200, 70, 199, 80]) and 6 seeded cases; qiskit with our minimizer equals mle_theta (|d theta| = 0); vs qiskit's default minimizer |da| <= 3.2e-5 with our likelihood never lower"
    requirement: QAE-01
    verification:
      - kind: integration
        ref: "tests/test_mlae.py#test_brute_on_our_likelihood_equals_qiskit_compute_mle"
        status: pass
      - kind: integration
        ref: "tests/test_mlae.py#test_qiskit_with_our_minimizer_equals_estimate"
        status: pass
      - kind: integration
        ref: "tests/test_mlae.py#test_vendored_beats_or_matches_qiskit_default"
        status: pass
    human_judgment: false
  - id: D3
    description: "QAE-01 probe edges: boundary (a < 1e-12 / > 1 - 1e-12, finite at grid ends), same-k merge, empty and invalid records, order invariance, no NaN, unsampled refused, schedules, numpy-only, k_max = 64 under 1 s and k 2048 refused"
    requirement: QAE-01
    verification:
      - kind: unit
        ref: "tests/test_mlae.py (11 edge tests: test_boundary_estimates ... test_large_power_is_fast_and_capped)"
        status: pass
    human_judgment: false
  - id: D4
    description: "QAE-03: N_A = 1,800 on ks [0, 1, 2, 4] x 100 where qiskit-algorithms reports num_oracle_queries = 700; MLAEResult has n_A and shots_total and no queries field"
    requirement: QAE-03
    verification:
      - kind: integration
        ref: "tests/test_mlae.py#test_cost_is_applications_not_oracle_queries"
        status: pass
    human_judgment: false
  - id: D5
    description: "QAE-02: AnalyticRunner, BackendRunner and IonQRunner satisfy the Runner protocol; BackendRunner refuses IonQ and groups shots; IonQRunner sends one bare 12-qubit IonQ-safe circuit, labels noisy runs unsampled, validates inputs before any job and records failures without retrying"
    requirement: QAE-02
    verification:
      - kind: unit
        ref: "tests/test_runners.py#test_runners_share_one_interface"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_ionq_runner_sends_one_bare_circuit"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_ionq_runner_labels_noisy_runs_unsampled"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_ionq_runner_rejects_bad_inputs_before_any_job"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_ionq_runner_reports_submission_failure"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_backend_runner_refuses_ionq_and_groups_shots"
        status: pass
    human_judgment: false
  - id: D6
    description: "QAE-04: seeded Aer [973, 3998, 1178, 1521] vs analytic [970, 3999, 1164, 1541] at k 0/1/2/8 x 4000 within 4 sqrt(2) sigma + 1 and each within 4 sigma + 1 of shots p_k; analytic scaling smoke slope -0.940; slow Aer slope -0.970 and Aer vs analytic RMSE within 8%"
    requirement: QAE-04
    verification:
      - kind: integration
        ref: "tests/test_runners.py#test_analytic_and_aer_agree"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_mlae_scaling_smoke"
        status: pass
      - kind: integration
        ref: "NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow tests/test_runners.py (2 passed)"
        status: pass
    human_judgment: false
  - id: D7
    description: "IonQ record schema v1, validation against tampering (19 mutations), loader file rules (missing, duplicate, non-list, oversize, invalid JSON, monkeypatched IONQ_RUNS_FILE) and IonQ-only estimate needing a sampled k = 0 record"
    requirement: QAE-02
    verification:
      - kind: unit
        ref: "tests/test_runners.py#test_record_validation_rejects_tampering"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_load_ionq_records_file_rules"
        status: pass
      - kind: unit
        ref: "tests/test_runners.py#test_ionq_estimate_needs_k0_and_skips_noisy"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 02: Vendored MLAE and Runners Summary

**A numpy-only maximum-likelihood amplitude estimator now matches qiskit-algorithms exactly on identical counts and reports cost only as N_A = Σ shots·(2k+1). Three runners (analytic, injected local backend, IonQ one-circuit) share `run(ks, shots)`. One Built-in-style list job gives a = 0.245094 ± 1.26e-3 at N_A = 18,000. Analytic and Aer agree hit-for-hit with the planner's numbers. The IonQ path sends one bare, IonQ-safe circuit and writes a validated record (schema v1).**

## Performance

- **Duration:** about 14 min
- **Started:** 2026-10-11T02:36:44Z
- **Completed:** 2026-10-11T02:50Z
- **Tasks:** 3 of 3
- **Files created:** 5 (no existing file modified)

## Key results

- **Tracer line (Task 1):** `MLAE TRACER OK hits=[262, 1000, 277, 997] a=0.245094 err=+2.09e-03 se=1.26e-03 N_A=18000`. This matches the planner's line exactly.
- **QAE-01 parity** (the Aer list job, ks [0, 1, 2, 4, 8] × 200 shots, seed 5, hits [40, 200, 70, 199, 80], plus 6 seeded single-qubit cases):

  | Check | Measured |
  |---|---|
  | `brute` over our likelihood vs qiskit `compute_mle`, worst \|Δθ\| | 0 (qiskit a = 0.2413897286) |
  | qiskit with our minimizer vs `mle_theta`, worst \|Δθ\| | 0 |
  | Vendored vs qiskit default minimizer, worst \|Δa\| | 3.16e-5 (Aer case 4.8e-6; vendored a = 0.2413849165, never lower likelihood) |

- **QAE-03 cost:** on ks [0, 1, 2, 4] × 100 shots, N_A = 1,800. qiskit-algorithms reports `num_oracle_queries = 700` on the same schedule.
- **QAE-04 hit lists** (k 0, 1, 2, 8 × 4000 shots, seed 404): Aer [973, 3998, 1178, 1521] and analytic [970, 3999, 1164, 1541]. Both equal the planner's measurements.
- **Scaling smoke** (analytic, `default_rng(2026 + M)`, 100 shots per power, R = 50):

  | M | N_A | MLAE RMSE | classical √(T1(1−T1)/N_A) |
  |---|---|---|---|
  | 3 | 900 | 8.07e-3 | 1.43e-2 |
  | 5 | 3,500 | 2.19e-3 | 7.25e-3 |
  | 7 | 13,300 | 6.43e-4 | 3.72e-3 |

  The fitted slope is −0.940 (accepted range −1.15 to −0.75).
- **Slow runs:**
  - `NEUTRON_QAE_SLOW=1 pytest -m slow tests/test_runners.py` gives `2 passed` in 64 s.
    - Aer scaling (R = 20): RMSE 7.65e-3, 2.30e-3, 5.61e-4 at N_A 900, 3,500, 13,300; slope −0.970.
    - Aer (R = 30) vs analytic (R = 400) RMSE: 7.90e-3 vs 7.83e-3 at N_A 900, and 2.37e-3 vs 2.19e-3 at N_A 3,500 (within 8%; the bound is 30%).
  - With `tests/test_grover.py` the slow set is 3 passed.
- **IonQ fake record** (Q1, k = 1, 200 shots): accepted, sampled, noise_model "ideal", hits 200. It has 1,503 CX, depth 2,533, size 3,013, max 1 control, body_bytes_est 168,728, n_A 600, and 12-character count keys. The IonQ-only estimate from fake k = 0, 1, 2 × 1000 (hits [260, 1000, 279]) is a = 0.245670, se = 2.30e-3, N_A = 9,000, z = +1.16.
- **Default suite:** 293 passed, 5 skipped in 21.8 s (22 s wall). Before this plan it was 243 passed and 3 skipped. `git status --porcelain` is the same before and after the run.
- **Gates:**
  - The MAIN GRAPH command prints `MAIN GRAPH UNCHANGED ['__init__.py', 'main.py', 'smoke.py']`.
  - `git ls-files data` lists only `data/smoke_probe.json`.
  - `foreign_imports(mlae.py)` is empty, and the compliance suite is green.
  - The frozen-file diff against `55b334d` is empty.
  - `freeze_kernels.py` prints `GOLDEN OK ... T1=0.24300446519524305`.
  - The Phase 1 tracer prints `TRACER OK`.

## Task Commits

1. **Task 1: Tracer.** A Built-in list job's flag hits go into the vendored MLAE, which returns an estimate with its Fisher se and N_A. Commit `886ef8e` (feat).
2. **Task 2: MLAE parity.** Parity with qiskit-algorithms, N_A vs num_oracle_queries, and the boundary, adjacency, empty, ordering and precision edges. Commit `b2570c7` (test).
3. **Task 3: Runners and IonQ records.** Runner interface, IonQ one-circuit runner and record schema, analytic vs Aer agreement, and the scaling smoke. Commit `318fadb` (test; it also adds the runner code to `runners.py`, as the plan's commit list specifies).

## Files Created

- `neutron_qae/mlae.py`: vendored MLAE (numpy + stdlib), `PowerResult`, `MLAEResult`, N_A, Fisher se and the schedules.
- `neutron_qae/runners.py`: the `Runner` protocol, `AnalyticRunner`, `BackendRunner`, `IonQRunner` and `hits_from_counts`, plus the IonQ record schema, validator, loader and IonQ-only estimate.
- `tests/ionq_fakes.py`: the `FakeIonQSimulator` test double.
- `tests/test_mlae.py`: 15 tests for QAE-01, QAE-03 and the probe edges.
- `tests/test_runners.py`: 35 default tests and 2 slow ones for QAE-02, QAE-04, the IonQ runner, record validation and the scaling smoke.

## Decisions Made

PD-17, PD-18 and PD-20 are implemented as written (see `key-decisions`). Implementation choices within the plan:

- `loglikelihood` adds terms one k at a time in qiskit-algorithms' order (`h log sin^2` then `(n − h) log cos^2`). The brute-force parity is therefore bit-exact, and memory stays O(grid).
- `hits_from_counts` accepts integral floats (for example `2.0`) as counts and rejects 1.5, bools and strings. qiskit-ionq builds noise-model counts from probabilities, so a float that is a whole number must not break parsing.
- On failure, the IonQ record keeps `counts = {}`, `hits = None` and `p_flag = None`. A failed `set_options` returns `accepted: False` without submitting.
- The record's `noise_model` is read from `backend.options` after the ideal-mode step and stored as a string (or None). `sampled` is true exactly when it reads `"ideal"`.
- `IonQRunner.run` also accepts `shots` as a one-element list, to fit the `Runner` signature.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Stricter IonQ record validation**
- **Found during:** Task 3 (`validate_ionq_record`)
- **Issue:** The plan's rule list does not require every schema key to be present. It also does not tie `p_flag` or `layout` to the rest of the record. A hand-pasted record could therefore lack fields that 04-04's evidence reads, or carry a `p_flag` that disagrees with its counts.
- **Fix:** The validator requires every key in `RECORD_KEYS`, checks that `layout` matches `MODEL_LAYOUT[model]`, that `p_flag == hits / shots`, that `ideal_mode` is in `IONQ_IDEAL_MODES` and that `timestamp` is a non-empty string. `RECORD_KEYS` is exported. The tampering test covers these cases too (19 mutations).
- **Files modified:** neutron_qae/runners.py, tests/test_runners.py
- **Committed in:** 318fadb

**2. [Rule 2 - Missing critical] Extra guard tests**
- **Found during:** Task 3
- **Fix:** Added tests for:
  - `BackendRunner(measure="all")`: flag at key index 0.
  - The `set_options` failure path: no job is sent and the record is `accepted: False`.
  - A noisy record that validates but is unsampled.
  - Invalid-JSON loading.
  - `MLAEResult.as_dict()` JSON round trip (in test_mlae).
- **Committed in:** b2570c7, 318fadb

**3. [Rule 3 - Blocking, lint] `# noqa: TRY004` on the ValueError raises the plan mandates for type errors**
- **Issue:** ruff flags `ValueError` for invalid types (TRY004). The plan requires `ValueError` for bools, non-integers and malformed untrusted input.
- **Fix:** Added targeted `noqa` comments. `ruff check neutron_qae/mlae.py neutron_qae/runners.py` passes.

---

**Total deviations:** 3 auto-fixed (2 missing-critical, 1 lint). **Impact:** stricter validation and more coverage. No interface changes, no scope creep.

## Issues Encountered

None. Every planner-measured number reproduced exactly: tracer hits, QAE-04 hit lists, the parity Aer hits, the scaling RMSEs and the slope.

## Handoff for 04-03 (main.py and ingest)

- **Built-in path:** `BackendRunner(backend, problem).run(list(BUILTIN_SCHEDULE), shots)`, then `mlae.estimate(records)`. Print `a_hat`, `a_hat − problem.reference`, `se` and `n_A`, or `MLAEResult.as_dict()`. Passing an IonQ backend to it raises ValueError.
- **IonQ path:** `IonQRunner(backend, problem, ideal_mode).run_point(k, shots)` returns the record dict to print after `IONQ_RECORD=`, for example with `json.dumps(record)`. Keys are in `runners.RECORD_KEYS` order.
  - Clamps: k 0..8, shots 2..10,000, `ideal_mode` in ("none", "set_options"); "kwarg" is refused.
  - A failed submission returns `accepted: False` with `error`; it never raises and never retries.
- **Stored records:** `load_ionq_records()` and `ionq_estimate()` read `runners.IONQ_RUNS_FILE` at call time.
  - A missing file gives `[]` and `None`.
  - When main.py starts importing runners, 04-03 must create `data/ionq_runs.json`. The literal path already appears in runners.py, so the data-file compliance gate will pass.
- **Test double:** `tests/ionq_fakes.FakeIonQSimulator(fail=None)` is the shared IonQ fake, with a `calls` list. Use `set_options(seed_simulator=...)` for reproducible counts.
- **Import graph:** runners.py imports `numpy`, `qiskit` (through grover and oracle) and `neutron_qae` only. It does not import qiskit_aer, qiskit_algorithms or qiskit_ionq; the `qiskit_ionq` version is read from `sys.modules`.

## Handoff for Phase 5 (ANLY-01 sweeps)

- **AnalyticRunner draw order:** one `rng.binomial(int(shots_i), sin^2((2k_i+1) theta))` per k, in input order, with theta = asin √p. Construct it as `AnalyticRunner(problem.p, np.random.default_rng(seed))` so the emulator uses the circuit's contract-checked p.
- **Schedules:** `exponential_schedule(M)` is the headline schedule and `linear_schedule(M)` the comparison.
- **Cost axis:** always `MLAEResult.n_A` (= `n_applications(records)`), never shots or `num_oracle_queries`.
- **Error bar:** `MLAEResult.se` is the asymptotic Fisher se. It is zero at a ∈ {0, 1}.
- **Evidence the analytic emulator stands in for Aer:**
  - The four seeded points match hit for hit within 4σ.
  - Aer and analytic RMSE agree within 8% at N_A 900 and 3,500.
  - The Aer slope is −0.970 and the analytic slope −0.940.
  - Use R ≥ 50 per point (ANLY-01).

## User Setup Required

None. No external service configuration is required.

## Next Phase Readiness

- 04-03 can wire `BackendRunner` (Built-in) and `IonQRunner` (IonQ) into main.py.
- 04-04's Qollab IonQ runs produce records that `load_ionq_records` validates and `ionq_estimate` turns into an IonQ-only estimate. That needs a sampled k = 0 record, and the planned protocol supplies k = 0, 1, 2.
- No blockers.

---
*Phase: 04-quantum-oracle-amplitude-estimation*
*Completed: 2026-10-11*

## Self-Check: PASSED

All 5 created files and the SUMMARY exist; commits 886ef8e, b2570c7 and 318fadb are ancestors of HEAD.
