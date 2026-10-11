---
phase: 05-scaling-study-figures
verified: 2026-10-11T12:30:00Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - ".planning/phases/05-scaling-study-figures/05-01-PLAN.md"
  - ".planning/phases/05-scaling-study-figures/05-01-SUMMARY.md"
  - ".planning/phases/05-scaling-study-figures/05-02-PLAN.md"
  - ".planning/phases/05-scaling-study-figures/05-02-SUMMARY.md"
  - ".planning/phases/05-scaling-study-figures/05-03-PLAN.md"
  - ".planning/phases/05-scaling-study-figures/05-03-SUMMARY.md"
  - "README.md"
  - "data/exit_histograms.json"
  - "data/scaling_rmse.json"
  - "data/thickness_study.json"
  - "data/truncation_bias.json"
  - "docs/RESULTS.md"
  - "main.py"
  - "neutron_qae/analysis.py"
  - "neutron_qae/artifacts.py"
  - "neutron_qae/figures.py"
  - "scripts/render_figures.py"
covered_digest: "v3:sha256:63bb73d482d203f37bd17818e140cabd4bd1cd904591d06c75bdfa3c7264cd98"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: Scaling Study & Figures Verification Report

**Phase Goal:** The Core Value evidence exists: on the same discrete problem, RMSE against the exact value falls roughly as 1/N_A for MLAE versus 1/sqrt(N_A) for matched classical MC, with supporting exit histograms, a truncation-bias disclosure and a wall-thickness rare-event study, all committed as precomputed artifacts.
**Verified:** 2026-10-11
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Log-log RMSE vs N_A, >= 50 reps, vs exact lattice value, slopes near -0.5 (classical) and -1 (MLAE) | VERIFIED | `data/scaling_rmse.json`: profile full, seed 2026, reference_T1 = 0.24300446519524305, repetitions = 100 at every point. I refit from the stored arrays in an isolated Python run: classical 13 points slope -0.49766 (SE 0.00524); MLAE analytic M>=2 slope -1.01509 (SE 0.02903); MLAE Aer M>=2 slope -1.03089 (SE 0.04765). These equal the stored fits to ~1e-15 and fall inside the plan bands. Cost for MLAE equals 300(2^M+M-2) (300 ... 617,100), classical cost is histories (100 ... 1e6). Aer/analytic RMSE ratio is 0.80 to 1.16 at every shared M. Figure inspected: curves, slope labels, 16-84 band, sampling-complexity title all present. |
| 2 | Overlaid exit histograms, classical vs direct Q1 sampling at matched shots, labelled circuit validation | VERIFIED | `data/exit_histograms.json`: 1,000,000 classical and 1,000,000 quantum shots; chi-square 16.46 / 17.01 / 13.14 vs bound 44.28 (dof 16); quantum outside_support 0, flag_mismatch 0; quantum flag_hits 242,507 and classical transmitted 243,123 (about T1 = 0.2430). JSON `label` is `circuit validation, not speedup evidence`, and the same text is the figure title. |
| 3 | Truncation-bias figure/table: transmission within K collisions vs full continuous | VERIFIED | `data/truncation_bias.json`: walls 6/10/15/20/30 cm transport-corrected plus 10 cm isotropic_raw. Bias/SE is 4.4 to 7.9 (>= 3 SE) for every corrected wall; coverage is 0.99886 / 0.99687 (10 cm, the ~99.7% disclosed) / 0.99566 / 0.99507 / 0.98909 and 0.8987 for isotropic_raw; within(0)/within(1) are consistent with exact T0/T1. Disclosed in docs/RESULTS.md (Truncation bias section) and the README. |
| 4 | >= 3 thicknesses, classical-to-MLAE ratio grows as transmission falls | VERIFIED | `data/thickness_study.json`: 5 walls, each with contract_abs_diff <= ~1e-13, `target_rel.bracketed` true for all, ratio 1.99 / 4.27 / 7.77 / 15.54 / 25.84 as T1 falls 0.419 to 0.0154; `ratio_increases_as_T1_falls` true, span 12.96 (>= 4 required). The shrinking absolute-target ratio (18.1 to 5.0) is disclosed in the JSON, the figure and RESULTS.md. |
| 5 | Results committed as JSON/PNG <= 2 MB each; figures re-render from the files without rerunning the sweep | VERIFIED | Eight data files tracked in git, largest 87,804 bytes, none above 2,000,000 (`find data -size +2000000c` empty). `scripts/render_figures.py --check` prints `RENDER CHECK OK 4`. `neutron_qae/artifacts.py` is stdlib-only and reached from `main.py` by one changed import line (`git diff --numstat 60bf3c5 -- main.py` gives `1 1 main.py`). Full-profile provenance: seed 2026, git_dirty false, real commit hashes (the scaling head `cbabd4e` exists in the repo). |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified).

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `neutron_qae/artifacts.py`, `analysis.py`, `figures.py` | VERIFIED | Substantive, wired. `main.py` imports `artifacts`; `figures.render_file` loads from JSON. |
| `scripts/sweep_scaling.py`, `sweep_histograms.py`, `sweep_truncation.py`, `sweep_thickness.py`, `render_figures.py` | VERIFIED | Present; their committed outputs carry matching provenance script names. |
| `data/{scaling_rmse,exit_histograms,truncation_bias,thickness_study}.json` and the four `fig_*.png` | VERIFIED | Present, tracked, within budget, profile full, git_dirty false. |
| `docs/RESULTS.md`, `README.md ## Results` | VERIFIED | Tables are the generated `format_markdown` output (drift gate in `tests/test_results_doc.py`); headline sentence and figure embedded. |

### Key Link Verification

| From | To | Status |
|------|----|--------|
| main.py -> neutron_qae/artifacts.py (literal data paths in import graph) | WIRED (one-line import) |
| sweep scripts -> analysis.py (loglog_fit, series fns) | WIRED |
| figures.py -> artifacts.load_artifact (render from JSON only) | WIRED (`RENDER CHECK OK 4`) |
| docs/RESULTS.md -> data/*.json via format_markdown | WIRED (drift test passes) |

### Behavioral Spot-Checks and Test Evidence

| Check | Result |
|-------|--------|
| `.venv/bin/python -m pytest -q` | 385 passed, 6 skipped, 1 xfailed in 28.5 s (the xfail is the known, documented IonQ 6.4-sigma finding, not loosened) |
| `NEUTRON_QAE_SLOW=1 pytest -m slow tests/test_artifacts.py tests/test_studies.py tests/test_results_doc.py` | 1 passed (the four-figure render test moved to `slow` in 05-02; still green) |
| `scripts/render_figures.py --check` | `RENDER CHECK OK 4` |
| `scripts/freeze_kernels.py` | `GOLDEN OK kernels_v1.json T1=0.24300446519524305` |
| Independent refit of all three slopes from stored arrays | Matches stored fits and the doc |
| Frozen Phase 2/3/4 modules (`exact.py`, `kernels.py`, `mc_lattice.py`, `oracle.py`, `mlae.py`, `runners.py`) | Unchanged vs 60bf3c5 (empty diff) |
| Tracked-file status of data/, neutron_qae/, scripts/, docs/, README.md, main.py | Clean (only `.planning/` working files are modified/untracked) |

### Probe Execution

No `probe-*.sh` scripts are declared or conventionally present for this phase. Step 7c: not applicable.

### Prohibitions

| Prohibition | Tier | Result |
|-------------|------|--------|
| No IonQ record in any fit | test | `ionq_marker.in_fit` is false, label says `execution proof ... not in any fit`; slopes recompute from the three simulator series only. Satisfied. |
| Cost axis is N_A = sum shots(2k+1), never shots or num_oracle_queries | test | Stored MLAE cost equals 300(2^M+M-2) exactly. Satisfied. |
| No sweep at import or in the default suite | test | Default suite 28 s, only micro configs. Satisfied. |
| Frozen modules and `main.py` untouched beyond one import line | test | Verified by diff and numstat. Satisfied. |
| No artifact above 2 MB or outside data/ | test | Verified. Satisfied. |
| No wall-clock speedup or quantum-advantage claim | judgment | A grep of README.md and docs/RESULTS.md found no non-negated "speedup" or "quantum advantage"; RESULTS.md states "sampling complexity only", "not a wall-clock comparison". I read the headline figure and the thickness figure titles; neither claims a speedup. This is a non-authoritative LLM-judge verdict; a human skim of the demo script/video wording in Phase 6 is advisable, but nothing flagged here. |
| Matplotlib not reachable from `main.py`; no backend selected in package | test | Covered by the passing artifact gates. Satisfied. |
| Histogram not presented as speedup evidence | test | Label in JSON and figure title. Satisfied. |
| Thickness cost-at-target never extrapolated | test | `bracketed` true for all 5 walls. Satisfied. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ANLY-01 | 05-01 | RMSE vs N_A, >= 50 reps, fitted slopes ~ -0.5 / -1 | SATISFIED | Truth 1 |
| ANLY-02 | 05-02 | Overlaid exit histograms, labelled circuit validation | SATISFIED | Truth 2 |
| ANLY-03 | 05-02 | Truncation-bias figure/table, K = 1 quantified | SATISFIED | Truth 3 |
| ANLY-04 | 05-02 | >= 3 thicknesses, ratio grows as transmission falls | SATISFIED | Truth 4 |
| ANLY-05 | 05-01, 05-02, 05-03 | Precomputed JSON/PNG <= 2 MB, re-render without sweep | SATISFIED | Truth 5 |

All five IDs from the plan frontmatter appear in REQUIREMENTS.md (marked Complete) and in the ROADMAP Phase 5 section. No orphaned Phase 5 requirements.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` debt markers were identified in the verification scan, and no stub or hollow-data patterns in the Phase 5 modules; the data flows from real sweeps. Findings of lesser weight:

| Item | Severity | Note |
|------|----------|------|
| Data JSON files have mode 0600 on disk | Info | Git tracks only the executable bit, so this has no effect on the committed content or the Qollab bundle. |
| `thickness_study.json` provenance `git_head` is `dc99bef` (the code commit), not the final HEAD | Info | By design: the head names the commit holding the sweep code, with git_dirty false. |

### Coincidental-reliance (advisory)

None flagged.

### Human Verification Required

None needed for the Phase 5 goal. The two figures I opened (scaling and thickness) render legibly. For Phase 6, not a blocker here: view all four PNGs once in the final Qollab console and confirm the 2 MB data files load logged out.

### Gaps Summary

No gaps. Every ROADMAP success criterion was checked against the committed artifacts, independently of the SUMMARY claims. The slopes, ratios and chi-squares in the docs match the stored JSON. The IonQ marker is kept out of every fit and disclosed with its 6.4 sigma discrepancy. The 05-02 deviation (render test moved behind `slow`) does not remove coverage, since `render_figures.py --check` and the slow-marked test both pass.

---

_Verified: 2026-10-11_
_Verifier: Claude (gsd-verifier)_
