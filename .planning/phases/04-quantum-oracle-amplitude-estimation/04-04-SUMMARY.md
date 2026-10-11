---
phase: 04-quantum-oracle-amplitude-estimation
plan: 04
subsystem: quantum
tags: [qollab, ionq, forte-1, amplitude-estimation, mlae, pyodide, evidence, human-gate]

# Dependency graph
requires:
  - phase: 04-quantum-oracle-amplitude-estimation (04-03)
    provides: "main() QAE mode (Built-in live MLAE, IonQ one circuit per Run with IONQ_RECORD=), scripts/ingest_ionq_records.py, scripts/run_local.py --backend fake-ionq, the 19-file bundle audit, docs/QUANTUM.md"
  - phase: 04-quantum-oracle-amplitude-estimation (04-02)
    provides: "validate_ionq_record, load_ionq_records, ionq_estimate, mlae.estimate, the neutron_qae.ionq_record v1 schema"
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "Qollab upload-and-run runbook, set_options(noise_model='ideal') finding, docs/QOLLAB-RUNTIME.md"
provides:
  - "data/ionq_runs.json: 3 real IonQ Forte 1 records from Qollab (Q1, k = 0, 1, 2, 1000 shots, ideal, sampled), ingested verbatim by script"
  - "docs/QOLLAB-RUNTIME.md ## Phase 4 IonQ runs (2026-10-11): run table, verbatim console lines, size ladder, timings, A-P1 result, IonQ-only estimate, deviation analysis"
  - "docs/QUANTUM.md ## IonQ results and the README Phase 4 IonQ paragraph (execution proof plus a three-power estimate, 6.4 sigma miss stated, no speedup claim)"
  - "tests/test_quantum_doc.py::test_ionq_records_in_docs_match_data (docs and data record sets equal)"
  - "tests/test_ionq_records.py: strict xfail keyed to KNOWN_4SIGMA_MISS plus test_known_4sigma_miss_matches_data"
  - "~/Desktop/qollab-phase4.zip rebuilt from 8350ae9 (55,182 B, BUNDLE OK 19) for the Phase 6 re-upload"
affects: [phase-5, phase-6, docs-02, docs-03, docs-05]

# Actuals (#2632)
actuals:
  tokens: 13671       # chars/4 over the added lines of the 7 changed files (54,685 chars, 2d416f8..8350ae9)
  tasks: 3
  commits: 1          # measured: git rev-list --count 2d416f8..HEAD at SUMMARY time (Task 1 changed no tracked file; Task 2 was a human action)
plan_head_before: 2d416f8b4ebfb356a3b25e925f0f3f23cf003b0d
plan_head_after: 8350ae9e27a8b440d845b167001e8e8988aa2604

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Human-run Qollab evidence: verbatim paste file -> ingest script (no --allow-fake) -> committed records -> docs quote the lines -> a test ties docs to data"
    - "A measured miss is kept visible with a strict xfail keyed to the exact record set (never a loosened tolerance); any data change switches the xfail off"
    - "Tests that read committed evidence follow the records state instead of assuming an empty file"

key-files:
  created: []
  modified:
    - data/ionq_runs.json
    - docs/QOLLAB-RUNTIME.md
    - docs/QUANTUM.md
    - README.md
    - tests/test_quantum_doc.py
    - tests/test_ionq_records.py
    - tests/test_main_qae.py

key-decisions:
  - "PD-22 resolved: the phase's single human gate ran. Hippolyte (signed in, Chrome) replaced the Draft project's files with the 2d416f8 bundle and ran R0 (Built-in) then IonQ Forte 1 k = 1, 0, 2. R4/R5 (noisy) were not run; nothing was published."
  - "IonQ execution proof accepted with a documented discrepancy (Hippolyte, verbatim `accept (a)`): the Q1 A·Q^k circuit runs on Qollab's IonQ Forte 1 simulator and mlae.estimate accepts the counts (SC4 Qollab half met), but the IonQ-only estimate misses the 4-sigma check (a = 0.228671, z = -6.38, N_A = 9000). The QAE-01 IonQ-accuracy truth is NOT MET; the cause is open."
  - "One circuit per Run protocol validated end to end on Qollab IonQ Forte 1: three Runs, three jobs, three accepted records, each passing validate_ionq_record with backend_class qiskit_ionq.ionq_backend.IonQSimulatorBackend."
  - "Qollab's request-body limit is above 307 KB: every body up to 306,656 B (Q1, k = 2) was accepted, so no size rejection occurred and Q1lite was never needed. Only the lower bound is known."
  - "A-P1 confirmed: Pyodide builds, transpiles and runs the Q1 QAE in the browser (R0 wall_clock_s 1.412, a_hat 0.242072 at N_A 18000). No pre-transpiled circuit file is needed."
  - "The 4-sigma assertion is kept unchanged; a strict xfail keyed to KNOWN_4SIGMA_MISS (the exact (timestamp, model, k, shots, hits) set) reports the miss and becomes a plain assertion if any record changes."
  - "IonQ records are a labelled execution proof, never a scaling data point (Phase 5); any display of the IonQ-only estimate needs a one-line caveat (Phase 6)."

patterns-established:
  - "Evidence fidelity: every committed IonQ record is the parsed form of a pasted IONQ_RECORD= line, and test_ionq_records_in_docs_match_data keeps docs and data identical"
  - "Findings that contradict the plan's expected numbers are surfaced to the human as a checkpoint before committing data, and recorded with the measured statistic"

requirements-completed: [QAE-01, QAE-02, QC-06]

coverage:
  - id: D1
    description: "Pre-flight tracer: bundle from 2d416f8 audited (BUNDLE OK 19, 51,698 B, sha256 071f1c57...1c45); fake-IonQ dry run of the exact form values (k = 0, 1, 2, 1000 shots, set_options) -> INGESTED 3 new, IONQ ESTIMATE a=0.245670 z=+1.16 N_A=9000; Built-in QAE TRACER OK; repo records file untouched"
    requirement: QAE-02
    verification:
      - kind: other
        ref: "Task 1 verify commands 1-3 (bundle audit, fake-IonQ dry run + ingest --allow-fake --out tmp, QAE tracer)"
        status: pass
    human_judgment: false
  - id: D2
    description: "R0 (A-P1): Qollab Built-in simulator (Pyodide) ran main() defaults: contract |d| = 3.3e-15, schedule [0, 1, 2, 4], hits [229, 1000, 304, 994], a_hat 0.242072 +- 1.26e-3, N_A 18000, wall_clock_s 1.412, QAE RUN COMPLETED"
    requirement: QAE-02
    verification:
      - kind: manual_procedural
        ref: "Hippolyte's R0 paste (QAE_REPORT= line quoted verbatim in docs/QOLLAB-RUNTIME.md ## Phase 4 IonQ runs)"
        status: pass
    human_judgment: true
    rationale: "Evidence is a human-run browser session on Qollab; no automated test can re-run the Pyodide path"
  - id: D3
    description: "ROADMAP SC4 Qollab half: three IonQ Forte 1 Runs each sent one bare transpiled Q1 A·Q^k circuit (cx 313 / 1503 / 2693) via backend.run + get_counts, no Sampler; all IONQ RUN ACCEPTED; records validate with backend_class qiskit_ionq.ionq_backend.IonQSimulatorBackend; mlae.estimate accepts them"
    requirement: QC-06
    verification:
      - kind: unit
        ref: "tests/test_ionq_records.py#test_committed_ionq_records_file_is_valid"
        status: pass
      - kind: unit
        ref: "tests/test_ionq_records.py#test_known_4sigma_miss_matches_data (ionq_estimate runs on the records: n_A 9000, ks (0, 1, 2))"
        status: pass
      - kind: other
        ref: "scripts/ingest_ionq_records.py paste.txt -> INGESTED 3 new, 0 duplicate, 0 failed attempt(s)"
        status: pass
    human_judgment: false
  - id: D4
    description: "QAE-01 on IonQ data: IonQ-only MLAE within 4 Fisher sigma of T1. Measured a = 0.228671, err -1.43e-2, se 2.24e-3, z = -6.38, N_A = 9000: NOT MET. Accepted by Hippolyte as a documented, open-cause discrepancy (`accept (a)`)"
    requirement: QAE-01
    verification:
      - kind: unit
        ref: "tests/test_ionq_records.py#test_ionq_only_estimate_within_4_sigma (strict xfail, KNOWN_4SIGMA_MISS)"
        status: fail
      - kind: other
        ref: "Task 3 IONQ ESTIMATE OK command -> AssertionError -6.384896030485165"
        status: fail
    human_judgment: true
    rationale: "The accuracy truth failed on real IonQ data; the user accepted the miss as a documented finding (resume signal `accept (a)`), so sign-off is a human judgment, not a test result"
  - id: D5
    description: "Size ladder (PD-21) recorded: no rejection, largest accepted body_bytes_est 306,656 B (k = 2), Q1lite unused; round trips run_s 11.96 / 22.29 / 22.55 s"
    verification:
      - kind: other
        ref: "grep -qF '## Phase 4 IonQ runs' docs/QOLLAB-RUNTIME.md && grep -qF 'Phase 4 IonQ path should use' docs/QOLLAB-RUNTIME.md"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Evidence fidelity: data/ionq_runs.json holds exactly the 3 parsed pasted records; docs/QOLLAB-RUNTIME.md quotes 3 IONQ_RECORD= lines and the QAE_REPORT= line verbatim; docs and data record sets are equal"
    requirement: QAE-02
    verification:
      - kind: unit
        ref: "tests/test_quantum_doc.py#test_ionq_records_in_docs_match_data"
        status: pass
      - kind: other
        ref: "IONQ_RECORD= line count in docs/QOLLAB-RUNTIME.md = 3 (>= 3)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Docs: docs/QUANTUM.md ## IonQ results and the README Phase 4 paragraph state a_hat, |a_hat - T1|, se, z, N_A, per-k P(flag) vs sin^2((2k + 1) theta) and timings, with the 6.4 sigma miss stated and no speedup claim"
    verification:
      - kind: unit
        ref: "tests/test_quantum_doc.py#test_ionq_results_section_matches_records_state"
        status: pass
    human_judgment: true
    rationale: "Honest framing (no speedup claim, the miss stated plainly) is a wording judgment a test cannot make"
  - id: D8
    description: "Noise honesty: the optional ideal_mode none runs (R4/R5) were not made, so no noisy record exists and no noisy comparison is reported"
    verification: []
    human_judgment: true
    rationale: "Nothing to verify; the verifier confirms that skipping the optional noisy runs is acceptable"
  - id: D9
    description: "No regression: default suite 337 passed, 5 skipped, 1 xfailed in 27.6 s with git status --porcelain unchanged; GOLDEN OK; frozen files unchanged since 55b334d"
    verification:
      - kind: other
        ref: ".venv/bin/python -m pytest -q (porcelain before == after)"
        status: pass
      - kind: other
        ref: ".venv/bin/python scripts/freeze_kernels.py -> GOLDEN OK kernels_v1.json T1=0.24300446519524305"
        status: pass
      - kind: other
        ref: "git diff --quiet 55b334d -- <frozen files> tests/golden"
        status: pass
    human_judgment: false
  - id: D10
    description: "Bundle rebuilt from 8350ae9 for the Phase 6 re-upload: ~/Desktop/qollab-phase4.zip, 55,182 B, sha256 9ba2439f193fd7e51b73c9db91cdced710717566956e28f3dbf6579d2e2bec3c, BUNDLE OK 19"
    verification:
      - kind: other
        ref: "shasum -a 256 ~/Desktop/qollab-phase4.zip (re-checked at closeout) + bundle audit -> BUNDLE OK 19"
        status: pass
    human_judgment: false

# Metrics
duration: 2h 01m (wall clock, including the human Qollab runs and the human-verify decision)
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 04: Qollab Built-in and IonQ Forte 1 Runs Summary

**The real Q1 QAE runs in Qollab's browser runtime (a = 0.242072 at N_A = 18,000), and one bare A·Q^k circuit per Run executes on IonQ Forte 1 at k = 0, 1 and 2 (all accepted, bodies up to 307 KB).**

- The three IonQ records are committed verbatim and tied to the docs by a test.
- Their IonQ-only MLAE estimate is 6.38 sigma below T1, so it misses the 4-sigma check. k = 1 and k = 2 deviate from the exact circuit far beyond shot noise, and the cause is still open.
- Hippolyte accepted the runs as the execution proof, with the miss recorded as a finding.

## Performance

- **Duration:** about 2 h wall clock. This includes Hippolyte's Qollab session and the human-verify decision on the miss.
- **Started:** 2026-10-11T04:32Z
- **Completed:** 2026-10-11T06:33Z
- **Tasks:** 3 of 3
- **Files:** 7 modified, none created. Two files went beyond the plan's list: `tests/test_ionq_records.py` and `tests/test_main_qae.py` (see Deviations).

## Run matrix

The runs took place at about 06:10-06:15 UTC, in the order R0, R2, R1, R3. The labels follow the protocol, not the order.

| Run | Backend | Model | k | Shots | Mode | hits | P(flag) measured | P(flag) exact | cx | body_bytes_est | run_s | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 | Built-in simulator (Pyodide) | Q1 | 0, 1, 2, 4 | 1000 per power | n/a | 229, 1000, 304, 994 | n/a | n/a | n/a | n/a | wall_clock_s 1.412 | `QAE RUN COMPLETED` |
| R1 | IonQ Forte 1 | Q1 | 0 | 1000 | set_options (ideal, sampled) | 267 | 0.2670 | 0.2430 | 313 | 31,136 | 11.96 | `IONQ RUN ACCEPTED` |
| R2 | IonQ Forte 1 | Q1 | 1 | 1000 | set_options (ideal, sampled) | 988 | 0.9880 | 0.9994 | 1,503 | 168,896 | 22.29 | `IONQ RUN ACCEPTED` |
| R3 | IonQ Forte 1 | Q1 | 2 | 1000 | set_options (ideal, sampled) | 349 | 0.3490 | 0.2859 | 2,693 | 306,656 | 22.55 | `IONQ RUN ACCEPTED` |
| R4, R5 | not run | | | | | | | | | | | |

**R0, the judged path (A-P1 confirmed):**
- The contract check gave |d| = 3.3e-15, with schedule [0, 1, 2, 4].
- The live MLAE gave a_hat = 0.242072 ± 1.26e-3 (|a_hat − T1| = 9.33e-4, z = −0.74) at N_A = 18,000.
- `wall_clock_s` was 1.412; Qollab's console header showed 3.4 s.

**Size ladder (PD-21):**
- No Run was rejected, so there is no rejection message to quote.
- The largest accepted body was 306,656 B. Qollab's body limit is therefore above about 307 KB; only this lower bound is known.
- Q1lite was not used.

**Timing (A2):**
- The k = 0 round trip (11.96 s) matches Phase 1's 11.5 s.
- k = 1 and k = 2 took about 22.3 s and 22.6 s. Qollab printed "Circuit execution time" of 1000 ms and 3000 ms for them.

**Other observations:**
- **Form:** five fields. This is inferred from all five values being accepted; Hippolyte did not state it.
- **Publish:** not published. The project is still a Draft and the public v1.0 is unchanged.

## IonQ-only estimate (QAE-01 on IonQ data)

```text
INGESTED 3 new, 0 duplicate, 0 failed attempt(s); 3 records (3 sampled) -> data/ionq_runs.json
IONQ ESTIMATE a=0.228671 err=-1.43e-02 se=2.24e-03 z=-6.38 N_A=9000 ks=[0, 1, 2]
```

**Per-k exact binomial tails against the exact P(flag):**

| k | Hits / 1000 | Expected | Tail | Tail probability |
|---|---|---|---|---|
| 0 | 267 | 243.0 | P(X ≥ 267) | 4.3e-2 |
| 1 | 988 | 999.4 | P(X ≤ 988) | 2.1e-12 |
| 2 | 349 | 285.9 | P(X ≥ 349) | 8.6e-6 |

k = 0 is consistent with T1. k = 1 and k = 2 are systematically off.

- **No single amplitude fits the three points.** The deviance is G = 14.6 on 2 degrees of freedom, p = 6.7e-4. The −6.38 sigma estimate is a symptom of the records breaking the Grover model, not an unlucky draw.
- **IonQ returned impossible outcomes.** It returned 3, 20 and 42 shots (k = 0, 1, 2) on basis states whose exact probability in the same transpiled circuit is below 1e-9.
- **The submitted circuits are correct.** qiskit `Statevector` and Aer, run locally on the same transpiled circuits, reproduce 0.2430, 0.9994 and 0.2859 exactly.
- **Where the deviation arises.** Hippolyte relayed IonQ's own "Probabilities" panel, which shows the same shifts. That places the deviation in IonQ's computation of the probabilities, before sampling.
- **Angle-rounding hypothesis tested and NOT confirmed.**
  - Rounding rx/ry/rz angles to 1, 2 or 3 decimals, or to 1/256, 1/1024 or 1/4096 of a turn, does not reproduce the measured numbers.
  - Neither does dropping rotations below 0.005-0.02 rad.
  - The cause is therefore open. It lies either in IonQ's ideal cloud simulation of the circuit or in qiskit-ionq 1.0.2 serialisation on Qollab.

## Checkpoint record

- **Task 2 (`checkpoint:human-action`, gate blocking).**
  - The resume signal was Hippolyte's pasted console output (labels R0, R2, R1, R3), saved verbatim to `/var/folders/0s/9zbv50r12p1fhm3y8xy2xn1h0000gn/T//neutron-qae-phase4-ionq/paste.txt`.
  - The paste included two "Orchestrator note" paragraphs relaying IonQ's Probabilities panel. These are summarised in the docs, not quoted as console lines.
- **Task 3 (human-verify).** Plan step 4 requires stopping when `test_ionq_only_estimate_within_4_sigma` fails, so the 4-sigma miss was surfaced as a human-verify checkpoint. Two options were offered:
  - (a) accept the IonQ runs as the execution proof and record the miss;
  - (b) re-run on Qollab.

  The resume signal, verbatim: `accept (a)`.

## Task Commits

1. **Task 1: Pre-flight tracer** (bundle, fake-IonQ dry run, ingest, IonQ-only estimate). No commit; no tracked file changed.
   - Bundle from 2d416f8: 51,698 B, sha256 `071f1c5747acbe6740525f05efef9e7e13190c530fd84e4080d20ca66f6b1c45`, `BUNDLE OK 19`.
   - Dry run: `IONQ ESTIMATE a=0.245670 … z=+1.16 N_A=9000`.
   - `QAE TRACER OK a=0.245094 N_A=18000 hits=[262, 1000, 277, 997]`.
2. **Task 2: Hippolyte's Qollab runs.** R0 on the Built-in simulator, then IonQ Forte 1 at k = 1, 0, 2. Human action, so no commit.
3. **Task 3: Records, estimate and docs.** Ingested the records verbatim, ran the IonQ-only estimate and wrote the docs. The 4-sigma miss was surfaced as human-verify and resolved `accept (a)`. Commit `8350ae9` (docs).

**Plan metadata:** the final `docs(04-04): complete ...` commit (SUMMARY, STATE, ROADMAP, REQUIREMENTS).

After 8350ae9 the bundle was rebuilt for the next upload: `~/Desktop/qollab-phase4.zip`, 55,182 B, sha256 `9ba2439f193fd7e51b73c9db91cdced710717566956e28f3dbf6579d2e2bec3c`, `BUNDLE OK 19`.

## Files Created/Modified

- `data/ionq_runs.json`: the 3 accepted IonQ Forte 1 records. They were written by `scripts/ingest_ionq_records.py` without `--allow-fake`, with no hand edits.
- `docs/QOLLAB-RUNTIME.md`: new `## Phase 4 IonQ runs (2026-10-11)` section. It holds the run table, the verbatim console lines, the ingest output, the size ladder, timings, the A-P1 result, the deviation analysis, and the form and publish observations. The Phase 1 sections and the "Phase 4 IonQ path should use" bullet are unchanged.
- `docs/QUANTUM.md`: `## IonQ results` now states the results, the miss and a pointer to the runtime doc.
- `README.md`: Phase 4 IonQ results paragraph, framed as an execution proof plus a three-power estimate, with the 6.4 sigma miss stated and no speedup claim.
- `tests/test_quantum_doc.py`: `test_ionq_records_in_docs_match_data`.
- `tests/test_ionq_records.py`: `KNOWN_4SIGMA_MISS`, a strict xfail on `test_ionq_only_estimate_within_4_sigma`, and `test_known_4sigma_miss_matches_data`.
- `tests/test_main_qae.py`: `test_main_qae_builtin_seeded` follows the committed records state.

## Decisions Made

See `key-decisions`. In short:
- PD-22 ran as planned.
- The IonQ execution proof is accepted with the miss recorded (`accept (a)`).
- The one-circuit-per-Run protocol is validated end to end.
- The body limit is above 307 KB.
- A-P1 is confirmed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_main_qae_builtin_seeded` assumed an empty records file**
- **Found during:** Task 3, after the ingest.
- **Issue:** The test asserted `qae["ionq_records"] is None` and `"IonQ records: none yet"`. Committing real records would have broken it.
- **Fix:** It now loads the committed records.
  - With no usable records it asserts the old behaviour.
  - Otherwise it asserts that the Built-in report carries the same a_hat, se, n_A and ks as `ionq_estimate`, and prints the `IonQ Forte 1 records (ideal, sampled): k=` line.
- **Files modified:** `tests/test_main_qae.py` (outside the plan's `files_modified`).
- **Committed in:** 8350ae9.

**2. [Rule 4 - Architectural/decision, user-accepted] Strict xfail keyed to `KNOWN_4SIGMA_MISS`**
- **Found during:** Task 3, step 4. `test_ionq_only_estimate_within_4_sigma` failed (z = −6.38).
- **Issue:** The plan says to stop before committing data that hides the failure. It also says never to loosen the tolerance or drop a record, and lets the user choose between a re-run and an xfail.
- **Fix:**
  - The assertion is unchanged.
  - A strict xfail matches only the exact committed (timestamp, model, k, shots, hits) set. It reports XFAIL for these records, fails the suite if they ever pass, and turns back into a plain assertion when any record changes.
  - `test_known_4sigma_miss_matches_data` pins z = −6.38 and N_A = 9000.
  - This was flagged at the human-verify checkpoint, and Hippolyte accepted it (`accept (a)`).
- **Files modified:** `tests/test_ionq_records.py` (outside the plan's `files_modified`).
- **Committed in:** 8350ae9.

**3. [Rule 1 - Presentation] Ingest path shortened in the doc**
- The `INGESTED` line in `docs/QOLLAB-RUNTIME.md` shows `data/ionq_runs.json` instead of the absolute repo path, which carries the local home directory. The doc says so explicitly. The records and every `IONQ_RECORD=` line are verbatim.

---

**Total deviations:** 3.
- 1 blocking test fix.
- 1 decision-level test change, accepted by the user.
- 1 presentation shortening.

**Impact:** the miss stays visible and enforced, with no tolerance change and no dropped record. Nothing outside the tests and docs changed.

## Issues Encountered

- **The IonQ-only estimate misses 4 sigma (z = −6.38).** The cause is open (see above). It was accepted as a documented finding and is carried as a STATE blocker for Phase 6.
- **The optional noisy runs (R4/R5) were not run,** so there is no noisy comparison (assumption A5 is unchecked).
- **The Qollab Draft still holds the 2d416f8 upload,** which predates the records. The Built-in path on Qollab shows the IonQ-only estimate only after the next upload.
- **Pre-existing warning.** `tests/test_smoke.py` emits a UserWarning ("Option noise_model is not used by this backend"). It is from Phase 1 and out of scope.

## User Setup Required

None remaining. The Qollab runs (the plan's `user_setup`) were done by Hippolyte in Task 2.

## Next Phase Readiness

Phase 4 is complete (4/4 plans). The phase is ready for verification and for Phases 5 and 6.

**ROADMAP Phase 4 criterion 4:**
- **Qollab half: met.** One bare A·Q^k circuit per Run, at most 7 controls, transpiled once, `backend.run` + `get_counts`, no Sampler, accepted on IonQ Forte 1, with counts that `mlae.estimate` accepts.
- **IonQ accuracy: not met.** z = −6.38. The user accepted it with the discrepancy documented.

**Phase 5:**
- The IonQ records are a labelled execution proof, never a scaling data point.
- The error-vs-N_A curve comes from the analytic and Aer runners only.

**Phase 6:**
- Re-upload the 8350ae9 bundle (`~/Desktop/qollab-phase4.zip`, sha256 `9ba2439f…bec3c`) so Built-in runs show the IonQ estimate.
- Add a one-line caveat where `main.py`'s Built-in path prints the IonQ-only estimate: it is 6.4 sigma off and the cause is open.
- Publish. The project is still a Draft.
- README on Qollab updates only through the Project Card or a fresh project.

**Open concern:** the cause of IonQ's deviation from the ideal model is unresolved, and it is recorded as a STATE blocker.

---
*Phase: 04-quantum-oracle-amplitude-estimation*
*Completed: 2026-10-11*

## Self-Check: PASSED

- All 7 modified files exist.
- Commits 2d416f8 (plan base) and 8350ae9 are ancestors of HEAD.
- Plan-level verification was re-run at closeout, with the results below.

| Check | Result |
|---|---|
| Default suite | 337 passed, 5 skipped, 1 xfailed in 27.6 s; porcelain unchanged |
| `tests/test_ionq_records.py tests/test_quantum_doc.py tests/test_docs.py` | 17 passed, 1 xfailed |
| `freeze_kernels.py` | `GOLDEN OK kernels_v1.json T1=0.24300446519524305` |
| Frozen-file diff against 55b334d | empty |
| `IONQ_RECORD=` lines in `docs/QOLLAB-RUNTIME.md` | 3 |
| Bundle sha256 | matches `9ba2439f…bec3c` |
| `IONQ ESTIMATE OK` command | fails with z = −6.38, as documented and accepted (D4); this is the recorded finding, not a self-check failure |
