# Qollab runtime findings (Phase 1 smoke test)

## Static facts (read from Qollab's runtime code, 2026-10-10)
- Pyodide v314.0.7 (Python 3.14.2, numpy 2.4.6, scipy 1.18.0, matplotlib 3.10.8 in its lockfile)
- Qollab /py index: qiskit 2.5.2 (only wasm build), qiskit-ionq 1.0.2, qiskit-aer 0.17.2
- backend preamble: built-in = BasicSimulator(); IonQ remote sim = IonQProvider("STUB").get_backend("simulator") + set_options(noise_model="<qpu>")
- qiskit_ionq installed only when an IonQ backend is selected; qiskit_aer only when an IBM noise model is selected
- main(...) is appended with positional form values; floats can arrive as ints
- One IonQ job per run (client-enforced); 403 → "anonymous user" message; proxy rejects oversized request bodies
- anon_enabled = true on 2026-10-10 (GET https://api.qollab.xyz/api/ionq/backends/simulator/cost)
- Re-uploading into an existing project skips README.md, so the write-up only updates by pasting README.md into the Project Card or by creating a new project from the archive (Pitfall 8)
- qiskit is imported by Qollab's preamble before main.py runs, so its import time shows up as the "initializing runtime" phase, not in wall_clock_s (Pitfall 10)

### What the ideal_mode values test
- `none`: keeps the noise model chosen in the Select QPU dialog (e.g. forte-1); counts are noisy.
- `kwarg`: sends `noise_model="ideal"` as a `backend.run` argument; if accepted, the counts are exact `round(p*shots)` with no shot noise.
- `set_options`: sets `backend.set_options(noise_model="ideal")` before the run; if accepted, the counts are sampled client-side with real shot statistics.
- The built-in BasicSimulator ignores the kwarg with a `UserWarning` and rejects `set_options` with an `AttributeError`, so `run_toy` applies both only on IonQ.

## Empirical runs
| # | Date/time ET | Logged in? | Browser | Backend entry | ideal_mode | accepted | noise_verdict | python / numpy / qiskit / qiskit_ionq | wall_clock_s | perf (q: run_s) |
|---|--------------|-----------|---------|---------------|-----------|----------|---------------|------------------------------------|--------------|-----------------|

## Raw reports
<!-- paste each QOLLAB_RUNTIME_REPORT=... line verbatim -->

## Conclusions for later phases
- noise_model="ideal" via kwarg: ACCEPTED / REJECTED (error: ...)
- noise_model="ideal" via set_options: ACCEPTED / REJECTED
- Phase 4 IonQ path should use: ...
- Live-run budget in Pyodide (Phase 6 quick mode): ~N qubits at depth 20 within X s
- Published URL: https://qollab.xyz/u/<user>/<project>   (version v0.0-smoke)
- Before the final publish (Phase 6): re-run the built-in smoke test, re-check the qiskit version in https://qollab.xyz/py/index.json and re-check the anon_enabled flag.
