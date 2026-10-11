---
phase: 05-scaling-study-figures
reviewed: 2026-10-11T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - README.md
  - docs/RESULTS.md
  - main.py
  - neutron_qae/analysis.py
  - neutron_qae/artifacts.py
  - neutron_qae/figures.py
  - scripts/render_figures.py
  - scripts/sweep_common.py
  - scripts/sweep_scaling.py
  - scripts/sweep_histograms.py
  - scripts/sweep_truncation.py
  - scripts/sweep_thickness.py
  - tests/test_analysis.py
  - tests/test_artifacts.py
  - tests/test_results_doc.py
  - tests/test_studies.py
  - data/scaling_rmse.json
  - data/exit_histograms.json
  - data/truncation_bias.json
  - data/thickness_study.json
findings:
  critical: 0
  warning: 10
  info: 7
  total: 17
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-10-11
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I reviewed the Phase 5 analysis, artifact, figure and sweep code, the four committed JSON artifacts, the docs and the drift tests. I re-derived the committed numbers and probed the validator in the scratchpad.

The committed data is internally consistent:
- The MLAE costs match 300·(2^M + M − 2).
- The chi-square values recompute from the stored counts: dof 16, below the bound 44.28.
- Truncation within0/within1 agree with the exact T0/T1 within |z| ≤ 2.5.
- Every thickness target is bracketed.
- The Aer/analytic RMSE ratios run from 0.797 to 1.158, which fits "about 0.8 to 1.2".
- The fitted slopes refit exactly.
- All committed artifacts are full-profile, `git_dirty: false`, seed 2026.

No finding invalidates a committed number, so there are no blockers. The defects are in four areas:
1. **Guards that don't enforce what they claim.** The underflow guard is set 10x too loose. Nothing stops a quick run from overwriting `data/`. `render_figures.py --check` does not compare image content.
2. **Statistical labelling.** `slope_se` is a residual-scatter number, not a sampling SE.
3. **Prose stated as fact without data behind it.** The MLAE cost formula is about 30x off the measured costs. The M = 3–4 plateau explanation names the wrong mechanism. The IonQ label is hardcoded.
4. **Validator gaps.** `1e999` gets in, a huge integer raises `OverflowError`, `M = 2..None` can be printed, and stale fits or costs are accepted.

## Warnings

### WR-01: Underflow guard admits walls whose classical curve cannot reach 1% relative RMSE

**File:** `neutron_qae/analysis.py:333-348`, `scripts/sweep_thickness.py:40,105-119`, `tests/test_studies.py:226-229`
**Issue:** `check_transmission` accepts T1·N_max ≥ 1000 expected events, and its docstring says this ensures the curve can reach a 1% relative target. It does not. Classical relative RMSE is sqrt((1 − T)/(T·N)), so reaching ε = 1% needs about (1 − T)/ε² ≈ 10,000 events. At 1000 events the floor is about 3.2%.

Measured at N_max = 1e6:

| Wall | Events | Best reachable rel. RMSE | Guard result |
|---|---|---|---|
| 35 cm | 7,676 | 1.14% | passes |
| 40 cm | 3,835 | 1.61% | passes (pinned as accepted by `test_check_transmission_boundary`) |
| 45 cm | 1,915 | 2.28% | passes |

None of these can be bracketed. Consequences:
- In the full profile, `--widths ... 40` runs the whole sweep and only then dies with a `ValueError` traceback from `_validate_target` ("bracketed must be true"). The script docstring promises the opposite: "aborts the run with exit code 2 and writes nothing" before any sweep starts.
- In the quick profile it silently writes an unbracketed artifact.
- The MLAE side has no guard at all: with `mlae_M_max = 9`, N_A tops out at 78,900.

**Fix:** Derive the threshold from the target, and pre-check the MLAE side too:
```python
def check_transmission(T1, n_max, target_rel=0.01, safety=1.5):
    ...
    needed = safety * (1.0 - T1) / (T1 * target_rel ** 2)   # classical N at the target
    if not n_max >= needed:
        raise ValueError(f"N_max {n_max:g} < {needed:.3g} histories needed for {target_rel:.0%} rel. RMSE")
```
Then update the 40 cm test expectation, and add a conservative MLAE check (for example ~40/(ε·sqrt(T)) ≤ N_A(m_max), calibrated on the committed data).

### WR-02: Quick-profile runs overwrite the committed full-profile artifacts by default

**File:** `scripts/sweep_common.py:29-30`, `scripts/sweep_scaling.py:3`, `scripts/sweep_histograms.py:3`, `scripts/sweep_truncation.py:3`, `scripts/sweep_thickness.py:3`
**Issue:**
- `--out-dir` defaults to `data/` for every profile.
- Each script's docstring shows `--profile quick --seed 2026` as the "tracer" command with no `--out-dir`.
- Running it replaces `data/*.json` and its PNG with quick results.
- `docs/RESULTS.md:102` states "quick output must never overwrite the committed full-profile files", but nothing enforces this.

The damage is recoverable through git, but it turns the drift tests and `test_artifacts_load_and_are_byte_stable` red and can get committed by accident.

**Fix:** In `base_parser`/`finish`, refuse `profile == "quick"` when the resolved out-dir is `ROOT / "data"` (exit 2 with a message), or default quick runs to a temp or scratch dir. Fix the docstring examples to pass `--out-dir`.

### WR-03: `slope_se` is a residual-scatter statistic on correlated points, presented as a standard error

**File:** `neutron_qae/analysis.py:148-172`, `docs/RESULTS.md:15-21,31`, `README.md` (Results bullets)
**Issue:** The repetitions are nested:
- Classical: one run per repetition, read at checkpoints. `prefix_estimates` says itself that "the estimates are correlated across N".
- MLAE: prefixes of one schedule run.

So the RMSE points on a curve are not independent. The OLS formula sqrt(SSR/(n−2)/Sxx) assumes independent residuals and measures only the curve's wiggle around a line. It is not the sampling uncertainty of the slope over repetitions.

The docs nonetheless quote "−0.50 ± 0.01", "−1.02 ± 0.03" and "−1.03 ± 0.05", and use them to argue that Aer "agrees within one standard error" (`RESULTS.md:31`, README Aer bullet). With 13 points, autocorrelated residuals can understate the SE by a large factor, so the "within one SE" claim has no quantified basis. The MLAE fit over M = 2..11 also includes the pre-asymptotic plateau (M = 3–4), so the SE also absorbs model misspecification.

**Fix:** Compute the slope SE by bootstrapping over repetitions in the sweep:
- resample rows of `E` with replacement,
- recompute the RMSE column and the fit,
- report the std of the slopes.

Store it as `slope_se_bootstrap` and use it in `headline_sentence` and the docs. At minimum, rename the field to something like `slope_resid_se`, and add a note that it is not a sampling SE and that points on a curve are correlated.

### WR-04: MLAE cost formula "about 1/(eps sqrt(T))" is off by ~30–40x from the measured costs

**File:** `docs/RESULTS.md:84`, `scripts/sweep_thickness.py:51-53` (copied into `data/thickness_study.json` notes)
**Issue:** The text says MLAE "needs about 1/(eps sqrt(T)) applications of A", while the classical formula (1 − T)/(T·ε²) is quantitatively right. Comparison with the measured values:

| | 6 cm | 30 cm |
|---|---|---|
| Classical formula / measured | 13,844 / 11,384 | (matches within 1.5x, as tested) |
| MLAE formula / measured | 154 / 5,709 | 806 / 23,022 |

The missing factor is about sqrt(shots per power) times a schedule constant. The Fisher information is 4·shots·Σ(2k+1)², which gives Δθ ≈ sqrt(3·shots)/(2·N_A) on the exponential schedule.

Read as "about", the formula overstates the MLAE advantage by more than an order of magnitude, which is exactly the kind of overclaim the project's claims discipline forbids. The predicted ratio growth (∝ sqrt((1−T)/T): about 5x from 6 cm to 30 cm) also differs from the measured 13x, and the text does not reconcile the two.

**Fix:** State it as a proportionality: "MLAE cost grows as 1/(eps sqrt(T)) up to a constant set by shots per power and the schedule (≈ sqrt(shots) here)". Note that the measured ratio growth (1.99 → 25.84) exceeds the asymptotic sqrt((1−T)/T) prediction because of the discrete schedule and pre-asymptotic MLAE. Update the JSON note through a re-run, or add a doc-only clarification.

### WR-05: The M = 3–4 plateau explanation names the wrong mechanism

**File:** `docs/RESULTS.md:30`
**Issue:** The doc says k = 1 and k = 4 "carry little information" because the flag probability "barely changes with theta" near odd multiples of π/2. For p = sin²((2k+1)θ), the per-shot Fisher information about θ is 4(2k+1)², independent of θ: the vanishing dp/dθ is cancelled by the vanishing variance p(1−p).

The real cause is finite-count saturation plus the symmetric ambiguity around the peak:
- at k = 1, p = 0.99941, so 300 shots expect 0.18 misses and almost always return 300/300;
- the likelihood is then flat-topped and symmetric in θ, and the asymptotic Fisher bound does not apply.

The current wording is a technically false explanation in a judged results document.

**Fix:** Reword along these lines: "near the peak, 300 shots almost always return all hits (expected misses 0.18 at k = 1), so the count saturates and the likelihood cannot tell θ − δ from θ + δ; the asymptotic Fisher information 4(2k+1)² per shot is not reached until k = 8 enters at M = 5."

### WR-06: IonQ marker label and doc prose are hardcoded, not derived from or checked against the records

**File:** `scripts/sweep_scaling.py:38-39,55-61`, `neutron_qae/artifacts.py:241-254`, `docs/RESULTS.md:32,108`, `README.md` (IonQ bullet)
**Issue:**
- `IONQ_LABEL` hardcodes "k = 0, 1, 2 x 1000 shots" and "6.4 sigma".
- `ks`, `n_A` and `z` are computed separately from `data/ionq_runs.json` (models Q1 + Q1lite by default).
- If more IonQ records are ingested (likely in Phase 6) and the sweep is re-run, the label, the figure annotation and the prose ("6.4 sigma", "N_A = 9,000") silently disagree with the marker numbers.
- The drift test only covers the formatted table line; `RESULTS_PHRASES` even pins the literal "6.4 sigma".

`_validate_ionq_marker` also accepts:
- a negative `abs_err` (verified: −5.0 accepted), which would break the log-axis figure;
- a `z` inconsistent with `(a_hat − T1)/se` (verified: 0.1 accepted);
- an `abs_err` that is not |a_hat − reference_T1|.

**Fix:** Build the label from the record data:
```python
f"IonQ Forte 1, ideal noise model, k = {', '.join(map(str, ks))}, {shots} shots each: ... {abs(z):.1f} sigma off T1 ..."
```
In `_validate_scaling`:
- require `abs_err > 0`;
- check `abs(abs_err - abs(a_hat - T1)) <= 1e-15`;
- check `abs(z - (a_hat - T1)/se) <= 1e-9*max(1, abs(z))`.

Generate the prose numbers from the JSON as well, or add them to the drift test.

### WR-07: "NaN and Infinity are rejected on load" is false; oversized integers escape as OverflowError

**File:** `neutron_qae/artifacts.py:14-17,76-77,551-564`
**Issue:**
- `json.loads(..., parse_constant=...)` only intercepts the literals `NaN`/`Infinity`/`-Infinity`. A numeric literal such as `1e999` parses to `float('inf')` and never reaches `_reject_constant`.
- Verified: an extra key `"extra": 1e999` under `parameters` loads successfully. Unvalidated fields such as `parameters.*` extras, `width_x_cm` in histograms and `trend` extras are open to this. `dumps_artifact` then fails ("Out of range float values"), so the documented round-trip breaks.
- A 400-digit integer in a `_num`-validated field (`width_x_cm`) raises `OverflowError` from `float(v)` in `_is_num`, not the `ValueError` the loader contract promises. Callers catching `ValueError` (as `main.py` does for IonQ records) would crash.

**Fix:**
```python
def _is_num(v):
    if isinstance(v, bool) or not isinstance(v, numbers.Real):
        return False
    try:
        return math.isfinite(float(v))
    except OverflowError:
        return False

doc = json.loads(text, parse_constant=_reject_constant, parse_float=_finite_float)
# _finite_float(s): x = float(s); raise ValueError if not math.isfinite(x); return x
```

### WR-08: Quick-profile validator accepts an Aer series with `aer_M_max: null`, and the headline prints "M = 2..None"

**File:** `neutron_qae/artifacts.py:273-302,686-691`
**Issue:** With `profile = "quick"`, `aer_M_max = None` and a non-null `mlae_aer` series:
- validation passes, because the length check at line 301 is skipped when `aer_m is None`;
- `headline_sentence` emits "(MLAE, Aer circuit simulation, M = 2..None)" (verified).

`sweep_scaling.py` never produces this combination, but a hand-edited or `--no-aer`-patched artifact can, and the validator is meant to be the gate.

**Fix:** Require `aer_m is None` ⇔ `aer is None`:
```python
if (aer is None) != (aer_m is None):
    _fail("parameters.aer_M_max", "must be null exactly when results.series.mlae_aer is null")
```

### WR-09: The validator accepts artifacts whose derived fields contradict their own data

**File:** `neutron_qae/artifacts.py:199-239,333-374,434-513`
**Issue:** Each of these passes validation (all verified or read from the code):
- A classical `fit.slope` of −1.0 against data that fits −0.498. `_validate_fit` checks only `points`/`cost_min`/`cost_max`. `test_headline_slopes_and_cross_check` refits the committed scaling data, but nothing refits the thickness series, and nothing re-checks a re-run before commit except that test.
- MLAE `cost` doubled (not 300·(2^M + M − 2)).
- A series `shots_per_power` (7) different from `parameters.shots_per_power`.
- Histogram `chi2` values that don't match the stored counts, and a `dof` other than 16 (the "17 categories" claim).
- Thickness `trend.ratio_increases_as_T1_falls` / `ratio_span` inconsistent with the walls' ratios.
- Thickness `target_*` costs not reproducible from the stored RMSE curves.

Since the docs are generated from these fields, a stale or hand-edited field propagates straight to README/RESULTS while every drift test passes.

**Fix:** These checks fit in a stdlib-only module:
- recompute the OLS slope/intercept in pure Python and compare at 1e-9;
- check MLAE `cost[M-1] == shots*(2**M + M - 2)` and series `shots_per_power == parameters.shots_per_power`;
- recompute both chi-square forms from the counts;
- recompute the log-log interpolation for `target_*` and the `trend` fields from `walls`.

### WR-10: `render_figures.py --check` does not compare figures with the committed PNGs

**File:** `scripts/render_figures.py:5-7,53-71`, `README.md` ("re-render the four PNGs from the JSON and compare"), `docs/RESULTS.md:99`
**Issue:** `--check` compares only pixel dimensions and the byte budget. A committed PNG rendered from older JSON (stale curves, old slopes in the legend, old IonQ label) passes "RENDER CHECK OK" as long as figsize and DPI are unchanged. The README and RESULTS describe this command as the freshness check ("compare fresh renders with the committed PNGs").

**Fix:** Add a content comparison. Exact bytes are not portable across matplotlib/freetype versions, so decode both PNGs (matplotlib's `imread` under Agg is fine in a local-only script) and require mean absolute pixel difference ≤ a small tolerance. Alternatively, record a hash of the source JSON text in PNG metadata (`savefig(metadata={"Description": sha})`) and compare it. Otherwise, reword the docs to "checks dimensions and size budget".

## Info

### IN-01: Inaccurate cost-unit equivalences in RESULTS

**File:** `docs/RESULTS.md:11,107`
**Issue:**
- Line 11 says one application of A "and one classical history are the same unit of work ...: one sampled neutron path". Inside A·Q^k, applications of A are coherent unitaries (A and A† in each Q), not sampled paths.
- Line 107 says "one application of A on hardware costs a full circuit execution". In fact one shot of A·Q^k contains 2k+1 applications.

**Fix:** "Cost is counted per application of A (2k + 1 per shot at Grover power k), compared one-for-one with histories by convention".

### IN-02: The speedup-claim lint is easy to defeat

**File:** `tests/test_results_doc.py:95-103`, `tests/test_artifacts.py:105-113`
**Issue:** Any "no " or "not " anywhere in the 40 characters before "speedup" or "advantage" passes, for example "it is not small: a quantum advantage of 26x". The lint also misses "faster", "outperform" and "exponential".
**Fix:** Allowlist the exact negated phrases ("no speedup", "not speedup evidence", "not a quantum-advantage claim", ...) and flag every other occurrence.

### IN-03: Duplicate JSON keys are silently accepted

**File:** `neutron_qae/artifacts.py:561`
**Issue:** `json.loads` keeps the last value for a duplicated key, so a hand-merged artifact can hide a conflicting value.
**Fix:** Pass `object_pairs_hook` and reject repeated keys.

### IN-04: Figure text hardcodes study parameters

**File:** `neutron_qae/figures.py:102,141`
**Issue:**
- The scaling title says "10 cm SPARC wall", but `width_x_cm` is a parameter.
- The histogram box says "16 rows + no exit" instead of using `parameters.rows`.

**Fix:** Format both from `doc["parameters"]`.

### IN-05: The truncation SE could be paired and the within-K checks are not recorded

**File:** `scripts/sweep_truncation.py:65-73`, `neutron_qae/artifacts.py:394-429`
**Issue:**
- `bias_se = T_full_se` is a valid but loose SE.
- The within(K) vs exact z-scores (|z| up to 2.48 for T0 and 2.06 for T1 at 30 cm) are tested but neither stored nor validated.
- The paired difference T_full − within1 (the ≥ 2-collision fraction, same histories) has a much smaller SE and isolates truncation from MC noise. At 30 cm it gives about 99.27% coverage, against 98.91% from T1/T_full.

**Fix:** Store `within0_z`/`within1_z` and validate |z| < 4. Optionally report the paired estimate alongside.

### IN-06: Figure edge cases crash or misplot

**File:** `neutron_qae/figures.py:151-152,94`
**Issue:**
- `min(positive)` raises on an all-zero histogram.
- An IonQ `abs_err` of 0 (not rejected by the validator; see WR-06) is placed at 0 on a log axis.

**Fix:** Guard the empty case. Require `abs_err > 0` in the validator.

### IN-07: Sweeps fail late and non-atomically

**File:** `scripts/sweep_common.py:35-43,62-89`
**Issue:**
- `provenance()` (git subprocess) runs only after the whole sweep. A missing git or a non-repo checkout throws `CalledProcessError` after minutes of compute.
- `finish` writes the JSON before rendering the PNG, so a render failure leaves a new JSON with a stale PNG.

**Fix:** Call `git_state()` at startup. Render to a temp PNG, then replace both files only after both succeed.

---

_Reviewed: 2026-10-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
