---
phase: 01-qollab-smoke-test-compliant-skeleton
plan: 03
subsystem: platform
tags: [qollab, ionq, pyodide, smoke-test, noise-model, publish, runtime-findings, pytest]

# Dependency graph
requires:
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "01-01: main.py smoke test, neutron_qae/smoke.py, .gitattributes export-ignore; 01-02: README write-up, LICENSE, docs/QOLLAB-RUNTIME.md template, tests/test_docs.py"
provides:
  - "Published public default Qollab project, version v1.0: https://qollab.xyz/u/hdelloye/quantum-neutron-transport-spar"
  - "docs/QOLLAB-RUNTIME.md filled: 10-row run table, 9 verbatim QOLLAB_RUNTIME_REPORT= lines, R8 refusal, conclusions for Phases 4-6"
  - "neutron_qae/smoke.py run_toy sends one bare circuit per IonQ job (Qollab accepts only ionq.circuit.v1)"
  - "tests/test_docs.py#test_runtime_findings_recorded; tests/test_smoke.py IonQ fake rejects circuit lists"
affects: [quantum-oracle, mlae, ionq-runner, figures, submission, 01-04]

# Actuals (#2632)
actuals:
  tokens: 7515
  tasks: 3
  commits: 2
plan_head_before: 2045d11441f40d38bd4d51f281f0f9876b2592f1
plan_head_after: 90a7261be789d6ace286a4db9f5aebf304665177

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Runtime evidence recorded by script from the paste file, then asserted identical line-for-line, so report lines are never retyped"
    - "IonQ-like test fake mirrors Qollab's server rule: a list of circuits raises, one QuantumCircuit per job passes"

key-files:
  created: []
  modified:
    - docs/QOLLAB-RUNTIME.md
    - tests/test_docs.py
    - neutron_qae/smoke.py
    - tests/test_smoke.py
    - README.md

key-decisions:
  - "Qollab IonQ accepts only ionq.circuit.v1 and one job per Run, so an IonQ Run carries exactly one circuit; the research assumption 'MLAE as one multi-circuit job' is false and Phase 4 must redesign its IonQ path"
  - "Phase 4 ideal IonQ runs use backend.set_options(noise_model='ideal') (ideal, sampled); the run kwarg gives exact round(p*shots) with no shot noise and is never used for statistics; ideal_mode none gives forte-1 noise"
  - "Published as v1.0 (Hippolyte's choice) instead of the planned v0.0-smoke; public and default"
  - "Logged-out IonQ (R8) refused by Qollab ('credits apply, sign in') despite anon_enabled true: recorded as a server-side blocker; the judged Built-in path passes logged out"

patterns-established:
  - "One circuit per IonQ backend.run on Qollab; never pass a list to an IonQ backend"

requirements-completed: [PLAT-02]

coverage:
  - id: D1
    description: "Seven-file upload bundle built by git archive from a committed HEAD, audited for unexpected files and secret-shaped strings (built twice: 2045d11, then 73a4cb7)"
    requirement: "PLAT-02"
    verification:
      - kind: other
        ref: "Task 1 bundle verify command -> BUNDLE OK 7 (both bundles); sha256 bcbd8198dc8bc24cc01afe3d7950f3fea060626e01da55ff5b005364792bed7e for the published one"
        status: pass
    human_judgment: false
  - id: D2
    description: "Toy smoke test runs to SMOKE TEST PASSED on Qollab's Built-in simulator signed in and logged out, and on IonQ Forte 1 signed in with all three ideal_mode values"
    requirement: "PLAT-02"
    verification:
      - kind: manual_procedural
        ref: "docs/QOLLAB-RUNTIME.md Raw reports: R1, R1 re-run, R4/R5/R6 (new bundle), R7 all SMOKE TEST PASSED"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py#test_runtime_findings_recorded"
        status: pass
    human_judgment: true
    rationale: "The runs happened in Hippolyte's browser on Qollab; the record is a human copy-paste that no test can re-execute"
  - id: D3
    description: "Logged-out IonQ Forte 1 run (R8)"
    requirement: "PLAT-02"
    verification:
      - kind: manual_procedural
        ref: "R8: refused before running by Qollab, anonymous IonQ jobs need sign-in (paraphrase, no verbatim screen copy)"
        status: fail
    human_judgment: true
    rationale: "Server-side Qollab policy outside the code; the plan's success criterion allows recording the anonymous denial as a blocker"
  - id: D4
    description: "Runtime versions and noise_model='ideal' acceptance recorded with conclusions for Phases 4-6"
    requirement: "PLAT-02"
    verification:
      - kind: unit
        ref: "tests/test_docs.py#test_runtime_findings_recorded"
        status: pass
      - kind: other
        ref: "grep -F 'Phase 4 IonQ path should use' docs/QOLLAB-RUNTIME.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "IonQ jobs carry one circuit (fix 73a4cb7)"
    requirement: "PLAT-02"
    verification:
      - kind: unit
        ref: "tests/test_smoke.py#test_ionq_like_backend_sends_exactly_one_job"
        status: pass
      - kind: manual_procedural
        ref: "R4/R5/R6 new bundle accepted with circuits_per_job 1"
        status: pass
    human_judgment: false

# Metrics
duration: 60min
completed: 2026-10-10
status: complete
---

# Phase 1 Plan 03: Qollab smoke test, publish and runtime findings Summary

**The toy project is published on Qollab as public default v1.0 and passes on the Built-in simulator signed in and logged out and on IonQ Forte 1 signed in (after a fix to one circuit per IonQ job); set_options gives ideal sampled IonQ counts, but Qollab IonQ takes only one circuit per Run and refuses anonymous IonQ jobs, so Phase 4's one-multi-circuit-job MLAE plan needs a redesign**

## Performance

- **Duration:** ~60 min (most of it Hippolyte's browser work at the Task 2 checkpoint)
- **Started:** 2026-10-10T18:50Z
- **Completed:** 2026-10-10T19:50:14Z
- **Tasks:** 3 (plus one Rule 1 fix)
- **Files modified:** 5 (docs/QOLLAB-RUNTIME.md, tests/test_docs.py, neutron_qae/smoke.py, tests/test_smoke.py, README.md)

## Accomplishments

- Published URL: https://qollab.xyz/u/hdelloye/quantum-neutron-transport-spar (project "Quantum Neutron Transport - SPARC First Wall", version **v1.0**, public and default; files replaced in the existing Draft, no second project)
- Anonymous-IonQ flag (Task 1, `curl -fsS https://api.qollab.xyz/api/ionq/backends/simulator/cost`), verbatim at 2026-10-10T18:51:37Z and again at 19:24:03Z: `{"cost":"0","anon_enabled":true}`
- noise_model conclusions: kwarg ACCEPTED (exact `round(p*shots)`, 100/100, no shot noise); set_options ACCEPTED (ideal, sampled, 109/91); none gives forte-1 noise (ghz_off_ideal_fraction 0.045)
- Phase 4 recommendation: use `backend.set_options(noise_model="ideal")` for ideal IonQ runs and `none` for the noisy comparison; send exactly one circuit per IonQ Run, so redesign MLAE on IonQ (one Run per Grover power, or a single `A Q^k` execution proof with the curve from local and Built-in runs)
- Runtime: Python 3.14.2 (emscripten, Pyodide 314.0.7), numpy 2.4.6, scipy 1.18.0, qiskit 2.5.2, qiskit_ionq 1.0.2 (loaded only after an IonQ backend is selected)
- Timing: IonQ Forte 1 job ~11.5 s round trip (console 13.3-13.4 s); Built-in wall_clock_s 0.081-0.346 s (console 1.7 s); 12-qubit perf probe 0.037-0.046 s in Pyodide vs 0.021 s native (~2x)
- Run settings form showed all four fields (Shots, Ghz Qubits, Ideal Mode, Perf Qubits)
- `.venv/bin/python -m pytest -q`: 36 passed

## Run matrix

| Run | Bundle | Logged in | Backend | ideal_mode | Result |
|-----|--------|-----------|---------|------------|--------|
| R1 | old (2045d11) | yes | Built-in | none | PASSED, wall 0.108 s |
| R4 | old | yes | IonQ Forte 1 | none | FAILED: IonQAPIError 400 `Only job type ionq.circuit.v1 is supported` |
| R5 | old | yes | IonQ Forte 1 | kwarg | FAILED: same 400 |
| R6 | old | yes | IonQ Forte 1 | set_options | FAILED: same 400 |
| R4 | new (73a4cb7) | yes | IonQ Forte 1 | none | PASSED, noisy, run_s 11.472 |
| R5 | new | yes | IonQ Forte 1 | kwarg | PASSED, ideal exact round(p*shots), 100/100 |
| R6 | new | yes | IonQ Forte 1 | set_options | PASSED, ideal sampled, 109/91 |
| R1 re-run | new | yes | Built-in | none | PASSED, wall 0.346 s |
| R7 | new (published v1.0) | no (incognito) | Built-in | none | PASSED, wall 0.081 s |
| R8 | new (published v1.0) | no (incognito) | IonQ Forte 1 | none | REFUSED before running: "it refuses Forte1 because credits apply. You need to sign in" (Hippolyte's description, not a verbatim screen copy; no report) |

R2/R3 (perf_qubits 16/20) were not run. Chrome version was not supplied. Every report line is in docs/QOLLAB-RUNTIME.md verbatim.

## Checkpoint resolution (Task 2, human-action)

Hippolyte uploaded the first bundle, ran R1 and R4-R6, which exposed the multi-circuit rejection; after fix 73a4cb7 the rebuilt bundle (8,362 bytes, sha256 `bcbd8198dc8bc24cc01afe3d7950f3fea060626e01da55ff5b005364792bed7e`, `BUNDLE OK 7`, pytest 35 passed) replaced the files in the same Draft project. He re-ran R4-R6 and R1, published v1.0 as public default, then ran R7 and R8 from a Chrome incognito window. Evidence pasted to the orchestrator scratchpad and copied into docs/QOLLAB-RUNTIME.md by script, with a line-for-line identity check.

## Task Commits

1. **Task 1: Pre-publication audit and the Qollab upload bundle** - no commit (no tracked file changed; bundle lives at ~/Desktop/qollab-smoke.zip)
2. **Task 2 deviation fix: send one circuit per IonQ job** - `73a4cb7` (fix)
3. **Task 2: Hippolyte uploads, runs, publishes and repeats logged out** - no commit (browser-only)
4. **Task 3: Record the Qollab findings verbatim and guard them with a test** - `90a7261` (docs)

**Plan metadata:** recorded in the docs(01-03) commit that adds this SUMMARY

## Files Created/Modified

- `docs/QOLLAB-RUNTIME.md` - run table, raw reports, conclusions for Phases 4-6; new static fact "one circuit per IonQ job"
- `tests/test_docs.py` - `test_runtime_findings_recorded`
- `neutron_qae/smoke.py` - `run_toy` sends one bare GHZ circuit; `all_ones()` and `ones_fraction` removed; `counts` is one dict; new `circuits_per_job: 1`
- `tests/test_smoke.py` - IonQ-like fake raises on list input; asserts one call with one QuantumCircuit
- `README.md` - module rule now states one job per run and one circuit per job on Qollab IonQ

## Decisions Made

- set_options is the Phase 4 ideal IonQ path; kwarg counts are never presented as sampled statistics.
- v1.0 kept as the published version name (Hippolyte's choice); the docs record that v0.0-smoke was the planned name.
- R8 recorded as a Qollab server-side blocker, not a code failure, per the plan's flagged assumption; the judged Built-in path passes logged out.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IonQ job carried two circuits; Qollab accepts only `ionq.circuit.v1`**
- **Found during:** Task 2, run R4 (signed in, IonQ Forte 1, ideal_mode none) -> `SMOKE TEST FAILED` with `IonQAPIError ... 'Only job type ionq.circuit.v1 is supported', status_code=400`; R5 and R6 failed the same way
- **Issue:** `run_toy` passed a two-circuit list to `backend.run`. qiskit-ionq 1.0.2 `helpers.py` sets `multi_circuit = isinstance(circuit, (list, tuple))` and sends `"type": "ionq.multi-circuit.v1"` for lists; Qollab's IonQ proxy rejects that type
- **Fix:** `run_toy` transpiles and sends one bare GHZ `QuantumCircuit`; `all_ones()` and `ones_fraction` removed; `counts` is one dict; `circuits_per_job: 1` added. Test fake now rejects lists. README rule updated
- **Files modified:** neutron_qae/smoke.py, tests/test_smoke.py, README.md
- **Verification:** pytest 35 passed at the time; bundle rebuilt (`BUNDLE OK 7`); R4/R5/R6 on the new bundle all `SMOKE TEST PASSED` with `circuits_per_job: 1`
- **Committed in:** `73a4cb7`

### Other differences from the plan text

- Published version is `v1.0`, not `v0.0-smoke` (Hippolyte's choice). The must-have truth naming v0.0-smoke is met in substance (public default version at a https://qollab.xyz/u/ URL).
- R8 has no verbatim error text; Hippolyte described the refusal in his own words. Recorded as such.
- R2/R3 and the Chrome version and stopwatch time-to-first-output were not supplied; the console header times (1.7 s Built-in) are recorded instead.
- The 01-04 PLAN interface table still lists `all_ones(n)` as an export of neutron_qae/smoke.py; it no longer exists (01-04 does not call it).

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** The fix was required for any IonQ run to succeed; it also surfaced the one-circuit-per-Run constraint that changes Phase 4's design.

## Issues Encountered

- Logged-out IonQ refused (R8) although the cost endpoint reports `anon_enabled: true`. Server-side; cannot be fixed in code. Added to STATE.md blockers.
- The README write-up was rendered from the first upload (project creation); the new bundle's README change (one-circuit rule bullet) may not show on Qollab, since re-uploading into an existing project skips README.md (Pitfall 8). Phase 6 should paste README.md into the Project Card or create the project fresh.

## Known Stubs

None. All placeholders in docs/QOLLAB-RUNTIME.md were replaced.

## User Setup Required

None further for this plan. Plan 01-04 needs Hippolyte to run `gh auth login`.

## Next Phase Readiness

- Phase 1 criterion 2 met (versions and noise_model acceptance recorded). Criterion 1 met for the Built-in path logged out; the logged-out IonQ half is a recorded Qollab-side blocker.
- BLOCKER for Phase 4 planning: one circuit per IonQ Run on Qollab. MLAE on IonQ must be redesigned (one Run per Grover power, or a single-circuit execution proof).
- Ready for 01-04 (GitHub remote and push).

## Self-Check: PASSED

- docs/QOLLAB-RUNTIME.md, tests/test_docs.py, neutron_qae/smoke.py, tests/test_smoke.py, README.md exist.
- Commits `73a4cb7` and `90a7261` are ancestors of HEAD; `git rev-list --count 2045d11..HEAD` = 2.
- `.venv/bin/python -m pytest -q`: 36 passed; `--collect-only` lists test_runtime_findings_recorded; acceptance greps (QOLLAB_RUNTIME_REPORT=, https://qollab.xyz/u/, v0.0-smoke, Phase 4 IonQ path should use) pass; the 9 report lines are identical to the evidence paste.

---
*Phase: 01-qollab-smoke-test-compliant-skeleton*
*Completed: 2026-10-10*
