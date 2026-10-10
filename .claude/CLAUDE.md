<!-- GSD:project-start source:PROJECT.md -->

## Project

**Quantum Neutron Transport: SPARC First Wall**

A hybrid classical plus quantum Monte Carlo neutron transport simulation of a 2D slab representing the first wall of MIT/CFS's SPARC tokamak, built for the Qollab × IonQ Hackathon (Quantum Impact theme). A classical Python Monte Carlo tracks 14 MeV neutrons through a tungsten-armored steel wall; a Qiskit quantum amplitude estimation (QAE) circuit estimates the same transmission fraction on IonQ's simulator within 24 qubits. The deliverable compares the two: error versus number of shots, plus overlaid exit-position histograms. Built by Hippolyte first, then handed to teammates via GitHub.

**Core Value:** Show, on a real fusion-relevant transport problem, that quantum amplitude estimation reaches a target accuracy with fewer samples than classical Monte Carlo, with an honest classical baseline sitting next to it.

### Constraints

- **Tech stack**: Python for the classical engine, Qiskit for the quantum circuits — hackathon rules require Qiskit; classical baseline in plain Python/numpy
- **Hardware**: ≤ 24 qubits — IonQ simulator limit available through Qollab
- **Timeline**: Submission by Oct 11 2026, 7:00 PM ET — hard hackathon deadline; partial submissions still eligible
- **License**: MIT, with attribution line and disclosure of all external libraries and AI tools used
- **Platform**: Must run without error on the Qollab-provided IonQ simulator, from a logged-out browser
- **Scaling honesty**: The speedup argument is sampling complexity (1/N vs 1/sqrt(N)), never "neutrons are quantum so qubits model them better"

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## TL;DR (read this first)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | **3.14** (local); Qollab runtime is Python 3.14 on Pyodide | Language | Matches the Qollab runtime ("The runtime is Python 3.14 with Qiskit 2.x"). Every package below installs cleanly on 3.14 (verified in a fresh venv on this Mac; `/Library/Frameworks/.../3.14` is already installed). numpy 2.5 needs Python 3.12 or later and matplotlib 3.11 needs 3.11 or later, so older Pythons are out anyway. | HIGH |
| qiskit | **2.5.2** (pin exactly) | Circuits, transpiler, `grover_operator`, `Statevector`, `BasicSimulator` | Qollab adds `qiskit>=2.5.2,<3.0.0` by default. 2.6.0rc1 shipped 2026-10-02 and a 2.6.0 final could land during the hackathon, so **pin `qiskit==2.5.2` in both `requirements.txt` and `pyproject.toml`** to keep local and Qollab identical. Qollab uses your Qiskit line as written when you supply one. | HIGH (version) / MEDIUM (that pinning is strictly required) |
| numpy | 2.x (local 2.5.3; Qollab/Pyodide ships its own numpy 2.x, ~2.4) | Classical MC engine, MLE post-processing | Qollab preloads NumPy ("NumPy 2.x"). **Do not pin numpy in the Qollab `requirements.txt`.** Pyodide ships its own build, and a pin to a version Pyodide lacks stops the run. Write against the numpy 2.0 API and use `np.random.Generator` (PCG64). | HIGH |
| MLAE (own ~60-line module, or `qiskit_algorithms.MaximumLikelihoodAmplitudeEstimation.compute_mle`) | qiskit-algorithms **0.4.0** | Amplitude estimation post-processing | MLAE needs no phase-estimation ancillas, so all qubits go to the physics. All Grover powers are known up front, so the whole estimate is **one multi-circuit job**, which fits the IonQ rule. It reaches ~1/N oracle-query scaling with an exponential schedule. See "AE API decision" below. | HIGH (verified locally) |
| qiskit-ionq | **1.1.1** local (Qollab installs `qiskit_ionq>=1.0.0`; its docs reference 1.0.2) | IonQ backend | On Qollab you never instantiate it. `backend` is pre-created from `IonQProvider` when the judge picks an IonQ entry in "Select QPU". Locally it is only needed if you have your own IonQ key. It ships **no primitives**, supports multi-circuit `backend.run([...])`, and `get_counts(i)` works per circuit. | HIGH |
| qiskit-aer | **0.17.2** (local dev only) | Fast local ideal and noisy simulation for the shot sweep | 10-20x faster than `BasicSimulator` at 16-20 qubits (measured: 20 qubits, ~370 gates, 1000 shots took 0.19 s on Aer vs 3.3 s on BasicSimulator). Compatible with qiskit 2.5.2 on 3.14 (verified). Qollab ships the same pin, but only behind its PQCA library flag, so **never import it from code `main.py` reaches**. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| qiskit-algorithms | 0.4.0 | `EstimationProblem`, `MaximumLikelihoodAmplitudeEstimation`, `IterativeAmplitudeEstimation`, `AmplitudeEstimation` | **Tests and local cross-checks only**, e.g. "our MLE equals the library's MLE" and "IAE with `StatevectorSampler` agrees". It is optional on Qollab (a "Qiskit Algorithms" toggle in Libraries). The README says it is "no longer officially supported by IBM", so do not make the Qollab path depend on it. | HIGH |
| scipy | local 1.18.1 (Pyodide ships ~1.18) | Bounded refinement of the MLE (`minimize_scalar`), binomial CIs | Optional. A dense grid search over theta in numpy is enough for MLAE. Already a Qiskit dependency, so it costs nothing. | HIGH |
| matplotlib | local 3.11.2 (Pyodide ships ~3.10) | Error-vs-oracle-queries log-log plot; overlaid exit histograms | It is the only plotting option inside Qollab: `plt.show()` renders SVG in the console and `plt.savefig("x.png")` renders it and offers a download. Do not list it in `requirements.txt`; Pyodide loads it on import. Avoid APIs added in 3.11. | HIGH |
| pytest | 9.1.1 | Unit and integration tests | Standard. Use `-m "not slow"` markers so the 24-qubit or deep-schedule tests do not block every run. | HIGH |
| pytest-cov | 7.1.0 | Coverage | Optional, for documentation-quality evidence. | HIGH |
| ruff | 0.17.0 | Lint and format | One tool, zero config, keeps teammate PRs consistent. | HIGH |
| JupyterLab + ipykernel | 4.6.4 / 7.4.0 | Local exploration notebook | **Local only.** Qollab does not run notebooks; it runs a top-level `main.py`. | HIGH |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `python3.14 -m venv .venv` + `pip install -e ".[dev]"` | Environment | Simplest path for teammates. `uv` is fine as an alternative but is not installed on this machine. |
| `pyproject.toml` | Local deps and pytest/ruff config | Never used by Qollab. Qollab reads only `requirements.txt`. |
| `requirements.txt` (Qollab-facing) | Qollab runtime deps | One line: `qiskit==2.5.2`. Qollab **rejects** pip options (`-r`, `-e`, `--index-url`), environment markers and URL requirements. |
| GitHub | Team handoff | MIT `LICENSE` at the root. The rules also require MIT for any outside repo the project relies on. |
| Qollab "Upload your own files" | Deploy | Upload the folder or an archive; a top-level `main.py` makes it a Python project. Then **Publish** a version and set it as default (it is private until then). |

## AE API decision (the important part)

| Approach | Result locally | Works on Qollab IonQ? | Verdict |
|----------|----------------|-----------------------|---------|
| `MaximumLikelihoodAmplitudeEstimation(..., sampler=StatevectorSampler())` | 0.29994, OK | No. `StatevectorSampler` is local-only, and there is no Sampler path to IonQ | Use in **tests** |
| MLAE with `qiskit_aer.primitives.SamplerV2` or `BackendSamplerV2(AerSimulator)` | **FAILS**: `AerError: unknown instruction: Q` (V2 primitives do not transpile) | n/a | Avoid |
| MLAE with `transpiler=` argument | **FAILS**: bug in 0.4.0 `mlae.py` line 178 transpiles only `circuits[0]` and returns a single circuit | n/a | Avoid |
| `IterativeAmplitudeEstimation` | 0.2996, OK locally | **No.** It calls `sampler.run` once per round, so multiple jobs break the one-job-per-run rule | Local comparison only |
| Canonical `AmplitudeEstimation` (QPE) | 0.3087 grid / 0.2996 MLE | One job, but costs m extra qubits plus controlled-Q^(2^j) depth | Avoid. It burns the 24-qubit budget |
| **`transpile(circuits)` then `backend.run(circuits, shots=N)` then per-circuit `get_counts(i)` then MLE** | **0.29948, OK** | **Yes.** One multi-circuit job, which IonQ accepts | **Use this** |

# MLE: maximise sum_k [h_k log sin^2((2k+1)θ) + (N-h_k) log cos^2((2k+1)θ)] over θ in [0, π/2]

## Qollab platform facts that constrain the stack

| Fact | Consequence for this project |
|------|------------------------------|
| Python runs **in the judge's browser** on Pyodide/WASM, Python 3.14, single thread. Only the IonQ job leaves the browser. | Heavy local simulation (24-qubit statevector, deep Grover powers) will be slow or run out of memory in the browser. Precompute the large ideal shot sweep locally with Aer, ship it as a JSON data file, and have `main.py` plot it plus run one live, reduced-size configuration. |
| Entry point is a **top-level `main.py`**. The project root is the first entry on `sys.path`, so packages in subfolders import normally. | Use a **flat layout** with the package folder at the repo root. **Not** `src/` layout, which would need `sys.path` hacks. |
| A `def main(shots: int = 1024, ...)` signature written on **one line** with only `int`/`float`/`str`/`bool` annotations becomes a Run-settings form. The runtime calls it; do not call it yourself. | Expose shots, the schedule depth and a "live vs precomputed" flag as `main()` parameters. This gives judges a no-code knob. |
| `backend` is a **global pre-created from the judge's "Select QPU" choice**. Do not create or hardcode a backend. | Pass `backend` into your modules as a parameter. Locally, inject `AerSimulator()` or `BasicSimulator()` the same way. This is the same dependency-injection pattern as the pluggable RNG. |
| **IonQ backends: one job per run** (simulators and hardware). Local simulators allow unlimited jobs. | Batch every circuit into a single `backend.run([...])`. Get the whole error-vs-queries curve from that one job by computing the MLE on **prefixes of the power schedule** and by binomially/hypergeometrically subsampling counts for smaller shot budgets. |
| IonQ entries on Qollab are **noise-model** simulators: Aria 1/2 (25 qubits, retired hardware models) and Forte 1 / Forte Ent. 1 (29 qubits). Run time grows linearly with shots. The ideal built-in option is `BasicSimulator` (24 qubits). | The "≤24 qubits" budget comes from the built-in simulator. Expect deep Grover circuits to be noise-dominated on IonQ. Report that honestly, and keep IonQ-run schedules shallow (k ≤ 1-2) with modest shots (≤ ~1000). |
| IonQ caps multi-controlled gates at **7 controls** (`TooManyControls`). Gate count is checked **after** IonQ compiles (`TooManyGates`). | `transpile(qc, ionq_backend)` **leaves an 8-control `mcx` intact** (verified), so you must decompose to a basis yourself. An ancilla-free 8-control MCX becomes ~252 CX at depth ~396 (verified). Budget Grover depth accordingly. |
| `BackendSamplerV2` **silently returns all-zero bitstrings on IonQ** (qiskit-ionq returns no per-shot memory). `BackendEstimatorV2` works. | Use `backend.run` + `get_counts`. Do not use Sampler-based qiskit-algorithms estimators on the IonQ path. |
| Debiasing (IonQ error mitigation) is **not available on the cloud simulators**. On QPUs it defaults on at ≥500 shots. | Irrelevant for the simulator. If you ever touch hardware, pass `error_mitigation=ErrorMitigation.NO_DEBIASING` for a clean comparison. |
| Data files load **only when their path appears as a literal string** in Python code. Limits are 2 MB per file, 100 files per project, 200 MB per account. Files written during a run vanish when it ends. | `PRECOMPUTED = "data/sweep_results.json"` as a literal. Keep the JSON small (summary statistics, not raw histories). |
| Network: GET only. `input()` does not work. Figures go to the console via `plt.show()`/`plt.savefig()`. `from js import sendFile` exposes downloads. | No runtime downloads from the core path. Results print to the console; offer JSON and PNG downloads via `sendFile` and `savefig`. |
| Browser needs **WebAssembly JSPI**: recent Chrome, Edge or Opera, or Firefox 153+. Anonymous runs depend on a server flag (`anon_enabled`); "Can't run quantum jobs as an anonymous user at the moment" is a documented failure. | README must tell judges which browser to use. Verify the logged-out run of the published project in Phase 1, not on the last night. |
| Qollab also offers a **JS / Qiskit project type**: HTML/CSS/JS in a sandboxed iframe that can import your Python modules (`await mod.fn.callPromising(backend, ...)`). | That is the natural home for the deferred v2 interactive visualisation. It can reuse the same Python package unchanged. |

## Installation

# Local dev (Python 3.14)

# (or: pip install -e ".[dev]" once pyproject.toml exists)

# requirements.txt  (Qollab-facing; keep it to this)

### Recommended repo layout (fits Qollab's rules and team handoff)

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| MLAE via `backend.run` | `IterativeAmplitudeEstimation` (qiskit-algorithms) | Local-only comparisons with `StatevectorSampler`, e.g. an extra curve "IAE (ideal)" on the plot. It never runs on IonQ via Qollab. |
| MLAE via `backend.run` | Canonical QPE `AmplitudeEstimation` | Only for a tiny (≤6 state qubits) illustrative circuit. It needs m evaluation qubits plus controlled Grover powers. |
| Own numpy MLE | `MaximumLikelihoodAmplitudeEstimation.compute_mle(counts_list, problem)` | Fine if you want library provenance. It accepts plain counts dicts from `backend.run` (verified). It needs qiskit-algorithms enabled on Qollab and `grover_operator=` passed explicitly. |
| Aer for local sweeps | `BasicSimulator` (Qollab built-in) | Final "runs as the judge sees it" checks, and the small live demo inside `main.py`. |
| Aer for local sweeps | `StatevectorSampler` / `Statevector` | Exact amplitudes and the zero-shot-noise test oracle. |
| Python/Qiskit project type | JS/Qiskit project type | v2 interactive front end (deferred). |
| venv + pip | uv | If the team already uses uv. It is faster and has a lockfile, but it is one more install for teammates. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `qiskit.algorithms` (in-core) | Removed from Qiskit core in 1.0. The import fails on Qiskit 2.x. | `qiskit_algorithms` (separate package) for tests; own MLAE for production |
| `qiskit.primitives.Sampler` / `Estimator` (V1) | Removed in Qiskit 2.x. qiskit-algorithms 0.4.0 dropped V1 support. | `StatevectorSampler` (local), `backend.run` (IonQ) |
| `qiskit.circuit.library.GroverOperator` class | Deprecated since Qiskit 2.1, removed in 3.0. It also triggers `MCXGate.get_num_ancilla_qubits` deprecations. | `qiskit.circuit.library.grover_operator(oracle, state_preparation)` function |
| `BackendSamplerV2` on IonQ | Silently returns all-zero bitstrings (documented by Qollab) | `backend.run` + `get_counts` |
| Aer `SamplerV2` / `BackendSamplerV2` with untranspiled Grover circuits | `AerError: unknown instruction: Q` (verified) | Transpile first, or use `backend.run` on transpiled circuits |
| qiskit-algorithms MLAE `transpiler=` argument | Bug in 0.4.0: only `circuits[0]` is transpiled and the estimate fails (verified) | Transpile the circuit list yourself |
| `IterativeAmplitudeEstimation` against an IonQ backend | Adaptive, so it needs multiple jobs; the second job aborts the run on Qollab | MLAE (non-adaptive, one job) |
| qiskit-finance AE wrappers (`EuropeanCallPricing`, `UncertaintyModel`...) | Stale (0.4.1, Feb 2024), finance-specific, and they pull pandas/yfinance into Pyodide | Build `A` and the oracle directly |
| `qiskit-ibm-runtime`, `qiskit-braket-provider` | Wrong vendor; not needed | qiskit-ionq is implicit via the Qollab `backend` |
| Pinning numpy/scipy/matplotlib in Qollab `requirements.txt` | Pyodide ships its own builds, and a pin it cannot satisfy stops the run | Leave them unlisted |
| `src/` layout, notebooks as the deliverable | Qollab runs only a top-level `main.py` and only puts the root on `sys.path` | Flat package plus `main.py` |
| Creating a backend in code (`AerSimulator()`, `IonQProvider().get_backend(...)`) inside `main.py` | Ignores the judge's QPU choice; Aer is not installed by default; no API key on Qollab | Use the injected global `backend` |
| Qubit-sourced random bits as the quantum contribution | Excluded by the hackathon rules | QAE |

## Stack Patterns by Variant

- Use `AerSimulator(method="statevector")` and `transpile(..., optimization_level=1)`.
- Ground truth from `Statevector`, plus the classical exact DP.
- Because Aer is 10-20x faster than BasicSimulator at 16-20 qubits, the full powers-of-two sweep is minutes, not hours.
- Use `backend.run(transpiled_circuits, shots=...)`. Multiple jobs are allowed.
- Keep the live circuit at ≤ ~16-18 qubits and a short schedule. WASM is single-threaded and several times slower than native. Measured natively, BasicSimulator at 20 qubits takes ~3.3 s per 370-gate circuit, and Grover powers multiply that.
- One job only: send all MLAE circuits in one list. Decompose MCX to ≤7 controls (basis-gate transpile). Use shots ≤ ~1000 and k ≤ 1-2.
- Wrap submission in `try/except` (`AttributeError` inside qiskit-ionq means a masked IonQ error).
- Report that noise caps the advantage. That framing helps the "honest baseline" story.
- *Unverified (LOW):* `backend.run(..., noise_model="ideal")` may be accepted, since Qollab passes run kwargs through, and would give an ideal IonQ cloud run. Test this in Phase 1 before relying on it.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| qiskit 2.5.2 | Python 3.10-3.14 | Requires numpy>=2.0,<3 and scipy>=1.14 |
| qiskit-aer 0.17.2 | qiskit 2.5.2, Python 3.14 (cp314 macOS arm64 wheel) | Verified install and run. Its classifiers stop at 3.12, but cp313/cp314 wheels exist. |
| qiskit-algorithms 0.4.0 | qiskit ≥1.0 incl. 2.x; V2 primitives only | Pure Python; runs on 3.14 (verified). Unsupported by IBM. |
| qiskit-ionq 1.1.1 | qiskit ≥2.0, Python ≥3.10 | Pure Python. `backend.run(list)` gives one multi-circuit job. Ideal-sim `max_shots` metadata is 1 (counts derived from probabilities). |
| numpy 2.5.3 (local) vs ~2.4 (Pyodide 314.x) | — | Avoid numpy 2.5-only APIs |
| matplotlib 3.11.2 (local) vs ~3.10 (Pyodide 314.x) | — | Avoid 3.11-only APIs |
| Qollab runtime | qiskit ≥2.5.2,<3; aer 0.17.2; algorithms 0.4.0; ionq ≥1.0.0; Python 3.14 | Exact strings from the Qollab JS bundle and the runtime-environment doc |

## Sources

- PyPI JSON API (queried 2026-10-09): qiskit 2.5.2 (2026-08-13; 2.6.0rc1 2026-10-02), qiskit-algorithms 0.4.0, qiskit-aer 0.17.2, qiskit-ionq 1.1.1 (2026-06-05), qiskit-finance 0.4.1 (2024-02), numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, pytest 9.1.1, ruff 0.17.0. HIGH
- Qollab docs, fetched server-rendered: https://qollab.xyz/learn/docs/runtime-environment , /python-qiskit-projects , /compute-backends , /primitives , /ideal-vs-noise-model-simulators , /transpilation , /how-your-circuit-is-compiled , /error-reference , /error-mitigation , /publish , /upload-your-files . HIGH
- Qollab JS bundle (qollab.xyz/_nuxt/*.js): exact package pins (`qiskit>=2.5.2,<3.0.0`, `qiskit_aer==0.17.2`, `qiskit-algorithms==0.4.0`, `qiskit_ionq>=1.0.0`), project types, 2 MB / 100-file limits, `anon_enabled` flag. HIGH
- Qollab hackathon pages: https://qollab.xyz/programs/hackathon/how-it-works , /terms (eligibility: Qiskit, runs on free simulators including IonQ's, published under MIT, attribution line, 2-3 min public video). HIGH
- qiskit-algorithms 0.4.0 source (GitHub tag 0.4.0: `mlae.py`, `iae.py`, `ae.py`, `estimation_problem.py`) and release notes (V2-only primitives, Qiskit 2.x support). HIGH
- qiskit-ionq 1.1.1 README and installed source (`ionq_backend.py`: multi-circuit run, max_shots). HIGH
- IBM Qiskit API docs: `GroverOperator` deprecated in 2.1, removed in 3.0, use `grover_operator`; `BackendSamplerV2` requires memory support. HIGH
- Local execution (Python 3.14.x venv, exact pins): MLAE/IAE/AE results, Aer SamplerV2 failure, MLAE `transpiler=` bug, `backend.run` + `compute_mle` success, IonQ transpile leaving 8-control MCX, decomposed cost, BasicSimulator vs Aer timings. HIGH
- Pyodide 314.0.7 lock file (numpy 2.4.6, scipy 1.18.0, matplotlib 3.10.8). MEDIUM, since the exact Pyodide build Qollab uses is not published
- IonQ press release on the Qollab partnership (context only). MEDIUM

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
