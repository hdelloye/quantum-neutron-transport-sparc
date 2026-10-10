---
phase: 01-qollab-smoke-test-compliant-skeleton
verified: 2026-10-10T20:45:00Z
status: gaps_found
score: 3/5 must-haves verified
covered_files: [".gitattributes", ".gitignore", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-01-PLAN.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-01-SUMMARY.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-02-PLAN.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-02-SUMMARY.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-03-PLAN.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-03-SUMMARY.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-04-PLAN.md", ".planning/phases/01-qollab-smoke-test-compliant-skeleton/01-04-SUMMARY.md", "LICENSE", "README.md", "data/smoke_probe.json", "docs/QOLLAB-RUNTIME.md", "main.py", "neutron_qae/__init__.py", "neutron_qae/smoke.py", "pyproject.toml", "requirements.txt", "scripts/run_local.py", "tests/compliance_checks.py", "tests/test_compliance.py", "tests/test_docs.py", "tests/test_smoke.py"]
covered_digest: "v3:sha256:7c5b43098f4640188264328e8ee0d70cf0774f5ee938bfbf824b3be14903c450"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "SC1: In a logged-out (incognito) browser, the published Qollab project runs the toy main.py start-to-finish without error on the built-in simulator AND on an IonQ simulator backend"
    status: partial
    reason: "Built-in half is VERIFIED (R7, logged out, SMOKE TEST PASSED). IonQ half FAILED: R8 (logged out, IonQ Forte 1) was refused by Qollab before running ('credits apply, you need to sign in') even though anon_enabled was true. No QOLLAB_RUNTIME_REPORT= line exists for it, and the refusal text is Hippolyte's paraphrase, not a verbatim copy. Only Forte 1 was tried logged out; other IonQ entries (Aria 1/2, Forte Ent. 1) were never tried. Server-side policy, not fixable in repo code, but the roadmap contract is not met as written."
    artifacts:
      - path: "docs/QOLLAB-RUNTIME.md"
        issue: "R8 recorded as REFUSED with no verbatim error text and no report line"
    missing:
      - "Either re-run logged out on another IonQ entry (Aria 1 / Aria 2 / Forte Ent. 1) and record a verbatim report, or capture the verbatim refusal text, or accept the deviation via an override (see Override suggestion)"
  - truth: "SC3 / PLAT-03: A teammate added as a GitHub collaborator can clone the repo, install requirements.txt, import the flat package, and run pytest green"
    status: partial
    reason: "Clone + install + pytest green holds (I re-cloned origin/main with owner credentials: 36 passed). But no teammate exists as a collaborator: collaborators = [hdelloye], invitations = [], and the repo is PRIVATE (anonymous GET returns 404), so a teammate cannot clone it today. The 01-04 plan prohibition 'MUST NOT leave the repository writable only by Hippolyte' is currently breached. REQUIREMENTS.md marks PLAT-03 [x] Complete, which overstates it."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "PLAT-03 ticked complete while the collaborator clause is open"
    missing:
      - "Hippolyte names teammate GitHub usernames; run gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/{username} -f permission=push for each (expect 201/204)"
      - "Untick PLAT-03 (or mark partial) until invitations exist"
advisory: []
behavior_unverified_items: []
human_verification:
  - test: "Confirm the published Qollab project is still public and default v1.0, then run it from a fresh logged-out incognito window on the Built-in simulator"
    expected: "Console shows one QOLLAB_RUNTIME_REPORT= line then SMOKE TEST PASSED (platform emscripten, qiskit 2.5.2)"
    why_human: "Qollab has no API and the project may have been unpublished after the 2026-10-10 runs; the shipped files match HEAD for all 7 upload files (sha1 identical to 73a4cb7), but live state cannot be read from here"
  - test: "Check which README the Qollab project page shows"
    expected: "Contains 'This effort is supported by Qollab & IonQ.' (the first upload's README should; the later README edit about one circuit per job likely did not propagate, per Pitfall 8)"
    why_human: "The Qollab write-up is rendered server-side and cannot be fetched from here"
  - test: "Judgment-tier prohibitions (non-authoritative LLM verdict, human review recommended): (a) DOCS-06 licenses not guessed; (b) 01-03 report lines verbatim and kwarg counts never presented as sampled; (c) 01-04 repo creation/visibility only on Hippolyte's explicit answer"
    expected: "(a) I spot-checked installed metadata: qiskit Apache-2.0, numpy BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0, pytest MIT, scipy BSD classifier, all matching README; qiskit-ionq, Pyodide MPL-2.0, ruff, GSD Core 1.16.0, Claude Code terms not re-checked. (b) 9 report lines parse as JSON and the flags match the labels; docs state kwarg = exact round(p*shots), never statistics; character-identity to the paste was not re-checkable. (c) Hippolyte only said 'private until v0'; name, teammates=none-yet, email, license defaults were orchestrator-proposed (01-04 SUMMARY admits this)"
    why_human: "unverified-prohibition: judgment-tier, cannot be mechanically proven"
---

# Phase 1: Qollab Smoke Test & Compliant Skeleton Verification Report

**Phase Goal:** Platform risk is retired before any physics is built: a toy Qiskit `main.py` is published on Qollab and runs start-to-finish from a logged-out browser on both the built-in and an IonQ simulator, served from a compliant, importable GitHub repo that teammates can clone.
**Verified:** 2026-10-10T20:45:00Z
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

The code, compliance, docs and Built-in-simulator halves are real and independently confirmed. Two parts of the goal sentence are not met: the logged-out IonQ run, and "teammates can clone" (no collaborator, private repo). Both are outside what code can fix, but the roadmap contract says what it says.

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | Logged out, published project runs toy main.py without error on Built-in AND IonQ simulator | ✗ FAILED (partial) | Built-in: R7 logged-out incognito, `SMOKE TEST PASSED`, platform emscripten, wall 0.081 s (report line in docs/QOLLAB-RUNTIME.md parses; is_ionq false, accepted true). IonQ: signed-in R4/R5/R6 pass (is_ionq true, accepted true), but logged-out R8 was refused by Qollab, no report. |
| 2   | Run reports Python/numpy/qiskit versions and whether `noise_model="ideal"` is accepted, recorded in repo | ✓ VERIFIED | 9 `QOLLAB_RUNTIME_REPORT=` lines parsed by me: Python 3.14.2, numpy 2.4.6, qiskit 2.5.2, qiskit_ionq 1.0.2, Pyodide 314.0.7. kwarg ACCEPTED (exact round(p*shots)), set_options ACCEPTED (sampled), recorded in Conclusions. `test_runtime_findings_recorded` passes. |
| 3   | Collaborator teammate can clone, install requirements.txt (qiskit==2.5.2), import flat package, run pytest green; no spaces in names | ✗ FAILED (partial) | Clone/pytest/no-whitespace parts verified (fresh clone of origin/main: 36 passed; `find` and `git ls-files -co` show no whitespace names). Collaborator part fails: collaborators = hdelloye only, no invitations, repo PRIVATE (anonymous API 404). |
| 4   | MIT LICENSE, attribution line, disclosure of every library and AI tool with licenses and confirmation | ✓ VERIFIED | LICENSE starts `MIT License`, holder line present; README line `This effort is supported by Qollab & IonQ.` on its own line; 9-row disclosure table incl. Claude Code and GSD Core plus confirmation paragraph; 7 docs tests pass; LICENSE and README ship in the git-archive upload set. |
| 5   | Automated test fails on reachable qiskit-aer/algorithms import, data file over 2 MB, or code constructing a backend | ✓ VERIFIED | Mutation-tested in a scratch copy: `import qiskit_aer` in package, `qiskit_algorithms` import inside a function, 3 MB data file, `BasicSimulator()` in package, `backend = None` in main.py, `main()` call in main.py, whitespace filename each made pytest fail with the intended compliance test. Baseline 36 passed. |

**Score:** 3/5 truths verified (0 present, behavior-unverified)

### Plan-level truths spot-checked

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| Local runner prints one `QOLLAB_RUNTIME_REPORT=` line, then `SMOKE TEST PASSED` | ✓ VERIFIED | I ran `scripts/run_local.py`: output ends `SMOKE TEST PASSED` |
| pytest exits 0; repo untouched by a run | ✓ VERIFIED | 36 passed; `git status --porcelain` identical before and after |
| main.py + flat package + requirements.txt (`qiskit==2.5.2` only) + pyproject + tests/scripts/data | ✓ VERIFIED | Files read; requirements.txt single requirement line |
| Three 0-byte placeholders deleted; PDF moved to gitignored references/, not tracked | ✓ VERIFIED | Root has no whitespace names; `references/Book_...pdf` 8,208,050 bytes; `git ls-files '*.pdf'` empty |
| One IonQ job per run, perf probe skipped on IonQ | ✓ VERIFIED | `test_ionq_like_backend_sends_exactly_one_job[none,kwarg]` passes; code reads `if is_ionq(backend) ...: return {"skipped"...}` (note WR-02: module-prefix guard fails open) |
| Code shipped to Qollab equals HEAD | ✓ VERIFIED | `git archive HEAD` = exactly 7 files; sha1 of all 7 identical between 73a4cb7 (published bundle) and HEAD |
| Repo on GitHub, main = local HEAD, MIT detected | ⚠️ PARTIAL | `licenseInfo.key = mit`, PRIVATE; origin/main is 470e38e, local HEAD is 4cc5ebd, behind by 2 docs-only commits (review report + disposition); code identical |

### Deferred Items

None. No later phase covers logged-out IonQ or teammate invitations (Phase 6 DOCS-08 is a handoff doc, DOCS-07 only adds the repo link).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `main.py` | one-line typed main reading injected backend | ✓ VERIFIED | exact signature, no guard, no backend assignment, report + verdict printed |
| `neutron_qae/smoke.py` | smoke functions taking backend param | ✓ VERIFIED | substantive and wired. `all_ones` was removed in 73a4cb7 (plan interface table is stale; harmless) |
| `neutron_qae/__init__.py` | flat package marker | ✓ VERIFIED | `__all__ = ["smoke"]` |
| `data/smoke_probe.json` | literal-path data file | ✓ VERIFIED | loaded on Qollab per R1/R7 (`data_file_literal_path`) |
| `scripts/run_local.py` | local injector | ✓ VERIFIED | ran it |
| `requirements.txt`, `pyproject.toml`, `.gitignore`, `.gitattributes` | config | ✓ VERIFIED | contents match plan |
| `tests/compliance_checks.py`, `test_compliance.py`, `test_smoke.py`, `test_docs.py` | gates | ✓ VERIFIED | 36 tests collected and passing; every promised test name present |
| `LICENSE`, `README.md` | compliance docs | ✓ VERIFIED | see truth 4 (README has an inaccuracy, WR-08 below) |
| `docs/QOLLAB-RUNTIME.md` | runtime record | ✓ VERIFIED | 4 sections, 9 report lines, conclusions filled, no placeholders |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| main.py | neutron_qae/smoke.py | `from neutron_qae.smoke import ...` | ✓ WIRED | present |
| scripts/run_local.py | main.py | `entry.backend = make_backend(` | ✓ WIRED | present, ran end to end |
| smoke.py | data/smoke_probe.json | literal `PROBE_FILE` | ✓ WIRED | confirmed on Qollab via report |
| tests/test_compliance.py | compliance_checks | pytest pythonpath | ✓ WIRED | tests run |
| local HEAD | github main | `HEAD:main` | ⚠️ PARTIAL | remote 2 doc-only commits behind |
| github repo | teammates | collaborators invitations | ✗ NOT_WIRED | none exist |
| Qollab bundle | published project | upload + publish | ✓ WIRED (per human-run record) | not re-checkable from here |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| main.py report | `report["toy"]` | `backend.run(...)` on injected backend | Yes (counts from real run) | ✓ FLOWING |
| smoke.runtime_report | `data_file_literal_path` | `open(PROBE_FILE)` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Local end-to-end smoke | `.venv/bin/python scripts/run_local.py` | ends `SMOKE TEST PASSED` | ✓ PASS |
| Test suite | `.venv/bin/python -m pytest -q` | 36 passed, 1 expected warning | ✓ PASS |
| Gates can fail | 6 mutations on a scratch copy | each fired the intended test | ✓ PASS |
| Fresh clone of origin/main | clone + pytest | 36 passed | ✓ PASS |
| Anon IonQ flag | `curl .../ionq/backends/simulator/cost` | `{"cost":"0","anon_enabled":true}` | ✓ (but contradicts R8) |

### Probe Execution

SKIPPED. No `probe-*.sh` declared or present.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| PLAT-01 | 01-01 | flat package, pinned requirements, pyproject, tests, scripts, no spaces | ✓ SATISFIED | layout verified, placeholders gone |
| PLAT-02 | 01-01, 01-03 | toy main.py on built-in and IonQ sim, published, runs from logged-out browser, versions + noise_model recorded | ⚠️ PARTIAL | Built-in logged out passes; IonQ signed-in passes; IonQ logged out refused. Versions and noise_model recorded. REQUIREMENTS.md says Complete |
| PLAT-03 | 01-02, 01-04 | on GitHub with teammates as collaborators, MIT, attribution | ✗ PARTIAL / BLOCKED | repo, MIT, attribution done; no collaborators. REQUIREMENTS.md says Complete (with a note) |
| PLAT-04 | 01-01 | no aer/algorithms reachable, data at most 2 MB literal path, backend injected | ✓ SATISFIED | mutation-verified (gate caveats in WR-05) |
| DOCS-06 | 01-02 | disclosure with licenses and confirmation | ✓ SATISFIED | table + paragraph; licenses spot-checked, judgment flag above |

Orphaned requirements: none. REQUIREMENTS.md maps exactly PLAT-01..04 and DOCS-06 to Phase 1, all claimed by a plan.

### Prohibitions

| Prohibition | Tier | Result |
| ----------- | ---- | ------ |
| No PDF committed / PDF not deleted | test | ✓ held |
| No aer/algorithms/ionq/ibm_runtime reachable | test | ✓ held (gate mutation-tested) |
| No backend constructed/assigned/read as free global | test | ✓ held |
| No gate that cannot fail; every gate has a negative test | test | ⚠️ WARNING: I showed `backend_assigned_in_main`, the main()-call branch, and the data literal-path gate DO fire, but no committed negative test exists for them or for the 100-file cap (WR-06). Docstring over-claims |
| Attribution line verbatim; AI tools disclosed | test | ✓ held |
| One job per IonQ run | test | ✓ held |
| Repo not writable only by Hippolyte | test | ✗ BREACHED (collaborators: hdelloye only) |
| Judgment-tier (license accuracy; verbatim reports; Hippolyte's explicit publication answer) | judgment | unverified-prohibition, human review recommended (see human_verification) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (all phase files) | - | TBD/FIXME/XXX/TODO scan | clean | no debt markers; no token-shaped strings; no tracked file over 2 MB |
| neutron_qae/smoke.py | 61 | `options_noise_model` put into JSON unsanitised (CR-01) | ⚠️ Warning | main() raises TypeError on Aer noise-model backends (Qollab IBM noise-model choices). Outside the two SC backends, but a judge can select it. Open and untriaged in 01-REVIEW-DISPOSITION.md |
| neutron_qae/smoke.py | 95-96, 103, 109, 152 | `ideal_mode` typo raises; set_options/transpile/perf_probe outside try (WR-01, WR-04) | ⚠️ Warning | judged Built-in run can crash on a mistyped form value |
| neutron_qae/smoke.py | 67-69 | one-job guard fails open for an unrecognised remote backend (WR-02) | ⚠️ Warning | |
| README.md | 17 | says logged-out IonQ works while anonymous is allowed (WR-08) | ⚠️ Warning | contradicts R8; this README is the Qollab write-up judges read |
| tests/compliance_checks.py | various | false negatives (tuple-unpack backend, `x = main()`, `from_backend`, module-level global, variable `__import__`) (WR-05) | ⚠️ Warning | SC5 holds for the named forms; the gate is not airtight |

All 16 review findings are still `open` (none triaged). I classed none as BLOCKER because none is a must-have truth, but CR-01 and WR-04 touch the judged runtime and should be fixed before Phase 6 copies `backend_report` into the real entry point.

### Human Verification Required

1. **Live Qollab state.** Open https://qollab.xyz/u/hdelloye/quantum-neutron-transport-spar logged out; expect public default v1.0, Built-in run ends `SMOKE TEST PASSED`. Why human: no API, could have been unpublished.
2. **Qollab write-up README.** Confirm the attribution line renders. Why human: server-rendered.
3. **Judgment-tier prohibitions** as listed in frontmatter.

### Gaps Summary

Two real gaps, both blocked on a person or on Qollab, not on code:

1. **Logged-out IonQ run (SC1, PLAT-02).** Qollab refuses anonymous Forte 1 jobs despite `anon_enabled: true` (re-checked just now; flag still true). Evidence is a paraphrase. Cheapest closures: try Aria 1/2 or Forte Ent. 1 logged out and paste verbatim, or accept the deviation.
   **This looks intentional.** To accept it, add to VERIFICATION.md frontmatter:
   ```yaml
   overrides:
     - must_have: "In a logged-out (incognito) browser, the published Qollab project runs the toy main.py start-to-finish without error on the built-in simulator and on an IonQ simulator backend"
     reason: "Qollab refuses anonymous IonQ jobs server-side (R8); built-in path passes logged out (R7) and IonQ passes signed in (R4-R6)"
     accepted_by: "Hippolyte Delloye"
     accepted_at: "<ISO timestamp>"
   ```
   Only Hippolyte can accept this. Also fix README line 17 so judges are not told logged-out IonQ works.
2. **Teammate collaborators (SC3, PLAT-03).** Name the usernames and send the invitations; until the repo is public or invitees exist, nobody but the owner can clone it. REQUIREMENTS.md and the ROADMAP should not show PLAT-03 as complete until then. The repo must also be flipped public before the v0 publish (STATE.md todo already records the command).

Summary claims that did NOT hold up: "PLAT-02 Complete" and "PLAT-03 Complete" in REQUIREMENTS.md traceability. The rest of the SUMMARY claims (tests, bundle contents, GitHub MIT detection, fresh-clone pass, runtime findings) were independently confirmed.

---

_Verified: 2026-10-10T20:45:00Z_
_Verifier: Claude (gsd-verifier)_
