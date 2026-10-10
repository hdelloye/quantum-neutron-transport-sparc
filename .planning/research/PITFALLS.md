# Pitfalls Research

**Domain:** Hybrid classical + quantum Monte Carlo neutron transport (Qiskit QAE on the IonQ simulator via Qollab, 24 qubits or fewer, 48-hour hackathon)
**Researched:** 2026-10-09
**Confidence:** MEDIUM overall. Library and API facts are HIGH: they come from PyPI metadata, qiskit-algorithms source code and Qiskit docs. Qollab platform behaviour is LOW, because public documentation is almost nonexistent. Physics and QAE-design pitfalls are MEDIUM: they rest on standard theory plus prior papers, and have not been run here yet.

**Suggested phase labels used below.** The roadmapper should rename these to match the real roadmap.
- **P0 Platform Smoke Test:** Qollab + IonQ simulator round trip, version discovery, a toy IAE run end to end.
- **P1 Physics Spec + Classical Engine:** cross sections, geometry, continuous engine, lattice engine, exact solver.
- **P2 Quantum Oracle (A):** reversible state preparation for the walk, qubit budget, a contract test against the exact solver.
- **P3 QAE + Scaling Study:** IAE/MLAE, query accounting, error-versus-cost sweep, plots.
- **P4 Publish, Docs, Video, Handoff:** Qollab publish, logged-out check, README/attribution/MIT, demo video, teammate handoff.

---

## Critical Pitfalls

### Pitfall 1: The qubit budget leaves out the per-step random bits, and fixing that breaks the 16x16 / multi-step plan

**What goes wrong:**
The PROJECT.md budget is 8 position qubits, 2 direction qubits, 3-4 step-counter qubits, 1 flag, and the rest for phase estimation. It never counts the qubits that hold each step's random choices. A QAE oracle A must be unitary: no measurement, no reset. So every random decision (collide or not, absorb or scatter, new direction, flight length) needs **fresh qubits that are never reused**. Reusing a "coin" qubit without a reset turns the classical random walk into a *quantum* walk. Paths interfere, the distribution spreads ballistically, and the amplitude no longer equals the classical transmission probability. Olivier & Nowak (arXiv 2410.19489) hit exactly this. They needed non-unitary coins, extra ancillas and partial measurements, and their measured walk diverged from classical results after tens of steps.

**Why it happens:**
Classical MC intuition says "randomness is free, draw another number." On a coherent circuit, entropy has to be stored somewhere, and that somewhere is qubits. Montanaro-style quantum MC builds A as "Hadamards/rotations on a seed register, then a reversible deterministic circuit." The seed register grows linearly with the number of random decisions.

**Consequences:**
- With 24 qubits: 8 (x,y) + 2 (direction) + about 2 (alive/absorbed, transmitted) leaves roughly 12 qubits for all randomness across all steps.
- At about 3 random qubits per lattice step (1 interaction rotation + 2 direction), that is roughly 4 steps.
- Moving one cell per step, a neutron needs **at least 16 steps just to cross a 16-cell slab**. The planned 16x16 walk with a step counter cannot transmit anything except under a different step model. This forces a rewrite if it is discovered in hour 20.

**How to avoid:**
- In P2, before writing gates, write down the budget formula: `n_total = n_x + n_y + n_dir + n_flags + K * (bits per collision event) [+ carry/ancilla]`. Solve it for K, the number of events that fit.
- Drop the step-counter register entirely. The circuit is unrolled, so the step index is classical and costs no qubits.
- Drop "remaining qubits for QAE phase estimation." Use IAE or MLAE, which need **zero** extra qubits (see Pitfall 3).
- Use **collision-to-collision flights** instead of cell-by-cell moves. Each event samples a flight length from a small distance register (2-3 qubits, exponential distribution amplitude-encoded with a few RY rotations), then a lateral direction. Use **Woodcock delta tracking** (one majorant cross section for the whole slab) so the flight-length distribution does not depend on position. Material then only enters as a position-controlled accept/reject rotation at the collision site, which is cheap because it is controlled on a few x bits.
- Define the quantum estimand honestly as **transmission within K collisions** (a truncated collision-order expansion, a standard transport concept). Compute the same truncated quantity exactly on the classical side (Pitfall 5).
- Seriously consider a reduced quantum geometry if K comes out at 2 or less in 2D. Options: QAE on an x-only (1D) slab, with y kept for the classical histogram; or a coarser y register (2 qubits). Make this decision in P2 with numbers, not in P3 in a panic.

**Warning signs:**
- The circuit diagram has the same "coin" qubit acted on in every step with no fresh qubits added.
- The quantum transmission comes out higher than classical, or the exit distribution looks ballistic or two-peaked (interference fingerprints).
- `A.num_qubits` creeps past 24 as steps are added.

**Phase to address:** P2, with a budget spreadsheet produced at the very start of P2. Flag P2 for deeper research and spikes.

---

### Pitfall 2: Apples-to-oranges comparison (classical and quantum estimate different quantities)

**What goes wrong:**
The classical engine samples continuous exponential flights with isotropic directions, interfaces at exactly 2 cm, and unbounded collisions. The quantum circuit encodes a lattice of 0.625 cm cells, 4 directions, a truncated number of events, and integer-cell interfaces. The two transmission fractions differ by a model bias (often several percent absolute). On an error-versus-cost plot, the quantum error then **floors at the model discrepancy** and the 1/N line flattens. Or the plot is quietly measured against the quantum circuit's own exact value while classical is measured against something else.

Specific mismatches to expect:
- **Interface position:** 2 cm / 0.625 cm = 3.2 cells. The quantum material boundary must sit at x=3 or x=4 cells (x<4 is cheapest: the two top bits of x are 00), while the classical engine puts it at 2.0 cm.
- **Truncation:** the quantum circuit stops after K events, so neutrons still alive are neither transmitted nor absorbed.
- **Direction set:** 4 lattice directions with backward probability 1/4 are not 2D/3D isotropic.
- **Source definition:** pencil beam at the centre cell versus uniform over the front face.
- **"Transmission" definition:** back face only, versus any exit. Side leakage on a 10 cm wide slab is large and must be a separate tally.

**Why it happens:**
The classical engine gets built first as "the physics." The quantum circuit later gets whatever simplifications fit, and nobody re-derives the classical side to match.

**How to avoid:**
- Build **three classical solvers** in P1:
  1. Continuous-physics MC: the physics reference, for the impact narrative.
  2. **Lattice MC** that runs the *identical* Markov chain the circuit encodes (same cells, directions, truncation K, source, tallies).
  3. **Exact solver** for that lattice chain: dynamic programming over (x, y, dir, alive) for K steps. It is tiny, about 256x4 states, and runs in milliseconds.
- The exact lattice value `p_star` is ground truth for **both** the lattice MC and QAE error curves.
- Report continuous-vs-lattice difference separately as discretization/model error.
- Write one `ProblemSpec` dataclass (geometry, sigmas, source, K, tally definitions) that both the classical lattice engine and the circuit builder consume. Never hard-code numbers twice.

**Warning signs:**
- QAE error stops improving at some N even though IAE confidence intervals keep shrinking.
- "Classical says 0.21, quantum says 0.17" and someone proposes "noise" as the explanation.
- Two files contain the literal `0.625` or `2.0` independently.

**Phase to address:** P1 (spec + lattice engine + exact solver), enforced by the P2 contract test.

---

### Pitfall 3: Using canonical (phase-estimation) QAE, or code written against the removed Qiskit APIs

**What goes wrong:**
- Canonical QAE (`AmplitudeEstimation` with `num_eval_qubits=m`) adds m evaluation qubits **and** requires a *controlled* Grover operator. That makes an already deep A much deeper. With A at about 20 qubits, at most m=4 fits (M=16), and the estimate snaps to the grid `sin^2(pi*y/M)` with discretization bias. The resulting "1/N plot" is a staircase.
- Separately, nearly every tutorial, StackOverflow answer and LLM-generated snippet uses `from qiskit.algorithms import ...`, `from qiskit.primitives import Sampler` (V1), `from qiskit import Aer, execute`, or `GroverOperator(...)`. In a current Qiskit 2.x environment these fail with `ImportError`/`AttributeError`, or emit deprecation warnings that look broken in a judge's run.

**Verified facts (HIGH, from PyPI metadata, qiskit-algorithms source and Qiskit docs):**
- `qiskit.algorithms` was split out to the standalone `qiskit-algorithms` package (Qiskit 0.44) and removed from Qiskit.
- `qiskit-algorithms` latest is **0.4.0 (2025-08-29)**. It requires `qiskit>=1.0` and Python >=3.9. It is **"no longer officially supported by IBM"** (community maintained). 0.4.0 **dropped V1 primitives** and supports only V2 (`StatevectorSampler`, `BackendSamplerV2`, Aer `SamplerV2`).
- Qiskit 2.0 removed the V1 primitive implementations. Current Qiskit is 2.5.x (Python >=3.10).
- `GroverOperator` (class) is deprecated as of Qiskit 2.1 and removed in 3.0. Use the function `qiskit.circuit.library.grover_operator`.
- `qiskit-ionq` latest is **1.1.1 (2026-06-05)**. It requires **`qiskit>=2.0.0`** and Python >=3.10. Any Qiskit 1.x environment needs an older `qiskit-ionq` (0.5/0.6 line).
- In Qiskit >1.3, `transpile()` defaults to `optimization_level=2`. IonQ docs recommend level 0 or 1 when targeting their QIS gateset.

**How to avoid:**
- Use **Iterative Amplitude Estimation** (`qiskit_algorithms.IterativeAmplitudeEstimation`). It needs no extra qubits, no controlled-Q, gives built-in confidence intervals and is well cited (Grinko et al. 2019). MLAE is the alternative.
- Pin versions in `requirements.txt` on hour 1 after discovering what Qollab has (Pitfall 9).
- Treat any AI-generated Qiskit snippet as V1-era until proven otherwise. Grep the repo for `qiskit.algorithms`, `from qiskit.primitives import Sampler`, `execute(`, `Aer.get_backend`, `GroverOperator(`.
- If `qiskit-algorithms` is not installable on Qollab, **vendor** `iae.py` or write a ~100-line IAE. Keep the Apache-2.0 header and NOTICE (Pitfall 12).

**Warning signs:** `ImportError: cannot import name 'Sampler'`, `DeprecationWarning: GroverOperator`, an AE result whose estimate only takes a handful of discrete values.

**Phase to address:** P0 (environment) and P3 (algorithm choice).

---

### Pitfall 4: State preparation A is not invertible, or depth explodes under Q^k

**What goes wrong:**
- The Grover operator is `Q = A S_0 A^dagger S_chi`, so Qiskit's `grover_operator(oracle, state_preparation=A)` calls `A.inverse()`. Any `measure`, `reset`, classical conditioning, or `initialize()` inside A makes inversion fail. `Initialize` is an Instruction containing a reset and cannot be inverted (HIGH, Qiskit docs). Use `StatePreparation` (a Gate) instead.
- A circuit for `Q^k A` contains **2k+1 copies of A**. If A has G two-qubit gates, IAE's late rounds (k = 8 to 30) produce circuits with tens to hundreds of thousands of gates. Quantum adders controlled on direction, boundary comparators and multi-controlled X gates on x-bits multiply G quickly. The S_0 reflection alone is one MCX across all roughly 20 qubits of A.
- The IonQ v0.3 job API documents **at most 7 controls per gate** and **150,000 gates total per multi-circuit job** (MEDIUM, API reference; the current v0.4 limits are unverified). A Q^k circuit can exceed this and be rejected with HTTP 400.

**Why it happens:**
The walk gets prototyped forward-only on a statevector, looks right, and A^dagger is only built when QAE is wired up in P3.

**How to avoid:**
- From the first line of P2, build A as a pure `QuantumCircuit` of unitary gates. Unit test `A.inverse()` and that `Operator(A).compose(Operator(A.inverse()))` is the identity (on a reduced-size spec).
- Track `A.size()`, `A.depth()` and the two-qubit gate count after `transpile(A, basis_gates=[...], optimization_level=1)` as a P2 metric. Set a budget, such as G at about 2,000 two-qubit gates, and a max k for IAE, and compute `(2k+1)*G` before submitting to IonQ.
- Transpile A once, build Q from the transpiled A and its inverse, and cache per k. Do not transpile the full Q^k from scratch at opt level 2/3 (this can take minutes).
- Keep the objective as **one** flag qubit. IAE's good-state counter assumes a single measured objective qubit (source comment: "one measured qubit only!").

**Warning signs:** `CircuitError: ... cannot be inverted` / `Initialize ... cannot be inverted`; transpile taking more than 60 s; IonQ 400/413 errors at high k.

**Phase to address:** P2 (invertibility, gate budget) and P3 (max-k cap and per-k caching).

---

### Pitfall 5: Quantum register arithmetic wraps around, so exits are miscounted

**What goes wrong:**
A 4-bit x register incremented past 15 wraps to 0 (adders are mod 2^n). A neutron leaving through the back face silently reappears at the front face. Likewise, y=0 minus 1 becomes 15, so side leakage reappears on the opposite side. Exited or absorbed particles that are not frozen keep walking in later steps and can re-enter.

**Why it happens:**
Reversible adders are modular by construction. Classical code uses `if x >= 16: exited = True; break`, but a circuit has no `break`.

**How to avoid:**
- Use an **(n+1)-bit** x register (a carry qubit) or a comparator computed *before* the move. Set `transmitted`, `leaked` or `reflected` flags reversibly.
- Hold an `alive` qubit and **control every subsequent step's move and collision on alive=1**, so dead particles are frozen. Absorption sets alive=0 and does not reset anything.
- For multi-cell flights in the x direction, the y at the exit point equals y before the flight (lattice directions), so the exit histogram stays well defined.
- Contract test: the exact `P(transmitted)` read from the statevector of A must equal the classical exact lattice solver to 1e-9. This single test catches wrap-around, missing freezes and wrong rotation angles.

**Warning signs:** transmission higher than physically plausible; nonzero probability at x=0 after many steps with no reflections modelled; probabilities summed over flags exceed 1 or do not sum to 1 with "still alive."

**Phase to address:** P2.

---

### Pitfall 6: Misrepresenting the 1/N claim (shots vs oracle queries, MSE vs RMSE, exact simulation)

**What goes wrong:**
- **Plotting against shots.** One shot of the circuit `Q^k A` costs 2k+1 applications of A. A classical history costs 1 application. Plotting QAE error against shots understates its cost by up to 2k+1 and fakes an extra speedup. In qiskit-algorithms IAE, `result.num_oracle_queries` accumulates `shots * k` (Q applications only, excluding the initial A; verified in source). That is a *different* N than "calls to A."
- **Exact probabilities.** Hand-rolled QAE that reads `Statevector.probabilities()` has zero sampling error, so the error curve drops to zero or machine precision. That is not a scaling result.
- **Mixing MSE and RMSE.** Classical MSE goes as 1/N and RMSE as 1/sqrt(N); QAE MSE goes as 1/N^2 and RMSE as 1/N. The Miao/Jin/Sone preprint states the result in MSE terms ("1/T^2 vs 1/N"). Mixing conventions on one plot produces wrong slopes.
- **Single-run curves.** One classical run's |p_hat - p| versus N is jagged, can hit 0 (a log-axis hole), and one lucky seed can look like any slope you want.
- **The "shot sweep in powers of two" framing does not fit IAE.** IAE chooses its own k schedule. You sweep `epsilon_target` (and fixed shots per round), not total shots.
- **Fitting slopes over too short a range.** The first IAE rounds use k=0 (plain sampling), so at small N QAE *is* classical. A 1.5-decade fit gives slopes like -0.7 that prove nothing.

**How to avoid:**
- Define cost N as **total applications of A (or A^dagger)**: classical N = histories; QAE N = sum over rounds of `shots_i * (2*k_i + 1)`. Compute it yourself from `result` fields; do not trust a single library counter's semantics. State the definition in the plot caption.
- Plot **RMSE over R independent repetitions** (R of at least 50) with 68% bands, versus N on log-log axes. Add reference lines with slopes -1/2 and -1. Fit slopes only over the regime where k > 0 dominates and report the fitted slope with uncertainty.
- Ground truth for both curves is `p_star` from the exact lattice solver (Pitfall 2).
- Seed everything: `numpy.random.default_rng(SeedSequence(...).spawn(R))` for classical; `StatevectorSampler(seed=...)` / Aer `seed_simulator` / IonQ job `seed` for quantum.

**Warning signs:** the QAE curve is suspiciously straight from N=1; QAE error is exactly 0 at some points; the y-axis says "error" without saying RMSE vs MSE vs CI half-width.

**Phase to address:** P3. Add a P4 docs review of plot captions.

---

### Pitfall 7: Running the full sweep through simulators that cannot handle it (laptop Aer at 24 qubits, or the shared IonQ queue)

**What goes wrong:**
- A 24-qubit statevector is 2^24 complex128 = 256 MB per state. Each gate touches every amplitude. A Q^k circuit with about 100k gates can take tens of minutes on a laptop. Multiply by (number of epsilons) x (R repetitions) x (IAE rounds) and the sweep never finishes inside 48 hours.
- On the IonQ simulator through Qollab, each IAE run is several jobs (one per round). 10 epsilons x 50 reps x about 6 rounds is about 3,000 jobs on a queue shared by every hackathon team. Queue delays in the final 12 hours are near certain.

**How to avoid:**
- For an *ideal* noiseless sampler, the outcome of a round depends only on θ (where a = sin²θ): `P(good | k) = sin^2((2k+1) θ)`. So:
  1. compute `a` once from the exact statevector of A (one simulation);
  2. **validate** against full-circuit sampling at a few k values (k = 0, 1, 2, ...) on Aer and once on the IonQ simulator;
  3. run the large repetition sweep with a thin custom `BaseSamplerV2` that returns binomial counts from that formula and plugs into the stock IAE.

  This is statistically identical to an ideal simulator. **Disclose it explicitly** in the docs ("analytic ideal-sampler emulation, validated against circuit simulation at k ≤ ..."). Hiding it is a technical-execution credibility risk.
- Use the IonQ simulator for a small set of representative IAE runs that prove it runs end to end, not for the sweep.
- Make sure the IonQ simulator is used with the **ideal** noise model. `ideal` is the API default (MEDIUM), but `noise_model="aria-1"` / `"forte-1"` examples are common in the docs, and noise destroys high-k rounds.
- Commit the sweep results (CSV) so plots regenerate in seconds.

**Warning signs:** a single Aer circuit takes more than 60 s; jobs sit in "queued" for more than 10 minutes; IAE confidence intervals blow up at high k on the cloud (noise) but not locally.

**Phase to address:** P3, with the IonQ round trip already proven in P0.

---

### Pitfall 8: Classical MC transport bugs that bias the baseline

**What goes wrong (each is a classic):**
- **Flying through a material interface with the old cross section.** Sampling `d = -ln(xi)/Sigma_t(W)` and moving 4 cm puts the neutron into steel without re-sampling. Correct options: stop at the interface and re-sample (memoryless property), or use delta tracking with a majorant.
- **Wrong mean free path:** using `ln(xi)` without the minus sign, or `-ln(xi)*Sigma` instead of dividing by Sigma.
- **`numpy` `rng.random()` returns values in [0,1).** `-log(u)` blows up at u=0. Use `-log1p(-u)` or `1-u`.
- **Collision-type sampling using the wrong material** (material looked up at the pre-flight position instead of the collision site).
- **Exit handling:** checking exit after the collision instead of before; counting side-face leakage as transmission; double-counting a particle that hits a corner.
- **Isotropic direction sampling done wrong:** in 3D, uniform in `mu` and not uniform in theta. In 2D, uniform angle in a plane is *not* the projection of 3D isotropic scattering. Choose and document one.
- **Pluggable random-bit source quantization.** If the "random-bit source" interface yields few bits per uniform (for example, 8 or 16), ξ is coarse, `-ln(xi)` has a truncated tail, and **deep-penetration (rare-event) transmission is biased**. Build uniforms from at least 53 bits, or make the interface `uniform()` rather than raw bits.
- **Unseeded or global-state RNG** (`np.random.seed` / `np.random.rand`): runs are not reproducible, and parallel repetitions may share streams. Use `Generator` with `SeedSequence.spawn`.
- **Standard error for a Bernoulli tally at small N:** p_hat = 0 gives SE = 0. Use RMSE over repetitions for plots and Wilson intervals for single-run CIs.

**How to avoid:**
Unit tests in P1 against analytic answers:
- (a) pure absorber, uncollided transmission `exp(-Sigma_t * L)` within 3 sigma;
- (b) two-layer pure absorber, `exp(-(Sigma_W*t_W + Sigma_SS*t_SS))`;
- (c) pure scatterer conserves particles (transmitted + reflected + leaked = 1);
- (d) lattice MC agrees with the exact lattice solver within 3 sigma.

**Warning signs:** two-layer pure-absorber test fails while the single-layer test passes (interface bug); results change between runs with the "same" seed.

**Phase to address:** P1.

---

### Pitfall 9: Qollab runnability: the project does not run for a logged-out judge

**What goes wrong (LOW-confidence specifics, because Qollab's runtime is undocumented publicly):**
- The Qollab browser runtime has a different Qiskit version and lacks `qiskit-algorithms`, `qiskit-aer` or `qiskit-ionq`, or forbids `pip install`.
- The notebook imports local modules that were never uploaded, or reads files with absolute paths (`/Users/hippolytedelloye/...`).
- The entry point runs the full sweep and takes 30 minutes, so the judge gives up or the kernel times out.
- The IonQ backend handle on Qollab is injected differently from `IonQProvider(token)`. Code that expects an env var or API key fails for anyone but the author.
- Publishing fails close to the deadline (platform load), or the published project is private, team-only or draft.
- The project lives under one person's Qollab account and teammates cannot edit or republish after the handoff.

**How to avoid:**
- **P0, hour 1:** create a throwaway Qollab project that prints `qiskit.__version__`, tries each import, builds a 2-qubit toy A (`ry` on 1 qubit), runs `IterativeAmplitudeEstimation` against the IonQ simulator, publishes it, and opens it in a private/incognito window logged out. This one test retires most of this pitfall.
- Provide a **"quick mode" entry point** (<2 minutes): small-K circuit, one IAE run on the IonQ simulator, plots regenerated from committed CSVs. Put a `RECOMPUTE = False` flag at the top.
- Use only relative paths. Keep source modules importable in the Qollab layout (or inline them if Qollab is single-notebook).
- Publish a working v0 by roughly hour 24 (partial submissions are eligible), then republish.
- Decide Qollab project ownership and team membership in P0.

**Warning signs:** "it works in my local Jupyter"; nobody has opened the published URL in an incognito window.

**Phase to address:** P0 (discovery), P4 (final logged-out verification).

---

### Pitfall 10: Overclaiming (advantage, novelty, physics)

**What goes wrong (each one costs credibility with technical judges):**
- **"Quantum advantage"** on a simulator. Wall-clock time is vastly worse than classical; the result is *query complexity* only. A small classical exact solver (Pitfall 2) solves the lattice problem deterministically in milliseconds. Judges who know transport will say so if you don't.
- **"Neutrons are quantum so qubits model them better."** Already excluded by PROJECT.md. Also check slides and video narration, not just the README.
- **"Quantum randomness."** Simulator bits are classical, and the rules exclude RNG-only projects. The pluggable random source in the classical engine must not be described as a quantum contribution.
- **"First ever" / "first quantum Monte Carlo particle transport."** This is **false**. Prior work found in this research:
  - **Olivier & Nowak (Thales), arXiv:2410.19489 (Oct 2024):** "Monte Carlo particle transport on quantum computers," discrete-time quantum walks plus amplitude amplification on a 2D grid.
  - **Lee, Lee & Kim, Phys. Rev. D 111, 116001 (2025)** (arXiv:2502.14374): quantum walk plus **QAE** for 10 MeV photon transport in water, reporting a quadratic speedup on the Qiskit simulator. This is the closest prior art and was **not** in PROJECT.md's literature check.
  - **Miao, Jin & Sone, arXiv:2607.10772 (2026):** QAE for fission yield and the U-238 resonance integral.

  The defensible claim narrows to: "to our knowledge, the first application of QAE to Monte Carlo *neutron* transport through a two-material fusion first-wall geometry." Cite all three and say what is different: neutrons, 14 MeV, a tokamak first wall, two materials, an honest lattice-exact baseline.
- **Ignoring the fault-tolerance caveat.** Babbush et al., PRX Quantum 2021 (arXiv:2011.04149), argue that quadratic speedups are unlikely to give practical advantage on early error-corrected machines. Citing it yourself in an "honest limitations" section *increases* the impact score.
- **Physics overclaim:** a one-group 14 MeV, isotropic-scattering model is not a SPARC wall-lifetime calculation. Call it "a SPARC-inspired two-layer first-wall benchmark."

**Phase to address:** P4 (docs), with novelty wording fixed in PROJECT.md now.

---

### Pitfall 11: Wrong or unsourced 14 MeV cross sections (and failing the "real dataset" theme criterion)

**What goes wrong:**
- Using thermal values (for example, W thermal capture of about 18 b) instead of 14 MeV values gives absurd absorption.
- At 14 MeV, true capture is tiny (millibarns). The "absorption" that matters is **non-elastic removal**: inelastic, (n,2n) and (n,p)/(n,α). Calling it "absorption" without defining it confuses judges with nuclear backgrounds.
- **Elastic scattering at 14 MeV on heavy nuclei is strongly forward-peaked.** Treating it as isotropic with the raw elastic cross section badly underestimates transmission. The standard one-group fix is the **transport-corrected cross section** `Sigma_tr = Sigma_t - mu_bar * Sigma_s` (MEDIUM, standard reactor physics; verify the `mu_bar` values from ENDF angular data or cite an approximate value).
- Using made-up round numbers: the Quantum Impact theme asks for "a real dataset and a measurable result" (event description). Unsourced sigmas read as a toy.
- Tungsten heavy alloy is not pure W (about 90-97 wt% W with Ni/Fe/Cu, about 17-18.5 g/cm^3). 316 SS is a Fe/Cr/Ni/Mo mix at about 7.95-8.0 g/cm^3. Number densities must be computed per constituent.

**How to avoid:**
- Pull 14 MeV point values from **ENDF/B-VIII.0** (NNDC Sigma or IAEA JANIS; or OpenMC's `openmc.data` if available) for W isotopes, Fe, Cr, Ni and Mo.
- Compute macroscopic sigmas in a small, committed `data/cross_sections.csv` with source URLs, densities and compositions.
- Sanity check: W mean free path should come out at about 3 cm, steel about 4.5-6 cm.
- Document the one-group definitions in a "Physics model and limitations" section.

**Phase to address:** P1.

---

### Pitfall 12: Compliance misses (attribution, disclosure, license mixing)

**What goes wrong:**
- The exact attribution line "This effort is supported by Qollab & IonQ." is missing or paraphrased.
- AI tools are not disclosed. Claude Code / GSD is being used to build this project, so it must be listed alongside Qiskit, qiskit-algorithms, qiskit-aer, qiskit-ionq, numpy, matplotlib and ENDF data.
- The MIT `LICENSE` file is missing from the repo **and** the Qollab project, or lists only one author.
- Vendored Apache-2.0 code (qiskit-algorithms `iae.py`, or a Qiskit snippet) is pasted into an MIT repo without its license header or NOTICE. Apache-2.0 is compatible with MIT distribution but **requires keeping the notice**.
- There is no demo video or repo link at submission time. Video recording and upload reliably take 1-2 hours more than planned.

**How to avoid:** add a P4 checklist item for each; create `LICENSE`, `ATTRIBUTION.md`/README sections and `THIRD_PARTY_NOTICES` in P0 so they exist from the first commit.

**Phase to address:** P0 (skeleton), P4 (final check).

---

### Pitfall 13: Handoff failure when the original author leaves mid-build

**What goes wrong:**
- Teammates clone the repo and cannot run it: unpinned versions, no setup instructions, the IonQ/Qollab credentials live only on Hippolyte's machine or account.
- Physics constants, qubit layout and the "why" of design decisions live in Hippolyte's head or chat history.
- Logic lives inside notebooks. `.ipynb` JSON produces unreadable diffs and merge conflicts as soon as two people edit; outputs bloat the repo.
- File names with spaces (`MonteCarlo Transport Problem.py` already exists) **cannot be imported as Python modules**.
- No test pins the classical-quantum agreement, so a teammate "optimizes" the circuit and silently breaks it.
- The GitHub remote is not set up (the repo currently has no remote) or teammates lack push rights at handoff time.
- There is no record of "what is verified vs what is next." Teammates re-do finished work or start the v2 UI on an unstable core.

**How to avoid:**
- Package layout from P0: `src/<pkg>/spec.py`, `classical/`, `quantum/`, `analysis/`; thin notebooks that only call functions; `nbstripout` or a "clear outputs before commit" rule. Delete or rename the placeholder files with spaces.
- `requirements.txt` with exact pins, a `make test` / `pytest` command, and a `README` "Run in 3 commands" section.
- **Contract tests that encode the design:**
  - `test_lattice_exact_matches_lattice_mc`
  - `test_circuit_amplitude_equals_exact_lattice` (1e-9, on a small spec)
  - `test_A_is_invertible`
  - `test_qubit_count_le_24`
- A `HANDOFF.md` (or the GSD STATE/pause-work artifacts) listing: the current `p_star` value, the qubit map table, which phases are verified, open decisions, and Qollab project ownership and access.
- Push to GitHub and add collaborators **before** the author goes offline. Credentials go through environment variables or Qollab's injected backend, never in code.

**Phase to address:** P0 (layout, remote, pins), continuously maintained, final pass in P4.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Analytic ideal-sampler emulation for the IAE repetition sweep | Sweep finishes in seconds instead of days | Judges may see it as "not really running circuits" if undisclosed | Acceptable **if** validated against full-circuit runs at small k and disclosed in the docs |
| x-only (1D) quantum geometry while classical stays 2D | Frees about 4 qubits for more collision events | Quantum histogram along the back face is no longer possible | Acceptable if the 2D histogram is clearly labelled classical-only and the scaling claim is stated for the 1D estimand |
| Truncating at K collisions | Fits 24 qubits | The estimand is not the full transmission | Acceptable, and standard (collision-order expansion), if `p_star(K)` and the truncation remainder are reported |
| Hard-coding cross sections inline | Saves 20 minutes | Numbers diverge between engines; no provenance | Never. Use a single spec plus CSV |
| Notebook-only code | Fast iteration | Merge conflicts, unimportable, untestable for teammates | Only for the final thin demo notebook |
| Vendoring IAE instead of depending on `qiskit-algorithms` | Removes a dependency risk on Qollab | Must maintain it plus keep the Apache notice | Acceptable if Qollab lacks the package |
| Skipping repetitions (single-run curves) | Faster plots | Slopes are noise; credibility hit | Never for the headline figure |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| qiskit-algorithms 0.4.0 | Passing a V1 `Sampler()`, or relying on its default | Pass an explicit V2 sampler: `StatevectorSampler(seed=..., default_shots=...)`, Aer `SamplerV2`, or `BackendSamplerV2(backend=ionq_backend)` |
| IAE result | Treating `num_oracle_queries` as the total calls to A | It accumulates `shots*k` (Q applications, excluding the initial A). Compute `sum(shots*(2k+1))` yourself and document it |
| qiskit-ionq 1.1.x | Installing alongside Qiskit 1.x | It requires `qiskit>=2.0`. Match versions to the Qollab runtime |
| IonQ simulator | Using a noisy model by accident; expecting per-shot memory | Use the `ideal` model (the default). The ideal simulator returns aggregate counts only (no `memory=True`) |
| IonQ gates | Large MCX gates and opt level 2/3 transpiles | At most 7 controls per gate (v0.3 API); `transpile(..., backend, optimization_level=1)` |
| IonQ job size | Submitting Q^k at high k | Precompute `(2k+1)*G` against the 150k-gate guidance and cap IAE's max k |
| IonQ measurement | Assuming partial or mid-circuit measurement works | Final measurements only; verify the counts keys map to the single objective qubit in the P0 toy run |
| Qiskit circuit library | `GroverOperator(...)` class | `grover_operator(oracle, state_preparation)` function (class deprecated in 2.1) |
| `initialize()` in A | Breaks `A.inverse()` | `StatePreparation` gate, or explicit RY trees |
| Credentials | API key in a notebook cell that gets published | Use env vars or the Qollab-provided handle; grep for `token=` before publishing |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Deep Q^k on a 24-qubit statevector | A single circuit takes minutes | Analytic emulation for sweeps; Aer fusion on; cap k | About 22+ qubits with more than 50k gates |
| Transpiling full Q^k at opt level 2/3 | `transpile` hangs | Transpile A once, compose, opt level 0/1 | More than 20k gates |
| Multi-controlled X across the whole register (S_0) | Two-qubit gate count explodes after decomposition | Let the backend or Aer handle `mcx` natively; ancilla-assisted decomposition if a qubit is spare | More than 7 controls on IonQ |
| Per-step `if` in pure-Python classical MC | 10^7 histories take hours | Vectorize over histories with numpy (track alive mask) | More than about 10^6 histories in pure Python |
| Shared IonQ queue in the final hours | Jobs pending for a long time | Do all cloud runs before hour 36; commit outputs | Last 12 hours of the event |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| IonQ/Qollab API key committed to the public GitHub repo or published notebook | Key abuse; account compute drained | `.env` plus `.gitignore`; `QISKIT_IONQ_API_TOKEN` env var; pre-publish grep |
| Publishing teammates' personal credentials in the handoff docs | Account compromise | Each teammate uses their own Qollab access; document *how* to get a key, never the key |

## UX Pitfalls (judge experience)

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Entry notebook runs for more than 5 minutes before the first output | Judge abandons it; the "runs without error" score suffers | Quick mode first; heavy recompute behind a flag |
| Headline plot without a definition of N and error | Judge cannot evaluate the claim | Caption: "N = calls to A; error = RMSE over R=... runs vs exact lattice value p* = ..." |
| Histograms "classical vs quantum" where the quantum one is plain sampling | Implies a speedup that does not exist for histograms | Label the quantum histogram "sampled from the encoded distribution (validation, no speedup)" |
| Jargon-only README | Fails the documentation criterion | One-paragraph plain-language "why fusion walls, why QAE," then the details |

## "Looks Done But Isn't" Checklist

- [ ] **Oracle A:** builds and simulates, but `A.inverse()` was never called. Verify `grover_operator(...)` constructs and the A·A^dagger identity test passes.
- [ ] **Quantum transmission value:** looks plausible, but was never compared to the exact lattice solver. Verify agreement to 1e-9.
- [ ] **Qubit count:** under 24 locally, but the IonQ transpile added ancillas. Verify `transpiled.num_qubits` on the IonQ backend target.
- [ ] **Error-vs-cost plot:** slopes look right, but the x-axis is shots. Verify the x-axis is A-calls including (2k+1).
- [ ] **Scaling sweep:** done, but the ground truth is the continuous classical MC. Verify both curves use the same `p_star`.
- [ ] **Classical engine:** passes the single-material test, but the interface is untested. Verify the two-layer pure-absorber analytic test.
- [ ] **IonQ run:** succeeded once from Hippolyte's account. Verify a logged-out incognito run of the published Qollab project.
- [ ] **Docs:** README exists, but check the exact attribution sentence, AI-tool disclosure, library list, `LICENSE` (MIT, all names), and Apache notices for vendored code.
- [ ] **Novelty section:** written, but check that Olivier & Nowak 2024, Lee et al. PRD 2025 and Miao et al. 2026 are cited and the claim is narrowed.
- [ ] **Handoff:** repo pushed, but check collaborators added, pins present, tests run with one command, HANDOFF notes current.
- [ ] **Demo video:** recorded, but check it is uploaded and linked in both the Qollab page and the README.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Qubit budget cannot fit the 2D multi-step walk (P1-1) | MEDIUM | Switch QAE to a 1D x-only slab or K=1-2 collision events; keep the 2D classical histogram; reframe the estimand as `T(<=K)` |
| Classical/quantum mismatch discovered late (P1-2) | LOW-MEDIUM | Build the exact lattice solver (about 1-2 hours); re-baseline both error curves against it |
| Qollab lacks `qiskit-algorithms` (P1-3/9) | LOW | Vendor `iae.py` with its Apache header, or a minimal custom IAE |
| IonQ rejects deep circuits (P1-4) | LOW | Cap IAE max k for the cloud run; demonstrate cloud execution at low k; do the sweep with validated emulation |
| Queue jammed near deadline (P1-7) | LOW if outputs are committed | Use committed results; state in the docs when and where cloud runs were done |
| Overclaim found in docs/video (P1-10) | LOW before submit, HIGH after | Grep docs for "advantage", "first", "quantum random"; re-record narration lines |
| Author leaves without handoff (P1-13) | HIGH | Prevent: push plus HANDOFF.md before leaving. Recovery: teammates rebuild context from `.planning/` and the tests |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Qubit budget omits per-step randomness | P2 (start), informed by P1 spec | Budget table in the repo; `A.num_qubits <= 24`; K chosen with numbers |
| 2. Apples-to-oranges comparison | P1 | Exact lattice solver exists; lattice MC within 3 sigma of it |
| 3. Canonical QAE / removed Qiskit APIs | P0, P3 | Grep shows no V1 imports; IAE used; pinned versions |
| 4. A not invertible / depth explosion | P2, P3 | Inverse test passes; gate-count metric logged per k |
| 5. Register wrap-around / unfrozen walkers | P2 | Contract test circuit vs exact lattice value to 1e-9 |
| 6. Misrepresented 1/N claim | P3 | Plot uses A-calls, RMSE over at least 50 runs, fitted slopes with uncertainty |
| 7. Simulator throughput/queue | P0 (round trip), P3 | Emulator validated vs circuit at small k; cloud runs done before hour 36 |
| 8. Classical transport bugs | P1 | Four analytic unit tests pass |
| 9. Qollab runnability | P0, P4 | Toy IAE published and run logged-out in hour 1-2; final incognito run |
| 10. Overclaiming | P4 (plus PROJECT.md now) | Prior-art citations present; claim wording reviewed |
| 11. Wrong/unsourced cross sections | P1 | `cross_sections.csv` with ENDF sources; MFP sanity check |
| 12. Compliance misses | P0, P4 | Checklist above fully ticked |
| 13. Handoff failure | P0, continuous, P4 | Fresh clone, one command, tests pass on a teammate's machine |

## Research Flags for the Roadmap

- **P2 needs a spike before full planning.** The qubit-budget and step-model decision (cell-walk vs delta-tracked flights, 2D vs 1D, K) drives everything downstream and is not settled by PROJECT.md's sketch.
- **P0 is mandatory and should come first,** even though it seems trivial. Qollab runtime facts are undocumented publicly (LOW confidence), and the whole submission depends on them.
- **P1 and P3 follow standard patterns** (analytic tests, IAE, RMSE sweeps). Unlikely to need extra research beyond this file.

## Sources

**HIGH confidence (primary: package metadata, source code, official docs)**
- qiskit-algorithms PyPI JSON: v0.4.0 (2025-08-29), `qiskit>=1.0`, IBM no longer officially supports it. https://pypi.org/project/qiskit-algorithms/
- qiskit-algorithms IAE source (V2 sampler calls, `num_oracle_queries += shots * k`, Q^k A construction, single-objective-qubit assumption): https://github.com/qiskit-community/qiskit-algorithms/blob/main/qiskit_algorithms/amplitude_estimators/iae.py
- qiskit-algorithms V2 migration PR: https://github.com/qiskit-community/qiskit-algorithms/pull/250
- qiskit-ionq PyPI JSON: v1.1.1 (2026-06-05), `qiskit>=2.0.0`, Python >=3.10; ideal simulator returns aggregate counts only. https://pypi.org/project/qiskit-ionq/
- qiskit-ionq README (noise_model usage, transpile caveats, token env vars): https://github.com/qiskit-community/qiskit-ionq
- Qiskit PyPI: current 2.5.2. https://pypi.org/project/qiskit/
- Qiskit 2.0 release notes, "Remove v1 primitive implementations": https://newreleases.io/project/github/Qiskit/qiskit/release/2.0.0rc1
- V2 primitives migration guide: https://quantum.cloud.ibm.com/docs/guides/v2-primitives
- GroverOperator deprecated in 2.1 in favour of `grover_operator`: https://quantum.cloud.ibm.com/docs/api/qiskit/qiskit.circuit.library.GroverOperator
- Initialize is non-invertible (contains reset); StatePreparation is invertible: https://quantum.cloud.ibm.com/docs/api/qiskit/qiskit.circuit.library.Initialize
- IonQ native gates / optimization-level guidance: https://docs.ionq.com/sdks/qiskit/native-gates-qiskit

**MEDIUM confidence (secondary or older API versions)**
- IonQ API v0.3 job limits (7 controls/gate, 150k gates per multi-circuit job, `ideal` default, seed field): https://docs.ionq.com/api-reference/v0.3/jobs/create-a-job.md
- IonQ simulator up to 29 qubits (Azure docs): https://learn.microsoft.com/en-us/azure/quantum/provider-ionq
- Hackathon facts (dates, MIT, Qollab publish, Quantum Impact requires "real dataset and measurable result"): https://quantumzeitgeist.com/ionq-quantum-hackathon-qollab-host/
- Prior art: Olivier & Nowak, "Monte Carlo particle transport on quantum computers," arXiv:2410.19489. https://arxiv.org/abs/2410.19489
- Prior art: Lee, Lee & Kim, "Quantum walk based Monte Carlo simulation for photon interaction cross sections," Phys. Rev. D 111, 116001 (2025), arXiv:2502.14374. https://arxiv.org/abs/2502.14374
- Prior art: Miao, Jin & Sone, arXiv:2607.10772 (QAE for fission yield and the U-238 resonance integral): https://papers.cool/arxiv/2607.10772
- Babbush et al., "Focus beyond quadratic speedups for error-corrected quantum advantage," PRX Quantum (2021), arXiv:2011.04149. https://arxiv.org/abs/2011.04149
- QAE theory (Brassard et al. 2002 error bound; Grinko et al. 2019 IAE; Suzuki et al. 2020 MLAE; Montanaro 2015): standard references, not re-fetched this session.
- Transport-corrected cross sections, forward-peaked 14 MeV elastic scattering, Woodcock delta tracking, approximate 14 MeV W/Fe cross sections: standard reactor-physics knowledge, to be verified against ENDF/B-VIII.0 in P1.

**LOW confidence (gaps)**
- Qollab runtime (Python/Qiskit versions, pip availability, IonQ backend injection, publish and logged-out behaviour, the 24-qubit cap): no public documentation found (qollab.xyz returned only a tagline). The P0 smoke test must establish these empirically.
- IonQ API v0.4 limits (current gate/size caps): not verified; v0.3 numbers used as guidance.

---
*Pitfalls research for: hybrid classical + quantum (QAE) Monte Carlo neutron transport, Qollab x IonQ hackathon*
*Researched: 2026-10-09*
