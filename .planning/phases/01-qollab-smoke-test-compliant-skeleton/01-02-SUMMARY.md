---
phase: 01-qollab-smoke-test-compliant-skeleton
plan: 02
subsystem: docs
tags: [license, mit, readme, disclosure, attribution, qollab, pytest, gh]

# Dependency graph
requires:
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "01-01: tests/compliance_checks.py (qollab_upload_files), .gitattributes export-ignore list, shared .venv, main.py form fields and scripts/run_local.py flags"
provides:
  - "MIT LICENSE (Copyright (c) 2026 Hippolyte Delloye and contributors)"
  - "README.md with the verbatim attribution line, browser (JSPI) note, Qollab and local run instructions, module rules and a 9-row library/AI-tool disclosure table"
  - "tests/test_docs.py: seven docs tests guarding LICENSE, attribution, disclosure cells, one row per component, upload set, write-up length and the runtime record's sections"
  - "docs/QOLLAB-RUNTIME.md: static Qollab runtime facts plus empty Empirical runs / Raw reports / Conclusions sections for plan 01-03"
  - "GitHub CLI gh 2.102.0 installed via homebrew-core for plan 01-04"
affects: [01-03, 01-04, quantum-oracle, figures, submission]

# Actuals (#2632)
actuals:
  tokens: 3635
  tasks: 2
  commits: 2
plan_head_before: 7b17a19b843103e982a92473abc26e2cab9ab54d
plan_head_after: ec8e6cbdd4229bd08b19bc640e6ca8e8ad40f1e0

# Tech tracking
tech-stack:
  added: [gh 2.102.0 (local tool, homebrew-core)]
  patterns:
    - "Docs compliance as tests: the disclosure table is parsed from README.md and checked for empty cells and duplicate components"
    - "README.md doubles as the Qollab write-up (kept under 65,000 characters by a test)"

key-files:
  created:
    - LICENSE
    - README.md
    - tests/test_docs.py
    - docs/QOLLAB-RUNTIME.md
  modified: []

key-decisions:
  - "Disclosure rows and license values copied from RESEARCH's sourced block exactly; Claude Code carries 'hosted service (Claude Opus and Sonnet models)' as its version so no cell is blank"
  - "test_disclosure_one_row_per_component checks the whole qiskit-ionq row (joined cells) for 1.0.2 and 1.1.1, as the plan words it"
  - "Upload set computed by git archive is now 7 files: LICENSE, README.md, data/smoke_probe.json, main.py, neutron_qae/__init__.py, neutron_qae/smoke.py, requirements.txt"

patterns-established:
  - "Placeholder text in docs/QOLLAB-RUNTIME.md (ACCEPTED / REJECTED, N, X) is deliberate and replaced by plan 01-03"

requirements-completed: [DOCS-06, PLAT-03]

coverage:
  - id: D1
    description: "MIT LICENSE with the canonical permission and warranty text and the 2026 copyright line"
    requirement: "PLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_docs.py#test_mit_license_present"
        status: pass
      - kind: other
        ref: "diff of LICENSE against the RESEARCH LICENSE block (identical); head -n 1 LICENSE prints MIT License"
        status: pass
    human_judgment: false
  - id: D2
    description: "README.md carries 'This effort is supported by Qollab & IonQ.' byte-for-byte on its own line and stays under the 65,000-character write-up limit"
    requirement: "PLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_docs.py#test_readme_attribution_and_disclosure"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py#test_readme_fits_qollab_writeup"
        status: pass
      - kind: other
        ref: "grep -qxF 'This effort is supported by Qollab & IonQ.' README.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "Disclosure table lists every external library and AI tool (9 rows, 4 non-empty cells each, unique components, qiskit-ionq row with 1.0.2 and 1.1.1) followed by the team-may-use statement"
    requirement: "DOCS-06"
    verification:
      - kind: unit
        ref: "tests/test_docs.py#test_disclosure_table_has_no_empty_cells"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py#test_disclosure_one_row_per_component"
        status: pass
    human_judgment: false
  - id: D4
    description: "LICENSE and README.md ship in the Qollab upload set"
    requirement: "PLAT-03"
    verification:
      - kind: unit
        ref: "tests/test_docs.py#test_license_and_readme_ship_to_qollab"
        status: pass
      - kind: other
        ref: "git archive --format=tar HEAD | tar -t (7 files incl. LICENSE, README.md)"
        status: pass
    human_judgment: false
  - id: D5
    description: "README run instructions and browser note are clear and accurate for a judge (wording quality, no test asserts readability)"
    requirement: "DOCS-06"
    verification:
      - kind: other
        ref: "grep for WebAssembly JSPI, Firefox 153, '## Run it on Qollab', '## Run it locally', '## Rules every module follows'"
        status: pass
    human_judgment: true
    rationale: "Clarity of the instructions for a judge and the accuracy of the license wording (A8/A9: not legal advice) are judgment calls"
  - id: D6
    description: "docs/QOLLAB-RUNTIME.md exists with its four sections, static facts and the ideal_mode explainer, ready for plan 01-03"
    verification:
      - kind: unit
        ref: "tests/test_docs.py#test_runtime_record_has_sections"
        status: pass
    human_judgment: false
  - id: D7
    description: "GitHub CLI installed for plan 01-04"
    verification:
      - kind: other
        ref: "gh --version -> gh version 2.102.0 (2026-09-30)"
        status: pass
    human_judgment: false

# Metrics
duration: 11min
completed: 2026-10-10
status: complete
---

# Phase 1 Plan 02: LICENSE, README disclosure and runtime record Summary

**MIT LICENSE plus a README that carries the verbatim "This effort is supported by Qollab & IonQ." line, judge-facing Qollab/local run instructions with the JSPI browser note, and a 9-row library and AI-tool disclosure, all guarded by seven docs tests; docs/QOLLAB-RUNTIME.md is ready for plan 01-03, and gh 2.102.0 is installed for plan 01-04**

## Performance

- **Duration:** 11 min
- **Started:** 2026-10-10T18:37:19Z
- **Completed:** 2026-10-10T18:48:39Z
- **Tasks:** 2
- **Files modified:** 4 created

## Accomplishments

- LICENSE is the canonical MIT text, identical (diff) to the RESEARCH block, holder line `Copyright (c) 2026 Hippolyte Delloye and contributors` (confirmable at plan 01-04)
- README.md (6,573 characters) has the sections in plan order: title + intro + attribution line, Status, Run it on Qollab, Run it locally, Repository layout, Rules every module follows, Libraries, tools and licenses (disclosure), License
- Disclosure table: Qiskit, qiskit-ionq, NumPy, SciPy / Matplotlib, qiskit-aer + qiskit-algorithms, pytest + ruff, Pyodide, Claude Code (Anthropic), GSD Core (@opengsd/gsd-core), then the confirmation paragraph
- Seven docs tests; full suite 35 passed (28 from 01-01 + 7 new)
- Qollab upload set (`git archive HEAD`) is now 7 files: LICENSE, README.md, data/smoke_probe.json, main.py, neutron_qae/__init__.py, neutron_qae/smoke.py, requirements.txt
- docs/QOLLAB-RUNTIME.md: 9 static-fact bullets, the `### What the ideal_mode values test` subsection, the 11-column empty runs table, the raw-reports placeholder, and the 5 research conclusion bullets plus the Phase 6 re-check bullet
- `gh --version`: `gh version 2.102.0 (2026-09-30)` / `https://github.com/cli/cli/releases/tag/v2.102.0`. `gh auth login` was not run (Hippolyte's step in 01-04)

## Task Commits

1. **Task 1: MIT LICENSE, README with verbatim attribution and full disclosure, and the docs tests** - `9b6389f` (docs)
2. **Task 2: Runtime-findings record, its section test, and the GitHub CLI** - `ec8e6cb` (docs)

**Plan metadata:** recorded in the docs(01-02) commit that adds this SUMMARY

## Files Created/Modified

- `LICENSE` - MIT license text
- `README.md` - project write-up (also the Qollab write-up): attribution, run instructions, layout, module rules, disclosure
- `tests/test_docs.py` - `test_mit_license_present`, `test_readme_attribution_and_disclosure`, `test_disclosure_table_has_no_empty_cells`, `test_disclosure_one_row_per_component`, `test_license_and_readme_ship_to_qollab`, `test_readme_fits_qollab_writeup`, `test_runtime_record_has_sections`
- `docs/QOLLAB-RUNTIME.md` - runtime findings record for Phases 4-6

## Decisions Made

- Every license and version value in the disclosure table comes from the RESEARCH block and its License sources paragraph; nothing was guessed or added.
- README documents only behaviour verified in the code: ideal_mode values from `IDEAL_MODES`, perf probe skipped on IonQ, `scripts/run_local.py` flags `--backend basic|aer` and `--shots`.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

- `brew install gh` also ran Homebrew's automatic cleanup, which removed leftover temporary cellar directories under `/opt/homebrew/var/homebrew/tmp/.cellar/` (Homebrew's own scratch data, not installed formulae). No effect on the project.
- The existing expected `UserWarning: Option noise_model is not used by this backend` from 01-01's kwarg test still appears; not a failure.

## Known Stubs

- `docs/QOLLAB-RUNTIME.md` Empirical runs table has no data rows, Raw reports holds only the HTML comment placeholder, and Conclusions holds `ACCEPTED / REJECTED`, `...`, `~N`, `X s` and `<user>/<project>` placeholders. Intentional: plan 01-03 Task 3 fills them from pasted `QOLLAB_RUNTIME_REPORT=` lines and adds `test_runtime_findings_recorded`.

## User Setup Required

None for this plan. Plan 01-04 needs Hippolyte to run `gh auth login`.

## Next Phase Readiness

- Ready for 01-03: the README is complete before the Qollab upload, so it becomes the write-up when the project is created from `git archive` (7 files).
- Ready for 01-04: `gh` is installed; only authentication remains. The LICENSE holder line is still the default and awaits Hippolyte's confirmation.

## Self-Check: PASSED

- LICENSE, README.md, tests/test_docs.py, docs/QOLLAB-RUNTIME.md exist on disk.
- Commits `9b6389f` and `ec8e6cb` are ancestors of HEAD; `git rev-list --count 7b17a19..HEAD` = 2.
- Every acceptance criterion of both tasks re-run and passing; plan verification: `pytest -q` 35 passed, attribution on its own line, `gh --version` prints `gh version 2.102.0`.

---
*Phase: 01-qollab-smoke-test-compliant-skeleton*
*Completed: 2026-10-10*
