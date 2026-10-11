---
phase: 04-quantum-oracle-amplitude-estimation
reviewed: 2026-10-11T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - README.md
  - data/ionq_runs.json
  - docs/QOLLAB-RUNTIME.md
  - docs/QUANTUM.md
  - main.py
  - neutron_qae/grover.py
  - neutron_qae/mlae.py
  - neutron_qae/oracle.py
  - neutron_qae/runners.py
  - scripts/ingest_ionq_records.py
  - scripts/qae_local.py
  - scripts/run_local.py
  - tests/ionq_fakes.py
  - tests/test_grover.py
  - tests/test_ingest_ionq_records.py
  - tests/test_ionq_records.py
  - tests/test_main_qae.py
  - tests/test_mlae.py
  - tests/test_oracle.py
  - tests/test_quantum_doc.py
  - tests/test_runners.py
  - tests/test_smoke.py
findings:
  critical: 1
  warning: 5
  info: 10
  total: 16
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-11
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

The circuit construction is correct. I traced the layout (x(5) a φ(4) e T, little-endian, UCRY angle index j + 16b with the first control as LSB, the x = 16 rule via `col = x % nx`, and T = x4 OR (¬x4 ∧ a ∧ e) with disjoint branches) against `exact.py`, and it matches. The Grover composition (logical A·Q^k, one transpile, explicit basis) is sound. The MLAE numerics are well guarded: the 0·log0 guard holds, no NaN reaches the argmax, golden refinement is accepted only on improvement, and a stress run (8 powers to k = 128, 30 × 10,000 shots per power, 20 reps) showed no grid-resolution failure. Input validation in `main.py` handles bool, NaN, inf, non-integral floats and kwarg correctly.

I reproduced the following defects in the scratchpad:

1. **IonQ `ideal_mode = "none"` cannot produce a record.** qiskit-ionq 1.0.2 returns `round(p·shots)` counts for non-ideal runs, and these never sum to `shots`. Every such run is therefore reported as `IONQ RUN FAILED` and its counts are thrown away. The test fake always samples, which hides this.
2. **The docs' claim that the local circuit was "the same transpiled circuit" is contradicted by the records themselves.** The submitted circuits' `size` and `depth` differ from the local transpile by 2k + 1 gates, and the contract p on Qollab differs in its last digits. So the "the circuit we build is correct" argument behind the accepted 6.4σ finding does not cover the circuit IonQ actually received.
3. **The "untrusted JSON" loader can raise exceptions that the judged Built-in path does not catch** (`OverflowError`, `RecursionError`). It also accepts `NaN` for `p_flag`.

The xfail keying is well guarded against masking MLAE or contract regressions, because the companion z = -6.38 check covers them. It lacks only `raises=`.

## Critical Issues

### CR-01: IonQ runs with `ideal_mode = "none"` always fail and discard their counts (rounded counts never sum to shots)

**File:** `neutron_qae/runners.py:313-322` (also `runners.py:165-166`, `runners.py:413`, `tests/ionq_fakes.py:10-11`, `docs/QUANTUM.md:115`, `README.md:39`)
**Issue:** For any IonQ result that is not ideal-simulator, qiskit-ionq 1.0.2 builds counts as `round(prob * shots)` and drops zero bins (`qiskit_ionq/ionq_job.py:139-141`; sampling only when `backend_name == "ionq_simulator" and noise_model == "ideal"`, line 498). `run_point` then calls `hits_from_counts(raw, pr.flag, pr.qubits, shots)` with `shots` set, and that raises `ValueError("counts sum to N, expected shots = M")`. The broad `except` turns this into `accepted: False`, sets `hits = None` and leaves `counts = {}`, because `counts` is assigned only after `hits_from_counts` succeeds. As a result:
- the IonQ job really ran and spent credits, but its data is lost;
- the console prints `IONQ RUN FAILED: ValueError: counts sum to 904, expected shots = 1000`;
- the ingest script files the run as a "failed attempt".

Reproduced with exact Q1 probabilities, so this happens even before any noise spreads the distribution. With a fake that returns qiskit-ionq-style rounded counts, `sum(round(p·1000))` is 904 at k = 0, 1014 at k = 1 and 908 at k = 2, and `IonQRunner(..., ideal_mode="none").run_point(0, 1000)` returns `accepted False`, `error "ValueError: counts sum to 904, expected shots = 1000"` and 0 counts kept. With the real forte-1 noise model the distribution is wider and the mismatch is larger.

Even if the runner were fixed, `validate_ionq_record` (line 413) would still reject such a record, because it enforces the same sum, so it could never reach `data/ionq_runs.json`. The documented behaviour ("These records are kept with `sampled: false` and reported", QUANTUM.md:115; README.md:39; R4/R5 in the protocol) is therefore unreachable. The fake (`tests/ionq_fakes.py`) always samples ideally "even when its option reads forte-1", so `test_ionq_noisy_record_is_unsampled` and `test_noisy_record_is_valid_but_unsampled` pass against behaviour that the real backend never shows.
**Fix:** Keep the raw counts before validating. Require the counts total to equal `shots` only for sampled records. Separate "job accepted" from "counts consistent":
```python
raw = dict(job.result().get_counts())
counts = {str(key): int(v) for key, v in raw.items()}
sampled = noise_model == "ideal"
hits = hits_from_counts(counts, pr.flag, pr.qubits, shots if sampled else None)
# record also "counts_total": sum(counts.values())
```
In `validate_ionq_record`, pass `shots if rec["sampled"] else None` and, for unsampled records, check `abs(total - shots) <= 2 ** qubits / 2` (rounding slack) instead of equality. Add a `RoundingIonQ` fake that returns `{k: round(p*shots)}` with zero bins dropped when `noise_model != "ideal"`, and test that a `none` run is accepted, keeps its counts and is refused by `mlae.estimate`.

## Warnings

### WR-01: The circuit submitted to IonQ is not the one the docs say was checked locally; records carry no way to verify it

**File:** `docs/QOLLAB-RUNTIME.md:185-186`, `docs/QUANTUM.md:141-142`, `neutron_qae/runners.py:299-300, 324-354`
**Issue:** The docs say: "Locally, qiskit's `Statevector` of the same transpiled circuits (`transpile_once`, seed 1) reproduces p_expected exactly … The circuit we build is therefore correct". The "impossible outcomes" counts (3/20/42 shots on states with probability < 1e-9) were computed against that local circuit. The committed records contradict this:

| k | record size / depth (Qollab, Pyodide) | local `transpile_once(measure="all")` |
|---|---|---|
| 0 | 556 / 520 | 555 / 519 |
| 1 | 3016 / 2536 | 3013 / 2533 |
| 2 | 5476 / 4552 | 5471 / 4547 |

There is exactly one extra gate per application of A or A† (2k + 1), and the contract p printed on Qollab (`0.24300446519524638`) differs from the local value (`0.24300446519524654`). So the wasm build produced different floating-point kernels or angles and a different transpiled circuit. The circuit IonQ received was never simulated, and the record has no fingerprint (QASM hash) and no in-run check of `tc`. The Built-in R0 run (measure="flag", 1000/1000 at k = 1) makes a gross Pyodide transpile bug unlikely, but it does not cover the measure="all" circuits that were sent. The accepted finding's root-cause narrative ("the deviation arises in IonQ's … simulation") rests on an unverified premise.
**Fix:** Inside `run_point`, before submitting, compute and record what the submitted circuit predicts (12 qubits is cheap in Pyodide), and add both fields to `RECORD_KEYS` and the docs:
```python
sv = Statevector(tc.remove_final_measurements(inplace=False))
p_tc = float(sv.probabilities([pr.flag])[1])
record["p_expected_tc"] = p_tc
record["circuit_sha256"] = hashlib.sha256(qasm3.dumps(tc).encode()).hexdigest()
```
Reword QOLLAB-RUNTIME.md:186 and QUANTUM.md:142 to "the locally transpiled circuit (which differs from the submitted one by 2k + 1 single-qubit gates)" until a re-run with `p_expected_tc` closes the gap.

### WR-02: Malformed records crash the judged Built-in path and the ingest script with exceptions other than `ValueError`

**File:** `neutron_qae/runners.py:158-159, 419, 448-452`; `main.py:111-115`; `scripts/ingest_ionq_records.py:48-51, 56-59`
**Issue:** `load_ionq_records` is documented as the untrusted-JSON gate, and `test_builtin_survives_corrupt_records_file` asserts that the Built-in path survives a corrupt file. But:
- **Huge integer count.** A count that is a JSON integer with about 400 digits makes `float(value).is_integer()` (line 158) raise `OverflowError`.
- **Huge integer `p_flag`.** A huge integer `p_flag` makes `p_flag - hits / shots` (line 419) raise `OverflowError`.
- **Deeply nested document.** A deeply nested document (`[[[[…]]]]`, well under 2 MB) makes `json.load` raise `RecursionError`.

All three were reproduced. `_ionq_summary` catches only `(ValueError, OSError)`, so the Built-in run aborts before `QAE RUN COMPLETED`. In the ingest script these become tracebacks (exit 1) instead of `INGEST ERROR` (exit 2), although the output file is untouched.
**Fix:** In `hits_from_counts`, test integers first and bound them:
```python
if isinstance(value, bool) or not isinstance(value, numbers.Real):
    raise ValueError(...)
if not _is_int(value):
    if not (isinstance(value, float) and math.isfinite(value) and value.is_integer()):
        raise ValueError(...)
value = int(value)
if value < 0 or (shots is not None and value > shots):
    raise ValueError(...)
```
Also:
- In `validate_ionq_record`, require `isinstance(p_flag, float) and math.isfinite(p_flag)`.
- In `load_ionq_records`, catch `RecursionError` next to `JSONDecodeError`.
- In `main._ionq_summary`, catch `Exception`, because the judged path must never die on the side-car file.
- In the ingest script, catch `(ValueError, OverflowError, RecursionError)` in `parse_paste` and `check_record`.

### WR-03: The record validator accepts `NaN` / `Infinity` and leaves several fields unchecked

**File:** `neutron_qae/runners.py:418-431`
**Issue:**
- **`NaN` passes the `p_flag` check.** `abs(p_flag - hits / shots) > 1e-12` is `False` for `NaN`, and Python's `json` parses `NaN`/`Infinity` by default. A record with `"p_flag": NaN` validates (reproduced). The ingest script then writes non-standard JSON (`NaN`) into `data/ionq_runs.json`, which strict JSON consumers reject.
- **`accepted: true` with a non-null `error` passes.**
- **Some fields are never checked:** `p_expected`, `cx`, `depth`, `size`, `max_controls`, `body_bytes_est`, `run_s`, `qiskit` and `backend_name` are not type- or range-checked. All of these are printed or quoted in the docs.

**Fix:** Parse with `json.loads(..., parse_constant=_reject)` in both the loader and the ingest script. Require `rec["error"] is None` when `accepted` is true. Type-check the numeric fields as non-negative finite numbers, and require `p_expected` to be in [0, 1] (see also WR-04).

### WR-04: Records feeding the Built-in estimate are not checked for provenance or for the current contract, and are labelled "IonQ Forte 1"

**File:** `neutron_qae/runners.py:378-432, 468-488`; `main.py:118, 161`
**Issue:**
- **No provenance check on the Built-in path.** The real-backend check (`backend_class` starts with `qiskit_ionq.` and has no `Fake`) exists only in the ingest script, not in `validate_ionq_record` or `load_ionq_records`. A hand-edited `data/ionq_runs.json` holding `FakeIonQSimulator` records (exactly what `tests/test_main_qae.py::_fake_record_file` writes) is shown to judges on the Built-in path as "IonQ Forte 1 records (ideal, sampled)". That label is hard-coded at main.py:161 and ignores `backend_name`.
- **No contract or version check.** Records are not tied to the oracle they were run against. After a Kernels contract change (v2, new T1), old records would still validate, because layout, qubits and flag are unchanged. They would silently be combined into an estimate compared against the new T1. The stored `p_expected` makes this checkable but is never compared.
- **Misleading label.** Even for the real records, the runs used `noise_model = "ideal"`, i.e. IonQ's ideal cloud simulator, not Forte 1 noise or hardware.

**Fix:**
- Move the provenance check into `validate_ionq_record`.
- In `ionq_power_results(records, problem)`, require `abs(rec["p_expected"] - sin²((2k+1)·problem.theta)) <= 1e-9`.
- Build the console label from the records (`backend_name`, `noise_model`), e.g. "IonQ ionq_simulator (noise_model=ideal) records".

### WR-05: `fisher_se` reports a near-zero standard error at a = 0 or 1

**File:** `neutron_qae/mlae.py:137-140, 180-181`
**Issue:** At the boundary the MLE is theta ≈ EPS or pi/2 − EPS, and `|sin 2θ|` drives the reported se to about 0. This was reproduced:
- all misses at k = 0, 1, 2, 4 × 1000 shots gives `a_hat = 1e-30`, `se = 2.9e-18`;
- 1000/1000 hits gives `se = 5.1e-17`.

Any downstream z-score is then effectively infinite. The ingest script guards `se > 0` but not `se ≈ 1e-18`, and `tests/test_ionq_records.py:79` divides by `res.se` unguarded. Phase 5 sweeps or a different model with a small T would report a falsely certain estimate.
**Fix:** When `a_hat` is within, say, `1 / sum(shots)` of 0 or 1, return the se from the inverted likelihood-ratio or Wilson bound, or `math.nan` with a flag. Document this in `MLAEResult`. Add a test that `estimate([PowerResult(0, 1000, 0)]).se` is either `>= 1e-4` or NaN, never about 0.

## Info

### IN-01: The strict xfail has no `raises=`, so any exception is recorded as XFAIL

**File:** `tests/test_ionq_records.py:66-69`
**Issue:** With the known record set, a `ZeroDivisionError` (se = 0), an `AttributeError` (`ionq_estimate` returning None) or a `TypeError` would all be reported as the expected failure. `test_known_4sigma_miss_matches_data` currently catches these, so nothing is masked today, but the guard should not depend on a second test.
**Fix:** `@pytest.mark.xfail(..., strict=True, raises=AssertionError)`.

### IN-02: The xfail docstring overstates what turns the xfail off

**File:** `tests/test_ionq_records.py:8-11, 45-47`
**Issue:** The docstring says the xfail "becomes a plain assertion as soon as any record is added, changed or removed". The key is only (timestamp, model, k, shots, hits) of *sampled Q1/Q1lite* records. Adding an unsampled or Q0 record, or editing counts and other fields while keeping hits, leaves the xfail active.
**Fix:** Reword to "as soon as the set of sampled Q1/Q1lite (timestamp, model, k, shots, hits) tuples changes", or key on the sha256 of the file.

### IN-03: `_send_file` catches only `ImportError`

**File:** `main.py:72-78, 183`
**Issue:** On the IonQ path, `sendFile` runs after `IONQ_RECORD=` is printed and before `IONQ RUN ACCEPTED`. A JS-side failure (`pyodide.ffi.JsException`, a `TypeError` from the bridge) would abort the run without the final status line. It worked in R1-R3.
**Fix:** Use `except Exception` there and print a one-line note, so that a download failure can never change the run outcome.

### IN-04: Duplicate detection keys on the exact timestamp string

**File:** `neutron_qae/runners.py:461`; `scripts/ingest_ionq_records.py:37-38`
**Issue:** The same run stored once with `+00:00` and once with `Z` (or with an edited timestamp) is accepted twice and counted twice. Reproduced: N_A doubles from 1000 to 2000.
**Fix:** Also reject records whose `counts` dicts are identical (or compare on `(model, k, shots, json.dumps(counts, sort_keys=True))`), and normalise timestamps with `datetime.fromisoformat`.

### IN-05: The Q1lite request sizes in QUANTUM.md do not match the code

**File:** `docs/QUANTUM.md:117`
**Issue:** The doc quotes "57 KB at k = 1, 103 KB at k = 2". `56 × size` of `transpile_once(power_circuit(..., measure="all"))` gives 56,224 and 101,528 bytes (56 KB and 102 KB). Adding Pyodide's 2k + 1 extra gates gives the same rounded values.
**Fix:** Use 56 KB and 102 KB, or generate the figure in the doc from code as the resource table is.

### IN-06: Exact-digit tracer assertions depend on the unpinned NumPy random stream

**File:** `tests/test_runners.py:145-146, 172-173`; `tests/test_main_qae.py:53-55`; `tests/test_grover.py:121-129`
**Issue:** `np.allclose(ys, [8.08e-3, 2.19e-3, 6.43e-4], rtol=5e-3)`, `abs(slope + 0.940) < 5e-3` and `h_an == [970, 3999, 1164, 1541]` depend on `Generator.binomial` streams, which NumPy does not guarantee across feature releases, and `numpy>=2.0,<3` is not pinned. `test_stitched_transpile_is_wrong` asserts that a qiskit synthesis pitfall still exists, so it would fail if qiskit fixed it.
**Fix:** Keep the statistical-band assertions and drop or relax the exact-digit ones. Alternatively, pin numpy in the dev extra and comment the stitched test as a pin-canary.

### IN-07: `mlae.estimate` silently picks one branch when there is no k = 0 record

**File:** `neutron_qae/mlae.py:164-183`
**Issue:** `estimate([PowerResult(1, 1000, 999)])` returns 0.259, the first of 2k + 1 near-equal maxima. Only `ionq_estimate` guards against this. Phase 5 callers of the public API get no warning.
**Fix:** Raise a `ValueError` (or add a flag on `MLAEResult`) when no record has k = 0, unless the caller passes `allow_ambiguous=True`.

### IN-08: The `sampled` rule differs from qiskit-ionq's rule

**File:** `neutron_qae/runners.py:307-308, 338`
**Issue:** qiskit-ionq samples only when `backend.name == "ionq_simulator"` **and** `noise_model == "ideal"` (`ionq_job.py:498`). The runner looks only at `noise_model`. A QPU backend with `noise_model="ideal"` set would be labelled `sampled: true` even though its counts are `round(p·shots)`. This is not reachable through Qollab's current `get_backend("simulator")`.
**Fix:** `sampled = noise_model == "ideal" and str(getattr(backend, "name", "")) == "ionq_simulator"`.

### IN-09: The README contradicts itself on logged-out IonQ runs

**File:** `README.md:32, 49`
**Issue:** Line 32 says logged-out IonQ runs work while anonymous jobs are allowed. Line 49 says "On IonQ, a run needs a signed-in account", which matches the R8 observation.
**Fix:** Keep the signed-in statement and drop the conditional one, or state both with dates.

### IN-10: The `BackendRunner` cache is keyed on k only

**File:** `neutron_qae/runners.py:186-209`
**Issue:** `measure` and `seed_transpiler` are public, mutable attributes, but cached circuits are keyed by `k` alone. Changing `runner.measure` after a run would reuse 1-clbit circuits with the 12-clbit layout and raise a width error. Tests already mutate `run_options` this way.
**Fix:** Key the cache on `(k, self.measure, self.seed_transpiler)`, or make those attributes read-only properties.

---

_Reviewed: 2026-10-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
