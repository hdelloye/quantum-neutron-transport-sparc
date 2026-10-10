---
phase: 02-problem-spec-kernels-contract
reviewed: 2026-10-10T23:38:20Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - docs/PHYSICS.md
  - neutron_qae/exact.py
  - neutron_qae/kernels.py
  - neutron_qae/nuclear_data.py
  - neutron_qae/problem.py
  - scripts/derive_cross_sections.py
  - scripts/freeze_kernels.py
  - tests/golden/kernels_v1.json
  - tests/test_exact.py
  - tests/test_kernels_contract.py
  - tests/test_kernels_golden.py
  - tests/test_nuclear_data.py
  - tests/test_physics_doc.py
  - tests/test_problem.py
  - README.md
findings:
  critical: 0
  warning: 8
  info: 9
  total: 17
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-10T23:38:20Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

I reviewed the Phase 2 problem specification, nuclear data, Kernels contract, exact solver, the derivation and freeze scripts, the golden file, the tests, PHYSICS.md and the README diff. Where a claim could be tested, I reproduced it in the scratchpad with the project venv (numpy 2.5.3). The suite passes (111 passed), and `scripts/freeze_kernels.py` check mode prints `GOLDEN OK`.

**What holds up (verified, not assumed):**
- **Core physics is right.** The barn to cm² and atom-density formula is correct: N = rho w N_A / M x 1e-24 atoms/b-cm, and Sigma = N sigma in 1/cm. The SS316 weight fractions sum to exactly 1. The first-collision column telescopes correctly. The interface column (0-based index 3) is split exactly at 2.0 cm, and its scatter ratio is the analytic collision-weighted average. The ray optical depth |delta tau_x| / |cos phi| is correct across the interface. T1 from the enumeration equals the closed form.
- **Hard rules hold.** `neutron_qae/__init__.py` and `main.py`/`smoke.py` import none of the new modules.
- **Doc numbers match the code.** I hand-checked the PHYSICS.md values against the code: atom densities, the (n,2n) split, mubar effective, optical thicknesses and 4A/(A+1)^2.
- **The T1 quadrature claim holds.** PHYSICS.md:151 says the K=1 quadrature error is "about 1e-6". Refining to 96 x-nodes and 768 phi-nodes moves T1 by 5.9e-7.

**What is defective:**
- **A false judge-facing claim.** PHYSICS.md says the chosen model is "15 times closer" to the reference. The doc's own table gives 7.25 times.
- **The immutability claim can be bypassed.** Any consumer can call `setflags(write=True)` on the "read-only" contract tables and then write to them.
- **No content validation in `Kernels`.** It accepts NaN or negative tables, and `build_kernels` silently produces NaN when exp underflows.
- **Fail-open replication gate.** In the derivation script, `--check` reports `MICRO_14MEV REPRODUCED` when derived values are NaN.
- **The `--download` path is not verified.** It never checks the sha256 table that PHYSICS.md records, and it does not restrict redirects.
- **The golden guard's `--force` escape hatch** overwrites the v1 golden in place under the same version. The documented change procedure also does not match how the golden path is derived.
- **Undisclosed per-entry flight error.** Per-entry flight values carry about 1e-3 absolute (2.5% relative) Gauss-Legendre error from the exit-face discontinuity inside each phi bin.
- **Undocumented y = beam_y assumption.** The flight tables assume every scatter site lies on the beam line, and the contract does not say so.

## Warnings

### WR-01: PHYSICS.md claims the frozen model is "15 times closer" to the reference; its own table gives 7.25 times

**File:** `docs/PHYSICS.md:131` (table at 127-129)
**Issue:** The doc says "The transport-corrected model is 15 times closer to the ENDF-angular reference than isotropic raw". The table four lines above gives reference 0.2290, transport-corrected 0.2437 (+6.5%) and isotropic raw 0.1224 (-46.5%). So |0.1224 - 0.2290| / |0.2437 - 0.2290| = 0.1066 / 0.0147 = **7.25**, not 15 (46.5 / 6.5 gives the same 7.2). The figure was carried over from `02-RESEARCH.md:512` without being recomputed.

This document is the honest-physics record that judges read, and it states (line 3) that "every number here is printed from the code" and that tests fail on drift. This number comes from no code, and no test covers it: `test_model_values_and_honest_labels` only substring-searches the three table values.
**Fix:**
```markdown
The transport-corrected model's error against the ENDF-angular reference is about 7 times smaller
than isotropic raw's (+6.5% vs -46.5%), which is why it is the frozen model.
```
Also add a test that recomputes the ratio from the table cells, or drop the multiplier entirely.

### WR-02: The "read-only" contract tables can be made writable again with `setflags(write=True)`

**File:** `neutron_qae/kernels.py:63-67`
**Issue:** `np.array(..., copy=True)` creates an array that owns its buffer. numpy lets an owning array turn its WRITEABLE flag back on, so the freeze is only advisory. I verified this on numpy 2.5.3: `k.flight.setflags(write=True); k.flight[0,0,0] = 123.0` succeeds and mutates the shared contract object that Phase 3 and Phase 4 both import. The docstring (lines 43-45) and PHYSICS.md:140 promise "private read-only float64 copies".
**Fix:** Expose a view of a locked base. numpy refuses to make such a view writable (verified: "cannot set WRITEABLE flag to True of this array"):
```python
arr = np.array(getattr(self, name), dtype=np.float64, copy=True)
...
arr.setflags(write=False)
view = arr.view()          # base is read-only -> view can never be made writable
object.__setattr__(self, name, view)
```
Add `with pytest.raises(ValueError): K.flight.setflags(write=True)` to `test_kernels_frozen_and_read_only`.

### WR-03: `Kernels` validates only shapes; NaN, negative and non-normalised tables are accepted, and `build_kernels` emits NaN on underflow

**File:** `neutron_qae/kernels.py:54-67`, `neutron_qae/kernels.py:93-95`
**Issue:**
- **Construction accepts garbage.** `Kernels(spec, -ones(17), 5*ones(16), full(nan), zeros)` constructs without error. `transmission_within` then returns T0 = -1.0 and T1 = nan (verified).
- **Underflow produces NaN.** For any spec where exp(-tau) underflows (for example `sparc_first_wall(width_x=6000.0)`), `first[j]` becomes 0. Then `ratio[j] = scat / first[j]` and `ws / ws.sum()` become 0/0 = NaN, and the tables silently contain NaN (verified).
- **The spec is never checked.** `Kernels` does not check that `spec` is a `ProblemSpec`, and `ProblemSpec` does not check that `front` and `back` are `Material`s.

The contract is the only interface between three phases, and Phase 4 may load it from serialized values. Its constructor should enforce the invariants that the docstring states (sums to 1, values in [0, 1], finite).
**Fix:** In `__post_init__`, after the shape check:
```python
if not np.all(np.isfinite(arr)) or np.any(arr < 0) or np.any(arr > 1 + 1e-12):
    raise ValueError(f"Kernels.{name} must be finite probabilities in [0, 1]")
```
then add cross-table checks: `abs(fsum(first_collision) - 1) < 1e-12`, `flight.sum(-1) ~ 1`, and `back_exit_rows.sum(-1) ~ flight[..., BACK]`. In `build_kernels`, raise a clear `ValueError` when any `first[j] == 0`.

### WR-04: `derive_cross_sections.py --check` fails open on NaN and prints "MICRO_14MEV REPRODUCED"

**File:** `scripts/derive_cross_sections.py:253-261` (and `fnum` at 48-53)
**Issue:** `check()` builds `rel = max(...)` and tests `rel > REL_TOL or dev > N2N_ABS_TOL`. Every comparison with NaN is False, and Python's `max(0.1, nan)` returns 0.1, so NaN is silently dropped or kept depending on argument order. I verified this by setting `W.mubar_lab = nan` and `Fe.sigma_n2n = nan`: `check()` returned `(0.0, 0.0, [])`, printed "0.00e+00" for W, and `main` would print `MICRO_14MEV REPRODUCED`.

NaN is reachable in two ways:
- `fnum` passes untrusted fields to `float()`, which accepts `"nan"` and `"inf"`.
- `means()` divides by `norm`, which becomes 0 when the clipped pdf is all zero.

This is the provenance gate behind the "reproduced" line that PHYSICS.md:213 cites.
**Fix:**
```python
def fnum(s):
    ...
    v = float(s)
    if not math.isfinite(v):
        raise ValueError(f"non-finite ENDF field {s!r}")
    return v

# in check():
values = (d["sigma_t"] / sigma_t - 1, d["sigma_el"] / sigma_el - 1, d["mubar_lab"] / mu - 1)
if not all(math.isfinite(v) for v in values) or not math.isfinite(dev):
    bad.append(el); continue
```

### WR-05: `--download` never verifies the recorded sha256 checksums, follows unrestricted redirects and does not check that Range was honoured

**File:** `scripts/derive_cross_sections.py:171-191`, `207-218`, `282`; claim at `docs/PHYSICS.md:196`
**Issue:**
- **Recorded checksums are never compared.** PHYSICS.md records the sha256 of all 36 parsed files (lines 222-259) and says the network is used for "HTTPS to www.nndc.bnl.gov, only". The script only prints hashes (`--sha256-table`) and never compares them, so a substituted or corrupted file is parsed silently. Only the numeric `--check` stands between it and a false result, and WR-04 shows that check fails open.
- **Redirects are unrestricted.** `urllib.request.urlopen` follows redirects to any host and scheme (http, https, ftp) through the default `HTTPRedirectHandler`, so "www.nndc.bnl.gov only" is not enforced.
- **Range responses are unchecked.** `HttpFile.read` does not check for status 206 or a matching `Content-Range`. A server that ignores Range returns the whole archive, which makes `readinto` raise a confusing slice-size `ValueError`.
- **A missing header crashes.** A missing `Content-Length` raises `TypeError`.
**Fix:**
- Keep a `{file: sha256}` dict (in the script, or parsed from PHYSICS.md), verify each downloaded and each `--endf-dir` file before parsing, and refuse on mismatch.
- Install an opener whose redirect handler rejects any target outside `https://www.nndc.bnl.gov/`.
- In `read`, require `resp.status == 206` and `len(data) == end - self.pos + 1`.

### WR-06: The golden guard's `--force` overwrites `kernels_v1.json` under the same version, and the documented change procedure does not match the code

**File:** `scripts/freeze_kernels.py:32, 83-88`; `tests/test_kernels_golden.py:18, 45`; `docs/PHYSICS.md:173-178`
**Issue:**
- **The path makes `--force` unnecessary after a bump.** `GOLDEN` is derived from `KERNELS_CONTRACT_VERSION` (`kernels_v{V}.json`). Following the documented procedure (step 1: bump the version), `--write` alone creates a new `kernels_v2.json` without refusing, so `--force` is never needed.
- **`--force` only ever rewrites the current version.** Because the path tracks the version, the only thing `--force` can do is overwrite the golden of the *current* version in place: a contract change that keeps version "1". That is exactly what the guard is meant to prevent. Its own refusal message offers it as an alternative ("bump KERNELS_CONTRACT_VERSION **or** pass --force").
- **The test is pinned to v1.** `test_kernels_golden.py` hard-codes `kernels_v1.json` and asserts `KERNELS_CONTRACT_VERSION == "1"`. After a real bump the suite still reads the stale v1 file. The procedure never mentions updating the test.
- **A silent overwrite is only partly caught.** A same-version overwrite whose T0/T1 drift stays below 1e-9 (the tolerance of the hard-coded checks in `test_golden_exact_values` and `test_exact.py`) passes the whole suite.
**Fix:**
- Remove `--force`, or have it refuse unless the existing file's `contract_version` differs from `KERNELS_CONTRACT_VERSION`.
- Make the test derive `GOLDEN = ROOT/"tests"/"golden"/f"kernels_v{KERNELS_CONTRACT_VERSION}.json"`.
- Rewrite PHYSICS.md steps 1-2 as "bump the version, then `--write`; update the tests' hard-coded version and T0/T1 values".

### WR-07: Per-entry flight and exit-row tables carry about 1e-3 absolute (2.5% relative) quadrature error from integrating across the exit-face discontinuity; undisclosed

**File:** `neutron_qae/kernels.py:96-112`; `docs/PHYSICS.md:151`
**Issue:**
- **Gauss-Legendre is applied across a jump.** Inside each phi bin, the exit face switches from BACK to LATERAL at the corner angle, and the exit row switches at row-edge angles. Both are discontinuities in phi (and in x), and Gauss-Legendre converges only O(1/n) across a jump.
- **Measured per-entry error.** Against a 96 x 768 reference:
  - max |delta flight| = 1.19e-3, worst at `flight[14, 12, BACK]` (0.33021 vs 0.33140);
  - max relative BACK error = 2.5%;
  - `back_exit_rows` entries off by up to 18% relative.
  - Raising to 48 x 384 does not reduce it (1.18e-3).
- **Why the summed value looks fine.** T1 is accurate to about 1e-6 only because the errors cancel in the bin sum.
- **What the doc says.** PHYSICS.md:151 gives only the T1 figure, and the docstring calls the tables "conditional averages". A Phase 3 or 4 consumer, or a judge, comparing per-bin or per-row values against an independent continuous calculation will see errors 1000 times larger than the documented accuracy.
**Fix:** Either split the phi quadrature at the exact breakpoints:
- the corner angles atan2(height_y - beam_y, width_x - X) and atan2(-beam_y, width_x - X), per x-node;
- the row-edge angles atan2(i*dy - beam_y, width_x - X).

Or, if contract v1 stays frozen as is, disclose it in PHYSICS.md: "individual flight entries are accurate to about 1e-3 absolute and back_exit_rows entries to about 20% relative. Only T1 and the summed row histogram are accurate to 1e-6."

### WR-08: The flight tables assume the scatter site lies on the beam line (y = beam_y), but neither the contract docstring nor PHYSICS.md says so

**File:** `neutron_qae/kernels.py:102, 111` (docstring 36-41); `docs/PHYSICS.md:146, 151`
**Issue:** `sl` uses `(height_y - beam_y)` and `-beam_y`, and the exit row uses `beam_y + s*sy`, so every flight starts at y = beam_y. That holds only for the first collision of the pencil beam. The contract describes `flight[j, b, o]` as "P(outcome o | scattered in column j, new direction in bin b)", which drops the y = beam_y condition.

The table also exposes a `COLLIDE` outcome, which invites a Phase 3 discrete MC (or a later K=2 extension) to chain a second flight from the same table. That chain would be wrong as soon as the neutron has moved laterally: lateral escape and exit rows would be computed from the wrong y.
**Fix:** Add to the `Kernels` docstring and the PHYSICS.md contract table: "flight and back_exit_rows are conditional on a scatter site on the beam line y = beam_y (first collision of the pencil beam); valid for K <= 1 only. Reusing them for later collisions is a contract change." Optionally rename the field or add a `valid_for_k = 1` attribute.

## Info

### IN-01: `spec_fingerprint` treats an int override and the equal float as different specs

**File:** `neutron_qae/problem.py:126-129, 180-185`
**Issue:** `__post_init__` accepts `int` for `width_x`, `height_y`, `boundary_x` and `beam_y`. `json.dumps` then writes `10` and `10.0` differently, so `spec_fingerprint(sparc_first_wall(width_x=10)) != spec_fingerprint(sparc_first_wall(width_x=10.0))` (verified), even though the physics is identical.
**Fix:** Coerce these fields with `object.__setattr__(self, name, float(v))` in `__post_init__`.

### IN-02: `column_segments` has no bounds check, and a boundary near a column edge can yield a sliver segment

**File:** `neutron_qae/problem.py:159-166`
**Issue:** `column_segments(16)` returns `(10.0, 10.625, SS316)` and `column_segments(-1)` returns `(-0.625, 0.0, WHA)`, both outside the slab, with no error. With `width_x=1.0, nx=10, boundary_x=0.3`, column 2 gets a `(0.3, 0.30000000000000004, SS316)` segment because 3 * 0.1 != 0.3. That is harmless for the frozen spec, where every edge is exact.
**Fix:** Raise `IndexError` for `j` outside `range(nx)`, and snap the boundary when `abs(boundary_x - edge) < 1e-12 * width_x`.

### IN-03: `transmission_within` accepts `True` and `1.0`; `exit_row_distribution_k1` skips the layout check and does not use `fsum`

**File:** `neutron_qae/exact.py:48-68`
**Issue:** `K == 1` is true for `True` and `1.0`, so non-int K slips through (verified). `exit_row_distribution_k1` runs for `nx=8` (sum 0.243002) even though `transmission_within(k, 1)` refuses that layout. That makes the two "exact" outputs inconsistent in scope. It also uses `+=` rather than `fsum`, unlike the T1 path.
**Fix:** Check `isinstance(K, int) and not isinstance(K, bool)`. Call the same layout check in `exit_row_distribution_k1`.

### IN-04: The golden's `outcomes` and `spec` keys are written but never verified

**File:** `scripts/freeze_kernels.py:34-35`; `tests/test_kernels_golden.py:29-41`
**Issue:** The module docstring says outcome order is part of the contract, but `EXACT_KEYS` omits `outcomes`, and neither the script nor the test compares `OUTCOMES` with the golden. Nothing ties `OUTCOMES` to `BACK`, `FRONT`, `LATERAL` and `COLLIDE` either. `spec` is covered indirectly by the fingerprint.
**Fix:** Add `"outcomes"` to `EXACT_KEYS`, and assert `OUTCOMES[BACK] == "back"` and so on in `test_kernels_contract.py`.

### IN-05: PHYSICS.md overclaims "every number here is printed from the code"; doc tests are loose substring searches

**File:** `docs/PHYSICS.md:3`; `tests/test_physics_doc.py:83-100`
**Issue:**
- **Untested numbers.** Several values are research-only and covered by no test: the model-bias table (127-129), the (n,2n), inelastic and capture split (94-96), the atom densities (84-85), the optical thicknesses (101) and the energy-sensitivity claim (192). WR-01's wrong multiplier is a direct result.
- **Loose matching.** `test_model_values_and_honest_labels` looks for needles such as `"0.997"` anywhere in the doc, so a value can move to another row and still pass.
**Fix:** Reword line 3 to name which tables are code-generated. Match model values in specific table rows with `_row()`.

### IN-06: Mismatched test comment and a tautological test

**File:** `tests/test_kernels_contract.py:38`; `tests/test_exact.py:94-96`
**Issue:**
- **Comment mismatch.** The comment says "bins 2, 3, 12, 13 reach it only from deeper columns", but the assertion checks bins `[0, 1, 14, 15]`. Bins 2, 3, 12 and 13 are not asserted at all.
- **Tautological test.** `test_fsum_is_order_independent` tests a property of `math.fsum` itself (it is correctly rounded), not of the module.
**Fix:** Assert that bins 2, 3, 12 and 13 are positive for deep columns and zero where geometry forbids it. Replace the fsum test with one that compares against a naive `sum` to show the fsum path is exercised.

### IN-07: Silent-zero and crash edge cases in the ENDF parser

**File:** `scripts/derive_cross_sections.py:85-101, 135-138, 221-232`
**Issue:**
- **Silent zero out of range.** `interp` returns `0.0` for energies outside the table. With `--energy-ev` above 20 MeV, sigma_el becomes 0 and `elemental` raises `ZeroDivisionError`.
- **Inconsistent fallbacks.** Law 5 falls back to `0.0` for non-positive y, while law 4 falls back to lin-lin.
- **Isotropic case crashes.** `dists` with `LTT == 0` (isotropic) returns an empty list, and `mubar` then crashes on `ds[k+1]`.
- **Hash and parse read separately.** `isotope_values` parses the file and then re-reads it to hash, so the hash and the parsed content can come from different reads.
**Fix:** Raise on out-of-range energies for MT1 and MT2. Use one fallback policy. Handle `LTT == 0` as mubar_cm = 0. Read bytes once, then hash and parse the same buffer.

### IN-08: `freeze_kernels.py` writes non-atomically and ignores `--force` without `--write`

**File:** `scripts/freeze_kernels.py:78-91`
**Issue:** `GOLDEN.write_text` truncates and then writes, so an interrupted write leaves a corrupt golden. `--force` on its own runs check mode silently (verified: exit 0).
**Fix:** Write to `GOLDEN.with_suffix(".tmp")` and `os.replace` it. Call `ap.error("--force requires --write")` when `--force` is given without `--write`.

### IN-09: Runtime tables are rebuilt on each platform; the golden is only checked locally

**File:** `neutron_qae/kernels.py:83-84`; `README.md:72`
**Issue:**
- **The tables depend on the platform's math libraries.** `build_kernels` recomputes the nodes with `leggauss` (LAPACK `eigvalsh`) and the cos, sin and exp values with the platform's libm.
- **The golden never reaches Qollab.** `tests/` is `export-ignore`d, so the golden is never checked on Pyodide's numpy 2.4 build.
- **Drift is probably tiny but unchecked.** Drift should be about 1e-15 relative, well inside Phase 4's 1e-12. But the README promise of "values frozen in tests/golden/kernels_v1.json" only holds locally.
**Fix:** In Phase 4/5, add a Pyodide-side sanity print that compares T1 with a literal `0.24300446519524305` at rtol 1e-12, or note the locality in README.

---

_Reviewed: 2026-10-10T23:38:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
