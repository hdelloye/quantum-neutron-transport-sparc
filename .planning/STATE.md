---
gsd_state_version: "1.0"
milestone: v0.0
current_phase: 3
current_phase_name: Classical Baseline
status: executing
stopped_at: Phase 02 complete, ready to plan Phase 1
last_updated: "2026-10-11T00:46:08.313Z"
last_activity: 2026-10-10
last_activity_desc: Phase 02 complete; next Phases 3 and 4 (Phase 1 gaps are human actions)
state_head: 9d6b8f382e90fa1cc70f0894ee7b9f2a6bc8d892
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 8
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-10)

**Core value:** Show, on a real fusion-relevant transport problem, that quantum amplitude estimation reaches a target accuracy with fewer samples than classical Monte Carlo, with an honest classical baseline sitting next to it.
**Current focus:** Phases 3 (Classical Baseline) and 4 (Quantum Oracle & AE) — both depend only on the frozen Phase 2 contract and can be planned/executed in parallel; Phase 1 has two human-dependent gaps (logged-out IonQ refused by Qollab; teammates not yet invited)

## Current Position

Phase: 3 (Classical Baseline) — READY TO EXECUTE
Plan: Not started
Status: Ready to execute
Last activity: 2026-10-10 — Phase 02 complete, transitioned to Phase 1

Progress: [██░░░░░░░░] 17%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 2 | - | - |

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
| Phase 02 P01 | 6 min | 3 tasks | 11 files |
| Phase 02 P02 | 5 min | 2 tasks | 4 files |

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
- [Phase 02]: PD-01 (costly): one-group model is transport-corrected (Sigma_tr = Sigma_t - mubar*Sigma_el); isotropic_raw selectable via sparc_first_wall('isotropic_raw'); golden frozen on transport-corrected
- [Phase 02]: PD-02 (costly): WHA = 97W-2Ni-1Fe wt% at 18.5 g/cm3 (arXiv:2603.03893); 316 SS = PNNL-15870 Rev. 2 entry 333 at 8.00 g/cm3
- [Phase 02]: PD-03: absorption = removal from the 14 MeV group, Sigma_a = Sigma_t - Sigma_el; (n,2n) counted once as removal
- [Phase 02]: PD-04: Kernels contract v1 supports K in {0, 1}; K=2 is a v2 contract change (QC-08)
- [Phase 02]: PD-05: x depth (0 = plasma face); 0-based column 3 = ROADMAP column 4 holds the 2.0 cm interface; material_at half-open; exit row = floor(y/dy) clipped; bin b from +x toward +y; beam at y=5.0
- [Phase 02]: PD-06: Kernels contract v1 frozen in tests/golden/kernels_v1.json (T1=0.24300446519524305) at rtol 1e-12 + spec fingerprint; changes go through scripts/freeze_kernels.py --write --force with a version bump; main.py unchanged
- [Phase 02]: PD-07: scripts/derive_cross_sections.py committed as optional, local-only replication of MICRO_14MEV (stdlib + numpy, network only with --download, AST-tested)

### Pending Todos

- [Phase 6 / v0, due before ~Oct 10 7:00 PM ET]: Flip the GitHub repository public before the v0 publish: `gh repo edit hdelloye/quantum-neutron-transport-sparc --visibility public --accept-visibility-change-consequences` (currently PRIVATE per Hippolyte's 'private until v0').
- [PLAT-03]: Invite teammates as collaborators once their GitHub usernames are known: `gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/{username} -f permission=push` (201 = invited, 204 = already a collaborator, 404 = report the spelling, do not guess). PLAT-03's collaborator clause stays open until then.

### Blockers/Concerns

- [Phase 1]: ~~Qollab behaviour undocumented (logged-out running, `noise_model="ideal"` pass-through, Pyodide performance).~~ Resolved 2026-10-10 by 01-03; see docs/QOLLAB-RUNTIME.md.
- [Phase 1]: ~~Placeholder files with spaces in names still at repo root.~~ Resolved 2026-10-10 by 01-01 (deleted; textbook PDF moved to gitignored references/).
- [Phase 2]: ~~Real ENDF/B-VIII.0 14 MeV cross sections for W heavy alloy and 316 SS not yet pulled; K=1 coverage fraction (~90%) will move.~~ Resolved 2026-10-10 by 02-01: Real ENDF/B-VIII.0 cross sections pulled; transport-corrected K=1 coverage is 99.7% (89.9% only under isotropic_raw).
- [Phase 4]: All Qollab IonQ simulators apply noise by default; 01-03 showed `backend.set_options(noise_model="ideal")` gives ideal sampled IonQ counts. Headline scaling plot stays ideal/local.
- [Deadline]: v0 publish target (~Oct 10 7:00 PM ET) PASSED without a v0 publish of the real project (the Phase 1 smoke test v1.0 is what is live on Qollab, possibly unpublished); flip the repo public and publish v0 as soon as Phase 3/4 have something green; IonQ cloud runs before ~hour 36 (Oct 11 ~7:00 AM ET); final by Oct 11 7:00 PM ET.
- [Phase 4]: Qollab IonQ runs carry exactly ONE circuit (ionq.circuit.v1 only + one job per Run). MLAE as one multi-circuit job is impossible on Qollab IonQ; redesign the IonQ path (one Run per Grover power, or a single A Q^k execution proof with the MLAE curve from local/Built-in runs). See docs/QOLLAB-RUNTIME.md
- [Phase 1]: Anonymous (logged-out) IonQ jobs are refused by Qollab ('credits apply, sign in') despite anon_enabled true; logged-out judges can run only the Built-in simulator path

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-10T22:28:08.099Z
Stopped at: Phase 2 complete and verified (4/4); Phase 1 executed with 2 human gaps; next: plan Phases 3 and 4
Resume file: None
