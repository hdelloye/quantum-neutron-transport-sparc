---
gsd_state_version: "1.0"
milestone: v0.0
current_phase: 1
current_phase_name: Qollab Smoke Test & Compliant Skeleton
status: planning
stopped_at: Phase 05 complete, ready to plan Phase 1
last_updated: "2026-10-11T17:30:30.398Z"
last_activity: 2026-10-11
last_activity_desc: Phase 05 complete, transitioned to Phase 1
state_head: fea47b0380fda8dd0291c8cefaa07597d58b2efb
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 15
  completed_plans: 15
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-10)

**Core value:** Show, on a real fusion-relevant transport problem, that quantum amplitude estimation reaches a target accuracy with fewer samples than classical Monte Carlo, with an honest classical baseline sitting next to it.
**Current focus:** Phase 05 — Scaling Study & Figures

## Current Position

Phase: 1 — Qollab Smoke Test & Compliant Skeleton
Plan: Not started
Status: Ready to plan
Last activity: 2026-10-11 — Phase 05 complete, transitioned to Phase 1

Progress: [███████░░░] 67%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 2 | - | - |
| 03 | 2 | - | - |
| 04 | 4 | - | - |
| 05 | 3 | - | - |

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
| Phase 03 P01 | 5min | 3 tasks | 5 files |
| Phase 03 P02 | 27min | 3 tasks | 2 files |
| Phase 04 P01 | 6 min | 3 tasks | 4 files |
| Phase 04 P02 | 14min | 3 tasks | 5 files |
| Phase 04 P03 | 14min | 3 tasks | 12 files |
| Phase 04 P04 | 121min | 3 tasks | 7 files |
| Phase 05 P01 | 10min | 3 tasks | 11 files |
| Phase 05 P02 | 25 min | 3 tasks | 14 files |
| Phase 05 P03 | 22min | 2 tasks | 4 files |

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
- [Phase 03]: PD-08 (costly): RandomSource protocol is one method random(size) -> float64 (size,) in [0,1); numpy Generator satisfies it unwrapped; as_source is the only Generator constructor; draw validates shape and range
- [Phase 03]: PD-09: continuous engine = vectorized Woodcock delta tracking, chunk 2^16, majorant max(front,back sigma_t), cross sections from spec (never Kernels), int64 tallies with binomial SEs
- [Phase 03]: PD-11: continuous validation compares sums only (within(0) vs e^-tau, within(1) vs T1, <=1-collision rows, first-collision columns); never full transmission vs T1 or per-entry kernels (WR-07)
- [Phase 03]: PD-12: reproducibility = same source state + n + chunk + numpy version + platform; different chunk gives different, equally valid histories
- [Phase 03]: PD-14: Phase 3 touches no frozen file, main graph or data/; 1e8 checks behind @pytest.mark.slow + NEUTRON_QAE_SLOW=1; absorption split by material deferred to a quick task
- [Phase 03]: PD-10: lattice engine samples x, a, phi, e sequentially from frozen Kernels tables (never categorical over the enumeration), one flight per history (WR-08), layout constants from exact.py
- [Phase 03]: PD-13: Phase 5 hooks - checkpoints/prefix_estimates, public shared sample_exit_rows, LatticeResult SEs, classical cost N = histories (LatticeResult.cost)
- [Phase 03]: sample_exit_rows maps zero-amplitude strings (x > 16, or escaped in a zero-back-mass bin) to -1 without drawing; kernels.py untouched, WR-08 caveat in mc_lattice docstring
- [Phase 04]: PD-15: Q1 keeps the direction register (12 qubits, x(5) a(1) phi(4) e(1) T(1), qubit i = bit i of exact.py's s, flag = top qubit); Q0 = 5 qubits flag 4; Q1lite (8 qubits) is only the IonQ size-ladder fallback
- [Phase 04]: PD-16: Grover operator via grover_operator() (Z on flag); compose logical A·Q^k then ONE transpile to BASIS [cx,rz,ry,rx,h,x,sx], opt 1, seed 1; never stitch A and Q (0.958 vs 0.9994), never transpile(c, backend)
- [Phase 04]: Contract gate: make_problem raises ContractError unless Statevector P(flag) equals exact T_K within 1e-12; runners and main.py take circuits only from make_problem
- [Phase 04]: Dev extras (qiskit-aer 0.17.2, qiskit-algorithms 0.4.0, ruff 0.16.10, matplotlib) installed in .venv under the Phase 1 dependency approval; qiskit-ionq not installed
- [Phase 04]: PD-17: vendored numpy MLAE with qiskit-algorithms grid conventions (exact QAE-01 parity), golden-section refinement, Fisher se, cost N_A = sum shots (2k+1) only
- [Phase 04]: PD-18: one Runner interface run(ks, shots) -> list[PowerResult]; AnalyticRunner, BackendRunner (injected local backend, list jobs), IonQRunner (one bare circuit per run)
- [Phase 04]: PD-20: IonQ record schema neutron_qae.ionq_record v1 in data/ionq_runs.json, validated on load; noisy runs kept sampled:false and excluded from MLAE
- [Phase 04]: PD-19: main(mode=qae, k=1, shots=1000, ideal_mode=set_options, model=Q1) one-line Qollab entry; Built-in = live MLAE over k 0,1,2,4 in one list job; IonQ = one bare A.Q^k circuit per run with an IONQ_RECORD= line; mode=smoke keeps Phase 1
- [Phase 04]: PD-23: form values validated with ValueError before any job (mode, model, k 0..8, shots 2..10000, ideal_mode none|set_options in qae); bools/non-integral rejected, integral floats accepted
- [Phase 04]: PD-21: IonQ size ladder k=0 (31 KB), k=1 (169 KB), k=2 (306 KB); on 'Circuit size is too large' re-run that k with model=Q1lite
- [Phase 04]: Phase 1 tracer is now scripts/run_local.py --mode smoke; IonQ records flow paste -> scripts/ingest_ionq_records.py -> data/ionq_runs.json
- [Phase 04]: IonQ execution proof accepted with a documented discrepancy (Hippolyte: accept (a)): Q1 A·Q^k runs on Qollab IonQ Forte 1 and mlae.estimate accepts the counts (SC4 Qollab half met); the IonQ-only estimate misses 4 sigma (a=0.228671, z=-6.38, N_A=9000), cause open; strict xfail keyed to KNOWN_4SIGMA_MISS, tolerance unchanged
- [Phase 04]: One circuit per Run IonQ protocol validated end to end on Qollab (R1-R3 k=0,1,2 accepted, records ingested verbatim); A-P1 confirmed: Pyodide runs the Q1 QAE in the browser (R0 a_hat 0.242072, N_A 18000, 1.412 s)
- [Phase 04]: Qollab IonQ request-body limit is above 307 KB (306,656 B Q1 k=2 accepted; only a lower bound); Q1lite fallback never needed
- [Phase 05]: PD-24: artifacts under data/ as JSON + PNG with literal paths in stdlib-only neutron_qae/artifacts.py (main-reachable via one import line); envelope neutron_qae.artifact v1; canonical JSON, size check before parse, NaN rejected; integrity = size cap + schema + provenance
- [Phase 05]: PD-25: headline = lattice MC (histories) vs MLAE (applications of A, exponential schedule, 300 shots/power) vs exact T1, R = 100 nested repetitions, analytic primary + Aer cross-check, OLS log-log fits (classical all points, MLAE M >= 2); IonQ one marker never in a fit
- [Phase 05]: PD-26: seed 2026, SeedSequence spawn(3) per stage, Aer seed_simulator 1818751028 in one memory job; full artifacts from committed code (git_dirty false)
- [Phase 05]: PD-30: figures render from artifact JSON only, lazy pyplot, no backend selection or show, allowlisted matplotlib calls, dpi 50..200, validated palette
- [Phase 05]: PD-31: default suite runs no real sweep; micro configs only; suite under 30 s (27.55 s after 05-01)
- [Phase 05]: PD-27: exit histograms at 1e6 matched samples, chi-square sums over 17 categories only, labelled circuit validation
- [Phase 05]: PD-28: truncation bias T_full - T1 per wall/model at 2e7 histories; K=1 coverage 99.69% at 10 cm, isotropic_raw 89.9% disclosure only
- [Phase 05]: PD-29: thickness study walls 6-30 cm, ratio at 1% relative RMSE 1.99->25.84; absolute 1e-3 disclosure 18.1->5.0; underflow guard refuses 50 cm
- [Phase 05]: 05-02: four-figure DPI-60 render test moved behind slow (suite >28.5 s); label render stays as default smoke
- [Phase 05]: PD-32 (docs from data): RESULTS.md tables and the README headline sentence are artifacts.format_markdown / headline_sentence output on the committed JSON, embedded verbatim and drift-tested

### Pending Todos

- [Phase 6 / v0, due before ~Oct 10 7:00 PM ET]: Flip the GitHub repository public before the v0 publish: `gh repo edit hdelloye/quantum-neutron-transport-sparc --visibility public --accept-visibility-change-consequences` (currently PRIVATE per Hippolyte's 'private until v0').
- [PLAT-03]: Invite teammates as collaborators once their GitHub usernames are known: `gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/{username} -f permission=push` (201 = invited, 204 = already a collaborator, 404 = report the spelling, do not guess). PLAT-03's collaborator clause stays open until then.

### Blockers/Concerns

- [Phase 6]: Phase 4 code review carry-overs — CR-01: IonQ runs with ideal_mode=none (noisy, round(p*shots) counts) crash hits_from_counts and lose the record (unused path so far; fix or document before any noisy run); WR-01: the circuit Qollab's browser transpiled differs by one gate per A from the local transpile (sizes 556/3016/5476 vs 555/3013/5471) and the contract p differs in the last digits, so docs claiming "the same transpiled circuits" reproduce p_expected must be reworded and the submitted circuit's own statevector P(flag)/QASM hash recorded per run; WR-02: malformed data/ionq_runs.json can crash the judged Built-in path (catch OverflowError/RecursionError in _ionq_summary). See 04-REVIEW.md.
- [Phase 1]: ~~Qollab behaviour undocumented (logged-out running, `noise_model="ideal"` pass-through, Pyodide performance).~~ Resolved 2026-10-10 by 01-03; see docs/QOLLAB-RUNTIME.md.
- [Phase 1]: ~~Placeholder files with spaces in names still at repo root.~~ Resolved 2026-10-10 by 01-01 (deleted; textbook PDF moved to gitignored references/).
- [Phase 2]: ~~Real ENDF/B-VIII.0 14 MeV cross sections for W heavy alloy and 316 SS not yet pulled; K=1 coverage fraction (~90%) will move.~~ Resolved 2026-10-10 by 02-01: Real ENDF/B-VIII.0 cross sections pulled; transport-corrected K=1 coverage is 99.7% (89.9% only under isotropic_raw).
- [Phase 4]: All Qollab IonQ simulators apply noise by default; 01-03 showed `backend.set_options(noise_model="ideal")` gives ideal sampled IonQ counts. Headline scaling plot stays ideal/local.
- [Deadline]: v0 publish target (~Oct 10 7:00 PM ET) PASSED without a v0 publish of the real project (the Phase 1 smoke test v1.0 is what is live on Qollab, possibly unpublished); flip the repo public and publish v0 as soon as Phase 3/4 have something green; IonQ cloud runs before ~hour 36 (Oct 11 ~7:00 AM ET); final by Oct 11 7:00 PM ET.
- [Phase 4]: Qollab IonQ runs carry exactly ONE circuit (ionq.circuit.v1 only + one job per Run). MLAE as one multi-circuit job is impossible on Qollab IonQ; redesign the IonQ path (one Run per Grover power, or a single A Q^k execution proof with the MLAE curve from local/Built-in runs). See docs/QOLLAB-RUNTIME.md
- [Phase 1]: Anonymous (logged-out) IonQ jobs are refused by Qollab ('credits apply, sign in') despite anon_enabled true; logged-out judges can run only the Built-in simulator path
- [Phase 6]: IonQ-only estimate is 6.4 sigma off T1 (z=-6.38; k=1,2 deviate from the exact circuit beyond shot noise) - a caveat is required wherever it is displayed (main.py Built-in path, README, docs); cause open. Re-upload the 8350ae9 bundle and publish (project still Draft).

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-11T17:07:59.140Z
Stopped at: Phase 05 complete, ready to plan Phase 1
Resume file: None
