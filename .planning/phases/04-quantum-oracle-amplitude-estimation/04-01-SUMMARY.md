---
phase: 04-quantum-oracle-amplitude-estimation
plan: 01
subsystem: quantum
tags: [qiskit, state-preparation, ucry, grover-operator, amplitude-estimation, transpile, ionq-safe, qiskit-aer]

# Dependency graph
requires:
  - phase: 02-problem-spec-kernels-contract
    provides: "frozen Kernels v1 (first_collision, scatter_ratio, flight[..., BACK]), exact.py register layout (X_BITS, A_BITS, PHI_BITS, E_BITS, N_BITS), bitstring_probabilities_k1, transmission_within"
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "dependency approval for the pyproject dev extras, compliance gates (no backend construction under neutron_qae/, no qiskit_aer/algorithms/ionq reachable from main.py)"
  - phase: 03-classical-baseline
    provides: "tests/random_doubles.foreign_imports AST gate, NEUTRON_QAE_SLOW slow-test convention"
provides:
  - "neutron_qae/oracle.py: make_problem(model='Q1', kernels=None, tol=1e-12) -> OracleProblem(model, A, flag, K, p, reference, kernels; theta, qubits) behind the ContractError gate; build_q0, build_q1(direction=True|False), x_amplitudes, flag_probability, check_contract; MODELS, MODEL_QUBITS, MODEL_FLAG, MODEL_K, MAX_QUBITS = 24, CONTRACT_TOL = 1e-12"
  - "neutron_qae/grover.py: grover(A, flag) via grover_operator(), power_circuit(A, flag, k, measure='none'|'flag'|'all'), transpile_once(c, seed=1), max_controls, check_ionq_safe, resources, resource_table, format_resource_table; BASIS, ALLOWED_OPS, MAX_CONTROLS = 7, TRANSPILE_SEED = 1"
  - "tests/test_oracle.py (15 tests) and tests/test_grover.py (19 default + 1 slow): contract, per-string enumeration match, support, invertibility, Aer statevector, widths, layout and model guards; Grover sweep to k = 64, stitching trap, IonQ safety, budget and control boundaries, resource table"
  - ".venv now holds qiskit-aer 0.17.2, qiskit-algorithms 0.4.0, ruff 0.16.10 (and matplotlib 3.11.2) from the pyproject dev extras"
affects: [04-02, 04-03, 04-04, phase-5, anly-01, anly-02, anly-04, docs-quantum]

# Actuals (#2632)
actuals:
  tokens: 7317        # chars/4 over the realized diff of neutron_qae/ and tests/ (29,269 chars)
  tasks: 3
  commits: 3
plan_head_before: 075f5b7131222af26523adda37e960b7714091cf
plan_head_after: bf09447c917909d57645f2215c70daa8d9a39c0f

# Tech tracking
tech-stack:
  added: ["qiskit-aer 0.17.2 (dev, local only)", "qiskit-algorithms 0.4.0 (dev, local only)", "ruff 0.16.10 (dev)", "matplotlib 3.11.2 (declared base dependency, first installed here)"]
  patterns:
    - "Oracle factory with a contract gate: every circuit comes from make_problem, which raises ContractError unless Statevector P(flag) equals exact T_K within 1e-12"
    - "Qubit indices derived from exact.py's layout constants, never retyped; flag = highest qubit for every model"
    - "Compose logical A·Q^k (with measurements) first, then ONE transpile to an explicit BASIS at opt level 1 with a fixed seed"
    - "Aer only inside tests (pytest.importorskip, AerSimulator constructed in the test), always on BASIS-transpiled circuits"

key-files:
  created:
    - neutron_qae/oracle.py
    - neutron_qae/grover.py
    - tests/test_oracle.py
    - tests/test_grover.py
  modified: []

key-decisions:
  - "PD-15 (locked, research): keep the direction register. Q1 = 12 qubits, layout x(5) a(1) phi(4) e(1) T(1), qubit i = bit i of exact.py's s = x | a << 5 | phi << 6 | e << 10, flag T = qubit 11 (T = x4 OR (NOT x4 AND a AND e)). Q0 = 5 qubits, flag = qubit 4. Q1lite (8 qubits: x(5) a(1) e(1) T(1), escape angle averaged over the 16 bins) exists only as the IonQ size-ladder fallback; its strings carry no direction, so sample_exit_rows cannot consume them. Every model's flag is its highest qubit."
  - "PD-16 (locked, research): Grover operator = grover_operator(oracle=Z on the flag, state_preparation=A) (the function; the class is deprecated in Qiskit 2.1). Compose the logical A·Q^k first, then ONE transpile(c, basis_gates=BASIS, optimization_level=1, seed_transpiler=1) with BASIS = [cx, rz, ry, rx, h, x, sx]. Never transpile A and Q separately (k = 1 gives 0.95787 instead of 0.99941), never transpile(c, backend)."
  - "Contract gate (ROADMAP SC1): make_problem(model, kernels=None) raises ContractError when the Statevector flag probability differs from exact.transmission_within(kernels, K) by more than CONTRACT_TOL = 1e-12 (K = 0 for Q0, 1 for Q1 and Q1lite); runners (04-02) and main.py (04-03) take circuits only from make_problem."
  - "Dev extras installed under the Phase 1 dependency approval (01-01-PLAN Task 1 list, 01-01-SUMMARY 'Checkpoint record (Task 1)', reply 'approved'): pip install -e '.[dev]' added qiskit-aer 0.17.2, qiskit-algorithms 0.4.0, ruff 0.16.10 and matplotlib 3.11.2 (all on the approved list) plus their transitive deps; qiskit stays 2.5.2, numpy 2.5.3; qiskit-ionq not installed."

patterns-established:
  - "check_ionq_safe(tc) as the pre-submission guard: <= 24 qubits, <= 7 controls, op names within BASIS + measure"
  - "format_resource_table(resource_table()) is the exact Markdown 04-03 embeds in docs/QUANTUM.md"

requirements-completed: [QC-01, QC-02, QC-03, QC-04, QC-05, QC-06]

coverage:
  - id: D1
    description: "Q0 (5 qubits) flag probability equals e^-tau = T0 within 1e-12 (measured +3.2e-15)"
    requirement: QC-01
    verification:
      - kind: unit
        ref: "tests/test_oracle.py#test_q0_flag_probability_equals_exp_minus_tau"
        status: pass
    human_judgment: false
  - id: D2
    description: "Q1 (12 qubits) reproduces exact.py string by string (max 6.0e-15), has support exactly the 728 positive strings, 0 flag mismatches, and is a measurement-free invertible unitary (Q0, Q1, Q1lite)"
    requirement: QC-02
    verification:
      - kind: unit
        ref: "tests/test_oracle.py#test_q1_bitstring_probabilities_match_enumeration"
        status: pass
      - kind: unit
        ref: "tests/test_oracle.py#test_q1_support_is_the_enumeration"
        status: pass
      - kind: unit
        ref: "tests/test_oracle.py#test_state_preparation_is_unitary_without_measure_or_reset"
        status: pass
      - kind: unit
        ref: "tests/test_oracle.py#test_q0_operator_identity"
        status: pass
    human_judgment: false
  - id: D3
    description: "Contract gate: Q1 flag P = T1 within 1e-12 on qiskit's Statevector (+3.5e-15) and Aer's statevector (3.3e-16); make_problem raises ContractError on mismatch; holds at widths 6/15/20 cm"
    requirement: QC-03
    verification:
      - kind: unit
        ref: "tests/test_oracle.py#test_q1_flag_probability_equals_exact_T1"
        status: pass
      - kind: integration
        ref: "tests/test_oracle.py#test_aer_statevector_contract"
        status: pass
      - kind: unit
        ref: "tests/test_oracle.py#test_contract_gate_raises_on_mismatch"
        status: pass
      - kind: unit
        ref: "tests/test_oracle.py#test_contract_holds_at_other_wall_widths"
        status: pass
    human_judgment: false
  - id: D4
    description: "Grover powers via grover_operator() reproduce sin^2((2k+1) theta) within 1e-11 up to k = 64 (Q1 k <= 16 max 4.6e-13; Aer k = 32/64 -3.5e-13/-2.3e-13; Q0 k <= 64 max 9.0e-14)"
    requirement: QC-04
    verification:
      - kind: unit
        ref: "tests/test_grover.py#test_grover_powers_follow_sin2"
        status: pass
      - kind: unit
        ref: "tests/test_grover.py#test_q0_grover_powers_up_to_64"
        status: pass
      - kind: integration
        ref: "tests/test_grover.py#test_q1_grover_powers_32_64_on_aer"
        status: pass
      - kind: unit
        ref: "NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow tests/test_grover.py (1 passed)"
        status: pass
      - kind: unit
        ref: "tests/test_grover.py#test_grover_uses_function_api"
        status: pass
    human_judgment: false
  - id: D5
    description: "Resource table (qubits, CX, depth, size, max controls) for Q0, Q1, Q1lite at k = 0, 1, 2 after one transpile, pinned to exact integers and deterministic; 24-qubit and 7-control boundaries enforced"
    requirement: QC-05
    verification:
      - kind: unit
        ref: "tests/test_grover.py#test_resource_table_values"
        status: pass
      - kind: unit
        ref: "tests/test_grover.py#test_qubit_budget_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_grover.py#test_max_controls_threshold"
        status: pass
    human_judgment: false
  - id: D6
    description: "Local half of QC-06: every executed A·Q^k is transpiled once to BASIS with max 1 control; untranspiled circuits rejected; the stitched recipe stays documented as wrong (0.95787 vs 0.99941). Acceptance by Qollab's IonQ is 04-04's checkpoint."
    requirement: QC-06
    verification:
      - kind: unit
        ref: "tests/test_grover.py#test_transpiled_circuits_are_ionq_safe"
        status: pass
      - kind: unit
        ref: "tests/test_grover.py#test_stitched_transpile_is_wrong"
        status: pass
      - kind: unit
        ref: "tests/test_grover.py#test_power_circuit_validation"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 01: Quantum Oracle and Grover Powers Summary

**12-qubit Q1 oracle built from the frozen Kernels with exact.py's bit layout. Its contract gate holds T1 = 0.24300446519524305 to 3.5e-15. Grover powers built with `grover_operator()` and transpiled once to an IonQ-safe basis (1-control gates only) follow sin^2((2k+1) theta) to 5e-13 up to k = 64. A·Q^1 gives P(flag) = 0.999407 with 1,503 CX.**

## Performance

- **Duration:** about 6 min
- **Started:** 2026-10-11T02:26:52Z
- **Completed:** 2026-10-11T02:33Z
- **Tasks:** 3 of 3
- **Files created:** 4 (no existing file modified)

## Key results

- **Tracer line (Task 1):** `ORACLE TRACER OK T1=0.243004465195243 dA=3.5e-15 P1=0.999407 cx=1503`. This matches the planner's line exactly.
- **Slow run:** `NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow tests/test_grover.py` gives `1 passed, 19 deselected` (Q1 k = 32 and 64 on qiskit's Statevector).
- **Default suite:** `243 passed, 3 skipped` in 12.3 s (wall time 12-13 s). It was 209 passed and 2 skipped before; the new tests add 15 + 19 passes and 1 slow skip. `git status --porcelain` is the same before and after the run.
- **Installed versions:** qiskit 2.5.2 (unchanged), qiskit-aer 0.17.2, qiskit-algorithms 0.4.0, ruff 0.16.10, matplotlib 3.11.2, numpy 2.5.3 (unchanged).
- **Contract and measured values** (all equal the planner's numbers):

  | Check | Measured |
  |---|---|
  | Q1 P − T1 | +3.5e-15 (Statevector), 3.3e-16 (Aer) |
  | Q0 P − T0 | +3.2e-15 (Statevector), 1.7e-16 (Aer) |
  | Per-string max difference vs enumeration | 6.0e-15 |
  | Strings above 1e-15 | 728 |
  | Zero-mass bins | 168 |
  | Width 6 / 15 / 20 cm, Q1 | −8.3e-14 / −1.1e-14 / −6.2e-17 |

- **Grover sweep:**

  | Range | Max error |
  |---|---|
  | Q1, k ≤ 16 | 4.6e-13 |
  | Q1, k = 32 and 64 on Aer | −3.5e-13 and −2.3e-13 |
  | Q0, k ≤ 64 | 9.0e-14 |
  | Stitched recipe, k = 1 | P = 0.95787 vs 0.99941 expected |

- **Frozen contract:** `git diff --quiet 55b334d -- <frozen files, main.py, data, tests/golden>` exits 0. `scripts/freeze_kernels.py` prints `GOLDEN OK kernels_v1.json T1=0.24300446519524305`. The Phase 1 tracer (`scripts/run_local.py`) prints `TRACER OK`. No backend is constructed under `neutron_qae/`.

## Resource table (for 04-03's docs/QUANTUM.md)

`format_resource_table(resource_table())` (seed_transpiler = 1, qiskit 2.5.2):

| Model | Circuit | Qubits | CX | Depth | Size | Max controls |
|---|---|---|---|---|---|---|
| Q0 | A | 5 | 26 | 82 | 89 | 1 |
| Q0 | A·Q^1 | 5 | 100 | 270 | 304 | 1 |
| Q0 | A·Q^2 | 5 | 174 | 458 | 519 | 1 |
| Q1 | A | 12 | 313 | 518 | 543 | 1 |
| Q1 | A·Q^1 | 12 | 1503 | 2532 | 3001 | 1 |
| Q1 | A·Q^2 | 12 | 2693 | 4546 | 5459 | 1 |
| Q1lite | A | 8 | 73 | 166 | 187 | 1 |
| Q1lite | A·Q^1 | 8 | 399 | 757 | 996 | 1 |
| Q1lite | A·Q^2 | 8 | 725 | 1348 | 1805 | 1 |

Seed 7 gives the same Q1 A·Q^2 counts (2,693 CX, depth 4,546), and two calls compare equal.

## Handoff to 04-02 (MLAE and runners) and 04-03

- `make_problem(model, kernels=None)` returns a contract-checked `OracleProblem`.
  - Its fields are `model`, `A`, `flag`, `K`, `p` and `reference`; it also exposes `theta = asin(sqrt(p))` and `qubits`.
  - `kernels=None` uses a cached `build_kernels(sparc_first_wall())`. Pass `kernels=` for thickness sweeps (ANLY-04).
- `power_circuit(A, flag, k, measure=...)` builds the logical A·Q^k. The `measure` option sets the count keys:

  | `measure` | Classical register | Count keys |
  |---|---|---|
  | `"flag"` | one bit named `flag` | `'0'` and `'1'` |
  | `"all"` | n bits named `meas`, qubit i into bit i, no barrier | n-bit keys; the flag (top qubit) is key index 0 (leftmost), and `int(key, 2) & 0x7FF` is exact.py's s for Q1 |
  | `"none"` | none | n/a |

- `transpile_once(c, seed=1)` is the only transpile path. It raises above 24 qubits. Run `check_ionq_safe(tc)` before any IonQ submission.
- None of the new modules constructs a backend, and both import only the stdlib, numpy, qiskit and neutron_qae. That makes them safe for 04-03 to make reachable from main.py.

## ROADMAP Phase 4 success criteria covered

- **Criterion 1** (Q0 = e^-tau; Q1 = T1 to 1e-12 on qiskit's and Aer's statevector; no measurement or reset; invertible; gate on every run): `test_q0_flag_probability_equals_exp_minus_tau`, `test_q1_flag_probability_equals_exact_T1`, `test_aer_statevector_contract`, `test_state_preparation_is_unitary_without_measure_or_reset`, `test_contract_gate_raises_on_mismatch`.
- **Criterion 2** (`grover_operator()` powers equal sin^2((2k+1) theta) up to k = 64): `test_grover_powers_follow_sin2`, `test_q0_grover_powers_up_to_64`, `test_q1_grover_powers_32_64_on_aer`.
- **Criterion 5, code half** (resource table after one full transpile, within 24 qubits): `test_resource_table_values`. Plan 04-03 puts the table in the docs.
- **QC-06, local half** (transpiled once, at most 1 control per gate): `test_transpiled_circuits_are_ionq_safe`.

## Task Commits

1. **Task 1: Tracer.** Dev extras installed; frozen Kernels → Q1 A → contract gate → A·Q^1 transpiled once, P = 0.9994. Commit `ed06140` (feat).
2. **Task 2: State preparation equals the enumeration.** Covers Q0 = e^-tau, per-string match, support, invertibility, the Aer contract, and the gate and layout edges. Commit `1ade9b0` (test).
3. **Task 3: Grover to k = 64.** Covers the IonQ-safe single transpile, the stitching trap, the 24-qubit boundary and the resource table. Commit `bf09447` (test).

## Files Created

- `neutron_qae/oracle.py`: Q0, Q1 and Q1lite state preparation, the contract gate, the `OracleProblem` dataclass and the `make_problem` factory.
- `neutron_qae/grover.py`: Grover operator, A·Q^k composition, `transpile_once`, control, safety and resource helpers, and the resource table.
- `tests/test_oracle.py`: 15 tests covering QC-01 to QC-03.
- `tests/test_grover.py`: 19 default tests plus 1 slow test, covering QC-04 to QC-06.

## Decisions Made

PD-15, PD-16, the contract gate and the dev-extras install are recorded in `key-decisions` above. Implementation choices within the plan:

- `check_ionq_safe` returns its argument, so it can be chained.
- `power_circuit` builds the Grover operator only when k > 0.
- `max_controls` treats a missing or `None` `num_ctrl_qubits` as 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, install scope] The dev-extras install also brought in matplotlib and transitive dependencies**
- **Found during:** Task 1 step 1. A dry run came before the real install.
- **Issue:** `pip install -e ".[dev]"` installs:
  - matplotlib 3.11.2, a pyproject base dependency;
  - the transitive deps of approved packages: contourpy, cycler, fonttools, kiwisolver, pillow, pyparsing, python-dateutil, six and psutil.

  These go beyond the three dev pins named in the task. The plan's own PD notes and the Phase 1 approval list name matplotlib explicitly. Transitive deps follow the Phase 1 precedent ("qiskit ... pulls its own transitive deps").
- **Fix:** Proceeded. qiskit stayed at 2.5.2 and numpy at 2.5.3, nothing outside the approved list plus transitive deps was installed, and qiskit-ionq was not installed.
- **Verification:** `pip list` output is recorded above. `git status --porcelain` was unchanged.

**2. [Style] Ruff fixes in the new files**
- `__all__` lists are sorted (RUF022).
- `tests/test_oracle.py` has its import order fixed (I001) and uses a dict comprehension (C402). This file was committed in Task 2, and the lint fix went into the Task 3 commit `bf09447`.
- There is no behaviour change. Ruff reports `All checks passed!` on the four new files. Pre-existing ruff findings elsewhere in the repo were left alone, as they are out of scope.

---

**Total deviations:** 2. One is a documented install-scope note; one is cosmetic lint.
**Impact on plan:** None. No tolerance, seed or frozen file changed, and every planner-measured number was reproduced exactly.

## Issues Encountered

None. The single pytest warning (`Option noise_model is not used by this backend`) comes from the pre-existing Phase 1 `tests/test_smoke.py` fake-IonQ test.

## Known Stubs

None.

## User Setup Required

None.

## Next Phase Readiness

Plan 04-02 (vendored MLAE and the Analytic, Backend and IonQ runners) can build on `make_problem`, `power_circuit` and `transpile_once`. Aer is available locally for the QAE-04 agreement tests.

## Self-Check: PASSED

- FOUND: neutron_qae/oracle.py, neutron_qae/grover.py, tests/test_oracle.py, tests/test_grover.py
- FOUND: commits ed06140, 1ade9b0, bf09447 (ancestors of HEAD). `gsd-tools check evaluation-scope --plan 04-01 --commits-only` resolves all three.
- Plan-level verification all passes:
  - full suite: exit 0 in 12 s, porcelain unchanged;
  - slow run: 1 passed;
  - Phase 1 tracer: TRACER OK;
  - freeze_kernels: GOLDEN OK;
  - frozen-file diff against 55b334d: clean.
