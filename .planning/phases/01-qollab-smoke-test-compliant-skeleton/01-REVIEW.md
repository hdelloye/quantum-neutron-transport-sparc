---
phase: 01-qollab-smoke-test-compliant-skeleton
reviewed: 2026-10-10T20:14:20Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - .gitattributes
  - .gitignore
  - LICENSE
  - README.md
  - data/smoke_probe.json
  - docs/QOLLAB-RUNTIME.md
  - main.py
  - neutron_qae/__init__.py
  - neutron_qae/smoke.py
  - pyproject.toml
  - requirements.txt
  - scripts/run_local.py
  - tests/compliance_checks.py
  - tests/test_compliance.py
  - tests/test_docs.py
  - tests/test_smoke.py
findings:
  critical: 1
  warning: 8
  info: 7
  total: 16
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-10T20:14:20Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

This review covers the Phase 1 Qollab smoke test (`main.py`, `neutron_qae/smoke.py`), the local runner, the static compliance gates and their tests, and the docs and packaging files. The suite passes (36 passed), and `git archive HEAD` ships exactly the 9 intended files, so the `.gitattributes` export-ignore rules work.

Every finding below was reproduced locally with stand-in backends (scratch scripts, not committed). The main problems:

1. **One blocker.** On a backend whose `options.noise_model` is a `NoiseModel` object, `main()` crashes at its first `json.dumps`. That backend is the Aer path that Qollab uses for its IBM noise-model choices.
2. **Uncaught failures.** Several code paths sit outside the `try` in `run_toy`, and `perf_probe` has no `try` at all. When they fail, the run ends in a traceback with no `QOLLAB_RUNTIME_REPORT=` line.
3. **Weak compliance gates.** The gates have confirmed false negatives: tuple-unpacking `backend`, `x = main()`, `AerSimulator.from_backend`, a module-level global `backend` in the package, and non-literal `__import__`. `tests/test_compliance.py` also claims every check has a negative test, which is not true.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `main()` crashes before any job on Aer noise-model backends, because `NoiseModel` is not JSON-serialisable

**File:** `neutron_qae/smoke.py:61`, `main.py:17`
**Issue:** `backend_report` puts `getattr(opts, "noise_model", None)` into the report as it is. On the built-in and IonQ backends this value is `None` or a string, so the JSON dump works. But `docs/QOLLAB-RUNTIME.md:7` records that Qollab loads `qiskit_aer` when an IBM noise model is selected. That backend is an `AerSimulator` built with `noise_model=` or `from_backend(...)`, so `options.noise_model` holds a `qiskit_aer.noise.NoiseModel` instance. `json.dumps(report, indent=1)` on `main.py:17` then raises `TypeError: Object of type NoiseModel is not JSON serializable`. The run dies with a traceback before the toy circuit runs and before any `SMOKE TEST` line. I reproduced this with a stand-in options object: `TypeError Object of type NoiseModel is not JSON serializable`. The same `backend_report` pattern will be copied into later phases' entry point.
**Fix:**
```python
def _jsonable(v):
    return v if v is None or isinstance(v, (str, int, float, bool)) else f"<{type(v).__name__}>"

    "options_noise_model": _jsonable(getattr(opts, "noise_model", None)),
    "options_shots": _jsonable(getattr(opts, "shots", None)),
```
As a second safeguard, call `json.dumps(report, default=repr)` in `main.py` lines 17, 21 and 25. Add a test that injects a backend whose `options.noise_model` is an arbitrary object.

## Warnings

### WR-01: Failures outside `run_toy`'s `try`, and anywhere in `perf_probe`, lose the whole report

**File:** `neutron_qae/smoke.py:103`, `neutron_qae/smoke.py:109`, `neutron_qae/smoke.py:152-154`
**Issue:** `run_toy` is designed to record `accepted=False` and an error string instead of crashing. Three calls bypass that design:
- `backend.set_options(noise_model="ideal")` (line 103) runs before the `try`. A backend that rejects the option raises out of `main()`. Reproduced: `AttributeError: Options field noise_model is not valid for this backend`.
- `transpile(ghz(n), backend)` (line 109) runs before the `try`. On a backend narrower than `n` (n is clamped only to 20) it raises `CircuitTooWideForTarget`. Reproduced on `GenericBackendV2(5)` with the default `ghz_qubits=6`.
- `perf_probe` has no error handling at all. `perf_qubits` defaults to 12 and is clamped only to 24, so on a backend narrower than that it raises `CircuitTooWideForTarget` (reproduced on a 5-qubit target). It also raises after the toy job already succeeded.

In each case the `QOLLAB_RUNTIME_REPORT=` line (main.py:21) and the `SMOKE TEST` verdict are never printed. That output is the evidence the smoke test exists to produce.
**Fix:** Move the `set_options` and `transpile` calls inside the existing `try`. Wrap the body of `perf_probe` in `try/except Exception as exc: return {"error": f"{type(exc).__name__}: {exc}"}`. Clamp `n` and `qubits` to `getattr(backend, "num_qubits", 24)`.

### WR-02: The one-job-per-run guard relies on a module-name denylist, so an unrecognised remote backend gets a second job

**File:** `neutron_qae/smoke.py:67-69`, `neutron_qae/smoke.py:139`
**Issue:** `perf_probe` skips only when `type(backend).__module__.startswith("qiskit_ionq")`. Suppose Qollab wraps the IonQ backend in a subclass defined in its own module, or adds another remote one-job vendor. `is_ionq` then returns `False`, and `perf_probe` sends a second `backend.run`. Qollab aborts the run on that second job. Reproduced: a subclass of an IonQ-module class with `__module__ = "qollab_runtime"` gives `is_ionq(...) == False`. The guard fails open, and this rule is the one the project calls hard.
**Fix:** Fail closed. Run the perf probe only on backends known to be local, for example:
```python
LOCAL_BACKENDS = ("qiskit.providers.basic_provider", "qiskit_aer")
def is_local(backend) -> bool:
    return type(backend).__module__.startswith(LOCAL_BACKENDS)
```
Also make `is_ionq` check the MRO (`any(c.__module__.startswith("qiskit_ionq") for c in type(backend).__mro__)`) and `str(getattr(backend, "name", "")).startswith("ionq")`.

### WR-03: The `noise_verdict` heuristic mislabels runs, and Phase 4 decisions rest on it

**File:** `neutron_qae/smoke.py:129-133`
**Issue:** `exact_half` is true only when both GHZ outcomes equal exactly `total / 2`, which causes two kinds of mislabel:
- **Sampled runs labelled exact.** A genuinely sampled ideal run hits 100/100 at 200 shots with probability C(200,100)/2^200 = 5.6%. It is then labelled "ideal, exact round(p*shots) (no shot noise)".
- **Exact runs labelled sampled.** With an odd shot count, or any state that is not 50/50, the counts from the exact-probability path can never be exactly half. They are then labelled "ideal, sampled".

`docs/QOLLAB-RUNTIME.md:85-88` turns this label from a single run (R5) into a project rule ("Never use the kwarg path for statistics"). The conclusion matches the qiskit-ionq source note in CLAUDE.md, but the code's label is not reliable evidence on its own, and later phases may reuse the heuristic.
**Fix:** Label the result "consistent with exact probabilities" rather than asserting it, and report the binomial likelihood of the observed split. Better, run a deterministic discriminator: an unbalanced circuit (e.g. `ry(θ)` with p=0.3 at shots=1000), where exact-probability output always equals `round(p*shots)` and sampled output almost never does. Record in `docs/QOLLAB-RUNTIME.md` that the R5 verdict is a 1-in-18 chance event under sampling.

### WR-04: A free-text `ideal_mode` typo in the Qollab form crashes the judged run

**File:** `neutron_qae/smoke.py:95-96`, `main.py:18`
**Issue:** `ideal_mode` is a `str` Run-settings field that judges type by hand. Any value other than the exact strings `none`, `kwarg` or `set_options` (e.g. `"Kwarg"`, `" none"`, `""`) raises `ValueError` out of `main()` after the runtime report is printed. That includes the Built-in simulator, where the value is documented as irrelevant (README.md:21). Reproduced: `ValueError ideal_mode must be one of ... got 'Kwarg'`.
**Fix:** Normalise with `ideal_mode = str(ideal_mode).strip().lower() or "none"`. Then either fall back to `"none"` with a printed warning, or record the error in `out` instead of raising. This keeps the judged Built-in path immune to form input.

### WR-05: Compliance gates have confirmed false negatives (and one false positive)

**File:** `tests/compliance_checks.py:71-76`, `tests/compliance_checks.py:125-139`, `tests/compliance_checks.py:142-154`, `tests/compliance_checks.py:157-168`, `tests/compliance_checks.py:178`, `tests/compliance_checks.py:192-197`
**Issue:** These gates are described as enforcing the platform's hard rules, but each of the following passes them (all reproduced against throwaway projects):
- `backend_assigned_in_main` only inspects `ast.Name` targets. `backend, other = ...` (Tuple target) and `for backend in ...` both return `[]`.
- The `main_signature_problems` call check only matches a bare `main()` expression statement. `result = main()` and `print(main())` at module level both return `[]`. Either would run main twice on Qollab.
- `backend_constructions` does not list `from_backend`. `AerSimulator.from_backend(backend)` returns `[]`, and this is the standard way to build a noisy Aer backend.
- `package_uses_global_backend` only inspects function bodies. A module-level `RESULT = backend.run(...)` in the package returns `[]`.
- `forbidden_imports` only sees `__import__` or `import_module` with a literal first positional argument. `__import__(name)` with a variable, and `import_module(name="qiskit_aer")`, both return `set()`. `smoke.py:17` already uses the variable form (see IN-07).
- False positive: `main_signature_problems` requires the line to end with `:`. The valid one-line signature `def main(shots: int = 10):  # form` is rejected.
**Fix:**
- Walk targets recursively: `ast.Tuple`/`ast.List`/`ast.Starred`, plus `ast.For.target`, `ast.withitem.optional_vars`, `ast.NamedExpr.target`, and `ast.alias.asname == "backend"`.
- Flag any `ast.Call` with `func.id == "main"` anywhere in the module except inside `def main` itself.
- Add `"from_backend"` to `BACKEND_FACTORY_ATTRS`.
- Scan module-level `Load` of `backend` in package files.
- Flag any non-literal `__import__`/`import_module` call in reachable code, unless it is on an explicit allow-list.
- Strip comments with `tokenize` before the `endswith(":")` test, or compare against `fn.lineno == fn.body[0].lineno` / `fn.end_lineno` of the args.

### WR-06: `tests/test_compliance.py` claims every check has a negative test; four have none

**File:** `tests/test_compliance.py:1`, `tests/test_compliance.py:19-22`, `tests/test_compliance.py:33-46`
**Issue:** The module docstring says "Each check has a negative test proving it can fail". There is no negative test for:
- `backend_assigned_in_main`
- the "do not call main() at module level" and `*args/**kwargs` branches of `main_signature_problems` (only the `__name__` guard, annotation, default and multi-line cases are exercised)
- `qollab_upload_files` / the 100-file cap
- the data-file literal-path test

A check that never fires would pass silently. WR-05 shows that `backend_assigned_in_main` and the main-call branch already miss common cases.
**Fix:** Add parametrised negative cases for each, e.g. `"backend = None\n"`, `"backend, x = 1, 2\n"`, `"main()\n"`, `"x = main()\n"`, a 101-file fake project, and an unreferenced `data/extra.json`. Alternatively, correct the docstring.

### WR-07: The data literal-path test fails on macOS `.DS_Store` files and on single-quoted literals

**File:** `tests/test_compliance.py:33-38`
**Issue:** `(ROOT / "data").rglob("*")` lists every file on disk, including ignored ones. Opening `data/` in Finder creates `data/.DS_Store`. The file is git-ignored and never shipped, yet it makes the test fail with `missing == ['data/.DS_Store']`. The test also searches only for the double-quoted form `"data/x"`. A valid single-quoted literal `'data/x'` (Qollab accepts any literal) is reported missing. Conversely, a double-quoted path that appears only in a comment satisfies the test.
**Fix:** Build the data list from `cc.repo_files(ROOT)` filtered to the `data/` prefix. Collect real string literals by AST-walking the reachable files for `ast.Constant` str values, and test membership against that set.

### WR-08: README's IonQ instructions contradict the recorded logged-out run

**File:** `README.md:17`
**Issue:** The README tells judges that logged-out IonQ runs "work only while Qollab allows anonymous IonQ jobs". It implies that a sign-in is needed only when the "anonymous user at the moment" message appears. `docs/QOLLAB-RUNTIME.md:35,90` records the opposite: run R8 was refused logged-out ("credits apply, you need to sign in") while the cost endpoint reported `anon_enabled: true`. A judge following the README would expect the logged-out IonQ path to work. This README is also the Qollab write-up.
**Fix:** State the observed behaviour, for example: "Running on IonQ Forte 1 requires signing in to Qollab (anonymous IonQ jobs were refused on 2026-10-10); the Built-in simulator runs logged out." Add a `test_docs.py` assertion that the README mentions sign-in for IonQ.

## Info

### IN-01: `_package_of` has two identical branches

**File:** `tests/compliance_checks.py:32-37`
**Issue:** Both the `__init__` branch and the fall-through return `".".join(parts[:-1])`, so the `if` is dead code. The result is still correct in both cases, but the code reads as if one branch were meant to differ.
**Fix:** Collapse to a single `return ".".join(rel.parts[:-1])` with a comment explaining why it is correct for both `pkg/__init__.py` and `pkg/mod.py`.

### IN-02: `runtime_report` catches only `OSError` when reading the probe file

**File:** `neutron_qae/smoke.py:47-51`
**Issue:** A malformed JSON file (`json.JSONDecodeError`, a `ValueError`) or a missing key (`KeyError`) crashes the smoke run. A probe that is meant to report problems should not crash on them.
**Fix:** `except (OSError, ValueError, KeyError) as exc:`.

### IN-03: `sendFile` failures other than `ImportError` crash the run before the verdict line

**File:** `main.py:22-27`
**Issue:** Inside Pyodide, `sendFile` can raise a `JsException`, or a `TypeError` if the signature differs. Either one aborts `main()` after the report is printed but before `SMOKE TEST PASSED/FAILED`.
**Fix:** `except Exception as exc: print(f"sendFile unavailable: {type(exc).__name__}", flush=True)`.

### IN-04: `scripts/run_local.py` always exits 0 and exposes only `--shots`

**File:** `scripts/run_local.py:24-32`
**Issue:** The return value of `entry.main(...)` is discarded, so `SMOKE TEST FAILED` still exits 0, and automation cannot detect a failure. `ghz_qubits`, `ideal_mode` and `perf_qubits` cannot be set locally.
**Fix:** Add the three arguments and end with `sys.exit(0 if report["toy"]["accepted"] else 1)`.

### IN-05: Stale comment in the upload test

**File:** `tests/test_compliance.py:44`
**Issue:** "LICENSE and README.md ... do not exist yet" is false now; both exist and are asserted in `test_docs.py:78-79`.
**Fix:** Delete the comment, or add `LICENSE` and `README.md` to the assertion on line 45.

### IN-06: `requires-python` disagrees with the documented local requirement

**File:** `pyproject.toml:12`, `README.md:27`
**Issue:** `pyproject.toml` allows Python 3.12, while the README says "You need Python 3.14" and Qollab runs 3.14.2. Installing on 3.12 or 3.13 is allowed but never tested.
**Fix:** Set `requires-python = ">=3.14"`, or soften the README to "3.14 recommended (matches Qollab)".

### IN-07: `_version` dynamically imports `qiskit_ionq` from code reachable from `main.py`, invisibly to the gate

**File:** `neutron_qae/smoke.py:15-17`, `neutron_qae/smoke.py:39`
**Issue:** `__import__(mod_name)` with `mod_name="qiskit_ionq"` imports a package that the project rules say must not be imported from code `main.py` reaches. It is harmless here because the call is wrapped in `try`, and this is deliberate for the runtime probe. But the forbidden-import gate cannot see it (WR-05), so the exception is undocumented and the same pattern with `qiskit_aer` would also pass.
**Fix:** Add a comment naming this as the one sanctioned dynamic probe, and add an allow-list entry (`smoke.py:_version`) once the gate starts flagging non-literal dynamic imports.

---

_Reviewed: 2026-10-10T20:14:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
