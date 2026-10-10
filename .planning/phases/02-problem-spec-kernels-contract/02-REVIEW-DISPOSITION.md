---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "PHYSICS.md claims the frozen model is \"15 times closer\" to the reference; its own table gives 7.25 times"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The \"read-only\" contract tables can be made writable again with `setflags(write=True)`"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`Kernels` validates only shapes; NaN, negative and non-normalised tables are accepted, and `build_kernels` emits NaN on underflow"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`derive_cross_sections.py --check` fails open on NaN and prints \"MICRO_14MEV REPRODUCED\""
  - id: WR-05
    severity: warning
    disposition: open
    title: "`--download` never verifies the recorded sha256 checksums, follows unrestricted redirects and does not check that Range was honoured"
  - id: WR-06
    severity: warning
    disposition: open
    title: "The golden guard's `--force` overwrites `kernels_v1.json` under the same version, and the documented change procedure does not match the code"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Per-entry flight and exit-row tables carry about 1e-3 absolute (2.5% relative) quadrature error from integrating across the exit-face discontinuity; undisclosed"
  - id: WR-08
    severity: warning
    disposition: open
    title: "The flight tables assume the scatter site lies on the beam line (y = beam_y), but neither the contract docstring nor PHYSICS.md says so"
  - id: IN-01
    severity: info
    disposition: open
    title: "`spec_fingerprint` treats an int override and the equal float as different specs"
  - id: IN-02
    severity: info
    disposition: open
    title: "`column_segments` has no bounds check, and a boundary near a column edge can yield a sliver segment"
  - id: IN-03
    severity: info
    disposition: open
    title: "`transmission_within` accepts `True` and `1.0`; `exit_row_distribution_k1` skips the layout check and does not use `fsum`"
  - id: IN-04
    severity: info
    disposition: open
    title: "The golden's `outcomes` and `spec` keys are written but never verified"
  - id: IN-05
    severity: info
    disposition: open
    title: "PHYSICS.md overclaims \"every number here is printed from the code\"; doc tests are loose substring searches"
  - id: IN-06
    severity: info
    disposition: open
    title: "Mismatched test comment and a tautological test"
  - id: IN-07
    severity: info
    disposition: open
    title: "Silent-zero and crash edge cases in the ENDF parser"
  - id: IN-08
    severity: info
    disposition: open
    title: "`freeze_kernels.py` writes non-atomically and ignores `--force` without `--write`"
  - id: IN-09
    severity: info
    disposition: open
    title: "Runtime tables are rebuilt on each platform; the golden is only checked locally"
open: 17
total: 17
recorded: 2026-10-10T23:40:21.111Z
---

# Phase 02: Code Review Disposition

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
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
