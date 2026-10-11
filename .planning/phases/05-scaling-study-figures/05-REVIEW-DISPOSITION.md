---
phase: 05
review: 05-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Underflow guard admits walls whose classical curve cannot reach 1% relative RMSE"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Quick-profile runs overwrite the committed full-profile artifacts by default"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`slope_se` is a residual-scatter statistic on correlated points, presented as a standard error"
  - id: WR-04
    severity: warning
    disposition: open
    title: "MLAE cost formula \"about 1/(eps sqrt(T))\" is off by ~30–40x from the measured costs"
  - id: WR-05
    severity: warning
    disposition: open
    title: "The M = 3–4 plateau explanation names the wrong mechanism"
  - id: WR-06
    severity: warning
    disposition: open
    title: "IonQ marker label and doc prose are hardcoded, not derived from or checked against the records"
  - id: WR-07
    severity: warning
    disposition: open
    title: "\"NaN and Infinity are rejected on load\" is false; oversized integers escape as OverflowError"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Quick-profile validator accepts an Aer series with `aer_M_max: null`, and the headline prints \"M = 2..None\""
  - id: WR-09
    severity: warning
    disposition: open
    title: "The validator accepts artifacts whose derived fields contradict their own data"
  - id: WR-10
    severity: warning
    disposition: open
    title: "`render_figures.py --check` does not compare figures with the committed PNGs"
  - id: IN-01
    severity: info
    disposition: open
    title: "Inaccurate cost-unit equivalences in RESULTS"
  - id: IN-02
    severity: info
    disposition: open
    title: "The speedup-claim lint is easy to defeat"
  - id: IN-03
    severity: info
    disposition: open
    title: "Duplicate JSON keys are silently accepted"
  - id: IN-04
    severity: info
    disposition: open
    title: "Figure text hardcodes study parameters"
  - id: IN-05
    severity: info
    disposition: open
    title: "The truncation SE could be paired and the within-K checks are not recorded"
  - id: IN-06
    severity: info
    disposition: open
    title: "Figure edge cases crash or misplot"
  - id: IN-07
    severity: info
    disposition: open
    title: "Sweeps fail late and non-atomically"
open: 17
total: 17
recorded: 2026-10-11T17:30:29.952Z
---

# Phase 05: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| WR-10 | warning | open | - |
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
