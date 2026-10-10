# Quantum Neutron Transport: SPARC First Wall

This project compares quantum amplitude estimation (QAE) with classical Monte Carlo on one fusion-relevant question: what fraction of 14 MeV neutrons passes through a tungsten-armored steel first wall like the one in MIT/CFS's SPARC tokamak. A classical Python Monte Carlo and a Qiskit amplitude-estimation circuit estimate the same transmission fraction, so the error of each method can be plotted against the number of samples it uses. It is built for the Qollab x IonQ Hackathon, Quantum Impact theme.

This effort is supported by Qollab & IonQ.

## Status

Phase 1 is the Qollab smoke test and compliant skeleton: a toy Qiskit `main.py` that reports what the Qollab runtime provides, runs a small GHZ circuit on the selected backend and prints `SMOKE TEST PASSED`. The physics and quantum parts (the problem specification, the shared `Kernels` contract, the classical Monte Carlo, the quantum oracle, maximum-likelihood amplitude estimation (MLAE) and the figures) arrive in later phases as modules under `neutron_qae/`.

## Run it on Qollab

1. Use a browser that supports WebAssembly JSPI: a recent Chrome, Edge or Opera, or Firefox 153 or later. Qollab runs Python inside the browser, so other browsers cannot start the runtime.
2. Open the project page and press **Run**.
3. In **Select QPU**, pick one of:
   - `Built-in simulator`: an ideal simulator that runs entirely in your browser. This is the path judges use, and it needs no account.
   - `IonQ Forte 1`: IonQ's remote noise-model simulator. The project sends exactly one job per run, as Qollab requires. Logged-out IonQ runs work only while Qollab allows anonymous IonQ jobs; if you see "Can't run quantum jobs as an anonymous user at the moment", sign in and run again.
4. Optionally change the **Run settings** fields:
   - `shots` (default 200): shots for the toy circuits.
   - `ghz_qubits` (default 6): size of the GHZ test circuit.
   - `ideal_mode` (default `none`): one of `none`, `kwarg` or `set_options`. On IonQ, `kwarg` passes `noise_model="ideal"` to `backend.run` and `set_options` sets it on the backend first; `none` keeps the noise model chosen in Select QPU. The built-in simulator is already ideal, so the value only matters on IonQ.
   - `perf_qubits` (default 12): width of a timing probe circuit (skipped on IonQ to keep one job per run).
5. Expect the console to show one line starting with `QOLLAB_RUNTIME_REPORT=` followed by a JSON report (Python, NumPy and Qiskit versions, backend, counts, timings), then `SMOKE TEST PASSED`.

## Run it locally

You need Python 3.14.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
.venv/bin/python scripts/run_local.py      # prints SMOKE TEST PASSED
.venv/bin/python -m pytest
```

Keep calling tools as `.venv/bin/python -m pip` and `.venv/bin/python -m pytest`: if the checkout path contains spaces, the console-script shebangs inside the venv can break, while `python -m` always works.

For later phases, `.venv/bin/python -m pip install -e ".[dev]"` adds qiskit-aer, qiskit-algorithms and ruff; `.venv/bin/python scripts/run_local.py --backend aer` then runs the same `main.py` on Aer. `scripts/run_local.py` also accepts `--shots N`.

## Repository layout

```text
main.py            Qollab entry point; main(...) reads the backend Qollab injects
requirements.txt   Qollab-facing dependencies (only qiskit==2.5.2)
pyproject.toml     local install, dev extras and pytest config (not used by Qollab)
LICENSE            MIT license
README.md          this file; also the Qollab project write-up
neutron_qae/       the Python package (smoke test now; physics and QAE modules later)
data/              small data files loaded by literal path (each at most 2 MB)
scripts/           local-only tools, e.g. run_local.py which injects a simulator like Qollab
tests/             pytest suite: compliance gates, smoke test, docs checks
docs/              project records, e.g. QOLLAB-RUNTIME.md with the Qollab runtime findings
```

## Rules every module follows

- The backend is injected by Qollab (or by `scripts/run_local.py`) and passed into package functions as a parameter. Package code never creates a backend.
- Nothing reachable from `main.py` imports qiskit-aer, qiskit-algorithms or qiskit-ionq. Those packages are not installed for every Qollab backend choice.
- Data files stay at or under 2 MB and are referenced by literal path strings in the code, because Qollab only loads data files whose path appears as a literal.
- The `main()` signature stays on one line, with `int`, `float`, `str` or `bool` parameters and literal defaults, so Qollab can build the Run settings form. `main.py` never calls `main()` itself; Qollab does.
- One `backend.run` call per run on IonQ: all circuits go in a single job.
- `tests/test_compliance.py` enforces these rules on every test run.

## Libraries, tools and licenses (disclosure)

| Component | Version | How we use it | License |
|-----------|---------|---------------|---------|
| Qiskit | 2.5.2 | Circuits, transpilation, BasicSimulator | Apache-2.0 |
| qiskit-ionq | 1.0.2 on Qollab (1.1.1 locally) | IonQ simulator backend provided by Qollab's runtime | Apache-2.0 |
| NumPy | Pyodide build on Qollab (2.x) | Numerics | BSD-3-Clause (bundled parts: 0BSD, MIT, Zlib, CC0-1.0) |
| SciPy / Matplotlib | Pyodide builds | Later phases: fitting, figures | BSD-3-Clause / Matplotlib License (PSF-based) |
| qiskit-aer, qiskit-algorithms | 0.17.2, 0.4.0 | Local tests and precomputation only; never run on Qollab | Apache-2.0 |
| pytest, ruff | 9.1.1, 0.16.10 | Testing, linting | MIT |
| Pyodide | 314.0.7 | Qollab's in-browser Python runtime (not redistributed by us) | MPL-2.0 |
| Claude Code (Anthropic) | hosted service (Claude Opus and Sonnet models) | AI coding assistant for research, planning, code and docs drafting, reviewed by the team | Anthropic usage terms; Anthropic assigns its rights in outputs to the user |
| GSD Core (@opengsd/gsd-core) | 1.16.0 | AI workflow framework driving research, planning and execution | MIT |

All third-party libraries are used under their open-source licenses, which permit use in an MIT-licensed project with their notices kept, so the team may use them. No third-party source code is copied into this repository; if any is vendored later, it keeps its license header and is listed here. The hackathon rules allow AI tools and open-source libraries when they are disclosed, and this section is that disclosure.

## License

MIT. See [LICENSE](LICENSE).
