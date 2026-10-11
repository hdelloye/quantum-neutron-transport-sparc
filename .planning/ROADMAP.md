# Roadmap: Quantum Neutron Transport: SPARC First Wall

## Overview

The work runs from platform risk to evidence to submission. Phase 1 proves that a toy Qiskit program publishes and runs on Qollab (built-in and IonQ simulators) from a logged-out browser, inside a compliant, importable GitHub repo. Phase 2 defines the SPARC first-wall problem once, with sourced 14 MeV cross sections, and freezes the `Kernels` contract plus the exact lattice answer that every later number is checked against. From there the work splits into two layers that run in parallel off that one contract: Phase 3 builds the classical baseline (continuous and matched discrete Monte Carlo), Phase 4 builds the quantum oracle and maximum-likelihood amplitude estimation. Phase 5 turns both into the headline evidence (error versus applications of A) plus supporting figures. Phase 6 publishes the final project on Qollab with documentation, demo video and handoff notes.

**Time checkpoints** (hackathon window Oct 9 7:00 PM ET to Oct 11 7:00 PM ET):
- Immediately: Phase 1 smoke test. A platform failure discovered late can zero the submission.
- ~Hour 24 (Oct 10 ~7:00 PM ET): v0 published on Qollab from whatever is green (DOCS-02, Phase 6), regardless of where Phases 3-5 stand.
- ~Hour 36 (Oct 11 ~7:00 AM ET): all IonQ cloud runs finished.
- Hour 48 (Oct 11 7:00 PM ET): final version published and re-checked from a logged-out browser.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Qollab Smoke Test & Compliant Skeleton** - Toy Qiskit program published and running logged-out on Qollab built-in and IonQ simulators, inside a compliant flat-package repo on GitHub
- [x] **Phase 2: Problem Spec & Kernels Contract** - SPARC slab defined once with ENDF/B-VIII.0 cross sections; frozen `Kernels` contract and exact lattice ground truth (completed 2026-10-10)
- [x] **Phase 3: Classical Baseline** - Continuous delta-tracking MC (physics reference) and matched discrete lattice MC (baseline), validated and driven by an injected random source (completed 2026-10-10)
- [x] **Phase 4: Quantum Oracle & Amplitude Estimation** - Q0/Q1 state preparation matching the exact value, Grover powers, vendored MLAE with analytic/Aer/IonQ runners and N_A cost accounting (completed 2026-10-11)
- [x] **Phase 5: Scaling Study & Figures** - RMSE-vs-N_A headline plot, exit histograms, truncation-bias and wall-thickness studies, committed as precomputed artifacts (completed 2026-10-11)
- [ ] **Phase 6: Submission, Documentation & Handoff** - v0 at ~hour 24, final logged-out-runnable Qollab project, README covering all four judging criteria, demo video, HANDOFF.md

**Layering:** Phases 3 and 4 depend only on Phase 2 (the frozen `Kernels` contract and exact solver) and run in parallel. Phase 5 needs both contract tests green (discrete MC converges to exact; circuit amplitude equals exact). Phase 6 finalizes last, but its v0 publish is time-triggered.

## Phase Details

### Phase 1: Qollab Smoke Test & Compliant Skeleton

**Goal**: Platform risk is retired before any physics is built: a toy Qiskit `main.py` is published on Qollab and runs start-to-finish from a logged-out browser on both the built-in and an IonQ simulator, served from a compliant, importable GitHub repo that teammates can clone.
**Depends on**: Nothing (first phase)
**Requirements**: PLAT-01, PLAT-02, PLAT-03, PLAT-04, DOCS-06
**Success Criteria** (what must be TRUE):
  1. In a logged-out (incognito) browser, the published Qollab project runs the toy `main.py` start-to-finish without error on Qollab's built-in simulator and on an IonQ simulator backend.
  2. The smoke-test run reports the Python, numpy and qiskit versions of Qollab's runtime and whether `noise_model="ideal"` is accepted, and those findings are recorded in the repo for later phases.
  3. A teammate added as a GitHub collaborator can clone the repo, install `requirements.txt` (pinning `qiskit==2.5.2`), import the flat package sitting next to `main.py`, and run `pytest` green; no file names with spaces remain.
  4. The repo carries an MIT LICENSE, the README line "This effort is supported by Qollab & IonQ.", and a disclosure of every external library and AI tool used, with licenses and confirmation the team may use them.
  5. An automated test fails if anything reachable from `main.py` imports qiskit-aer or qiskit-algorithms, if any committed data file exceeds 2 MB, or if code constructs a backend instead of receiving it as a parameter.

**Plans**: 4/4 plans executed
Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Dependency approval, tracer (toy main.py + neutron_qae + local runner, SMOKE TEST PASSED), compliance gates with negative tests, placeholder cleanup (PLAT-01, PLAT-02, PLAT-04)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — MIT LICENSE, README with attribution line and library/AI disclosure, docs tests, runtime-record template, GitHub CLI install (DOCS-06, PLAT-03)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md — Qollab upload, built-in + IonQ Forte 1 smoke runs, publish v0.0-smoke, logged-out re-run, findings recorded in docs/QOLLAB-RUNTIME.md (PLAT-02)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 01-04-PLAN.md — GitHub auth, publication decision, repo create + push, collaborator invites, fresh-clone pytest (PLAT-03)

**Research flag**: yes. Empirical Qollab checks: logged-out run behaviour, `noise_model` pass-through, Pyodide performance, IonQ gate-count/size limits (research/SUMMARY.md, Gaps to Address).

### Phase 2: Problem Spec & Kernels Contract

**Goal**: The SPARC first-wall problem is defined exactly once with sourced 14 MeV cross sections, and the frozen `Kernels` contract plus the exact "transmission within K collisions" value exist, so classical and quantum work can proceed independently against the same ground truth.
**Depends on**: Phase 1
**Requirements**: PHYS-01, PHYS-02, PHYS-05, PHYS-06
**Success Criteria** (what must be TRUE):
  1. `ProblemSpec` describes a 10 cm x 10 cm slab on a 16 x 16 grid with 2.0 cm tungsten heavy alloy on the plasma side and 8.0 cm 316 stainless steel behind, and a test shows the material boundary inside column 4 is handled correctly rather than snapped to a column edge.
  2. Every one-group 14 MeV cross section (total, scattering, absorption including the non-elastic treatment) for both materials is cited in code and docs with its ENDF/B-VIII.0 source and evaluation date.
  3. `Kernels`, built from `ProblemSpec`, exposes the first-collision column distribution, scatter ratio per column, and escape probability per column and direction; tests show probability is conserved across each table's outcomes, and the dataclass is frozen as the one contract both classical and quantum code import.
  4. The exact lattice solver enumerates every random-bit string of the discrete model and returns the exact transmission within K collisions; this value is the reference that Phase 3, 4 and 5 tests compare against.

**Plans**: 2/2 plans complete
Plans:
**Wave 1**
- [x] 02-01-PLAN.md — Tracer sparc_first_wall() -> build_kernels() -> exact T0/T1 against the research reference; cited ENDF/B-VIII.0 provenance; column-4 boundary, conservation, symmetry, immutability and bit-layout edge tests; golden freeze of Kernels contract v1 (PHYS-01, PHYS-02, PHYS-05, PHYS-06)

**Wave 2** *(blocked on Wave 1 completion; Phases 3 and 4 can start as soon as 02-01 is committed, 02-02 changes no contract file)*
- [x] 02-02-PLAN.md — docs/PHYSICS.md with every cross section, MAT number and evaluation date checked against the code; README contract pointers; optional local-only ENDF derivation script (PHYS-02, PHYS-05)

**Research flag**: light. Short ENDF/B-VIII.0 lookup for 14 MeV tungsten heavy alloy and 316 SS values, non-elastic/(n,2n) treatment, transport correction.
**Contract note**: freeze `Kernels` and the exact solver before Phases 3 and 4 start; any later change is an explicit contract change that re-runs both branches' contract tests.

### Phase 3: Classical Baseline

**Goal**: An honest classical baseline exists: a continuous delta-tracking Monte Carlo serves as the physics reference, and a discrete lattice Monte Carlo samples exactly the `Kernels` model the circuit encodes; both are validated against analytic and exact answers and both are driven by an injected random source.
**Depends on**: Phase 2
**Requirements**: PHYS-03, PHYS-04, PHYS-07, PHYS-08
**Success Criteria** (what must be TRUE):
  1. A seeded, vectorized continuous MC run (Woodcock delta tracking, isotropic scattering, loss on exit through any face) reports transmission fraction, absorption fraction, back-face exit-position histogram and collision-order breakdown, each with a standard error.
  2. The continuous MC's uncollided transmission matches e^{-τ} within its standard error, and two runs with the same seed reproduce identical histories.
  3. The discrete lattice MC (matched mode) samples the frozen `Kernels` model, and its mean converges to the exact lattice solver value within standard error as the number of histories grows.
  4. Both engines take their random source as a parameter (numpy Generator by default), and swapping in a different source requires no engine code change.

**Plans**: 2/2 plans complete
Plans:
**Wave 1**
- [x] 03-01-PLAN.md — Tracer (seeded source -> Woodcock delta-tracking continuous MC -> within(0) = e^-tau, within(1) = exact T1), RandomSource protocol with swapped/scripted sources and an engine RNG gate, analytic/thickness/marginal-sum/edge checks, slow 1e8 check (PHYS-03, PHYS-04, PHYS-08)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-02-PLAN.md — Tracer (frozen Kernels -> matched lattice MC -> converges to exact T1), bit-string/row/RMSE distributions vs the enumeration, hash-source swap with one-flight accounting, Phase 5 hooks (checkpoints, shared sample_exit_rows, cost = histories), slow 1e8 check (PHYS-07, PHYS-08)

**Runs in parallel with**: Phase 4 (both depend only on Phase 2).

### Phase 4: Quantum Oracle & Amplitude Estimation

**Goal**: A state-preparation circuit within 24 qubits, whose flag probability equals the exact lattice value, is wrapped in Grover powers and a vendored maximum-likelihood amplitude estimator, producing transmission estimates through analytic, Aer and IonQ runners with cost counted honestly as applications of A.
**Depends on**: Phase 2
**Requirements**: QC-01, QC-02, QC-03, QC-04, QC-05, QC-06, QAE-01, QAE-02, QAE-03, QAE-04
**Success Criteria** (what must be TRUE):
  1. On an Aer statevector, Q0's flag probability equals e^{-τ}, and Q1's flag probability (fresh qubits for every random choice, no measurement or reset inside A, invertible) equals the exact lattice solver value to 1e-12; this contract test gates every QAE run.
  2. Powers Q^k of the Grover operator built with `grover_operator()` reproduce sin²((2k+1)θ) on a statevector for k up to 64.
  3. The vendored numpy MLAE, given counts from one `backend.run([...])` job of A·Q^k circuits, returns the same estimate as qiskit-algorithms MLAE on identical counts, and every estimate reports its cost as N_A = Σ shots·(2k+1), never raw shots or `num_oracle_queries`.
  4. The analytic, Aer and IonQ runners share one interface; analytic and Aer agree within statistical error on at least three (k, shots) points, and an IonQ-runner job (decomposed to at most 7 controls per gate, transpiled once as a whole circuit, `backend.run` + `get_counts`, no Sampler) completes on Qollab's IonQ simulator and yields counts the MLAE accepts.
  5. A resource table lists qubits, CX count and depth for Q0 and Q1 after a single full-circuit transpile, all within the 24-qubit budget.

**Plans**: 4/4 plans complete
Plans:
**Wave 1**
- [x] 04-01-PLAN.md — Tracer (frozen Kernels -> Q1 A, contract P(flag) = T1 to 1e-12 -> A·Q^1 transpiled once, P = 0.9994), dev-extras install under the Phase 1 approval, Q0/Q1/Q1lite oracle with exact.py's bit layout, Grover powers to k = 64, IonQ-safe transpile-once checks, resource table (QC-01, QC-02, QC-03, QC-04, QC-05, QC-06)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 04-02-PLAN.md — Tracer (Built-in-style list job -> flag hits -> vendored MLAE -> a_hat, se, N_A), qiskit-algorithms parity, N_A vs num_oracle_queries, analytic/backend/IonQ runners with one interface, analytic vs Aer agreement, IonQ record schema, loader and IonQ-only estimate (QAE-01, QAE-02, QAE-03, QAE-04)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 04-03-PLAN.md — Tracer (injected Built-in backend -> main() QAE mode -> QAE_REPORT=), IonQ one circuit per Run with IONQ_RECORD=, smoke mode kept, input validation, data/ionq_runs.json and verbatim ingest script, README and docs/QUANTUM.md with the resource table, 19-file bundle audit (QAE-02, QC-05, QC-06)

**Wave 4** *(blocked on Wave 3 completion; one human checkpoint, IonQ runs before ~7:00 AM ET Oct 11)*
- [x] 04-04-PLAN.md — Pre-flight bundle and fake-IonQ dry run, Hippolyte runs Built-in once and IonQ Forte 1 at k = 0, 1, 2 on Qollab, records ingested verbatim, IonQ-only MLAE estimate within 4 sigma of T1, findings in docs (QAE-01, QAE-02, QC-06)

**Research flag**: yes. Qubit/gate budget spike with the real Phase 2 cross sections before building Q1; Lee/Lee/Kim full text for circuit-design comparison; IonQ gate/size limits on submission.
**Runs in parallel with**: Phase 3. IonQ cloud runs finish before ~hour 36 (Oct 11 ~7:00 AM ET).

### Phase 5: Scaling Study & Figures

**Goal**: The Core Value evidence exists: on the same discrete problem, RMSE against the exact value falls roughly as 1/N_A for MLAE versus 1/sqrt(N_A) for matched classical MC, with supporting exit histograms, a truncation-bias disclosure and a wall-thickness rare-event study, all committed as precomputed artifacts.
**Depends on**: Phase 3, Phase 4
**Requirements**: ANLY-01, ANLY-02, ANLY-03, ANLY-04, ANLY-05
**Success Criteria** (what must be TRUE):
  1. A log-log figure of RMSE versus N_A (at least 50 repetitions per point, measured against the exact lattice value) shows discrete classical MC and MLAE with fitted slopes near -0.5 and -1 respectively.
  2. Overlaid back-face exit-position histograms, classical versus direct sampling of Q1 at matched shot counts, are labelled as circuit validation rather than speedup evidence.
  3. A truncation-bias figure or table compares transmission within K collisions to full continuous transmission, so the K = 1 approximation is quantified and disclosed.
  4. Repeating the comparison for at least three slab thicknesses shows the classical-to-MLAE sample-count ratio growing as transmission falls.
  5. Sweep results and figures are committed as JSON/PNG files of at most 2 MB each, and the figures re-render from those files without rerunning the sweep.

**Plans**: 3/3 plans complete
Plans:
**Wave 1**
- [x] 05-01-PLAN.md — Tracer (quick sweep -> validated data/scaling_rmse.json -> PNG rendered from the JSON -> literal paths reachable from main.py via one changed import line), full headline sweep (matched lattice MC vs analytic MLAE, Aer cross-check, R = 100, IonQ as one labelled marker never fitted), artifacts/analysis/figures modules, re-render script, edge gates (ANLY-01, ANLY-05)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 05-02-PLAN.md — Tracer exit-histogram slice (1e6 matched samples, classical vs Q1 k = 0 on Aer through one row sampler, chi-square, labelled circuit validation), truncation bias per wall and model (2e7 continuous histories per case), five-wall thickness study with the cost ratio at 1% relative RMSE (ANLY-02, ANLY-03, ANLY-04, ANLY-05)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 05-03-PLAN.md — Tracer results doc (stdlib Markdown formatters from the committed JSON, drift-tested), docs/RESULTS.md and README Results section with honest caveats, claims and link gates, 30-file bundle audit (ANLY-05)

### Phase 6: Submission, Documentation & Handoff

**Goal**: A judge opening the Qollab project from a logged-out browser can run a quick mode that finishes, read documentation that addresses every judging criterion honestly, and watch the demo video; teammates can continue the work from GitHub.
**Depends on**: Phase 5
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-07, DOCS-08
**Success Criteria** (what must be TRUE):
  1. A v0 of the project is published on Qollab by about hour 24 (Oct 10 ~7:00 PM ET), and the final version is published before Oct 11 7:00 PM ET.
  2. From a logged-out browser, the final Qollab project runs the typed `main(...)` quick mode to completion: a small live MLAE run on the injected backend plus rendering of the precomputed figures.
  3. The README explains what the project does, the problem, how to run it locally and on Qollab, and how to replicate the results, with one section per judging criterion (novelty, technical execution, impact, documentation).
  4. The README's prior-art section cites Olivier & Nowak (arXiv:2410.19489), Lee/Lee/Kim (PRD 111, 116001) and Miao/Jin/Sone (arXiv:2607.10772) and states only the narrowed novelty claim; its limitations section states one-group physics, K-collision truncation, ideal-simulator scaling plot, IonQ simulator noise, no wall-clock speedup claim, sampling-complexity argument only.
  5. The Qollab project has the demo video, repo link and Quantum Impact theme tag attached, and a teammate following HANDOFF.md can find module owners, run the tests, read the frozen `Kernels` contract and pick up a remaining task.

**Plans**: 3 plans
Plans:
**Wave 1**
- [ ] 06-01-PLAN.md — Quick mode as the new main() default (contract check, live MLAE k = 0, 1, 2, four figures from data/*.json, QUICK MODE OK), IonQ caveat line, WR-02 catch, CR-01 refusal (DOCS-01)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 06-02-PLAN.md — Judge-facing README (run, replicate, results with four figures, one section per criterion, prior art + narrowed claim, seven limitations), WR-01/CR-01 doc fixes, HANDOFF.md, docs gates, BUNDLE OK 30 + public-repo audit (DOCS-03, DOCS-04, DOCS-05, DOCS-08)

**Wave 3** *(blocked on Wave 2 completion; human-action)*
- [ ] 06-03-PLAN.md — Push + audited qollab-final.zip, then Hippolyte: repo public, fresh Qollab project v1.0-final, hackathon submission (Quantum Impact), logged-out quick run, demo video; evidence recorded in docs/QOLLAB-RUNTIME.md (DOCS-02, DOCS-07)
**Time-triggered checkpoint**: the v0 publish (DOCS-02) does not wait for Phases 3-5; it ships whatever is green at ~hour 24. The README skeleton and HANDOFF.md can be drafted as soon as Phase 2 freezes `Kernels`.

## Progress

**Execution Order:**
1 -> 2 -> (3 and 4 in parallel) -> 5 -> 6. The Phase 6 v0 publish is time-triggered at ~hour 24.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Qollab Smoke Test & Compliant Skeleton | 4/4 | In Progress | - |
| 2. Problem Spec & Kernels Contract | 2/2 | Complete    | 2026-10-10 |
| 3. Classical Baseline | 2/2 | Complete    | 2026-10-10 |
| 4. Quantum Oracle & Amplitude Estimation | 4/4 | Complete    | 2026-10-11 |
| 5. Scaling Study & Figures | 3/3 | Complete    | 2026-10-11 |
| 6. Submission, Documentation & Handoff | 0/TBD | Not started | - |
