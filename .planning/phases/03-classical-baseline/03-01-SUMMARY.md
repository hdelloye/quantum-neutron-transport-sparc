---
phase: 03-classical-baseline
plan: 01
subsystem: physics
tags: [monte-carlo, woodcock-delta-tracking, random-source-protocol, numpy, reproducibility, binomial-se]

# Dependency graph
requires:
  - phase: 02-problem-spec-kernels-contract
    provides: "frozen ProblemSpec (front/back Material, tau_x, row_of, boundary_x, beam_y), Kernels v1 (first_collision), exact.transmission_within and exit_row_distribution_k1, tests/compliance_checks.reachable_modules"
provides:
  - "neutron_qae/random_source.py: RandomSource protocol (one method random(size)), as_source (None / int / np.integer / SeedSequence -> default_rng; RandomSource -> identity; bool or other -> TypeError), validating draw (size 0 skips the source)"
  - "neutron_qae/mc_continuous.py: vectorized Woodcock delta tracking run_continuous(spec, n, source=None, *, chunk=1<<16, max_order=8, max_iter=100_000, histories=False); ContinuousResult (int64 read-only counts, every fraction with a binomial SE, within(K), row_fractions/row_se); ContinuousHistories(fate, ncol, yexit, x_first); BACK/FRONT/LATERAL/ABSORBED, FATES"
  - "tests/random_doubles.py: HashCounterSource (SHA-256 counter, 53-bit), ScriptedSource, rng_violations and foreign_imports AST gates"
  - "tests/test_random_source.py and tests/test_mc_continuous.py: 52 default tests plus one slow 1e8 check behind NEUTRON_QAE_SLOW=1"
affects: [03-02, mc-lattice, phase-4, phase-5, anly-03-truncation-bias, anly-04-thickness-study, phase-6-main]

# Actuals (#2632)
actuals:
  tokens: 8640        # chars/4 over the 5 created files (34,561 chars)
  tasks: 3
  commits: 3
plan_head_before: 5c1f099fc8d5c82e040ffdafc37fd755e9d61721
plan_head_after: 6197eb9a2a667cf6182901969eed91fbd0164065

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injected randomness: engines receive a source, call as_source once and draw(src, size) for every uniform; only as_source builds a numpy Generator (AST-gated over neutron_qae/mc_*.py)"
    - "Result dataclass with int64 read-only count arrays; fractions and binomial SEs derived once from integer counts by a single helper"
    - "Slow checks: @pytest.mark.slow plus skipif(NEUTRON_QAE_SLOW != '1'), no pyproject/conftest change"
    - "Validation by marginal sums only (within(0), within(1), <=1-collision rows, first-collision columns), fixed seeds, |z| < 4, chi2 < dof + 5 sqrt(2 dof)"

key-files:
  created:
    - neutron_qae/random_source.py
    - neutron_qae/mc_continuous.py
    - tests/random_doubles.py
    - tests/test_random_source.py
    - tests/test_mc_continuous.py
  modified: []

key-decisions:
  - "PD-08 (locked, costly): the random-source protocol is one structural method random(size) -> float64 (size,) in [0, 1); a numpy Generator satisfies it unwrapped; as_source(None | int | np.integer | SeedSequence | source) is the only Generator constructor; draw() validates shape and range. Phases 4-6 call this seam."
  - "PD-09 (locked): continuous engine = Woodcock delta tracking vectorized in chunks of 2^16, majorant max(front.sigma_t, back.sigma_t), cross sections from spec.front/back (never Kernels), material at the tentative site (half-open), exit tested before collision, corner ties to the x face, isotropic 2D phi = 2 pi u, int64 tallies with binomial SEs computed once, max_iter guard."
  - "PD-11 (locked): validation compares sums only (within(0) vs e^-tau, within(1) vs T1, <=1-collision row histogram, first-collision column histogram); never the full transmission vs T1, never individual Kernels entries (WR-07). Fixed seeds, |z| < 4, chi2 < dof + 5 sqrt(2 dof)."
  - "PD-12 (locked): reproducibility contract = same source state + same n + same chunk + same numpy version and platform; draw order documented in the docstring; a different chunk gives different, equally valid histories (stated and tested)."
  - "PD-14 (locked): no edit to main.py, __init__.py, kernels.py, exact.py, problem.py, nuclear_data.py, smoke.py, data/, tests/golden/; no new dependency or data file; 1e8 checks behind @pytest.mark.slow + NEUTRON_QAE_SLOW=1. Open Question 2 (absorption split by material) not implemented: it needs a new result field and tally and PHYS-03 does not ask for it; recorded for a later quick task."

patterns-established:
  - "Engine RNG gate: rng_violations(path) over every neutron_qae/mc_*.py, so 03-02's mc_lattice.py is covered automatically"
  - "Scripted single histories (ScriptedSource) pin fate, ncol, yexit, x_first and uniforms consumed exactly"

requirements-completed: [PHYS-03, PHYS-04, PHYS-08]

coverage:
  - id: D1
    description: "Seeded vectorized delta-tracking run reports transmission, absorption, front reflection, lateral leakage, collision-order breakdown and exit-row histograms, each with a binomial SE from int64 counts"
    requirement: PHYS-03
    verification:
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_tallies_and_standard_errors"
        status: pass
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_pure_absorber_two_layer"
        status: pass
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_pure_scatterer_conserves"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uncollided transmission matches e^-tau, at-most-one-collision transmission matches exact T1 (default, isotropic_raw, widths 6/15/20 cm), marginal sums match the kernels, slow 1e8 check passes"
    requirement: PHYS-04
    verification:
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_uncollided_matches_exp_minus_tau"
        status: pass
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_le1_transmission_matches_exact_T1"
        status: pass
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_marginal_sums_match_kernels"
        status: pass
      - kind: other
        ref: "NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow tests/test_mc_continuous.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Same seed + n + chunk reproduces identical per-history arrays; int seed equals default_rng(seed); a different chunk changes histories but not statistics"
    requirement: PHYS-04
    verification:
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_same_seed_reproduces_histories"
        status: pass
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_chunk_size_changes_histories_not_statistics"
        status: pass
    human_judgment: false
  - id: D4
    description: "Random source is a parameter (default unseeded numpy Generator); a SHA-256 counter source drives the unchanged engine; engines never own randomness (AST gate); only as_source constructs a Generator"
    requirement: PHYS-08
    verification:
      - kind: unit
        ref: "tests/test_mc_continuous.py#test_swap_source_without_engine_change"
        status: pass
      - kind: unit
        ref: "tests/test_random_source.py#test_engines_never_own_randomness"
        status: pass
      - kind: unit
        ref: "tests/test_random_source.py#test_only_as_source_constructs_a_generator"
        status: pass
    human_judgment: false
  - id: D5
    description: "Judged Qollab path and frozen Phase 2 contract untouched (MAIN GRAPH UNCHANGED, git diff vs 217ab3a clean, GOLDEN OK, Phase 1 TRACER OK)"
    verification:
      - kind: other
        ref: "git diff --quiet 217ab3a -- main.py neutron_qae/__init__.py neutron_qae/smoke.py neutron_qae/kernels.py neutron_qae/exact.py neutron_qae/problem.py neutron_qae/nuclear_data.py data tests/golden"
        status: pass
      - kind: other
        ref: ".venv/bin/python scripts/freeze_kernels.py"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-10-11
status: complete
---

# Phase 3 Plan 01: Random Source and Continuous Delta-Tracking MC Summary

**Vectorized Woodcock delta-tracking MC on the frozen SPARC spec, driven through a one-method injected RandomSource, matching e^-tau and the exact T1 within 4 SE (and to the planner's measured digits) with integer tallies and binomial SEs on every fraction**

## Performance

- **Duration:** about 5 min
- **Started:** 2026-10-11T00:47:01Z
- **Completed:** 2026-10-11T00:52:00Z
- **Tasks:** 3 (all committed)
- **Files created:** 5 (no existing file modified)

## Accomplishments

- Tracer line, identical to the planner's measurement: `CONTINUOUS TRACER OK T=0.243590+-0.000429 A=0.721956+-0.000448 z0=-0.30 z1=-0.24`. The prototype draw order is preserved exactly.
- `HashCounterSource` (SHA-256, not numpy) drives the unchanged engine at n = 200,000 and consumes exactly 445,741 uniforms. The AST gate prints `RNG GATE OK ['mc_continuous.py']`, and `default_rng` appears only inside `as_source`.
- Every Task 3 measurement reproduced the planner's numbers digit for digit:
  - pure absorber z = -0.25, fates [92960, 0, 0, 307040]
  - pure scatterer [80720, 55212, 64068, 0], 20 iterations
  - isotropic_raw z1 = +1.49
  - widths 6 / 15 / 20 cm give (z0, z1) = (-1.19, -1.51) / (-1.94, -1.57) / (-0.77, -0.69)
  - seed-99 row chi2 14.1 (bound 44.28) and column chi2 16.1 (bound 46.15)
- Slow 1e8 check (seed 11, 10.3 s): `z1=+0.80 z0=+1.02 row_chi2=34.4 separation=17.2 SE`. The K = 1 truncation bias is resolved, which is why the full transmission is never tested against T1.
- Default suite: **163 passed, 1 skipped in 1.9 s** (111 pre-existing + 52 new; the slow check is the skip). `git status --porcelain` is unchanged by the run, the main import graph is unchanged (`['__init__.py', 'main.py', 'smoke.py']`), freeze_kernels prints `GOLDEN OK`, the Phase 1 tracer prints `TRACER OK`, and `data/` holds only `smoke_probe.json`.

## Task Commits

1. **Task 1: Tracer, seeded source -> continuous delta tracking -> within(0) = e^-tau and within(1) = T1**: `b281f8a` (feat)
2. **Task 2: Random-source protocol hardening, doubles, RNG gate, swapped and scripted sources**: `18ef11a` (test)
3. **Task 3: Continuous physics edges, analytic layers, thicknesses, marginal sums, chunk and input edges, slow 1e8 check**: `6197eb9` (test)

## Files Created/Modified

- `neutron_qae/random_source.py`: the PHYS-08 seam (`RandomSource`, `as_source`, `draw`), numpy + stdlib only.
- `neutron_qae/mc_continuous.py`: `run_continuous`, `ContinuousResult`, `ContinuousHistories` and the fate constants. The docstring covers the draw order, the reproducibility contract and the three transmissions. The prototype loop (lines 33-80) is copied verbatim.
- `tests/random_doubles.py`: test-only doubles (copied from the prototype) and the `rng_violations` / `foreign_imports` gates.
- `tests/test_random_source.py`: 12 tests covering protocol, coercion, draw validation (5 parametrized cases plus zero-size), the RNG gate and its teeth test, the as_source-only check and the hash double's sanity.
- `tests/test_mc_continuous.py`: 40 default tests plus 1 slow test, covering the tracer, tallies/SE, reproducibility, swap/unseeded/scripted/bad sources, analytic layers, isotropic_raw, thicknesses, marginals, row binning, chunks, max_order, max_iter and input validation.

## Decisions Made

PD-08, PD-09, PD-11, PD-12 and PD-14 were implemented as written in the plan (see `key-decisions`). Open Question 2, the absorption split by material, was not implemented (reason under PD-14).

Small implementation choices inside the plan's latitude:
- `as_source` also rejects `np.bool_`.
- `within(K)` accepts `np.integer` and rejects floats and K > max_order.
- `transmission` and the other fraction properties return Python floats.

## Deviations from Plan

None. The plan was executed as written, and no package fix was needed: every test passed against the copied prototype logic. Test layout differs slightly from the plan's wording:
- The draw-validation checks are a 5-case parametrized test, with the zero-size behaviour in its own `test_draw_zero_size_skips_source`.
- The `run_continuous("spec", 10)` TypeError check is its own `test_non_spec_raises_type_error`.

Both are more granular than the plan, with the same assertions.

## Issues Encountered

None. One pre-existing UserWarning from `tests/test_smoke.py` (noise_model option) is unrelated to this plan.

## Handoffs

- **Phase 5 (exit-histogram figures): 1e8 edge-row finding.** At n = 1e8 the at-most-one-collision row histogram has chi2 = 34.4 at seed 11 (16.7 at seed 13, planner run). Row 0 pooled over both runs (2e8 histories) sits at z = -2.9. The cause is about 1% relative quadrature error in the two edge rows of the kernels' summed row histogram (WR-07), about 3e-6 absolute, which only shows at 1e8 or more histories. The fixed-seed chi2 bound of 44.28 holds. Per-row z tests stay forbidden. Exit-histogram figures should not present edge-row residuals at very large n as an engine defect.
- **For 03-02:** `as_source` and `draw` (package), plus `HashCounterSource`, `ScriptedSource`, `rng_violations` and `foreign_imports` (`tests/random_doubles.py`), are ready. The RNG gate globs `neutron_qae/mc_*.py`, so `mc_lattice.py` is covered automatically. `test_engines_never_own_randomness` also checks `foreign_imports` for every engine.
- **For Phase 5 ANLY-03 / ANLY-04:** `transmission` (all orders) and `within(K)` are separate named quantities with SEs. `sparc_first_wall(width_x=w)` is validated at 6, 15 and 20 cm.

## User Setup Required

None.

## Next Phase Readiness

Ready for 03-02 (matched lattice MC). Phase 3 success criteria 1, 2 and 4 (continuous half) are met.

## Self-Check: PASSED
