# Phase 3: Classical Baseline - Research

**Researched:** 2026-10-10
**Domain:** Vectorized numpy Monte Carlo transport (Woodcock delta tracking), discrete sampling of a frozen probability-table contract, injected random sources
**Confidence:** HIGH. Every number below was measured this session with working prototypes run against the repo's frozen `neutron_qae` modules.

<user_constraints>
## User Constraints (no CONTEXT.md; ROADMAP Phase 3, PROJECT.md Key Decisions and the frozen Phase 2 contract act as the user's decisions)

### Locked Decisions
- **ROADMAP Phase 3 goal (verbatim):** "An honest classical baseline exists: a continuous delta-tracking Monte Carlo serves as the physics reference, and a discrete lattice Monte Carlo samples exactly the `Kernels` model the circuit encodes; both are validated against analytic and exact answers and both are driven by an injected random source."
- **Success criteria (verbatim):**
  1. A seeded, vectorized continuous MC run (Woodcock delta tracking, isotropic scattering, loss on exit through any face) reports transmission fraction, absorption fraction, back-face exit-position histogram and collision-order breakdown, each with a standard error.
  2. The continuous MC's uncollided transmission matches e^{-τ} within its standard error, and two runs with the same seed reproduce identical histories.
  3. The discrete lattice MC (matched mode) samples the frozen `Kernels` model, and its mean converges to the exact lattice solver value within standard error as the number of histories grows.
  4. Both engines take their random source as a parameter (numpy Generator by default), and swapping in a different source requires no engine code change.
- **PROJECT.md Key Decisions:** "Classical engine takes its random source as a parameter"; "Three classical solvers (continuous, lattice, exact)". Classical baseline is plain Python/numpy.
- **Phase 2 decisions that bind this phase:**
  - PD-01: transport-corrected one-group model by default; `isotropic_raw` stays selectable.
  - PD-03: absorption = removal from the 14 MeV group.
  - PD-04: Kernels contract v1 covers K ∈ {0, 1}.
  - PD-05: geometry and indexing conventions (x is depth, beam at y = 5.0, row = floor(y/dy) clipped, direction bin measured from +x toward +y).
  - PD-06: Kernels v1 is frozen with T1 = 0.24300446519524305; `main.py` is unchanged.
- **The `Kernels` contract is frozen.** Phase 3 consumes it read-only. Any change is a contract change that also breaks Phase 4, which runs in parallel.

### Claude's Discretion (this research recommends one choice for each)
- Module names, result dataclasses, the random-source protocol shape, chunking, test seeds and tolerances, test doubles.

### Deferred Ideas (OUT OF SCOPE)
- PHYS-09 implicit-capture / variance-reduction baseline (v2).
- K = 2 lattice (QC-08, v2). The lattice MC must not chain a second flight from `flight` (WR-08).
- Wiring the engines into `main.py`. That is Phase 6.
- The error-vs-N sweeps and figures. That is Phase 5; this phase only provides the hooks.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PHYS-03 | Continuous classical MC (numpy, vectorized, seeded, Woodcock delta tracking, isotropic scattering, loss on exit) tallies transmission fraction, absorption fraction, back-face exit-position histogram and collision-order breakdown, with standard errors | Pattern 2 (`mc_continuous.run_continuous`) and Code Example 2. Prototype: 1e7 histories in 1.0 s, 1e5 in 11 ms. All tallies are integer counts with binomial SEs |
| PHYS-04 | Uncollided transmission equals e^{-τ}; histories reproducible from a seed | Validation section V1–V3. Measured T0 z = −0.33 (1e6, seed 2026). Same-seed runs give bit-identical per-history arrays |
| PHYS-07 | Discrete lattice MC samples exactly the `Kernels` model (matched mode); mean converges to exact within SE | Pattern 3 (`mc_lattice.run_lattice`). Measured at 1e8: z = −0.05. Bit-string chi² = 694 on 727 dof. Zero samples outside the support. Row chi² = 14.4 on 16 bins |
| PHYS-08 | Engine takes its random source as a parameter (numpy Generator by default), never owns randomness | Pattern 1 (`random_source.RandomSource`, a structural Protocol that `numpy.random.Generator` already satisfies). A SHA-256 counter source and a scripted source drive both engines with no engine change (measured) |
</phase_requirements>

## Project Constraints (from .claude/CLAUDE.md and the Phase 1/2 gates)

- Classical baseline in plain Python/numpy. **No new packages.** No numba, and no scipy on the engine path. [VERIFIED: .claude/CLAUDE.md "classical baseline in plain Python/numpy"]
- Write against the numpy 2.0 API and use `np.random.Generator`. Never use `np.random.seed` / `np.random.rand` globals. [CITED: .claude/CLAUDE.md stack table]
- Pyodide on Qollab ships numpy 2.4.6 and local is 2.5.3. Avoid numpy 2.5-only APIs. [VERIFIED: docs/QOLLAB-RUNTIME.md line 4 "numpy 2.4.6"]
- Flat package. New modules go in `neutron_qae/`, with no subpackages. `pyproject.toml` has `packages = ["neutron_qae"]`.
- **Do not edit `main.py` and do not import the new modules from `neutron_qae/__init__.py`.** `__init__.py` holds `__all__ = ["smoke"]` [VERIFIED: neutron_qae/__init__.py:8]. Phase 6 wires the engines in. The compliance walker `tests/compliance_checks.py` follows every import reachable from `main.py`. `FORBIDDEN_REACHABLE = {"qiskit_aer", "qiskit_algorithms", "qiskit_ionq", "qiskit_ibm_runtime"}` [VERIFIED: tests/compliance_checks.py:12]. The new modules import only numpy, stdlib and `neutron_qae.problem`/`kernels`, so they would stay compliant even if made reachable.
- No `data/` files in this phase. Every file in `data/` must be referenced by a literal path from `main.py`-reachable code (`test_every_data_file_is_referenced_by_literal_path`). No whitespace in any repo path.
- Test-only helpers (test doubles) go under `tests/`. `ALLOWLIST_DIRS = ("tests", "scripts")` [VERIFIED: tests/compliance_checks.py:18]. `pytest` config: `pythonpath = [".", "tests"]`, `markers = ["slow: long-running"]` [VERIFIED: pyproject.toml].
- Do not modify `neutron_qae/kernels.py`, `exact.py`, `problem.py` or `tests/golden/kernels_v1.json`. They are the frozen contract, and Phase 4 is executing against them in parallel.
- GSD workflow: work goes through `/gsd-execute-phase`.

## Summary

Phase 3 adds three small, numpy-only modules:
- `neutron_qae/random_source.py`: a one-method `RandomSource` protocol, `random(size) -> float64[size] in [0,1)`. `numpy.random.Generator` satisfies it as-is, so no adapter is needed.
- `neutron_qae/mc_continuous.py`: a Woodcock delta-tracking engine, vectorized over histories with a compacting active-index loop.
- `neutron_qae/mc_lattice.py`: a matched sampler of the frozen `Kernels` v1 tables. It draws the same 11-bit strings `x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10` that `exact.py` enumerates and the Q1 circuit measures.

All three were prototyped this session against the real repo modules. The prototype lives at `/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase3/proto/` (`random_source.py`, `mc_continuous.py`, `mc_lattice.py`, `check1..6.py`).

**Physics identity.** The continuous engine uses `spec.front` and `spec.back`, the same `Material.sigma_t` / `sigma_s` numbers the kernels use. Under the default `transport_corrected` model these are the transport-corrected values Σ_tr = 0.1712763935199962 (WHA) and 0.1395029186699459 (SS316), with Σ_s,tr = 0.014547480358451131 and 0.018035691288369696 cm⁻¹. The majorant is Σ_tr,WHA, and steel accepts 81.4% of tentative collisions.

**Validation results:**
- **T0:** τ = 2.0·Σ_WHA + 8.0·Σ_SS = 1.4585761363995597 and e^{−τ} = 0.23256718303628812. This equals `first_collision[16]` bit-for-bit.
- **T≤1:** the continuous quantity "exits the back face after at most one real collision" equals the exact T1 = 0.24300446519524305. At 1e8 histories the MC gives 0.2430122 ± 0.0000429 (z = +0.18).
- **T_all:** the full continuous transmission is 0.2437152 ± 0.0000429. That is 16.6 SE above T1 (K=1 coverage 0.99708), so **T_all must never be tested against T1.**
- **Lattice MC:** gives 0.2430025 at 1e8 (z = −0.05). Over 200 reps at N = 1e4 its RMSE is 0.00438, against a theoretical 0.00429.
- **WR-07 does not show up in any K ≤ 1 marginal:**
  - continuous ≤1-collision exit rows vs `exit_row_distribution_k1`: chi² 17.8 on 16 bins at 1e8;
  - first-collision column: chi² 18.1 on 17 bins;
  - exactly-one-collision front, lateral and back leakage, absorption at first collision, and P(≥2 collisions) all fall within |z| < 1.9 of the kernel-weighted sums.

**Primary recommendation:** Build `random_source.py` → `mc_lattice.py` → `mc_continuous.py` as in the Code Examples, with `chunk = 1 << 16`. Use integer-count tallies with binomial SEs computed once at the end. Write tests with fixed seeds and tolerances in standard errors (|z| < 4). Leave `main.py`, `__init__.py` and the contract files untouched.

## Architectural Responsibility Map

The project is a single Python package (no web tiers), so the tiers here are modules.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Randomness (uniforms) | `neutron_qae/random_source.py` (protocol + `as_source`) | caller (seeds, `SeedSequence.spawn`) | PHYS-08: engines never construct generators. The only `default_rng` call in the package sits in `as_source` |
| Continuous physics reference | `neutron_qae/mc_continuous.py` | `neutron_qae/problem.py` (Σ, geometry, `row_of`) | Reads `ProblemSpec` only, never `Kernels`, so it independently validates the kernels |
| Matched discrete baseline | `neutron_qae/mc_lattice.py` | `neutron_qae/kernels.py` (frozen tables), `exact.py` (bit layout constants) | Must sample exactly what the circuit encodes. It imports the layout constants instead of re-typing them |
| Ground truth | `neutron_qae/exact.py` (existing, frozen) | — | `transmission_within`, `exit_row_distribution_k1`, `bitstring_probabilities_k1` |
| Error-vs-N sweeps, figures | Phase 5 (`scripts/` + `data/`) | `mc_lattice` checkpoints | Not this phase. Phase 3 only exposes `checkpoints` / per-history hits |
| Test doubles | `tests/random_doubles.py` | — | They stay out of the shipped package |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.5.3 local / 2.4.6 Pyodide | All array work, `Generator` (PCG64) default source | Already the project's only numeric dependency. [VERIFIED: `.venv` numpy 2.5.3; docs/QOLLAB-RUNTIME.md numpy 2.4.6] |
| Python stdlib (`math`, `dataclasses`, `typing.Protocol`, `hashlib` in tests only) | 3.14 | Protocol, result dataclasses, the hash test double | No dependency added |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Tests | Already installed. Mark runs of 1e7 histories or more `@pytest.mark.slow` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Woodcock delta tracking | Exact free-flight sampling via the inverse optical depth (what the Phase 2 `proto/cmc.py` did) | Exact sampling is also exact and slightly cheaper, but the ROADMAP locks "Woodcock delta tracking". Delta tracking also removes all interface logic |
| One-method `random(size)` protocol | Wrapper class `NumpySource(rng).uniform(n)` (ARCHITECTURE.md sketch) | The wrapper adds a type for nothing, while `Generator.random(size)` already fits structurally. Integers are derived as `floor(u*16)`, which is exact (see Pitfall 6) |
| Sequential conditional lattice sampling (x, a, φ, e) | One categorical draw over the 2048 enumerated bit-string probabilities | The categorical draw is the exact enumeration in disguise, so convergence to T1 becomes a near-tautology. Sequential sampling is the independent Markov-chain simulation, so its convergence is evidence |
| numba / Cython | — | Not available in Pyodide. Vectorized numpy is already fast enough (below) |

**Installation:** none. No package is added.

## Package Legitimacy Audit

No external packages are installed in this phase. numpy and pytest are already pinned or installed and were approved in Phase 1.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 caller (test / Phase 5 script / Phase 6 main)
   │  seed:int | SeedSequence | Generator | any obj with .random(size)
   ▼
 random_source.as_source(...) ──► RandomSource  (.random(size) -> float64 in [0,1))
   │                                   │
   │            ┌──────────────────────┴───────────────────────┐
   ▼            ▼                                              ▼
 ProblemSpec ─► mc_continuous.run_continuous(spec, n, source)   Kernels v1 ─► mc_lattice.run_lattice(k, n, source)
 (Σ_t, Σ_s per │  per chunk of 2^16 histories:                  (frozen)     │ per chunk:
  material,    │   active idx ─► flight d=-log1p(-u)/Σ_maj       │            │  x ~ first_collision (inverse CDF, 17 outcomes)
  beam, row_of)│   d ≥ dist-to-box? ─yes─► exit face, y_exit     │            │  a ~ Bern(scatter_ratio[x % 16])
               │        │no                                      │            │  φ = floor(16u)
               │   u·Σ_maj < Σ_s(x) ─► scatter, φ=2πu, ncol+=1   │            │  e ~ Bern(flight[x % 16, φ, BACK])
               │   < Σ_t(x) ─► absorb, ncol+=1                   │            │  T = (x==16) | (a & e);  row ~ back_exit_rows | escaped
               │   else virtual (continue, same direction)       │            ▼
               ▼                                                 │      LatticeResult (count, SE, rows, bitstrings?, checkpoints?)
      ContinuousResult (int counts → fractions + binomial SE)   │            │
               │                                                 ▼            ▼
               └────────► validation vs exact.transmission_within / exit_row_distribution_k1 / first_collision
```

### Recommended Project Structure
```
neutron_qae/
├── random_source.py   # RandomSource Protocol, as_source(), draw()  (~40 lines)
├── mc_continuous.py   # BACK/FRONT/LATERAL/ABSORBED fates, ContinuousResult, run_continuous  (~120 lines)
└── mc_lattice.py      # LatticeResult, run_lattice, sample_exit_rows  (~90 lines)
tests/
├── random_doubles.py          # HashCounterSource (SHA-256 counter, 53-bit), ScriptedSource, RecordingSource
├── test_random_source.py      # protocol conformance, as_source coercions, draw() validation, no-global-RNG AST gate
├── test_mc_continuous.py      # PHYS-03/04: tallies, SE, T0 = e^-τ, T≤1 = T1, analytic cases, reproducibility
└── test_mc_lattice.py         # PHYS-07: convergence, bit-string distribution, rows, scripted history, swap source
```
Do not touch `main.py`, `neutron_qae/__init__.py`, `kernels.py`, `exact.py`, `problem.py` or the golden file.

### Pattern 1: Structural random-source protocol (PHYS-08)
**What:** `RandomSource` is a `typing.Protocol` marked `@runtime_checkable` with one method, `random(self, size: int) -> np.ndarray`.
- `numpy.random.Generator` already has `random(size=None, dtype=..., out=None)`, so `isinstance(np.random.default_rng(1), RandomSource)` is `True` (measured).
- `as_source(source=None)` maps:
  - `None` → `np.random.default_rng()`, the "numpy Generator by default", unseeded;
  - `int` / `np.integer` / `SeedSequence` → `default_rng(seed)`;
  - anything with `.random` → returned unchanged;
  - anything else → `TypeError`.
- Engines call `draw(src, size)`, which checks shape `(size,)` and range `[0, 1)` (cheap, and it catches a broken source).
**When to use:** every random number in both engines. **The engines never mention `np.random`** (an AST test enforces this, see V8).
**Why one method:** uniforms of at least 53 bits avoid the coarse-ξ tail bias in `-log(ξ)` (PITFALLS.md Pitfall 8, "random-bit source quantization"). Integers come from `floor(u·n)`.

### Pattern 2: Woodcock delta tracking, vectorized over histories (PHYS-03)
- **State per chunk** (struct of arrays): `x, y, ux, uy` (float64), `ncol` (int64, real collisions), `fate` (int64, −1 = alive), `yexit` (NaN unless a back exit), and optionally `x_first` (position of the first real collision).
- **Start:** `x = 0`, `y = spec.beam_y`, `ux = 1.0`, `uy = 0.0`. Set `uy` to the literal `0.0` so an uncollided neutron exits at exactly y = 5.0, which is row 8. Do not compute it as `sin(0)`; that also gives 0, but the literal is clearer.
- **Majorant:** `smaj = max(spec.front.sigma_t, spec.back.sigma_t)`. With the default model that is the WHA value 0.1712763935199962. Steel's acceptance is Σ_SS/Σ_maj = 0.81449.
- **Loop (compacting active index array `act`):**
  1. `d = -log1p(-u)/smaj`, one uniform per active particle.
  2. Distance to the box along the ray: `sx` to the back face (cx > 0) or the front face (cx < 0) or ∞, and `sl` to the top face (sy > 0) or the bottom face (sy < 0) or ∞. Then `s = min(sx, sl)`.
  3. **Exit if `d >= s`:** face = `BACK if sx <= sl and cx > 0`, `FRONT if sx <= sl and cx < 0`, else `LATERAL`. This is the same tie rule as `kernels.py` (`np.where(sx <= sl, ...)`). For a BACK exit, `yexit = y + sx*sy`.
  4. Otherwise move to the tentative site. One uniform `u·smaj` partitions the event:
     - `< Σ_s(x_new)` → real scatter (`ncol += 1`, `φ = 2πu'`, a third uniform for the scattered subset only);
     - `< Σ_t(x_new)` → real absorption (`ncol += 1`, `fate = ABSORBED`);
     - else → virtual (same direction, keep going).
     The material uses the **new** position with the half-open rule `x < boundary_x` → front, matching `ProblemSpec.material_at`.
  5. `act = act[still alive]`.
- **Tallies per chunk:** accumulate integer `np.bincount`s (fates; transmitted orders clipped to `max_order + 1`; `spec.row_of(yexit)` for all orders and for `ncol <= 1`). SEs are computed once at the end from the counts.
- **Chunking:** `chunk = 1 << 16` was fastest and smallest in the measurements (1e7 histories in 1.01 s with a 13 MB peak, against 1.11 s and 209 MB at 2^20). Results depend on the chunk size because the uniform draw order depends on it. Make `chunk` a keyword with this default and keep it fixed in reproducibility tests.
- **Iteration counts (measured):** the transport-corrected run needs at most 7–8 loop iterations per chunk (c ≈ 0.085–0.13, mfp at majorant 5.8 cm). Raw isotropic needs 17 and a pure scatterer 22. A guard of `max_iter = 100_000` raises `RuntimeError` and never triggers in practice.

### Pattern 3: Matched lattice MC on Kernels v1 (PHYS-07)
**What:** per history, draw exactly the four random registers `exact.py` enumerates, in the same conditional structure:

| Register | Bits | Sample | From |
|---|---|---|---|
| x | 5 | inverse CDF over `first_collision` (17 outcomes, `x == 16` = uncollided) | `np.searchsorted(cdf, u, side="right")`, `cdf[-1] = 1.0` forced, clamp to 16 |
| a | 1 | `u < scatter_ratio[x % 16]` | **x = 16 uses column 0, like the circuit** (`col = x % nx`) |
| φ | 4 | `min(floor(16u), 15)` | uniform 1/16 |
| e | 1 | `u < flight[x % 16, φ, BACK]` | |
| (row) | — | if `x < 16 and a and e`: inverse CDF of `back_exit_rows[col, φ, :]` scaled by `u·flight[col, φ, BACK]`; if `x == 16`: `spec.row_of(spec.beam_y)` (row 8) | not part of the bit string; matches `exit_row_distribution_k1` |

- Transmitted = `(x == 16) | (a & e)`, the same predicate as `exact.bitstring_probabilities_k1`.
- Bit string = `x | a << 5 | phi << 6 | e << 10`. This is `REGISTER_LAYOUT = "x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10, little-endian (bit i = Qiskit qubit i)"` [VERIFIED: neutron_qae/exact.py:15-17, `X_BITS, A_BITS, PHI_BITS, E_BITS = 5, 1, 4, 1`, `N_BITS = X_BITS + A_BITS + PHI_BITS + E_BITS     # 11`]. Import these constants. Do not retype them.
- **Measured:**
  - 1e7 histories in 0.52 s (chunk 2^16);
  - 1e8 → mean 0.2430025, z = −0.05;
  - 4e6 bit strings → chi² 694.1 on 727 dof, 0 samples outside the support (728 non-zero strings, because e = 1 has zero probability wherever `flight[..., BACK] == 0`);
  - exit rows at 1e8 → chi² 14.4 on 16 bins.
- **WR-08 guard:** the tables assume the scatter site lies on the beam line, which holds for the first collision of the normally incident pencil beam. The lattice MC therefore samples one flight only and **must never chain** `flight[..., COLLIDE]` into a second flight. Say so in the docstring. Do not edit `kernels.py` (frozen; Phase 4 is running in parallel).
- **Phase 5 hooks:**
  - `checkpoints=(1000, 10000, ...)` returns cumulative transmitted counts at those N, so prefix estimates come from one run without storing 1e8 booleans;
  - `return_bitstrings=True` for the circuit-vs-classical histogram;
  - `sample_exit_rows(k, bitstrings, source)` as a public helper, so Phase 5 can turn Q1 measurement bit strings into rows **with the same code** that the classical tally uses (like-for-like ANLY-02).
- **Counting N:** one lattice history = one sample of the K = 1 model = the classical counterpart of one A application measured once (one k = 0 shot). The classical cost is **N = histories**, compared against N_A = Σ shots·(2k+1). It is never counted in uniforms (each history uses 4 uniforms, plus 1 if it escapes after a scatter). The RMSE is √(T1(1−T1)/N) = 0.4289/√N, which the 200 reps at N = 1e4 reproduced (0.00438 vs 0.00429). For independent repetitions use `np.random.SeedSequence(seed).spawn(R)`.

### Pattern 4: Result dataclasses with integer counts
`@dataclass(frozen=True, eq=False)`, the same style as `Kernels`. Store `n`, the int64 count arrays and the `source` description or seed if the caller provides one. Expose fractions and SEs as properties: `p = count/n`, `se = sqrt(p(1-p)/n)`.
- **ContinuousResult:**
  - `transmission`, `absorption`, `reflection` (front), `leakage_lateral`, each `*_se`;
  - `order_counts` (transmitted with 0..max_order collisions, plus overflow), `within(K) -> (p, se)`;
  - `row_counts` (all orders) and `row_counts_le1`, `row_fractions()` / `row_se()`;
  - `iterations`.
- **LatticeResult:** `transmitted`, `mean`, `se`, `row_counts`, `bitstrings | None`, `checkpoint_counts | None`.

### Anti-Patterns to Avoid
- **Testing T_all against T1.** They differ by 6.9e-4 (16.6 SE at 1e8). Compare `within(1)` against T1, and `within(0)` against `first_collision[16]` = e^{−τ}.
- **Using the true total cross section for the uncollided check.** e^{−τ_t} = 0.0867 is the physical uncollided value. The model's e^{−τ} is 0.2326. Use `spec.tau_x(spec.width_x)` (Phase 2 Pitfall 10).
- **Float accumulation of fractions across chunks.** Accumulate int64 counts and divide once.
- **`np.random.default_rng` or `np.random.*` inside the engines.** Only `as_source` may construct a Generator.
- **Chaining a second flight from `Kernels.flight`** (WR-08). It is wrong once the neutron has left the beam line.
- **A categorical sampler over the enumerated 2048 probabilities as "the lattice MC".** It is valid, but it is the exact solver in disguise.
- **Tests with `|diff| < 1·SE`.** That fails about 32% of seeds. Use fixed seeds and `|z| < 4`; the result is deterministic and has margin.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Material interface crossing | Distance-to-interface tracking, re-sampling at x = 2.0 | Woodcock delta tracking with Σ_maj | Exact, with no interface code. The PITFALLS.md "old cross section through the interface" bug cannot happen |
| Exponential flights | `-log(u)` | `-np.log1p(-u)` | `u ∈ [0,1)`, so `log(0)` is avoided |
| Categorical sampling | Python loops / `rng.choice` per row | `np.searchsorted` on a cumulative table; row-wise `(cumsum <= u[:,None]).sum(1)` | Vectorized and source-agnostic (`rng.choice` would bypass the protocol) |
| Independent repetitions | Ad-hoc seed arithmetic (`seed + i`) | `np.random.SeedSequence(seed).spawn(R)` | Statistically independent streams |
| Ground truth | Re-deriving T1 | `exact.transmission_within(k, 1)`, `exact.exit_row_distribution_k1(k)` | Frozen and golden-tested |
| Exit row binning | `int(y/dy)` / `round` | `spec.row_of(y)` | floor + clip, PD-05. y = 5.0 → row 8 |

**Key insight:** both engines are short because the hard parts are already frozen: geometry and Σ (`ProblemSpec`), tables (`Kernels`), truth (`exact`). Phase 3's risk is in statistics hygiene (counts, SEs, seeds, draw order), not in physics code.

## Common Pitfalls

### Pitfall 1: Confusing the three "transmissions"
**What goes wrong:** the continuous T_all (0.24372) is compared with the exact T1 (0.24300) and fails at large N, or T0 is compared with the physical e^{−τ_t}.
**How to avoid:** the continuous T≤1 = `within(1)` is the quantity that equals T1. It is exact because the beam is normally incident, so the first collision always lies on y = beam_y, the WR-08 condition. The kernels are conditional averages over that same physics, with quadrature error ~1e-6. T_all − T1 = 7.1e-4 is the ANLY-03 truncation bias (coverage 0.99708).

### Pitfall 2: WR-07 per-entry quadrature error
**What goes wrong:** someone compares individual `flight[j, b, ·]` or `back_exit_rows[j, b, i]` entries against the continuous MC (up to 2.5% / 18% relative error per entry) and declares the contract broken.
**How to avoid:** compare only **marginals**: T1, the row histogram, the first-collision column, and exactly-one-collision front/lateral/back/absorbed. All of them agree with the continuous MC at 4e6–1e8 histories (|z| < 1.9, row chi² 17.8/16). Per-(j, b) comparisons are out of scope. The lattice MC is unaffected because it samples the tables themselves.

### Pitfall 3: Reproducibility depends on more than the seed
**What goes wrong:** "same seed, different histories" when `chunk` or `n` differs, or across platforms.
**Why:** the vectorized draw order depends on the chunk size (measured: changing `chunk` changes the histories). libm `log1p`/`cos`/`sin` may differ in the last ulp between macOS and Pyodide. numpy does not promise that `Generator` method streams stay stable across versions [ASSUMED: NEP 19 wording recalled, not re-read].
**How to avoid:** the guarantee and the test are "same source state + same `n` + same `chunk` + same platform → identical per-history arrays". Document the draw order in each engine's docstring:
- continuous, per iteration: flight uniforms (all active), then collision-type uniforms (non-exiting), then direction uniforms (scattered);
- lattice, per chunk: x, a, φ, e (m each), then row uniforms (escaped scattered).

### Pitfall 4: Standard error edge cases
`p̂ = 0` gives SE = 0 (rare rows at small N). Report the count alongside it. Use binomial SEs from counts: histories are iid, so batch means are unnecessary for single-run SEs. For plots, Phase 5 uses RMSE over spawned reps.

### Pitfall 5: Memory in Pyodide
A 2^20 chunk peaks at 209 MB for the continuous engine. Use `chunk = 1 << 16` (13 MB peak, and also the fastest).

### Pitfall 6: Integer draws from uniforms
`floor(u·16)` is exactly uniform on 0..15 when u is a multiple of 2^-53 (Generator.random and the hash double both produce such values). Clamp with `min(·, 15)` for arbitrary sources. For the 17-outcome x and the rows, use the inverse CDF with `cdf[-1] = 1.0` forced, so rounding cannot produce index 17.

### Pitfall 7: Delta-tracking correctness details
- Use the material at the **tentative collision site**, not the pre-flight position.
- Count only real collisions (scatter or absorb) in `ncol`. Virtual collisions are not collisions.
- Exit is checked **before** the collision (`d >= s` → exit).
- At a corner tie (`sx == sl`), assign the x face, matching the kernels.
- Under `np.errstate(divide="ignore", invalid="ignore")`, guard `cx == 0` / `sy == 0` with `np.where(..., np.inf)`. The initial beam has `sy == 0`.

### Pitfall 8: Pyodide speed
There is no numba in Pyodide. Natively, 1e5 continuous histories take 11 ms and 1e5 lattice histories 5.7 ms. Pyodide was ~2× native on the Phase 1 qiskit probe [VERIFIED: docs/QOLLAB-RUNTIME.md line 93], and vectorized numpy in WASM is likely 2–5× slower than native [ASSUMED]. Expect ≤ 0.1 s for 1e5 and ≤ 1 s for 1e6 in the judge's browser. Phase 6 should measure before choosing the live N.

## Code Examples

These are verified prototypes (scratchpad `phase3/proto/`, every check passes against the repo's frozen modules). Rename and finish them as needed: docstrings, `max_order` and `checkpoints` plumbing.

### 1. `neutron_qae/random_source.py`
```python
from __future__ import annotations
from typing import Protocol, runtime_checkable
import numpy as np

@runtime_checkable
class RandomSource(Protocol):
    def random(self, size: int) -> np.ndarray:  # float64 uniforms in [0, 1), shape (size,)
        ...

def as_source(source=None) -> RandomSource:
    """None -> np.random.default_rng() (unseeded); int/SeedSequence -> default_rng(seed); else duck-typed source."""
    if source is None or isinstance(source, (int, np.integer, np.random.SeedSequence)):
        return np.random.default_rng(source)
    if not isinstance(source, RandomSource):
        raise TypeError(f"random source must have .random(size); got {type(source).__name__}")
    return source

def draw(source: RandomSource, size: int) -> np.ndarray:
    u = np.asarray(source.random(size), dtype=np.float64)
    if u.shape != (size,):
        raise ValueError(f"random source returned shape {u.shape}, expected ({size},)")
    if size and not (u.min() >= 0.0 and u.max() < 1.0):
        raise ValueError("random source must return uniforms in [0, 1)")
    return u
```
Note: `isinstance(True, int)` is true, so reject `bool` explicitly if you want strictness.

### 2. `neutron_qae/mc_continuous.py` (core loop)
```python
BACK, FRONT, LATERAL, ABSORBED = 0, 1, 2, 3     # fates; BACK/FRONT/LATERAL values match kernels.py outcomes

def run_continuous(spec, n, source=None, *, chunk=1 << 16, max_order=8, max_iter=100_000, histories=False):
    src = as_source(source)
    fW, fS = spec.front, spec.back
    smaj = max(fW.sigma_t, fS.sigma_t)
    L, H, xb = spec.width_x, spec.height_y, spec.boundary_x
    fate_c = np.zeros(4, np.int64); ord_c = np.zeros(max_order + 2, np.int64)
    rows = np.zeros(spec.ny, np.int64); rows1 = np.zeros(spec.ny, np.int64)
    done = 0
    while done < n:
        m = min(chunk, n - done); done += m
        x = np.zeros(m); y = np.full(m, spec.beam_y); ux = np.ones(m); uy = np.zeros(m)
        ncol = np.zeros(m, np.int64); fate = np.full(m, -1, np.int64); yexit = np.full(m, np.nan)
        act = np.arange(m); it = 0
        while act.size:
            it += 1
            if it > max_iter:
                raise RuntimeError("delta tracking did not terminate")
            xa, ya, cx, sy = x[act], y[act], ux[act], uy[act]
            d = -np.log1p(-draw(src, act.size)) / smaj
            with np.errstate(divide="ignore", invalid="ignore"):
                sx = np.where(cx > 0, (L - xa) / cx, np.where(cx < 0, -xa / cx, np.inf))
                sl = np.where(sy > 0, (H - ya) / sy, np.where(sy < 0, -ya / sy, np.inf))
            out = d >= np.minimum(sx, sl)
            face = np.where(sx <= sl, np.where(cx > 0, BACK, FRONT), LATERAL)
            eo = act[out]; fate[eo] = face[out]
            yexit[eo] = np.where(face[out] == BACK, ya[out] + sx[out] * sy[out], np.nan)
            stay = ~out; ai = act[stay]; dd = d[stay]
            xn = xa[stay] + dd * cx[stay]; x[ai] = xn; y[ai] = ya[stay] + dd * sy[stay]
            front = xn < xb                                   # half-open, == ProblemSpec.material_at
            ss = np.where(front, fW.sigma_s, fS.sigma_s); st = np.where(front, fW.sigma_t, fS.sigma_t)
            u = draw(src, ai.size) * smaj
            scat = u < ss; absb = (u >= ss) & (u < st)        # else: virtual collision
            ncol[ai[scat | absb]] += 1
            fate[ai[absb]] = ABSORBED
            sc = ai[scat]; phi = 2.0 * np.pi * draw(src, sc.size)
            ux[sc] = np.cos(phi); uy[sc] = np.sin(phi)
            act = ai[~absb]
        fate_c += np.bincount(fate, minlength=4)
        tb = fate == BACK
        ord_c += np.bincount(np.minimum(ncol[tb], max_order + 1), minlength=max_order + 2)
        r = spec.row_of(yexit[tb])
        rows += np.bincount(r, minlength=spec.ny); rows1 += np.bincount(r[ncol[tb] <= 1], minlength=spec.ny)
    ...  # build ContinuousResult; if histories=True also return concatenated (fate, ncol, yexit[, x_first])
```

### 3. `neutron_qae/mc_lattice.py` (core)
```python
from neutron_qae.exact import X_BITS, A_BITS, PHI_BITS    # shifts: a << 5, phi << 6, e << 10
from neutron_qae.kernels import BACK

def run_lattice(k, n, source=None, *, chunk=1 << 16, return_bitstrings=False, checkpoints=()):
    src = as_source(source); sp = k.spec; nx, nd = sp.nx, sp.n_dir
    cdf_x = np.cumsum(k.first_collision); cdf_x[-1] = 1.0
    q = k.flight[..., BACK]; rc = np.cumsum(k.back_exit_rows, axis=-1)
    ...
    # per chunk of m histories:
    x = np.minimum(np.searchsorted(cdf_x, draw(src, m), side="right"), nx)
    col = x % nx                                               # x == nx (uncollided) rotates a/e like column 0
    a = (draw(src, m) < k.scatter_ratio[col]).astype(np.int64)
    phi = np.minimum((draw(src, m) * nd).astype(np.int64), nd - 1)
    e = (draw(src, m) < q[col, phi]).astype(np.int64)
    t = (x == nx) | ((a == 1) & (e == 1))
    bits = x | (a << X_BITS) | (phi << (X_BITS + A_BITS)) | (e << (X_BITS + A_BITS + PHI_BITS))
    r = np.full(m, -1, np.int64); r[x == nx] = sp.row_of(sp.beam_y)
    se_ = np.nonzero((x < nx) & (a == 1) & (e == 1))[0]
    u = draw(src, se_.size) * q[col[se_], phi[se_]]
    r[se_] = np.minimum((rc[col[se_], phi[se_]] <= u[:, None]).sum(axis=1), sp.ny - 1)
```
Factor the last four lines into `sample_exit_rows(k, bitstrings, source)` so Phase 5 can reuse them on Q1 counts.

### 4. Test doubles (`tests/random_doubles.py`)
```python
class HashCounterSource:            # SHA-256 counter mode, 53-bit uniforms; not numpy's bit generator
    def __init__(self, key=b"neutron-qae"): self.key, self.counter, self.calls, self.drawn = key, 0, 0, 0
    def random(self, size):
        self.calls += 1; self.drawn += size
        nb = (size + 3) // 4
        buf = b"".join(hashlib.sha256(self.key + (self.counter + i).to_bytes(8, "little")).digest() for i in range(nb))
        self.counter += nb
        w = np.frombuffer(buf, dtype="<u8")[:size]
        return (w >> np.uint64(11)).astype(np.float64) * 2.0 ** -53

class ScriptedSource:               # replays fixed uniforms; raises when exhausted
    def __init__(self, values): self.values, self.pos = np.asarray(values, float), 0
    def random(self, size):
        if self.pos + size > self.values.size: raise RuntimeError("ScriptedSource exhausted")
        out = self.values[self.pos:self.pos + size]; self.pos += size; return out.copy()
```
Measured with these doubles:
- `HashCounterSource` driving `run_continuous` (2e5 histories, T≤1 z = −1.66, 446,113 uniforms in 21 calls, 0.06 s) and `run_lattice` (2e5, z = −0.16), with no engine change;
- `ScriptedSource([0.99, 0.5, 0.5, 0.5])` → lattice history x = 16, a = 0, φ = 8, e = 0 → bit string 528 (`0b1000010000`), transmitted, row 8, 4 uniforms consumed;
- `ScriptedSource([0.95])` → continuous uncollided back exit at y = 5.0, ncol 0, 1 uniform;
- `ScriptedSource([0.10, 0.01, 0.0, 0.95])` → collision at x = 0.615 in WHA, scatter (0.01·Σ_maj < Σ_s,W), φ = 0, then back exit at y = 5.0 with ncol = 1, 4 uniforms.

## Validation plan (tests the planner should create; every row measured in the prototype)

| # | Test | Setup | Assertion | Measured |
|---|------|-------|-----------|----------|
| V1 | Uncollided = e^{−τ} (PHYS-04) | default spec, n = 1e6, `default_rng(2026)` | `|within(0) − exp(−spec.tau_x(spec.width_x))| < 4·SE`; also `exp(-tau) == k.first_collision[16]` to 1e-15 | z = −0.33 (0.15 s). Over 300 seeds the z mean is −0.02 and the std 0.95 (unbiased) |
| V2 | T≤1 = exact T1 | same run | `|within(1) − transmission_within(k,1)| < 4·SE` | z = −0.45 |
| V3 | Same seed → identical histories (PHYS-04) | n = 5e4, `histories=True`, twice with `default_rng(5)` | `np.array_equal(..., equal_nan=True)` on fate, ncol, yexit | True |
| V4 | Two-layer pure absorber | `ProblemSpec(front=Material("A", ΣW, 0.0), back=Material("B", ΣS, 0.0))`, n = 4e5 | T = e^{−τ} within 4 SE; FRONT = LATERAL = 0 | z = −0.60, fates [92867, 0, 0, 307133] |
| V5 | Pure scatterer conservation | Σ_s = Σ_t both layers | ABSORBED = 0; counts sum to n | [80741, 54798, 64461, 0] |
| V6 | Tallies + SE present (PHYS-03) | default run | fates sum to n; `order_counts.sum() == fate_counts[BACK]`; `row_counts.sum() == fate_counts[BACK]`; SE = √(p(1−p)/n) | 1e7: T 0.243647 ± 0.000136, A 0.721624 |
| V7 | isotropic_raw also matches | `sparc_first_wall("isotropic_raw")`, n = 4e6 | `within(1)` vs exact raw T1 0.11006367028977174 within 4 SE | 0.110212 ± 0.000157 (z = +0.94) |
| V8 | Engines never own randomness (PHYS-08) | AST scan of `mc_continuous.py`, `mc_lattice.py` | no `random` attribute access on `np` and no `default_rng`/`RandomState`/`np.random` names; only `random_source.as_source` constructs one | — |
| V9 | Swap source, no code change (PHYS-08) | `HashCounterSource`, both engines, 2e5 | |z| < 4 against T1 | −1.66 / −0.16 |
| V10 | Lattice converges to T1 (PHYS-07) | N ∈ {1e3, 1e4, 1e5, 1e6}, fixed seed | |z| < 4 at each N; plus RMSE over 100 spawned reps at N = 1e3 vs 1e4 has ratio in [2.4, 4.2] (≈√10) | 1e6: z = −0.59; RMSE 1e4 = 0.00438 vs 0.00429 theory |
| V11 | Lattice bit strings = enumeration | 4e6, `return_bitstrings=True` | zero counts where `bitstring_probabilities_k1` gives p = 0; chi² over the support < dof + 5√(2·dof) | 0 outside, chi² 694 / 727 dof |
| V12 | Lattice rows = `exit_row_distribution_k1` | 1e6 (fast) or 1e8 (slow mark) | chi² < 16 + 5√32 | 1e8: 14.4 |
| V13 | Scripted single histories | the `ScriptedSource` cases above | exact fate / bit string / row / uniforms consumed | see Code Example 4 |
| V14 (slow) | Continuous ≤1 rows and first-collision column vs kernels marginals | 4e6–1e8 | chi² bounds as V12 | rows 17.8/16; columns 18.1/17 |
| V15 | Input validation | n ≤ 0, non-int n, source without `.random`, bad shape or out-of-range uniforms | ValueError / TypeError | — |

Keep the default (non-slow) suite to ≲ 3 s of Phase 3 tests in total. The 1e8 runs (12 s and 7 s) are `@pytest.mark.slow`.

**Expected reference numbers for the docs (seed-specific, 1e8 histories):**
- continuous, default model: T_all = 0.2437152 ± 4.3e-5; T≤1 = 0.2430122 ± 4.3e-5; absorption ≈ 0.7216; front ≈ 0.0166; lateral ≈ 0.0181 (from 1e7: fates [2436471, 166146, 181147, 7216236]);
- transmitted collision orders at 1e7: [2325065, 104305, 6650, 419, 30, 2, 0, …].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 2 `proto/cmc.py`: exact free-flight sampling by inverting τ(x), collision-order tally, owns `rng` | Woodcock delta tracking, protocol-injected source, chunked int tallies | This phase | Meets the ROADMAP's locked method and PHYS-08 |
| ARCHITECTURE.md sketch `NumpySource(rng).uniform(n)` | Structural `RandomSource.random(size)`, which a Generator satisfies directly | This phase | One fewer type. The default really is "a numpy Generator" |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | numpy does not guarantee `Generator` method streams across versions (NEP 19), so reproducibility is promised per platform and version only | Pitfall 3 | Low. Tests compare runs within one process |
| A2 | Vectorized numpy in Pyodide is 2–5× slower than native, so 1e5 histories take ≲ 0.1 s in the browser | Pitfall 8 | Low. Phase 6 measures it before choosing the live N |
| A3 | libm differences between macOS and Pyodide may change rare histories in the last ulp | Pitfall 3 | Low. No cross-platform byte-equality test is planned |

## Open Questions (RESOLVED — Q1: kernels.py untouched, WR-08 caveat in mc_lattice docstring (PD-14); Q2: absorption split by material deferred to a quick task (PD-14))

1. **Should Phase 3 also apply the WR-07/WR-08 docstring fixes in `kernels.py`?**
   - What we know: both are open in 02-REVIEW-DISPOSITION.md. Neither changes a table value.
   - Recommendation: **no** (Phase 4 is executing against `kernels.py` in parallel). Put the WR-08 caveat in the `mc_lattice` docstring. Leave `kernels.py` to a post-Phase-4 quick task.
2. **Absorption split by material (WHA vs SS) for an "impact" tally?**
   - Recommendation: optional, one extra `bincount` on `x < boundary_x` at absorption. It is not required by PHYS-03. Add it only if it costs under 10 minutes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (.venv) | everything | ✓ | 3.14.8 | — |
| numpy | engines | ✓ | 2.5.3 (Pyodide 2.4.6) | — |
| pytest | tests | ✓ | 9.1.1 | — |

Measured on an Apple M3 Pro. Nothing is missing.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Validate `n` (int ≥ 1), `chunk` (int ≥ 1), the source type (`as_source` raises TypeError) and its output shape and range (`draw`). Bound loop iterations with `max_iter` |
| V6 Cryptography | no | `hashlib` appears only in a test double and is not used for security |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Huge `n` from a future `main()` form field exhausts browser memory / CPU | DoS | Chunked processing (bounded memory). Phase 6 caps the live `n` |
| Malformed random source (NaN, ≥ 1, wrong length) silently biases results | Tampering | `draw()` validation raises ValueError |

No file I/O, network or `data/` files are involved in this phase.

## Sources

### Primary (HIGH confidence)
- Repo code read this session: `neutron_qae/problem.py` (lines 18-19 `MODELS = ("transport_corrected", "isotropic_raw")`; 117-123 defaults `width_x: float = 10.0`, `height_y: float = 10.0`, `nx: int = 16`, `ny: int = 16`, `boundary_x: float = 2.0`, `beam_y: float = 5.0`, `n_dir: int = 16`; 148-150 `return self.front if x < self.boundary_x else self.back`; 168-171 `row_of`), `neutron_qae/kernels.py` (line 19 `BACK, FRONT, LATERAL, COLLIDE = 0, 1, 2, 3`; 101-106 face rule `face = np.where(sx <= sl, np.where(cx > 0, BACK, FRONT), LATERAL)`), `neutron_qae/exact.py` (15-17 register layout, 40-44 transmitted predicate `x == nx or (a == 1 and e == 1)`), `tests/test_exact.py` (21-22 `T0_REF = 0.23256718303628812`, `T1_REF = 0.24300446519524305`), `tests/compliance_checks.py` (12, 18), `pyproject.toml`, `neutron_qae/__init__.py:8`.
- Prototype runs this session (scratchpad `phase3/proto/check1.py`–`check6.py`): every measured number in this document.
- `.planning/phases/02-problem-spec-kernels-contract/02-REVIEW.md` WR-07, WR-08; `02-RESEARCH.md` Patterns 4–5, Pitfall 10.

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` §1 (delta tracking, RNG injection, tallies); `PITFALLS.md` Pitfall 8 (classic MC bugs). These are project research, consistent with the prototype.
- Woodcock delta tracking as a standard exact method (Woodcock et al. 1965) [CITED: ARCHITECTURE.md; confirmed empirically here by the unbiased z distribution and the pure-absorber test].

### Tertiary (LOW confidence)
- A1–A3 above.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. numpy only, nothing new.
- Architecture: HIGH. All three modules were prototyped and validated against the frozen contract at up to 1e8 histories.
- Pitfalls: HIGH for the physics and statistics (measured). MEDIUM for Pyodide speed and cross-platform reproducibility (assumed).

**Research date:** 2026-10-10
**Valid until:** end of hackathon (2026-10-11), or until the Kernels contract changes.
