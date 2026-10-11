---
phase: 05-scaling-study-figures
plan: 01
subsystem: analysis
tags: [scaling, rmse, mlae, lattice-mc, aer, artifacts, figures, provenance, anly-01, anly-05]
status: complete

# Dependency graph
requires:
  - phase: 03-classical-baseline (03-02)
    provides: "run_lattice(..., checkpoints=), LatticeResult.prefix_estimates(), cost = histories, SeedSequence spawning"
  - phase: 04-quantum-oracle-amplitude-estimation (04-02, 04-04)
    provides: "AnalyticRunner, BackendRunner.circuits, mlae.estimate / exponential_schedule / n_applications, load_ionq_records + ionq_estimate, the 3 IonQ Forte 1 records (accepted 6.4 sigma miss)"
provides:
  - "neutron_qae/artifacts.py: stdlib-only, main-reachable; literal paths data/scaling_rmse.json + data/fig_scaling_rmse.png, ARTIFACTS registry, envelope schema neutron_qae.artifact v1, validate/dumps/write/load_artifact, png_dimensions, budget constants"
  - "neutron_qae/analysis.py: summarize_errors, classical_rmse_series, mlae_rmse_series, backend_rmse_series, loglog_fit, fit_series, cost_at_target"
  - "neutron_qae/figures.py: render_scaling, RENDERERS, render_file, DEFAULT_DPI/MIN_DPI/MAX_DPI, FIGSIZE_ONE/TWO, PD-30 palette constants (not reachable from main.py)"
  - "scripts/sweep_common.py (base_parser, git_state, versions, provenance, finish), scripts/sweep_scaling.py (--seed --profile --out-dir --dpi --no-aer), scripts/render_figures.py (--only --out-dir --dpi --check)"
  - "data/scaling_rmse.json (full profile, 8,353 B) and data/fig_scaling_rmse.png (770 x 506, 87,804 B): the headline RMSE-vs-cost evidence"
  - "tests/test_artifacts.py (11 committed-artifact gates) and tests/test_analysis.py (16 helper/loader edge tests)"
affects: [05-02, 05-03, phase-6, docs-02, readme]

# Actuals (#2632)
actuals:
  tokens: 18134       # chars/4 over the added lines of the realized diff c8e3c8a..HEAD, PNG excluded (72,537 chars)
  tasks: 3
  commits: 5          # measured: git rev-list --count c8e3c8a..HEAD at SUMMARY time
plan_head_before: c8e3c8acf6c59b331125da217faa740d59fb8f59
plan_head_after: 79cea3d95dc58f806552874b939d31dd5868aaeb

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Artifact = validated JSON (envelope v1, sorted keys, indent 1, no NaN, trailing newline, size-checked before parse) + PNG rendered only from that file"
    - "Literal data/ paths live in one stdlib-only module made main-reachable by one import line"
    - "Nested repetitions: one experiment per repetition observed at increasing cost (checkpoints / schedule prefixes)"
    - "Aer cross-check as ONE job with memory=True, repetitions read as shot blocks"
    - "Full-profile artifacts produced from committed code (git_dirty false), fits recomputed from stored arrays in tests"

key-files:
  created:
    - neutron_qae/artifacts.py
    - neutron_qae/analysis.py
    - neutron_qae/figures.py
    - scripts/sweep_common.py
    - scripts/sweep_scaling.py
    - scripts/render_figures.py
    - data/scaling_rmse.json
    - data/fig_scaling_rmse.png
    - tests/test_artifacts.py
    - tests/test_analysis.py
  modified:
    - main.py

key-decisions:
  - "PD-24: artifacts live under data/ as JSON + PNG (data/scaling_rmse.json, data/fig_scaling_rmse.png; 05-02 adds exit_histograms, truncation_bias, thickness_study); literal paths in stdlib-only neutron_qae/artifacts.py, reachable from main.py through one changed import line; envelope neutron_qae.artifact v1 (schema, schema_version, kind, profile, provenance, parameters, results, notes); sort_keys, indent 1, allow_nan False, trailing newline; size check before parse; parse_constant rejects NaN/Infinity; integrity = size cap + schema + seed/provenance, never a float hash"
  - "PD-25: headline = matched lattice MC vs MLAE on the 10 cm wall against exact T1; exponential schedule, 300 shots per power; analytic runner primary (M = 1..11), Aer cross-check (M = 1..9); R = 100 nested repetitions; RMSE + 16-84 percentile band of |err|; OLS log10-log10 fits, slope SE sqrt(SSR / (n - 2) / Sxx); classical all points, MLAE M >= 2; IonQ = one labelled marker, never in a fit"
  - "PD-26: seed 2026; root SeedSequence spawn(3) -> classical, analytic, aer; repetition r = <stage>.spawn(R)[r]; Aer seed_simulator = ss_aer.generate_state(1, uint32)[0] = 1818751028 in one backend.run(..., shots = R x 300, memory=True); full artifacts from committed code; never re-run with other seeds"
  - "PD-30: figures.py renders from artifact dicts only, lazy pyplot, never matplotlib.use or show, allowlisted long-standing calls, DEFAULT_DPI 110, dpi 50..200, figsize (7.0, 4.6) / (9.0, 4.0), no bbox_inches tight, the validated palette (#fcfcfb surface, #2a78d6 classical, #eb6834 MLAE analytic, #1baf7a Aer open diamonds, #0b0b0b exact, #52514e secondary/IonQ, #d9d8d4 grid)"
  - "PD-31: the default suite never runs a real sweep; micro configurations only; render test at dpi 60; suite under 30 s (measured 27.55 s)"
  - "The IonQ marker's long JSON label is drawn as text beside the X marker (ax.text), not as a legend entry, so the compact legend never covers data"

patterns-established:
  - "New artifact kind = add (JSON, PNG) to artifacts.ARTIFACTS + a _VALIDATORS entry + a figures.RENDERERS entry + a sweep script ending in sweep_common.finish"

requirements-completed: [ANLY-01, ANLY-05]

# Metrics
duration: 10min
completed: 2026-10-11
---

# Phase 5 Plan 01: Headline RMSE-vs-Cost Scaling Study Summary

**Matched lattice MC vs MLAE on the 10 cm SPARC wall at R = 100: fitted slopes -0.4977 +- 0.0052 (classical, histories), -1.0151 +- 0.0290 (analytic MLAE, applications of A) and -1.0309 +- 0.0476 (Aer cross-check), committed as a validated, provenance-stamped JSON plus a PNG re-rendered from it; the IonQ estimate is one labelled marker outside every fit.**

## Performance

- **Duration:** about 10 min (08:42Z to 08:52Z)
- **Started:** 2026-10-11T08:42:23Z
- **Completed:** 2026-10-11
- **Tasks:** 3 / 3
- **Files:** 10 created, 1 modified (main.py, one line)

## Evidence lines

- Tracer: `SCALING TRACER OK classical=-0.5094 mlae=-0.9367 png=770x506`
- Quick sweep: `SWEEP scaling_rmse profile=quick seed=2026 classical_slope=-0.5094 mlae_slope=-0.9367 aer_slope=none total_s=0.4`
- Full sweep (from clean commit cbabd4e): `SWEEP scaling_rmse profile=full seed=2026 classical_slope=-0.4977 mlae_slope=-1.0151 aer_slope=-1.0309 total_s=70.8`; timings_s classical 5.48, mlae_analytic 45.19, mlae_aer 20.0, make_problem 0.04, total 70.77; wall 71.7 s
- `HEADLINE OK {'classical_lattice': -0.4977, 'mlae_aer': -1.0309, 'mlae_analytic': -1.0151} aer/analytic [1.158, 0.963, 0.954, 0.946, 0.908, 0.974, 0.943, 0.797, 0.828]`
- `MAIN GRAPH OK ['__init__.py', 'artifacts.py', 'exact.py', 'grover.py', 'kernels.py', 'main.py', 'mlae.py', 'nuclear_data.py', 'oracle.py', 'problem.py', 'runners.py', 'smoke.py']` (no matplotlib, qiskit_aer, qiskit_algorithms, qiskit_ionq)
- `git diff --numstat 60bf3c5 -- main.py` -> `1	1	main.py`
- `RENDER CHECK OK 1`
- Full default suite: `364 passed, 5 skipped, 1 xfailed, 1 warning in 27.55s` (real 27.94 s), `git status --porcelain` unchanged
- `GOLDEN OK kernels_v1.json T1=0.24300446519524305`; frozen-file `git diff --quiet 60bf3c5 -- ...` exits 0
- `QAE TRACER OK a=0.245094 N_A=18000 hits=[262, 1000, 277, 997]` and the Phase 1 smoke `TRACER OK` still pass

## Headline numbers (data/scaling_rmse.json, profile full, seed 2026)

| Series | Cost range | Points (fit) | Slope +- SE |
|---|---|---|---|
| classical_lattice (histories) | 100 ... 1,000,000 | 13 (13) | -0.4977 +- 0.0052 |
| mlae_analytic (applications of A) | 300 ... 617,100 | 11 (10, M >= 2) | -1.0151 +- 0.0290 |
| mlae_aer (applications of A) | 300 ... 155,700 | 9 (8, M >= 2) | -1.0309 +- 0.0476 |

- Classical RMSE: 0.04319, 0.02989, 0.01815, 0.01455, 0.008893, 0.005976, 0.004632, 0.002983, 0.001939, 0.001337, 0.0009376, 0.0006816, 0.0004154
- Analytic MLAE RMSE: 0.02292, 0.009927, 0.00469, 0.004069, 0.001315, 0.0006794, 0.0003427, 0.0001901, 8.34e-05, 4.267e-05, 1.999e-05
- Aer RMSE: 0.02655, 0.009555, 0.004476, 0.00385, 0.001195, 0.0006617, 0.0003231, 0.0001515, 6.909e-05
- Aer/analytic RMSE ratios (M = 1..9): 1.158, 0.963, 0.954, 0.946, 0.908, 0.974, 0.943, 0.797, 0.828
- IonQ marker: n_A 9000, a_hat 0.228671, se 0.002245, |a_hat - T1| 0.014333, z -6.385, ks [0, 1, 2], in_fit false
- Sizes: JSON 8,353 B (budget 500,000), PNG 87,804 B (budget 400,000)
- Provenance: git_head `cbabd4e5cc29fa2958121f7054591f07db2e5181` (the `feat(05-01): Aer cross-check ...` commit), git_dirty false, argv `["--seed", "2026"]`, created_utc 2026-10-11T08:48:05Z, versions python 3.14.8 / numpy 2.5.3 / qiskit 2.5.2 / qiskit_aer 0.17.2 / matplotlib 3.11.2; aer_seed_simulator 1818751028

All numbers match the planner's scratchpad measurements to the printed digits.

## Task Commits

1. **Task 1: Tracer** - `0d7c853` (feat): artifacts/analysis/figures modules, sweep_common + sweep_scaling (quick), main.py import line, quick JSON + PNG
2. **Task 2: Full sweep** - `cbabd4e` (feat: Aer series + full profile code), `3c82b23` (fix: IonQ label beside its marker), `ae6a513` (test: full artifact + committed-artifact gates)
3. **Task 3: Edges and gates** - `79cea3d` (test): render_figures.py --check, test_analysis.py, stdlib/allowlist/backend gates

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] main.py import comment shortened to keep ruff clean**
- **Found during:** Task 1
- **Issue:** The plan's exact line (`... # noqa: F401 - artifacts holds Phase 5's literal data/ paths (Qollab loads data files by literal path)`, 160 chars) makes ruff's isort rule I001 fail on main.py, which passed ruff at 60bf3c5.
- **Fix:** Same import, shorter comment: `from neutron_qae import artifacts, mlae, oracle, runners  # noqa: F401 - data/ paths`. The why lives in the artifacts.py module docstring. Still exactly one changed line (`1 1 main.py`); the key_link pattern still matches.
- **Files modified:** main.py
- **Commit:** 0d7c853

**2. [Rule 1 - Bug] IonQ marker label overflowed the legend and the legend covered data points**
- **Found during:** Task 2 (visual check of the full figure)
- **Issue:** With the IonQ label as a legend entry, the legend (11 lines) covered the Aer diamonds at N_A 20,400 and 39,900.
- **Fix:** The X marker carries no legend entry; its JSON label is drawn beside it with `ax.text` (allowlisted), wrapped at 56 characters. The JSON was not regenerated: the PNG was re-rendered from the committed full JSON with the fixed figures.py, so the JSON's git_head stays the Aer-code commit cbabd4e as the acceptance criterion requires.
- **Files modified:** neutron_qae/figures.py
- **Commit:** 3c82b23

**3. [Ordering] backend_rmse_series and cost_at_target landed in the Task 1 commit**
- The plan adds them in Tasks 2 and 3; they were written with the rest of analysis.py and committed in 0d7c853. Their tests landed in Tasks 2 and 3 as planned. No behavioural difference.

**4. [Rule 2 - Correctness] Validator cross-checks added**
- `validate_artifact` also requires classical cost == parameters.classical_N, the MLAE series to run to mlae_M_max / aer_M_max, and no unknown series names, so a truncated or extra series cannot pass.

No test was moved behind the slow marker: the default suite measured 27.55 s, under the 28.5 s fallback threshold (new tests add about 1.5 s of call time including the matplotlib import).

## Known Stubs

None.

## Notes

- `write_artifact` creates its temporary file with `tempfile.mkstemp`, so the written JSON has mode 0600 locally; git records only the executable bit, so the committed file is unaffected.
- The legend sits lower-left; for the quick profile it overlaps part of the classical band (interim artifact only).

## Handoffs

**For 05-02:**
- Register each new kind in `artifacts.ARTIFACTS` (literal `"data/<name>"` strings in artifacts.py), add a `_VALIDATORS[kind]` function (use the `_fail`/`_int`/`_num`/`_ascending_ints`/`_num_list` helpers; ValueError messages name the dotted field), and a `figures.RENDERERS[kind]`.
- `analysis.cost_at_target(cost, rmse, target)` (first crossing, log-log interpolation, None when not bracketed), `analysis.fit_series(series, min_M)`, `analysis.mlae_rmse_series` / `classical_rmse_series` for the thickness study.
- Sweep scripts: `sweep_common.base_parser`, `sweep_common.provenance(seed, script, argv, timings)`, `sweep_common.finish(doc, kind, out_dir, dpi)`; select Agg before importing figures; commit code before the full run (git_dirty false).
- Palette constants in figures.py: SURFACE, CLASSICAL, MLAE_ANALYTIC, MLAE_AER, EXACT, SECONDARY, GRID; FIGSIZE_TWO for two-panel figures; only allowlisted matplotlib calls (test_figures_use_only_long_standing_matplotlib_api).
- tests/test_artifacts.py iterates `artifacts.ARTIFACTS`, so new kinds are gated automatically (budgets, byte-stable dumps, provenance, notes, render at dpi 60). The 5 s render budget and the suite's 30 s cap are shared.

**For 05-03 and Phase 6:**
- `figures.render_file(kind, json_path, png_path, dpi)` and `figures.RENDERERS` re-render any figure from its JSON; `scripts/render_figures.py --check` confirms committed PNGs.
- figures.py (matplotlib) is NOT reachable from main.py yet; Phase 6 decides the quick-mode wiring. artifacts.py is reachable and stdlib-only.
- The IonQ marker label already states "execution proof, 6.4 sigma off T1, cause open; not in any fit".

## Self-Check: PASSED

- FOUND: neutron_qae/artifacts.py, neutron_qae/analysis.py, neutron_qae/figures.py, scripts/sweep_common.py, scripts/sweep_scaling.py, scripts/render_figures.py, data/scaling_rmse.json, data/fig_scaling_rmse.png, tests/test_artifacts.py, tests/test_analysis.py
- FOUND commits: 0d7c853, cbabd4e, 3c82b23, ae6a513, 79cea3d (all ancestors of HEAD)
