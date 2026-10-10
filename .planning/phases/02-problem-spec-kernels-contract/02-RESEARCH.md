# Phase 2: Problem Spec & Kernels Contract - Research

**Researched:** 2026-10-10
**Domain:** One-group 14 MeV neutron data (ENDF/B-VIII.0), discrete collision-event transport model, exact enumeration
**Confidence:** HIGH. Every number below was computed this session from the real ENDF/B-VIII.0 files, cross-checked against PNNL-15870 atom densities, an 8M-history continuous Monte Carlo and a Qiskit statevector.

<user_constraints>
## User Constraints (no CONTEXT.md; this phase skipped /gsd-discuss-phase)

There is no CONTEXT.md. Per the orchestrator, the ROADMAP Phase 2 section, the PROJECT.md Key Decisions and the project research stand in for user decisions. They are copied verbatim below.

### Locked Decisions (ROADMAP Phase 2 and PROJECT.md Key Decisions, verbatim)
- "`ProblemSpec` describes a 10 cm x 10 cm slab on a 16 x 16 grid with 2.0 cm tungsten heavy alloy on the plasma side and 8.0 cm 316 stainless steel behind, and a test shows the material boundary inside column 4 is handled correctly rather than snapped to a column edge."
- "Every one-group 14 MeV cross section (total, scattering, absorption including the non-elastic treatment) for both materials is cited in code and docs with its ENDF/B-VIII.0 source and evaluation date."
- "`Kernels`, built from `ProblemSpec`, exposes the first-collision column distribution, scatter ratio per column, and escape probability per column and direction; tests show probability is conserved across each table's outcomes, and the dataclass is frozen as the one contract both classical and quantum code import."
- "The exact lattice solver enumerates every random-bit string of the discrete model and returns the exact transmission within K collisions; this value is the reference that Phase 3, 4 and 5 tests compare against."
- "Contract note: freeze `Kernels` and the exact solver before Phases 3 and 4 start; any later change is an explicit contract change that re-runs both branches' contract tests."
- PROJECT.md Key Decisions: "One quantum step = one collision, fresh qubits per random choice"; "One-group 14 MeV physics"; "2D slab 10 × 10 cm, 16 × 16 grid ... 2.0 cm W boundary falls inside column 4 and is handled by the kernels"; "Three classical solvers (continuous, lattice, exact)".
- PROJECT.md Active scope: "isotropic scattering; particle lost on exit through any face".
- Out of scope (REQUIREMENTS.md): "Anisotropic scattering, fission, (n,2n) multiplication"; "Multigroup or continuous-energy physics"; "3D geometry or finer than 16 × 16".

### Claude's Discretion (the research recommends a choice for each)
- Alloy composition and density, 316 SS composition: **WHA 97W-2Ni-1Fe at 18.5 g/cm³ (SPARC's own alloy); 316 SS from PNNL-15870 Rev. 2 at 8.00 g/cm³.**
- How non-elastic and (n,2n) are treated: **"14 MeV-group removal". Non-elastic is loss; (n,2n) is not double-counted.**
- Elastic anisotropy: **a transport-corrected one-group model, isotropic in the model.** The user should confirm this (Assumption A1).
- Direction discretisation, beam, column indexing, K scope, file layout and how the contract is frozen: see Architecture Patterns.

### Deferred Ideas (OUT OF SCOPE)
- K=2 encoding (QC-08), the Q1-Y uniform source (QC-07), implicit capture (PHYS-09) and the interactive UI (UI-01). All are v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PHYS-01 | ProblemSpec: 10×10 cm slab, 16×16 grid, 2.0 cm WHA + 8.0 cm 316 SS, boundary handled correctly inside column 4 | §Pattern 1 (frozen `ProblemSpec`) and §Pattern 3 (the mixed column). Column 4 in 1-based counting is index 3, spanning [1.875, 2.5) cm with 0.125 cm WHA and 0.5 cm SS. A test asserts the exact segment split, τ₃ = 0.125Σ_W + 0.5Σ_SS, p_first[3] and c[3] in closed form. Prototype tests pass. |
| PHYS-02 | One-group 14 MeV Σ (total, scattering, absorption incl. non-elastic) from ENDF/B-VIII.0, cited with source and evaluation date | §Nuclear Data: per-element σ values at 14.1 MeV, MAT numbers and EVAL dates for all 34 isotopic files, compositions, atom densities (matched to PNNL to 6 digits), macroscopic Σ and mean free paths. |
| PHYS-05 | Frozen `Kernels` (first-collision column, scatter ratio, escape per column and direction) is the classical/quantum contract | §Pattern 4 (conditional-average kernels), §Code Examples (`build_kernels`), conservation, symmetry and freeze tests, and the golden-file freeze. Prototype passes 7/7 tests. |
| PHYS-06 | Exact solver enumerates every random-bit string and returns the exact transmission within K collisions | §Pattern 5. All 2^11 = 2048 bit strings of the Q1 registers x(5) a(1) φ(4) e(1) are enumerated. T₁ = 0.24300446519524305 matches the closed form to 1e-16, a Qiskit `Statevector` per bit string to 6e-15, and the continuous MC ≤1-collision tally within 0.19 σ. |
</phase_requirements>

## Project Constraints (from .claude/CLAUDE.md and Phase 1 gates)

- Python 3.14, `qiskit==2.5.2`, numpy 2.x. Qollab runs Pyodide 314.0.7 with numpy 2.4.6. Avoid numpy 2.5-only APIs. [VERIFIED: docs/QOLLAB-RUNTIME.md runtime rows "3.14.2 / 2.4.6 / 2.5.2"]
- Flat package `neutron_qae/` next to `main.py`. No `src/` layout. `pyproject.toml:19` reads `packages = ["neutron_qae"]          # REQUIRED: auto-discovery fails (...)`, so **new subpackages would also need listing. Use flat modules instead.** [VERIFIED: pyproject.toml:19]
- Nothing reachable from `main.py` may import `FORBIDDEN_REACHABLE = {"qiskit_aer", "qiskit_algorithms", "qiskit_ionq", "qiskit_ibm_runtime"}`. [VERIFIED: tests/compliance_checks.py:11]
- Files must stay under `MAX_FILE_BYTES = 2_000_000`. [VERIFIED: tests/compliance_checks.py:12]
- **Every file under `data/` must appear as a literal `"data/..."` string inside code reachable from `main.py`.** Lines 36-37 of tests/test_compliance.py: `data = [p for p in (ROOT / "data").rglob("*") if p.is_file()] ...` and `missing = [... if f'"{p.relative_to(ROOT).as_posix()}"' not in text]`. A new `data/*.json` that `main.py` does not reach fails the existing suite. [VERIFIED: tests/test_compliance.py:36-37]
- `.gitattributes` lines 5-7 read `tests/ export-ignore`, `scripts/ export-ignore`, `docs/ export-ignore`. Golden files in `tests/` and docs in `docs/` never reach the Qollab upload. [VERIFIED: .gitattributes:5-7]
- Backends are injected, never constructed. `ALLOWLIST_DIRS = ("tests", "scripts")` [VERIFIED: tests/compliance_checks.py:17]. Phase 2 code needs no backend at all.
- No whitespace in repo paths. Use the GSD workflow for edits. Commit planning docs (`commit_docs: true`).
- `workflow.nyquist_validation: false`, so the Validation Architecture section is skipped. `security_enforcement: true` at ASVS level 1, so the Security Domain is included. [VERIFIED: .planning/config.json]

## Summary

The real ENDF/B-VIII.0 files were downloaded this session: 41 isotopic evaluations, pulled from the NNDC neutron-sublibrary zip with HTTP range requests. MF3 (MT1, MT2, partials) and MF4/MT2 angular data were parsed at 14.1 MeV. With SPARC's own heavy alloy (97W-2Ni-1Fe, 18.5 g/cm³) and PNNL-15870 316 SS (8.00 g/cm³), the true total cross sections are **Σ_t(WHA) = 0.3309 cm⁻¹ (mean free path 3.02 cm)** and **Σ_t(SS316) = 0.2229 cm⁻¹ (mfp 4.49 cm)**. The 2 cm of WHA is therefore 0.66 mfp, the 8 cm of steel is 1.78 mfp, and τ_total = 2.445. Both values hit the project's sanity targets of ~3 cm and 4.5-6 cm. Elastic scattering is about half of Σ_t (0.53 in WHA, 0.46 in SS) and very forward-peaked (lab μ̄ = 0.917 in WHA, 0.822 in SS). True capture is negligible (~7e-5 cm⁻¹). The non-elastic part in WHA is 79% (n,2n).

The physics decision that matters is how a one-group isotropic model treats that forward-peaked elastic scattering. The research compared three cases with a continuous 2D Monte Carlo of the 14 MeV-group transmission (uncollided plus elastic-only):
- the "raw isotropic" model (Σ_t, c = Σ_el/Σ_t) gives **0.122**;
- the **transport-corrected** model (Σ_tr = Σ_t − μ̄Σ_el, Σ_s,tr = (1−μ̄)Σ_el) gives **0.244**;
- a reference run that samples the actual ENDF lab angular distributions gives **0.229**.

The transport-corrected model is +6.5% from the reference; raw isotropic is −46%. **Recommend the transport-corrected model as the default** and keep `isotropic_raw` selectable for a disclosed comparison. In the transport-corrected model K=1 covers 99.7% of transmission and K=2 covers 100.0%. In raw isotropic, K=1 covers 89.9% and K=2 covers 96.7%, which reproduces the Phase 1 "~90%" claim.

The contract design gives K=1 a single, exact value. The kernels are **conditional averages over the continuous model**:
- `first_collision[j]` is exact from the optical depth;
- `scatter_ratio[j]` is the collision-weighted average (exact in the mixed column);
- `flight[j, b, outcome]` averages the escape probability over the scatter-site density inside column j and over φ inside bin b, using Gauss-Legendre quadrature.

With these tables the discrete K=1 transmission **equals the continuous-physics ≤1-collision transmission**. The prototype gives 0.243004 against the 8M-history MC's 0.243033 ± 0.00015. The only approximation left is K-truncation, plus quadrature error of about 1e-6. Phase 3 therefore gets a hard test with no "discretisation tolerance", and the truncation-bias disclosure (ANLY-03) becomes clean.

**Primary recommendation:**
- Add four flat modules: `neutron_qae/nuclear_data.py` (cited constants, no data file), `problem.py` (frozen `ProblemSpec`), `kernels.py` (frozen `Kernels`, contract v1, K≤1) and `exact.py` (2^11 bit-string enumeration).
- Freeze the contract with `tests/golden/kernels_v1.json`, compared at rtol 1e-12, never a byte hash.
- Use the transport-corrected one-group model, with T₀ = 0.2325671830 and T₁ = 0.2430044652 as the reference values.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Nuclear data constants and provenance | `neutron_qae/nuclear_data.py` (pure constants) | `docs/PHYSICS.md` (citations table) | One place for numbers. Pyodide-safe, with no file I/O and no `data/` coupling. |
| Macroscopic Σ and the geometry definition | `neutron_qae/problem.py` | — | "Defined exactly once" (ROADMAP). Phases 3, 4 and 5 import it. |
| Probability tables (the contract) | `neutron_qae/kernels.py` | `tests/golden/kernels_v1.json` | The only classical/quantum coupling. Pure numpy, no qiskit. |
| Ground truth T_K | `neutron_qae/exact.py` | — | Consumes only `Kernels`. Stdlib `math.fsum`. |
| Reproducible derivation from ENDF | `scripts/derive_cross_sections.py` (optional, dev-only, network) | — | Lives in `scripts/`: export-ignored and never reached from `main.py`. |
| Contract enforcement | `tests/test_kernels_contract.py`, `tests/test_exact.py`, `tests/test_problem.py` | — | Freezing the contract is a test property. |

## Nuclear Data (PHYS-02): the numbers

**Source data.** ENDF/B-VIII.0 neutron sublibrary (CSEWG release 2018-02-02; D. Brown et al., Nucl. Data Sheets 148, 1 (2018)). The files came from `https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip`, 310,158,456 bytes, Last-Modified 2024-03-15, with members `ENDF-B-VIII.0_neutrons/n-ZZZ_Sy_AAA.endf`. MF3 was interpolated with the file's own interpolation law at 14.1 MeV. μ̄ is the exact mean of the lab cosine from MF4/MT2 (LCT=2, CM→lab transform), with the pdf interpolated linearly in E. [VERIFIED: files downloaded and parsed this session]

**Evaluation provenance** (headers read from each file this session; the `NDS 148, ...` and `DIST-FEB18` strings appear verbatim in the headers):

| Element | Isotopic files (MAT) | Evaluation (verbatim header) |
|---|---|---|
| W | W-180 (7425), W-182 (7431), W-184 (7437), W-186 (7443) | `IAEA Eval090806` (2009-08-06), `NDS 148, 1 (2018) DIST-FEB18` |
| W | W-183 (7434) | `IAEA EVAL-AUG14` |
| Fe | Fe-54 (2625), Fe-56 (2631) | `CIELO EVAL-DEC17`, `NDS 148, 214 (2018)` |
| Fe | Fe-57 (2634), Fe-58 (2637) | `CIELO EVAL-Oct16` |
| Ni | Ni-58 (2825) `LANL,ORNL EVAL-Aug12`; Ni-60 (2831), Ni-61 (2834), Ni-62 (2837), Ni-64 (2843) | `EVAL-Oct12` (T. Kawano, A. Kahler et al.) |
| Cr | Cr-50 (2425), Cr-52 (2431), Cr-53 (2434), Cr-54 (2437) | `LANL,ORNL EVAL-OCT97` (S. Chiba, M. Chadwick et al.) |
| Mo | 92 (4225) `EVAL-MAY 2011`; 94 (4231), 97 (4240) `JNDC,BNL EVAL-FEB05`; 95 (4234) `BNL,KAERI EVAL-DEC10`; 96 (4237), 98 (4243) `JNDC EVAL-AUG89`; 100 (4249) `CNDC EVAL-AUG00` | |
| Mn | Mn-55 (2525) | `IAEA Eval-Feb11` |
| Si | Si-28 (1425) `EVAL-DEC02`; Si-29 (1428), Si-30 (1431) `EVAL-JUN97` | LANL,ORNL |
| C | C-12 (625), C-13 (628) | `EVAL-AUG15` |
| P | P-31 (1525) | `LANL,LLNL EVAL-DEC97` |
| S | S-32 (1625), S-33 (1628), S-34 (1631), S-36 (1637) | `FUJI E.C. EVAL-MAY87` |

**Natural abundances** come from NIST "Atomic Weights and Isotopic Compositions" (fetched this session):
- W: 180 0.0012, 182 0.2650, 183 0.1431, 184 0.3064, 186 0.2843
- Fe: 54 0.05845, 56 0.91754, 57 0.02119, 58 0.00282
- Ni: 58 0.68077, 60 0.26223, 61 0.011399, 62 0.036346, 64 0.009255
- Cr: 50 0.04345, 52 0.83789, 53 0.09501, 54 0.02365
- Mo: 92 0.1453, 94 0.0915, 95 0.1584, 96 0.1667, 97 0.0960, 98 0.2439, 100 0.0982
- Si: 28 0.92223, 29 0.04685, 30 0.03092
- C: 12 0.9893, 13 0.0107
- S: 32 0.9499, 33 0.0075, 34 0.0425, 36 0.0001
- Mn-55 and P-31: 1

[VERIFIED: physics.nist.gov Compositions ascii2]

**Per-element one-group microscopic values at 14.1 MeV** (abundance-weighted; μ̄ is weighted by σ_el). Paste these into `nuclear_data.py` exactly as written. [VERIFIED: computed this session from the files above]

| Element | σ_t (b) | σ_el (b) | σ_nonel = σ_t−σ_el (b) | σ(n,2n) (b) | μ̄_lab elastic |
|---|---|---|---|---|---|
| W | 5.367 | 2.84245 | 2.5245 | 2.0727 | 0.920464 |
| Fe | 2.57208 | 1.16978 | 1.4023 | 0.4191 | 0.821381 |
| Ni | 2.70486 | 1.24823 | 1.4566 | 0.1619 | 0.82251 |
| Cr | 2.41505 | 1.05993 | 1.3551 | 0.3426 | 0.829759 |
| Mo | 4.07235 | 2.28007 | 1.7923 | 1.1701 | 0.851513 |
| Mn | 2.47933 | 1.14606 | 1.3333 | 0.6868 | 0.814957 |
| Si | 1.8079 | 0.717912 | 1.0900 | 0.0255 | 0.752766 |
| C | 1.32159 | 0.832494 | 0.4891 | 0 | 0.622879 |
| P | 1.87835 | 0.96125 | 0.9171 | 0.0108 | 0.728879 |
| S | 1.73681 | 0.761595 | 0.9752 | 0.0121 | 0.649242 |

Spot checks per isotope (b): W-184 has σ_t 5.3863, σ_el 2.8672, σ_inel 0.4220, σ(n,2n) 2.0909, σ_γ 0.0007. Fe-56 has σ_t 2.5760, σ_el 1.1732, σ_inel 0.7790, σ(n,2n) 0.4316. These are consistent with the well-known ~5.4 b (W) and ~2.5 b (Fe) totals at 14 MeV [ASSUMED: literature recall, consistent].

Energy sensitivity is small. Between 14.0 and 14.2 MeV, Σ_t moves less than 0.3% and the uncollided T moves less than 0.5%, so 14.1 MeV is not a fragile choice. [VERIFIED: recomputed at 14.0 and 14.2 MeV]

**Compositions:**
- **WHA:** 97 W / 2 Ni / 1 Fe wt%, ρ = 18.5 g/cm³. Rizzi et al., arXiv:2603.03893, "Thermal modeling of runaway electron induced damage in the SPARC tokamak", says "The panel is made up of W heavy alloy (WHA) with a composition of 97% W, 2% Ni, 1% Fe" and "the room temperature value of 18.5 g/cm3 was used". [CITED: arxiv.org/html/2603.03893v1] This is consistent with ASTM B777 Class 4 (97% W, 18.25–18.85 g/cc). [CITED: gsalloy.com ASTM B777 table]
- **316 SS:** PNNL-15870 Rev. 2 (April 2021), entry 333 "Steel, Stainless 316". Density 8 g/cm³. Weight fractions C 0.000800, Mn 0.020000, P 0.000450, S 0.000300, Si 0.010000, Cr 0.170000, Ni 0.120000, Mo 0.025000, Fe 0.653450. Total 8.713E-02 atoms/b-cm. [VERIFIED: PNNL-15870Rev2.pdf, p. 227, read this session]

**Atom densities** (atoms/b-cm) follow N = ρ·w·N_A/M·1e-24:
- SS316: Fe 0.056373, Cr 0.015751, Ni 0.009850, Mo 0.001255, Mn 0.001754, Si 0.001715, total 0.08713. This matches PNNL's printed values digit for digit. [VERIFIED]
- WHA: W 0.058783, Ni 0.003796, Fe 0.001995, total 0.06457.

**Macroscopic one-group Σ (cm⁻¹) and mean free paths:**

| Quantity | WHA 97W | SS316 |
|---|---|---|
| Σ_t (true total, MT1) | 0.33089 (mfp 3.022 cm) | 0.22287 (mfp 4.487 cm) |
| Σ_el (MT2) | 0.17416 | 0.10141 |
| Σ_nonel = Σ_t − Σ_el | 0.15673 | 0.12147 |
| … of which (n,2n) | 0.12329 | 0.03333 |
| … of which inelastic MT4 | 0.02900 | 0.06273 |
| … of which capture MT102 | 0.00007 | 0.00007 |
| μ̄_lab effective | 0.9165 | 0.8221 |
| **Σ_tr = Σ_t − μ̄Σ_el (model total)** | **0.171276** (λ_tr 5.84 cm) | **0.139503** (λ_tr 7.17 cm) |
| **Σ_s,tr = (1−μ̄)Σ_el (model scatter)** | **0.014547** | **0.018036** |
| Model scatter ratio c | 0.084936 | 0.129285 |
| Optical thickness of the layer, true / transport | 2 cm: 0.662 / 0.343 | 8 cm: 1.783 / 1.116 |

Full-precision model values come from the constants above (transport-corrected): Σ_t,W = 0.1712763935199962, Σ_s,W = 0.014547480358451131, Σ_t,SS = 0.1395029186699459, Σ_s,SS = 0.018035691288369696. The raw-isotropic values are Σ_t,W = 0.3308900275980838, Σ_s,W = 0.1741611144365387, Σ_t,SS = 0.2228736475733168, Σ_s,SS = 0.10140642019174056. [VERIFIED: prototype run]

### One-group definitions (the disclosed approximation)

1. **The group is "14 MeV neutrons".** Elastic scattering keeps a neutron in the group. The maximum fractional energy loss is 4A/(A+1)², about 2% on W and about 7% on Fe, so an elastically scattered neutron is still a ~14 MeV neutron.
2. **"Absorption" means removal from the 14 MeV group.** That covers every non-elastic channel: inelastic, (n,2n), (n,3n), (n,p), (n,α) and capture. In formula form, Σ_a ≡ Σ_t − Σ_el. **(n,2n) is not double-counted.** Its secondary neutrons are emitted below ~7 MeV (the threshold is ~7.4 MeV on W), outside the group, so for a 14 MeV-group tally (n,2n) is exactly a removal. Real multiplication of lower-energy neutrons is out of scope (REQUIREMENTS.md) and is disclosed.
3. **Elastic anisotropy uses the transport correction:** Σ_tr = Σ_t − μ̄₀Σ_el, Σ_s,tr = (1−μ̄₀)Σ_el, with isotropic scattering in the model. This is the standard P1-preserving "extended transport approximation": a fraction μ̄₀ of elastic events is treated as straight-ahead, and the rest is isotropic. [CITED: standard reactor physics (Duderstadt & Hamilton, Lamarsh); flagged in .planning/research/PITFALLS.md Pitfall 11] Consequence: the model's "uncollided" means "not removed and not deflected in the P1 sense". Its T₀ = e^{−τ_tr} = 0.2326, while the true-uncollided e^{−τ_t} = 0.0867 is reported separately in the docs.
4. **Flatland isotropy.** Direction φ is uniform on [0, 2π) in the x-y plane. Both engines use it (ARCHITECTURE.md §1).

**Why the transport-corrected model.** Measured in this session, in 2D flatland, for 14 MeV-group back-face transmission:

| Model | T_all | T≤0 | T≤1 | T≤2 | K=1 coverage | K=2 coverage |
|---|---|---|---|---|---|---|
| Reference: real ENDF lab angular distribution, Σ_t, removal | **0.2290** | 0.0867 | 0.1697 | 0.2105 | 0.741 | 0.919 |
| **Transport-corrected (recommended)** | 0.2437 (+6.5%) | 0.2326 | 0.2430 | 0.2437 | **0.997** | **1.000** |
| Isotropic raw | 0.1224 (−46.5%) | 0.0867 | 0.1101 | 0.1184 | 0.899 | 0.967 |

(Continuous MC with exact free-flight sampling; 8e6 histories for the two model rows and 2e6 for the reference row, so SE ≤ 3e-4.) [VERIFIED: prototype run]

**K-coverage answer to the STATE.md Phase 2 blocker:**
- With the transport-corrected model, K=1 captures 99.7% of transmission. The Q1 circuit therefore estimates essentially the full model transmission, and the truncation bias is 0.3%.
- With raw isotropic, the Phase 1 "~90%" figure holds (89.9%).
- Truncation stays below 0.7% across thicknesses (transport-corrected): K=1 coverage is 0.9971 at 10 cm, 0.9955 at 15 cm, 0.9944 at 20 cm and 0.9929 at 30 cm.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.5.3 local / 2.4.6 on Qollab | Tables, Gauss-Legendre quadrature (`np.polynomial.legendre.leggauss`), `np.add.at` | Already a dependency; all APIs used exist in numpy 2.0+ [VERIFIED: venv import; QOLLAB-RUNTIME.md] |
| Python stdlib (`dataclasses`, `math.fsum`, `json`, `hashlib`) | 3.14 | Frozen dataclasses, exact-ish summation, golden file, spec fingerprint | No dependency cost; Pyodide-safe |
| pytest | 9.1.1 | Contract tests | Already installed [VERIFIED: venv] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit (`Statevector`, `StatePreparation`, `UCRYGate`) | 2.5.2 | *Optional* test: enumeration equals the statevector per bit string | Only in `tests/`, and only if the planner wants an early de-risk for Phase 4 (QC-03 owns it formally) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Constants in `nuclear_data.py` | `data/cross_sections.json` | It must then be loaded by a literal path from code `main.py` reaches, or `test_every_data_file_is_referenced_by_literal_path` fails. That brings cwd-relative path fragility in tests and Pyodide. Rejected. |
| `fractions.Fraction` exact arithmetic | float64 + `math.fsum` | The probabilities contain `exp(·)`, which is irrational, so Fractions cannot represent them. float64 with fsum reaches ~1e-16, far below the 1e-12 contract tolerance. |
| `openmc.data` / NJOY to get one-group data | Hand parser of ENDF MF3/MF4 (scratch script) | OpenMC is not installed and is a heavy dependency. Point values at 14.1 MeV need only TAB1 interpolation. |

**Installation:** none. No new packages.

## Package Legitimacy Audit

No external packages are installed in this phase. Everything uses numpy, stdlib and the already-pinned qiskit 2.5.2.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 ENDF/B-VIII.0 files ─┐   (dev-only, scripts/derive_cross_sections.py, network)
 NIST abundances ─────┼──► per-element σ_t, σ_el, μ̄ @14.1 MeV ──► neutron_qae/nuclear_data.py (constants + provenance)
 PNNL-15870 / Rizzi ──┘                                                │
                                                                       ▼
                                   problem.one_group(ρ, wt%, model) ──► Material(σ_t, σ_s)  [transport_corrected | isotropic_raw]
                                                                       │
                                   problem.ProblemSpec (frozen: geometry, beam, n_dir, materials)
                                          │                      │                         │
                                          ▼                      ▼                         ▼
                              kernels.build_kernels(spec)   Phase 3 continuous MC     docs/PHYSICS.md (table)
                                          │                 (same Material numbers)
                       Kernels (frozen v1): first_collision[17], scatter_ratio[16],
                       flight[16,16,4], back_exit_rows[16,16,16]
                          │                   │                         │
                          ▼                   ▼                         ▼
              exact.transmission_within   Phase 3 discrete MC     Phase 4 build_A (StatePreparation/UCRY)
              (2^11 bit strings → T0, T1)  (samples same tables)   flag prob must equal T1 to 1e-12
                          │
                          ▼
              tests/golden/kernels_v1.json (frozen values, rtol 1e-12) ── gates Phases 3, 4, 5
```

### Recommended Project Structure
```
neutron_qae/
├── nuclear_data.py   # constants: MICRO_14MEV, ATOMIC_WEIGHT, WHA_97W, SS316, PROVENANCE (citations, MAT, EVAL dates)
├── problem.py        # Material, ProblemSpec (frozen), atom_densities, one_group, sparc_first_wall, spec_fingerprint
├── kernels.py        # KERNELS_CONTRACT_VERSION="1", outcome constants, Kernels (frozen, eq=False), build_kernels
└── exact.py          # bitstring_probabilities_k1, transmission_within(k, K) for K in {0,1}, exit_row_distribution_k1
tests/
├── test_nuclear_data.py       # PNNL atom densities, mfp sanity, provenance present
├── test_problem.py            # PHYS-01 geometry + column-3 boundary test
├── test_kernels_contract.py   # conservation, symmetry, frozen, golden comparison
├── test_exact.py              # enumeration == closed form, total prob == 1, golden T0/T1
└── golden/kernels_v1.json     # written by scripts/freeze_kernels.py (~115 KB)
scripts/
├── freeze_kernels.py          # regenerates golden (an explicit contract change)
└── derive_cross_sections.py   # optional: ENDF download+parse; reproduces MICRO_14MEV
docs/PHYSICS.md                # cross-section table, citations, one-group definitions, model comparison
```
Keep the modules flat. Do not create subpackages (see the pyproject constraint). **Do not touch `main.py` in this phase.** Nothing new needs to be reachable yet, and Phase 6 wires the modules in.

### Pattern 1: `ProblemSpec` defined once, frozen and validated
- `@dataclass(frozen=True)` with fields `front, back, width_x=10.0, height_y=10.0, nx=16, ny=16, boundary_x=2.0, beam_y=5.0, n_dir=16`. Derived properties `dx` and `dy`. Methods `material_at(x)`, `tau_x(x)` and `column_segments(j)`.
- `__post_init__` validates: `0 < boundary_x < width_x`, `0 < beam_y < height_y`, and for each material `0 ≤ σ_s ≤ σ_t`, `σ_t > 0`.
- Factory `sparc_first_wall(model="transport_corrected", **overrides)`. Overrides such as `width_x=20.0` give the ANLY-04 thickness variants for free, because the kernels are generic in geometry.
- `spec_fingerprint(spec)` returns `sha256(json.dumps(dataclasses.asdict(spec), sort_keys=True))`. The inputs are deterministic IEEE sums of literal constants, so the hash is stable across platforms. Store it in the golden file.

### Pattern 2: Coordinates and indexing convention (state it in docstrings)
- x is depth into the wall: x=0 is the plasma face and x=10 the back face. y is lateral, 0..10.
- **Column j (0-based) spans [j·dx, (j+1)·dx), with dx = 0.625 cm (exact in binary).** The 2.0 cm interface is at 3.2 columns, i.e. inside 0-based column 3 = **"column 4" in the ROADMAP's 1-based wording**. Column 3 holds 0.125 cm WHA (20%) and 0.5 cm SS (80%).
- Source: a pencil beam at y = 5.0 cm, normally incident at x = 0 (the Q1 design). Uncollided neutrons exit the back face at y = 5.0. With the row rule `row = min(floor(y/dy), ny−1)` they land in row 8. Document this edge convention.
- Direction bin b covers φ ∈ [2πb/16, 2π(b+1)/16), with φ measured from +x toward +y. Bins 0-3 and 12-15 point forward. Bins 4-11 have cos φ ≤ 0 and give zero back escape. Mirror symmetry holds: `flight[:, b] == flight[:, 15−b]`.

### Pattern 3: Mixed column handled exactly (never snapped)
Inside a single material, τ is linear in x. Every per-column quantity is therefore a sum over the column's single-material sub-segments [a, b):
- `first_collision[j] = e^{−τ(x_j)} − e^{−τ(x_{j+1})}` (telescopes, so the 17 entries sum to exactly 1)
- `scatter_ratio[j] = Σ_seg c_seg·(e^{−τ(a)} − e^{−τ(b)}) / first_collision[j]` (the exact collision-weighted average)
- Prototype: c[3] = 0.11850355190070459 lies strictly between c_W = 0.0849 and c_SS = 0.1293.

### Pattern 4: Conditional-average kernels (why the discrete K=1 value is exact)
`flight[j, b, o] = P(outcome o | scattered in column j, φ in bin b)`, averaged over:
- (i) scatter sites inside column j, with density ∝ Σ_s(x)·e^{−τ(x)} (Gauss-Legendre, 24 nodes per material sub-segment); and
- (ii) φ uniform in bin b (Gauss-Legendre, 48 nodes per bin).

From a site (x, y0) the ray exits through the back, front or lateral face, whichever comes first. τ_ray = |τ(x_exit) − τ(x)|/|cos φ| is closed-form because Σ depends only on x. The neutron escapes with probability e^{−τ_ray} and otherwise collides again. Each node's four outcomes sum to 1, so each table row sums to 1 to about 1e-16. Because c[j]·flight[j,b,BACK] is exactly P(scatter ∧ escape | collide in j, bin b), we get T₁ = T₀ + Σ_j first[j]·c[j]·mean_b flight[j,b,BACK], which is **the continuous ≤1-collision transmission**. Quadrature error is about 1e-6; tables with (24,48) and (96,192) nodes differ by 7e-7. `back_exit_rows[j,b,i]` uses the same nodes to bin the exit y. That gives the exact K=1 exit histogram for ANLY-02 at no qubit cost.

### Pattern 5: Exact solver as literal bit-string enumeration (PHYS-06)
- Random registers (Q1 order, little-endian, matching Qiskit qubit indices 0..10): **x (5 bits)**, a (1), φ (4), e (1). That is 2^11 = 2048 strings, of which 17·2·16·2 = 1088 can be non-zero.
  - x is the first-collision column 0..15, or 16 = uncollided; x = 17..31 has amplitude 0.
  - a = 1 means scatter, with P = c[x mod 16].
  - φ is the bin, uniform 1/16.
  - e = 1 means escape through the back face, with P = flight[x mod 16, φ, BACK].
  - T = (x == 16) ∨ (a ∧ e).
- **x = 16 mirrors column 0's rotations**, because a UCRY controlled on x[0:4] sees 0000. The enumeration reproduces this so that per-bit-string probabilities match the circuit. This was verified with a Qiskit `Statevector`: max difference 6e-15, P(T=1) difference 3.5e-15. [VERIFIED: prototype]
- `transmission_within(k, 0) = first_collision[16]`. `transmission_within(k, 1) = fsum(p for strings with T)`. For K ≥ 2, raise ValueError ("contract v1 supports K ≤ 1"). Rationale:
  - in the transport-corrected model K=2 adds only 0.0007 absolute, about 0.3% of T (continuous MC: T≤2 = 0.24370 vs T≤1 = 0.24303);
  - a 2D K=2 lattice needs a next-collision cell register (256 cells + 3 exits ≈ 9 bits). That makes 25 random bits plus a flag, which is over 24 qubits; the old Q2 design coarsened to 8 bins and column-only flights;
  - K=2 is QC-08, which is v2.
- State-space sizes: K=1 has 2^11 strings. A cell-resolved K=2 has 5+1+4+9+1+4+1 = 25 bits (2^25 ≈ 33.5M strings, ≤ 9.0M non-zero), which is feasible classically as a tensor contraction but is a contract change.

### Pattern 6: Freezing the contract
- `KERNELS_CONTRACT_VERSION = "1"` lives in `kernels.py`.
- `scripts/freeze_kernels.py` writes `tests/golden/kernels_v1.json` with: version, `spec_fingerprint`, `asdict(spec)`, the four tables as nested lists (`repr` floats round-trip exactly), T0 and T1.
- `tests/test_kernels_contract.py` rebuilds and compares with `np.testing.assert_allclose(rtol=1e-12, atol=1e-15)`. It asserts the fingerprint and version, and that T1 equals the golden value to 1e-12.
- **Do not hash the output float bytes.** `leggauss` goes through LAPACK eigenvalues and libm `exp`, which can differ in the last ulp between macOS and Pyodide or Linux.
- The golden file goes in `tests/golden/`, **not `data/`**. Files in `data/` must be referenced from `main.py`-reachable code, while `tests/` is export-ignored and never uploaded.
- Make the arrays read-only in `__post_init__` with `a.setflags(write=False)`. Use `@dataclass(frozen=True, eq=False)`. The default `eq=True` would compare tuples of arrays and raise "truth value of an array is ambiguous".

### Anti-Patterns to Avoid
- **Snapping the boundary** to x = 1.875 or x = 2.5, or using one material per column. This fails PHYS-01. The test asserts both snapped values differ from τ₃ by more than 1e-3.
- **Midpoint-only escape tables** (column centre, bin-centre angle). They are acceptable as a model but bring a ~1% K=1 discretisation bias that must then be explained. Conditional averaging removes it at no qubit cost.
- **Putting K=2 tables into v1 "just in case".** That enlarges the frozen surface, and the transport-corrected K=2 contribution is about 0.3% of T.
- **Importing qiskit in `kernels.py`, `problem.py` or `exact.py`.** Phase 3 must stay qiskit-free, and Pyodide import time matters.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gauss-Legendre nodes and weights | Your own node generator | `np.polynomial.legendre.leggauss(n)` | Exact, in numpy since 1.x, Pyodide-safe |
| Accurate summation of 2048 products | A naive `sum` | `math.fsum` | Error-free, so the 1e-12 contract has headroom |
| Isotopic abundances, atomic weights | Memory | NIST table values (above) | Already verified this session |
| 316 SS composition | "Typical" spec ranges | PNNL-15870 Rev. 2 entry 333 | An authoritative radiation-transport compendium; atom densities checkable to 6 digits |
| A one-group transport model | An ad-hoc anisotropy fudge | Transport correction Σ_tr = Σ_t − μ̄Σ_el | Textbook, P1-preserving, and measured here at +6.5% vs the ENDF-angular reference |

**Key insight:** every K=1 table is a conditional probability that has a closed form or a smooth integral. Compute them by quadrature once in `build_kernels`, and the three consumers (exact, discrete MC, circuit) cannot disagree.

## Common Pitfalls

### Pitfall 1: barn ↔ cm² and the number-density chain
**What goes wrong:** Σ comes out 1e24 times too big, or wt% gets used as atom%. **Avoid:** N[atoms/b-cm] = ρ·w·N_A/M·1e-24, then Σ[cm⁻¹] = N[atoms/b-cm]·σ[b]. Test the result against PNNL: Fe 0.056373, Cr 0.015751, Ni 0.009850 and total 8.713e-2. **Warning sign:** an mfp that is not about 3 cm in W and about 4.5 cm in SS.

### Pitfall 2: Thermal or resonance values instead of 14 MeV
W thermal capture is about 18 b, while at 14.1 MeV it is 0.0007 b. Use the 14.1 MeV MF3 values only. 14.1 MeV is above every resolved and unresolved resonance range, so MF3 is the full cross section there.

### Pitfall 3: Double-counting (n,2n), or counting it as scattering
Treating (n,2n) as "scatter with multiplicity 2" in a one-group 14 MeV tally overstates transmission. Its secondaries are below 7 MeV. Removal is the correct one-group 14 MeV treatment, so state it as such.

### Pitfall 4: Isotropic scattering with raw Σ_el
This halves the transmission (0.122 vs a 0.229 reference). Use the transport correction, or, if raw is chosen, disclose the −46% physics bias.

### Pitfall 5: Contract tests on float bytes, or golden files in `data/`
See Pattern 6. Byte hashes break across platforms, and `data/` files break the Phase 1 literal-path gate.

### Pitfall 6: Frozen dataclass holding mutable numpy arrays
`frozen=True` blocks rebinding an attribute but not `k.flight[0,0,0] = 1`. Use `setflags(write=False)` and `eq=False`. A test asserts that mutation raises.

### Pitfall 7: The uncollided state in the circuit is not "inert"
For x = 16 the a and e registers still rotate (as column 0). Probability tests over individual bit strings must mirror that. Only P(T) is unaffected.

### Pitfall 8: The beam on a row boundary
y0 = 5.0 sits exactly on the boundary between rows 7 and 8. Fix the row rule (floor) and test it. Otherwise exit histograms flip asymmetrically between implementations.

### Pitfall 9: Python.org framework Python has no CA bundle
`urllib` calls to `www.nndc.bnl.gov` fail with `CERTIFICATE_VERIFY_FAILED` on this Mac. Any derivation script must run with `SSL_CERT_FILE=/etc/ssl/cert.pem` (observed this session). That script is dev-only and must never run in Qollab, which allows GET only.

### Pitfall 10: Comparing T against the wrong "uncollided"
In the transport-corrected model T₀ = e^{−τ_tr} = 0.2326. The physical uncollided flux is e^{−τ_t} = 0.0867. Phase 3's PHYS-04 test must use the model's τ (from `ProblemSpec`), and the docs must label both.

## Code Examples

Verified prototype (scratchpad `clean/`, 7/7 tests pass, 2026-10-10). Copy it, renaming as needed.

```python
# neutron_qae/problem.py (core)
@dataclass(frozen=True)
class Material:
    name: str
    sigma_t: float   # model total, 1/cm
    sigma_s: float   # model isotropic scattering, 1/cm
    @property
    def scatter_ratio(self) -> float: return self.sigma_s / self.sigma_t

def atom_densities(rho, wfrac):                      # atoms / (barn cm)
    return {el: rho * w * nd.AVOGADRO / nd.ATOMIC_WEIGHT[el] * nd.BARN_CM2 for el, w in wfrac.items()}

def one_group(name, rho, wfrac, model="transport_corrected"):
    n = atom_densities(rho, wfrac)
    sig_t = sum(n[e] * nd.MICRO_14MEV[e][0] for e in n)
    sig_el = sum(n[e] * nd.MICRO_14MEV[e][1] for e in n)
    mu_sig_el = sum(n[e] * nd.MICRO_14MEV[e][1] * nd.MICRO_14MEV[e][2] for e in n)
    if model == "transport_corrected":
        return Material(name, sig_t - mu_sig_el, sig_el - mu_sig_el)
    if model == "isotropic_raw":
        return Material(name, sig_t, sig_el)
    raise ValueError(model)

# ProblemSpec.tau_x / column_segments
def tau_x(self, x):
    x = np.asarray(x, dtype=float)
    return self.front.sigma_t * np.minimum(x, self.boundary_x) + self.back.sigma_t * np.maximum(x - self.boundary_x, 0.0)

def column_segments(self, j):
    x0, x1 = j * self.dx, (j + 1) * self.dx
    if x1 <= self.boundary_x: return [(x0, x1, self.front)]
    if x0 >= self.boundary_x: return [(x0, x1, self.back)]
    return [(x0, self.boundary_x, self.front), (self.boundary_x, x1, self.back)]
```

```python
# neutron_qae/kernels.py (core of build_kernels; BACK, FRONT, LATERAL, COLLIDE = 0, 1, 2, 3)
edges = np.exp(-spec.tau_x(np.arange(nx + 1) * spec.dx))
first = np.empty(nx + 1); first[:nx] = edges[:-1] - edges[1:]; first[nx] = edges[-1]
gx, gwx = np.polynomial.legendre.leggauss(24); gp, gwp = np.polynomial.legendre.leggauss(48)
dphi = 2.0 * math.pi / nd_
for j in range(nx):
    scat, xs, ws = 0.0, [], []
    for a, b, m in spec.column_segments(j):
        scat += m.scatter_ratio * (math.exp(-spec.tau_x(a)) - math.exp(-spec.tau_x(b)))
        xn = 0.5 * (b - a) * gx + 0.5 * (a + b)
        xs.append(xn); ws.append(0.5 * (b - a) * gwx * m.sigma_s * np.exp(-spec.tau_x(xn)))
    ratio[j] = scat / first[j]
    xs = np.concatenate(xs); ws = np.concatenate(ws); ws /= ws.sum()
    for bb in range(nd_):
        phi = (bb + 0.5 * (gp + 1.0)) * dphi
        X, P = np.meshgrid(xs, phi, indexing="ij"); W = np.outer(ws, 0.5 * gwp)
        cx, sy = np.cos(P), np.sin(P)                       # Gauss nodes avoid cos=0 / sin=0
        sx = np.where(cx > 0, (spec.width_x - X) / cx, -X / cx)
        sl = np.where(sy > 0, (spec.height_y - spec.beam_y) / sy, -spec.beam_y / sy)
        s = np.minimum(sx, sl)
        esc = np.exp(-np.abs(spec.tau_x(X + s * cx) - spec.tau_x(X)) / np.abs(cx))
        face = np.where(sx <= sl, np.where(cx > 0, BACK, FRONT), LATERAL)
        for f in (BACK, FRONT, LATERAL):
            flight[j, bb, f] = np.sum(W * esc * (face == f))
        flight[j, bb, COLLIDE] = np.sum(W * (1.0 - esc))
        hit = face == BACK
        row = np.clip(((spec.beam_y + s * sy) / spec.dy).astype(int), 0, ny - 1)
        np.add.at(rows[j, bb], row[hit], (W * esc)[hit])
```

```python
# neutron_qae/exact.py
def bitstring_probabilities_k1(k):
    nx, nd_ = k.spec.nx, k.spec.n_dir          # 16, 16
    out = []
    for s in range(2 ** 11):                   # x(5) | a<<5 | phi<<6 | e<<10
        x, a, phi, e = s & 31, (s >> 5) & 1, (s >> 6) & 15, (s >> 10) & 1
        if x > nx: continue
        col = x % nx                           # x=16 rotates a/e like column 0 (circuit mirror)
        c = float(k.scatter_ratio[col]); q = float(k.flight[col, phi, BACK])
        p = float(k.first_collision[x]) * (c if a else 1 - c) / nd_ * (q if e else 1 - q)
        out.append((s, p, x == nx or (a == 1 and e == 1)))
    return out

def transmission_within(k, K):
    if K == 0: return float(k.first_collision[-1])
    if K == 1: return math.fsum(p for _, p, t in bitstring_probabilities_k1(k) if t)
    raise ValueError("contract v1 supports K in {0, 1}; K=2 is a contract change (QC-08, v2)")
```

```python
# tests: the boundary test (PHYS-01) and conservation (PHYS-05), both passing in the prototype
def test_boundary_inside_column_3_not_snapped():
    assert [(a, b) for a, b, _ in SPEC.column_segments(3)] == [(1.875, 2.0), (2.0, 2.5)]
    tau3 = SPEC.tau_x(2.5) - SPEC.tau_x(1.875); W, S = SPEC.front.sigma_t, SPEC.back.sigma_t
    assert tau3 == pytest.approx(0.125 * W + 0.5 * S, rel=1e-14)
    assert abs(tau3 - 0.625 * W) > 1e-3 and abs(tau3 - 0.625 * S) > 1e-3
    cw, cs, a = SPEC.front.scatter_ratio, SPEC.back.scatter_ratio, 0.125 * W
    expect = (cw * (1 - math.exp(-a)) + cs * math.exp(-a) * (1 - math.exp(-0.5 * S))) / (1 - math.exp(-tau3))
    assert K.scatter_ratio[3] == pytest.approx(expect, rel=1e-13)

def test_probability_conserved():
    assert math.fsum(K.first_collision) == pytest.approx(1.0, abs=1e-14)
    assert np.abs(K.flight.sum(-1) - 1).max() < 1e-13
    assert np.abs(K.back_exit_rows.sum(-1) - K.flight[..., BACK]).max() < 1e-13
    assert math.fsum(p for _, p, _ in bitstring_probabilities_k1(K)) == pytest.approx(1.0, abs=1e-14)
    assert np.abs(K.flight - K.flight[:, ::-1]).max() < 1e-14 and np.all(K.flight[:, 4:12, BACK] == 0)
```

**Reference values the executor must reproduce** (transport-corrected, 24/48 nodes):

| Quantity | Value |
|---|---|
| τ_total | 1.4585761363995597 |
| T₀ | 0.23256718303628812 |
| T₁ | 0.24300446519524305 |
| c[3] | 0.11850355190070459 |

Isotropic raw gives T₀ = 0.08674615049972412 and T₁ = 0.11006367028977174. The p_first vector (transport-corrected, rounded) is [0.10152 0.09121 0.08195 0.0632 0.05528 0.05067 0.04644 0.04256 0.03901 0.03575 0.03277 0.03003 0.02752 0.02522 0.02312 0.02119 | 0.23257]. Golden comparisons use rtol 1e-12 against the file generated by the executor's own code. These numbers are the cross-check that the code matches the research to ~1e-9.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ENDF/B-VII.1, elemental W/Fe evaluations | ENDF/B-VIII.0, isotopic only (CIELO Fe-56) | Feb 2018 | Must abundance-weight the isotopes; there is no natural-element file |
| Placeholder Σ (W 1/3, SS 1/6 cm⁻¹, c≈0.5) | ENDF-derived, transport-corrected Σ | This phase | K=1 coverage moves from ~90% to 99.7%; T₁ moves from 0.167 to 0.243 |

**Deprecated/outdated:** ENDF/B-VIII.1 exists [ASSUMED: released ~2024-2025]. The project requirement names VIII.0, so stay on VIII.0.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The **transport-corrected** one-group model is the default (user confirmation wanted; `isotropic_raw` stays selectable) | Nuclear Data, Summary | If the user prefers raw isotropic, T₁ becomes 0.110, K=1 coverage 90%, and docs must disclose a −46% physics bias. A one-argument switch, but golden values change. Lock before freezing. |
| A2 | The pencil beam at y = 5.0 cm, normal incidence, is the v1 source (matches the Q1 12-qubit design) | Pattern 2 | A uniform source (Q1-Y) would need a y-indexed escape table. That is v2. |
| A3 | 16 uniform direction bins (4 qubits). With conditional averaging, T₁ is bin-count independent; bins matter only for histograms and K≥2 | Pattern 4 | Phase 4 could drop the φ register entirely (an escape averaged per column, 8 qubits, far fewer CX) and keep T₁. Mention to the Phase 4 planner. |
| A4 | Contract v1 scope is K ∈ {0,1}; K=2 is a contract change | Pattern 5 | If Phase 5 wants a lattice-exact K=2 bar, add a v1.1 contract. Continuous MC tallies (Phase 3) already give T≤K for ANLY-03. |
| A5 | Literature totals (~5.4 b W, ~2.5 b Fe at 14 MeV) as plausibility only | Nuclear Data | None: the values were computed from the files. |
| A6 | ENDF/B-VIII.1 exists | State of the Art | None for this phase |

## Open Questions (RESOLVED — Q1: transport-corrected model locked by orchestrator, plan PD-01; Q2: derivation script included, plan 02-02 PD-07; Q3: owned by Phase 4 QC-03)

1. **Transport-corrected vs raw isotropic (A1).**
   - What we know: transport-corrected is 15× closer to the ENDF-angular reference.
   - What's unclear: whether the user wants the circuit's scatter branch to matter more for the narrative. In the transport-corrected model, scattering is 4% of T₁.
   - Recommendation: lock transport-corrected, and have docs/PHYSICS.md show the three-row model table above as a "physics model bias" disclosure.
2. **Should `scripts/derive_cross_sections.py` be committed this phase?**
   - Recommendation: yes if time permits, ~150 lines, dev-only. The working parser is in the scratchpad: `/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/scripts/{fetch_endf.py,endf_xs.py,mubar.py,macro.py}` (may be cleaned by the OS).
   - Otherwise the constants plus the citation table satisfy PHYS-02. A derivation script is "replication" polish for DOCS-03.
3. **Should a Qiskit statevector check go into Phase 2 tests?**
   - It is optional. It is verified here (6e-15 per bit string) and owned by QC-03 in Phase 4.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `.venv` | everything | ✓ | 3.14.8 | — |
| numpy | kernels | ✓ | 2.5.3 | — |
| qiskit | optional statevector test | ✓ | 2.5.2 | skip the test |
| pytest | tests | ✓ | 9.1.1 (36 existing tests pass) | — |
| qiskit-aer | not needed in Phase 2 | ✗ (not installed, despite `dev` extras) | — | Phase 4 must install it or use `Statevector` |
| Network to nndc.bnl.gov | only the optional derivation script | ✓ (needs `SSL_CERT_FILE=/etc/ssl/cert.pem`) | — | Constants are already computed here |

**Missing dependencies with no fallback:** none for Phase 2.

## Validation Architecture

Skipped: `workflow.nyquist_validation` is `false` in .planning/config.json. The test plan lives in Code Examples and Pattern 6. Quick run: `.venv/bin/python -m pytest -q tests/test_problem.py tests/test_kernels_contract.py tests/test_exact.py tests/test_nuclear_data.py` (under 1 s; the prototype suite runs in 0.09 s).

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (minor) | `ProblemSpec.__post_init__` / `Material.__post_init__` range checks; `transmission_within` rejects K ∉ {0,1} |
| V6 Cryptography | no | sha256 is used only as a content fingerprint, not for security |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered nuclear data from download (derivation script) | Tampering | HTTPS to nndc.bnl.gov only; record the sha256 of each parsed member in docs; parse as data with no `eval`; the script lives in export-ignored `scripts/` and never runs on Qollab |
| Silent contract drift between branches | Tampering/Repudiation | Golden file + version + spec fingerprint; regenerating needs an explicit `scripts/freeze_kernels.py` run, noted in the commit message |

## Sources

### Primary (HIGH confidence)
- ENDF/B-VIII.0 neutron sublibrary, NNDC zip `https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip`. 41 files parsed (MF1/451 headers, MF3 MT1/2/4/16/17/102/103/107, MF4 MT2) at 14.0, 14.1 and 14.2 MeV.
- NNDC ENDF/B-VIII.0 page: release 2018-02-02, Nucl. Data Sheets 148.
- PNNL-15870 Rev. 2 (April 2021), entry 333 Steel, Stainless 316 (p. 227), text extracted this session.
- NIST Atomic Weights and Isotopic Compositions (physics.nist.gov, ascii2).
- Rizzi et al., arXiv:2603.03893 (SPARC WHA 97W-2Ni-1Fe, 18.5 g/cm³): https://arxiv.org/html/2603.03893v1
- Repo files read this session: tests/compliance_checks.py, tests/test_compliance.py, pyproject.toml, .gitattributes, main.py, neutron_qae/__init__.py, docs/QOLLAB-RUNTIME.md, .planning/*.md.

### Secondary (MEDIUM confidence)
- ASTM B777 class table (distributor copy): https://gsalloy.com/product/astm-b777-tungsten-high-density-metal/
- Transport correction and removal concept: standard reactor-physics texts (not re-fetched).

### Tertiary (LOW confidence)
- ENDF/B-VIII.1 existence (training knowledge).

## Metadata

**Confidence breakdown:**
- Nuclear data: HIGH. Computed from primary files; atom densities match PNNL to 6 digits; insensitive to ±0.1 MeV.
- Model choice: HIGH on the numbers, MEDIUM on the preference. A1 needs user confirmation.
- Kernels/exact design: HIGH. The prototype passes conservation, boundary, symmetry and freeze tests. Exact T₁ matches the continuous MC (0.19 σ at 8e6 histories) and the Qiskit statevector (3.5e-15).
- Pitfalls: HIGH. Most were observed directly this session (SSL, eq=False, data/ gate, x=16 mirroring).

**Research date:** 2026-10-10
**Valid until:** end of hackathon (2026-10-11). The nuclear data do not change.
