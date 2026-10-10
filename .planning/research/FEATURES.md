# Feature Research

**Domain:** Hybrid classical + quantum Monte Carlo neutron transport demonstrator (QAE vs classical MC on a 2D SPARC first-wall slab), 48-hour hackathon submission
**Researched:** 2026-10-09
**Confidence:** MEDIUM overall. Rubric, prior art and QAE algorithm facts come from primary sources (HIGH/MEDIUM). Feature prioritization is judgment (MEDIUM). Note: the `classify-confidence` / `research-plan` seams could not run because `node` is not on PATH, so tiers below were assigned by hand. Primary sources (arXiv, official docs) are MEDIUM-HIGH. Secondary news coverage is MEDIUM.

---

## Read This First: Three Findings That Change the Feature List

1. **Close prior art exists, so the novelty claim must cite it and be scoped.** Olivier & Nowak (Thales, arXiv:2410.19489, Oct 2024) is titled "Monte Carlo particle transport on quantum computers". It does 2D heterogeneous shielding transport with a discrete-time quantum walk: a 2^n x 2^n position register, a 3-qubit coin, and a position-dependent coin built from local cross sections. It proposes amplitude amplification but reports **no amplitude-estimation results and no error-vs-queries plot**. Its runs are emulation only, and its flux diverges after tens of steps because of how it handles absorption. Miao, Jin & Sone (arXiv:2607.10772, Jul 2026) apply QAE to two nuclear expectations with no transport. A defensible claim is: "first end-to-end QAE estimate of a neutron-transport tally (first-wall transmission), with measured error-vs-oracle-query scaling against a matched classical MC baseline, on a fusion geometry with evaluated nuclear data." **Do not claim "first quantum neutron/particle transport."** A prior-art section that cites both papers is now table stakes. Confidence: HIGH (read from the arXiv abstract and HTML).

2. **The Quantum Impact theme asks for a real dataset and the best classical result.** Coverage of the event (Quantum Zeitgeist) describes the theme as "Use a real dataset ... Compare the best classical result with a hybrid version that adds a quantum step." Judging is on novelty, how well it runs, what it changes, and how clearly it is written. For this project, the "real dataset" is evaluated nuclear data (ENDF/B-VIII.0 14 MeV cross sections for W and Fe/Cr/Ni) and real SPARC materials. "Best classical" means the baseline needs at least one standard variance-reduction technique (implicit capture / survival biasing), not only analog MC. Confidence: MEDIUM. This is secondary coverage; the official Qollab rules page could not be fetched. **Verify the video and repo requirements on qollab.xyz.**

3. **The quantum circuit and the classical engine must sample the *same discrete model*, or the error-vs-N plot is meaningless.** Two consequences:
   - (a) The classical engine needs a **matched discrete mode** that uses the same lattice, flight-length discretization and step cap as the circuit, alongside the continuous-physics mode.
   - (b) For a classical random walk, each collision step needs its **own fresh random-bit qubits**. Reusing a 2-qubit direction register across steps without measurement gives a coherent quantum walk: paths interfere, and the ancilla amplitude is no longer the classical transmission probability.

   A pure nearest-neighbour walk with 1 cell = 0.625 cm and 3-4 steps also **cannot reach the back face** (16 cells away), so transmission would be exactly 0. Each step must be a collision-to-collision free flight of several cells. This drives the qubit budget (roughly steps x bits-per-step + position + flag) and makes an **exact reference value** feature mandatory. Confidence: HIGH for the physics and quantum-mechanics reasoning (Montanaro-style encoding of randomness as a superposition of random bits). The specific qubit arithmetic should be confirmed in ARCHITECTURE/PITFALLS.

---

## Feature Landscape

### Table Stakes (Judges Mark You Down Without These)

#### A. Classical MC engine

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| C1 | **Two-layer slab geometry** (2 cm W heavy alloy + 8 cm 316 SS), material lookup by x-cell | Core problem definition; every small MC code has a geometry/material map | LOW | Material = f(column index). Keep it a pure function so the quantum oracle can mirror it exactly. |
| C2 | **Cross-section table with provenance** (Σt, Σs, Σa per material at 14 MeV, plus density and composition used) | "Real dataset" requirement for Impact; it is the first question a nuclear-engineering judge asks | LOW | Pull MT=1/2/3 from ENDF/B-VIII.0 (NNDC/IAEA) and cite them. W-HA ~17-18.5 g/cc and 316 SS composition give macroscopic values. State the one-group simplification explicitly: non-elastic, including (n,2n), is treated as absorption. Sanity check: Σt(W) ~0.3/cm (mfp ~3 cm), consistent with PROJECT.md. |
| C3 | **Analog transport loop**: exponential free flight, isotropic 2D scatter, absorb/scatter by Σs/Σt, leak on any face | Minimal physics of any MC transport code | LOW | Vectorize over histories with numpy. Event-based is fine at this size. |
| C4 | **Tallies**: transmission (back face), reflection (front face), side leakage, absorption, exit-position histogram on the back face | Requirements list these; a conservation check (sum = 1) is the standard sanity test | LOW | Tally all leakage faces, not only the back, so they can be checked to sum to 1 with absorption. |
| C5 | **Statistical error per tally**: sample std error, relative error, 95% CI | Every MC code reports R (MCNP convention); a judge will reject numbers without error bars | LOW | Binomial: sqrt(p(1-p)/N). Report relative error R as well. |
| C6 | **Pluggable random-bit source + seeded reproducibility** (`numpy.random.Generator` via `SeedSequence`, injected) | Already a PROJECT.md decision. Seeded reruns are standard reproducibility practice | LOW | Same seed must give identical tallies. Record the seed in every results file. |
| C7 | **Matched discrete mode**: same lattice, discretized flight lengths, direction set and step cap as the quantum circuit | Without it, the error comparison is between two different estimands (see finding 3) | MEDIUM | Make the discrete model a separate, explicit "model spec" object that both the engine and the circuit builder consume. |
| C8 | **Analytic / limit-case validation tests** | Standard V&V for transport codes; cheap credibility | LOW | (i) Uncollided transmission = exp(-Σt,W·2 - Σt,SS·8). (ii) Pure absorber gives transmission = uncollided. (iii) Σa=0 gives absorption = 0. (iv) Leak + absorb = 1. Write these as pytest tests. |

#### B. Quantum (QAE) side

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| Q1 | **State-preparation operator A**: random-bit registers in superposition (amplitude-loaded with material-dependent probabilities) → reversible walk arithmetic on the position register → transmission flag ancilla | It is the actual quantum contribution. The amplitude on flag=1 must equal the discrete-model transmission probability | HIGH | Fresh random qubits per step; no mid-circuit measurement, because QAE needs a coherent A. Material-dependent probabilities are controlled RY rotations conditioned on the x-register. This is the hardest feature; budget most of the build time here. |
| Q2 | **Exact reference value** for the discrete model: classical enumeration over all random-bit strings, **and** the statevector probability of flag=1 from Aer | Lets every error plot use *true* error instead of estimated error. It also proves A is correct (they must agree to ~1e-12) | LOW-MEDIUM | With ≤ ~20 random bits, enumeration is ≤ 1M cases and takes seconds. This is the single most important correctness gate. |
| Q3 | **Grover operator Q** built from A and the flag oracle (Qiskit `grover_operator` / `EstimationProblem`) | Standard QAE construction | LOW (given A) | Qiskit 2.x API details belong in STACK.md. |
| Q4 | **Iterative or maximum-likelihood QAE** (IAE, Grinko et al. 2021; MLAE, Suzuki et al. 2020) as the main estimator | Needs **no extra evaluation qubits** (canonical QPE-based QAE needs m more), which matters under a 24-qubit cap. It is also the de facto choice in published demos | MEDIUM | `qiskit-algorithms` has IAE/MLAE/FAE, but its README says it is "no longer officially supported by IBM", and Qiskit 2.0 broke its `BaseSampler` imports (community reports). **Plan a ~100-line in-house IAE or MLAE fallback** that runs circuits Q^k A directly through a Sampler. Confidence: MEDIUM. |
| Q5 | **Honest query accounting**: N_quantum = total applications of A, Σ shots·(2k+1), not raw shot count | 1/N scaling is in oracle queries. Plotting "shots" for QAE hides the Grover depth and is the most common way these demos mislead | LOW | Log k-schedule and shots per round for every run. |
| Q6 | **Confidence interval output** from QAE (Clopper-Pearson / Chernoff, which IAE provides natively) | The classical side reports CIs (C5), so the quantum side must too | LOW | Report the CI next to the estimate in the results table. |
| Q7 | **Resource table**: qubits, depth, 2-qubit gate count for A and for Q^k at each k used, after transpiling to the IonQ native gate set | Judges in "how well it runs" look for this. It also answers "would this run on real hardware?" | LOW | Use `transpile` with the IonQ backend target. Report the maximum k actually run. |
| Q8 | **Backend switch**: local Aer (dev/sweeps) ↔ IonQ simulator via Qollab (submission run), selected with one config flag | The rules require running on the IonQ simulator; local Aer avoids the shared queue | LOW | The same code path is used for both; only the Sampler changes. |
| Q9 | **≤ 24 qubits, verified programmatically** (assert in code, and print the qubit count in the notebook) | Hard platform constraint | LOW | Fail fast if the model spec would exceed the budget. |

#### C. Comparison and plots

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| P1 | **Headline log-log plot: RMSE vs N** (classical histories vs QAE oracle queries), averaged over R independent repetitions (R ≥ 30), with reference slopes −1/2 and −1 and fitted slopes printed | This is the evidence for the Core Value. A single-run error curve is too noisy to show a slope | MEDIUM | Use the true error from Q2. Powers of two for N. Shade ±1σ bands across repetitions. |
| P2 | **Overlaid exit-position histograms** (classical vs quantum at matched N) | In the requirements, and makes the result visual | LOW-MEDIUM | **Caution:** QAE estimates one scalar. A histogram from *direct sampling* of A has no speedup; label it "distribution validation: the circuit encodes the same physics". If a QAE histogram is wanted, run one QAE per bin (16x cost) on 2-4 bins only. |
| P3 | **Results table**: estimate ± CI, true value, queries used, wall time, for both methods at 2-3 target accuracies | Judges skim tables. "Queries to reach 1% relative error" is the cleanest single comparison number | LOW | Generated from cached results. |
| P4 | **Cached results + plot regeneration without rerun** (JSON/CSV in `results/`) | Judges and teammates must reproduce the figures without waiting on the IonQ queue | LOW | Plot scripts read only from `results/`. |

#### D. Reproducibility and documentation (rubric: "how clearly it is written" and "how well it runs")

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| D1 | **Single runnable entry point** (notebook on Qollab plus `python -m` script locally) with a **fast mode** (< 2-3 min) and a full mode | It must run without error from a logged-out Qollab browser. Judges will not wait 30 min | LOW-MEDIUM | Fast mode: small sweep, few repetitions, reads cached full results for the plots. |
| D2 | **README**: one-paragraph pitch, headline figure, quickstart, repo map, how to reproduce each figure, and a results summary | Baseline for every hackathon judging pass | LOW | Put the headline plot above the fold. |
| D3 | **Attribution line** "This effort is supported by Qollab & IonQ." | Explicit submission requirement (PROJECT.md) | LOW | In the README, the notebook header and the Qollab project page. |
| D4 | **MIT LICENSE file** | Explicit requirement | LOW | Root `LICENSE`. |
| D5 | **Library and AI-tool disclosure** (Qiskit, qiskit-ionq, numpy, matplotlib, any qiskit-algorithms use, and AI assistants used) | Explicit requirement | LOW | `ACKNOWLEDGMENTS` section in the README. |
| D6 | **Judging-criteria writeup**: one section each for Novelty, Technical Execution, Impact, Documentation | Maps the work onto the rubric so judges do not have to infer it | LOW | Novelty section = prior-art table (Olivier & Nowak 2024; Miao/Jin/Sone 2026; Montanaro 2015; Stamatopoulos 2020 option pricing as the QAE-MC template) plus the scoped claim. |
| D7 | **Limitations / threats-to-validity section** | Expected by any technical judge; pre-empts "but on a simulator..." | LOW | Must state: (i) the speedup is in oracle-query complexity, not wall-clock, and simulating the circuit classically is exponentially *slower*; (ii) at this toy size, exact enumeration beats both methods, so the argument is about scaling; (iii) one-group, 2D, isotropic, (n,2n) ignored; (iv) the noiseless simulator overstates achievable Grover depth. |
| D8 | **Demo video** (2-4 min) | Listed in PROJECT.md as required. Not confirmed in public event coverage, so verify on qollab.xyz | LOW-MEDIUM | Script: problem (SPARC wall), physics, circuit, headline plot, limitations. Record it from the notebook. |
| D9 | **Modular repo layout** (`transport/`, `quantum/`, `experiments/`, `results/`, `docs/`, `tests/`) | PROJECT.md handoff requirement; also scores on documentation | LOW | One shared `model_spec` module consumed by both sides (C7). |
| D10 | **Pinned dependencies** (`requirements.txt` with exact versions) | Qiskit API churn (1.x → 2.x) breaks unpinned demos | LOW | Pin to what Qollab runs. Check its Qiskit version first. |

### Differentiators (Competitive Advantage)

Ordered by value-to-cost for this rubric.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| X1 | **"Best classical" baseline with variance reduction** (implicit capture / survival biasing, optionally Russian roulette) plotted as a third curve | Directly answers the Impact theme's "best classical result". Shows that VR improves the constant but keeps slope −1/2, while QAE changes the exponent. This is a strong argument that judges rarely see | LOW-MEDIUM | Implicit capture is ~15 lines. Use weighted-tally variance for its error. |
| X2 | **Rare-event / thickness scaling study**: queries-to-reach-target-*relative*-error vs wall thickness (or vs transmission p) | Classical needs N ~ 1/(p ε²) and QAE needs ~ π/(ε √p), so the advantage ratio ~ 1/(π ε √p) **grows as transmission shrinks**. Deep-penetration shielding is exactly where MCNP/OpenMC struggle. This is the "what it changes" story | MEDIUM | Can use exact statevector values plus IAE runs on Aer at 3-4 thicknesses. Even a theoretical-curve overlay anchored to measured points is persuasive. |
| X3 | **Crossover analysis**: the N (or target accuracy) where QAE first beats classical, including constant factors | Honest framing; shows the team understands that the asymptotics do not apply at small N | LOW | Falls out of P1 data. |
| X4 | **CI coverage check**: the fraction of R repetitions whose 95% CI contains the true value, for both methods | Shows statistical rigor; catches a mis-specified IAE alpha | LOW | Needs the repetition harness from P1. |
| X5 | **Engineering impact translation**: convert transmission into backing-structure fluence per MW fusion power for SPARC (~140 MW fusion, ~5.6e19 n/s at 14 MeV), and into "histories needed for 1% relative error" vs "QAE queries needed" | Turns a toy number into a design-relevant statement (wall lifetime, magnet shielding budget) | LOW | Back-of-envelope with stated assumptions. Cite the SPARC power figure. |
| X6 | **Continuous-physics reference + discretization-bias report**: transmission from continuous classical MC vs discrete-model exact value | Quantifies how much physics the 16x16 / few-step encoding loses. A judge-proof answer to "is your circuit still physics?" | LOW | Both modes already exist (C3, C7). |
| X7 | **Noise-model run** (IonQ Aria/Forte noise model, if exposed through Qollab, or an Aer depolarizing model) showing where Grover depth stops helping | Connects to real hardware feasibility. IonQ's own low-depth AE paper (Giurgica-Tiron et al., PRR 2022) only reached ~depth 60 / ~90 two-qubit gates | MEDIUM | Stretch goal. Keep it out of the headline plot so noise does not confound the scaling result. |
| X8 | **Low-depth AE variant** (MLAE with a linear/power-law k schedule) compared with IAE on max depth vs achieved error | Shows awareness of NISQ depth limits. Trades some speedup for depth | MEDIUM | Only after IAE works. |
| X9 | **Cross-check against OpenMC** for the continuous slab transmission | External validation by an industry-standard code | MEDIUM-HIGH | OpenMC plus nuclear data install is heavy for 48 h. Optional and post-core; cite rather than run if time is short. |
| X10 | **Circuit diagram + annotated "how the walk is encoded" figure** | Huge documentation win; most QAE demos are opaque | LOW | One schematic of the registers (position, per-step random bits, flag) plus one zoomed `qc.draw('mpl')` of a single step. |

### Anti-Features (Deliberately Do NOT Build)

| # | Anti-Feature | Why Requested | Why Problematic | Alternative |
|---|--------------|---------------|-----------------|-------------|
| A1 | **Qubit-sourced random numbers as "the quantum version"** | Easy, and sounds quantum | Event coverage says random output alone does not qualify (stated for Playground; same spirit applies). On a simulator the bits are classical PRNG output anyway. Zero efficiency gain | Keep the pluggable bit source (C6) as plumbing only. The quantum contribution is QAE. |
| A2 | **"Neutrons are quantum, so qubits model them better"** framing | Intuitive pitch | Physically wrong for this problem: 14 MeV neutron transport is a classical linear Boltzmann / Markov process. Experts will penalize it | Frame the advantage purely as sampling complexity: 1/N vs 1/√N in oracle queries. |
| A3 | **Coherent quantum walk with a reused coin register** (no fresh random qubits per step, no measurement) | Saves qubits; looks like Olivier & Nowak | Paths interfere. The flagged amplitude is not the classical transmission probability, so QAE estimates the wrong number | Fresh random-bit qubits per collision step, and fewer steps. Validate with Q2. |
| A4 | **Mid-circuit measurement/reset inside A** | Lets you reuse qubits for more steps | Breaks the coherence QAE needs (Q must be unitary on A's output). Olivier & Nowak report it made their amplified strategy expensive | Bound the step count; accept a shallower walk. |
| A5 | **Canonical QPE-based QAE as the main estimator** | It is the "textbook" QAE | Costs m extra evaluation qubits plus a QFT, which competes with the walk under a 24-qubit cap | IAE/MLAE (Q4). Optionally one tiny canonical-QAE point for illustration. |
| A6 | **Plotting QAE error vs raw shots** | Simpler bookkeeping | Hides Grover depth; misleading; experts will notice | Oracle-query accounting (Q5). |
| A7 | **Comparing QAE (discrete model) against continuous-physics classical MC on the error plot** | The continuous code is "more real" | The two estimate different quantities, so the error mixes bias with variance and the slope comparison is invalid | Matched discrete mode (C7) for P1; continuous mode only for X6. |
| A8 | **Claiming wall-clock speedup or "exponential speedup"** | Headline appeal | False on a simulator, and false asymptotically (QAE is quadratic) | State "quadratic reduction in oracle queries" plus the limitations section (D7). |
| A9 | **QAE histogram over all 16 bins as the headline** | Looks impressive | 16 separate estimations, 16x cost, and burns the shared queue | Sampling-based histogram labelled as validation (P2); QAE on 1-4 bins at most. |
| A10 | **Full sweeps on the shared IonQ queue during development** | "Test on the real target" | Queue latency kills a 48 h schedule; shared resource | Aer for all sweeps; IonQ simulator only for the final reference runs (Q8). |
| A11 | **Interactive HTML/Java visualization in v1** | Demo appeal | Already deferred in PROJECT.md; competes with the core for time | Static matplotlib figures plus the video. v2 after handoff. |
| A12 | **Multigroup, 3D, anisotropic scattering, (n,2n), real hardware** | "More realistic" | Each one breaks the qubit budget or confounds the scaling result | List them as future work in D7. |
| A13 | **Novelty claim "first quantum neutron transport"** | Strong pitch | Falsified by Olivier & Nowak (2024) | Scoped claim (finding 1), with citation. |

---

## Feature Dependencies

```
C1 geometry ─┬─> C3 analog loop ──> C4 tallies ──> C5 stat errors
C2 xs table ─┘          │
                        └──> X1 variance-reduction baseline
C6 bit source ──> C3, C7

C7 matched discrete model spec ──┬──> Q1 state prep A ──> Q3 Grover Q ──> Q4 IAE/MLAE ──> Q5/Q6 accounting + CI
                                 ├──> Q2 exact reference (enumeration) <──cross-check──> Q1 (statevector)
                                 └──> classical matched-mode runs
Q9 qubit-budget assert ──gates──> Q1

Q2 + Q4/Q5 + classical matched mode ──> P1 RMSE-vs-N headline plot ──┬──> X3 crossover
                                                                      ├──> X4 CI coverage
                                                                      └──> X2 thickness/rare-event study
Q1 (direct sampling) + C4 histogram ──> P2 overlaid histograms
Q1, Q3 ──> Q7 resource table ──> X7 noise run, X8 low-depth AE
P1, P2, P3 ──> P4 cached results ──> D1 entry point (fast mode) ──> D8 video
Everything ──> D2/D6/D7 writeup;  D3, D4, D5, D9, D10 independent (do on day 1)

Conflicts:
A3/A4 (coin reuse, mid-circuit measure) ──conflicts──> Q4 (QAE needs coherent unitary A)
A5 canonical QAE ──conflicts──> Q1 qubit budget
A7 continuous-vs-discrete comparison ──conflicts──> P1 validity
```

### Dependency Notes

- **C7 (model spec) is the keystone.** Q1, Q2 and the matched classical runs all consume it. Define it first, as data (grid, cell size, flight-length bins, direction set, step cap, per-material probabilities), before writing either engine's discrete path.
- **Q2 gates everything quantum.** Do not run any QAE sweep until the statevector flag probability equals the enumerated exact value. Otherwise P1 measures error against the wrong target.
- **P1 requires the repetition harness.** X3, X4 and X2 are nearly free once P1's harness exists, which is why they rank high among differentiators.
- **X1 enhances P1.** It adds the "best classical" curve on the same axes.
- **D3/D4/D5/D9/D10 have no dependencies.** Do them in the first hour so a partial submission is still eligible.
- **Q4 depends on the qiskit-algorithms / Qiskit version check (STACK).** If the library is incompatible with Qollab's Qiskit, the in-house IAE/MLAE is on the critical path.

---

## MVP Definition

### Launch With (v1, must ship by Oct 11 19:00 ET)

- [ ] D3, D4, D5, D9, D10: attribution, license, disclosure, layout, pins. Partial-submission insurance.
- [ ] C1-C6, C8: continuous classical engine with tallies, errors, seeds and validation tests. The honest baseline.
- [ ] C7: shared discrete model spec plus the matched classical mode. Makes the comparison valid.
- [ ] Q1, Q2, Q3, Q9: state prep, exact reference, Grover operator, budget assert. The quantum core.
- [ ] Q4, Q5, Q6, Q8: IAE (or MLAE) with query accounting and CI, Aer and IonQ backends. The quantum result.
- [ ] P1, P2, P3, P4: headline RMSE-vs-N plot, histograms, results table, cached results. The evidence.
- [ ] Q7: resource table. Cheap, and it answers "would it run?"
- [ ] D1, D2, D6, D7, D8: entry point with fast mode, README, rubric writeup with prior art and scoped novelty, limitations, video. Rubric coverage.
- [ ] X1: implicit-capture "best classical" curve. Low cost; directly addresses the theme wording.

### Add After Core Works (v1.x, inside the window if time allows)

- [ ] X3 crossover and X4 CI coverage, as soon as the P1 harness exists (near-free).
- [ ] X5 engineering-impact translation, during the writeup (just arithmetic).
- [ ] X6 discretization-bias report, once both modes produce numbers.
- [ ] X10 encoding schematic, during the writeup.
- [ ] X2 thickness/rare-event study, if Q1 is parameterized by layer thickness. Strongest "impact" add-on.

### Future Consideration (v2+, after handoff)

- [ ] X7 noise-model study and X8 low-depth AE: needs stable core and time; risk of confounding the message.
- [ ] X9 OpenMC cross-check: heavy install.
- [ ] Interactive visualization (A11), multigroup, 3D, (n,2n), hardware runs (A12).

---

## Feature Prioritization Matrix

| Feature | Judge Value | Implementation Cost | Priority |
|---------|-------------|---------------------|----------|
| D3/D4/D5/D9/D10 compliance basics | HIGH (disqualifying if missing) | LOW | P1 |
| C1-C6, C8 classical engine + validation | HIGH | LOW | P1 |
| C7 matched discrete model spec | HIGH | MEDIUM | P1 |
| Q1 state preparation A | HIGH | HIGH | P1 |
| Q2 exact reference / statevector check | HIGH | LOW-MEDIUM | P1 |
| Q3/Q4 Grover + IAE/MLAE | HIGH | MEDIUM | P1 |
| Q5/Q6 query accounting + CI | HIGH | LOW | P1 |
| Q8/Q9 backend switch + budget assert | HIGH | LOW | P1 |
| P1 RMSE-vs-N headline plot | HIGH | MEDIUM | P1 |
| P2 overlaid histograms (sampling, labelled) | MEDIUM | LOW-MEDIUM | P1 |
| P3/P4 results table + cache | MEDIUM | LOW | P1 |
| Q7 resource table | MEDIUM | LOW | P1 |
| D1/D2/D6/D7 entry point + docs | HIGH | LOW-MEDIUM | P1 |
| D8 demo video | HIGH (if required) | LOW-MEDIUM | P1 |
| X1 variance-reduction baseline | HIGH | LOW-MEDIUM | P1 |
| X3 crossover, X4 CI coverage | MEDIUM | LOW | P2 |
| X2 rare-event thickness study | HIGH | MEDIUM | P2 |
| X5 engineering impact numbers | MEDIUM | LOW | P2 |
| X6 discretization-bias report | MEDIUM | LOW | P2 |
| X10 encoding schematic | MEDIUM | LOW | P2 |
| X7 noise model, X8 low-depth AE | MEDIUM | MEDIUM | P3 |
| X9 OpenMC cross-check | LOW-MEDIUM | MEDIUM-HIGH | P3 |

---

## Competitor / Prior-Art Feature Analysis

| Feature | Olivier & Nowak 2024 (arXiv:2410.19489) | Miao/Jin/Sone 2026 (arXiv:2607.10772) | Typical QAE finance demo (Stamatopoulos 2020; Qiskit Finance tutorials) | Our Approach |
|---------|------------------------------------------|----------------------------------------|-----------------------------------------------------|--------------|
| Transport geometry | 2D heterogeneous "bypass" grid, reflective boundaries, Σt = 1 fixed | None (scalar expectations) | None (payoff distribution) | 2D two-layer W + 316 SS slab, leakage boundaries, ENDF-derived Σ |
| Walk encoding | Coherent discrete-time quantum walk, 3-qubit coin reused, non-unitary coin via ancilla | n/a | Distribution loaded once (no walk) | Fresh random bits per collision step, so it is a classical Markov chain in superposition |
| Amplitude estimation | Proposed (amplification), **no AE results** | Canonical QAE; QPE up to 14 qubits; resonance case via exact Grover eigendecomposition | IAE/canonical QAE | IAE/MLAE (zero extra qubits), gate-level, run on Aer and the IonQ simulator |
| Error-vs-queries evidence | None | O(1/T²) MSE scaling shown | Usually shown | RMSE vs oracle queries over ≥30 repetitions, with a VR classical baseline and a crossover |
| Classical baseline | Finite differences + 500k-particle MC | Classical MC | Classical MC | Analog MC + implicit capture, matched discrete model + continuous physics |
| Hardware/noise | Emulation only | Simulation | Mostly simulation | IonQ simulator (ideal); optional noise model |
| Known weakness | Flux diverges after tens of steps (absorption treatment); depth exponential in position qubits | No transport | No physics | Few collision steps (qubit cap); one-group; quantify via X6 |

---

## Sources

- Olivier, N. & Nowak, M., "Monte Carlo particle transport on quantum computers", arXiv:2410.19489 (Oct 2024). https://arxiv.org/abs/2410.19489 and https://arxiv.org/html/2410.19489v1. Confidence: HIGH (primary).
- Miao, J., Jin, M., Sone, A., "Demonstrating Quadratic Monte Carlo Speedup via Quantum Amplitude Estimation: Nuclear Engineering Examples", arXiv:2607.10772 (Jul 2026). https://papers.cool/arxiv/2607.10772. Confidence: HIGH (abstract).
- Quantum Zeitgeist, "IonQ and QOLLAB host a quantum hackathon this October" (themes, judging criteria, MIT, Qollab/IonQ simulator, prizes). https://quantumzeitgeist.com/ionq-quantum-hackathon-qollab-host/. Confidence: MEDIUM (secondary; the official qollab.xyz rules were not reachable).
- Grinko, D. et al., "Iterative Quantum Amplitude Estimation", arXiv:1912.05559 / npj QI 2021. https://arxiv.org/pdf/1912.05559v2. Confidence: HIGH.
- Yu, K. et al., "Comparison of Amplitude Estimation Algorithms by Implementation", arXiv:2005.05300. https://arxiv.org/pdf/2005.05300. Confidence: MEDIUM (abstract only).
- Giurgica-Tiron, T. et al., "Low depth amplitude estimation on a trapped ion quantum computer", arXiv:2109.09685 / PRR 4, 033034 (2022). https://arxiv.org/abs/2109.09685. Confidence: HIGH.
- qiskit-community/qiskit-algorithms README ("no longer officially supported by IBM"). https://github.com/qiskit-community/qiskit-algorithms. Confidence: HIGH for the status; Qiskit 2.x incompatibility reported by the community is MEDIUM. Verify in STACK.
- Qiskit-algorithms IAE API (sampler-based constructor). https://qiskit.org/ecosystem/algorithms/stubs/qiskit_algorithms.IterativeAmplitudeEstimation.html. Confidence: MEDIUM.
- IonQ docs, simulation with noise models (Aria 25 qubits, Forte 36). https://docs.ionq.com/guides/simulation-with-noise-models. Confidence: MEDIUM.
- Bachoc et al., interacting-particle methods for neutron-shielding rare events (motivation for X2). https://www.math.univ-toulouse.fr/~fbachoc/manuscript_REDVAR_accepted.pdf. Confidence: MEDIUM.
- Background (training knowledge, not re-fetched; LOW-MEDIUM): Montanaro 2015 "Quantum speedup of Monte Carlo methods" (encoding classical randomness as a superposition of random bits); Suzuki et al. 2020 MLAE; Stamatopoulos et al. 2020 "Option pricing using quantum computers"; MCNP relative-error (R) reporting convention; ENDF/B-VIII.0 MT=1/2/3 for W and Fe.

---
*Feature research for: hybrid classical + QAE Monte Carlo neutron transport demonstrator (Qollab x IonQ hackathon)*
*Researched: 2026-10-09*
