---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "IonQ runs with `ideal_mode = \"none\"` always fail and discard their counts (rounded counts never sum to shots)"
  - id: WR-01
    severity: warning
    disposition: open
    title: "The circuit submitted to IonQ is not the one the docs say was checked locally; records carry no way to verify it"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Malformed records crash the judged Built-in path and the ingest script with exceptions other than `ValueError`"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The record validator accepts `NaN` / `Infinity` and leaves several fields unchecked"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Records feeding the Built-in estimate are not checked for provenance or for the current contract, and are labelled \"IonQ Forte 1\""
  - id: WR-05
    severity: warning
    disposition: open
    title: "`fisher_se` reports a near-zero standard error at a = 0 or 1"
  - id: IN-01
    severity: info
    disposition: open
    title: "The strict xfail has no `raises=`, so any exception is recorded as XFAIL"
  - id: IN-02
    severity: info
    disposition: open
    title: "The xfail docstring overstates what turns the xfail off"
  - id: IN-03
    severity: info
    disposition: open
    title: "`_send_file` catches only `ImportError`"
  - id: IN-04
    severity: info
    disposition: open
    title: "Duplicate detection keys on the exact timestamp string"
  - id: IN-05
    severity: info
    disposition: open
    title: "The Q1lite request sizes in QUANTUM.md do not match the code"
  - id: IN-06
    severity: info
    disposition: open
    title: "Exact-digit tracer assertions depend on the unpinned NumPy random stream"
  - id: IN-07
    severity: info
    disposition: open
    title: "`mlae.estimate` silently picks one branch when there is no k = 0 record"
  - id: IN-08
    severity: info
    disposition: open
    title: "The `sampled` rule differs from qiskit-ionq's rule"
  - id: IN-09
    severity: info
    disposition: open
    title: "The README contradicts itself on logged-out IonQ runs"
  - id: IN-10
    severity: info
    disposition: open
    title: "The `BackendRunner` cache is keyed on k only"
open: 16
total: 16
recorded: 2026-10-11T07:21:19.957Z
---

# Phase 04: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| IN-10 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
