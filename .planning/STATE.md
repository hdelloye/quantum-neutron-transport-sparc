---
gsd_state_version: "1.0"
milestone: v0.0
current_phase: 01
current_phase_name: Qollab Smoke Test & Compliant Skeleton
status: verifying
stopped_at: Completed 01-04-PLAN.md
last_updated: "2026-10-10T20:09:26.918Z"
last_activity: 2026-10-10
last_activity_desc: Phase 01 execution started
state_head: 905508ab6e18e633c56834368e938af447681ed2
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 4
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** Show, on a real fusion-relevant transport problem, that quantum amplitude estimation reaches a target accuracy with fewer samples than classical Monte Carlo, with an honest classical baseline sitting next to it.
**Current focus:** Phase 01 — Qollab Smoke Test & Compliant Skeleton

## Current Position

Phase: 01 (Qollab Smoke Test & Compliant Skeleton) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
Last activity: 2026-10-10 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 3 min | 3 tasks | 12 files |
| Phase 01 P02 | 11 min | 2 tasks | 4 files |
| Phase 01 P03 | 60 min | 3 tasks | 5 files |
| Phase 01 P04 | 3 min | 3 tasks | 0 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: `Kernels` contract and exact solver get their own phase (Phase 2) so classical (Phase 3) and quantum (Phase 4) run in parallel off one frozen contract.
- [Roadmap]: Library/AI disclosure (DOCS-06) moved into Phase 1 with the other compliance items so a partial submission stays eligible.
- [Research]: One quantum step = one collision; quantity estimated is "transmission within K collisions" (K=1 for Q1).
- [Research]: MLAE submitted as one multi-circuit `backend.run` job; cost counted as N_A = Σ shots·(2k+1). **SUPERSEDED 2026-10-10 (01-03):** Qollab IonQ accepts only `ionq.circuit.v1`, so an IonQ Run carries one circuit; the one-job MLAE holds only for local/Built-in runs. Cost accounting N_A unchanged.
- [Phase 01]: Compliance file scans use git ls-files --cached --others --exclude-standard so not-yet-committed files are gated too
- [Phase 01]: Whitespace gate uses str.isspace() over the whole repo-relative path; size gate is 2,000,000 bytes (decimal)
- [Phase 01]: Upload-set test in 01-01 requires only main.py and requirements.txt; LICENSE/README.md asserted by 01-02 docs tests
- [Phase 01]: README disclosure table copied from RESEARCH sourced block; Claude Code version cell reads 'hosted service (Claude Opus and Sonnet models)' so no cell is blank
- [Phase 01]: Qollab upload set (git archive) is 7 files incl. LICENSE and README.md; README is the write-up only at project creation
- [Phase 01]: Qollab IonQ accepts only ionq.circuit.v1 and one job per Run, so an IonQ Run carries exactly one circuit; the 'MLAE as one multi-circuit job' assumption is false (Phase 4 redesign)
- [Phase 01]: Ideal IonQ runs use backend.set_options(noise_model='ideal') (ideal, sampled); the run kwarg gives exact round(p*shots) with no shot noise and is never used for statistics
- [Phase 01]: Qollab project published as public default v1.0 (Hippolyte's choice, not v0.0-smoke): https://qollab.xyz/u/hdelloye/quantum-neutron-transport-spar
- [Phase 01]: Logged-out IonQ run (R8) refused by Qollab (credits apply, sign in) despite anon_enabled true; judged Built-in path passes logged out
- [Phase 01]: GitHub repo hdelloye/quantum-neutron-transport-sparc created PRIVATE until v0 (Hippolyte: 'private until v0'); flip public before the v0 publish
- [Phase 01]: No teammates invited yet (teammates=none-yet, orchestrator-proposed default); PLAT-03 collaborator clause open until usernames are named
- [Phase 01]: Commit email and LICENSE holder line kept (orchestrator-proposed defaults); repo-local user.name Hippolyte Delloye

### Pending Todos

- [Phase 6 / v0, due before ~Oct 10 7:00 PM ET]: Flip the GitHub repository public before the v0 publish: `gh repo edit hdelloye/quantum-neutron-transport-sparc --visibility public --accept-visibility-change-consequences` (currently PRIVATE per Hippolyte's 'private until v0').
- [PLAT-03]: Invite teammates as collaborators once their GitHub usernames are known: `gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/{username} -f permission=push` (201 = invited, 204 = already a collaborator, 404 = report the spelling, do not guess). PLAT-03's collaborator clause stays open until then.

### Blockers/Concerns

- [Phase 1]: ~~Qollab behaviour undocumented (logged-out running, `noise_model="ideal"` pass-through, Pyodide performance).~~ Resolved 2026-10-10 by 01-03; see docs/QOLLAB-RUNTIME.md.
- [Phase 1]: Placeholder files with spaces in names still at repo root ("Monte Carlo Transport Problem", ".tex", "MonteCarlo Transport Problem.py"); remove or rename.
- [Phase 2]: Real ENDF/B-VIII.0 14 MeV cross sections for W heavy alloy and 316 SS not yet pulled; K=1 coverage fraction (~90%) will move.
- [Phase 4]: All Qollab IonQ simulators apply noise by default; 01-03 showed `backend.set_options(noise_model="ideal")` gives ideal sampled IonQ counts. Headline scaling plot stays ideal/local.
- [Deadline]: v0 publish by ~hour 24 (Oct 10 ~7:00 PM ET); IonQ cloud runs before ~hour 36 (Oct 11 ~7:00 AM ET); final by Oct 11 7:00 PM ET.
- [Phase 4]: Qollab IonQ runs carry exactly ONE circuit (ionq.circuit.v1 only + one job per Run). MLAE as one multi-circuit job is impossible on Qollab IonQ; redesign the IonQ path (one Run per Grover power, or a single A Q^k execution proof with the MLAE curve from local/Built-in runs). See docs/QOLLAB-RUNTIME.md
- [Phase 1]: Anonymous (logged-out) IonQ jobs are refused by Qollab ('credits apply, sign in') despite anon_enabled true; logged-out judges can run only the Built-in simulator path

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-10T20:09:26.904Z
Stopped at: Completed 01-04-PLAN.md
Resume file: None
