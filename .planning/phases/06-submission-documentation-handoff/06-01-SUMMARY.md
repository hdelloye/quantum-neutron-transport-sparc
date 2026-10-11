---
phase: 06-submission-documentation-handoff
plan: 01
subsystem: entry-point
tags: [qollab, main-py, quick-mode, figures, ionq-caveat, wr-02, cr-01, docs-01]
status: complete

# Dependency graph
requires:
  - phase: 05-scaling-study-figures
    provides: "figures.RENDERERS / SURFACE, artifacts.load_artifact, headline_sentence, HISTOGRAM_LABEL, the four committed data/*.json artifacts"
  - phase: 04-quantum-oracle-amplitude-estimation
    provides: "main() qae mode, runners.BackendRunner / IonQRunner / load_ionq_records / ionq_estimate, the committed IonQ Forte 1 records (z = -6.38)"
provides:
  - "main() quick mode, now the default (PD-33): Q1 contract, one live list job over k = 0, 1, 2, MLAE, the IonQ line with its CAVEAT, four figures from data/*.json via plt.savefig, QUICK_REPORT=, QUICK MODE OK / QUICK MODE INCOMPLETE: ..."
  - "_ionq_line: the IonQ estimate can only be printed with its computed-sigma CAVEAT on the same line (quick and qae)"
  - "WR-02 closed on the judged path: _ionq_summary returns {error} for ValueError, OSError, OverflowError, RecursionError, TypeError, KeyError"
  - "CR-01 closed in main.py (PD-34): ideal_mode 'none' refused in quick and qae modes before any job"
  - "scripts/run_local.py --figure-dir (default: fresh temp dir), Agg backend selected in the script only"
  - "tests/test_main_quick.py (6 tests, 1 slow) and the updated tests/test_main_qae.py"
affects: [06-02 README/HANDOFF, 06-03 publish and logged-out check]

# Actuals (#2632)
actuals:
  tokens: 7176        # chars/4 over the realized diff b15c243..f989824 (28,704 chars)
  tasks: 3
  commits: 3          # measured: git rev-list --count b15c243..HEAD at SUMMARY time
plan_head_before: b15c243d4091f1fbf84b34b01e06e4b1c906614f
plan_head_after: f98982419a2f658d1ed1b413aee21791cd510e93

tech-stack:
  added: []
  patterns:
    - "Figures in the browser: render from committed JSON, show through plt.savefig(os.path.join(FIGURE_DIR, name)); never stat or read back the saved file (Qollab writes nothing to disk)"
    - "Per-figure try/except: a figure failure is a report entry and an INCOMPLETE final line, never a traceback"
    - "Caveat bound to the estimate: one helper builds the whole printed line"

key-files:
  created:
    - tests/test_main_quick.py
  modified:
    - main.py
    - scripts/run_local.py
    - tests/test_main_qae.py

key-decisions:
  - "PD-33 (costly): mode='quick' is main()'s default; MODES = (quick, qae, smoke); quick uses the form's shots per power over QUICK_SCHEDULE (0, 1, 2), honours model, k applies to IonQ only"
  - "PD-34: CR-01 closed by refusing ideal_mode='none' in quick and qae modes in main.py; runners.py untouched; noisy IonQ runs become a HANDOFF item"
  - "PD-35: quick figures shown via plt.savefig(os.path.join(FIGURE_DIR, name), dpi=90, facecolor=figures.SURFACE); FIGURE_DIR = '' on Qollab; main.py never selects a matplotlib backend"

patterns-established:
  - "Quick-mode tests: model Q0, QUICK_FIGURES monkeypatched to at most one figure, FIGURE_DIR = tmp_path; the four-figure run is slow-marked"

requirements-completed: [DOCS-01]

coverage:
  - id: D1
    description: "Untouched Run of main() on the Built-in simulator: contract, live MLAE [0, 1, 2], four figures, QUICK MODE OK in under 5 s"
    requirement: DOCS-01
    verification:
      - kind: integration
        ref: "scripts/run_local.py --seed 2026 --figure-dir <tmp> (QUICK TRACER OK a=0.246050 N_A=9000 figures=4)"
        status: pass
      - kind: unit
        ref: "tests/test_main_quick.py::test_quick_is_the_default_mode"
        status: pass
      - kind: integration
        ref: "NEUTRON_QAE_SLOW=1 pytest -m slow tests/test_main_quick.py::test_quick_full_defaults_four_figures_under_5s"
        status: pass
  - id: D2
    description: "IonQ estimate always printed with its computed-sigma CAVEAT (6.4 sigma on committed data)"
    requirement: DOCS-01
    verification:
      - kind: integration
        ref: "scripts/run_local.py --mode qae --seed 2026 (QAE TRACER OK a=0.245094 N_A=18000 caveat=yes)"
        status: pass
      - kind: unit
        ref: "tests/test_main_qae.py::test_builtin_prints_ionq_estimate_when_records_exist"
        status: pass
  - id: D3
    description: "WR-02 and CR-01 closed on the judged path; quick on IonQ sends one bare circuit; figure failures isolated"
    requirement: DOCS-01
    verification:
      - kind: unit
        ref: "tests/test_main_qae.py::test_ionq_summary_survives_malformed_records, test_noisy_ideal_mode_is_refused_before_any_job; tests/test_main_quick.py::test_quick_on_ionq_sends_one_bare_circuit, test_corrupt_artifact_gives_incomplete_not_a_crash, test_one_failing_renderer_does_not_stop_the_others"
        status: pass

# Metrics
duration: ~15min
completed: 2026-10-11
---

# Phase 6 Plan 01: Quick mode as main()'s default Summary

**An untouched Qollab Run now contract-checks Q1, runs a live 3-power MLAE (N_A 9000), prints the IonQ line with its 6.4-sigma CAVEAT, shows the four Phase 5 figures through plt.savefig and ends `QUICK MODE OK` in 2.3 s locally; WR-02 and CR-01 are closed in main.py.**

## Performance

- **Duration:** about 15 min
- **Completed:** 2026-10-11
- **Tasks:** 3 / 3
- **Files modified:** 4 (main.py, scripts/run_local.py, tests/test_main_qae.py, tests/test_main_quick.py)

## Accomplishments

- Tracer lines (all printed as specified):
  - `QUICK TRACER OK a=0.246050 N_A=9000 figures=4 t=1.54s` + `PNG OK` (four `quick_fig_*.png` in a temp dir, none in the repo)
  - `QAE TRACER OK a=0.245094 N_A=18000 caveat=yes`
  - `SUITE OK 398 passed, 7 skipped, 1 xfailed, 1 warning in 28.90s` (an earlier run: 28.60 s), porcelain unchanged
  - `QUICK WALL OK 2.26s` (process wall clock, `scripts/run_local.py` with defaults)
  - Slow test `test_quick_full_defaults_four_figures_under_5s`: 1 passed in 1.83 s
  - `GOLDEN OK kernels_v1.json T1=0.24300446519524305`, `SMOKE TEST PASSED`, `REGRESSION OK`
- Four PNG sizes at QUICK_DPI 90, in QUICK_FIGURES order: scaling_rmse 630x414, exit_histograms 630x414, truncation_bias 810x360, thickness_study 810x360.
- Final-line strings: `QUICK MODE OK`; `QUICK MODE INCOMPLETE: live run <ok|failed>, <n> of <N> figures rendered`.
- IonQ line as printed with the committed data/ionq_runs.json:
  `IonQ Forte 1 records (ideal, sampled): k=[0, 1, 2] -> a_hat=0.228671, |a_hat - T1|=1.43e-02, se=2.24e-03, z=-6.38, N_A=9000. CAVEAT: execution proof only, not in any fit or claim; 6.4 sigma from exact T1; the k >= 1 records deviate beyond shot noise, cause open (docs/QUANTUM.md)`
- CR-01 refusal text: `ideal_mode 'none' is refused in quick and qae modes (Phase 4 review CR-01): IonQ noise-model counts are round(p shots) values that do not sum to shots, so the run's record would be lost; use 'set_options'`.

## Task Commits

1. **Task 1: Tracer - quick mode default on BasicSimulator** - `5360500` (feat)
2. **Task 2: IonQ caveat, WR-02, CR-01, quick on IonQ** - `226743a` (fix; tests written first and seen failing: 12 failed before the implementation)
3. **Task 3: figure-failure isolation, reachability, slow timing test** - `f989824` (test; no main.py fix was needed)

## Handoff to 06-02 (names README must document)

- Default mode is `quick` (signature `def main(mode: str = "quick", k: int = 1, shots: int = 1000, ideal_mode: str = "set_options", model: str = "Q1"):`); `qae` and `smoke` remain.
- Output markers: `QUICK MLAE a_hat=... (live, <backend>)`, `QUICK_REPORT=` (one JSON line: mode, backend, live, ionq_records incl. `z` and `caveat`, figures, figures_ok, wall_clock_s), `figure i/4 <kind>: shown (download quick_fig_<name>.png)`, `QUICK MODE OK` / `QUICK MODE INCOMPLETE: ...`.
- Local: `scripts/run_local.py [--seed 2026] [--figure-dir DIR]` (quick, PNGs to a temp dir by default); `--mode qae --seed 2026` reproduces the Phase 4 QAE run.
- CR-01: `ideal_mode="none"` refused in quick and qae (smoke still accepts it); noisy IonQ runs are a HANDOFF item (fix in runners: keep raw counts, enforce the sum only for sampled records).
- CAVEAT wording as above; the caveat names docs/QUANTUM.md as where the open cause is discussed.
- In-browser half of DOCS-01 (Pyodide matplotlib through Qollab's savefig hook) is unverified until 06-03's logged-out run.

## Deviations from Plan

**1. [Rule 1 - Bug in verify command] Task 3 SUITE OK check rejects any `xfailed`**
- **Found during:** Task 3
- **Issue:** the plan's check asserts `'failed' not in s`, which matches the pre-existing `1 xfailed` (test_ionq_only_estimate_within_4_sigma), so it fails on a green suite.
- **Fix:** re-ran the same check with the word `xfailed` stripped before the `failed`/`error` test; summary line and time unchanged. No code change.

Otherwise the plan was executed as written. Note: the suite time (28.6 / 28.9 s) stayed under the plan's 29.0 s threshold, so the default-mode test keeps its one rendered figure; the margin to the 30 s gate is about 1 s.

## Known Stubs

None.

## Self-Check: PASSED
