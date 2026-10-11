---
phase: 06-submission-documentation-handoff
plan: 02
subsystem: docs
tags: [readme, judging-criteria, limitations, handoff, wr-01, cr-01, wr-03, wr-04, wr-05, bundle-audit, public-audit]

requires:
  - phase: 06-01
    provides: quick mode as main()'s default, QUICK_REPORT= / QUICK MODE OK strings, IonQ CAVEAT line, CR-01 refusal, --figure-dir
  - phase: 05-scaling-study-figures
    provides: Results section, four figures, docs/RESULTS.md, 30-file bundle manifest
provides:
  - "Judge-facing README.md (also the Qollab write-up at project creation) with the DOCS-03 heading order"
  - "### Novelty with the three prior-art citations and only the narrowed PROJECT.md claim (DOCS-04)"
  - "## Limitations with seven ordered bullets incl. the open IonQ discrepancy (DOCS-05)"
  - "HANDOFF.md (DOCS-08): owners, test commands, Kernels contract change procedure, Qollab rules, what is left; export-ignored"
  - "WR-01/CR-01 wording fixed in docs/QUANTUM.md and docs/QOLLAB-RUNTIME.md; WR-03/WR-04/WR-05 fixed in README/docs/RESULTS.md"
  - "tests/test_submission_docs.py: 17 pure string tests (14 functions, 0.02 s)"
affects: [06-03 publish/video, GitHub teammates]

actuals:
  tokens: 16000
  tasks: 3
  commits: 3
plan_head_before: dff72f18c372cdd33f2bde1f5602989b06baf745
plan_head_after: c528b846e80729079ea6301e3a88fc7a22408ea5

tech-stack:
  added: []
  patterns:
    - "Docs-drift tests parse the code (main.py def line) rather than restating defaults"
    - "Generated RESULTS blocks stay verbatim; corrective notes go after the generated block"

key-files:
  created:
    - HANDOFF.md
    - tests/test_submission_docs.py
  modified:
    - README.md
    - docs/QUANTUM.md
    - docs/QOLLAB-RUNTIME.md
    - docs/RESULTS.md
    - .gitattributes

key-decisions:
  - "PD-36: HANDOFF.md is export-ignored (GitHub-only); the Qollab bundle stays the 30-file 05-03 manifest; README links to docs/ and HANDOFF.md stay relative and the GitHub URL is named once near the top"
  - "WR-03 fix without touching the frozen formatter: the generated headline sentence and Slope SE column stay verbatim; a following sentence labels the +- values as fit scatter"
  - "WR-04 fix: RESULTS keeps the classical cost law but states MLAE costs are read off measured curves only"

requirements-completed: [DOCS-03, DOCS-04, DOCS-05, DOCS-08]

coverage:
  - id: D1
    description: "README heading order, four criterion sections non-empty, quick mode documented from main.py's def line, four figures with alt text"
    requirement: DOCS-03
    verification:
      - kind: unit
        ref: "tests/test_submission_docs.py#test_readme_headings_in_order, test_readme_documents_quick_mode_from_code, test_readme_figures_have_alt_text, test_criteria_sections_non_empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "Novelty: three citations and the narrowed claim; banned novelty phrase absent"
    requirement: DOCS-04
    verification:
      - kind: unit
        ref: "tests/test_submission_docs.py#test_novelty_prior_art_and_narrowed_claim, test_banned_novelty_phrases_absent"
        status: pass
    human_judgment: false
  - id: D3
    description: "Seven limitations in order, one lead per bullet, between ### Documentation and ## Repository layout; 6.4 sigma on every 0.228671 line"
    requirement: DOCS-05
    verification:
      - kind: unit
        ref: "tests/test_submission_docs.py#test_limitations_section, test_ionq_estimate_always_has_caveat"
        status: pass
    human_judgment: false
  - id: D4
    description: "HANDOFF.md sections, owners for every module, commands, contract, what is left; not shipped to Qollab"
    requirement: DOCS-08
    verification:
      - kind: unit
        ref: "tests/test_submission_docs.py#test_handoff_sections_and_owners, test_handoff_commands_and_contract, test_handoff_what_is_left, test_handoff_not_shipped"
        status: pass
    human_judgment: false
  - id: D5
    description: "Review carry-overs: WR-01 wording gone, one-gate-per-A fact present; WR-03/04/05 wording fixed"
    verification:
      - kind: unit
        ref: "tests/test_submission_docs.py#test_wr01_wording_removed, test_phase5_review_wording_fixed"
        status: pass
    human_judgment: false
  - id: D6
    description: "README reads well for judges (tone, clarity, honesty of framing)"
    verification: []
    human_judgment: true
    rationale: "Prose quality for judges cannot be checked by string tests"

duration: 12min
completed: 2026-10-11
status: complete
---

# Phase 6 Plan 02: Submission Docs and Handoff Summary

**The README is now the judge-facing write-up: what it does, the problem, running it on Qollab (quick mode is the default) and locally, how to replicate the results, Results with all four figures, one section per judging criterion (the novelty section cites the three prior-art papers and makes only the narrowed claim), seven ordered limitations, then layout, rules and disclosure. HANDOFF.md is added and export-ignored. The WR-01, CR-01, WR-03, WR-04 and WR-05 wording is fixed, and 17 string tests guard all of it. Suite: 415 passed in 28.3 s. Audits print `BUNDLE OK 30` and `PUBLIC AUDIT OK`.**

## Performance

- **Duration:** about 12 min
- **Started:** 2026-10-11T17:53:23Z
- **Completed:** 2026-10-11T18:05Z
- **Tasks:** 3 of 3
- **Files modified:** 7 (README.md, HANDOFF.md, .gitattributes, docs/QUANTUM.md, docs/QOLLAB-RUNTIME.md, docs/RESULTS.md, tests/test_submission_docs.py)

## Accomplishments

- **README:** 25,533 characters, under the 65,000 limit. Headings in order:
  - What it does
  - The problem
  - Run it on Qollab
  - Run it locally
  - Replicate the results
  - Results
  - Judging criteria (Novelty, Technical execution, Impact, Documentation)
  - Limitations
  - Repository layout
  - Rules every module follows
  - Libraries, tools and licenses (disclosure)
  - License
- **What README states:**
  - It gives the GitHub URL.
  - It documents the quick-mode output in order: contract, `QUICK MLAE`, the verbatim IonQ CAVEAT line, the four figures with PNG downloads, `QUICK_REPORT=`, then `QUICK MODE OK` or `QUICK MODE INCOMPLETE`.
  - It gives the CR-01 refusal and the browser (JSPI) note.
  - It covers the IonQ one-circuit runs, `--figure-dir` and the slow suite.
- **Novelty:**
  - Cites Olivier & Nowak (arXiv:2410.19489), Lee, Lee & Kim (Phys. Rev. D 111, 116001; arXiv:2502.14374) and Miao, Jin & Sone (arXiv:2607.10772).
  - Then the sentence "To our knowledge, this is the first end-to-end QAE estimate of a neutron transport tally through a two-material fusion first wall, with measured error-versus-oracle-query scaling against a matched classical baseline."
- **Limitations:** seven bullets in the DOCS-05 order. The IonQ bullet gives 0.228671 and 6.4 sigma on the same line, the one-gate-per-A browser transpile fact, and says the cause is open.
- **Docs fixes:**
  - docs/QUANTUM.md and docs/QOLLAB-RUNTIME.md: the "same transpiled circuit" wording is replaced by the WR-01 fact (556/3016/5476 gates against 555/3013/5471; not simulated locally; no fingerprint). The CR-01 statements now say `none` is refused, and noisy runs are a HANDOFF item.
  - docs/RESULTS.md:
    - WR-04: the MLAE cost law is removed.
    - WR-05: the plateau is now explained as count saturation (p(k=1) = 0.9994, about 0.18 expected misses in 300 shots).
    - WR-03: the slope +- values are labelled fit scatter.
- **HANDOFF.md** has five sections:
  - Module owners: 18 rows, all owned by Hippolyte Delloye, with a claim-by-PR rule.
  - Run the tests.
  - The frozen Kernels contract.
  - Qollab rules.
  - What is left: 8 numbered items.

## Task Commits

1. **Task 1 (tracer): criteria, novelty, limitations, gating tests:** `2f25b33` (docs). The tracer gate re-ran the four docs test files (31 passed, 1 skipped) and printed `BUNDLE OK 30` (exact manifest).
2. **Task 2: full README and the WR-01, CR-01, WR-03, WR-04 and WR-05 doc fixes:** `dd6309b` (docs). Printed `README OK 25530 chars, 16 headings`; `grep -ci 'same transpiled circuit'` gives 0 for all three files.
3. **Task 3: HANDOFF.md, export-ignore, handoff tests:** `c528b84` (docs)

## Verification output

- `SUITE OK 415 passed, 7 skipped, 1 xfailed, 1 warning in 28.27s`, with an unchanged porcelain listing.
- `GOLDEN OK kernels_v1.json T1=0.24300446519524305`
- The quick run ends with `QUICK MODE OK`.
- `PUBLIC AUDIT OK`
- `BUNDLE OK 30`: HANDOFF.md, .planning/, docs/, tests/ and scripts/ are all absent from the bundle.
- None of this plan's commits touches main.py, neutron_qae/, data/ or tests/golden.

## Decisions Made

- **PD-36:** HANDOFF.md is export-ignored, and the bundle stays at 30 files.
- **WR-03, fixed without touching the frozen formatter:** the verbatim headline sentence and the Slope SE column stay as they are. A following sentence (README, and RESULTS after the generated block) calls the +- values fit scatter, not sampling standard errors.
- **"Within one standard error" removed:** the claim is replaced by the two fitted slopes (-1.02 and -1.03, or -1.015 and -1.031).

## Deviations from Plan

**1. [Rule 1: Bug] The fit-scatter note was placed inside the generated table block in RESULTS**
- **Found during:** Task 2
- **Issue:** The note sat between the scaling table and the IonQ marker line. That broke the verbatim `format_markdown` match (`test_results_doc_embeds_headline`).
- **Fix:** Moved the note after the generated block (after the "Repetitions per point" line).
- **Commit:** `dd6309b`

**2. [Scope note] Orchestrator-mandated docs/RESULTS.md edits**
- docs/RESULTS.md is not in the plan's `files_modified`. It was edited because the orchestrator notes require the WR-03/04/05 fixes.
- The WR-03/04/05 test is `test_phase5_review_wording_fixed`. It strips whitespace, so it also catches the spaced form `1 / (eps sqrt(T))` that RESULTS actually used.

**3. [Test ordering] The WR test moved from Task 1 to Task 2**
- That test was drafted in Task 1 but committed in Task 2, together with the fixes it gates.
- Until Task 3, the HANDOFF parametrisation of `test_banned_novelty_phrases_absent` skipped because the file did not exist yet. It passes now.

No slow-marker move was needed: the suite runs in 28.3 s, under the 30 s gate.

## Issues Encountered

- The plan's `SUITE OK` check (`'failed' not in s`) would match the pre-existing `1 xfailed`. It was run with `' failed'` instead, as the orchestrator advised.

## Known Stubs

- README sentence: "The live Qollab project and the demo video are linked from the Qollab project card." This is intentional. 06-03 replaces it with the live URLs (see the handoff below).

## Next Phase Readiness (06-03 handoff)

- **HEAD to upload:** `c528b84`, or the docs commit that follows it. Build the bundle with `git archive --format=zip -o <zip> HEAD`, which gives the 30-file manifest.
- Qollab copies README.md into the write-up only when a fresh project is created. Create a fresh project from this bundle to get the new write-up.
- **Sentence for 06-03 to replace:** README line 7, `Source code: https://github.com/hdelloye/quantum-neutron-transport-sparc. The live Qollab project and the demo video are linked from the Qollab project card.` Replace the second sentence with the live Qollab URL and the video URL. Keep the GitHub URL: `test_readme_documents_quick_mode_from_code` requires it.
- Still open in STATE:
  - collaborators (PLAT-03)
  - making the repo public
  - the IonQ discrepancy (documented as open)

---
*Phase: 06-submission-documentation-handoff*
*Completed: 2026-10-11*

## Self-Check: PASSED
