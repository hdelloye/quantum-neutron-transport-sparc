# Architecture Research

**Domain:** Hybrid classical + quantum Monte Carlo neutron transport (QAE estimate of slab transmission, Qiskit, IonQ simulator through Qollab)
**Researched:** 2026-10-09
**Confidence:** HIGH for the quantum-encoding structure and QAE wiring, because a prototype was built and checked against a statevector (Qiskit 2.5.2, qiskit-algorithms 0.4.0). MEDIUM for the physics fractions, which use placeholder cross sections. LOW for the Qollab runtime details, which are not publicly documented.

---

## 0. The Decision That Shapes Everything Else

**The 24-qubit "random walk" in PROJECT.md does not fit as currently sketched. There is a version that does, and it is described below.**

Turning a classical random walk into a unitary `A` (Montanaro 2015, "standard reversible-computation techniques") means every random choice the walk makes needs its own fresh qubits. Those qubits cannot be reset or reused, because QAE needs `A†`, and mid-circuit measurement or reset breaks unitarity. So the qubit cost scales with **(random bits per step) × (number of steps)**. The position register is a minor part of the bill.

| Encoding | Qubits | Verdict |
|---|---|---|
| Cell-by-cell lattice walk on 16×16 (8 position qubits, 2 direction qubits, status bits, plus 3–4 coin qubits per step; at least 16 steps to cross the slab) | 8 + 2 + 2 + 16×3 ≈ **60+** | **Does not fit.** |
| "Coined quantum walk" that reuses one coin register every step | ~12 | **Wrong physics.** Reusing the coin makes paths interfere, so the walk spreads ballistically instead of following classical Markov-chain statistics. The flag amplitude would not equal the MC transmission. |
| "Step-counter register" | 3–4 | **Unnecessary.** Steps are unrolled into circuit layers, so the step index is the layer position and does not need a register. |
| **Collision-event (first-collision) encoding, recommended, see §3** | **12** (pencil beam) / **16** (uniform source, 8 position qubits) | **Fits.** Built and verified exactly. |

The fix is to make one quantum "step" equal **one collision event**, not one grid cell. Local, per-ray probabilities are precomputed classically from the cross sections: the first-flight pmf per column, the scatter ratio per column, and the escape probability per (column, angle). Every MC code precomputes these. The circuit then coherently composes the joint distribution over histories, and QAE estimates its sum. At 14 MeV through about 2 mean free paths, uncollided plus single-scatter histories carry **about 90%** of the transmission. Truncating at K=1 collision captures most of the physics, and the truncation is explicit and reported. In shielding this quantity is the classic "uncollided + first-collision" component.

---

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│ L0  PROBLEM SPEC (single source of truth)                                 │
│   ProblemSpec: geometry 10×10 cm, 16×16 grid, W | 316SS boundary @ 2 cm,   │
│   one-group Σt/Σs/Σa per material, source (pencil | uniform-y),           │
│   angle bins, collision truncation K                                       │
└───────────────┬───────────────────────────────────────┬───────────────────┘
                │                                       │
┌───────────────▼─────────────────┐     ┌───────────────▼───────────────────┐
│ L1a CLASSICAL ENGINE            │     │ L1b SHARED DISCRETE MODEL          │
│ (continuous physics reference)  │     │ model/kernels.py                   │
│ vectorized delta-tracking MC    │     │  first-flight pmf  P(x1)  [17]     │
│ RandomSource injected           │     │  scatter ratio     c(x1)  [16]     │
│ tallies incl. collision order   │     │  escape table      Pesc(x1[,y],φ)  │
└───────────────┬─────────────────┘     └──┬─────────────┬──────────────┬────┘
                │                          │             │              │
                │               ┌──────────▼───┐ ┌───────▼──────┐ ┌─────▼──────────┐
                │               │ exact.py     │ │ discrete_mc  │ │ L2 QUANTUM     │
                │               │ p_K by exact │ │ classical MC │ │ encoding.py    │
                │               │ summation    │ │ on SAME      │ │ build_A()      │
                │               │ (ground truth)│ │ kernels      │ │ (UCRY, StatePrep)│
                │               └──────┬───────┘ └──────┬───────┘ └─────┬──────────┘
                │                      │                │               │
                │                      │                │      ┌────────▼─────────┐
                │                      │                │      │ L3 QAE LAYER     │
                │                      │                │      │ problem.py       │
                │                      │                │      │ ae.py (MLAE/IAE) │
                │                      │                │      │ runners.py       │
                │                      │                │      │  Analytic|SV/Aer │
                │                      │                │      │  |IonQ           │
                │                      │                │      └────────┬─────────┘
┌───────────────▼──────────────────────▼────────────────▼───────────────▼─────────┐
│ L4 EXPERIMENTS + ANALYSIS                                                        │
│ experiments/sweep.py → results/*.csv (tidy records)  →  analysis/plots.py        │
│ error-vs-N (oracle calls), slope fits, truncation bias, exit histograms          │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ L5 PUBLICATION                                                                   │
│ qollab/demo.py (self-contained, quick mode) · notebooks/demo.ipynb · README/docs │
│ committed results/ + figures/ so judges see output even if a live run is cut     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Arrows only point down or sideways.** Plotting never runs simulations. The quantum layer never imports the classical engine. The only coupling between the classical and quantum worlds is `model/kernels.py`, together with the ProblemSpec it is derived from.

### Component Responsibilities

| Component | Owns | Does not own | Typical implementation |
|---|---|---|---|
| `config.ProblemSpec` | All numbers: geometry, cross sections, grid, angle bins, K, source type, seeds | Any computation | frozen `@dataclass`, loaded from defaults or YAML/TOML, `to_dict()` for provenance in results |
| `physics/` | Material table, column-to-material map, optical depth τ(x), ray optical depth along an angle | Sampling | pure numpy functions |
| `classical/engine.py` | Continuous-physics MC: free flights, collisions, isotropic 2D scattering, boundary fates | Random bits (injected), plotting | vectorized struct-of-arrays, Woodcock delta tracking |
| `classical/rng.py` | `RandomSource` protocol plus the numpy adapter | Physics | `Protocol` with `uniform(n) -> ndarray` |
| `classical/tallies.py` | `TransportResult`: transmission, absorption, leakage per face, exit-y histogram, **collision-order histogram of transmitted particles**, batch statistics | | dataclass plus `np.bincount` |
| `model/kernels.py` | **The discrete model.** Turns ProblemSpec into probability tables | Circuits, sampling | numpy; deterministic |
| `model/exact.py` | Exact `p_K` and exact exit-y distribution by summing the kernels | | numpy sum, about 1 ms |
| `model/discrete_mc.py` | Classical MC that samples **the same** kernels. This is the apples-to-apples baseline for the QAE scaling plot | | `rng.choice` on the tables, vectorized |
| `quantum/encoding.py` | `build_A(kernels) -> (QuantumCircuit, RegisterMap)` | Estimation | Qiskit `StatePreparation`, `UCRYGate`, `mcx` |
| `quantum/problem.py` | `EstimationProblem` and Grover operator factory | | `qiskit_algorithms.EstimationProblem`, `qiskit.circuit.library.grover_operator` |
| `quantum/runners.py` | "Run `Q^k A` with s shots and return hits", for three backends | Estimation logic | `AnalyticRunner`, `StatevectorRunner`/`AerRunner`, `IonQRunner` (`BackendSamplerV2`) |
| `quantum/ae.py` | MLAE (exponential schedule) and IAE drivers; **oracle-call accounting** | Circuits | own MLAE (~60 lines) plus a wrapper over `qiskit_algorithms` IAE/MLAE |
| `quantum/sampling.py` | Direct sampling of `A` (k=0) to draw the quantum exit-position histogram | | measure registers, then classical post-processing |
| `experiments/` | Parameter sweeps and repetitions; writes tidy CSV/Parquet with provenance | Plot styling | loops over seeds; no globals |
| `analysis/` | RMSE, log-log slope fits, CIs, figures | Running simulations | pandas plus matplotlib, reads `results/` only |
| `qollab/` and `notebooks/` | Judge-facing entry points | Library logic (imports it or vendors a minimal copy) | one script, `--quick` default |

---

## 1. Classical Engine (L1a)

### Particle state: struct-of-arrays, population-vectorized

Do not write a per-particle Python loop. Hold the whole population as numpy arrays and advance **one event per iteration for every alive particle**:

```
x, y        float64[n]   position (cm)
ux, uy      float64[n]   direction cosines (2D, flatland-isotropic)
alive       bool[n]
n_coll      int16[n]     real-collision count (needed for the K-truncation comparison)
fate        int8[n]      0=alive 1=transmitted(back face) 2=absorbed 3=reflected(front) 4=leaked(lateral)
```

The loop ends when `alive.any()` is false. In practice this takes fewer than 30 iterations because absorption at 14 MeV ends histories quickly. For N = 2^20 histories this runs in about a second in numpy.

### Geometry and material lookup: Woodcock delta tracking

There are two materials, so use a **majorant cross section** `Σ_maj = max(Σt_W, Σt_SS)`. Sample flights with `Σ_maj`, then accept a real collision with probability `Σt(material(x)) / Σ_maj`. This removes all distance-to-boundary logic at the W|SS interface, which is the usual source of bugs in vectorized code, and the method is exact. Material lookup is `MAT_OF_COLUMN[np.clip((x/dx).astype(int), 0, 15)]` for grid tallies, or the exact rule `x < 2.0` for physics. Keep the physical boundary at **2.0 cm**, not at a column edge. 2 cm is 3.2 columns, and the kernels handle the mixed column exactly (see §3).

### Collision sampling

On a real collision: absorb with probability `Σa/Σt`; otherwise scatter isotropically in 2D (`φ ~ U[0, 2π)`). **Pick 2D-flatland isotropy and use it in both engines.** Mixing 3D-isotropic sampling into a 2D geometry would make the classical and quantum models disagree for reasons unrelated to the method.

### RNG injection

```python
class RandomSource(Protocol):
    def uniform(self, n: int) -> np.ndarray: ...   # float64 in [0,1)

@dataclass
class NumpySource:
    rng: np.random.Generator
    def uniform(self, n): return self.rng.random(n)

def transport(spec: ProblemSpec, n: int, source: RandomSource, *, max_collisions: int | None = None) -> TransportResult: ...
```

The engine **never** calls `np.random.*` globals and never seeds anything. Seeds live in `experiments/`. `max_collisions` lets the engine reproduce the truncated model for validation.

### Tallies

- Transmission, absorption and leakage fractions (front, lateral) with standard error `sqrt(p(1-p)/N)`.
- Exit-y histogram on the back face (16 bins matching the grid).
- **Collision-order tally for transmitted particles.** This one is load-bearing. It shows that ≤1-collision histories carry about 90% of transmission, which justifies K=1 in the quantum model.
- Running standard error versus N via batch means (powers of two).

**Measured with placeholder cross sections** (W: Σt = 1/3 cm⁻¹, Σs/Σt = 0.55; SS: Σt = 1/6 cm⁻¹, Σs/Σt = 0.5; pencil beam at mid-height). These are prototype numbers; the STACK/FEATURES researchers own the real values:

| Collisions before transmission | 2D isotropic, continuous | 4-direction lattice |
|---|---|---|
| 0 (uncollided, = e^{-τ}, τ = 2.0) | 0.136 (74% of T) | 0.134 (71%) |
| ≤1 | 0.168 (**91.5%**) | 0.170 (90%) |
| ≤2 | 0.178 (97%) | 0.182 (97%) |
| all | 0.183 | 0.188 |

---

## 2. Shared Discrete Model (L1b)

This layer is the main architectural idea. **A single kernel module feeds three consumers**, which guarantees that the classical baseline, the exact answer and the quantum circuit describe the same stochastic process:

```
ProblemSpec ──► kernels.py ──┬──► exact.py        p_K   (ground truth for error plots)
                             ├──► discrete_mc.py  p̂_N   (classical, 1/√N)
                             └──► encoding.py     A     (quantum, amplitude² = p_K)
```

Kernel tables for K=1, pencil beam at y₀:

| Table | Shape | Definition |
|---|---|---|
| `P_first[j]`, j = 0..15, plus `P_unc` | 17 | `exp(-τ(x_j)) − exp(-τ(x_{j+1}))`; `P_unc = exp(-τ(10 cm))` |
| `c[j]` | 16 | scatter ratio; collision-density-weighted average in the mixed W/SS column |
| `P_esc[j, b]` | 16 × N_φ | from the column center along the bin-center angle φ_b: 0 if cos φ ≤ 0 or the ray leaves laterally first, else `exp(-Δτ / cos φ)` |
| (Q1-Y) `P_esc[j, y, b]` | 16 × 16 × N_φ | same, with the lateral check depending on y |
| `exit_y_bin(j, [y,] b)` | table | deterministic exit row, used to post-process quantum samples into a histogram |

`p_K1 = P_unc + Σ_j P_first[j] · c[j] · mean_b P_esc[j,b]`. The prototype gives **0.16662**. The continuous engine's ≤1-collision tally gives 0.168; the gap is discretization error, and it should be reported.

**Validation chain:**
1. Engine against an analytic pure absorber: `T = e^{-τ}`.
2. Engine's uncollided tally against `P_unc`.
3. Engine's ≤1-collision tally against `exact.p_K1`, within discretization tolerance.
4. Statevector `P(T=1)` against `exact.p_K1` to 1e-12. Verified at diff = 1e-15.

---

## 3. Quantum Encoding (L2): Collision-Event State Preparation

### How `A` is built (Q1, pencil beam, verified)

```
x  (5q)  StatePreparation(√P_first[0..15], √P_unc at |16⟩)  → first-collision column, or |10000⟩ = uncollided-transmitted
a  (1q)  UCRY(2·asin√c[j]) controlled on x[0:4]              → 1 = scattered (0 = absorbed)
φ  (4q)  H⊗4                                                 → 16 isotropic angle bins (2D)
e  (1q)  UCRY(2·asin√P_esc[j,b]) controlled on x[0:4] + φ    → 1 = once-scattered neutron escapes through back face
T  (1q)  T = x[4]  ⊕  (¬x[4] ∧ a ∧ e)                        → CX(x4,T); X(x4); MCX(x4,a,e → T); X(x4)
```

Then `A|0⟩ = √(1−p)|ψ₀⟩|0⟩_T + √p|ψ₁⟩|1⟩_T`, with `p = p_K1`. The Grover operator is `Q = A S₀ A† S_χ`, with `S_χ = Z` on T, built by `grover_operator(oracle, state_preparation=A)`.

Notes:
- **Use `StatePreparation`, not `initialize`.** `Initialize` contains a reset, so it is not a unitary gate and cannot be inverted for `A†`.
- `UCRYGate` qubit order is `[target] + controls`, and the first control is the least significant bit of the angle index. Verified in the prototype. Lock it in with a unit test.
- Material dependence costs **no qubits**. It is baked into the angle tables, which are indexed by column bits.
- Exit position is **not** stored in a register. It is a deterministic function of the measured (x, [y], φ), so the quantum exit histogram is a classical post-process of A-samples (see §5).

### Qubit and gate budget

Q1 and Q1-Y measured after `transpile(basis=[cx, rz, ry, rx, h, x, sx], optimization_level=1)`; Q0 and Q2 are design estimates:

| Variant | Registers | **Qubits** | CX in A | CX in Q (Grover) | Physics captured | Status |
|---|---|---|---|---|---|---|
| **Q0** smoke test | x(5), flag = x[4] | **5** | ~26 (est.) | ~100 (est.) | uncollided only; `p = e^{-τ}` analytic | build first; validates the QAE pipeline against a closed form |
| **Q1** headline | x(5) a(1) φ(4) e(1) T(1) | **12** | **313** | **1,188** | uncollided + single scatter, ~90% of T | **recommended**, verified exact (diff 1e-15) |
| **Q1-Y** (literal 16×16, 8 position qubits) | x(5) y₀(4, H⊗4 uniform source) a(1) φ(4) e(1) T(1) | **16** | **4,153** | **9,492** | same, uniform-y source, lateral leakage depends on y | verified exact; use if the "8 position qubits" story matters for judging |
| **Q2** stretch, K=2 | x(5) a₁(1) φ₁(3) t₁(5) a₂(1) φ₂(3) e₂(1) T(1) | **20** | ~25k (est.) | ~52k (est.) | ≤2 collisions, ~97% of T | local-only; needs the analytic runner; too deep for IonQ |
| Naive per-cell walk | x(4) y(4) d(2) status(2) + 16 steps × 3 coins | ~60 | n/a | n/a | n/a | **does not fit** |

QAE adds **zero** qubits when using IAE or MLAE, since neither uses phase estimation. The "remaining qubits for QAE phase estimation" in PROJECT.md should be dropped; canonical QPE-based QAE is the wrong choice here.

Where the gate cost comes from: a `UCRY` with n controls costs 2ⁿ CX. The escape multiplexer dominates (8 controls in Q1, 12 in Q1-Y). That exponent, not qubits, is the first thing that breaks as the model grows.

Runtime (Qiskit `Statevector`, Q1, 12 qubits, one laptop core): k=16 → 19k CX, 1.3 s; k=64 → 76k CX, 5.4 s. Exact match to `sin²((2k+1)θ)` **only when the full logical circuit `Q^k A` is transpiled once** (see Anti-Pattern 4).

---

## 4. QAE Layer (L3)

### Components

```python
problem = EstimationProblem(state_preparation=A, objective_qubits=[T])  # Q is built for you

class GroverPowerRunner(Protocol):
    def run(self, k: int, shots: int) -> int: ...      # number of T=1 outcomes for Q^k A

AnalyticRunner(theta)      # Binomial(shots, sin²((2k+1)θ)), with θ from ONE statevector of A
StatevectorRunner / Aer    # builds Q^k A logically, transpiles once, samples
IonQRunner                 # qiskit-ionq backend "simulator" via BackendSamplerV2 + preset pass manager
```

### IAE vs MLAE: use both, for different jobs

| | **MLAE, exponential schedule** (Suzuki et al. 2020) | **IAE** (Grinko et al. 2021) |
|---|---|---|
| Role | **Headline error-vs-N sweep** | Single "official" estimate with a confidence interval (demo, IonQ run) |
| Schedule | fixed: m = 0, 1, 2, 4, …, 2^(M−1), N_shot per level | adaptive (FindNextK) |
| Why | deterministic cost per run makes a clean x-axis; the paper's own error-vs-N_q figure uses exactly this setup (slope ≈ −0.95 vs −0.50 classical) | rigorous ε/α guarantee; standard in Qiskit |
| Implementation | own ~60-line driver over `GroverPowerRunner` (grid search plus refine of the log-likelihood) | `qiskit_algorithms.IterativeAmplitudeEstimation(epsilon_target, alpha, sampler=...)` |

Verified on Q1 with `StatevectorSampler(default_shots=100)`: IAE (ε = 0.005, α = 0.05) gave 0.16628 against exact 0.16662, powers [0, 0, 0, 2, 8, 38], CI [0.1649, 0.1676]. MLAE (schedule 5) gave 0.16554.

### Oracle-call accounting (critical for honesty)

The x-axis of the scaling plot must be **applications of A** (A and A† each count 1):

```
N_A = Σ_rounds shots_r · (2·k_r + 1)        (Suzuki eq. 11)
classical: N = number of histories          (one history ≈ one A)
```

**`qiskit_algorithms` reports `num_oracle_queries = Σ shots·k`.** It counts Grover applications only, and k=0 rounds count as zero. The prototype reported 4,800 for IAE, while the true `N_A` is 4,800·2 + 600 = 10,200. Always compute `N_A` yourself from the (k, shots) log. Plotting against Qiskit's counter would overstate the quantum advantage by about 2× and would be caught by an informed judge.

**Shots ≠ oracle calls.** A shot at power k costs 2k+1 A-applications. "Powers-of-two shots for both methods" from PROJECT.md should become: classical N = 2^j histories; QAE points at their actual `N_A`, chosen by (M, N_shot) to span the same 10²–10⁶ range.

### Making the sweep feasible: the analytic runner

The error-vs-N curve needs RMSE over R ≈ 200–1000 independent repetitions per point. With a deep `Q^k A` that is impossible on a shared cloud simulator and slow even locally. Because `A` is verified to give `P(T) = sin²θ` exactly, an ideal noiseless sampler is **statistically identical** to `Binomial(shots, sin²((2k+1)θ))`. Two reasons this is defensible:
1. Suzuki et al. generate their error-vs-queries figure this way ("Bernoulli sampling with probability sin²((2m_k+1)θ_a)").
2. IonQ's ideal simulator itself "runs a single calculation to produce output probabilities rather than simulating each shot".

Requirement: cross-validate the analytic runner against the statevector/Aer runner at 3–5 points, and against IonQ at 1–2 low-k points. Show the overlay in the docs and disclose the method in the README.

### IonQ wiring

`qiskit-ionq ≥ 1.0` supports Qiskit 2.x (IonQ API v0.4). Use `IonQProvider().get_backend("simulator")`, `BackendSamplerV2(backend=...)`, and pass `transpiler=generate_preset_pass_manager(optimization_level=1, backend=...)` to IAE. IonQ recommends optimization level 0–1. The ideal simulator allows up to 29 qubits, but **no documented gate or size limit was found**. Keep IonQ circuits to k ≤ 8 (Q1 ≈ 10k CX; Q1-Y ≈ 80k CX) and smoke-test circuit size early.

---

## 5. Comparison and Analysis Layer (L4)

**Tidy record schema** (one row per estimate), written by `experiments/` and read by `analysis/`:

```
method ∈ {classical_cont, classical_discrete, qae_mlae, qae_iae, exact}
model ∈ {Q0, Q1, Q1Y, Q2}   backend ∈ {numpy, analytic, statevector, aer, ionq}
N_cost (histories or N_A)   estimate   truth (exact p_K)   seed   schedule/k-log   spec_hash   git_sha   timestamp
```

Figures:
1. **Error vs N (headline).** RMSE against `p_K` for `classical_discrete` and `qae_mlae` on the same axes, log-log. Overlay the reference lines `√(p(1−p)/N)` and the Cramér–Rao `√(p(1−p))/N`, plus fitted slopes (expect about −0.5 and about −0.9 to −1.0). Plot a few IAE points with their CIs. Mark the analytic-runner points that were checked on Aer/IonQ.
2. **Truncation bias.** Classical continuous T (all orders) against `p_K1` (and `p_K2`), with the collision-order bars. This is the honest statement of what the circuit computes.
3. **Exit-y histograms.** (a) classical continuous, filtered to ≤1 collision via `n_coll`; (b) quantum, from k=0 samples of A post-processed with `exit_y_bin`; (c) exact from kernels. All at matched N. Both sampling methods are 1/√N here; this figure shows agreement, not speedup.
4. (Optional) wall-clock table. Classical wins on wall time at this toy scale, and saying so up front is a credibility point.

---

## 6. Publication Layer (L5)

- `qollab/demo.py`: **one self-contained entry point** with a `--quick` default that finishes in under about 60 s: build Q1, check exact against statevector, run one IAE estimate on the available backend, plot the committed sweep results, and draw a small live sweep with the analytic runner. Backend auto-selection: IonQ if credentials or platform are present, otherwise local.
- Dependencies limited to `qiskit`, `numpy`, `matplotlib`, and optionally `qiskit-ionq` and `qiskit-algorithms`. **Vendor the MLAE driver** so the demo still works if `qiskit-algorithms` (no longer IBM-supported, last release 0.4.0 on 2025-08-29) is not installable on Qollab.
- `results/` and `figures/` are committed, so the judging artifact does not depend on a live 48-hour-old queue.
- README sections map to the four judging criteria. Include the attribution line, library and AI disclosure, MIT license and replication commands.
- **The Qollab runtime is unknown.** All that is public is "run real quantum code in their browser through our playground", with no package list, timeout or credential model. This is the highest platform risk; see build order.

---

## Recommended Project Structure

```
sparc-qae-transport/
├── pyproject.toml              # pip install -e . ; pins qiskit>=2.x, numpy, matplotlib; extras [ionq], [algos], [aer]
├── LICENSE                     # MIT
├── README.md                   # judging-criteria map, attribution, disclosure, replication
├── src/qtransport/
│   ├── config.py               # ProblemSpec (frozen dataclass) + DEFAULT_SPEC + spec_hash()
│   ├── physics/
│   │   ├── materials.py        # one-group Σt/Σs/Σa for W-HA and 316SS + citations
│   │   └── geometry.py         # slab, column→material, tau(x), ray optical depth
│   ├── classical/
│   │   ├── rng.py              # RandomSource protocol, NumpySource
│   │   ├── engine.py           # vectorized delta-tracking transport()
│   │   └── tallies.py          # TransportResult, histograms, collision-order tally
│   ├── model/                  # ★ shared discrete model — the contract between worlds
│   │   ├── kernels.py          # Kernels dataclass: P_first, P_unc, c, P_esc, exit_y_bin
│   │   ├── exact.py            # p_K, exact exit distribution
│   │   └── discrete_mc.py      # classical MC on the kernels
│   ├── quantum/
│   │   ├── encoding.py         # build_A(kernels, variant) -> (circuit, RegisterMap)
│   │   ├── problem.py          # EstimationProblem + Grover operator
│   │   ├── runners.py          # Analytic / Statevector / Aer / IonQ runners
│   │   ├── ae.py               # MLAE (own), IAE wrapper, N_A accounting
│   │   └── sampling.py         # k=0 sampling → exit histogram
│   ├── experiments/
│   │   ├── sweep.py            # error-vs-N sweeps → results/*.csv
│   │   └── histograms.py
│   └── analysis/
│       ├── stats.py            # RMSE, slope fits
│       └── plots.py            # figures from results only
├── scripts/                    # thin CLIs: run_classical, run_quantum, run_sweep, make_figures
├── qollab/demo.py              # judge entry point (quick mode)
├── notebooks/demo.ipynb        # narrative walkthrough (mirrors demo.py)
├── results/                    # committed CSV outputs
├── figures/                    # committed PNG/SVG
├── tests/                      # analytic checks, kernel/exact/statevector equality, runner cross-checks
└── docs/                       # physics.md, encoding.md (qubit table), methodology.md (N_A, analytic runner)
```

### Structure Rationale

- **`model/` sits between `classical/` and `quantum/`.** It is the only shared contract. Teammates can work on the classical engine or the circuits independently once `Kernels` is frozen.
- **`classical/` does not import `model/`, and `quantum/` does not import `classical/`.** The validation that ties them together lives in `tests/` and `experiments/`, so a bug in one world cannot silently "fix" the other.
- **`analysis/` reads files only.** Figures can be regenerated in seconds, and the Qollab demo can show committed results.
- **`src/` layout plus `pip install -e .`** prevents notebook path hacks, which break on handoff.

---

## Architectural Patterns

### Pattern 1: Single Discrete Model, Three Consumers
**What:** Precompute local transition kernels once. The exact solver, classical discrete MC and quantum circuit all consume them.
**When:** Any QAE demo that claims "quantum vs classical on the same problem".
**Trade-offs:** Requires discretization (angle bins, cell centers) and truncation, which introduces bias against continuous physics. It makes the scaling comparison exact and lets the bias be reported separately.

### Pattern 2: Collision-Event Unrolling with Multiplexed Rotations
**What:** One circuit stage per collision event. Each random choice is a fresh register prepared by `StatePreparation` or `UCRYGate`, with angles from the kernels and controls on the earlier history registers.
**When:** Turning a short-horizon Markov process into `A`.
**Trade-offs:** Qubits grow linearly in K (about 8–15 per event); CX grows as 2^(controls). Fine for K ≤ 1 on IonQ and K = 2 locally.

```python
def build_A(k: Kernels) -> tuple[QuantumCircuit, RegisterMap]:
    qc = QuantumCircuit(12, name="A")
    X, A_, PH, E, T = [0,1,2,3,4], 5, [6,7,8,9], 10, 11
    qc.append(StatePreparation(k.first_flight_amplitudes()), X)          # 17 outcomes in 5 qubits
    qc.append(UCRYGate(list(2*np.arcsin(np.sqrt(k.c)))), [A_] + X[:4])
    qc.h(PH)
    ang = [2*np.arcsin(np.sqrt(k.P_esc[j, b])) for b in range(16) for j in range(16)]  # index j + 16*b
    qc.append(UCRYGate(ang), [E] + X[:4] + PH)
    qc.cx(X[4], T); qc.x(X[4]); qc.mcx([X[4], A_, E], T); qc.x(X[4])
    return qc, RegisterMap(x=X, a=A_, phi=PH, e=E, flag=T)
```

### Pattern 3: Runner Abstraction for Grover Powers
**What:** Estimation algorithms only call `run(k, shots) -> hits`. Backends are swappable.
**When:** Always. It lets one MLAE implementation drive the analytic, statevector, Aer and IonQ backends, and makes cross-validation a loop.
**Trade-offs:** The IAE wrapper over `qiskit_algorithms` bypasses it (that code talks to a Sampler directly). Accept this for the single-estimate demo.

### Pattern 4: Population-Vectorized Delta Tracking
**What:** Struct-of-arrays particles, one event per iteration, majorant flights, rejection for virtual collisions.
**When:** Classical engine with a heterogeneous medium in numpy.
**Trade-offs:** Wastes some samples on virtual collisions (Σ_maj/Σt_SS = 2 in steel), which is negligible. Removes all interface-crossing code.

---

## Data Flow

### Main pipeline

```
ProblemSpec ─┬─► physics ─► classical.engine(spec, N, RandomSource) ─► TransportResult ──────────┐
             │                                                                                    │
             └─► model.kernels(spec) ─┬─► model.exact ─► p_K (truth) ───────────────────────────┤
                                      ├─► model.discrete_mc(N, RandomSource) ─► p̂_classical ─────┤
                                      └─► quantum.encoding ─► A ─► problem(A, T) ─► Q             │
                                                                     │                            │
                                         runners (analytic|sv|aer|ionq) ◄── ae.MLAE / ae.IAE      │
                                                                     └─► p̂_quantum, N_A log ─────┤
                                                                                                  ▼
                                                     experiments ─► results/*.csv ─► analysis ─► figures/
                                                                                                  ▼
                                                                            README / qollab/demo.py
```

### Key data flows

1. **Truth flow:** `spec → kernels → exact.p_K`. Every error metric is computed against this one number, never against another estimator.
2. **Quantum estimation flow:** `kernels → A → (k, shots) schedule → hits → likelihood → p̂, N_A`. N_A is logged per run.
3. **Validation flow:** engine `n_coll ≤ K` tally ↔ `exact.p_K` ↔ statevector `P(T)`. Run as tests, not in the demo path.
4. **Histogram flow:** k=0 samples of A → measured (x, [y], φ, a, e) → `kernels.exit_y_bin` → histogram. Compared with the engine's ≤K-collision exit tally and the exact kernel distribution.

---

## Suggested Build Order

| # | Build | Depends on | Exit criterion | Parallelizable? |
|---|---|---|---|---|
| 1 | `config`, `physics`, `classical/` engine + tallies + tests; **IonQ/Qollab smoke test** (2-qubit Bell circuit through the real platform) | none | pure-absorber `e^{-τ}` within 3σ; collision-order tally; a job completes on the IonQ simulator from Qollab | engine work and platform smoke test in parallel |
| 2 | `model/kernels`, `exact`, `discrete_mc` | 1 (physics) | engine ≤1-collision tally ≈ `p_K1`; discrete MC → `p_K1` | can start once physics exists |
| 3 | `quantum/encoding`: **Q0, then Q1** (Q1-Y optional) | 2 (kernels interface) | statevector `P(T) == p_K` to 1e-12; `Q^k A` matches `sin²((2k+1)θ)` for k ≤ 16 | yes, against stub kernels while 2 finishes |
| 4 | `quantum/problem`, `runners`, `ae` (MLAE own + IAE wrapper), N_A accounting | 3 | IAE CI covers `p_K` on statevector; analytic ≡ statevector runner at 3–5 points | |
| 5 | `experiments` + `analysis`: sweeps, slope fits, histograms; IonQ estimate at low k | 4, and 1 for the classical side | headline figure with slopes ≈ −0.5 vs ≈ −1; one IonQ IAE estimate agrees with `p_K` | analysis code can be written against fake CSVs early |
| 6 | Publication: `qollab/demo.py`, notebook, README, docs, license | 5 | logged-out Qollab run succeeds in quick mode | docs can start at phase 1 |
| 7 (stretch) | Q2 (K=2) local-only, or per-bin QAE of the exit histogram | 4 | statevector exactness at 20 qubits | |

**Why this order:**
- The kernels interface is the hinge, so freeze its dataclass early.
- Q0 debugs the whole QAE stack against a closed form before any physics-heavy circuit exists.
- The Qollab/IonQ smoke test goes in phase 1 because that platform is the least-documented dependency, and it cannot be fixed at hour 46.

---

## Scaling Considerations (problem size, not users)

| Scale | What changes |
|---|---|
| Q1 (K=1, 16 angle bins, pencil) | 12 qubits, ~1.2k CX per Grover iteration; everything runs anywhere, including IonQ at k ≤ 8 |
| Q1-Y / 32 angle bins | 16–17 qubits; escape multiplexer 2^12–2^13 CX; IonQ k ≤ 2–4; local fine |
| K = 2 | ~20 qubits, ~50k CX per Grover iteration; local statevector of A only, analytic runner for sweeps |
| K ≥ 3 or 3D or multigroup | exceeds 24 qubits; would need arithmetic-based (QROM/adder) flight sampling rather than multiplexers. Out of scope. |

### Scaling priorities
1. **First bottleneck: CX count from multiplexer controls (2ⁿ).** Mitigate by keeping the escape table's controls ≤ 8–12, using fewer angle bins, or exploiting symmetry (P_esc = 0 for cos φ ≤ 0, so only half the bins need controls).
2. **Second bottleneck: per-event qubits.** That is the K limit; see the table in §3.

---

## Anti-Patterns

### Anti-Pattern 1: Coin-reusing quantum walk as a Monte Carlo
**What people do:** Build a coined quantum walk (position register plus one coin register reused every step) and read the exit amplitude.
**Why it's wrong:** It is unitary interference dynamics, not a classical Markov chain. Its "transmission" is not the MC transmission and won't match the classical baseline.
**Do this instead:** Use fresh randomness registers per event (Pattern 2), and treat classical MC statistics as the specification.

### Anti-Pattern 2: Comparing QAE to a classical MC of a different model
**What people do:** Plot QAE error against the classical continuous engine's error, each relative to its own reference.
**Why it's wrong:** The curves would partly reflect discretization and truncation differences, not sampling complexity.
**Do this instead:** Use the same `p_K` truth for `discrete_mc` and QAE; report truncation bias in a separate figure.

### Anti-Pattern 3: Counting shots (or Qiskit's `num_oracle_queries`) as cost
**What people do:** Use the x-axis "shots" or the library counter.
**Why it's wrong:** A shot at power k costs 2k+1 A-applications; Qiskit counts Σ shots·k. Either way the advantage is overstated.
**Do this instead:** Log (k, shots) per round and compute `N_A = Σ shots(2k+1)`.

### Anti-Pattern 4: Transpiling A and Q separately, then stitching
**What people do:** `tA = transpile(A)`, `tQ = transpile(Q)`, then compose `tQ` k times for speed.
**Why it's wrong:** Observed in the prototype. Even at `optimization_level=0` the stitched circuit was wrong (k=1: 0.865 vs 0.907 correct). The transpiler assumes each standalone circuit starts in |0…0⟩ and exploits that, likely by using idle qubits as clean ancillas when synthesizing the multi-controlled reflection. That assumption is false mid-circuit.
**Do this instead:** Compose the logical `Q^k A`, then transpile once (k=64 in 0.6 s), or let `qiskit_algorithms` do it via its `transpiler` argument. Add a test that checks `sin²((2k+1)θ)` at k = 1, 16.

### Anti-Pattern 5: Using `initialize()` inside A
**What people do:** Use `qc.initialize(amps)` for the first-flight distribution.
**Why it's wrong:** It contains a reset, so it is not invertible and the Grover operator can't be built.
**Do this instead:** Use `StatePreparation(amps)`.

### Anti-Pattern 6: Precomputing p and encoding it in one rotation
**What people do:** Compute the transmission classically and apply `Ry(2·asin√p)`.
**Why it's wrong:** The quantum part becomes trivial, and judges will see it.
**Do this instead:** Precompute only **local** kernels (per cell and per ray). The circuit composes the joint history distribution; the sum over histories happens in amplitude. State openly that at 16×16 the exact sum is also classically cheap, and that the claim is about sample complexity as the history space grows ((cells × angles)^K).

---

## Integration Points

### External services

| Service | Integration pattern | Notes |
|---|---|---|
| IonQ cloud simulator | `qiskit-ionq ≥ 1.0` → `IonQProvider().get_backend("simulator")` → `BackendSamplerV2` | Ideal simulator samples exact probabilities and allows ≤ 29 qubits; no published gate limit was found, so smoke-test large circuits; use optimization level 0–1 |
| Qollab playground | unknown runtime (browser "playground") | Verify early: Python version, installable packages, IonQ credential injection, timeout. Keep the demo dependency-light |
| `qiskit-algorithms` 0.4.0 | `EstimationProblem`, `IterativeAmplitudeEstimation(sampler=BaseSamplerV2, transpiler=...)` | Works with Qiskit 2.5.2 (verified). No longer officially supported by IBM, so vendor MLAE as a fallback |
| Qiskit Aer (optional) | `AerSimulator(method="statevector")` | Faster than `Statevector` for Q1-Y/Q2 spot checks; not required for Q1 |

### Internal boundaries

| Boundary | Communication | Notes |
|---|---|---|
| `classical` ↔ `model` | none (both read `ProblemSpec`) | coupled only in tests |
| `model` → `quantum` | `Kernels` dataclass (numpy arrays) | freeze early; teammate handoff contract |
| `quantum.ae` → `quantum.runners` | `run(k, shots) -> int` | the only backend-specific seam |
| `experiments` → `analysis` | files in `results/` (CSV with spec_hash, git_sha) | no in-memory coupling |
| library → `qollab/demo.py` | import, or a vendored minimal copy | demo must survive missing optional deps |

---

## Sources

- Suzuki et al., "Amplitude estimation without phase estimation", *Quantum Inf. Process.* 19, 75 (2020), arXiv:1904.10246. Read in full. Sources for: N_q = Σ N_k(2m_k+1), LIS/EIS schedules, Bernoulli-sampled error-vs-queries methodology, slopes −0.95 (EIS) vs −0.50 (classical). **HIGH**
- Grinko, Gacon, Zoufal, Woerner, "Iterative Quantum Amplitude Estimation", *npj Quantum Inf.* 7, 52 (2021), arXiv:1912.05559. No QPE, O(1/ε) oracle calls up to a log-log factor. **HIGH**
- Montanaro, "Quantum speedup of Monte Carlo methods", *Proc. R. Soc. A* 471 (2015), arXiv:1504.06987. A randomized algorithm becomes unitary A via reversible computation. **HIGH**
- qiskit-algorithms GitHub and PyPI: 0.4.0 (2025-08-29) adds PrimitivesV2 and Qiskit 2.x support; "no longer officially supported by IBM". IAE signature `IterativeAmplitudeEstimation(epsilon_target, alpha, confint_method, min_ratio, sampler: BaseSamplerV2, *, transpiler, transpiler_options)`. https://github.com/qiskit-community/qiskit-algorithms, https://qiskit-community.github.io/qiskit-algorithms/stubs/qiskit_algorithms.IterativeAmplitudeEstimation.html **HIGH**
- Qiskit `grover_operator` docs (zero-reflection synthesis depends on available scratch qubits; `reflection_qubits` parameter). https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.grover_operator **HIGH**
- IonQ Qiskit guide (qiskit-ionq ≥ 1.0 supports Qiskit 2.0; backend "simulator"; optimization level 0–1). https://docs.ionq.com/guides/sdks/qiskit **HIGH**
- IonQ noise-model and simulator guide (ideal simulator ≤ 29 qubits; computes probabilities once rather than per shot). https://docs.ionq.com/guides/simulation-with-noise-models **HIGH**
- IonQ × Qollab announcement (browser "playground", share/fork/remix; no runtime specifics). https://www.ionq.com/news/ionq-partners-with-qollabs-creative-challenge-advancing-creative-quantum-innovation **LOW** for runtime details
- Carrera Vazquez and Woerner, "Efficient State Preparation for Quantum Amplitude Estimation", arXiv:2005.07711. State preparation is the bottleneck. **MEDIUM**
- **Prototype measurements (this research, 2026-10-09):** Qiskit 2.5.2 + qiskit-algorithms 0.4.0 on local Python 3.14 venv. Q1: 12 qubits, A = 313 CX, Q = 1,188 CX, statevector P(T) = p_K1 to 1e-15; Q1-Y: 16 qubits, A = 4,153 CX, Q = 9,492 CX, exact match; IAE/MLAE run end-to-end; `num_oracle_queries` = Σ shots·k observed; stitching separately transpiled A/Q gives wrong amplitudes. **HIGH** for structure; physics fractions use placeholder cross sections (**MEDIUM**).
- Woodcock delta tracking (Woodcock et al. 1965; used in Serpent). Standard method, from domain knowledge, not re-verified this session. **MEDIUM**

---
*Architecture research for: hybrid classical + QAE Monte Carlo neutron transport (SPARC first wall)*
*Researched: 2026-10-09*
