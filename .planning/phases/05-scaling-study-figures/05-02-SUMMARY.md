---
phase: 05-scaling-study-figures
plan: 02
subsystem: analysis
tags: [exit-histograms, chi-square, truncation-bias, thickness-study, rare-event, artifacts, figures, anly-02, anly-03, anly-04, anly-05]
status: complete

# Dependency graph
requires:
  - phase: 05-scaling-study-figures (05-01)
    provides: "artifacts registry + envelope v1, sweep_common.finish/provenance, classical_rmse_series, mlae_rmse_series, fit_series, cost_at_target, render_file, PD-30 palette"
  - phase: 03-classical-baseline
    provides: "run_lattice, sample_exit_rows, run_continuous (within(K), order_fractions), exact T0/T1"
  - phase: 04-quantum-oracle-amplitude-estimation
    provides: "make_problem(\"Q1\", kernels) contract gate, BackendRunner(measure=\"all\")"
provides:
  - "data/exit_histograms.json + data/fig_exit_histograms.png: matched 1e6-sample classical vs Q1 (k = 0, Aer) row histograms, labelled circuit validation"
  - "data/truncation_bias.json + data/fig_truncation_bias.png: T0, T1 vs continuous T_full per wall and model, bias and K = 1 coverage"
  - "data/thickness_study.json + data/fig_thickness_ratio.png: five walls, cost at 1% relative RMSE, classical/MLAE ratio, absolute-target disclosure"
  - "artifacts.py: HISTOGRAM_/TRUNCATION_/THICKNESS_ FILE/FIGURE literals, registry with four kinds, three kind validators, CROSS_SECTION_MODELS"
  - "analysis.py: classical_exit_rows, quantum_exit_rows, chi2_two_sample, chi2_goodness, chi2_bound, check_transmission"
  - "figures.py: render_exit_histograms, render_truncation_bias, render_thickness_study in RENDERERS"
  - "scripts/sweep_histograms.py, scripts/sweep_truncation.py, scripts/sweep_thickness.py (--widths, underflow guard)"
  - "tests/test_studies.py (11 tests)"
affects: [05-03, phase-6, docs-05, readme]

# Actuals (#2632)
actuals:
  tokens: 24105       # chars/4 over the added lines of the realized diff 05341ae..HEAD, PNG excluded (96,419 chars)
  tasks: 3
  commits: 6          # measured: git rev-list --count 05341ae..HEAD at SUMMARY time
plan_head_before: 05341aee5dd412b03953f29b52ea7de6ed585ba6
plan_head_after: ed19949abd63c38b26854cce94a221b5d941dabb

tech-stack:
  added: []
  patterns:
    - "Each study is a vertical slice: script -> validated JSON -> PNG rendered from that JSON -> committed-artifact tests"
    - "Code committed first, sweep run on a clean tree (git_dirty false), data committed second"
    - "Guards run for every input before any sweep starts (thickness underflow guard: exit 2, nothing written)"
    - "Costs at target read off measured curves by log-log interpolation only; bracketed required in full profile"

key-files:
  created:
    - scripts/sweep_histograms.py
    - scripts/sweep_truncation.py
    - scripts/sweep_thickness.py
    - tests/test_studies.py
    - data/exit_histograms.json
    - data/fig_exit_histograms.png
    - data/truncation_bias.json
    - data/fig_truncation_bias.png
    - data/thickness_study.json
    - data/fig_thickness_ratio.png
  modified:
    - neutron_qae/artifacts.py
    - neutron_qae/analysis.py
    - neutron_qae/figures.py
    - tests/test_artifacts.py

key-decisions:
  - "PD-27: exit histograms at S = 1,000,000 matched samples; SeedSequence(seed).spawn(3) -> classical, rows, aer; Aer statevector on BackendRunner(measure=all).circuits([0])[0]; 17 categories; two-sample chi-square and goodness of fit with bound dof + 5 sqrt(2 dof); no per-row z-scores (WR-07)"
  - "PD-28: truncation cases transport_corrected 6/10/15/20/30 cm then isotropic_raw 10 cm, SeedSequence(seed).spawn(6) in case order, 2e7 histories each; bias SE = transmission SE; coverage = T1 / T_full; isotropic_raw is a disclosure point only"
  - "PD-29: thickness walls 6/10/15/20/30 cm (2.0 cm W), child = SeedSequence(seed).spawn(5)[i], classical, analytic = child.spawn(2); R = 100, 13-point grid, M = 1..9 at 300 shots; target 0.01 T1 by cost_at_target; absolute 1e-3 disclosure; underflow guard check_transmission(T1, max N, 1000)"
  - "05-02 timing fallback: the four-figure DPI-60 render test moved behind slow; the exit-histogram label render remains the fast default-suite smoke render"

requirements-completed: [ANLY-02, ANLY-03, ANLY-04, ANLY-05]

duration: ~25 min (continuation; Task 1 by the previous executor)
completed: 2026-10-11
---

# Phase 5 Plan 02: Exit histograms, truncation bias and wall-thickness study Summary

**1e6-sample classical vs Q1 (Aer) exit histograms agree by chi-square (16.46 / 17.01 / 13.14, bound 44.28); K = 1 covers 99.69% of the 10 cm transmission (bias 7.9 SE); the classical-to-MLAE cost ratio at 1% relative RMSE grows 1.99 -> 25.84 from 6 to 30 cm walls, while at a fixed 1e-3 absolute RMSE it shrinks 18.1 -> 5.0 (disclosed).**

## Interruption and continuation

The first executor completed Task 1 (`e894566`, `5f46b1e`) and was cut off by an API rate limit partway through Task 2. This continuation started from a partial working tree: changes to `neutron_qae/artifacts.py` and `neutron_qae/figures.py`, plus an untracked `scripts/sweep_truncation.py`. The suite showed 5 failures because `truncation_bias` was registered before its data existed.

- **Kept as-is:** the `truncation_bias` validator and registration, `CROSS_SECTION_MODELS`, `render_truncation_bias`, the `_sample_text` generalisation ("2e7"), and the whole of `scripts/sweep_truncation.py`. All of it was checked against PD-28 and the plan's field list. A quick-profile run worked first time.
- **Added:** `ax2.set_xlim` in the truncation figure, so the 30 cm label is no longer clipped. Also the truncation tests, plus the test that pins `CROSS_SECTION_MODELS == problem.MODELS`, which a comment in `artifacts.py` promised but nobody had written.
- **Redone:** nothing. Task 3 was written from scratch.

## Performance

- Task 2 sweep: `SWEEP truncation_bias profile=full seed=2026 coverage_10cm=0.9969 min_coverage=0.9891 iso_coverage=0.8987 total_s=11.4`
- Task 3 sweep: `SWEEP thickness_study profile=full seed=2026 ratios=[1.99, 4.27, 7.77, 15.54, 25.84] monotone=True total_s=74.9` (about 15 s per wall)
- Task 1 sweep (previous executor): 1.25 s total
- Default suite: `374 passed, 6 skipped, 1 xfailed in 27.89s` and then `27.18s` after the slow move. Before the move it measured 28.20 s after Task 2 and 28.58 s / 29.76 s after Task 3, with machine load average about 3.2. Porcelain was unchanged.
- `RENDER CHECK OK 4`; `GOLDEN OK kernels_v1.json T1=0.24300446519524305`. The frozen-file diff against 60bf3c5 is empty and main.py's numstat is still `1 1`. The QAE tracer still gives a=0.245094, N_A=18000, hits=[262, 1000, 277, 997].

## Checker lines

- `HISTOGRAMS OK {'classical_vs_quantum': 16.46, 'classical_vs_exact': 17.01, 'quantum_vs_exact': 13.14} png=770x506` (Task 1)
- `TRUNCATION OK coverage [('tra', 6.0, 0.9989), ('tra', 10.0, 0.9969), ('tra', 15.0, 0.9957), ('tra', 20.0, 0.9951), ('tra', 30.0, 0.9891), ('iso', 10.0, 0.8987)]`
- `THICKNESS OK rel ratios [1.99, 4.27, 7.77, 15.54, 25.84] abs ratios [18.1, 13.96, 10.07, 9.57, 5.04]`

## Artifacts

| File | Bytes | PNG px | git_head (dirty) |
|---|---|---|---|
| data/exit_histograms.json | 3,713 | | e894566 (false) |
| data/fig_exit_histograms.png | 56,366 | 770 x 506 | |
| data/truncation_bias.json | 6,171 | | 30e60a9 (false) |
| data/fig_truncation_bias.png | 69,035 | 990 x 440 | |
| data/thickness_study.json | 25,567 | | dc99bef (false) |
| data/fig_thickness_ratio.png | 80,397 | 990 x 440 | |

The registry now holds four kinds: `scaling_rmse`, `exit_histograms`, `truncation_bias` and `thickness_study`. Every JSON is under 500,000 B and every PNG under 400,000 B.

The thickness PNG was re-rendered from the committed JSON with `scripts/render_figures.py --only thickness_study` after a layout-only change to `figures.py` (legend placement and y headroom), so the PNG shows the `ed19949` renderer. The JSON numbers come from clean `dc99bef`.

## Handoff numbers for 05-03

- **Histograms (ANLY-02):** chi-square, classical vs quantum = 16.46, classical vs exact = 17.01, quantum vs exact = 13.14 (dof 16, bound 44.28). Outside support 0, flag mismatch 0. Each side has 1,000,000 samples. The label is "circuit validation, not speedup evidence".
- **Truncation (ANLY-03), transport-corrected:**

  | Wall | Coverage | Bias | Bias in SE |
  |---|---|---|---|
  | 6 cm | 0.9989 | 4.80e-4 | 4.4 |
  | 10 cm | 0.9969 | 7.63e-4 | 7.9 |
  | 15 cm | 0.9957 | 5.32e-4 | 7.3 |
  | 20 cm | 0.9951 | 3.04e-4 | 5.6 |
  | 30 cm | 0.9891 | 1.69e-4 | 6.1 |

  isotropic_raw at 10 cm: coverage 0.8987, bias 1.24e-2 (169 SE). It is shown for disclosure only; the circuit does not use it.
- **Thickness (ANLY-04):**

  | Wall | T1 | Classical N at 1% (theory) | MLAE N_A | Ratio | Ratio at 1e-3 absolute |
  |---|---|---|---|---|---|
  | 6 cm | 0.41939 | 11,384 (13,844) | 5,709 | 1.99 | 18.1 |
  | 10 cm | 0.24300 | 30,457 (31,152) | 7,135 | 4.27 | 13.96 |
  | 15 cm | 0.12224 | 67,051 (71,810) | 8,634 | 7.77 | 10.07 |
  | 20 cm | 0.06131 | 173,706 (153,106) | 11,176 | 15.54 | 9.57 |
  | 30 cm | 0.01536 | 594,814 (641,168) | 23,022 | 25.84 | 5.04 |

  Span 12.96; log-log slope of the ratio against T1 is -0.765. The underflow guard refuses a 50 cm wall (T1 = 9.56e-4, 955.9 expected events at 1e6) and accepts 40 cm.

## Task Commits

1. Task 1 (previous executor): `e894566` feat (tracer code), `5f46b1e` test + data
2. Task 2: `30e60a9` feat (truncation code), `cc6017e` test + data
3. Task 3: `dc99bef` feat (thickness code), `ed19949` test + data (+ figure layout, slow move)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Test-time budget] Four-figure render test moved behind `slow`**
- **Found during:** Task 3 final suite measurement
- **Issue:** The default suite measured 28.58 s and 29.76 s, above the orchestrator's 28.5 s trigger (hard gate 30 s).
- **Fix:** `tests/test_artifacts.py::test_figures_render_from_committed_json` (DPI-60 re-render of all four figures, about 0.6 s) is now `@pytest.mark.slow` and skipped unless `NEUTRON_QAE_SLOW=1`. Its assertions are unchanged; it passes under `NEUTRON_QAE_SLOW=1`. `scripts/render_figures.py --check` (`RENDER CHECK OK 4`) also covers it. `test_exit_histogram_is_labelled_validation` stays in the default suite as the fast smoke render. The suite now measures 27.2-27.9 s.
- **Commit:** ed19949

**2. [Rule 1 - Figure legibility] Thickness and truncation figure layout**
- The thickness figure's right-panel legend covered the 30 cm and then the 6 cm annotation. It now sits lower left, with y headroom added. The truncation coverage panel clipped the 30 cm label, so an x-limit margin was added.
- **Commits:** 30e60a9 (truncation), ed19949 (thickness)

**3. [Scope] `--widths` validation exit code**
- `sweep_thickness.main` returns 2 for non-numeric, non-ascending or <= 2.0 cm widths as well as for underflow walls. Every message names the offending wall.

None of these changed a seed, target, wall list, shot count or assertion.

## Known Stubs

None.

## Threat Flags

None. All new surface is in the plan's threat register: T-05-05 count parsing (Task 1), T-05-06 width validation plus the underflow guard (Task 3), and T-05-07 provenance and validators.

## Self-Check: PASSED

- All six data files exist and are committed. They load and validate with `git_dirty` false.
- Commits e894566, 5f46b1e, 30e60a9, cc6017e, dc99bef and ed19949 are all ancestors of HEAD.
