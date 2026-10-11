---
phase: 03-classical-baseline
verified: 2026-10-10T19:00:00Z
status: passed
score: 9/9 must-haves verified
covered_files:
  - ".planning/phases/03-classical-baseline/03-01-PLAN.md"
  - ".planning/phases/03-classical-baseline/03-01-SUMMARY.md"
  - ".planning/phases/03-classical-baseline/03-02-PLAN.md"
  - ".planning/phases/03-classical-baseline/03-02-SUMMARY.md"
  - "neutron_qae/mc_continuous.py"
  - "neutron_qae/mc_lattice.py"
  - "neutron_qae/random_source.py"
  - "tests/random_doubles.py"
  - "tests/test_mc_continuous.py"
  - "tests/test_mc_lattice.py"
  - "tests/test_random_source.py"
covered_digest: "v3:sha256:202ad8327279fe9fc9b8dbe47f011ba6bd50ddc5bad3dc0e01e98f688517060f"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: Classical Baseline Verification Report

**Phase Goal:** An honest classical baseline exists: a continuous delta-tracking Monte Carlo serves as the physics reference, and a discrete lattice Monte Carlo samples exactly the `Kernels` model the circuit encodes; both are validated against analytic and exact answers and both are driven by an injected random source.
**Verified:** 2026-10-10
**Status:** passed (with one flagged judgment-tier prohibition, see below)
**Re-verification:** No, initial verification

## Goal Achievement

Verification did not rely on the SUMMARY or on the plan's own tests alone. In addition to re-running the suite, I wrote independent scripts (scratchpad, not committed) that used fresh seeds, an independent pure-Python scalar delta-tracking implementation with its own RNG, and a non-numpy-Generator source.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP SC1 / PHYS-03: seeded vectorized Woodcock delta-tracking run reports transmission, absorption, back-face exit-row histogram and collision-order breakdown, each with a standard error | VERIFIED | `neutron_qae/mc_continuous.py` `run_continuous` (loop lines 190-241): vectorized delta tracking, majorant `max(front.sigma_t, back.sigma_t)`, exit tested before collision, isotropic 2D scattering `phi = 2 pi u`, loss through back/front/lateral faces. `ContinuousResult` holds int64 read-only counts; every fraction has a binomial SE from one helper `_frac_se`. Independent run (seeds 777, 4242, n = 1e6): fate counts sum to n, `order_counts.sum() == fate_counts[BACK]`, `row_counts.sum() == fate_counts[BACK]`, `row_counts_le1.sum() == order_counts[:2].sum()` all True. Order fractions decay [0.2324, 0.0105, 0.00064, 3e-5, ...], T = 0.2435 +- 0.0004, A = 0.7219 +- 0.0004. |
| 2 | ROADMAP SC2 / PHYS-04: uncollided transmission matches e^{-tau} within SE; same seed reproduces identical histories | VERIFIED | `within(0)` vs e^{-tau_model} = 0.23256718303628812: z = -0.49 (seed 777), +0.19 (seed 4242), +0.08 (independent scalar engine). Same-seed `fate/ncol/yexit/x_first` arrays identical (`np.array_equal(..., equal_nan=True)`, seed 5, n = 20,000 in my run; plan test uses 50,000). `within(1)` vs exact T1 = 0.24300446519524305: z = -0.38, +0.02, +0.09. Contract and chunk-dependence documented in docstring and tested (`test_chunk_size_changes_histories_not_statistics`). |
| 3 | ROADMAP SC3 / PHYS-07: discrete lattice MC samples the frozen `Kernels` model and its mean converges to the exact lattice value within SE | VERIFIED | `mc_lattice.py` `run_lattice` draws x (inverse CDF over `first_collision`, cdf[-1] forced 1.0), a, phi, e sequentially from `first_collision`, `scatter_ratio`, `flight[..., BACK]`, `back_exit_rows`; layout constants from `exact.py`; x = 16 reuses column 0. Fresh-seed results at n = 1e6: z = -1.01 (seed 777), -1.57 (seed 4242); n = 2e6 seed 123: mean 0.2430125 vs T1 0.2430045. Bit-string sampling at n = 2e6: 0 samples outside the 728-string support of `bitstring_probabilities_k1`, chi2 = 765.8 over 726 dof (bound 916.5); exit-row chi2 vs `exit_row_distribution_k1` = 8.1 (bound 44.3). Planned convergence (N = 1e3..1e6) and RMSE-vs-1/sqrt(N) tests pass. |
| 4 | ROADMAP SC4 / PHYS-08: both engines take their random source as a parameter (numpy Generator by default); swapping needs no engine code change | VERIFIED | `random_source.py`: one-method `RandomSource` protocol, `as_source(None)` builds an unseeded `default_rng`, a Generator passes through unwrapped, `draw()` validates shape and range. Both engines call only `as_source` once and `draw` for every uniform. Independent swap: a legacy `np.random.RandomState` wrapper drives `run_continuous` (z1 = +0.07) and `run_lattice` (z = +1.04) unchanged; test doubles `HashCounterSource` (SHA-256) and `ScriptedSource` drive both with exact uniform-count accounting (445,741 continuous; 802,076 lattice, matching the one-flight-per-history count). AST gate `rng_violations` is applied to `neutron_qae/mc_*.py`; my grep finds `default_rng` / `np.random` in the engines only inside docstrings. |
| 5 | Physics honesty: continuous engine validated by marginal sums only; full transmission is a separate named quantity and is never tested against T1 | VERIFIED | `transmission` and `within(K)` are separate properties. Independent scalar engine: full transmission 0.24388 vs `within(1)` consistent with T1. The only `transmission`-vs-reference test comparison is the two-layer pure absorber vs e^{-tau} (legitimate: no scattering, so full = uncollided). The slow test asserts `(transmission - T1)/se > 8` to show the truncation bias is resolved. No test compares an individual Kernels entry with continuous output (grep of tests). |
| 6 | Independent physics cross-check (goal-backward: is the reference genuinely correct, not just self-consistent) | VERIFIED | A separately written scalar Python delta-tracking loop (own RNG, N = 2e5) gives `within(0)` z = +0.08 and `within(1)` z = +0.09 against e^{-tau} and exact T1, and full transmission 0.24388 agrees with the vectorized 0.2430-0.2443. |
| 7 | Edge truths: n validation, scripted never-collide / lateral / front exits, zero-count SE, chunk edges, max_iter, bad source | VERIFIED | Covered by the 209-test default suite (`test_mc_continuous.py`, `test_random_source.py`, `test_mc_lattice.py`); my spot checks: n in (0, -1, 1.5, True) raises ValueError for `run_lattice`; nx = 8 Kernels raises ValueError naming the register layout; checkpoints `(10000, 1, 2500, 2500)` with chunk 4096 normalise to `(1, 2500, 10000)` with counts `[1, 584, 2429]` (matches plan). |
| 8 | 03-02 Rule-1 deviation: `sample_exit_rows` zero-mass rows | VERIFIED | `sample_exit_rows(k, [1184, 1056, 528, 31, 5])` returns `[-1, 11, 8, -1, -1]`: string 1184 (escaped in a zero-mass bin, previously row 15) now maps to -1; 1056 gives a positive-mass row; 528 (never-collided) gives row 8; x > 16 gives -1. The engine path is unchanged (rows reproduce, chi2 8.1). Code lines 130-135 `live = cr[:, -1] > 0` confirm. |
| 9 | No regression and frozen contract: frozen modules unchanged, Phase 3 modules not reachable from `main.py`, no new dependency or data file | VERIFIED | `git diff --stat 217ab3a -- main.py neutron_qae/__init__.py smoke.py kernels.py exact.py problem.py nuclear_data.py data tests/golden` is empty; `git diff 217ab3a HEAD -- . ':!.planning'` shows only the 7 new Phase 3 files, all additions. `reachable_modules(root)` = `main.py`, `neutron_qae/__init__.py`, `neutron_qae/smoke.py`. `data/` holds only `smoke_probe.json`. `freeze_kernels.py` prints `GOLDEN OK`; `run_local.py` prints `SMOKE TEST PASSED`. |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `neutron_qae/random_source.py` | RandomSource protocol, `as_source`, `draw`; contains `runtime_checkable` | VERIFIED | 64 lines, substantive, imported by both engines (`from neutron_qae.random_source import as_source, draw`) |
| `neutron_qae/mc_continuous.py` | Woodcock MC; exports BACK/FRONT/LATERAL/ABSORBED/FATES/ContinuousResult/ContinuousHistories/run_continuous | VERIFIED | 242 lines, all exports present, wired to `problem.ProblemSpec` and `random_source` |
| `neutron_qae/mc_lattice.py` | Matched lattice MC; exports LatticeResult/run_lattice/sample_exit_rows | VERIFIED | 269 lines, all exports present, wired to `exact` layout constants, `kernels.BACK/Kernels`, `random_source` |
| `tests/random_doubles.py` | HashCounterSource, ScriptedSource, `rng_violations`, `foreign_imports` | VERIFIED | present, 89 lines |
| `tests/test_random_source.py` | PHYS-08 tests including `test_engines_never_own_randomness` | VERIFIED | present, 112 lines, passes |
| `tests/test_mc_continuous.py` | PHYS-03/04 tests including `test_uncollided_matches_exp_minus_tau` | VERIFIED | present, 298 lines, passes |
| `tests/test_mc_lattice.py` | PHYS-07 tests including `test_lattice_converges_to_exact_T1` | VERIFIED | present, 326 lines, passes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `mc_continuous.py` | `random_source.py` | `as_source` once per run, `draw` for each uniform | WIRED | import at line ~79, used in loop |
| `mc_continuous.py` | `problem.py` | `spec.front/back`, `boundary_x`, `beam_y`, `row_of` | WIRED | `spec.row_of(yexit[tb])`, material lookup at tentative site |
| `mc_lattice.py` | `exact.py` | layout constants only (X_BITS, A_BITS, PHI_BITS, E_BITS, N_BITS) | WIRED | no enumeration imported; sequential sampling |
| `mc_lattice.py` | `kernels.py` | `first_collision`, `scatter_ratio`, `flight[..., BACK]`, `back_exit_rows` | WIRED | all four tables read; no `sigma`/`tau` use found in the module code |
| `mc_lattice.py` | `random_source.py` | `as_source`, `draw` | WIRED | |
| `run_lattice` | `sample_exit_rows` | per-chunk row tally goes through the public helper | WIRED | `r = sample_exit_rows(k, bits, src)`; spy test exists |
| tests | `exact.py` | `transmission_within`, `exit_row_distribution_k1`, `bitstring_probabilities_k1` as references | WIRED | |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ContinuousResult` tallies | `fate_counts`, `order_counts`, `row_counts*` | `np.bincount` over per-history arrays filled in the delta-tracking loop from injected uniforms | Yes (independently cross-checked by scalar engine) | FLOWING |
| `LatticeResult` | `transmitted`, `row_counts`, `checkpoint_counts` | sequential draws from frozen Kernels tables | Yes (matches enumeration chi2) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Default suite | `.venv/bin/python -m pytest -q` | 209 passed, 2 skipped, 1 pre-existing warning, 2.6 s | PASS |
| Slow 1e8 checks | `NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow` | 2 passed in 15.3 s | PASS |
| Frozen golden contract | `.venv/bin/python scripts/freeze_kernels.py` | `GOLDEN OK kernels_v1.json T1=0.24300446519524305` | PASS |
| Phase 1 tracer | `.venv/bin/python scripts/run_local.py` | `SMOKE TEST PASSED` | PASS |
| Fresh-seed continuous vs e^{-tau} / T1 | independent script, seeds 777 and 4242 | z0 = -0.49 / +0.19, z1 = -0.38 / +0.02 | PASS |
| Independent scalar delta tracker | independent script, N = 2e5 | z0 = +0.08, z1 = +0.09 | PASS |
| Lattice distribution vs enumeration | independent script, n = 2e6 | 0 outside support, chi2 765.8 < 916.5; rows chi2 8.1 < 44.3 | PASS |
| Non-Generator source swap | `np.random.RandomState` wrapper | continuous z1 = +0.07, lattice z = +1.04 | PASS |

### Probe Execution

Step 7c: SKIPPED. No probe scripts are declared in the Phase 3 plans or summaries, and `scripts/*/tests/probe-*.sh` does not exist.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PHYS-03 | 03-01 | Continuous MC, vectorized, seeded, Woodcock, isotropic, loss on exit; tallies with SEs | SATISFIED | Truth 1, 6 |
| PHYS-04 | 03-01 | e^{-tau} analytic check and seed reproducibility | SATISFIED | Truth 2 |
| PHYS-07 | 03-02 | Matched lattice MC converges to exact within SE | SATISFIED | Truth 3, 8 |
| PHYS-08 | 03-01, 03-02 | Random source as a parameter, numpy Generator default, engine never owns randomness | SATISFIED | Truth 4 |

All four requirement IDs declared in the PLAN frontmatter (03-01: PHYS-03, PHYS-04, PHYS-08; 03-02: PHYS-07, PHYS-08) appear in REQUIREMENTS.md, are marked Complete in its traceability table, and match the ROADMAP Phase 3 requirement list. No orphaned requirements: REQUIREMENTS.md maps no other ID to Phase 3.

### Prohibitions

| Prohibition | Tier | Verdict |
|-------------|------|---------|
| PHYS-08: engine must not call numpy random, construct a Generator or hold a seed | test | Enforced: AST gate `test_engines_never_own_randomness` and `test_only_as_source_constructs_a_generator` pass; gate has a teeth test; my grep confirms only docstring mentions |
| PHYS-03: no fraction without SE; at-most-one transmission not presented as full transmission | test | Enforced: every fraction property has a `_se` twin from `_frac_se`; `transmission` vs `within(K)` separate and documented |
| PHYS-04: no reproducibility claim beyond contract | test | Enforced: docstring states same source state + n + chunk + numpy + platform; chunk-change test passes |
| MUST NOT change frozen files / make Phase 3 reachable from main.py / add data or dependency | test | Enforced: git diff empty for frozen set, reachable graph unchanged, data/ unchanged, pyproject untouched |
| PHYS-07: lattice derives no probability from cross sections or geometry | test | Enforced: `test_lattice_static_gates`; my grep finds no `sigma`, `tau` or `spec.front/back` use in module code |
| PHYS-07: not a categorical draw over the enumeration | test | Enforced: sequential four-register sampling; imports only layout constants from `exact.py`; my bit-string chi2 shows it still matches the enumeration, so the match is not a tautology |
| PHYS-07: no second flight chained (WR-08) | test | Enforced: exact uniform count 4n + escaped (802,076 at n = 2e5) |
| PHYS-07: cost is histories | test | Enforced: `LatticeResult.cost == n` |
| PHYS-03/04: MUST NOT validate continuous engine by full transmission vs T1 or individual Kernels entries (WR-07) | judgment | **FLAGGED: unverified-prohibition, human review recommended (non-authoritative LLM-judge verdict: not violated).** Evidence behind the verdict: the only `transmission`-vs-reference assertion in `tests/test_mc_continuous.py` is the pure-absorber case against e^{-tau} (line 175), the other use is the slow separation check asserting a gap > 8 SE; no test compares a single `flight`/`back_exit_rows` entry with continuous output (line 213 comment states sums only). The reviewer should confirm that reading. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | | `TODO/FIXME/XXX/TBD/HACK` grep over all 7 Phase 3 files returns nothing | | |

No stubs, no hardcoded-empty render paths, no console-only implementations. `return null`-style hits are absent.

### Deferred Items

None. Items the plans excluded (PHYS-09 variance reduction, K = 2, `main.py` wiring, Phase 5 sweeps, absorption split by material) are not Phase 3 must-haves.

### Human Verification Required

None required for the goal. The single judgment-tier prohibition above is flagged for optional human confirmation (autonomous completion reads "complete with 1 flagged prohibition"). If the run is interactive, treat it as one human-resolution item.

### Observations (non-blocking, informational)

- At n = 1e8 the at-most-one-collision row histogram shows chi2 about 34 (bound 44.28); the 03-01 SUMMARY attributes this to roughly 1% relative quadrature error in the two edge rows of the Kernels summed row histogram (WR-07). This is a Phase 5 hand-off (do not present edge-row residuals at huge n as an engine defect), not a Phase 3 gap, and per-row z tests remain forbidden.
- Open Question 2 (absorption split by material) was deliberately not built; PHYS-03 does not require it.
- Quick task noted in 03-02 SUMMARY: WR-07/WR-08 docstring fixes in `kernels.py` and PHYSICS.md, left until after Phase 4.
- A code review (`03-REVIEW.md`) runs in parallel and was not consulted here.

### Gaps Summary

No gaps. All four ROADMAP success criteria hold in the codebase and were confirmed by independent evidence (fresh seeds, an independently written scalar delta tracker, a non-numpy random source, a distribution check against the exact enumeration), not only by the plan's own tests. The frozen Phase 2 contract and the judged Qollab path are untouched.

---

_Verified: 2026-10-10T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
