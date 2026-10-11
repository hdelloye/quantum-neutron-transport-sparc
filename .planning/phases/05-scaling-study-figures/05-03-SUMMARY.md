---
phase: 05-scaling-study-figures
plan: 03
subsystem: docs
tags: [results, markdown, drift-test, readme, bundle, claims-discipline, anly-05]
status: complete

# Dependency graph
requires:
  - phase: 05-scaling-study-figures (05-01)
    provides: "artifacts registry + envelope v1, data/scaling_rmse.json + fig_scaling_rmse.png, render_figures.py --check"
  - phase: 05-scaling-study-figures (05-02)
    provides: "data/exit_histograms.json, truncation_bias.json, thickness_study.json and their PNGs; slow-marker move of the four-figure render test"
provides:
  - "artifacts.format_markdown(doc): stdlib, deterministic Markdown table(s) for all four kinds (validates first; no trailing newline)"
  - "artifacts.headline_sentence(doc): fitted slopes +- SE for the scaling series (Aer part omitted when null)"
  - "docs/RESULTS.md: six sections, four figures, every table embedded verbatim from the committed JSON"
  - "README.md ## Results: headline figure, headline sentence, one bullet per study, IonQ and sampling-complexity caveats; Phase 5 status, sweep commands, layout"
  - "tests/test_results_doc.py: drift gate per artifact, README headline, figure-link resolution, sections/caveats, un-negated claim gate (11 tests)"
  - "~/Desktop/qollab-phase5.zip: audited 30-file Qollab upload bundle (outside the repo)"
affects: [phase-6, docs-05, readme, qollab-publish]

# Actuals (#2632)
actuals:
  tokens: 6508        # chars/4 over the added lines of the realized diff 0a66bd5..f4bb14a (26,031 chars)
  tasks: 2
  commits: 2          # measured: git rev-list --count 0a66bd5..HEAD at SUMMARY time
plan_head_before: 0a66bd56f60ac1dd57b3112b37df0e9bdd86ae9a
plan_head_after: f4bb14a86ef94685fcba1154d5d6e58f2af2487b

tech-stack:
  added: []
  patterns:
    - "Docs generated from data: tables and the headline sentence are formatter output on committed JSON, pasted verbatim and drift-tested"
    - "Claims gate: every 'speedup' / 'quantum advantage' in README and RESULTS must have 'no ' or 'not ' in the 40 preceding characters"
    - "Figure links are relative, resolve to git-tracked files under data/, never remote"

key-files:
  created:
    - docs/RESULTS.md
    - tests/test_results_doc.py
  modified:
    - neutron_qae/artifacts.py
    - README.md

key-decisions:
  - "PD-32 (docs from data): every result number in docs/RESULTS.md tables and the README headline sentence is produced by artifacts.format_markdown / headline_sentence from the committed JSON and embedded verbatim; tests fail on drift; prose may only quote the same formatted strings or round them"
  - "Formatter details beyond the contract: thickness headers derive '1%' and '1e-3' from target_rel_rmse / target_abs_rmse; unbracketed costs print 'not bracketed'; the IonQ line's source name is the first comma field of the JSON label"

patterns-established:
  - "New artifact kind = registry entry + validator + renderer + _FORMATTERS entry + its table pasted into docs/RESULTS.md (the parametrized drift test picks it up automatically)"

requirements-completed: [ANLY-05]

coverage:
  - id: D1
    description: "format_markdown / headline_sentence turn each committed artifact into Markdown without matplotlib; quick-profile docs with null Aer and IonQ format without those rows"
    requirement: ANLY-05
    verification:
      - kind: unit
        ref: "tests/test_results_doc.py#test_format_markdown_handles_quick_profile"
        status: pass
      - kind: unit
        ref: "tests/test_artifacts.py#test_artifacts_module_is_stdlib_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/RESULTS.md embeds every artifact table and the headline sentence verbatim; README carries the headline sentence"
    requirement: ANLY-05
    verification:
      - kind: unit
        ref: "tests/test_results_doc.py#test_results_doc_embeds_every_artifact_table"
        status: pass
      - kind: unit
        ref: "tests/test_results_doc.py#test_readme_carries_headline_sentence"
        status: pass
    human_judgment: false
  - id: D3
    description: "Claims discipline and link hygiene in README.md and docs/RESULTS.md (sections, caveat phrases, negated speedup mentions, committed relative figure links)"
    requirement: ANLY-05
    verification:
      - kind: unit
        ref: "tests/test_results_doc.py#test_no_unnegated_speedup_claims"
        status: pass
      - kind: unit
        ref: "tests/test_results_doc.py#test_figure_links_resolve"
        status: pass
      - kind: unit
        ref: "tests/test_results_doc.py#test_results_doc_sections_and_caveats"
        status: pass
    human_judgment: false
  - id: D4
    description: "Audited 30-file Qollab upload bundle built by git archive from f4bb14a"
    requirement: ANLY-05
    verification:
      - kind: other
        ref: "git archive --format=zip -o ~/Desktop/qollab-phase5.zip HEAD + manifest/size/secret audit -> BUNDLE OK 30"
        status: pass
    human_judgment: false
  - id: D5
    description: "README Results section reads honestly and stands on its own if Qollab does not render the embedded PNG (flag A-4)"
    verification: []
    human_judgment: true
    rationale: "Readability and Qollab write-up rendering are judgment and platform checks; Phase 6 publish check owns A-4"

duration: 22min
completed: 2026-10-11
---

# Phase 5 Plan 03: Results write-up, README Results section and upload bundle Summary

**Stdlib `format_markdown` tables for all four committed artifacts, embedded verbatim in a six-section docs/RESULTS.md and a README `## Results` section (headline: slopes -0.50 +- 0.01 classical, -1.02 +- 0.03 MLAE analytic, -1.03 +- 0.05 Aer), with drift, link and un-negated-claim gates. The 30-file Qollab bundle passes its audit.**

## Performance

- **Duration:** about 22 min
- **Started:** 2026-10-11T16:33:39Z
- **Completed:** 2026-10-11T16:56:03Z
- **Tasks:** 2 / 2
- **Files:** 2 created, 2 modified

## Evidence lines

- Tracer: `RESULTS TRACER OK Fitted slopes: -0.50 +- 0.01 (classical lattice MC, 13 points), -1.02 +- 0.03 (MLAE, analytic runner, M = 2..11), -1.03 +- 0.05 (MLAE, Aer circuit simulation, M = 2..9).` These match the planner's values. The tracer feedback gate re-ran the automated verify, it passed, and execution expanded to Task 2.
- Default suite: `385 passed, 6 skipped, 1 xfailed, 1 warning in 27.11s` (real 27.44 s). It was 374 passed before this plan; the 11 new tests add about 0.1 s. `git status --porcelain` was unchanged.
- Slow suite: `NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow` gives `6 passed, 386 deselected in 88.39s`. The plan text says 5; 05-02 moved the four-figure render test behind `slow`, which makes 6. None were skipped or failed.
- `RENDER CHECK OK 4`; `GOLDEN OK kernels_v1.json T1=0.24300446519524305`.
- Frozen files: `git diff --quiet 60bf3c5 -- <frozen list>` exits 0. `git diff --numstat 60bf3c5 -- main.py` gives `1	1	main.py`. Nothing under data/ changed.
- QAE tracer: `run_local.py --seed 2026` gives a_hat 0.2450944623 (a=0.245094), N_A 18000, hits [262, 1000, 277, 997], then `QAE RUN COMPLETED`. Smoke: `SMOKE TEST PASSED`.
- Bundle: `BUNDLE OK 30`. `~/Desktop/qollab-phase5.zip` has sha256 `28b74fb5f72d0971c10bf98b05c5996e2f93817297c93832a4bcbcc51d04e03e` and is 377,990 bytes, built by `git archive` from f4bb14a. It holds exactly the expected 30 files (the 19 from Phase 4, plus analysis.py, artifacts.py, figures.py and the eight data/ artifacts). Every file is at most 2,000,000 bytes and no text file contains a secret-shaped string.
- README is 17,746 characters (Python `len`; 17,749 bytes), under the 65,000 limit. It keeps the attribution line and the disclosure table; `tests/test_docs.py` and `tests/test_quantum_doc.py` pass.

## Accomplishments

- `neutron_qae/artifacts.py` gained `format_markdown(doc)` and `headline_sentence(doc)`. They need only the standard library, have no matplotlib dependency and are deterministic. They validate the document first and raise ValueError for an unregistered kind, or for a headline sentence requested from a non-scaling doc. Phase 6 can print these tables on Qollab.
- `docs/RESULTS.md` has six sections: Headline, Exit-position histograms, Truncation bias, Wall-thickness study, Reproduce, and Limits of this evidence. It links four figures with `../data/` paths and embeds every table verbatim. It covers the M = 3 to 4 plateau explanation, the Aer cross-check and the IonQ caveat. It states the relative-error reading of the thickness ratio with the absolute-target disclosure (18.10 to 5.04), measured run times, and the quick-profile warning (`--out-dir`, never overwrite the full artifacts).
- `README.md` got a Phase 5 Status paragraph and a `## Results` section placed after the quantum section. That section has the embedded headline figure, the headline sentence, six bullets (Aer, histograms, truncation, thickness, IonQ, sampling complexity only) and a link to RESULTS.md. `## Run it locally` now lists the sweep and render commands. The layout lists artifacts/analysis/figures, the eight data files, the five Phase 5 scripts and RESULTS.md. The Matplotlib disclosure row now says what it does: the figures in data/.

## Task Commits

1. **Task 1: Tracer (scaling JSON -> formatter -> RESULTS headline -> drift test)** - `0096944` (feat)
2. **Task 2: Remaining formatters, full RESULTS.md, README Results, gates, bundle audit** - `f4bb14a` (docs)

## Files Created/Modified

- `neutron_qae/artifacts.py` - `format_markdown` (four kinds), `headline_sentence`, table helpers
- `docs/RESULTS.md` - the Phase 5 results write-up (new)
- `README.md` - Status, Results, local commands, layout, disclosure row
- `tests/test_results_doc.py` - drift, link and claims gates (new, 11 tests)

## Decisions Made

- PD-32 is implemented as planned. Two small additions go beyond the contract. First, the thickness headers derive "1%" and "1e-3" from the JSON targets. Second, unbracketed quick-profile costs print `not bracketed` instead of failing.
- Measured run times in Reproduce come from each JSON's `provenance.timings_s.total` (70.77 s, 1.25 s, 11.45 s, 74.9 s), rounded.

## Provenance note (orchestrator request)

`analysis.cost_at_target` landed in `0d7c853` (05-01 Task 1). That is before the scaling artifact's `git_head` `cbabd4e`, so the cost_at_target caveat does not apply. `analysis.py` did change after `cbabd4e`: 05-02 (`e894566`, `dc99bef`) added histogram, chi-square and transmission-guard helpers. Those changes are purely additive (136 insertions; the one deletion is an import line that moved). The scaling series code the artifact was produced with is unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Wording accuracy] M = 3 to 4 plateau note**
- **Found during:** Task 1
- **Issue:** The plan's note says "3 theta and 9 theta near pi/2". 9 theta is about 4.64 rad, which is near 3 pi/2, not pi/2.
- **Fix:** The doc says "near odd multiples of pi/2". It also says the curve recovers when k = 8 enters at M = 5, which was checked against `mlae.exponential_schedule` and the RMSE values.
- **Commit:** 0096944

**2. [Rule 2 - Safety] Quick-profile reproduce instruction**
- **Found during:** Task 2
- **Issue:** The sweep scripts write to `data/` by default, so a quick run would overwrite the committed full-profile artifacts.
- **Fix:** Reproduce tells readers to pass `--profile quick --out-dir <scratch directory>` and never to overwrite the full files.
- **Commit:** f4bb14a

**3. [Note] Slow-suite count is 6, not 5**
- 05-02 moved `test_figures_render_from_committed_json` behind `slow`. All 6 pass. Nothing was changed.

**Total deviations:** 2 auto-fixed (1 wording, 1 safety), 1 expected-count note.
**Impact on plan:** No change to any number, test assertion, data file or frozen module.

## Known Stubs

None.

## Threat Flags

None. The new surface is docs, plus a stdlib formatter over already-validated JSON. T-05-08 (bundle audit), T-05-09 (drift and claims gates) and T-05-10 (link gate) are mitigated as planned. No package was installed (T-05-SC).

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness (Phase 6 handoff)

- **figures.py is not reachable from main.py.** In quick mode, main.py must import `neutron_qae.figures` (matplotlib loads on Pyodide when imported), call `render_*` on the loaded artifact dicts and then `plt.show()`. figures.py itself never calls `use` or `show`.
- **Tables without matplotlib.** `artifacts.format_markdown(artifacts.load_artifact(path, kind))` prints any table with no matplotlib. artifacts.py is already main-reachable and holds the literal data/ paths.
- **IonQ wording rules.** Wherever the IonQ result appears, call it an execution proof, 6.4 sigma off T1, cause open, and not in any fit. Never present it as scaling evidence. Every "speedup" or "quantum advantage" must be negated; `tests/test_results_doc.py` enforces this for README.md and docs/RESULTS.md.
- **WR-01 doc carry-over is still open.** The "same transpiled circuits" wording belongs to Phase 6; this plan did not repeat that claim.
- **A-4 is flagged.** Qollab's write-up view may not render the embedded PNG. The README Results text is written to stand on its own; Phase 6 should confirm this at publish.
- **Upload.** `~/Desktop/qollab-phase5.zip` (sha256 `28b74fb5...e03e`) is the audited 30-file bundle from f4bb14a. Rebuild it with `git archive` after any later commit.

## Self-Check: PASSED

- FOUND: docs/RESULTS.md, tests/test_results_doc.py, neutron_qae/artifacts.py, README.md, ~/Desktop/qollab-phase5.zip
- FOUND commits: 0096944 and f4bb14a, both ancestors of HEAD
