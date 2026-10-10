---
phase: 01-qollab-smoke-test-compliant-skeleton
plan: 01
subsystem: infra
tags: [qiskit, qollab, pytest, compliance, ast, basicsimulator, flat-layout]

# Dependency graph
requires: []
provides:
  - "Qollab entry point main.py with a one-line typed main(shots, ghz_qubits, ideal_mode, perf_qubits) that reads the injected global backend"
  - "Flat package neutron_qae/ with smoke.py (runtime/backend reports, IonQ-safe single two-circuit job, perf probe)"
  - "scripts/run_local.py: the only allow-listed backend constructor outside tests; injects BasicSimulator or AerSimulator like Qollab"
  - "Stdlib-only compliance suite (tests/compliance_checks.py) with a negative test for every gate"
  - "Local .venv (Python 3.14.8, qiskit 2.5.2, pytest 9.1.1), clean repo root, textbook PDF preserved in gitignored references/"
affects: [01-02, 01-03, 01-04, problem-spec, kernels, classical-mc, quantum-oracle, mlae, figures]

# Actuals (#2632)
actuals:
  tokens: 6746
  tasks: 3
  commits: 2
plan_head_before: 228ee9f0eae62fb83adc77e9ed6b9dc53357e2f1
plan_head_after: 8798bb02ae35bc1aeb6cc83d5b2085db53be2d53

# Tech tracking
tech-stack:
  added: [qiskit==2.5.2, pytest==9.1.1]
  patterns:
    - "Backend dependency injection: main.py reads the module-global backend; every package function takes backend as a parameter"
    - "Data files referenced only by literal path strings (PROBE_FILE = \"data/smoke_probe.json\")"
    - "IonQ detection by type(backend).__module__ prefix, never by importing qiskit_ionq"
    - "One backend.run call per main() on IonQ (multi-circuit list); perf probe skipped on IonQ"
    - "Compliance gates are ast-based, stdlib only, scan every node, and each has a tmp_path negative test"

key-files:
  created:
    - main.py
    - neutron_qae/__init__.py
    - neutron_qae/smoke.py
    - data/smoke_probe.json
    - scripts/run_local.py
    - requirements.txt
    - pyproject.toml
    - .gitignore
    - .gitattributes
    - tests/compliance_checks.py
    - tests/test_compliance.py
    - tests/test_smoke.py
  modified: []

key-decisions:
  - "Package name neutron_qae in a flat layout at the repo root (src/ layout breaks Qollab imports)"
  - "Compliance file scans use git ls-files --cached --others --exclude-standard, so not-yet-committed files are gated too"
  - "Whitespace gate uses str.isspace() over the whole repo-relative path (directories, tab and U+00A0 included); size gate is the stricter decimal 2,000,000 bytes"
  - "LICENSE/README.md are not required by the upload-set test in this plan; plan 01-02's docs tests assert them"

patterns-established:
  - "Local runner pattern: os.chdir(ROOT); import main as entry; entry.backend = make_backend(kind); entry.main(...)"
  - "Negative tests build fake projects under pytest tmp_path, so the test run never writes inside the repo"

requirements-completed: [PLAT-01, PLAT-02, PLAT-04]

coverage:
  - id: D1
    description: "Toy main.py runs end-to-end locally through neutron_qae on an injected BasicSimulator, printing one QOLLAB_RUNTIME_REPORT= line and SMOKE TEST PASSED"
    requirement: "PLAT-02"
    verification:
      - kind: e2e
        ref: ".venv/bin/python scripts/run_local.py | tracer assertion script (prints TRACER OK)"
        status: pass
      - kind: integration
        ref: "tests/test_smoke.py#test_main_runs_with_injected_basic_simulator"
        status: pass
    human_judgment: false
  - id: D2
    description: "Nothing reachable from main.py imports qiskit_aer, qiskit_algorithms, qiskit_ionq or qiskit_ibm_runtime (five negative forms proven to fire)"
    requirement: "PLAT-04"
    verification:
      - kind: unit
        ref: "tests/test_compliance.py#test_nothing_reachable_from_main_imports_aer_or_algorithms"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_forbidden_import_is_detected_through_package"
        status: pass
    human_judgment: false
  - id: D3
    description: "No backend constructed, assigned in main.py or read as a free global in the package outside tests/ and scripts/"
    requirement: "PLAT-04"
    verification:
      - kind: unit
        ref: "tests/test_compliance.py#test_no_backend_constructed_outside_local_runners"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_backend_construction_is_detected"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_global_backend_read_in_package_is_detected"
        status: pass
    human_judgment: false
  - id: D4
    description: "IonQ-like backend: one main() call makes exactly one backend.run call and perf_probe is skipped"
    requirement: "PLAT-04"
    verification:
      - kind: integration
        ref: "tests/test_smoke.py#test_ionq_like_backend_sends_exactly_one_job"
        status: pass
    human_judgment: false
  - id: D5
    description: "No committed or committable file over 2,000,000 bytes and no whitespace in any repo path; placeholders deleted, PDF moved to gitignored references/ and untracked"
    requirement: "PLAT-01"
    verification:
      - kind: unit
        ref: "tests/test_compliance.py#test_no_committed_file_over_2mb"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_no_whitespace_in_repo_paths"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_whitespace_path_is_detected"
        status: pass
      - kind: other
        ref: "find root -maxdepth 1 -name '* *' empty; test -s references/<PDF>; git check-ignore references/<PDF>; git ls-files '*.pdf' empty"
        status: pass
    human_judgment: false
  - id: D6
    description: "main() signature is Qollab form-compatible and the Qollab upload set stays under 100 files without tests/, scripts/ or .planning/"
    requirement: "PLAT-01"
    verification:
      - kind: unit
        ref: "tests/test_compliance.py#test_main_signature_is_qollab_form_compatible"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_bad_main_signature_is_detected"
        status: pass
      - kind: unit
        ref: "tests/test_compliance.py#test_qollab_upload_stays_under_100_files_and_ships_entry_point"
        status: pass
    human_judgment: false

# Metrics
duration: 3min
completed: 2026-10-10
status: complete
---

# Phase 1 Plan 01: Qollab-compliant code skeleton Summary

**Toy Qiskit main.py running end-to-end through the flat neutron_qae package on an injected BasicSimulator, policed by a stdlib-only ast compliance suite (28 tests, every gate with a negative test), with the repo root cleaned and the textbook PDF moved to gitignored references/**

## Performance

- **Duration:** about 3 min (continuation run; Task 1 approval obtained earlier)
- **Started:** 2026-10-10T18:31:34Z
- **Completed:** 2026-10-10T18:34:15Z
- **Tasks:** 3 (1 checkpoint + 2 code tasks)
- **Files modified:** 12 created

## Checkpoint record (Task 1)

Task 1, `checkpoint:human-verify` gate="blocking-human", "Hippolyte approves the Python dependency list before the first pip install". Hippolyte's reply, verbatim:

```
approved
```

No package was rejected. `.venv` did not exist before approval (verified at resume: `test ! -e .venv` true). Only the approved packages were installed: `qiskit==2.5.2` (with its own transitive dependencies) and `pytest==9.1.1`.

## Local tracer run

`.venv/bin/python scripts/run_local.py` printed `TRACER OK` under the plan's assertion script and ended with `SMOKE TEST PASSED`. The report line:

```
QOLLAB_RUNTIME_REPORT={"runtime": {"python": "3.14.8", "python_full": "3.14.8 (v3.14.8:8e6e75d9102, Sep 30 2026, 14:34:30) [Clang 21.0.0 (clang-2100.1.1.101)]", "platform": "darwin", "numpy": "2.5.3", "qiskit": "2.5.2", "scipy": "1.18.1", "qiskit_ionq": "not importable (ModuleNotFoundError)", "pyodide": null, "data_file_literal_path": "data file loaded by literal path"}, "backend": {"class": "qiskit.providers.basic_provider.basic_simulator.BasicSimulator", "name": "basic_simulator", "options_noise_model": null, "options_shots": 1024, "is_ionq": false}, "toy": {"ideal_mode": "none", "applied": "n/a (local ideal simulator)", "run_kwargs": {"shots": 200}, "n": 6, "accepted": true, "error": null, "counts": [{"111111": 103, "000000": 97}, {"111111": 200}], "transpile_s": 0.007, "run_s": 0.001, "ghz_off_ideal_fraction": 0.0, "ones_fraction": 1.0, "noise_verdict": "ideal, sampled"}, "perf": {"qubits": 12, "depth": 20, "cx": 220, "transpile_s": 0.001, "run_s": 0.023}, "wall_clock_s": 0.034}
```

## Accomplishments

- main.py with the exact one-line form signature, reading only the injected `backend`, no `__name__` guard, printing one `QOLLAB_RUNTIME_REPORT=` line and `SMOKE TEST PASSED`
- `neutron_qae/smoke.py` sends one `backend.run` job carrying two circuits, detects IonQ by module name, clamps form inputs (T-01-01), and skips the perf probe on IonQ
- Compliance gates for forbidden reachable imports, files over 2,000,000 bytes, backend construction/assignment/global read, main() form signature, whitespace in paths, literal data paths, and the Qollab upload set; each gate has a negative test
- One-IonQ-job guarantee tested on a BasicSimulator subclass whose `__module__` is `qiskit_ionq.ionq_backend` (ideal_mode "none" and "kwarg")
- Repo cleanup: the three 0-byte placeholders deleted; the 8,208,050-byte Carter 1975 PDF moved intact into gitignored `references/`; `git ls-files '*.pdf'` is empty
- Computed Qollab upload set is exactly `data/smoke_probe.json`, `main.py`, `neutron_qae/__init__.py`, `neutron_qae/smoke.py`, `requirements.txt` (LICENSE and README.md arrive in 01-02)

## Task Commits

1. **Task 1: Hippolyte approves the Python dependency list** - checkpoint only, no commit (reply: `approved`)
2. **Task 2: Tracer - toy main.py runs end-to-end through neutron_qae on an injected BasicSimulator** - `fedf909` (feat)
3. **Task 3: Compliance gates, pytest config and repo cleanup** - `8798bb0` (feat)

**Plan metadata:** recorded in the docs(01-01) commit that adds this SUMMARY

## Files Created/Modified

- `main.py` - Qollab entry point; typed one-line `main(...)`, reads injected global backend, prints the runtime report
- `neutron_qae/__init__.py` - flat package marker, `__all__ = ["smoke"]`
- `neutron_qae/smoke.py` - `runtime_report`, `backend_report`, `is_ionq`, `ghz`, `all_ones`, `run_toy`, `perf_probe`; `PROBE_FILE` literal path
- `data/smoke_probe.json` - data file proving literal-path loading
- `scripts/run_local.py` - local runner injecting BasicSimulator/AerSimulator into main.py like Qollab
- `requirements.txt` - Qollab-facing; single requirement `qiskit==2.5.2`
- `pyproject.toml` - setuptools metadata, `dev` extra, `packages = ["neutron_qae"]`, pytest `pythonpath = [".", "tests"]`
- `.gitignore` - research entries (venv written as `.venv`), plus `references/`, `.planning/research/.cache/`, `.claude/worktrees/`
- `.gitattributes` - export-ignore list so `git archive` ships only what Qollab needs
- `tests/compliance_checks.py` - stdlib-only gates mirroring Qollab's Walker; `repo_files` (tracked plus non-ignored untracked) and `whitespace_paths` added
- `tests/test_compliance.py` - PLAT-01/PLAT-04 gates plus negative tests
- `tests/test_smoke.py` - end-to-end local mirror and the one-IonQ-job test

## Decisions Made

- Followed the plan's two deliberate changes to the research compliance helper (`tracked_files` renamed to `repo_files` with `--others --exclude-standard`; new `whitespace_paths`). Both callers (`oversized_files`, `qollab_upload_files`) were updated.
- Code bodies were copied verbatim from RESEARCH "Code Examples" with a small extraction script, not retyped, so no transcription drift.

## Deviations from Plan

None - plan executed exactly as written.

Execution note (not a code deviation): the first attempt at the placeholder deletion used a shell variable path (`"$MAIN_ROOT/$n"`), which the Claude Code safety check blocked before anything ran. The deletion was re-issued with literal absolute paths after the same `test ! -s` 0-byte check on each file, as the check suggested. Result identical to the plan.

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

- pytest emits one expected `UserWarning: Option noise_model is not used by this backend` in `test_ionq_like_backend_sends_exactly_one_job[kwarg]`; the research noise_model table documents this BasicSimulator behaviour. Not a failure.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 01-02 (LICENSE, README, docs tests). Its docs tests should add LICENSE and README.md back to the upload-set assertion.
- `.venv` exists in the main checkout with qiskit 2.5.2 and pytest 9.1.1; later plans reuse it. qiskit-aer, qiskit-algorithms, ruff and matplotlib are declared in pyproject.toml but not installed.
- 01-03 can zip the repo with `git archive` and upload; the "set_options" ideal mode is only exercisable on Qollab's IonQ backend.

## Self-Check: PASSED

- All 12 key files exist on disk.
- Commits `fedf909` and `8798bb0` are ancestors of HEAD; `check evaluation-scope --plan 01-01 --commits-only` resolves both.
- Plan verification: `scripts/run_local.py` ends with `SMOKE TEST PASSED` with one report line; `pytest -q` gives 28 passed; no whitespace name at the repo root; PDF present, non-empty and ignored; no tracked PDF; `git status --porcelain` unchanged by a full pytest run.

---
*Phase: 01-qollab-smoke-test-compliant-skeleton*
*Completed: 2026-10-10*
