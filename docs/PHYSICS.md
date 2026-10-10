# Physics record: SPARC first wall, one-group 14.1 MeV model

This file records the physics behind the project and the frozen classical/quantum contract. Every number here is printed from the code (`neutron_qae/nuclear_data.py`, `neutron_qae/problem.py`, `neutron_qae/kernels.py`, `neutron_qae/exact.py`), and `tests/test_physics_doc.py` fails if a cited value, a citation or a label drifts from the code. The code is the source of truth; this file explains it.

## Problem geometry and indexing

Conventions (decision PD-05), defined once in `ProblemSpec` and used by every engine:

- The wall is a 10 cm x 10 cm slab on a 16 x 16 grid, so dx = dy = 0.625 cm (exact in binary).
- x is depth through the wall: x = 0 is the plasma face and x = 10 cm the back face. y is lateral, 0 <= y <= 10 cm.
- Materials: 2.0 cm of tungsten heavy alloy (WHA) for 0 <= x < 2.0, then 8.0 cm of 316 stainless steel (SS316) for 2.0 <= x <= 10.0. `material_at` is half-open, so x = 2.0 is SS316.
- Columns are 0-based: column j spans [j dx, (j + 1) dx). The 2.0 cm interface lies inside index 3, which is the ROADMAP's 1-based "column 4". That column holds 0.125 cm of WHA and 0.5 cm of SS316 and is integrated exactly over its two sub-segments; it is never snapped to a column edge.
- Source: a pencil beam entering at (x = 0, y = 5.0), normal incidence (+x).
- Exit row of a back-face crossing at height y: `ProblemSpec.row_of(y)` = floor(y / dy), clipped to [0, 15]. The uncollided beam therefore exits in row 8 (y = 5.0 sits exactly on the edge between rows 7 and 8, and floor puts it in 8).
- Direction bin b covers phi in [2 pi b / 16, 2 pi (b + 1) / 16), with phi measured from +x toward +y. Bins 0-3 and 12-15 point forward; bins 4-11 cannot reach the back face.

## Nuclear data (ENDF/B-VIII.0, 14.1 MeV)

**Library.** ENDF/B-VIII.0, neutrons sublibrary, CSEWG release 2018-02-02; D. A. Brown et al., Nucl. Data Sheets 148, 1 (2018). Source: https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip. Method: MF3 MT1/MT2/MT16 interpolated at 14.1 MeV with each file's interpolation law; mubar_lab from MF4/MT2 with the exact CM-to-lab transform; natural-abundance weighting; mubar weighted by sigma_el.

**Per-element microscopic values at 14.1 MeV** (`MICRO_14MEV`, `SIGMA_N2N_14MEV`, `ATOMIC_WEIGHT`; atomic weights are IUPAC/NIST standard values). sigma(n,2n) is part of the removal sigma_t - sigma_el and is never treated as scattering.

| Element | sigma_t (b) | sigma_el (b) | sigma(n,2n) (b) | mubar_lab | atomic weight |
|---|---|---|---|---|---|
| C | 1.32159 | 0.832494 | 0.0 | 0.622879 | 12.011 |
| Si | 1.8079 | 0.717912 | 0.0255 | 0.752766 | 28.085 |
| P | 1.87835 | 0.96125 | 0.0108 | 0.728879 | 30.973761998 |
| S | 1.73681 | 0.761595 | 0.0121 | 0.649242 | 32.06 |
| Cr | 2.41505 | 1.05993 | 0.3426 | 0.829759 | 51.9961 |
| Mn | 2.47933 | 1.14606 | 0.6868 | 0.814957 | 54.938044 |
| Fe | 2.57208 | 1.16978 | 0.4191 | 0.821381 | 55.845 |
| Ni | 2.70486 | 1.24823 | 0.1619 | 0.82251 | 58.6934 |
| Mo | 4.07235 | 2.28007 | 1.1701 | 0.851513 | 95.95 |
| W | 5.367 | 2.84245 | 2.0727 | 0.920464 | 183.84 |

**Per-isotope provenance** (`PROVENANCE`): one row per ENDF/B-VIII.0 isotopic file behind the element values, with its MAT number, the evaluation string exactly as it appears in the file header, the evaluation date, and the natural abundance (mole fraction, `ABUNDANCE`; NIST Atomic Weights and Isotopic Compositions, physics.nist.gov). 36 isotopes.

| Isotope | MAT | Evaluation | Date | Abundance |
|---|---|---|---|---|
| C-12 | 625 | EVAL-AUG15 | 2015-08 | 0.9893 |
| C-13 | 628 | EVAL-AUG15 | 2015-08 | 0.0107 |
| Si-28 | 1425 | EVAL-DEC02 | 2002-12 | 0.92223 |
| Si-29 | 1428 | EVAL-JUN97 | 1997-06 | 0.04685 |
| Si-30 | 1431 | EVAL-JUN97 | 1997-06 | 0.03092 |
| P-31 | 1525 | LANL,LLNL EVAL-DEC97 | 1997-12 | 1.0 |
| S-32 | 1625 | FUJI E.C. EVAL-MAY87 | 1987-05 | 0.9499 |
| S-33 | 1628 | FUJI E.C. EVAL-MAY87 | 1987-05 | 0.0075 |
| S-34 | 1631 | FUJI E.C. EVAL-MAY87 | 1987-05 | 0.0425 |
| S-36 | 1637 | FUJI E.C. EVAL-MAY87 | 1987-05 | 0.0001 |
| Cr-50 | 2425 | LANL,ORNL EVAL-OCT97 | 1997-10 | 0.04345 |
| Cr-52 | 2431 | LANL,ORNL EVAL-OCT97 | 1997-10 | 0.83789 |
| Cr-53 | 2434 | LANL,ORNL EVAL-OCT97 | 1997-10 | 0.09501 |
| Cr-54 | 2437 | LANL,ORNL EVAL-OCT97 | 1997-10 | 0.02365 |
| Mn-55 | 2525 | IAEA Eval-Feb11 | 2011-02 | 1.0 |
| Fe-54 | 2625 | CIELO EVAL-DEC17; NDS 148, 214 (2018) | 2017-12 | 0.05845 |
| Fe-56 | 2631 | CIELO EVAL-DEC17; NDS 148, 214 (2018) | 2017-12 | 0.91754 |
| Fe-57 | 2634 | CIELO EVAL-Oct16 | 2016-10 | 0.02119 |
| Fe-58 | 2637 | CIELO EVAL-Oct16 | 2016-10 | 0.00282 |
| Ni-58 | 2825 | LANL,ORNL EVAL-Aug12 | 2012-08 | 0.68077 |
| Ni-60 | 2831 | EVAL-Oct12 | 2012-10 | 0.26223 |
| Ni-61 | 2834 | EVAL-Oct12 | 2012-10 | 0.011399 |
| Ni-62 | 2837 | EVAL-Oct12 | 2012-10 | 0.036346 |
| Ni-64 | 2843 | EVAL-Oct12 | 2012-10 | 0.009255 |
| Mo-92 | 4225 | EVAL-MAY 2011 | 2011-05 | 0.1453 |
| Mo-94 | 4231 | JNDC,BNL EVAL-FEB05 | 2005-02 | 0.0915 |
| Mo-95 | 4234 | BNL,KAERI EVAL-DEC10 | 2010-12 | 0.1584 |
| Mo-96 | 4237 | JNDC EVAL-AUG89 | 1989-08 | 0.1667 |
| Mo-97 | 4240 | JNDC,BNL EVAL-FEB05 | 2005-02 | 0.096 |
| Mo-98 | 4243 | JNDC EVAL-AUG89 | 1989-08 | 0.2439 |
| Mo-100 | 4249 | CNDC EVAL-AUG00 | 2000-08 | 0.0982 |
| W-180 | 7425 | IAEA Eval090806; NDS 148, 1 (2018) DIST-FEB18 | 2009-08-06 | 0.0012 |
| W-182 | 7431 | IAEA Eval090806; NDS 148, 1 (2018) DIST-FEB18 | 2009-08-06 | 0.265 |
| W-183 | 7434 | IAEA EVAL-AUG14 | 2014-08 | 0.1431 |
| W-184 | 7437 | IAEA Eval090806; NDS 148, 1 (2018) DIST-FEB18 | 2009-08-06 | 0.3064 |
| W-186 | 7443 | IAEA Eval090806; NDS 148, 1 (2018) DIST-FEB18 | 2009-08-06 | 0.2843 |

**Materials** (`WHA_97W`, `SS316`, `MATERIAL_SOURCES`; decision PD-02):

- **WHA 97W-2Ni-1Fe**, 18.5 g/cm3, weight fractions W 0.97, Ni 0.02, Fe 0.01. Source: Rizzi et al., arXiv:2603.03893 (thermal modeling of runaway-electron damage in the SPARC tokamak), which gives the SPARC first-wall panel as W heavy alloy with 97% W, 2% Ni, 1% Fe and a room-temperature density of 18.5 g/cm3. Consistent with ASTM B777 Class 4.
- **316 SS**, 8.00 g/cm3. Source: PNNL-15870 Rev. 2 (April 2021), entry 333 "Steel, Stainless 316", p. 227. Weight fractions: C 0.0008, Mn 0.02, P 0.00045, S 0.0003, Si 0.01, Cr 0.17, Ni 0.12, Mo 0.025, Fe 0.65345.

**Atom densities** (atoms/b-cm), N = rho w N_A / M x 1e-24:

- WHA: W 0.058783, Ni 0.003796, Fe 0.001995; total 0.06457.
- SS316: Fe 0.056373, Cr 0.015751, Ni 0.009850, Mo 0.001255, Mn 0.001754, Si 0.001715, C 0.000321, P 0.000070, S 0.000045; total 0.08713 (matches the values printed in PNNL-15870).

**Macroscopic one-group values** (1/cm) and mean free paths:

| Quantity | WHA 97W | SS316 |
|---|---|---|
| Sigma_t (true total, MT1) | 0.33089 (mfp 3.02 cm) | 0.22287 (mfp 4.49 cm) |
| Sigma_el (MT2) | 0.17416 | 0.10141 |
| Sigma_nonel = Sigma_t - Sigma_el (removal) | 0.15673 | 0.12147 |
| ... of which (n,2n) | 0.12329 | 0.03333 |
| ... of which inelastic MT4 | 0.02900 | 0.06273 |
| ... of which capture MT102 | 0.00007 | 0.00007 |
| mubar_lab, effective | 0.9165 | 0.8221 |
| Sigma_tr = Sigma_t - mubar Sigma_el (model total) | 0.171276 (mfp 5.84 cm) | 0.139503 (mfp 7.17 cm) |
| Sigma_s,tr = (1 - mubar) Sigma_el (model scatter) | 0.014547 | 0.018036 |
| Model scatter ratio c | 0.084936 | 0.129285 |
| Optical thickness of the layer, true / transport-corrected | 2 cm: 0.662 / 0.343 | 8 cm: 1.783 / 1.116 |

The split of the removal into (n,2n), inelastic and capture is from the research derivation and is shown for context only; the model uses the removal total Sigma_t - Sigma_el.

## One-group model

Definitions (decisions PD-01 and PD-03):

1. **The group is "14 MeV neutrons".** Elastic scattering keeps a neutron in the group: the maximum fractional energy loss is 4A/(A+1)^2, about 2% on W and about 7% on Fe.
2. **Absorption means removal from the 14 MeV group.** Every non-elastic channel (inelastic, (n,2n), (n,3n), (n,p), (n,alpha), capture) removes the neutron, so Sigma_a = Sigma_t - Sigma_el. (n,2n) is counted once, as a removal: its secondaries are born below about 7 MeV, outside the group. Multiplication of lower-energy neutrons is out of scope.
3. **Transport correction for elastic anisotropy:** Sigma_tr = Sigma_t - mubar * Sigma_el and Sigma_s,tr = (1 - mubar) * Sigma_el, with scattering then treated as isotropic. This is the P1-preserving extended transport approximation: a fraction mubar of elastic events is treated as straight-ahead and the rest as isotropic.
4. **Flatland isotropy.** The new direction phi is uniform on [0, 2 pi) in the x-y plane, in both engines.

**Model values** (printed from `sparc_first_wall()`, transport-corrected, the default and frozen model):

| Material | Sigma_t (1/cm) | Sigma_s (1/cm) | scatter ratio | removal Sigma_a (1/cm) |
|---|---|---|---|---|
| WHA 97W-2Ni-1Fe | 0.171276 | 0.014547 | 0.084936 | 0.15673 |
| SS316 | 0.139503 | 0.018036 | 0.129285 | 0.12147 |

Under `sparc_first_wall("isotropic_raw")` the totals are the evaluated ones, Sigma_t = 0.33089 (WHA) and 0.22287 (SS316), with Sigma_s = Sigma_el. The removal Sigma_a = 0.15673 and 0.12147 is identical in both models, because the transport correction subtracts the same mubar * Sigma_el from Sigma_t and Sigma_s.

**Model bias.** Back-face transmission of the 14 MeV group in 2D flatland, measured with a continuous Monte Carlo (exact free-flight sampling; 8e6 histories for the two model rows, 2e6 for the reference, standard error at most 3e-4):

| Model | T_all | T<=0 | T<=1 | T<=2 | K=1 coverage | K=2 coverage |
|---|---|---|---|---|---|---|
| Reference: ENDF lab angular distribution, Sigma_t, removal | 0.2290 | 0.0867 | 0.1697 | 0.2105 | 0.741 | 0.919 |
| Transport-corrected (used) | 0.2437 (+6.5%) | 0.2326 | 0.2430 | 0.2437 | 0.997 | 1.000 |
| Isotropic raw | 0.1224 (-46.5%) | 0.0867 | 0.1101 | 0.1184 | 0.899 | 0.967 |

The transport-corrected model is 15 times closer to the ENDF-angular reference than isotropic raw, which is why it is the frozen model. K=1 captures 99.7% of its transmission (coverage 0.997); under isotropic raw K=1 captures 89.9% (coverage 0.899).

**Two different "uncollided" numbers.** Keep them apart:

- The **model uncollided transmission** is T0 = exp(-tau_tr) = 0.2325671830, with tau_tr the transport-corrected optical depth of the wall from `ProblemSpec.tau_x`. This is what the model and both engines call "uncollided", and what Phase 3's uncollided check (PHYS-04) must compare against.
- The **physical uncollided transmission** is exp(-tau_t) = 0.0867, with the true total cross sections. It is the fraction of 14 MeV neutrons that cross the wall without any interaction. It is not a model output, and it must not be confused with T0.

## Kernels contract v1

`neutron_qae/kernels.py` defines `KERNELS_CONTRACT_VERSION = "1"` and `build_kernels(sparc_first_wall())`, the single source of the tables that the classical Monte Carlo samples and the quantum oracle encodes. The `Kernels` dataclass is frozen; its four tables are private read-only float64 copies (nx = 16 columns, n_dir = 16 direction bins, ny = 16 rows):

| Field | Shape | Meaning |
|---|---|---|
| `first_collision` | (17,) | `first_collision[j]` = P(first collision in column j) for the normally incident beam; `first_collision[16]` = P(uncollided to the back face). Sums to 1. |
| `scatter_ratio` | (16,) | `scatter_ratio[j]` = P(scatter given a collision in column j); in the interface column 3 it is the collision-weighted average of the two materials' ratios over its two sub-segments. |
| `flight` | (16, 16, 4) | `flight[j, b, o]` = P(outcome o given a scatter in column j into direction bin b). Each `flight[j, b, :]` sums to 1. |
| `back_exit_rows` | (16, 16, 16) | `back_exit_rows[j, b, i]` = P(leave the back face in row i given j, b), rows by `ProblemSpec.row_of`; sums over i to `flight[j, b, BACK]`. |

Outcome indices: `BACK, FRONT, LATERAL, COLLIDE = 0, 1, 2, 3`.

**Construction.** The flight tables are conditional averages, over the scatter-site density Sigma_s(x) exp(-tau(x)) inside column j (24 Gauss-Legendre x-nodes per material sub-segment) and over phi uniform inside bin b (48 Gauss-Legendre phi-nodes per bin). From each node the ray leaves through the back, front or lateral face, whichever comes first, and escapes with probability exp(-tau_ray). Because of this averaging, the discrete K=1 value equals the continuous at-most-one-collision transmission up to quadrature error (about 1e-6).

**Exact solver** (`neutron_qae/exact.py`). The Q1 register layout is `exact.REGISTER_LAYOUT`:

`x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10, little-endian (bit i = Qiskit qubit i)`

- x is the first-collision column 0-15, or 16 for uncollided; a = 1 means scatter; phi is the direction bin; e = 1 means the flight reaches the back face.
- The solver enumerates all 2048 bit strings literally; strings with x > 16 have amplitude 0, leaving 1088 kept.
- Mirror rule: x = 16 has low bits 0000, the same as column 0, so its a and e branches use column 0's `scatter_ratio[0]` and `flight[0, phi, BACK]`, exactly like the circuit's uniformly controlled rotations. Every x = 16 string counts as transmitted.
- Transmitted means T = (x == 16) or (a and e). The probabilities of transmitted strings are summed with `math.fsum`.
- `transmission_within(k, 0)` = T0 = 0.2325671830 and `transmission_within(k, 1)` = T1 = 0.2430044652. Contract v1 supports K in {0, 1}; K = 2 raises ValueError and is a contract change (QC-08, v2).

**Freeze.** The golden file `tests/golden/kernels_v1.json` holds the version, the spec fingerprint, the quadrature, the register layout, the four tables, T0, T1 and the exact K=1 exit-row histogram. `tests/test_kernels_golden.py` rebuilds the kernels and compares them at rtol 1e-12 / atol 1e-15, and checks the spec fingerprint (a sha256 of the `ProblemSpec` inputs, never of output floats).

**Consumers.**

- Phase 3: the discrete classical Monte Carlo samples exactly these tables and must converge to T1; its histograms use `ProblemSpec.row_of`.
- Phase 4: QC-03 compares the Q1 flag probability with T1 at 1e-12, using `exact.REGISTER_LAYOUT` for the qubit order.
- Phase 5: every reported error is measured against T1.

## Changing the contract

The contract is frozen. Any change to a table, the quadrature, the outcome order, the register layout or the problem inputs is a contract change. Procedure:

1. Bump `KERNELS_CONTRACT_VERSION` in `neutron_qae/kernels.py`.
2. Regenerate the golden file with `scripts/freeze_kernels.py --write --force`. The default mode (`.venv/bin/python scripts/freeze_kernels.py`) only checks and prints `GOLDEN OK kernels_v1.json`; `--write` alone refuses with exit 2 when the file exists.
3. Re-run the Phase 3 and Phase 4 contract tests (classical Monte Carlo and quantum oracle) against the new golden values.
4. Name the change and the new T1 in the commit message.

Docs and README describe contract v1; they never redefine it.

## Derivation and replication

How `MICRO_14MEV` and `SIGMA_N2N_14MEV` were derived from ENDF/B-VIII.0:

1. Read every isotopic file of each element (the 36 files in the provenance table).
2. Interpolate MF3 MT1 (total), MT2 (elastic) and MT16 ((n,2n)) at 14.1 MeV with each file's own interpolation law.
3. Compute mubar_lab for elastic scattering from MF4/MT2 with the exact CM-to-lab transform (the mean lab cosine of the angular distribution interpolated linearly in energy).
4. Weight the isotopes by natural abundance: sigma = sum a_i sigma_i, and mubar = sum a_i sigma_el,i mubar_i / sigma_el (weighted by sigma_el).
5. Atom densities N = rho w N_A / M x 1e-24 atoms/b-cm, then Sigma = sum N sigma per material.

The choice of 14.1 MeV is not fragile: moving the energy between 14.0 and 14.2 MeV changes Sigma_t by less than 0.3% and the uncollided transmission by less than 0.5%.

### Reproduce the constants

`scripts/derive_cross_sections.py` re-derives every `MICRO_14MEV` and `SIGMA_N2N_14MEV` value from the 36 isotopic files. It is optional and local-only: it lives in export-ignored `scripts/`, nothing in `neutron_qae` or `main.py` imports it, it never runs on Qollab, and it touches the network only with `--download` (HTTPS to www.nndc.bnl.gov, only the 36 named members of the ENDF/B-VIII.0 neutrons zip). It parses ENDF numbers with `float()` only. Keep the ENDF files in their own directory and run Python with `-I`.

With the files already on disk:

```bash
.venv/bin/python -I scripts/derive_cross_sections.py --endf-dir <dir> --check --sha256-table
```

To fetch the missing files first (python.org macOS builds need the system CA bundle):

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python -I scripts/derive_cross_sections.py --download <dir> --check --sha256-table
```

Expected last line (run on 2026-10-10 against the files listed below):

```text
MICRO_14MEV REPRODUCED (max rel dev 2.72e-06, max n2n abs dev 4.05e-05)
```

The script passes when every sigma_t, sigma_el and mubar_lab is within relative 1e-5 of `MICRO_14MEV` and every sigma(n,2n) within absolute 1e-4 of `SIGMA_N2N_14MEV`; the constants are the same derivation rounded to 6 significant figures (4 decimals for (n,2n)).

### Parsed file checksums (sha256)

The 36 files parsed for the run above, from the NNDC ENDF/B-VIII.0 neutrons zip (member directory `ENDF-B-VIII.0_neutrons/`):

| File | MAT | sha256 |
|---|---|---|
| n-006_C_012.endf | 625 | daa7901e0067f9ac6d9b2392514ba00e71e37d00c8a8ecbbde0620237815f981 |
| n-006_C_013.endf | 628 | abaa8cc34398e6ada0a8c451efd5eef1019a37c7a0a708a4280af71ab77621de |
| n-014_Si_028.endf | 1425 | 34031d6a70ca4fda8a39b4cb037d966bd8c2cdc0b2df885382a8be1a5df304ab |
| n-014_Si_029.endf | 1428 | f212f322a224d8cd2cc6d164ecba8f598e492d1f912b121043994b6ae096cfe1 |
| n-014_Si_030.endf | 1431 | 56a633f775a581c0ac51031694853f2cff5a00b5ee196d56dbbd930af56a2a04 |
| n-015_P_031.endf | 1525 | 1074533d30922be72a9c5f34ad7fd5e0224ff6b64eeb65eaae5a6e7d7125e807 |
| n-016_S_032.endf | 1625 | 7ba8a10068f1caea4f0eff17c38fa2a74ae6d62a180b3f2d4b027a9cc6e8a373 |
| n-016_S_033.endf | 1628 | e555b6e93b973b0a11ecbb04f9846b993f58c763d5c98de6ca05dae7eaf7c70b |
| n-016_S_034.endf | 1631 | aa8d9b591978ef8971c74b31d7f3b90478dcc62908e3b1677023293a3170caa1 |
| n-016_S_036.endf | 1637 | a992da4609efebeb4e341afec0b2ec0b35c8736269a968503b1b7f2740456579 |
| n-024_Cr_050.endf | 2425 | ad442e640e82c98d22be47b60e41820a0ff3aeb8868c38de17b8af0cd4eee739 |
| n-024_Cr_052.endf | 2431 | c42bee3cbc9171d2fb70f3fdf409faeebfc7d2d7ea12ebfc003e78410376aa14 |
| n-024_Cr_053.endf | 2434 | 41aee5af2f3d671ea8c857fc642cf3c6e80d56976f774b11dad6316daf87bdfb |
| n-024_Cr_054.endf | 2437 | 8cce14a7d12aacc82fbb1e0fc91c069daedf41063f02735e592fd1d3f3672a09 |
| n-025_Mn_055.endf | 2525 | d2e907cfabc7f0b8da89eef0ebaaedefe9d9eca49830a58eb5955df3107988ba |
| n-026_Fe_054.endf | 2625 | d5000c8d07900ff7e8022c55c81ce81ca5ee837a208227a90c60b22e8588cb76 |
| n-026_Fe_056.endf | 2631 | b8bb897c76f85f7a22a989949c5c353e6b6541278b555b88be3a53102184bbae |
| n-026_Fe_057.endf | 2634 | cdef054c5abbda7c740266cc01632c6b90ead02ec7d856630cab6906cfc96147 |
| n-026_Fe_058.endf | 2637 | 57b574915c9f552950f93f8c9fbe8c40335d704d85209f1a299df5fa6fa2194c |
| n-028_Ni_058.endf | 2825 | 098a3a11d5475aa9854f8275c4c25af608ffa937c38049733120b33203067b60 |
| n-028_Ni_060.endf | 2831 | 8aee9f9294ee39aaa1899256e535bf33d4b8aa974831a3ab54492bb35c14b248 |
| n-028_Ni_061.endf | 2834 | 119766f579c84a4f510d24eb6d129e2ab2651c433da78f23fc57ba18b30cc5b8 |
| n-028_Ni_062.endf | 2837 | f0740804e97e693da6bc801ba0fdb599f4779a18a753805bde1b13f2ed384b91 |
| n-028_Ni_064.endf | 2843 | 80454b9641844725a12e0a2dfb927c3adb84c029593e4ac7ef74f2b71049e2c1 |
| n-042_Mo_092.endf | 4225 | 46e8ecba129cd3e1663cca605645fcbdadd03c17daa882b60844bb782618c6f6 |
| n-042_Mo_094.endf | 4231 | ba6112ac44aa96235825f5196aa08e94a0161ea92415a25ccd05d11fda6a6e65 |
| n-042_Mo_095.endf | 4234 | 4126c7cd6647f27514d008970f1c9fbf68139692bbee149a639adecd0c929249 |
| n-042_Mo_096.endf | 4237 | e84ad36979f7bcef839c59c530e5ba8f5f2dfb14f98afc19cbec4cbd1b1ae6e2 |
| n-042_Mo_097.endf | 4240 | be2d15b8942911892fb46f7a3a65736a5079e53b5d1079e21dcbc786e21f4bf3 |
| n-042_Mo_098.endf | 4243 | 8f0ce9597cb4cfaace43e1264377d3cb274e2e59c61bec4fb23071fa5912f319 |
| n-042_Mo_100.endf | 4249 | 0d7fa0243df8d27c6c30d060981c6d2ace987d927b3a8a02f23d3073e1d765d0 |
| n-074_W_180.endf | 7425 | 653eda1cfdc03bd2c18d4f95ab12c3bd09fa826e723bd93f331d1407b301ebc1 |
| n-074_W_182.endf | 7431 | bdc5fcab5e1f1ae2e09b7647c06b1a79e74e9ae26b4420c93c8176ad43752d0d |
| n-074_W_183.endf | 7434 | a2c724526c67dbab4150a0e26542e8b2e25e6119c18a852ce4101496f4e091d4 |
| n-074_W_184.endf | 7437 | 2d09fbd182f5840344489d2f12c01abea5a8f553f6b8813becbd2880a1d9f30f |
| n-074_W_186.endf | 7443 | 65269bbefd5de35f1269cf227d3a33a6fb60ec152c9a668c0ee20e157f6a354d |

## Approximations disclosed

- **One energy group.** Only 14 MeV-group neutrons are tracked; elastic scattering keeps them in the group.
- **Removal treatment of (n,2n).** (n,2n) and every other non-elastic channel remove the neutron from the group. The lower-energy secondaries, and the multiplication they represent, are not modelled.
- **Transport correction instead of anisotropic scattering.** The forward-peaked elastic scattering is replaced by the transport-corrected isotropic model, which overestimates total transmission by +6.5% against the ENDF-angular reference (0.2437 vs 0.2290).
- **2D flatland.** Directions live in the x-y plane, not in 3D.
- **Pencil beam.** A single normally incident beam at y = 5.0 cm, not a distributed plasma source.
- **K <= 1 truncation.** The quantum circuit and the exact reference count at most one collision; in the transport-corrected model this misses 0.3% of the transmission (K=1 coverage 0.997).
