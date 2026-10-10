---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "`main()` crashes before any job on Aer noise-model backends, because `NoiseModel` is not JSON-serialisable"
  - id: WR-01
    severity: warning
    disposition: open
    title: "Failures outside `run_toy`'s `try`, and anywhere in `perf_probe`, lose the whole report"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The one-job-per-run guard relies on a module-name denylist, so an unrecognised remote backend gets a second job"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The `noise_verdict` heuristic mislabels runs, and Phase 4 decisions rest on it"
  - id: WR-04
    severity: warning
    disposition: open
    title: "A free-text `ideal_mode` typo in the Qollab form crashes the judged run"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Compliance gates have confirmed false negatives (and one false positive)"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`tests/test_compliance.py` claims every check has a negative test; four have none"
  - id: WR-07
    severity: warning
    disposition: open
    title: "The data literal-path test fails on macOS `.DS_Store` files and on single-quoted literals"
  - id: WR-08
    severity: warning
    disposition: open
    title: "README's IonQ instructions contradict the recorded logged-out run"
  - id: IN-01
    severity: info
    disposition: open
    title: "`_package_of` has two identical branches"
  - id: IN-02
    severity: info
    disposition: open
    title: "`runtime_report` catches only `OSError` when reading the probe file"
  - id: IN-03
    severity: info
    disposition: open
    title: "`sendFile` failures other than `ImportError` crash the run before the verdict line"
  - id: IN-04
    severity: info
    disposition: open
    title: "`scripts/run_local.py` always exits 0 and exposes only `--shots`"
  - id: IN-05
    severity: info
    disposition: open
    title: "Stale comment in the upload test"
  - id: IN-06
    severity: info
    disposition: open
    title: "`requires-python` disagrees with the documented local requirement"
  - id: IN-07
    severity: info
    disposition: open
    title: "`_version` dynamically imports `qiskit_ionq` from code reachable from `main.py`, invisibly to the gate"
open: 16
total: 16
recorded: 2026-10-10T20:16:38.728Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
