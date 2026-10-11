# Quantum Neutron Transport: SPARC First Wall

This project compares quantum amplitude estimation (QAE) with classical Monte Carlo on one fusion-relevant question: what fraction of 14 MeV neutrons passes through a tungsten-armored steel first wall like the one in MIT/CFS's SPARC tokamak. A classical Python Monte Carlo and a Qiskit amplitude-estimation circuit estimate the same transmission fraction, so the error of each method can be plotted against the number of samples it uses. It is built for the Qollab x IonQ Hackathon, Quantum Impact theme.

This effort is supported by Qollab & IonQ.

## Status

Phase 1 is the Qollab smoke test and compliant skeleton. It reports what the Qollab runtime provides, runs a small GHZ circuit on the selected backend and prints `SMOKE TEST PASSED`. It is still available as `mode = smoke`.

Phase 2 added the SPARC first-wall problem definition, with cited ENDF/B-VIII.0 cross sections, and the frozen `Kernels` contract that the classical and quantum engines share (see [docs/PHYSICS.md](docs/PHYSICS.md)).

Phase 3 added the classical baseline:
- a continuous Woodcock delta-tracking Monte Carlo (the physics reference);
- a matched discrete lattice Monte Carlo that samples exactly the model the quantum circuit encodes;
- an injected random source driving both.

Phase 4 added the quantum part (see [docs/QUANTUM.md](docs/QUANTUM.md)):
- the contract-checked oracle A for that same model;
- its Grover powers, transpiled once to an IonQ-safe basis;
- a maximum-likelihood amplitude estimator (MLAE) that reports its cost as applications of A;
- the QAE mode of `main.py`, which runs all of this on Qollab.

The error-versus-cost figures arrive in Phase 5.

## Run it on Qollab

1. Use a browser that supports WebAssembly JSPI: a recent Chrome, Edge or Opera, or Firefox 153 or later. Qollab runs Python inside the browser, so other browsers cannot start the runtime.
2. Open the project page and press **Run**.
3. In **Select QPU**, pick one of:
   - `Built-in simulator`: an ideal simulator that runs entirely in your browser. This is the path judges use, and it needs no account.
   - `IonQ Forte 1`: IonQ's remote noise-model simulator. The project sends exactly one job per run, as Qollab requires. Logged-out IonQ runs work only while Qollab allows anonymous IonQ jobs; if you see "Can't run quantum jobs as an anonymous user at the moment", sign in and run again.
4. Optionally change the **Run settings** fields. Every value is checked before any job is sent; an out-of-range value stops the run with an error and is never silently adjusted.
   - `mode` (default `qae`): `qae` runs amplitude estimation; `smoke` reproduces the Phase 1 smoke test.
   - `k` (default 1): the Grover power for an IonQ run, an integer from 0 to 8.
   - `shots` (default 1000): an integer from 2 to 10,000. On the Built-in simulator it is the number of shots per Grover power; on IonQ it is the number of shots of the single circuit.
   - `ideal_mode` (default `set_options`): `set_options` or `none` in `qae` mode.
     - `set_options` sets IonQ's `noise_model="ideal"` on the backend first. The counts are then real samples.
     - `none` keeps the noise model chosen in Select QPU. The counts are then rounded probabilities, which are reported but never used for statistics.
     - `smoke` mode also accepts `kwarg`.
   - `model` (default `Q1`): `Q1` (12 qubits), `Q1lite` (8 qubits, the IonQ size fallback) or `Q0` (5 qubits, no collision).

   `k` and `ideal_mode` apply to IonQ runs only; the Built-in run ignores them.
5. On the **Built-in simulator**, the run:
   - checks the circuit against the exact answer;
   - sends one job of four circuits (Grover powers k = 0, 1, 2, 4);
   - prints one `QAE_REPORT=` line (JSON), then an `MLAE a_hat=... N_A=...` line and an `IonQ records` line with the estimate from the IonQ runs stored in `data/ionq_runs.json`;
   - ends with `QAE RUN COMPLETED`.
6. On **IonQ**, a run needs a signed-in account. It sends exactly one job carrying one circuit (A followed by k Grover steps), prints one `IONQ_RECORD=` line (JSON with the counts and resources) and ends with `IONQ RUN ACCEPTED`, or `IONQ RUN FAILED: <error>` if the job was refused. The IonQ estimate is built from several runs (k = 0, 1, 2); see [docs/QUANTUM.md](docs/QUANTUM.md).
7. With `mode = smoke` the console shows one `QOLLAB_RUNTIME_REPORT=` line (runtime versions, backend, counts, timings), then `SMOKE TEST PASSED`.

## Run it locally

You need Python 3.14.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
.venv/bin/python scripts/run_local.py                 # QAE mode, as on Qollab: prints QAE RUN COMPLETED
.venv/bin/python scripts/run_local.py --seed 2026     # reproducible Built-in counts
.venv/bin/python scripts/run_local.py --mode smoke    # prints SMOKE TEST PASSED
.venv/bin/python -m pytest
```

Keep calling tools as `.venv/bin/python -m pip` and `.venv/bin/python -m pytest`: if the checkout path contains spaces, the console-script shebangs inside the venv can break, while `python -m` always works.

`.venv/bin/python -m pip install -e ".[dev]"` adds qiskit-aer, qiskit-algorithms and ruff.

`scripts/run_local.py` options:
- `--mode`, `--k`, `--shots`, `--ideal-mode` and `--model` set the matching Run settings fields; fields you leave out keep `main()`'s defaults.
- `--seed N` makes the counts reproducible.
- `--backend aer` runs the same `main.py` on Aer.
- `--backend fake-ionq` exercises the IonQ path with a local test double.

Other local tools:
- `.venv/bin/python scripts/qae_local.py resources` prints the resource table.
- `scripts/qae_local.py aer-mlae` and `scripts/qae_local.py analytic` run local estimates.
- `.venv/bin/python scripts/ingest_ionq_records.py PASTE` turns a pasted Qollab console output into validated records in `data/ionq_runs.json`.

## Repository layout

```text
main.py            Qollab entry point; main(...) reads the backend Qollab injects
requirements.txt   Qollab-facing dependencies (only qiskit==2.5.2)
pyproject.toml     local install, dev extras and pytest config (not used by Qollab)
LICENSE            MIT license
README.md          this file; also the Qollab project write-up
neutron_qae/       the Python package:
  smoke.py         Phase 1 Qollab smoke test (main.py mode=smoke)
  nuclear_data.py  cited 14.1 MeV ENDF/B-VIII.0 cross sections and material compositions
  problem.py       ProblemSpec: the SPARC first-wall slab, geometry and one-group materials
  kernels.py       frozen Kernels contract v1 shared by the classical and quantum engines
  exact.py         exact lattice solver (literal bit-string enumeration, T0 and T1)
  random_source.py the injected random source every Monte Carlo engine draws from
  mc_continuous.py continuous Woodcock delta-tracking Monte Carlo (physics reference)
  mc_lattice.py    matched discrete lattice Monte Carlo (the classical baseline)
  oracle.py        quantum state preparation A for Q0, Q1 and Q1lite, behind the contract gate
  grover.py        Grover powers A·Q^k, transpiled once to an IonQ-safe basis; resource table
  mlae.py          maximum-likelihood amplitude estimation and the cost N_A
  runners.py       analytic, injected-backend and IonQ one-circuit runners; IonQ record schema
data/              small data files loaded by literal path (each at most 2 MB)
  smoke_probe.json Phase 1 literal-path probe
  ionq_runs.json   IonQ records ingested from Qollab console output
scripts/           local-only tools: run_local.py (injects a simulator like Qollab), qae_local.py
                   (resource table, local estimates), ingest_ionq_records.py (paste -> data/ionq_runs.json)
tests/             pytest suite: compliance gates, smoke test, physics, contract, quantum and docs checks
  golden/          frozen contract values (tests/golden/kernels_v1.json)
docs/              project records: QOLLAB-RUNTIME.md (Qollab runtime findings), PHYSICS.md (physics, data
                   sources and the Kernels contract), QUANTUM.md (circuits, resources, MLAE, IonQ protocol)
```

## Quantum oracle and amplitude estimation

The quantum half estimates the same transmission fraction as the matched classical Monte Carlo. Details and measurements are in [docs/QUANTUM.md](docs/QUANTUM.md).

- **Q1** prepares the K = 1 lattice model on 12 qubits.
  - Each random choice (first-collision column, scatter or absorb, direction bin, escape) gets its own register; one flag qubit marks transmission.
  - Before any job, its flag probability is checked against the exact lattice answer T1 = 0.24300446519524305 to within 1e-12.
- **Circuit sizes.** After one full transpile to a basis with at most one control per gate, the Q1 circuits are:

  | Circuit | Qubits | CX |
  |---|---|---|
  | A | 12 | 313 |
  | A·Q^1 | 12 | 1,503 |
  | A·Q^2 | 12 | 2,693 |

  All stay within 24 qubits.
- **MLAE** combines the counts of several Grover powers k into one estimate with a Fisher standard error. Its cost is N_A = sum of shots (2k + 1), the number of applications of A. One application of A is the same unit as one classical history.
- **IonQ protocol.** Qollab's IonQ path carries one circuit per run, so the IonQ estimate is built from separate runs at k = 0, 1 and 2 with `ideal_mode = set_options`. Each run prints an `IONQ_RECORD=` line. Records are ingested into `data/ionq_runs.json`, and the Built-in run shows the resulting IonQ-only estimate to every visitor.
- **IonQ results (2026-10-11, execution proof plus a three-power IonQ-only estimate).**
  - Three IonQ Forte 1 runs on Qollab (k = 0, 1, 2; 1000 shots each; ideal, sampled) were all accepted, with request bodies up to 307 KB. They gave P(flag) = 0.267, 0.988 and 0.349, against the exact 0.2430, 0.9994 and 0.2859.
  - The IonQ-only MLAE estimate is a_hat = 0.228671 (se 2.24e-03, N_A = 9,000). That is 6.4 sigma below T1, because the k = 1 and k = 2 points depart from the exact circuit far beyond shot noise. It is reported as found; see [docs/QUANTUM.md](docs/QUANTUM.md).
  - The Built-in run of the same upload ran the full QAE in the browser: a_hat = 0.242072, se = 1.26e-03, N_A = 18,000.
  - No speedup is claimed from these runs.
- **Honest framing.**
  - The comparison is sampling complexity only: estimation error against N_A, roughly 1/N_A for MLAE against 1/sqrt(N) for classical Monte Carlo.
  - It is not a wall-clock or quantum-advantage claim.
  - The full error curve comes from the analytic and Aer runners (Phase 5). The IonQ runs show that the real circuit executes and give a three-power estimate.
  - IonQ noise-model runs are reported, never used for statistics.

## Rules every module follows

- The backend is injected by Qollab (or by `scripts/run_local.py`) and passed into package functions as a parameter. Package code never creates a backend.
- Nothing reachable from `main.py` imports qiskit-aer, qiskit-algorithms or qiskit-ionq. Those packages are not installed for every Qollab backend choice.
- Data files stay at or under 2 MB and are referenced by literal path strings in the code, because Qollab only loads data files whose path appears as a literal.
- The `main()` signature stays on one line, with `int`, `float`, `str` or `bool` parameters and literal defaults, so Qollab can build the Run settings form. `main.py` never calls `main()` itself; Qollab does.
- One job per run and one circuit per job on Qollab's IonQ backends: Qollab allows a single `backend.run` call per run and its IonQ proxy accepts only job type `ionq.circuit.v1`, so the circuit is passed to `backend.run` on its own, never in a list (qiskit-ionq sends any list as `ionq.multi-circuit.v1`, which Qollab rejects).
- `tests/test_compliance.py` enforces these rules on every test run.
- Physics enters classical and quantum code only through the frozen `Kernels` contract (`neutron_qae/kernels.py`, `KERNELS_CONTRACT_VERSION = "1"`, values frozen in `tests/golden/kernels_v1.json`). Import it; never rebuild private tables. Changing it is a contract change, described in docs/PHYSICS.md. `tests/test_kernels_golden.py` checks the freeze on every test run.

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
