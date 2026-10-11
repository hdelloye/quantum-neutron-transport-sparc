---
phase: 03-classical-baseline
plan: 02
subsystem: physics
tags: [monte-carlo, matched-lattice, kernels-v1, numpy, random-source-protocol, phase5-hooks, binomial-se]

# Dependency graph
requires:
  - phase: 02-problem-spec-kernels-contract
    provides: "frozen Kernels v1 (first_collision, scatter_ratio, flight[..., BACK], back_exit_rows), exact.py layout constants, bitstring_probabilities_k1, exit_row_distribution_k1, transmission_within"
  - phase: 03-classical-baseline (03-01)
    provides: "as_source / draw (PHYS-08 seam), HashCounterSource, ScriptedSource, rng_violations, foreign_imports, RNG gate globbing neutron_qae/mc_*.py"
provides:
  - "neutron_qae/mc_lattice.py: run_lattice(k, n, source=None, *, chunk=1 << 16, return_bitstrings=False, checkpoints=()) sampling x, a, phi, e sequentially from the frozen tables (one flight per history, WR-08)"
  - "LatticeResult: n, transmitted, mean, se, cost (= n histories), row_counts, row_fractions, row_se, bitstrings, checkpoints, checkpoint_counts, prefix_estimates() -> (Ns, means, ses), chunk"
  - "sample_exit_rows(k, bitstrings, source=None): the engine's own row sampler, public for Phase 5 (Q1 counts -> rows)"
  - "tests/test_mc_lattice.py: 46 default tests plus one slow 1e8 check behind NEUTRON_QAE_SLOW=1"
affects: [phase-5, anly-01-rmse-curve, anly-02-exit-histogram, anly-04-thickness-study, phase-6-main]

# Actuals (#2632)
actuals:
  tokens: 6590        # chars/4 over the 2 created files (26,362 chars)
  tasks: 3
  commits: 3
plan_head_before: 12e9fd5dd89466cde2f636df6ea7392dd108744c
plan_head_after: cd3bbe72ed20f4dd85b69ee2a497914b42875d64

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Matched sampling: the four Q1 registers drawn sequentially from the frozen tables, bit layout from exact.py constants, never a categorical draw over the enumeration"
    - "Checkpointed prefix counts recorded inside the chunk loop (no per-history flags stored)"
    - "One shared helper (sample_exit_rows) for engine row tallies and for hardware bit strings"

key-files:
  created:
    - neutron_qae/mc_lattice.py
    - tests/test_mc_lattice.py
  modified: []

key-decisions:
  - "PD-10 (locked): the lattice engine samples the four registers sequentially from the frozen tables (x by inverse CDF over first_collision with cdf[-1] = 1.0, a, phi = min(floor(16u), 15), e), never a categorical draw over the 2^11 enumeration; x = 16 reuses column 0; one flight per history (WR-08); layout constants from exact.py; escaped rows by inverse CDF of back_exit_rows[col, phi] scaled by its own total and clamped to ny - 1."
  - "PD-13 (locked): Phase 5 hooks are explicit: checkpoints= gives cumulative transmitted counts at several N in one run, sample_exit_rows(k, bitstrings, source) is public and shared with the engine, LatticeResult carries SEs, and the classical cost is N = histories (one k = 0 application of A measured once), exposed as LatticeResult.cost."
  - "Open Question 1 resolved: kernels.py untouched; the WR-08 caveat lives in the mc_lattice module docstring; the kernels.py / PHYSICS.md docstring fixes (WR-07, WR-08) are left for a quick task after Phase 4."
  - "sample_exit_rows maps zero-amplitude strings to -1 without drawing: x > 16, and escaped strings (a = 1, e = 1) in one of the 168 of 256 (column, direction) bins with no back-face mass. The engine never produces either kind, so its stream is unchanged."

patterns-established:
  - "Phase 5 classical curve: RMSE over SeedSequence(seed).spawn(R) repetitions, checkpoints for several N per repetition (prefixes are nested and correlated within one repetition)"

requirements-completed: [PHYS-07, PHYS-08]

coverage:
  - id: D1
    description: "Matched lattice MC on the frozen Kernels converges to the exact T1 within 4 SE at N = 1e3..1e6 and at three other wall thicknesses, and its RMSE over 100 spawned repetitions tracks sqrt(T1 (1 - T1) / N)"
    requirement: PHYS-07
    verification:
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_lattice_converges_to_exact_T1"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_rmse_tracks_one_over_sqrt_n"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_other_wall_thicknesses_match_exact"
        status: pass
      - kind: other
        ref: "NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow tests/test_mc_lattice.py tests/test_mc_continuous.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sampled bit strings equal the enumeration (zero samples outside the 728-string support, chi2 within bound); exit rows equal exit_row_distribution_k1; the static gate shows no cross-section, optical-depth or enumeration use"
    requirement: PHYS-07
    verification:
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_bitstring_distribution_matches_enumeration"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_exit_rows_match_exact_distribution"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_lattice_static_gates"
        status: pass
    human_judgment: false
  - id: D3
    description: "Lattice engine takes its random source as a parameter; a SHA-256 counter source drives it unchanged with exactly 4 n + escaped uniforms (one flight per history); RNG gate covers both engines"
    requirement: PHYS-08
    verification:
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_swap_source_without_engine_change"
        status: pass
      - kind: unit
        ref: "tests/test_random_source.py#test_engines_never_own_randomness"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_unseeded_default_source_runs"
        status: pass
    human_judgment: false
  - id: D4
    description: "Phase 5 hooks: checkpoints / prefix_estimates, shared sample_exit_rows (contract, edges, never a zero-mass row), cost = histories, SEs"
    requirement: PHYS-07
    verification:
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_checkpoints_are_prefix_counts"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_sample_exit_rows_contract"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_sample_exit_rows_row_edges"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_sample_exit_rows_never_zero_mass"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_run_lattice_uses_shared_row_sampler"
        status: pass
      - kind: unit
        ref: "tests/test_mc_lattice.py#test_cost_is_histories"
        status: pass
    human_judgment: false
  - id: D5
    description: "Judged Qollab path and frozen contract untouched (MAIN GRAPH UNCHANGED, git diff vs 217ab3a clean, GOLDEN OK, Phase 1 TRACER OK, git status unchanged by the suite)"
    verification:
      - kind: other
        ref: "git diff --quiet 217ab3a -- main.py neutron_qae/__init__.py neutron_qae/smoke.py neutron_qae/kernels.py neutron_qae/exact.py neutron_qae/problem.py neutron_qae/nuclear_data.py data tests/golden"
        status: pass
      - kind: other
        ref: ".venv/bin/python scripts/freeze_kernels.py"
        status: pass
    human_judgment: false

# Metrics
duration: 27min
completed: 2026-10-11
status: complete
---

# Phase 3 Plan 02: Matched Lattice MC and Phase 5 Hooks Summary

**A sequential four-register sampler on the frozen Kernels v1 tables, driven by the injected random source. Its bit strings match the 2^11 enumeration, its mean converges to the exact T1 at the planner's measured digits, and it gives Phase 5 checkpointed prefix estimates, a shared row sampler and the classical cost in histories.**

## Performance

- **Duration:** about 27 min
- **Started:** 2026-10-11T00:57:31Z
- **Completed:** 2026-10-11T01:24:27Z
- **Tasks:** 3 (all committed)
- **Files created:** 2 (no existing file modified)

## Accomplishments

- The tracer line is identical to the planner's: `LATTICE TRACER OK T=0.243002+-0.000429 z=-0.01 prefix=0.2580,0.2475,0.2428`. The prototype's draw order is preserved exactly.
- Every planner measurement reproduced digit for digit:
  - convergence at seed 2026, N = 1e3, 1e4, 1e5, 1e6: z = +1.58, +1.09, +0.14, -0.01
  - bit strings at seed 3, n = 4e6: 0 samples outside the 728-string support, chi2 665.4 (bound 917.7)
  - exit rows at seed 4, n = 1e6: chi2 17.4 (bound 44.28)
  - RMSE over spawned repetitions: 0.01264 against a theoretical 0.01356 (N = 1e3), and 0.00474 against 0.00429 (N = 1e4)
  - `HashCounterSource(b"x")` at n = 2e5: z = -0.52, using exactly 802,076 uniforms (= 4 n + scattered-and-escaped histories, so one flight per history)
  - checkpoints at seed 9: [1, 584, 2429]
  - wall widths 6 / 15 / 20 cm: z = -0.70 / +0.82 / -1.24
- Slow 1e8 check (seed 12): `mean=0.2430199 z=+0.36 row_chi2=25.8`. The explicit slow run reports 2 passed (lattice and continuous) in 14.9 s.
- Default suite: **209 passed, 2 skipped in 2.5 s** (3 s wall). That is 163 tests from before plus 46 new; the two skips are the slow checks. The run leaves `git status --porcelain` unchanged.
- The RNG gate prints `RNG GATE OK ['mc_continuous.py', 'mc_lattice.py']`.
- Regression checks:
  - `MAIN GRAPH UNCHANGED ['__init__.py', 'main.py', 'smoke.py']`
  - frozen files identical to 217ab3a
  - `GOLDEN OK kernels_v1.json T1=0.24300446519524305`
  - Phase 1 `TRACER OK`
  - `data/` holds only `smoke_probe.json`

## ROADMAP Phase 3 success criteria

1. Continuous delta-tracking MC with tallies and SEs (PHYS-03): `test_mc_continuous.py::test_tallies_and_standard_errors`, `test_pure_absorber_two_layer`, `test_pure_scatterer_conserves` (03-01).
2. The continuous engine matches e^-tau and T1 and is reproducible (PHYS-04): `test_uncollided_matches_exp_minus_tau`, `test_le1_transmission_matches_exact_T1`, `test_same_seed_reproduces_histories` (03-01).
3. The matched lattice MC samples the Kernels model and converges within SE (PHYS-07): `test_mc_lattice.py::test_bitstring_distribution_matches_enumeration`, `test_lattice_converges_to_exact_T1`, `test_rmse_tracks_one_over_sqrt_n`, `test_exit_rows_match_exact_distribution`.
4. The random source is a parameter for both engines (PHYS-08): `test_mc_continuous.py::test_swap_source_without_engine_change`, `test_mc_lattice.py::test_swap_source_without_engine_change`, `test_random_source.py::test_engines_never_own_randomness`.

## Task Commits

1. **Task 1: Tracer, frozen Kernels -> matched lattice sampler -> mean converges to exact T1, with checkpoints and the shared row sampler**: `04666f5` (feat)
2. **Task 2: Distributions equal the enumeration, swapped source with one-flight accounting, static gates, reproducibility, validation**: `bfc51e5` (test)
3. **Task 3: Phase 5 hooks and edges, checkpoints, sample_exit_rows contract, cost, thicknesses, slow 1e8 check (plus the row-sampler fix)**: `cd3bbe7` (test)

## Files Created/Modified

- `neutron_qae/mc_lattice.py`: `run_lattice`, `LatticeResult` and `sample_exit_rows`. Imports only numpy, `exact`'s layout constants, `kernels.BACK`/`Kernels` and `random_source`. The docstring covers matched mode, the register table, the WR-08 caveat, draw order and reproducibility, the classical cost and the Phase 5 hooks.
- `tests/test_mc_lattice.py`: 46 default tests plus 1 slow test (tracer, distributions, swap, gates, reproducibility, validation, checkpoints, row-sampler contract and edges, thicknesses, partial chunks, 1e8).

## Decisions Made

PD-10 and PD-13 were implemented as written, and Open Question 1 was resolved as planned (see `key-decisions`). Choices made within the plan's latitude:
- `LatticeResult.bitstrings` is stored read-only, like the count arrays.
- The wrong-layout check is its own test, `test_wrong_layout_raises`, rather than one case of the parametrized validation test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `sample_exit_rows` placed zero-amplitude escaped strings in a zero-mass row**
- **Found during:** Task 3 (row-sampler contract)
- **Issue:** An escaped string (x < 16, a = 1, e = 1) whose (column, direction) bin has no back-face mass (168 of the 256 bins, where `flight[..., BACK] == 0`) has zero amplitude in the ideal circuit, but noisy IonQ counts can contain it. Its cumulative row total is 0, so the inverse CDF counted all 16 rows and the clamp put the string in row 15, a zero-mass row (string 1184 -> 15). This broke the plan's "never a zero-mass row" contract.
- **Fix:** Such strings now map to -1 without drawing a uniform, the same treatment as x > 16. The engine never produces them, because e = 1 requires u < flight[..., BACK] = 0, so the engine's stream and every measured number are unchanged. The docstring documents both zero-amplitude kinds.
- **Files modified:** neutron_qae/mc_lattice.py
- **Verification:** `test_sample_exit_rows_never_zero_mass` (every live bin samples only positive-mass rows; all 168 x 50 dead-bin strings give -1). The tracer line and all seeds reproduce exactly after the fix.
- **Committed in:** `cd3bbe7`

---

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** This makes Phase 5 hardware-count handling correct and does not change the engine. No scope creep.

## Issues Encountered

None. The pre-existing UserWarning from `tests/test_smoke.py` (noise_model option) is unrelated to this plan.

## Handoffs

- **Phase 5 ANLY-01 (classical RMSE vs N):**
  - The classical cost is N = histories (`LatticeResult.cost`). Compare it against N_A = sum over the schedule of shots * (2k + 1).
  - Compute RMSE over `np.random.SeedSequence(seed).spawn(R)` repetitions. Use `checkpoints=` for several N per repetition; those prefixes are nested within one repetition.
  - The expected curve is 0.4289 / sqrt(N).
- **Phase 5 ANLY-02 (exit histogram):**
  - `sample_exit_rows(k, [int(key, 2) for each shot], source)` turns Q1 counts into rows with the engine's own code.
  - Zero-amplitude strings (x > 16, or escaped in a zero-mass bin) come back as -1. Report how many there were; do not drop them silently.
  - The 1e8 edge-row finding from 03-01 still applies: about 1% relative quadrature error in the edge rows (WR-07) shows only at 1e8 histories or more.
- **ANLY-03:** the truncation bias is the continuous engine's `transmission` minus `within(1)` (03-01).
- **ANLY-04 (thickness study):** `sparc_first_wall(width_x=w)` with nx = 16 is validated at 6, 15 and 20 cm for both engines. A spec with nx != 16 or n_dir != 16 raises ValueError (11-bit layout).
- **Quick task after Phase 4:** WR-07 / WR-08 docstring fixes in `kernels.py` and PHYSICS.md.

## User Setup Required

None.

## Next Phase Readiness

Phase 3 is complete: success criteria 1-4 are met with the tests listed above, and Phase 5 can import every hook it needs.

## Self-Check: PASSED
