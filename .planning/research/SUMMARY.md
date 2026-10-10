# Project Research Summary

**Project:** Quantum Neutron Transport: SPARC First Wall
**Domain:** Hybrid classical + quantum Monte Carlo neutron transport (QAE demonstrator), hackathon submission
**Researched:** 2026-10-09
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a quantum-amplitude-estimation (QAE) Monte Carlo demonstrator. The classical random walk of a 14 MeV neutron through a two-material slab is encoded as a unitary state-preparation circuit A in which every random choice consumes fresh qubits; QAE then estimates the transmission probability with error scaling roughly 1/N in applications of A, against a matched classical baseline whose error scales 1/sqrt(N). The Architecture researcher prototyped the encoding (Q1, 12 qubits, beam source) in Qiskit 2.5.2 and the flag-qubit probability matched the exact discrete answer to 1e-15, so the core idea is feasible inside the 24-qubit budget.

Research overturned five assumptions in PROJECT.md. (1) The novelty claim narrows: Olivier & Nowak (2024) did quantum-walk transport in emulation without QAE, and Lee, Lee & Kim (PRD 2025) did photon transport with QAE; the defensible claim is "first end-to-end QAE estimate of a neutron transport tally through a two-material fusion first wall, with measured error-vs-oracle-queries scaling against a matched classical baseline." (2) The step-by-step walk with reused direction qubits and a step counter cannot work: reused qubits create interference (wrong answer) and one-cell steps need ~60 qubits. One quantum step must be one collision, with kernels precomputed from cross sections; the quantity becomes "transmission within K collisions". (3) The estimator must be maximum-likelihood AE (MLAE) submitted as one multi-circuit job, because Qollab's IonQ backends accept one job per run; cost must be counted as N_A = Σ shots·(2k+1). (4) Qollab runs Python 3.14 in the browser (Pyodide) from a top-level `main.py`, not a notebook, with the backend injected and data files ≤ 2 MB. (5) Three classical solvers are needed so the comparison is like-for-like: continuous MC (physics reference), discrete lattice MC (baseline), exact lattice calculation (ground truth).

Key risks: Qollab platform behaviour is undocumented (logged-out running, `noise_model="ideal"` pass-through, Pyodide performance), so a smoke test must happen in hour one; all IonQ simulators on Qollab apply noise, so the headline scaling plot is an ideal local result and the IonQ run proves execution; real 14 MeV cross sections for tungsten heavy alloy and 316 SS still need to be pulled from ENDF/B-VIII.0.

## Key Findings

### Recommended Stack

Pin to Qollab's runtime: Python 3.14, `qiskit==2.5.2` (2.6.0 may land mid-hackathon), `qiskit-algorithms==0.4.0` and `qiskit-aer==0.17.2` for local tests only, `qiskit-ionq>=1.0.0` provided by Qollab. Do not pin numpy/scipy/matplotlib in `requirements.txt`; Qollab supplies its own builds. Flat package at repo root next to `main.py` (no `src/` layout). See STACK.md.

**Core technologies:**
- Qiskit 2.5.2: circuits, `StatePreparation` (not `initialize()`, which cannot be inverted), `grover_operator()` function (the `GroverOperator` class is deprecated) — matches Qollab's installed version
- numpy: classical engines, exact solver, vendored MLAE fit — Qollab provides it, no pin needed
- qiskit-aer 0.17.2 (local only): statevector contract tests and full-simulation spot checks — behind a toggle on Qollab, keep out of `main.py`
- qiskit-algorithms 0.4.0 (local/tests only): IAE and MLAE cross-check of the vendored estimator — no longer IBM-supported, `transpiler=` bug in MLAE, `num_oracle_queries` undercounts
- `backend.run(circuits, shots=...)` + `get_counts()`: the only path that works on Qollab IonQ — `BackendSamplerV2` silently returns zeros there
- matplotlib: error-vs-N_A plot, histograms — Qollab's own build

### Expected Features

See FEATURES.md (30 table-stakes items C1–C8, Q1–Q9, P1–P4, D1–D10; differentiators X1–X10; anti-features A1–A13).

**Must have (table stakes):**
- Shared discrete problem spec (`Kernels` dataclass) consumed by both classical and quantum branches — the handoff contract
- Continuous classical MC with Woodcock delta tracking, seeded, vectorized, with collision-order tallies
- Discrete lattice MC sampling exactly the circuit's model (matched mode)
- Exact lattice solver (enumerate all random-bit strings) as ground truth; test that circuit amplitude matches it to 1e-9 or better
- Q0 (uncollided only, 5 qubits, checkable against e^{-τ}) then Q1 (12 qubits, beam) state-prep circuit
- Vendored numpy MLAE; cost accounted as N_A = Σ shots·(2k+1)
- RMSE-vs-N_A plot over ≥ 50 repetitions against the exact value, both methods, fitted slopes
- Exit-position histograms, labelled as circuit validation (direct sampling has no speedup)
- Sourced ENDF/B-VIII.0 one-group 14 MeV cross sections
- Prior-art section citing Olivier & Nowak, Lee/Lee/Kim, Miao/Jin/Sone; limitations section (noise, truncation K, no wall-clock claim)
- MIT license, attribution line, AI and library disclosure, README with run instructions, `main.py` that runs logged-out, demo video, repo link

**Should have (competitive):**
- Implicit-capture variance-reduction classical curve as "best classical" baseline
- Wall-thickness / rare-event study: QAE advantage grows as transmission gets rarer (ratio ≈ 1/(π ε √p))
- Crossover analysis and confidence-interval coverage check
- Q1-Y (16 qubits, uniform source, literal 8 position qubits)
- IonQ run at small Grover powers (k ≤ 8) showing noise effect

**Defer (v2+):**
- K=2 encoding (~20 qubits, ~50k CX per Grover step; local-only stretch)
- Interactive HTML/JS front end (Qollab JS/Qiskit project type can import the same package)
- Multigroup energy, anisotropic scattering, (n,2n), 3D

### Architecture Approach

One shared problem spec feeds two branches: the continuous classical engine (physics reference) and a shared discrete model (`model/kernels.py`) that in turn feeds the exact solver (truth), the discrete classical MC (like-for-like baseline), and the quantum circuit followed by the QAE layer with swappable runners (analytic, statevector/Aer, IonQ). All write result files that the analysis layer reads; the publication layer (`main.py` with a quick mode and precomputed JSON) sits on top. See ARCHITECTURE.md for the qubit/gate budget table (Q0, Q1, Q1-Y, Q2, naive walk).

**Major components:**
1. `physics/` + ProblemSpec — geometry (10 × 10 cm, 16 × 16 grid, 2.0 cm W boundary at 3.2 columns handled by kernels), cross sections, source definition
2. `classical/` — continuous delta-tracking MC, discrete lattice MC, implicit-capture variant, tallies and standard errors
3. `model/kernels.py` + `exact.py` — collision-to-collision probability kernels and exact enumerated transmission; the contract between teammates
4. `quantum/` — Q0/Q1/(Q1-Y) state preparation via `StatePreparation`, flag qubit, `grover_operator()`, transpile-once rule, IonQ 7-control decomposition
5. `qae/` — vendored MLAE, runners (analytic Binomial(shots, sin²((2k+1)θ)), Aer, IonQ), N_A accounting
6. `analysis/` — sweeps, RMSE over repetitions, slope fits, histograms, figures, results JSON ≤ 2 MB
7. `main.py` + docs — Qollab entry point with typed `main(...)` settings form, README, HANDOFF.md, prior art, limitations

### Critical Pitfalls

See PITFALLS.md (13 critical pitfalls with warning signs, prevention, phase mapping).

1. **Reused coin/direction qubits or mid-circuit reset inside A** — creates a coherent walk (interference) or a non-invertible A; use fresh qubits per random choice, unroll steps, no measurement inside A
2. **Classical and quantum estimating different quantities** — build the matched discrete MC and the exact solver; gate every QAE sweep on circuit amplitude == exact value
3. **Plotting QAE against raw shots or Qiskit's `num_oracle_queries`** — count N_A = Σ shots·(2k+1); plot RMSE over ≥ 50 runs against the exact value
4. **Qiskit API churn** — `initialize()` not invertible, `GroverOperator` deprecated, Samplers broken on IonQ/Aer with Grover ops, MLAE `transpiler=` bug; transpile the full circuit once, decompose > 7-control gates before IonQ
5. **Qollab publish/run failures discovered late** — hour-one smoke test: tiny `main.py`, IonQ simulator run, publish, logged-out incognito run; v0 published by ~hour 24; all IonQ cloud runs before hour 36
6. **Overclaiming** — no "first quantum transport", no "quantum advantage", no wall-clock speedup, no "neutrons are quantum so qubits are better"; cite prior art and Babbush et al. in limitations
7. **Handoff breakage** — placeholder files with spaces in names cannot be imported; rename; freeze `Kernels` early; HANDOFF.md

## Implications for Roadmap

Based on research, suggested phase structure (coarse, 5 phases):

### Phase 1: Platform Smoke Test and Repo Skeleton
**Rationale:** Qollab behaviour is undocumented and every later phase depends on it; compliance items block nothing and keep a partial submission eligible.
**Delivers:** Qollab + IonQ round trip with a toy MLAE circuit, logged-out run verified, `noise_model="ideal"` tested, Python/numpy versions printed; flat package layout, `main.py` stub, pinned `requirements.txt`, MIT LICENSE, attribution line, AI/library disclosure, GitHub remote with collaborators, placeholder files renamed.
**Addresses:** D1–D10 compliance features
**Avoids:** Qollab publish failures, handoff breakage, late discovery of platform limits

### Phase 2: Physics Spec, Classical Engines and Exact Solver
**Rationale:** The exact discrete answer is the ground truth for every later plot; the `Kernels` dataclass is the contract that lets quantum work start.
**Delivers:** ProblemSpec with sourced ENDF/B-VIII.0 14 MeV cross sections, continuous delta-tracking MC with collision-order tallies, `Kernels`, exact solver, discrete lattice MC, implicit-capture variant, analytic validation tests (e^{-τ} uncollided), standard-error-vs-N curve.
**Uses:** numpy, pytest
**Implements:** components 1–3

### Phase 3: Quantum Oracle and Estimator
**Rationale:** Needs frozen `Kernels`; highest technical risk; must pass the contract test before any sweep.
**Delivers:** Q0 then Q1 (Q1-Y optional) state preparation, contract test (statevector == exact to 1e-12), resource table (qubits, CX, depth), `grover_operator()` wiring, vendored MLAE validated against qiskit-algorithms, analytic/Aer/IonQ runners, N_A accounting, IonQ-ready decomposition.
**Uses:** Qiskit 2.5.2, qiskit-aer, qiskit-algorithms (tests only)
**Implements:** components 4–5
**Spike first:** re-verify the qubit/gate budget with real cross sections; choose Q1 vs Q1-Y.

### Phase 4: Scaling Study and Figures
**Rationale:** Produces the Core Value evidence; everything else is validation.
**Delivers:** RMSE-vs-N_A plot (≥ 50 repetitions, both methods, fitted slopes), results table, exit-position histograms, truncation-bias figure, precomputed JSON ≤ 2 MB, IonQ estimate at k ≤ 8 with noise discussion. Stretch: thickness/rare-event study, crossover, CI coverage.
**Implements:** component 6

### Phase 5: Publish, Documentation, Video and Handoff
**Rationale:** Submission is judged on documentation as much as code; must be live on Qollab before the deadline.
**Delivers:** `main.py` quick mode with typed settings, v0 published by ~hour 24 and final by deadline, README covering the four judging criteria, prior-art and limitations sections, demo video, HANDOFF.md, final logged-out run.
**Implements:** component 7

### Phase Ordering Rationale

- Phase 1 first because the platform risk is the one thing that can zero the submission, and compliance items are cheap.
- Phase 2 before 3 because the exact solver is the truth for the circuit contract test; Phases 2 and 3 can overlap once `Kernels` is frozen (teammate split: classical vs quantum).
- Phase 4 depends on both branches passing their contract tests.
- Phase 5 runs partly in parallel (docs skeleton early, v0 publish at hour 24) but finalizes last.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** empirical Qollab checks (logged-out flag, `noise_model` pass-through, Pyodide performance, IonQ gate-count limit)
- **Phase 2:** short ENDF/B-VIII.0 lookup for 14 MeV W and 316 SS values, non-elastic/(n,2n) treatment, transport correction
- **Phase 3:** qubit/gate budget spike with real cross sections; Lee/Lee/Kim full text for circuit design comparison

Phases with standard patterns (skip research-phase):
- **Phase 4:** standard sweep/plot patterns once runners exist
- **Phase 5:** standard docs/publish patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions from PyPI and Qollab's own bundle/docs; API behaviour reproduced locally |
| Features | MEDIUM | Rubric from secondary coverage; prior art from arXiv directly |
| Architecture | HIGH (structure) / MEDIUM (physics numbers) | Encoding prototyped and verified; cross sections are placeholders |
| Pitfalls | MEDIUM-HIGH | API facts verified; Qollab behaviour LOW |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- Real 14 MeV cross sections (W heavy alloy, 316 SS) from ENDF/B-VIII.0: Phase 2 lookup; K=1 coverage fraction (~90%) will move
- Qollab logged-out running flag: Phase 1 smoke test
- `noise_model="ideal"` acceptance on Qollab IonQ: Phase 1 test
- IonQ v0.4 gate/size limits: Phase 1/3 submission test
- Demo video requirement: confirm on qollab.xyz rules page (participant PDF says yes)
- Q1 vs Q1-Y headline choice: Phase 3 spike
- Pyodide performance for live demo: Phase 1/5

## Sources

### Primary (HIGH confidence)
- Qollab docs and site bundle — runtime, backends, primitives, project rules
- PyPI API — qiskit, qiskit-algorithms, qiskit-aer, qiskit-ionq versions
- Qiskit docs — `grover_operator`, `StatePreparation`, primitives V2
- IonQ docs — Qiskit guide, noise-model simulation, gate constraints
- arXiv:2410.19489 (Olivier & Nowak), PRD 111 116001 (Lee, Lee, Kim), arXiv:2607.10772 (Miao, Jin, Sone) — prior art
- arXiv:1904.10246 (Suzuki et al., MLAE), arXiv:1912.05559 (Grinko et al., IAE), arXiv:1504.06987 (Montanaro) — QAE theory
- Local prototype: Qiskit 2.5.2 + qiskit-algorithms 0.4.0 in a scratch venv

### Secondary (MEDIUM confidence)
- Quantum Zeitgeist coverage of the IonQ × Qollab hackathon — theme wording
- Pyodide 314.x lock file — inferred numpy/matplotlib versions

### Tertiary (LOW confidence)
- Qollab logged-out behaviour and `noise_model` pass-through — untested inference

---
*Research completed: 2026-10-09*
*Ready for roadmap: yes*
