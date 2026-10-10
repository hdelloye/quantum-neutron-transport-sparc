# Requirements: Quantum Neutron Transport: SPARC First Wall

**Defined:** 2026-10-10
**Core Value:** Show, on a real fusion-relevant transport problem, that quantum amplitude estimation reaches a target accuracy with fewer samples than classical Monte Carlo, with an honest classical baseline sitting next to it.

## v1 Requirements

Requirements for the hackathon submission (deadline Oct 11 2026, 7:00 PM ET). Each maps to roadmap phases.

### Platform & Repository

- [ ] **PLAT-01**: Repo has a flat package at root next to `main.py`, `requirements.txt` pinning `qiskit==2.5.2`, `pyproject.toml`, `tests/`, `scripts/`; placeholder files with spaces in names are removed or renamed
- [ ] **PLAT-02**: A toy `main.py` runs on Qollab's built-in simulator and on an IonQ simulator backend, is published, and runs start-to-finish from a logged-out browser (smoke test records Python/numpy/qiskit versions and whether `noise_model="ideal"` is accepted)
- [ ] **PLAT-03**: Repository is on GitHub with teammates as collaborators, MIT LICENSE, and the attribution line "This effort is supported by Qollab & IonQ." in README
- [ ] **PLAT-04**: Nothing reachable from `main.py` imports qiskit-aer or qiskit-algorithms; data files are ≤ 2 MB and loaded by literal path; `backend` is injected, never created in code

### Physics & Classical Baseline

- [ ] **PHYS-01**: ProblemSpec defines the 2D slab (10 cm × 10 cm, 16 × 16 grid), a 2.0 cm tungsten heavy alloy layer on the plasma side and 8.0 cm 316 stainless steel behind, with the material boundary handled correctly inside column 4
- [ ] **PHYS-02**: One-group 14 MeV cross sections (total, scattering, absorption incl. non-elastic treatment) for both materials are taken from ENDF/B-VIII.0 and cited with source and evaluation date
- [ ] **PHYS-03**: Continuous classical Monte Carlo (numpy, vectorized, seeded, Woodcock delta tracking, isotropic scattering, loss on exit) tallies transmission fraction, absorption fraction, exit-position histogram on the back face, and collision-order breakdown, with standard errors
- [ ] **PHYS-04**: Continuous MC passes analytic checks: uncollided transmission equals e^{-τ}, and histories are reproducible from a seed
- [ ] **PHYS-05**: `Kernels` dataclass holds the collision-to-collision probability tables (first-collision column, scatter ratio per column, escape probability per column and direction) derived from ProblemSpec, and is the frozen contract between classical and quantum code
- [ ] **PHYS-06**: Exact lattice solver enumerates every random-bit string of the discrete model and returns the exact "transmission within K collisions" (ground truth for all error plots)
- [ ] **PHYS-07**: Discrete lattice MC samples exactly the `Kernels` model (matched mode) and its mean converges to the exact value within standard error
- [ ] **PHYS-08**: Classical engine takes its random source as a parameter (numpy Generator by default) and never owns randomness

### Quantum Circuit

- [ ] **QC-01**: Q0 state-preparation circuit (uncollided transmission only, ~5 qubits) built with `StatePreparation` and a flag qubit; flag probability equals e^{-τ} on a statevector
- [ ] **QC-02**: Q1 state-preparation circuit (transmission within one collision, beam at mid-height, ~12 qubits) uses fresh qubits for every random choice, no measurement or reset inside A, and is invertible
- [ ] **QC-03**: Contract test: Q1 flag probability on the Aer statevector equals the exact lattice solver value to 1e-12
- [ ] **QC-04**: Grover operator is built with the `grover_operator()` function; powers Q^k reproduce sin²((2k+1)θ) on a statevector for k up to 64
- [ ] **QC-05**: Resource table reports qubits, CX count and depth for Q0, Q1 (and Q1-Y if built) after a single full-circuit transpile
- [ ] **QC-06**: Circuits sent to IonQ are decomposed so no gate has more than 7 controls, and transpiled once as a whole (never A and Q separately)

### Amplitude Estimation

- [ ] **QAE-01**: Vendored numpy maximum-likelihood amplitude estimation takes counts from a list of A Q^k circuits run as one `backend.run([...])` job and returns the estimate, matching qiskit-algorithms MLAE on the same counts in tests
- [ ] **QAE-02**: Three runners share one interface: analytic (Binomial draws from the exact θ), Aer shot-based, IonQ via injected backend using `backend.run` + `get_counts` (never a Sampler)
- [ ] **QAE-03**: Cost is reported as applications of A, N_A = Σ shots·(2k+1), never raw shots or Qiskit's `num_oracle_queries`
- [ ] **QAE-04**: Analytic runner agrees with the Aer shot-based runner at matched (k, shots) within statistical error on at least three points

### Scaling Study & Figures

- [ ] **ANLY-01**: Error-vs-N_A plot: RMSE over ≥ 50 repetitions against the exact value, for discrete classical MC and MLAE, on log-log axes with fitted slopes (expected ≈ −0.5 and ≈ −1)
- [ ] **ANLY-02**: Overlaid exit-position histograms, classical vs quantum (direct sampling of Q1), at matched shot counts, labelled as circuit validation rather than speedup evidence
- [ ] **ANLY-03**: Truncation-bias figure/table: transmission within K collisions vs full continuous transmission, so the K=1 approximation is quantified and disclosed
- [ ] **ANLY-04**: Wall-thickness / rare-event study: repeat the scaling comparison for at least three slab thicknesses and show the sample-count ratio growing as transmission falls
- [ ] **ANLY-05**: Precomputed sweep results and figures are committed as JSON/PNG ≤ 2 MB each so `main.py` can render them without rerunning the sweep

### Qollab Submission & Documentation

- [ ] **DOCS-01**: `main.py` exposes a typed `main(...)` quick mode (small live MLAE run on the injected backend plus rendering of precomputed figures) that completes in the judge's browser
- [ ] **DOCS-02**: A v0 is published on Qollab by roughly hour 24 and the final version before the deadline; final check from a logged-out browser
- [ ] **DOCS-03**: README covers what it does, the problem, how to run (locally and on Qollab), replication steps, and a section per judging criterion (novelty, technical execution, impact, documentation)
- [ ] **DOCS-04**: Prior-art section cites Olivier & Nowak (arXiv:2410.19489), Lee/Lee/Kim (PRD 111, 116001), Miao/Jin/Sone (arXiv:2607.10772) and states the narrowed novelty claim
- [ ] **DOCS-05**: Limitations section states: one-group physics, K-collision truncation, ideal-simulator scaling plot, noise on IonQ simulators, no wall-clock speedup claim, sampling-complexity argument only
- [ ] **DOCS-06**: Disclosure of all external libraries and AI tools used, with licenses, and confirmation the team may use them
- [ ] **DOCS-07**: Short demo video and repo link attached to the Qollab project page, theme tag Quantum Impact
- [ ] **DOCS-08**: HANDOFF.md describes module ownership, how to run tests, the frozen `Kernels` contract, and what is left to do, so teammates can continue from GitHub

## v2 Requirements

Deferred. Tracked but not in current roadmap.

### Classical

- **PHYS-09**: Implicit-capture variance-reduction curve as "best classical" baseline

### Quantum

- **QC-07**: Q1-Y uniform-source variant (16 qubits) with its own contract test
- **QC-08**: K=2 encoding (~20 qubits, local-only)
- **QAE-05**: IonQ noisy-simulator MLAE estimate at k ≤ 8 with noise discussion

### Analysis

- **ANLY-06**: Confidence-interval coverage check and crossover sample count

### Front end

- **UI-01**: Interactive HTML/JS visualization (Qollab JS/Qiskit project type importing the same package)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Qubit-sourced random bits as the quantum contribution | Rulebook excludes RNG-only projects; simulator bits are classical |
| Plasma turbulence / nonlinear plasma simulation | Quantum evolution is linear; published approaches scale worse than classical and do not fit 24 qubits |
| Multigroup or continuous-energy physics | Costs qubits the budget does not have |
| Anisotropic scattering, fission, (n,2n) multiplication | Out of v1 physics scope; noted in limitations |
| 3D geometry or finer than 16 × 16 | Position register would exceed the qubit budget |
| Real IonQ hardware | Hackathon provides the simulator only |
| Step-by-step quantum walk with reused direction qubits | Produces interference, not classical MC statistics; ~60 qubits |
| Iterative amplitude estimation on Qollab | Adaptive, multi-job; Qollab IonQ backends accept one job per run |
| Claims of "first quantum transport" or wall-clock speedup | Prior art exists; only sampling-complexity scaling is claimed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (filled by roadmap) | | |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 0
- Unmapped: 35 ⚠️

---
*Requirements defined: 2026-10-10*
*Last updated: 2026-10-10 after initial definition*
