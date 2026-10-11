---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "The lattice engine silently renormalizes a malformed `first_collision`, giving a wrong T1 with no error"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`as_source` accepts the `numpy.random` module and legacy `RandomState`, routing engine draws through the global RNG"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The `-1` row sentinel mixes physical non-escape with zero-amplitude (noise) strings, but the contract asks callers to count the latter"
  - id: IN-01
    severity: info
    disposition: open
    title: "The documented `ValueError` for bad checkpoints is a `TypeError` for non-iterables"
  - id: IN-02
    severity: info
    disposition: open
    title: "Checkpoint prefixes are not the same histories as a standalone run of that size"
  - id: IN-03
    severity: info
    disposition: open
    title: "The Wald SE is exactly 0 at p in {0, 1}, which makes small-N z-scores degenerate"
  - id: IN-04
    severity: info
    disposition: open
    title: "`row_of(NaN)` maps silently to row 0, and `ContinuousHistories.yexit` is NaN for every non-back history"
  - id: IN-05
    severity: info
    disposition: open
    title: "The golden draw-count assertions pin a total, not the documented order, and one prefix golden depends on the numpy stream"
  - id: IN-06
    severity: info
    disposition: open
    title: "The first-collision column chi2 uses 17 degrees of freedom for 17 bins whose counts sum to n"
  - id: IN-07
    severity: info
    disposition: open
    title: "The 1e8 edge-row finding in the SUMMARY is attributed to the wrong cause"
  - id: IN-08
    severity: info
    disposition: open
    title: "Duplicated helpers, and result dataclasses that do not validate their own invariants"
open: 11
total: 11
recorded: 2026-10-11T01:34:24.051Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
