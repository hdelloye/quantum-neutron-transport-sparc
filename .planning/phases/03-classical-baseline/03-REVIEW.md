---
phase: 03-classical-baseline
reviewed: 2026-10-10T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - neutron_qae/mc_continuous.py
  - neutron_qae/mc_lattice.py
  - neutron_qae/random_source.py
  - tests/random_doubles.py
  - tests/test_mc_continuous.py
  - tests/test_mc_lattice.py
  - tests/test_random_source.py
findings:
  critical: 0
  warning: 3
  info: 8
  total: 11
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-10
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

I reviewed the two engines, the random-source protocol, the test doubles and the three test files. I read `kernels.py`, `exact.py` and `problem.py` as context only. I traced each finding to code and reproduced the behavioural ones in the scratchpad (scripts `q1.py`, `q2.py`, `q3.py`).

On valid inputs, the core physics and statistics hold up under adversarial tracing:
- **Woodcock delta tracking:** the majorant is the larger of the two materials' sigma_t. The exit test runs before the collision. Material lookup at the new site uses the half-open rule, and the partition into scatter, absorption and virtual collision is correct.
- **Lattice sampling:** the inverse-CDF register draws and the column-0 reuse for x = 16 are correct.
- **Row sampling:** it never lands in a zero-mass row.
- **Checkpoint prefixes:** the counts have no off-by-one error and no bias.
- **Standard errors:** the binomial SEs are correct.

An independent check also passed. I pooled six continuous runs of 1e8 histories each (seeds 11, 13, 101-104) and compared them with a kernel built at 4x x-nodes and 8x phi-nodes. The at-most-one-collision row chi2 was 16.2 on 16 degrees of freedom, with no systematic row residual.

The defects are at the edges:
- the lattice engine silently accepts a non-normalized `Kernels` and returns a wrong answer;
- `as_source` lets numpy's module-level global RNG through the protocol;
- the `-1` row sentinel mixes two different cases, although the docstring asks callers to count them separately.

The remaining findings are test-hygiene and Phase 5 hand-off hazards.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The lattice engine silently renormalizes a malformed `first_collision`, giving a wrong T1 with no error

**File:** `neutron_qae/mc_lattice.py:246` (also `:103-110`)
**Issue:** `cdf_x = np.cumsum(k.first_collision); cdf_x[-1] = 1.0` overwrites the last cumulative entry without checking that the table sums to 1. `_check_kernels` checks only `nx` and `n_dir`. `Kernels` is a public dataclass whose constructor validates shapes only.

If the table sums to more than 1, `cdf_x` becomes non-monotone. `searchsorted` then never returns `nx`, so the uncollided bin is lost. If it sums to less than 1, all the missing mass goes into the uncollided bin.

Reproduced with `fc[0] += 0.2` and `run_lattice(Kernels(sp, fc, ...), 100_000, 1)`. The run raises no error and returns mean = 0.043 (T1 = 0.243).

`scatter_ratio` and `flight[..., BACK]` outside [0, 1] are also absorbed silently by the `u < p` comparisons. The engine's stated purpose is to sample exactly the model that the circuit encodes, so a mismatched table should fail loudly. It should not be quietly reshaped.
**Fix:**
```python
cdf_x = np.cumsum(k.first_collision)
if not (np.all(k.first_collision >= 0) and abs(cdf_x[-1] - 1.0) <= 1e-12):
    raise ValueError(f"first_collision must be a probability vector (sum {cdf_x[-1]!r})")
if not (np.all((k.scatter_ratio >= 0) & (k.scatter_ratio <= 1)) and np.all((q >= 0) & (q <= 1))):
    raise ValueError("scatter_ratio / flight[..., BACK] must lie in [0, 1]")
cdf_x[-1] = 1.0   # now only absorbs a <= 1e-12 rounding residual
```
Put this in `_check_kernels`, or in a small `_check_tables` called by `run_lattice`.

### WR-02: `as_source` accepts the `numpy.random` module and legacy `RandomState`, routing engine draws through the global RNG

**File:** `neutron_qae/random_source.py:42-48`
**Issue:** The runtime-checkable `RandomSource` protocol checks only that a `.random` attribute exists. Reproduced:
- `as_source(np.random) is np.random` is `True`. `run_continuous(spec, n, np.random)` therefore draws every uniform from numpy's module-level global state. That state is shared, mutable and seeded by anyone, which is exactly the "module-level randomness" the hard rule forbids. The AST gate cannot catch it because the call sits in the caller.
- `np.random.RandomState(0)` is accepted too (legacy MT19937, not the documented `Generator`).
- The stdlib `random` module passes coercion, then fails deep in the engine with `TypeError: Random.random() takes no arguments (1 given)`. That error does not point to the bad source.

**Fix:**
```python
import types
...
if isinstance(source, types.ModuleType) or isinstance(source, np.random.RandomState):
    raise TypeError("pass a Generator, a seed or a RandomSource object, not a module or legacy RandomState")
```
Add `np.random`, `random` and `np.random.RandomState(0)` to the `bad` tuple in `tests/test_random_source.py::test_as_source_coercions`.

### WR-03: The `-1` row sentinel mixes physical non-escape with zero-amplitude (noise) strings, but the contract asks callers to count the latter

**File:** `neutron_qae/mc_lattice.py:177-224` (docstring `:188-192`, code `:215-219`)
**Issue:** `sample_exit_rows` returns `-1` both for legitimate K = 1 outcomes (absorbed, or scattered but not escaped) and for zero-amplitude strings (`x > nx`, or `e = 1` in one of the 168 dead bins). The docstring tells callers to "report how many there were, not drop them silently", but the return value cannot tell the two apart.

Phase 5 is the only caller that sees noisy Q1 counts. To report them, it would have to re-implement the bit decoding and the `cumsum(back_exit_rows)[..., -1] > 0` liveness test. That duplicates the logic this shared helper was meant to own, and a divergent copy would misreport hardware noise. A second hazard: any caller that indexes `row_counts[r]` without filtering will send `-1` silently to row 15 through Python negative indexing.
**Fix:** Use a distinct sentinel for zero-amplitude strings, for example `-2`, and export the constants:
```python
NO_EXIT, ZERO_AMPLITUDE = -1, -2
r = np.full(s.size, NO_EXIT, np.int64); r[x > nx] = ZERO_AMPLITUDE
...
r[se_[~live]] = ZERO_AMPLITUDE       # before filtering se_ by live
```
`run_lattice` keeps `r[r >= 0]`. Alternatively, add `return_invalid=True` to return a boolean mask. Extend `test_sample_exit_rows_contract` to check the distinction.

## Info

### IN-01: The documented `ValueError` for bad checkpoints is a `TypeError` for non-iterables

**File:** `neutron_qae/mc_lattice.py:239`
**Issue:** `tuple(checkpoints)` raises `TypeError: 'int' object is not iterable` for `checkpoints=1000` and for `checkpoints=None` (reproduced). The docstring at `:234` promises `ValueError` for bad checkpoints. Passing a single int instead of a tuple is a likely Phase 5 mistake.
**Fix:** `cps = (checkpoints,) if _is_int(checkpoints) else tuple(checkpoints)`. Alternatively, wrap the call in `try/except TypeError` and re-raise as `ValueError`.

### IN-02: Checkpoint prefixes are not the same histories as a standalone run of that size

**File:** `neutron_qae/mc_lattice.py:252-263` (doc `:54-57`, `:69-73`)
**Issue:** The chunk size is `m = min(chunk, n - done)`, so the four register draws for a history sit at offsets that depend on `n`. Reproduced with seed 9: the prefix at 2500 in a run of 10_000 has 593 transmitted, while `run_lattice(K, 2500, 9)` has 579. The behaviour is valid and is covered by "same n", but Phase 5's RMSE-vs-N plots could easily assume that the two are interchangeable.
**Fix:** State it explicitly in the "Phase 5 hooks" docstring: "a checkpoint at N is not the same sample as `run_lattice(k, N, same_seed)`".

### IN-03: The Wald SE is exactly 0 at p in {0, 1}, which makes small-N z-scores degenerate

**File:** `neutron_qae/mc_lattice.py:113-116, 165-174`; `neutron_qae/mc_continuous.py:73-76`
**Issue:** `prefix_estimates()` at N = 1 always returns SE 0 (reproduced: `(array([1]), array([0.]), array([0.]))`). Any zero-count tally also reports SE 0. This is correct as the plug-in binomial SE, but Phase 5 will compute z-scores or error bars at small N, and a zero SE gives `inf` or a missing error bar.
**Fix:** Document this in `prefix_estimates`. For plots, use the RMSE over SeedSequence repetitions, or a Wilson interval, rather than the per-run Wald SE.

### IN-04: `row_of(NaN)` maps silently to row 0, and `ContinuousHistories.yexit` is NaN for every non-back history

**File:** `neutron_qae/mc_continuous.py:89, 236` (cross-module: `neutron_qae/problem.py:170`)
**Issue:** The engine filters `yexit[tb]` before calling `row_of`, which is correct. But `spec.row_of(np.array([np.nan]))` returns `[0]`, with only a RuntimeWarning from the cast (reproduced). A Phase 5 consumer that bins `h.yexit` directly from `histories=True` without masking `fate == BACK` will dump every non-transmitted history into row 0.
**Fix:** Warn about this in the `ContinuousHistories.yexit` comment. Optionally, have `run_continuous` expose a ready `yexit_row` array that uses `-1` for non-back histories.

### IN-05: The golden draw-count assertions pin a total, not the documented order, and one prefix golden depends on the numpy stream

**File:** `tests/test_mc_continuous.py:109`; `tests/test_mc_lattice.py:128, 209`
**Issue:**
- `h.drawn == 445_741` is a recorded number, not a derived one. It catches any change but does not prove the documented per-iteration order. The scripted tests use n = 1, so the interleaving across several histories in one chunk (all flights, then collision types, then directions) is never pinned.
- `HashCounterSource` discards the unused words of the last digest block on each call, so its stream depends on how calls are partitioned. `drawn` therefore counts requested uniforms, not hash words consumed. That is fine for the test, but it should be noted.
- `list(r.checkpoint_counts) == [1, 584, 2429]` depends on the `Generator.random` stream of PCG64, and numpy does not promise that stream stays the same across versions (`numpy>=2.0,<3`). It is redundant with the derived `expected` check on the line above.

**Fix:** Add a two-history `ScriptedSource` case to the continuous tests that pins the cross-history interleaving. Drop the `[1, 584, 2429]` literal, or switch that test to `HashCounterSource`.

### IN-06: The first-collision column chi2 uses 17 degrees of freedom for 17 bins whose counts sum to n

**File:** `tests/test_mc_continuous.py:222`
**Issue:** `cols` sums to n exactly, so the correct number of degrees of freedom is 16. `_chi2_bound(17)` = 46.15 is slightly looser than the 44.28 the documented rule implies. The rows test (`:217`) correctly uses 16 because transmitted rows do not sum to n. In `test_mc_lattice.py:97` the bit-string test correctly uses `support - 1`.
**Fix:** `_chi2_bound(16)`.

### IN-07: The 1e8 edge-row finding in the SUMMARY is attributed to the wrong cause

**File:** `tests/test_mc_continuous.py:213-214, 293-297` (cross-ref `03-01-SUMMARY.md:193`, `03-02-SUMMARY.md:226`)
**Issue:** The 03-01 SUMMARY attributes the 1e8 row chi2 of 34.4 (seed 11, row 0 at z = -2.9) to "about 1% relative quadrature error in the edge rows". It tells Phase 5 to treat edge-row residuals as a kernel artefact.

My check does not support that:
- The v1 `exit_row_distribution_k1` differs from a 96 x-node / 384 phi-node rebuild by at most 0.15% in any row, and by 0.04% in row 0.
- Six independent 1e8 continuous runs pooled (6e8 histories) give chi2 = 16.2 against the high-resolution reference, with row 0 at z = -1.19.

Seed 11 alone gives chi2 = 36.7, a tail fluctuation with p of about 0.003. It is not a systematic effect. The slow test still passes, but the hand-off note would lead Phase 5 to misread a noisy panel.
**Fix:** Correct the Phase 5 note. Seed 11 is a statistical outlier, and the summed kernel row histogram is accurate to about 1e-3 relative. Optionally, move the slow test to a seed whose chi2 is not in the tail.

### IN-08: Duplicated helpers, and result dataclasses that do not validate their own invariants

**File:** `neutron_qae/mc_continuous.py:73-82, 93-108`; `neutron_qae/mc_lattice.py:93-100, 113-139`
**Issue:**
- `_check_int` and `_frac_se` are copy-pasted between the two engines.
- `ContinuousResult(0, ...)` is accepted and yields NaN fractions with a RuntimeWarning (reproduced).
- `LatticeResult` does not check `len(checkpoints) == len(checkpoint_counts)`, `transmitted <= n` or `n >= 1`.

If Phase 5 merges or rebuilds results, nothing catches inconsistent tallies.
**Fix:** Move the two helpers into a small private `neutron_qae/_mc_common.py`. In each `__post_init__`, add `n >= 1` plus cheap consistency checks: `fate_counts.sum() == n`, `order_counts.sum() == fate_counts[BACK]`, and matching checkpoint lengths.

---

_Reviewed: 2026-10-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
