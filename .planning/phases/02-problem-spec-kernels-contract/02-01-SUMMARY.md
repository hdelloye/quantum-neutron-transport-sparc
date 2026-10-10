---
phase: 02-problem-spec-kernels-contract
plan: 01
subsystem: physics
tags: [endf-b-viii.0, one-group, transport-correction, kernels-contract, exact-enumeration, golden-file, numpy]

# Dependency graph
requires:
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "flat neutron_qae package, .venv (numpy 2.5.3, pytest 9.1.1), tests/compliance_checks.py (reachable_modules, MAX_FILE_BYTES), scripts/ ROOT pattern"
provides:
  - "neutron_qae/nuclear_data.py: cited 14.1 MeV ENDF/B-VIII.0 constants with per-isotope provenance (36 MAT rows), abundances, sigma(n,2n), compositions and material sources"
  - "neutron_qae/problem.py: Material (scatter_ratio, sigma_a), MODELS/DEFAULT_MODEL, atom_densities, one_group, frozen validated ProblemSpec with row_of, sparc_first_wall(model, **overrides), spec_fingerprint"
  - "neutron_qae/kernels.py: frozen Kernels contract v1 (first_collision, scatter_ratio, flight, back_exit_rows; read-only private float64 copies) and build_kernels"
  - "neutron_qae/exact.py: literal 2^11 enumeration of the K=1 model, transmission_within(k, K in {0,1}), exit_row_distribution_k1, REGISTER_LAYOUT"
  - "tests/golden/kernels_v1.json: frozen contract v1 (T0=0.23256718303628812, T1=0.24300446519524305) written only by scripts/freeze_kernels.py --write"
affects: [02-02, classical-mc, quantum-oracle, mlae, figures, phase-3, phase-4, phase-5]

# Actuals (#2632)
actuals:
  tokens: 12109       # chars/4 over the 10 code/test files (48,437 chars); the 67,831-byte golden JSON adds ~16,958 more (full diff 125,560 chars -> 31,390)
  tasks: 3
  commits: 3
plan_head_before: 3ea85b9825f13623ed0966993e6eb7796b90acfe
plan_head_after: 461f490733ab5c4beedbde594bdf724d20f1c1c0

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Contract dataclass: @dataclass(frozen=True, eq=False) storing private np.array(copy=True) float64 tables with setflags(write=False) and shape checks via object.__setattr__"
    - "Golden freeze: stdlib json (repr floats) written only by a guarded script (--write refuses without --force, exit 2); tests compare at rtol 1e-12 / atol 1e-15 plus a sha256 fingerprint of the spec inputs, never a hash of output floats"
    - "Ground truth by literal enumeration + math.fsum, with the closed form as a cross-check only"
    - "Single row rule ProblemSpec.row_of (floor, clipped) used by every engine"
    - "AST import allowlist test keeps contract modules to numpy + stdlib + neutron_qae"

key-files:
  created:
    - neutron_qae/nuclear_data.py
    - neutron_qae/problem.py
    - neutron_qae/kernels.py
    - neutron_qae/exact.py
    - scripts/freeze_kernels.py
    - tests/golden/kernels_v1.json
    - tests/test_exact.py
    - tests/test_nuclear_data.py
    - tests/test_problem.py
    - tests/test_kernels_contract.py
    - tests/test_kernels_golden.py
  modified: []

key-decisions:
  - "PD-01 (costly): one-group model is transport-corrected (Sigma_tr = Sigma_t - mubar*Sigma_el, Sigma_s,tr = (1-mubar)*Sigma_el); isotropic_raw selectable via sparc_first_wall('isotropic_raw'); every golden value frozen on transport-corrected"
  - "PD-02 (costly): WHA = 97W-2Ni-1Fe wt% at 18.5 g/cm3 (Rizzi et al. arXiv:2603.03893); 316 SS = PNNL-15870 Rev. 2 entry 333 at 8.00 g/cm3"
  - "PD-03: absorption = removal from the 14 MeV group, Sigma_a = Sigma_t - Sigma_el; (n,2n) counted once as removal"
  - "PD-04: Kernels contract v1 supports K in {0, 1}; K=2 is a v2 contract change (QC-08) and raises ValueError"
  - "PD-05: x = depth (0 = plasma face), y lateral; 0-based column j = [j*dx, (j+1)*dx), dx = 0.625; interface inside 0-based column 3 = ROADMAP column 4; material_at half-open; exit row = floor(y/dy) clipped; bin b = [2pi b/16, 2pi(b+1)/16) from +x toward +y; pencil beam at y = 5.0, normal incidence"
  - "PD-06: four flat modules, constants in code (nothing in data/), frozen read-only Kernels, golden tests/golden/kernels_v1.json at rtol 1e-12 + spec fingerprint, main.py unchanged"

patterns-established:
  - "Contract change procedure: bump KERNELS_CONTRACT_VERSION, run scripts/freeze_kernels.py --write --force, re-run Phase 3 and Phase 4 contract tests"
  - "Physics numbers are defined only in nuclear_data.py / problem.py; consumers call sparc_first_wall()"

requirements-completed: [PHYS-01, PHYS-02, PHYS-05, PHYS-06]

coverage:
  - id: D1
    description: "Tracer: sparc_first_wall() -> build_kernels() -> exact T0/T1 reproduces the research reference (T0 0.23256718303628812, T1 0.24300446519524305) and their closed forms"
    requirement: PHYS-06
    verification:
      - kind: unit
        ref: "tests/test_exact.py#test_reference_values_match_research"
        status: pass
      - kind: unit
        ref: "tests/test_exact.py#test_T1_equals_closed_form"
        status: pass
      - kind: other
        ref: "plan Task 1 tracer command (prints TRACER OK 0.23256718303628812 0.24300446519524305)"
        status: pass
    human_judgment: false
  - id: D2
    description: "SPARC first-wall ProblemSpec with the 2.0 cm interface integrated exactly inside ROADMAP column 4 (0-based 3), half-open boundary, floor row rule, input validation and spec fingerprint"
    requirement: PHYS-01
    verification:
      - kind: unit
        ref: "tests/test_problem.py#test_boundary_inside_roadmap_column_4_is_not_snapped"
        status: pass
      - kind: unit
        ref: "tests/test_problem.py (11 tests incl. parametrised validation)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cited ENDF/B-VIII.0 nuclear data: MAT number, verbatim evaluation string and date for all 36 isotopes, library and material citations, atom densities and macroscopic values matching the research"
    requirement: PHYS-02
    verification:
      - kind: unit
        ref: "tests/test_nuclear_data.py#test_provenance_covers_every_isotope"
        status: pass
      - kind: unit
        ref: "tests/test_nuclear_data.py (all tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Frozen Kernels contract v1: shapes, conservation, back-face bins, mirror symmetry, immutability, determinism, numpy/stdlib-only imports"
    requirement: PHYS-05
    verification:
      - kind: unit
        ref: "tests/test_kernels_contract.py#test_kernels_frozen_and_read_only"
        status: pass
      - kind: unit
        ref: "tests/test_kernels_contract.py#test_contract_modules_use_only_numpy_and_stdlib"
        status: pass
    human_judgment: false
  - id: D5
    description: "Golden freeze tests/golden/kernels_v1.json with guarded writer and independent rtol-1e-12 comparison plus tamper negative test"
    requirement: PHYS-05
    verification:
      - kind: unit
        ref: "tests/test_kernels_golden.py#test_rebuilt_kernels_match_golden"
        status: pass
      - kind: unit
        ref: "tests/test_kernels_golden.py#test_tampered_golden_is_detected"
        status: pass
      - kind: other
        ref: "python scripts/freeze_kernels.py (GOLDEN OK); --write without --force exits 2 with sha256 unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "PHYS-06 edges: little-endian 11-bit layout, x=16 mirrors column 0, K outside {0,1} rejected, fixed 16x16 layout, order-independent fsum, exact K=1 exit-row histogram"
    requirement: PHYS-06
    verification:
      - kind: unit
        ref: "tests/test_exact.py (PHYS-06 edge tests)"
        status: pass
    human_judgment: false
  - id: D7
    description: "No Qollab regression: main.py/__init__/smoke.py/data unchanged since 34a827a, new modules unreachable from main.py, Phase 1 tracer passes, full suite leaves git status unchanged"
    verification:
      - kind: integration
        ref: "scripts/run_local.py tracer -> TRACER OK; MAIN GRAPH UNCHANGED ['__init__.py', 'main.py', 'smoke.py']; git diff --quiet 34a827a gate"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-10-10
status: complete
---

# Phase 2 Plan 01: Problem Spec & Kernels Contract v1 Summary

**ENDF/B-VIII.0-cited transport-corrected one-group SPARC first wall, frozen `Kernels` contract v1 and a literal 2^11 enumeration giving T0 = 0.23256718303628812 and T1 = 0.24300446519524305, frozen in `tests/golden/kernels_v1.json`.**

## Performance

- **Duration:** about 6 min of execution (timestamps below); plan reading came before the start mark
- **Started:** 2026-10-10T22:14:20Z
- **Completed:** 2026-10-10T22:19:14Z
- **Tasks:** 3 of 3
- **Files created:** 11 (0 existing files modified)

## Key outputs

- Tracer line: `TRACER OK 0.23256718303628812 0.24300446519524305` (both digit-for-digit equal to the research reference)
- Golden check: `GOLDEN OK kernels_v1.json T1=0.24300446519524305`
- Golden file: `tests/golden/kernels_v1.json`, 67,831 bytes, sha256 `350474b3d7c4d6e3839eb67e5e2ff395b3ccef0bb070780a5e67984985d8df14`
- Spec fingerprint (transport_corrected default): `2c279f38b9c47d1dced4952e03a6b987b47b28bec1a684768c34676ac335695f`
- Test suite: 36 -> 102 passed; `git status --porcelain` is unchanged by the run
- Phase 1 tracer (`scripts/run_local.py`) still prints `TRACER OK`; `main.py` import graph is still `['__init__.py', 'main.py', 'smoke.py']`

## Accomplishments

- One path wired end to end: cited constants -> `one_group` -> frozen `ProblemSpec` -> `build_kernels` -> `transmission_within`. The values are bit-identical to the prototype.
- Every microscopic cross section traces to ENDF/B-VIII.0: 36 isotope rows, each with a MAT number (MAT // 100 == Z), a verbatim evaluation string and a date that falls before the 2018-02-02 release.
- The column-4 interface is integrated exactly over its two sub-segments (tau = 0.125 Sigma_WHA + 0.5 Sigma_SS316) and is never snapped to a column edge.
- `Kernels` is frozen and read-only: it holds private copies, so mutating the source arrays does not affect it, and a wrong table shape raises ValueError.
- Contract v1 is frozen. The writer refuses to overwrite without `--force`, and the independent golden test catches a 1e-9 relative change to any table, a different fingerprint and a version change.

## Task Commits

1. **Task 1: Tracer - sparc_first_wall() -> build_kernels() -> exact T0/T1** - `03b628d` (feat)
2. **Task 2: Contract edges - provenance, column-4 boundary, conservation, symmetry, immutability, validation, bit layout** - `c309e30` (test)
3. **Task 3: Freeze contract v1 - golden file, guarded freeze script, independent golden test** - `461f490` (feat)

## Files Created/Modified

- `neutron_qae/nuclear_data.py` - cited 14.1 MeV constants: LIBRARY, MICRO_14MEV, SIGMA_N2N_14MEV, ATOMIC_WEIGHT/NUMBER, ABUNDANCE, PROVENANCE, WHA_97W, SS316, MATERIAL_SOURCES
- `neutron_qae/problem.py` - Material, MODELS, atom_densities, one_group, ProblemSpec (validated, row_of), sparc_first_wall, spec_fingerprint
- `neutron_qae/kernels.py` - KERNELS_CONTRACT_VERSION "1", outcome indices, quadrature (24, 48), frozen Kernels, build_kernels
- `neutron_qae/exact.py` - REGISTER_LAYOUT, N_BITS, bitstring_probabilities_k1, transmission_within, exit_row_distribution_k1
- `scripts/freeze_kernels.py` - LOCAL ONLY golden writer/checker
- `tests/golden/kernels_v1.json` - frozen contract v1
- `tests/test_exact.py`, `tests/test_nuclear_data.py`, `tests/test_problem.py`, `tests/test_kernels_contract.py`, `tests/test_kernels_golden.py` - 66 new tests

## Decisions Made

The plan's PD-01 to PD-06 are implemented as written (see key-decisions). PD-01 and PD-02 are marked costly. No new decisions were needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Input validation] Finite-value and type checks beyond the listed cases**
- **Found during:** Task 1
- **Issue:** The plan's validation list did not reject NaN/inf cross sections, NaN/inf geometry, non-finite densities or weight fractions, or a float `nx`. Any of these would yield numbers that look plausible but mean nothing (threat T-02-04).
- **Fix:** `Material`, `ProblemSpec` and `atom_densities` also reject non-finite values. `ProblemSpec` requires int (not bool) counts. Parametrised tests cover `width_x=-10.0`, `nx=True`, `nx=16.0` and `sigma_t=nan`.
- **Files modified:** neutron_qae/problem.py, tests/test_problem.py
- **Committed in:** 03b628d, c309e30

**2. [Minor] Extra tamper case and split single-element test**
- The single-element `{W: 1.0}` check is its own test (`test_single_element_composition`) rather than a parametrised case of `test_one_group_input_edges`.
- `test_tampered_golden_is_detected` also checks a contract_version change.

---

**Total deviations:** 1 auto-fixed (Rule 2) plus 2 minor additive test changes. **Impact:** stricter validation only; every planned value and tolerance is unchanged.

## Issues Encountered

- During the Task 1 acceptance run, a bash line accidentally included `git checkout -q 34a827a --` with no pathspec. It did nothing: HEAD stayed on `main` at 3ea85b9 and every working-tree change, including the orchestrator's `.planning/config.json` edit, was intact. This was checked right away with `git symbolic-ref HEAD`, `git status` and `git reflog`.
- `ruff` is not installed in `.venv`, so no lint pass was run. Lint is not a plan gate.

## Known Stubs

None.

## User Setup Required

None. No external service configuration is required.

## STATE blocker resolution

[Phase 2] Real ENDF/B-VIII.0 cross sections pulled; transport-corrected K=1 coverage is 99.7% (89.9% only under isotropic_raw).

## Next Phase Readiness

**Handoff for Phase 3 (classical MC):**
- PHYS-04's uncollided check uses the model optical depth from `ProblemSpec.tau_x`: exp(-tau_tr) = T0 = 0.2326, not the physical 0.0867.
- The discrete MC samples exactly the `Kernels` tables and should converge to the golden T1 = 0.24300446519524305.
- Histograms use `ProblemSpec.row_of`; `exit_row_distribution_k1` is the exact K=1 reference histogram.

**Handoff for Phase 4 (quantum oracle):**
- QC-03 compares the Q1 flag probability with the golden T1 at 1e-12.
- The register order is `exact.REGISTER_LAYOUT`: x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10, little-endian (bit i = Qiskit qubit i).
- x = 16 rotates a and e like column 0.
- RESEARCH A3: T1 does not depend on the phi bin count, so a phi-free Q1 variant would keep T1 exactly.

Plan 02-02 (physics docs) is ready to run against these modules.

## Self-Check: PASSED
- All 11 created files exist; commits 03b628d, c309e30 and 461f490 are ancestors of HEAD (checked before this SUMMARY was committed).
