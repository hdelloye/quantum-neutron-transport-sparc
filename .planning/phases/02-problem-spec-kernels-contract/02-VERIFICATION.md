---
phase: 02-problem-spec-kernels-contract
verified: 2026-10-10T23:10:00Z
status: passed
score: 4/4 roadmap truths verified (plus 15/15 plan-level truths and 9/9 prohibitions)
covered_files:
  - .planning/phases/02-problem-spec-kernels-contract/02-01-PLAN.md
  - .planning/phases/02-problem-spec-kernels-contract/02-01-SUMMARY.md
  - .planning/phases/02-problem-spec-kernels-contract/02-02-PLAN.md
  - .planning/phases/02-problem-spec-kernels-contract/02-02-SUMMARY.md
  - README.md
  - docs/PHYSICS.md
  - neutron_qae/exact.py
  - neutron_qae/kernels.py
  - neutron_qae/nuclear_data.py
  - neutron_qae/problem.py
  - scripts/derive_cross_sections.py
  - scripts/freeze_kernels.py
  - tests/golden/kernels_v1.json
  - tests/test_exact.py
  - tests/test_kernels_contract.py
  - tests/test_kernels_golden.py
  - tests/test_nuclear_data.py
  - tests/test_physics_doc.py
  - tests/test_problem.py
covered_digest: "v3:sha256:9b2b3415afdc78396bf9272a1013d81edee6462310040ab99c99be8e004938ad"
behavior_unverified: 0
overrides_applied: 0
coincidental_reliance_items:
  - truth: "Exit-row / K=1 values frozen on the transport-corrected model"
    reason: fixture-only
    harden: "Advisory only: the golden file records the model name and spec fingerprint, so a model switch is detected; nothing to fix for contract v1."
---

# Phase 2: Problem Spec & Kernels Contract Verification Report

**Phase Goal:** The SPARC first-wall problem is defined exactly once with sourced 14 MeV cross sections, and the frozen `Kernels` contract plus the exact "transmission within K collisions" value exist, so classical and quantum work can proceed independently against the same ground truth.
**Verified:** 2026-10-10T23:10:00Z
**Status:** passed
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths (ROADMAP success criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1 / PHYS-01: `ProblemSpec` = 10x10 cm, 16x16, 2.0 cm WHA + 8.0 cm SS316; boundary inside column 4 handled, not snapped | VERIFIED | `problem.py` `ProblemSpec`/`column_segments`. Run live: `column_segments(3) == [(1.875, 2.0, WHA), (2.0, 2.5, SS316)]`; `tau_x` integrates 0.125*Sigma_WHA + 0.5*Sigma_SS316; test `test_boundary_inside_roadmap_column_4_is_not_snapped` asserts it differs from both snapped values by >1e-3 and checks `scatter_ratio[3]` closed form. Half-open `material_at(2.0)` is SS316. Degenerate geometry raises ValueError (checked boundary_x 0/10, beam_y 0, nx 0). 0-based index 3 = roadmap's 1-based column 4, documented in code, tests and PHYSICS.md. |
| 2 | SC2 / PHYS-02: every one-group 14 MeV cross section (total, scattering, absorption incl. non-elastic) for both materials cited in code and docs with ENDF/B-VIII.0 source and evaluation date | VERIFIED | `nuclear_data.py`: `LIBRARY` (ENDF/B-VIII.0, 2018-02-02, Brown et al. NDS 148, 1), `MICRO_14MEV` for 10 elements, `PROVENANCE` 36 isotope rows (MAT, verbatim evaluation string, date). I spot-checked 5 isotopes (W-183, W-184, Fe-56, Ni-58, Mo-92) against the raw ENDF headers in the scratchpad: MAT numbers and evaluation strings match. Removal `Sigma_a = Sigma_t - Sigma_s` = 0.15673 / 0.12147 per cm (n,2n counted once). `docs/PHYSICS.md` has 10 element rows, 36 isotope rows (`grep` = 36), material sources and the three-model bias table; `tests/test_physics_doc.py` re-reads every row against code. `scripts/derive_cross_sections.py --endf-dir ... --check` re-run by me: `MICRO_14MEV REPRODUCED (max rel dev 2.72e-06, max n2n abs dev 4.05e-05)`. |
| 3 | SC3 / PHYS-05: `Kernels` built from `ProblemSpec` exposes first-collision column distribution, scatter ratio per column, escape per column and direction; probability conserved; dataclass frozen as the one contract | VERIFIED | `kernels.py`: `@dataclass(frozen=True, eq=False)`, four tables as private read-only float64 copies, shape-checked in `__post_init__`. Live: `fsum(first_collision)` = 1.0; `flight.sum(-1)` max dev 4.4e-16; `back_exit_rows.sum(-1) - flight[...,BACK]` max 1.2e-15; all entries >= 0, ratios in [0,1]; backward bins 4-11 have BACK exactly 0, bins 0,1,14,15 > 0; mirror symmetry 4.4e-16 / 1.1e-16; item assignment raises ValueError; attribute rebinding raises FrozenInstanceError. Golden `tests/golden/kernels_v1.json` (67,831 B < 2 MB) compared at rtol 1e-12; `freeze_kernels.py` prints `GOLDEN OK`; `--write` without `--force` exits 2 and the golden sha256 is unchanged (350474b3...). |
| 4 | SC4 / PHYS-06: exact solver enumerates every random-bit string and returns exact transmission within K collisions | VERIFIED | `exact.py` loops over all 2^11 strings (1088 kept, probabilities sum to 1.0) and returns `math.fsum` of transmitted strings. T0 = 0.23256718303628812 and T1 = 0.24300446519524305, digit-for-digit equal to RESEARCH references; T0 equals `exp(-tau)`; `exit_row_distribution_k1` sums to T1 (dev 3e-17). K in {-1, 2, 1.5} raises ValueError containing "contract v1"; nx != 16 raises. Independent check I wrote (analog continuous-geometry MC with 4e6 histories, not using the Kernels tables): T1_MC = 0.24291 +- 0.00021, z = -0.44, uncollided 0.23241 vs T0 0.23257. The enumerated value is physically consistent with the model, not just self-consistent. |

**Score:** 4/4 roadmap truths verified, 0 behavior-unverified.

### Plan-level must-haves (02-01 and 02-02 frontmatter)

All 15 truths in 02-01 and 7 in 02-02 were checked; none reduced the roadmap scope. Highlights re-confirmed by running code or reading source:

| Truth | Status | Evidence |
|-------|--------|----------|
| Tracer T0/T1/c[3] equal research reference (T0 0.23256718303628812, T1 0.24300446519524305, c[3] 0.11850355190070459) | VERIFIED | Printed by my own script, exact repr match |
| Fingerprint: stable across calls; differs for `isotropic_raw` and `width_x=20` | VERIFIED | live |
| Row rule: y=5.0 -> 8, 4.9999 -> 7, 10.0 -> 15, 0.0 -> 0 | VERIFIED | live |
| x = 16 mirrors column 0 (circuit-consistent) | VERIFIED | `exact.py` uses `col = x % nx`; source read |
| Register layout little-endian `x | a<<5 | phi<<6 | e<<10` in `REGISTER_LAYOUT` and golden | VERIFIED | source + `test_golden_metadata` |
| Golden tamper negative test (1e-9 perturbation, fingerprint, version) | VERIFIED | `test_tampered_golden_is_detected` read and passing |
| No Qollab regression: main.py/`__init__`/smoke.py/data unchanged since 34a827a; `git status` unchanged by test run; Phase 1 tracer passes | VERIFIED | `git diff --stat 34a827a -- main.py neutron_qae/__init__.py neutron_qae/smoke.py data` empty; `run_local.py` prints SMOKE TEST PASSED; `git status --porcelain` shows only the 3 pre-existing `.planning` files before and after; main.py imports only `neutron_qae.smoke` |
| Doc: honest labels (model uncollided T0 = 0.2325671830 vs physical uncollided 0.0867), T1 and K=1 coverage 0.997/0.899, contract section, change procedure | VERIFIED | PHYSICS.md lines 127-136, 171-181; I recomputed exp(-tau_t) = exp(-(2*0.33089+8*0.22287)) = 0.0867 |
| README pointers (PHYSICS.md, KERNELS_CONTRACT_VERSION, tests/golden/) and no contract change from 02-02 | VERIFIED | README lines 11, 59-60, 72; golden sha unchanged, `GOLDEN OK` |

### Prohibitions (ADR-550 D3/D4)

| Prohibition | Tier | Status | Evidence |
|-------------|------|--------|----------|
| No snapping of interface / one material per column | test | VERIFIED | column-4 test, `column_segments`, boundary-on-edge test |
| Geometry and cross-section numbers only in nuclear_data.py / problem.py | judgment | VERIFIED (non-authoritative judge verdict: grep of main.py, smoke.py, `__init__.py` for 18.5, 0.1712, 5.367, boundary_x, 2.0 found nothing; kernels.py and exact.py read geometry from `spec`) | No unresolved flag; human review optional |
| No cross section without MAT + evaluation string + date | test | VERIFIED | `test_provenance_covers_every_isotope`; 36 rows; headers spot-checked |
| No file/network read of nuclear data; contract modules import only numpy/stdlib/neutron_qae | test | VERIFIED | modules read; constants in code; `data/` holds only smoke_probe.json; AST allowlist test passing |
| Kernels not mutable/aliased; quadrature fixed at (24, 48) | test | VERIFIED | live mutation attempts raise; golden records quadrature |
| Golden not regenerated silently | test | VERIFIED | `--write` exits 2, sha unchanged |
| main.py unchanged / new modules not reachable | test | VERIFIED | git diff empty; main import graph is smoke only |
| T_K by literal enumeration, not sampling or closed form alone | test | VERIFIED | `exact.py` loops 2048 strings + `math.fsum`; closed form only in tests |
| No silent K=2 truncation | test | VERIFIED | ValueError for K in {-1, 2, 1.5} |
| 02-02: no doc cross section without source; both uncollided numbers labelled; derive script local-only, no eval; docs do not redefine the contract | test | VERIFIED | `test_physics_doc.py` (9 tests) + my replication run |

No flagged (unverified) prohibitions.

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `neutron_qae/nuclear_data.py` | VERIFIED | 117 lines, constants with citations, wired into `problem.py` (`nd.MICRO_14MEV`, `nd.WHA_97W`, `nd.SS316`) |
| `neutron_qae/problem.py` | VERIFIED | 185 lines, `row_of` present, wired to kernels via `spec.column_segments`, `spec.tau_x`, `spec.row_of` |
| `neutron_qae/kernels.py` | VERIFIED | `KERNELS_CONTRACT_VERSION = "1"`, frozen, wired from exact.py |
| `neutron_qae/exact.py` | VERIFIED | `math.fsum`, `from neutron_qae.kernels import` |
| `scripts/freeze_kernels.py` | VERIFIED | `--force` guard works |
| `tests/golden/kernels_v1.json` | VERIFIED | `spec_fingerprint`, tables, T0/T1, exit_rows_k1 |
| five test files + `tests/test_physics_doc.py` | VERIFIED | full suite 111 passed |
| `docs/PHYSICS.md`, `README.md`, `scripts/derive_cross_sections.py` | VERIFIED | contents as above |

### Key Link Verification

All five 02-01 links and four 02-02 links are WIRED (problem -> nuclear_data, kernels -> problem, exact -> kernels, freeze script -> golden, golden test -> golden JSON; doc test -> PHYSICS.md and nuclear_data, derive script -> nuclear_data, README -> PHYSICS.md). Verified by source reading and by the passing tests that exercise each link.

### Data-Flow Trace (Level 4)

Not a rendering phase. Value chain traced: `MICRO_14MEV` + `WHA_97W/SS316` -> `one_group` -> `ProblemSpec` -> `build_kernels` -> `bitstring_probabilities_k1` -> `transmission_within`. Every link computes from real constants; no static returns. FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `.venv/bin/python -m pytest -q` | 111 passed, 1 pre-existing Phase 1 warning | PASS |
| Golden check | `.venv/bin/python scripts/freeze_kernels.py` | `GOLDEN OK kernels_v1.json T1=0.24300446519524305` | PASS |
| Overwrite guard | `freeze_kernels.py --write` | exit 2, sha256 unchanged | PASS |
| Phase 1 tracer | `scripts/run_local.py` | SMOKE TEST PASSED | PASS |
| Independent T1 | analog MC, 4e6 histories | 0.24291 +- 0.00021 vs 0.243004 (z = -0.44) | PASS |
| ENDF replication | `derive_cross_sections.py --check` | MICRO_14MEV REPRODUCED | PASS |

### Probe Execution

No probes declared by either plan and none exist (`scripts/*/tests/probe-*.sh` is empty). Step 7c: not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PHYS-01 | 02-01 | ProblemSpec 2D slab, boundary inside column 4 handled | SATISFIED | SC1 evidence |
| PHYS-02 | 02-01, 02-02 | ENDF/B-VIII.0 one-group cross sections cited with source and evaluation date | SATISFIED | SC2 evidence (code + docs) |
| PHYS-05 | 02-01, 02-02 | Frozen `Kernels` contract | SATISFIED | SC3 evidence |
| PHYS-06 | 02-01 | Exact lattice solver | SATISFIED | SC4 evidence |

All four phase requirement IDs appear in plan frontmatter and are marked complete in REQUIREMENTS.md (traceability rows 111-114). Orphan check: no other requirement is mapped to Phase 2 in REQUIREMENTS.md (PHYS-03/04/07/08 map to Phase 3). No ORPHANED requirements.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK in any phase-modified file. No stubs, empty implementations or hardcoded empties feeding output. None.

### Advisory notes (non-blocking)

- ROADMAP progress table still shows Phase 2 as "In Progress" and the plan checkboxes are ticked; the orchestrator should update status on completion. This is bookkeeping, not a goal gap.
- Modeling limits are disclosed, not hidden: transport-corrected one-group model is +6.5% vs the ENDF-angular reference; K=1 truncation covers 99.7% of the model transmission; (n,2n) is treated as removal. These are documented approximations, consistent with the roadmap's scope.
- A parallel code review (02-REVIEW.md) was running and was not awaited; findings there are separate from this goal-backward verification.
- Pre-existing uncommitted `.planning/config.json`, `.planning/milestone.lock`, `.planning/state.json` are unrelated to this phase.

### Human Verification Required

None. (Readability of PHYSICS.md prose is a UX judgment the plan flagged as human-judged, but it is not a goal-achievement condition.)

### Gaps Summary

No gaps. Every roadmap success criterion is backed by code I read and ran, with an independent Monte Carlo cross-check of the exact T1 and a re-run of the ENDF derivation. The `Kernels` contract v1 and exact T0/T1 are frozen, guarded and documented, so Phases 3 and 4 can proceed against the same ground truth.

---

_Verified: 2026-10-10T23:10:00Z_
_Verifier: Claude (gsd-verifier)_
