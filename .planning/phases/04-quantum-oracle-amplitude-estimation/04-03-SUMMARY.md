---
phase: 04-quantum-oracle-amplitude-estimation
plan: 03
subsystem: quantum
tags: [qollab, main-entry, amplitude-estimation, mlae, ionq, basic-simulator, ingest, docs, upload-bundle]

# Dependency graph
requires:
  - phase: 04-quantum-oracle-amplitude-estimation (04-01)
    provides: "make_problem / OracleProblem (contract gate), resource_table / format_resource_table, check_ionq_safe, MODELS"
  - phase: 04-quantum-oracle-amplitude-estimation (04-02)
    provides: "mlae.estimate, BackendRunner, IonQRunner.run_point, validate_ionq_record, load_ionq_records, ionq_estimate, IONQ_RUNS_FILE, tests/ionq_fakes.FakeIonQSimulator"
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "smoke.py (run_toy, perf_probe, runtime/backend reports, is_ionq), compliance gates, the git-archive bundle audit"
provides:
  - "main.py: def main(mode: str = \"qae\", k: int = 1, shots: int = 1000, ideal_mode: str = \"set_options\", model: str = \"Q1\") with PD-23 validation; Built-in live MLAE over (0, 1, 2, 4) -> QAE_REPORT= / QAE RUN COMPLETED; IonQ one bare circuit -> IONQ_RECORD= / IONQ RUN ACCEPTED|FAILED; mode=smoke = Phase 1 path"
  - "data/ionq_runs.json (empty JSON list, main-reachable through runners.IONQ_RUNS_FILE)"
  - "scripts/ingest_ionq_records.py PASTE [--out PATH] [--allow-fake]: verbatim, validated, idempotent, atomic paste -> records"
  - "scripts/run_local.py --backend basic|aer|fake-ionq --mode --k --shots --ideal-mode --model --seed"
  - "scripts/qae_local.py resources | aer-mlae | analytic"
  - "docs/QUANTUM.md (layout, contract, resource table, transpile-once, MLAE, N_A, runners, IonQ protocol, IonQ results, evidence limits) and the Phase 4 README"
  - "~/Desktop/qollab-phase4.zip: the audited 19-file upload bundle for 04-04"
affects: [04-04, phase-5, phase-6, docs-03, docs-05]

# Actuals (#2632)
actuals:
  tokens: 14796       # chars/4 over the added lines of the 12 changed files (59,187 chars)
  tasks: 3
  commits: 4
plan_head_before: f477185bf11ebfdc3edaabf6ccf44ef64b5a37df
plan_head_after: 7b094c75b1f537dd43efda2f750c8662f0db76b1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Qollab entry dispatches on is_ionq(backend): Built-in = one list job + live MLAE; IonQ = exactly one IonQRunner.run_point per main() call"
    - "Form values are validated (ValueError) before make_problem and before any job; never clamped; integral floats accepted, bools rejected"
    - "Machine-readable console lines (QAE_REPORT=, IONQ_RECORD=) plus a terminal status line are the evidence contract; ingest scripts parse the verbatim paste"
    - "Docs that quote code output (resource table) are checked against the code by a test"

key-files:
  created:
    - data/ionq_runs.json
    - scripts/ingest_ionq_records.py
    - scripts/qae_local.py
    - docs/QUANTUM.md
    - tests/test_main_qae.py
    - tests/test_ingest_ionq_records.py
    - tests/test_ionq_records.py
    - tests/test_quantum_doc.py
  modified:
    - main.py
    - scripts/run_local.py
    - tests/test_smoke.py
    - README.md

key-decisions:
  - "PD-19 (locked, orchestrator; costly): interim entry signature def main(mode: str = \"qae\", k: int = 1, shots: int = 1000, ideal_mode: str = \"set_options\", model: str = \"Q1\"): on one line with literal defaults. mode=smoke keeps the Phase 1 path (GHZ 6 qubits, perf 12 qubits fixed). On IonQ: one IonQRunner.run_point(k, shots), one IONQ_RECORD= line (compact sorted JSON), js.sendFile of the same JSON, IONQ RUN ACCEPTED or IONQ RUN FAILED. On any other backend: live MLAE through BackendRunner over BUILTIN_SCHEDULE = (0, 1, 2, 4) in one list job, QAE_REPORT=, the IonQ-only estimate from data/ionq_runs.json, QAE RUN COMPLETED; k and ideal_mode do not affect the Built-in run (stated in the output and the README)."
  - "PD-21 (locked): size ladder k = 0 (31 KB), k = 1 (169 KB), k = 2 (306 KB) for Q1; on 'Circuit size is too large' re-run that k with model=Q1lite (57 KB at k = 1, 103 KB at k = 2); every record carries body_bytes_est."
  - "PD-23 (locked): form values validated before any job, never clamped: mode in {qae, smoke}; model in {Q0, Q1, Q1lite}; k integer 0..8; shots integer 2..10,000; ideal_mode in {none, set_options} for qae (kwarg refused: round(p shots) counts) and in smoke.IDEAL_MODES for smoke; bools and non-integral numbers rejected; integral floats accepted. k and model are validated in smoke mode too (the form always sends them)."
  - "Open Question 2 resolved: Phase 4 owns the QAE mode of main.py; Phase 6 extends it with precomputed figures."
  - "The Phase 1 tracer command is now scripts/run_local.py --mode smoke; plain scripts/run_local.py runs the QAE mode with main()'s defaults, mirroring an untouched Qollab form."
  - "On the Built-in path the IonQ-only estimate is compared with T1 (Q1 and Q1lite records), even when the Built-in model is Q0; QAE_REPORT also carries the model's own exact reference."

patterns-established:
  - "One main() call on IonQ = one job = one bare circuit; the Built-in list job is never built on an IonQ backend"
  - "Records path: Qollab console -> verbatim paste file -> scripts/ingest_ionq_records.py -> data/ionq_runs.json (validated on ingest and again on every load); tests never write the repo records file"
  - "A corrupt or invalid records file is reported on the Built-in path (IonQ records: invalid (...)) and never stops the judged run"

requirements-completed: [QAE-02, QC-05, QC-06]

coverage:
  - id: D1
    description: "Tracer: BasicSimulator (seed 2026) injected like Qollab -> main() defaults -> contract gate -> one list job over k = 0, 1, 2, 4 -> MLAE: QAE_REPORT with hits [262, 1000, 277, 997], a_hat 0.245094, N_A 18000, abs_diff 3.5e-15, ends QAE RUN COMPLETED"
    requirement: QAE-02
    verification:
      - kind: e2e
        ref: "scripts/run_local.py --seed 2026 | Task 1 checker -> QAE TRACER OK a=0.245094 N_A=18000 hits=[262, 1000, 277, 997]"
        status: pass
      - kind: integration
        ref: "tests/test_main_qae.py#test_main_qae_builtin_seeded"
        status: pass
    human_judgment: false
  - id: D2
    description: "PD-19 signature on one line; main.py never calls main() or assigns backend; compliance gates green"
    requirement: QAE-02
    verification:
      - kind: unit
        ref: "tests/test_main_qae.py#test_main_signature_is_the_phase4_form"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_main_signature_is_qollab_form_compatible"
        status: pass
    human_judgment: false
  - id: D3
    description: "IonQ path: one main() call sends exactly one bare 12-qubit IonQ-safe circuit and prints one validated IONQ_RECORD (Q1, k 1, 200 shots, n_A 600, cx 1503, sampled) then IONQ RUN ACCEPTED; noisy (ideal_mode none) records are unsampled; k = 0 prints the single-record estimate; Q1lite record has 8-bit keys and 399 CX"
    requirement: QC-06
    verification:
      - kind: integration
        ref: "tests/test_main_qae.py#test_main_qae_ionq_sends_one_bare_circuit"
        status: pass
      - kind: integration
        ref: "tests/test_main_qae.py#test_ionq_noisy_record_is_unsampled"
        status: pass
      - kind: integration
        ref: "tests/test_main_qae.py#test_ionq_k0_prints_single_record_estimate"
        status: pass
      - kind: integration
        ref: "tests/test_main_qae.py#test_ionq_q1lite_record"
        status: pass
    human_judgment: false
  - id: D4
    description: "PD-23: 19 invalid form-value cases raise ValueError with no job sent; integral floats (k = 1.0, shots = 100.0) accepted; a failed IonQ submission is printed once as IONQ RUN FAILED with accepted false and no retry"
    requirement: QAE-02
    verification:
      - kind: unit
        ref: "tests/test_main_qae.py#test_invalid_form_values_send_no_job (19 cases)"
        status: pass
      - kind: unit
        ref: "tests/test_main_qae.py#test_integral_float_form_values_are_accepted"
        status: pass
      - kind: unit
        ref: "tests/test_main_qae.py#test_failed_ionq_submission_is_reported"
        status: pass
    human_judgment: false
  - id: D5
    description: "Smoke mode kept: scripts/run_local.py --mode smoke passes the Phase 1 checker (TRACER OK); tests/test_smoke.py passes with mode=smoke (6-qubit GHZ keys, perf probe 12 qubits, IonQ fake one bare circuit)"
    verification:
      - kind: e2e
        ref: "scripts/run_local.py --mode smoke | Phase 1 checker -> TRACER OK"
        status: pass
      - kind: integration
        ref: "tests/test_smoke.py (4 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Records on the Built-in path and data gate: fake k 0, 1, 2 records give the IonQ-only estimate with N_A 9000; empty file prints 'IonQ records: none yet'; corrupt file prints 'IonQ records: invalid (' and still completes; data/ionq_runs.json committed as [] and passes the literal-path and size gates"
    requirement: QAE-02
    verification:
      - kind: integration
        ref: "tests/test_main_qae.py#test_builtin_prints_ionq_estimate_when_records_exist"
        status: pass
      - kind: integration
        ref: "tests/test_main_qae.py#test_builtin_survives_corrupt_records_file"
        status: pass
      - kind: unit
        ref: "tests/test_ionq_records.py#test_committed_ionq_records_file_is_valid"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_every_data_file_is_referenced_by_literal_path"
        status: pass
    human_judgment: false
  - id: D7
    description: "Ingest script: verbatim storage, failed attempts listed not stored, idempotent re-ingest, malformed/tampered/conflicting input rejected with the file untouched, real qiskit-ionq backend required, --allow-fake never writes the repo file"
    requirement: QAE-02
    verification:
      - kind: integration
        ref: "tests/test_ingest_ionq_records.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D8
    description: "QC-05 docs: docs/QUANTUM.md holds the exact format_resource_table(resource_table()) text (Q0, Q1, Q1lite at k = 0, 1, 2, all <= 12 qubits) plus layout, contract, transpile-once, MLAE, N_A, runners and IonQ protocol; README documents the five Run settings fields and outputs and keeps attribution and disclosure"
    requirement: QC-05
    verification:
      - kind: unit
        ref: "tests/test_quantum_doc.py (6 tests)"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py, tests/test_physics_doc.py"
        status: pass
    human_judgment: false
  - id: D9
    description: "No speedup or quantum-advantage claim in README, docs/QUANTUM.md or console output; IonQ framed as execution proof plus three-power estimate"
    verification: []
    human_judgment: true
    rationale: "Honest-framing prohibition is verification: judgment in the plan; wording needs a human read"
  - id: D10
    description: "Bundle: git archive of HEAD 7b094c7 = exactly the 19 expected files, no secret-shaped strings, no IonQProvider; MAIN GRAPH OK with the 11 Pyodide-safe modules"
    verification:
      - kind: other
        ref: "Task 3 bundle audit -> BUNDLE OK 19 (sha256 75e15e911429d6563b6eb5e0568d25b43eb0b86fef7212838cc9dae5e65d4d22, 51,698 bytes)"
        status: pass
      - kind: other
        ref: "Task 3 MAIN GRAPH command -> MAIN GRAPH OK"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 03: Qollab QAE Entry, IonQ Protocol and Phase 4 Docs Summary

**`main.py` now runs QAE on whatever backend Qollab injects.**
- **Built-in simulator:** one job of four contract-gated Q1 circuits (k = 0, 1, 2, 4) feeds the vendored MLAE. The run prints a = 0.245094 at N_A = 18,000 and the IonQ-only estimate from `data/ionq_runs.json`.
- **IonQ:** exactly one bare A·Q^k circuit is sent per run, and the run prints a validated `IONQ_RECORD=`.
- **Smoke mode:** `mode=smoke` keeps the Phase 1 test.

A verbatim ingest script, `docs/QUANTUM.md` (with its resource table checked against the code) and an audited 19-file bundle complete the handoff to 04-04.

## Performance

- **Duration:** about 14 min
- **Started:** 2026-10-11T04:15:59Z
- **Completed:** 2026-10-11T04:30Z
- **Tasks:** 3 of 3
- **Files:** 12 (8 created, 4 modified)

## Key results

- **QAE tracer:** `QAE TRACER OK a=0.245094 N_A=18000 hits=[262, 1000, 277, 997]`. The Built-in run's `wall_clock_s` is 0.944 natively. The contract check gives |d| = 3.5e-15.
- **Phase 1 tracer** (`scripts/run_local.py --mode smoke`): `TRACER OK`.
- **Default suite:** 335 passed, 6 skipped in 26.6 s (27 s wall, under the 30 s cap). Before this plan it was 293 passed, 5 skipped. `git status --porcelain` is identical before and after the run, and `git diff --quiet HEAD -- data/ionq_runs.json` holds.
- **Plan-level tests:**
  - The 3 test files give 36 passed and exactly 1 skipped: `test_ionq_only_estimate_within_4_sigma`, while the records file is empty.
  - `NEUTRON_QAE_SLOW=1 pytest -q -m slow`: 5 passed, 336 deselected in 89 s.
- **Main graph:** `MAIN GRAPH OK ['__init__.py', 'exact.py', 'grover.py', 'kernels.py', 'main.py', 'mlae.py', 'nuclear_data.py', 'oracle.py', 'problem.py', 'runners.py', 'smoke.py']`. No forbidden imports.
- **Bundle:** `BUNDLE OK 19`.
  - File: `~/Desktop/qollab-phase4.zip`, 51,698 bytes, built from HEAD `7b094c7`.
  - sha256: `75e15e911429d6563b6eb5e0568d25b43eb0b86fef7212838cc9dae5e65d4d22`
- **Other gates:**
  - The frozen-file diff against `55b334d` is empty.
  - `freeze_kernels.py` prints `GOLDEN OK kernels_v1.json T1=0.24300446519524305`.
  - README is 13,077 characters and keeps the attribution line.
- **Fake-IonQ form runs** (`run_local.py --backend fake-ionq`, 1000 shots, ideal):

  | Run | Measured P(flag) | Expected P(flag) | CX | Estimated request |
  |---|---|---|---|---|
  | Q1, k = 0 | 0.2600 | 0.2430 | 313 | 31 KB |
  | Q1, k = 1 | 1.0000 | 0.9994 | 1,503 | 169 KB |
  | Q1, k = 2 | 0.2790 | 0.2859 | 2,693 | 306 KB |
  | Q1lite, k = 1 | 1.0000 | 0.9994 | 399 | 56 KB |
- **Local QAE tool:**
  - `scripts/qae_local.py aer-mlae --M 5 --shots 100 --seed 1` gives a = 0.243564, |a − T1| = 5.6e-4, se = 2.13e-3, N_A = 3,500.
  - `analytic --M 5 --shots 100 --reps 50 --seed 2026` gives RMSE 2.09e-3 against the classical 7.25e-3 at N_A = 3,500.

## Task Commits

1. **Task 1: Tracer.** main() QAE mode on the injected backend (Built-in live MLAE, IonQ one circuit with `IONQ_RECORD=`), smoke mode kept, `data/ionq_runs.json`, `run_local.py` options. Commit `26a9f14` (feat).
2. **Task 2: IonQ protocol hardening.** Ingest script, records tests and protocol-edge tests. Commit `5e5a614` (test).
3. **Suite-time fix** (deviation 3). The Built-in record-file tests now run on Q0. Commit `041bf5a` (test).
4. **Task 3: Docs and local tool.** README, `docs/QUANTUM.md`, `scripts/qae_local.py`, `tests/test_quantum_doc.py`. Commit `7b094c7` (docs). The bundle was then built from this HEAD.

## Files Created/Modified

- `main.py`: Qollab entry.
  - `MODES`, `BUILTIN_SCHEDULE`, `_as_int`, `_check_inputs`, `_run_smoke`, `_run_qae_builtin`, `_run_qae_ionq`.
  - It never assigns `backend` and never calls `main()`.
- `data/ionq_runs.json`: `[]` plus a newline. Plan 04-04 fills it.
- `scripts/run_local.py`: `--backend basic|aer|fake-ionq`, `--mode`, `--k`, `--shots`, `--ideal-mode`, `--model`, `--seed`. Only the options given are passed to main().
- `scripts/ingest_ionq_records.py`: paste to validated records, verbatim, idempotent and atomic (temp file plus `os.replace`). It prints `INGESTED ...` and `IONQ ESTIMATE ...`.
- `scripts/qae_local.py`: `resources`, `aer-mlae`, `analytic`.
- `docs/QUANTUM.md`: the 11 sections the plan specifies.
- `README.md`:
  - Phase 3 and Phase 4 status.
  - The five Run settings fields with their ranges, and the Built-in and IonQ outputs.
  - Local commands, the updated layout, and a new `## Quantum oracle and amplitude estimation` section.
- `tests/test_main_qae.py` (29 tests), `tests/test_ingest_ionq_records.py` (6), `tests/test_ionq_records.py` (2), `tests/test_quantum_doc.py` (6).
- `tests/test_smoke.py`: re-pointed at `mode="smoke"`, with 6-qubit GHZ keys.

## Decisions Made

PD-19, PD-21 and PD-23 are implemented as written (see `key-decisions`). Open Question 2 is resolved. Choices within the plan:

- **Smoke mode validation.** It validates `k` and `model` too, because the Qollab form always sends them, and it accepts `kwarg` as `ideal_mode` (Phase 1 behaviour).
- **`QAE_REPORT` keys.** It also carries `reference` (the model's exact T_K). The IonQ summary dict carries `models` (the sampled record models used), `ks`, `shots` and `hits`.
- **`IONQ RUN FAILED` line.** It prints `record["error"]`, which already starts with the exception class (for example `RuntimeError: Circuit size is too large ...`).
- **Ingest script edge cases.**
  - It also deduplicates within a single paste.
  - It creates the output file when it does not exist, even with 0 records.
  - It leaves an existing file untouched when nothing new is added, which keeps re-ingest byte-identical.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IonQ-only error is measured against T1, not the Built-in model's reference**
- **Found during:** Task 1 (`_run_qae_builtin`)
- **Issue:** The plan says the IonQ summary's `abs_err` is "vs problem.reference". IonQ records are Q1 or Q1lite, whose flag probability is T1. With `model="Q0"` on the Built-in path, `problem.reference` is T0 = 0.2326, so the printed IonQ error would have been wrong by about 0.01.
- **Fix:** t1 is `problem.reference` when K = 1, otherwise `exact.transmission_within(problem.kernels, 1)`. `test_builtin_prints_ionq_estimate_when_records_exist` runs the Built-in path on Q0 and asserts that the error is computed against T1.
- **Files modified:** main.py, tests/test_main_qae.py
- **Committed in:** 26a9f14, 041bf5a

**2. [Rule 2 - Missing critical] Wider PD-23 coverage**
- **Found during:** Task 2
- **Fix:** The plan listed 9 invalid inputs. `test_invalid_form_values_send_no_job` covers 19:
  - the plan's 9;
  - non-string choices (`mode=1`, `ideal_mode=None`), case (`model="q1"`), `k="1"`, `k=None`, `shots=False`, `shots=100.5` and `ideal_mode="bogus"`;
  - smoke-mode invalid `ideal_mode` and `shots`.

  The integral-float acceptance became its own test, which also asserts the values are stored as `int`.
- **Committed in:** 5e5a614

**3. [Rule 3 - Blocking] Default suite near the 30 s cap**
- **Found during:** Task 3 (after adding `tests/test_quantum_doc.py`)
- **Issue:** The full suite measured 27.1 s, against a 30 s acceptance bound, with the two corrupt-file and records Built-in tests transpiling Q1 up to k = 4.
- **Fix:** Those two tests now run the Built-in path on `model="Q0"`. That does not change what they check, and it adds coverage of the T1 path from deviation 1. This saves about 1.2 s. The change is an extra commit not listed in the plan.
- **Committed in:** 041bf5a

**4. [Rule 3 - Lint] `# noqa: TRY004` on main.py's type-check ValueError**
- PD-23 mandates ValueError for non-numeric form values. `ruff check` passes on every new or changed file except the line listed under Issues.

---

**Total deviations:** 4 auto-fixed (1 bug, 1 missing-critical, 2 blocking/lint). **Impact:** a correct IonQ error on non-Q1 Built-in runs and stronger input coverage. No interface change and no scope creep. The PD-19 signature is exactly as planned.

## Issues Encountered

- **Pre-existing lint in `tests/test_smoke.py`.** `ruff check tests/test_smoke.py` reports TRY004 on the Phase 1 inline fake's `raise RuntimeError(...)`. The line is unchanged since Phase 1, so it is out of scope and logged in `deferred-items.md`.
- **Q1lite request size.** `docs/QUANTUM.md` and PD-21 quote 57 KB and 103 KB for Q1lite at k = 1 and 2. Those are the research measurements with qiskit-ionq's serializer. The record's `body_bytes_est` (56 bytes per gate) reads 56 KB and 102 KB. Both are estimates, and 04-04's accepted or rejected runs bracket the real limit.
- **Suite time.** The default suite stays at about 27 s, so there is roughly 3 s of headroom under the 30 s cap. The 6 ingest tests spend about 5 s in subprocesses (about 0.5 s each for Python and qiskit import). Phase 5 or 6 additions should be budgeted against this.

## Handoff for 04-04 (Qollab runs)

**Upload.** Upload `~/Desktop/qollab-phase4.zip` (sha256 `75e15e91…4d22`, 19 files). The Run settings form should show five fields: Mode, K, Shots, Ideal Mode, Model.

**R0, Built-in simulator** (logged out, or the incognito check):
- Form values: defaults, that is `mode=qae, k=1, shots=1000, ideal_mode=set_options, model=Q1`.
- Expect `contract: ... (|d| = 3.5e-15 ...)`, one `QAE_REPORT=` line, an `MLAE a_hat=...` line, `IonQ records: none yet ...` and `QAE RUN COMPLETED`.
- **R0 is the first evidence for assumption A-P1.** It shows whether qiskit 2.5.2 in Pyodide synthesizes StatePreparation, UCRY and the mcx into the basis and runs Statevector in the browser. Record `wall_clock_s` (0.94 s natively). If R0 fails, stop with the traceback; the gap-closure plan ships pre-transpiled circuits.

**R1-R3, IonQ Forte 1** (signed in):
- R1: `mode=qae, k=0, shots=1000, ideal_mode=set_options, model=Q1` (31 KB).
- R2: the same with `k=1` (169 KB).
- R3: the same with `k=2` (306 KB).
- On `IONQ RUN FAILED: ... Circuit size is too large ...`, re-run that k with `model=Q1lite`.

**Optional honest-noise runs:** `k=0` and `k=1` with `ideal_mode=none`. They are kept as `sampled: false`, reported, and excluded from the MLAE.

**Ingest:**
1. Save the console output verbatim to a file and run `.venv/bin/python scripts/ingest_ionq_records.py <paste-file>`. Expect `INGESTED n new, ...` and `IONQ ESTIMATE a=... N_A=9000 ks=[0, 1, 2]` for the three ideal 1000-shot runs.
2. Commit `data/ionq_runs.json`.

**After ingest:**
- `tests/test_ionq_only_estimate_within_4_sigma` stops skipping and must pass.
- `tests/test_quantum_doc.py::test_ionq_results_section_matches_records_state` **fails until** the `## IonQ results` section of `docs/QUANTUM.md` no longer says `No IonQ records yet`. Replace that sentence with the measured results in the same commit.
- Rebuild and re-upload the bundle (same audit command, still 19 files) so logged-out Built-in runs show the IonQ estimate.

## User Setup Required

None. No external service configuration is required (04-04 holds the human Qollab steps).

## Next Phase Readiness

- 04-04 can upload the audited bundle and run R0 to R3 on Qollab tonight, and the ingest path is tested end to end on fake records.
- Phase 6 extends `main()` (PD-19 notes that changing parameter names or order is costly).
- No blockers. Assumption A-P1 (Pyodide synthesis) is still unverified until R0.

---
*Phase: 04-quantum-oracle-amplitude-estimation*
*Completed: 2026-10-11*

## Self-Check: PASSED

All 12 plan files exist. Commits 26a9f14, 5e5a614, 041bf5a and 7b094c7 are ancestors of HEAD. Every acceptance criterion and plan-level verification command was re-run and passed (results above). `~/Desktop/qollab-phase4.zip` exists with the recorded sha256.
