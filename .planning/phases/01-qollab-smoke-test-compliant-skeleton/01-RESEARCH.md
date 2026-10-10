# Phase 1: Qollab Smoke Test & Compliant Skeleton - Research

**Researched:** 2026-10-10 (hackathon window in progress; deadline Oct 11 2026, 7:00 PM ET)
**Domain:** Qollab browser runtime (Pyodide) + Qiskit/qiskit-ionq backend behaviour, flat Python packaging, static compliance tests, GitHub and Qollab publishing
**Confidence:** HIGH for runtime mechanics (read from Qollab's live worker code and executed against qiskit-ionq source); MEDIUM for anything server-side (Qollab proxy, IonQ) until the smoke test runs

## Summary

Most of what project-level research marked "undocumented" about Qollab can now be read straight from Qollab's own runtime. The Python worker (`/_nuxt/pyworker-C7AWKy02.js`, fetched today) shows exactly what happens when you press Run. It loads **Pyodide v314.0.7** (Python 3.14.2, numpy 2.4.6) and installs packages from Qollab's **private wheel index first**, which today holds only `qiskit 2.5.2` (a wasm build) and `qiskit-ionq 1.0.2`. It then prepends a preamble that defines `backend`: `BasicSimulator()` for the built-in simulator, or `IonQProvider("STUB").get_backend("simulator")` plus `backend.set_options(noise_model="<qpu>")` for an IonQ remote simulator. An AST "Walker" scans `main.py` and every local module it imports, so it can preload external packages and data files named by literal strings. Finally it appends `main(<form values, positional>)` to the source and runs the whole thing as one script. Every design rule below follows from those mechanics.

The `noise_model="ideal"` question is now half-answered. On the client side the answer is yes. In both qiskit-ionq 1.0.2 (what Qollab installs) and 1.1.1, a run kwarg `noise_model="ideal"` overrides the dialog's noise model in the job payload (verified by building the payload locally). There is a catch: qiskit-ionq decides whether to sample counts from `backend.options.noise_model`, not from the kwarg. So the kwarg path returns `counts = round(p*shots)`, which are deterministic and carry **no shot noise**. That is wrong for honest MLAE statistics in Phase 4. `backend.set_options(noise_model="ideal")` gives properly sampled counts. Whether Qollab's proxy or IonQ accepts "ideal" from a hackathon account is server-side and can only be settled by the smoke run. The toy `main.py` below tests both paths, one run each.

Two rules findings change priorities. The hackathon terms say **"Judges run every project on a free local simulator, and results from IonQ's simulators or hardware neither add nor subtract points."** So the built-in-simulator path is the judged path, and the IonQ run must work but carries no score. Anonymous IonQ runs depend on a server flag, which is **on today** (`{"cost":"0","anon_enabled":true}`) but can change. The built-in simulator runs entirely in the browser and is not gated by that flag.

**Primary recommendation:** Build the skeleton in three plans. (1) An autonomous wave creates the flat `neutron_qae/` package, the smoke-test `main.py`, a stdlib-only compliance test suite, the LICENSE, a README with attribution and disclosure, `.gitignore` and `.gitattributes`; `pytest` must be green. (2) A human-action wave covers GitHub: `brew install gh`, `gh auth login`, `gh repo create --public --source=. --push`, and the collaborator invites. (3) A human-action wave covers Qollab: upload a `git archive` zip, run the smoke test on the built-in simulator and IonQ Forte 1 (`ideal_mode` = none / kwarg / set_options), publish as public default, repeat both runs in an incognito window, and paste the `QOLLAB_RUNTIME_REPORT=` lines into `docs/QOLLAB-RUNTIME.md`. Every code block in this document was run in a scratch prototype (23 tests passing).

<user_constraints>
## User Constraints

No CONTEXT.md exists for this phase (it was not run through `/gsd-discuss-phase`). Per the orchestrator, the user's decisions are the ROADMAP Phase 1 section and the PROJECT.md constraints and Key Decisions, quoted verbatim below.

### Locked Decisions
From PROJECT.md `## Constraints` (verbatim):
- **Tech stack**: Python for the classical engine, Qiskit for the quantum circuits — hackathon rules require Qiskit; classical baseline in plain Python/numpy
- **Hardware**: ≤ 24 qubits — IonQ simulator limit available through Qollab
- **Timeline**: Submission by Oct 11 2026, 7:00 PM ET — hard hackathon deadline; partial submissions still eligible
- **License**: MIT, with attribution line and disclosure of all external libraries and AI tools used
- **Platform**: Must run without error on the Qollab-provided IonQ simulator, from a logged-out browser
- **Scaling honesty**: The speedup argument is sampling complexity (1/N vs 1/sqrt(N)), never "neutrons are quantum so qubits model them better"

From PROJECT.md `## Key Decisions` (verbatim, Phase-1-relevant rows):
- "Phase 1 = Qollab smoke test + compliance | Platform behaviour is undocumented and can zero the submission; compliance items keep a partial submission eligible"
- "Classical engine takes its random source as a parameter | Keeps the engine identical across experiments; also lets a future RNG section reuse it" (same dependency-injection pattern as the injected `backend`)
- "Interactive front end deferred to v2 | Core comparison must work first; teammates build the UI after handoff"

From STATE.md decisions (verbatim):
- "[Roadmap]: Library/AI disclosure (DOCS-06) moved into Phase 1 with the other compliance items so a partial submission stays eligible."

From ROADMAP Phase 1 Success Criteria (verbatim):
1. In a logged-out (incognito) browser, the published Qollab project runs the toy `main.py` start-to-finish without error on Qollab's built-in simulator and on an IonQ simulator backend.
2. The smoke-test run reports the Python, numpy and qiskit versions of Qollab's runtime and whether `noise_model="ideal"` is accepted, and those findings are recorded in the repo for later phases.
3. A teammate added as a GitHub collaborator can clone the repo, install `requirements.txt` (pinning `qiskit==2.5.2`), import the flat package sitting next to `main.py`, and run `pytest` green; no file names with spaces remain.
4. The repo carries an MIT LICENSE, the README line "This effort is supported by Qollab & IonQ.", and a disclosure of every external library and AI tool used, with licenses and confirmation the team may use them.
5. An automated test fails if anything reachable from `main.py` imports qiskit-aer or qiskit-algorithms, if any committed data file exceeds 2 MB, or if code constructs a backend instead of receiving it as a parameter.

### Claude's Discretion
Not formally recorded. The following are open, and this research recommends an answer for each:
- Package name: recommend `neutron_qae`, as in STACK.md and `.claude/CLAUDE.md`. ARCHITECTURE.md's `src/qtransport/` is superseded because a `src/` layout breaks Qollab imports.
- GitHub repo name and visibility: recommend public; the name is the user's choice (e.g. `sparc-first-wall-qae`).
- Toy circuit design, records file name, and test layout (all prescribed below).

### Deferred Ideas (OUT OF SCOPE)
From PROJECT.md / REQUIREMENTS.md: the interactive HTML/JS front end (UI-01, v2), real IonQ hardware runs, and every physics/quantum feature (Phases 2-6). Phase 1 must not build physics, kernels or QAE.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (verbatim, `.planning/REQUIREMENTS.md`) | Research Support |
|----|-------------|------------------|
| PLAT-01 | "Repo has a flat package at root next to `main.py`, `requirements.txt` pinning `qiskit==2.5.2`, `pyproject.toml`, `tests/`, `scripts/`; placeholder files with spaces in names are removed or renamed" [VERIFIED: .planning/REQUIREMENTS.md:12] | Flat layout + `[tool.setuptools] packages=["neutron_qae"]` (auto-discovery fails, verified); `pythonpath=[".","tests"]`; placeholders are untracked 0-byte files, so delete them; a test rejects tracked names containing spaces |
| PLAT-02 | "A toy `main.py` runs on Qollab's built-in simulator and on an IonQ simulator backend, is published, and runs start-to-finish from a logged-out browser (smoke test records Python/numpy/qiskit versions and whether `noise_model=\"ideal\"` is accepted)" [VERIFIED: .planning/REQUIREMENTS.md:13] | Qollab worker mechanics (Runtime Facts); toy `main.py`/`smoke.py` that emits one `QOLLAB_RUNTIME_REPORT=` JSON line; `ideal_mode` form parameter; publish + incognito runbook; `docs/QOLLAB-RUNTIME.md` template |
| PLAT-03 | "Repository is on GitHub with teammates as collaborators, MIT LICENSE, and the attribution line \"This effort is supported by Qollab & IonQ.\" in README" [VERIFIED: .planning/REQUIREMENTS.md:14] | `gh` absent but installable via Homebrew; `gh repo create --public --source=. --remote=origin --push`; `PUT /repos/{owner}/{repo}/collaborators/{username}` creates invitations that must be accepted; MIT text; README test |
| PLAT-04 | "Nothing reachable from `main.py` imports qiskit-aer or qiskit-algorithms; data files are ≤ 2 MB and loaded by literal path; `backend` is injected, never created in code" [VERIFIED: .planning/REQUIREMENTS.md:15] | `tests/compliance_checks.py` mirrors Qollab's own Walker; 2 MB check over `git ls-files`; data-literal check; backend construction/assignment/global-read checks; each has a negative test |
| DOCS-06 | "Disclosure of all external libraries and AI tools used, with licenses, and confirmation the team may use them" [VERIFIED: .planning/REQUIREMENTS.md:59] | License metadata pulled from installed packages and PyPI; GSD license from npm; Anthropic Consumer Terms on output ownership; disclosure table template |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Directives extracted from `.claude/CLAUDE.md` (which embeds PROJECT.md and STACK.md):
- Python 3.14 locally; Qollab runtime is Python 3.14 on Pyodide.
- **Pin `qiskit==2.5.2` in both `requirements.txt` and `pyproject.toml`.**
- **Do not pin numpy (or scipy/matplotlib) in the Qollab `requirements.txt`**; Pyodide ships its own builds. Write against the numpy 2.0 API.
- `requirements.txt` must contain no pip options (`-r`, `-e`, `--index-url`), environment markers or URL requirements.
- **Flat layout** with the package folder at the repo root, **not** `src/`.
- **`qiskit_aer`, `qiskit_algorithms` and `qiskit_ionq` imports live only in `scripts/` and `tests/`.**
- **Never create or hardcode a backend** in code `main.py` reaches; pass `backend` into modules as a parameter.
- One job per run on IonQ backends: batch every circuit into one `backend.run([...])`.
- Data files load only when their path appears as a literal string; ≤ 2 MB per file, ≤ 100 files per project.
- No `BackendSamplerV2` on IonQ (all-zero bitstrings); use `backend.run` + `get_counts`.
- Use `grover_operator()`, never the `GroverOperator` class; no `qiskit.algorithms`, no V1 primitives (relevant later; the compliance grep can include these).
- README must tell judges which browser to use (WebAssembly JSPI).
- GSD workflow enforcement: file changes go through GSD commands (`/gsd-execute-phase` for this work).
- Tools: pytest (`-m "not slow"` markers), ruff; JupyterLab local only.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Running `main.py` (Python execution) | Browser / Client (Pyodide web worker, single thread) | — | Qollab: "no code runs on a server except the quantum job itself" [CITED: qollab.xyz/learn/docs/runtime-environment] |
| Backend selection and construction | Qollab runtime preamble (client) | — | The worker prepends `backend = BasicSimulator()` or the IonQ provider lines; user code only receives it [VERIFIED: Qollab pyworker bundle] |
| Built-in simulation (the judged path) | Browser (BasicSimulator in WASM) | — | Local, free, never queues, not gated by the anon flag |
| IonQ remote simulation | API / Backend (Qollab proxy → IonQ cloud) | Browser (qiskit-ionq client builds payload and counts) | Job POSTs are rewritten to Qollab's proxy; one job per run is enforced client-side in the fetch rewriter [VERIFIED: pyworker bundle] |
| Package installation | Browser (micropip: Qollab `/py` index, then PyPI) | CDN (Pyodide 314.0.7 on jsDelivr) | `set_index_urls([/py, "PYPI"])` [VERIFIED: pyworker bundle] |
| Project file loading (modules, data) | Browser (AST Walker + lazy meta-path finder) | Qollab API (file fetch) | Only reachable modules and literal-path data files are fetched [VERIFIED: pyworker bundle] |
| Compliance gates | Local dev / CI (pytest, stdlib `ast`) | — | Static checks on the repo; never shipped to Qollab |
| Source of truth for teammates | GitHub (public repo) | — | Qollab has no Git import; the GitHub repo is linked from the project card [CITED: qollab.xyz/learn/docs/write-your-project-page] |
| Runtime findings record | Repo docs (`docs/QOLLAB-RUNTIME.md`) | — | Read by Phases 4-6 |

## Qollab Runtime Facts (read from Qollab's live code, 2026-10-10)

The decisive facts, with provenance. "Worker" means `https://qollab.xyz/_nuxt/pyworker-C7AWKy02.js`. The hashed file name will change on redeploy.

| # | Fact | Evidence | Consequence |
|---|------|----------|-------------|
| R1 | Runtime is **Pyodide v314.0.7**, whose lock reports `"python": "3.14.2"`, numpy `2.4.6`, scipy `1.18.0`, matplotlib `3.10.8`, micropip `0.11.1` | Worker first line: `import{loadPyodide as e}from"https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs"`; `pyodide-lock.json` info `{'abi_version': '2026_0', 'arch': 'wasm32', 'platform': 'emscripten_5_0_3', 'python': '3.14.2'}` [VERIFIED: worker + jsDelivr lockfile] | Write against numpy 2.4 and matplotlib 3.10 APIs (local has numpy 2.5.3, matplotlib 3.11.2). The smoke test confirms actual loaded versions |
| R2 | Qollab's private index `https://qollab.xyz/py/index.json` lists `qiskit 2.5.2` (`qiskit-2.5.2-cp310-abi3-pyemscripten_2026_0_wasm32.whl`), `qiskit-aer 0.17.2`, **`qiskit-ionq 1.0.2`**, `pqca`, `qave`, `pyscf`, `docplex`, `fastdtw`, `pylatexenc`, `pybase64` | Fetched JSON [VERIFIED: qollab.xyz/py/index.json?v=27] | `qiskit==2.5.2` is the **only** installable qiskit (PyPI has no wasm wheel), so the pin matches. **Pitfall:** if Qollab swaps the index to 2.6.x mid-event, `qiskit==2.5.2` would stop installing. Re-run the smoke test before the final publish (Phase 6) |
| R3 | micropip tries index URLs in order and stops at the first match; the worker calls `E.set_index_urls([new URL('/py',self.location).toString(),'PYPI'])` | Worker [VERIFIED]; micropip docs: "If a list of URLs is provided, micropip will try each URL in order until it finds a package." [CITED: micropip.pyodide.org/en/stable/project/api.html] | `qiskit_ionq>=1.0.0` resolves to **1.0.2** on Qollab (local dev has 1.1.1). The smoke test prints it |
| R4 | Provider packages install **only when that provider is selected**: `r={ionq:[n.qiskitIonq],ibm:[n.qiskitAer,n.qiskitIbmRuntime],aws:[n.qiskitBraketProvider]}` with `qiskitIonq:'qiskit_ionq>=1.0.0'` | Worker [VERIFIED] | On the built-in simulator `import qiskit_ionq` fails. Picking an IBM noise model silently makes `qiskit_aer` importable, which can hide a forbidden import during manual testing. Detect IonQ by `type(backend).__module__.startswith("qiskit_ionq")`, never by importing it |
| R5 | Backend preamble: built-in → `from qiskit.providers.basic_provider import BasicSimulator` … `backend = BasicSimulator()`; IonQ remote sim → `from qiskit_ionq import IonQProvider\nprovider = IonQProvider("STUB")` then `backend = provider.get_backend("simulator")\nbackend.set_options(noise_model="${t}")` then `del provider` | Worker function `je` [VERIFIED] | `backend` is a module global of `main.py`. On IonQ it is an `IonQSimulatorBackend` named `ionq_simulator` whose `options.noise_model` is the QPU model (e.g. `forte-1`). The API key is the platform's (`"STUB"` is rewritten by the proxy), so no secret ever belongs in our code |
| R6 | Preamble also sets `os.environ['QISKIT_PARALLEL'] = 'FALSE'` and `os.environ['RAYON_NUM_THREADS'] = '1'`, replaces `concurrent.futures.ThreadPoolExecutor` with a main-thread executor, and filters one DeprecationWarning | Worker [VERIFIED] | Single-threaded; transpile/simulate is serial. Locally Qiskit may parallelize, so local timings understate Pyodide cost |
| R7 | **`main()` call injection:** `function Ne(e,t){if(t==null)return{code:e,…};… e+='\nmain('+t.map(…string→JSON.stringify, boolean→True/False, else raw…).join(',')+')'` | Worker [VERIFIED] | Form values are passed **positionally** in parameter order. A float default `1.0` reaches Python as `1` (an int) because it goes through a JS number, so always coerce with `float()`/`int()` inside `main`. Never call `main()` yourself or add an `if __name__ == "__main__":` block: the whole file runs as `__main__`, so main would run twice |
| R8 | **Form parser:** regex `/^def\s+main\s*\(.*$/m` (first match only); each parameter must have a `TypeDef` whose name is one of `str,int,float,bool`; defaults are parsed only if they are a `Number`, `Boolean` or `String` literal | UI bundle `BWPMdZ7B.js` function `Cc` [VERIFIED] | Signature on one line at column 0; no `-1` defaults (a unary expression is not a Number literal, so the default is dropped); give every parameter a default; never put a line starting `def main(` above the real one (docstring examples included) |
| R9 | **Project-file Walker** (Python, embedded in worker): `ast.walk` over `main.py` and every local module it imports (absolute and relative); every string `Constant` that names an existing non-`.py` file under the root is loaded as data; every non-local top-level import name is collected as an "external" and passed to `loadPackagesFromImports`; a `LazyFinder` on `sys.meta_path` fetches local modules imported dynamically | Worker `var Pe` source [VERIFIED] | Imports of scipy/matplotlib in sub-modules **do** get loaded. Data paths must be literal strings anywhere in reachable code. Function-body and `try/except` imports are scanned too, so the compliance test must scan every node |
| R10 | IonQ **one job per run** is enforced in the fetch rewriter: `if(t.isPosted())throw Error('The code has already filed one circuit execution job; only one job is allowed per code run')` | Worker [VERIFIED] | Smoke test sends exactly one job on IonQ (two circuits in one list); the perf probe is skipped on IonQ |
| R11 | Proxy response handling: a 400 containing `request body too large` is rewritten to "Circuit size is too large, please try running a smaller circuit (less gates)"; **403 → `onJobFailedAccessDenied`**, which the UI shows as "Can't run quantum jobs as an anonymous user at the moment - please sign in to continue" | Worker + UI bundle [VERIFIED] | There is a request-size cap on IonQ jobs (relevant to Phase 4 Grover depth). Anonymous denial applies to **IonQ jobs only**; the built-in simulator never calls the server |
| R12 | Anonymous IonQ runs flag: `GET https://api.qollab.xyz/api/ionq/backends/simulator/cost` → `{"cost":"0","anon_enabled":true}` | curl, 2026-10-10 [VERIFIED: live endpoint] | Logged-out IonQ runs are allowed **right now**. It is a server flag, so re-check before the final publish (one curl) |
| R13 | Qollab's IonQ remote-sim entries are all noise models: Aria 1/2 (25 qubits), Forte 1 / Forte Enterprise 1 (29). Built-in = BasicSimulator, ideal, 24 qubits | [CITED: qollab.xyz/learn/docs/compute-backends, /ideal-vs-noise-model-simulators] | Use **IonQ Forte 1** (remote simulator) for the smoke test |
| R14 | Upload: files, folder or archive (`.zip`, `.tar`, `.tar.gz`, …); "A single wrapping folder is removed"; `.git`, `__MACOSX`, `.DS_Store`, `Thumbs.db`, `._*` are skipped; a top-level `README.md` "becomes the project's write-up… up to 65,000 characters" and is not stored as a file; when adding to an existing project "README.md is skipped here" | [CITED: qollab.xyz/learn/docs/upload-your-files] | There is **no GitHub import**, so upload a `git archive` zip. README goes to the write-up only when creating a project |
| R15 | Limits: "A project holds up to 100 files of up to 2 MB each, and all your projects together can use 200 MB." "A run has no time limit." | [CITED: qollab.xyz/learn/docs/runtime-environment] | Keep tests/scripts/.planning out of the upload (export-ignore); a test enforces ≤ 100 shipped files |
| R16 | Publishing: draft private; Publish → version name, notes, Visibility "public and the new default version"; "You can publish up to 10 versions an hour"; public URL `qollab.xyz/u/<your-username>/<project>` | [CITED: qollab.xyz/learn/docs/publish, /project-anatomy] | Logged-out testing requires a **public default** version. Publishing copies the draft, so re-publish after every change |
| R17 | Browser: "needs a browser that supports WebAssembly JSPI, such as a recent Chrome, Edge or Opera, or Firefox 153 or later" | [CITED: qollab.xyz/learn/docs/runtime-environment] | Chrome 155.0.8059.39 is installed on this Mac. Put the browser note in the README |
| R18 | Stdout is wired with `setStdout({batched: …})` | Worker [VERIFIED] | Batched mode emits on newline. End every progress message with a newline; `flush=True` is harmless |
| R19 | Hackathon terms: "Judges run every project on a free local simulator, and results from IonQ's simulators or hardware neither add nor subtract points." Attribution: "This effort is supported by Qollab & IonQ". Undisclosed "open-source library as a starting point" or "Copying code… without disclosure and attribution" leads to disqualification. Demo video 2-3 min at a public link | [CITED: qollab.xyz/programs/hackathon/terms] | Built-in path = judged path. Disclosure is a disqualification-avoidance item, not polish |

### `noise_model="ideal"`: what is settled and what is not

| Path | Client-side behaviour (qiskit-ionq 1.0.2 and 1.1.1, verified locally) | Server-side | Counts quality |
|------|------------------------------------------------------------|-------------|----------------|
| `ideal_mode="none"` | payload `noise = {'model': 'forte-1', 'seed': None}` | Normal path | Noisy, `round(p*shots)` of a noisy histogram |
| `ideal_mode="kwarg"`: `backend.run(circs, shots=N, noise_model="ideal")` | payload `noise = {'model': 'ideal', 'seed': None}`; `is_ideal_sim` stays **False** (it reads `backend.options.noise_model`) | **Unknown**: the Qollab proxy or IonQ may reject or override it | If accepted: `_build_counts(..., use_sampler=False)` gives `{'00': 50, '11': 50}`, i.e. **exact `round(p*shots)` with no shot noise** |
| `ideal_mode="set_options"`: `backend.set_options(noise_model="ideal")` then `run` | payload `{'model': 'ideal'}`; `is_ideal_sim` **True** | **Unknown** (same) | If accepted: client-side sampling with `np.random.RandomState`, e.g. `{'00': 51, '11': 49}`, which is correct shot statistics |
| BasicSimulator (built-in) | `run(..., noise_model="ideal")` → only `UserWarning: Option noise_model is not used by this backend`; `set_options(noise_model=...)` **raises** `AttributeError: Options field noise_model is not valid for this backend` | n/a | Ideal sampled |

[VERIFIED: local execution of `qiskit_ionq.helpers.qiskit_to_ionq` and `qiskit_ionq.ionq_job._build_counts` on 1.0.2 and 1.1.1, using Qollab's exact preamble `IonQProvider("STUB").get_backend("simulator").set_options(noise_model="forte-1")`; no network]

**Planner implication for Phase 4:** if the smoke test shows "set_options" accepted, Phase 4 can obtain an ideal IonQ cloud run with real shot statistics. If only "kwarg" is accepted, the counts carry no shot noise and must be labelled as such. If neither is accepted, the IonQ run proves execution only, which the roadmap already assumes.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qiskit | **2.5.2** (exact pin) | Circuits, `transpile`, `BasicSimulator` (local tests) | The only qiskit build Qollab can install (R2). PyPI latest is also 2.5.2, with 2.6.0rc1 pre-release [VERIFIED: PyPI JSON 2026-10-10] |
| Python | 3.14 (local 3.14.8; Qollab 3.14.2) | Language | Matches Pyodide 314.0.7 [VERIFIED] |
| numpy | unpinned (local 2.5.3, Qollab 2.4.6) | Pulled in by qiskit | Do not pin (CLAUDE.md) |
| setuptools | ≥ 77 (build backend only) | `pip install -e .` | Supports PEP 639 `license = "MIT"` + `license-files` [ASSUMED: version floor; the local editable install succeeded] |

### Supporting (local dev / tests only, never reachable from `main.py`)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Test runner | Always. The Phase 1 suite needs only `qiskit` + `pytest` |
| ruff | **0.16.10** (not 0.17.0, released 2026-10-09T19:46, less than one day old) | Lint/format | Optional in Phase 1. Pin the prior release so the "too-new" legitimacy flag does not apply |
| qiskit-ionq | 1.1.1 local (Qollab: 1.0.2) | Only to reproduce payload behaviour locally | Not needed by Phase 1 tests; do not add to `requirements.txt` |
| qiskit-aer / qiskit-algorithms | 0.17.2 / 0.4.0 | Later phases | Put them in the `[dev]` extra now so `pip install -e ".[dev]"` is the single teammate command |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `git archive` zip upload | Dragging the repo folder | Folder upload drags `.planning/`, `tests/` and `__pycache__` past the 100-file cap and into public view. Use the archive |
| `gh` CLI | GitHub web UI | Web UI works if `gh` install or auth fails. Fallback steps are below |
| Static `ast` import walk | `modulefinder` | `modulefinder` executes no code but cannot see `importlib.import_module("x")` string calls, and resolves against the local environment, where `qiskit_aer` *is* installed. A custom walk that mirrors Qollab's own Walker is exact |

**Installation:**
```bash
# Teammate (minimum for Phase 1 tests)
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest
# Full dev (later phases)
pip install -e ".[dev]"
```

**Version verification** (2026-10-10): qiskit 2.5.2 (2026-08-13), pytest 9.1.1 (2026-06-19), ruff 0.16.10 (2026-10-01) / 0.17.0 (2026-10-09), matplotlib 3.11.2 (2026-09-11) [VERIFIED: PyPI JSON API].

## Package Legitimacy Audit

Seam run: `gsd_run query package-legitimacy check --ecosystem pypi qiskit qiskit-ionq qiskit-aer qiskit-algorithms numpy matplotlib pytest ruff`.

| Package | Registry | Latest published | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| qiskit | PyPI | 2026-08-13 | unknown to seam | ibm.com/quantum/qiskit | SUS (`unknown-downloads`) | Approved with note: also served by Qollab's own index (R2) and named in Qollab docs |
| qiskit-ionq | PyPI | 2026-06-05 | unknown | github.com/qiskit-community/qiskit-ionq | SUS (`unknown-downloads`) | Approved with note: Qollab installs it itself (R4); never in our requirements |
| qiskit-aer | PyPI | 2025-09-17 | unknown | github.com/Qiskit/qiskit-aer | SUS (`unknown-downloads`) | Dev extra only; named in Qollab bundle |
| qiskit-algorithms | PyPI | 2025-08-29 | unknown | github.com/qiskit-community/qiskit-algorithms | SUS (`unknown-downloads`) | Dev extra only; named in Qollab docs Libraries table |
| numpy | PyPI | 2026-09-06 | unknown | (none in metadata) | SUS (`unknown-downloads`, `no-repository`) | Transitive via qiskit; not listed by us |
| matplotlib | PyPI | 2026-09-11 | unknown | matplotlib.org | SUS (`too-new`, `unknown-downloads`) | Not installed in Phase 1 |
| pytest | PyPI | 2026-06-19 | unknown | github.com/pytest-dev/pytest | SUS (`unknown-downloads`) | Approved with note |
| ruff | PyPI | 2026-10-09 | unknown | docs.astral.sh/ruff | SUS (`too-new`, `unknown-downloads`) | **Pin 0.16.10**; optional |

No `postinstall` scripts (all `postinstall: None`). Every SUS verdict comes from the seam not seeing PyPI download counts (`unknown-downloads`). It is not a name-confusion signal: all names match the official docs (Qollab runtime-environment Libraries table, Qiskit docs). Earlier project research had already installed every one in a venv.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** all eight above, for `unknown-downloads`. The planner should add **one** `checkpoint:human-verify` before the first `pip install` of the dev environment, covering this list. The Qollab-facing `requirements.txt` contains only `qiskit==2.5.2`.

## Architecture Patterns

### System Architecture Diagram

```
                       ┌─────────────────────── GitHub (public repo, source of truth) ─────────────────────┐
 local dev ──git push──►  main.py  requirements.txt  neutron_qae/  data/  LICENSE  README.md               │
   │                   │  tests/ scripts/ docs/ pyproject.toml .planning/   (export-ignore: not shipped)    │
   │ pytest            └──────────────────────────────┬───────────────────────────────────────────────────────┘
   │ (compliance +                                    │ git archive --format=zip HEAD  (≤100 files, README→write-up)
   │  smoke w/ injected                               ▼
   │  BasicSimulator)            Qollab project (draft) ──Publish: public + default──► qollab.xyz/u/<user>/<project>
   │                                                                                         │ judge / incognito
   ▼                                                                                         ▼  presses Run
 scripts/run_local.py                                   Select QPU dialog ──► Run settings form (from def main(...))
 (injects backend,                                                │                         │ positional values
  mirrors Qollab)                                                 ▼                         ▼
                              ┌──────── Pyodide web worker (browser, single thread) ───────────────────────┐
                              │ micropip: Qollab /py index → PyPI   (qiskit 2.5.2 wasm; +qiskit_ionq 1.0.2   │
                              │                                      only if IonQ chosen)                    │
                              │ Walker: ast-scan main.py + local imports → fetch modules + literal data files│
                              │ preamble: backend = BasicSimulator()  |  IonQProvider("STUB")…set_options(…)  │
                              │ exec: preamble + main.py + "main(<form values>)"                              │
                              │        main() → neutron_qae.smoke.run_toy(backend, …)                         │
                              └───────────────┬──────────────────────────────────────┬──────────────────────┘
                                 built-in:    │ in-browser BasicSimulator             │ IonQ: ONE fetch POST /jobs
                                              ▼                                       ▼ (rewritten to Qollab proxy;
                                        counts → console                    403 = anonymous denied; 2nd POST = error)
                                        "QOLLAB_RUNTIME_REPORT={json}"               ▼
                                              │                              IonQ cloud noise-model simulator
                                              ▼                                       │ probabilities
                         Hippolyte copies the JSON line ──► docs/QOLLAB-RUNTIME.md ◄──┘ (qiskit-ionq builds counts)
                                                             (read by Phases 4-6)
```

### Recommended Project Structure (end of Phase 1)
```
main.py                     # Qollab entry. Defines main(...) only; uses injected global `backend`
requirements.txt            # exactly: qiskit==2.5.2  (+ comments)
pyproject.toml              # local build + pytest config (export-ignored)
LICENSE                     # MIT
README.md                   # attribution line, how to run, browser note, disclosure (becomes Qollab write-up)
.gitignore                  # __pycache__/, *.egg-info/, .venv/, ... (load-bearing for the upload)
.gitattributes              # export-ignore for everything Qollab must not receive
neutron_qae/
  __init__.py
  smoke.py                  # Phase 1 toy: runtime_report, backend_report, run_toy, perf_probe (backend is a parameter)
data/
  smoke_probe.json          # tiny file proving literal-path data loading works on Qollab
scripts/
  run_local.py              # ONLY place a backend is constructed (allow-listed)
tests/
  compliance_checks.py      # stdlib helpers (imported via pytest pythonpath)
  test_compliance.py        # PLAT-01/04 gates + negative tests
  test_smoke.py             # main.main() end-to-end with injected BasicSimulator
  test_docs.py              # LICENSE/README attribution/disclosure present
docs/
  QOLLAB-RUNTIME.md         # recorded smoke-test findings (static facts + empirical runs)
```
Later phases add modules under `neutron_qae/` (physics, kernels, circuits, mlae, …) and `scripts/precompute_*.py`; the compliance tests already cover them.

### Pattern 1: Injected backend (dependency injection of the QPU)
**What:** `main.py` reads the global `backend` and passes it into package functions. Package functions take `backend` as a parameter and never read a global or construct one.
**When:** always; enforced by `backend_constructions`, `backend_assigned_in_main` and `package_uses_global_backend`.
**Local:** `scripts/run_local.py` sets `main.backend = BasicSimulator()` (or `AerSimulator()`) and calls `main.main(...)`, which mirrors R5 and R7. Tests use `monkeypatch.setattr(entry, "backend", BasicSimulator(), raising=False)`.

### Pattern 2: One self-describing report line
**What:** every Qollab run prints one machine-readable line `QOLLAB_RUNTIME_REPORT={...json...}`, followed by `SMOKE TEST PASSED|FAILED`. On Qollab it also calls `js.sendFile` to offer `qollab_runtime_report.json` as a download.
**Why:** the console has a copy button (R14 docs). One line per run is easy to paste into `docs/QOLLAB-RUNTIME.md`, so nothing is retyped by hand.

### Pattern 3: IonQ-safe single job
**What:** build all circuits first, `transpile(list, backend, optimization_level=1)` once, then make **one** `backend.run(list, shots=…)` call and read `get_counts(i)`. Wrap the submit in `try/except Exception` and record `AttributeError` (masked IonQ errors, per Qollab error reference).
**Why:** R10 enforces one job per run. The smoke test already uses a two-circuit list, which proves the multi-circuit single job that Phase 4's MLAE depends on.

### Pattern 4: Ship only what Qollab needs (`.gitattributes` export-ignore + `git archive`)
`git archive` honours directory `export-ignore` entries. Verified: `tests/`, `docs/`, `.planning/`, `scripts/`, `pyproject.toml` were all omitted. Note that `git check-attr` reports `unspecified` for files *inside* an ignored directory, which is why the test parses `.gitattributes` itself. The archive also includes **any tracked junk** (`__pycache__/`, `*.egg-info/` appeared in a prototype archive before `.gitignore` existed), so `.gitignore` must land in the first commit.

### Anti-Patterns to Avoid
- **`if __name__ == "__main__": main()` in `main.py`:** runs `main()` twice on Qollab (R7).
- **Multi-line or `Optional[int]` main signature, or negative defaults:** the form disappears silently and `main()` is not called (R8; the docs say "Nothing warns you").
- **`import qiskit_ionq` anywhere reachable:** fails on the built-in simulator (R4). Use the module-name check.
- **`backend.set_options(...)` without an IonQ check:** raises on BasicSimulator.
- **Building data paths with f-strings/`os.path.join`:** the file is never loaded (R9).
- **`src/` layout:** Qollab only puts the root on `sys.path`.
- **Uploading the repo folder:** blows the 100-file cap and publishes `.planning/` on Qollab.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Repo creation, push, invites | Manual curl to the GitHub API with a PAT | `gh repo create … --source=. --remote=origin --push`; `gh api -X PUT repos/{owner}/{repo}/collaborators/{user}` | gh handles auth, the credential helper and pagination |
| Upload bundle | A Python zip script with hand-maintained include lists | `git archive --format=zip -o <path> HEAD` + `.gitattributes export-ignore` | Exactly the committed tree, deterministic, and matches what GitHub's "Download ZIP" serves [ASSUMED for GitHub ZIP] |
| Reachability analysis | Regex grep for `import qiskit_aer` | `ast` walk that mirrors Qollab's Walker (code below) | Regex misses `from x import y`, relative imports and function-body imports, and false-positives on comments |
| License text | Typing MIT from memory | Canonical text below (choosealicense.com) | Exact wording matters |
| Version reporting | Parsing `pip list` | `module.__version__`, falling back to `importlib.metadata.version` | Works in Pyodide; micropip installs dist-info [ASSUMED for Pyodide dist-info] |

**Key insight:** Qollab's own Walker is short and readable. Matching it exactly (`ast.walk` over every node, local-vs-external by whether `<root>/<top>.py` or `<root>/<top>/` exists) makes the PLAT-04 test say precisely what Qollab will do.

## Common Pitfalls

### Pitfall 1: main() never runs, or runs twice
**What goes wrong:** the console shows only top-level output, or everything prints twice.
**Why:** signature broken (multi-line, unannotated, `Optional`, negative default) → no form → no call; or a `__name__` guard / explicit `main()` call plus Qollab's appended call.
**How to avoid:** `test_main_signature_is_qollab_form_compatible`; keep `main.py` side-effect-free at module level.
**Warning signs:** no "Run settings" form in the Select QPU dialog.

### Pitfall 2: Float parameters arrive as ints
**What goes wrong:** `threshold: float = 1.0` arrives as `1`; integer arithmetic surprises follow.
**Why:** the values travel as JS numbers (R7).
**How to avoid:** `x = float(x)` / `int(x)` at the top of `main`.

### Pitfall 3: An IBM noise-model run hides a forbidden import
**What goes wrong:** `import qiskit_aer` "works" in a manual Qollab test because an IBM backend was picked, which installs Aer (R4). It then fails for a judge on the built-in simulator.
**How to avoid:** the static test; test only on the built-in simulator and IonQ Forte 1.

### Pitfall 4: kwarg-ideal counts look perfect because they are not sampled
**What goes wrong:** `noise_model="ideal"` as a run kwarg returns `round(p*shots)`. MLAE then shows zero variance and an impossible scaling plot.
**How to avoid:** prefer `set_options` (R-table above). The smoke test reports `noise_verdict` = `"ideal, exact round(p*shots) (no shot noise)"` versus `"ideal, sampled"` versus `"noisy"`.

### Pitfall 5: Qollab index drift
**What goes wrong:** the Qollab `/py` index replaces qiskit 2.5.2 and the `==2.5.2` line can no longer install ("Could not install every package listed in requirements.txt").
**How to avoid:** re-run the published smoke test before the final publish. If it fails, change the pin to the version in `https://qollab.xyz/py/index.json`.

### Pitfall 6: Anonymous IonQ denial at judging time
**What goes wrong:** "Can't run quantum jobs as an anonymous user at the moment".
**How to avoid:** it is server-controlled (R12) and does not affect the built-in simulator (the judged path, R19). Keep the built-in path complete on its own; the README explains that IonQ runs may need sign-in.

### Pitfall 7: Junk in the upload, or more than 100 files
**How to avoid:** `.gitignore` in the first commit, `.gitattributes` export-ignore, and `test_qollab_upload_stays_under_100_files_and_ships_entry_point`.

### Pitfall 8: README edits do not reach Qollab
**What goes wrong:** on re-upload into an existing project, "README.md is skipped" (R14).
**How to avoid:** paste README into the Project Card write-up manually on each publish, or create a fresh project from the archive for v0. Record this in the runbook.

### Pitfall 9: `gh` missing / no SSH keys / no git identity
**Found:** `gh` not installed (Homebrew available, formula gh 2.102.0); `~/.ssh` absent; no `~/.gitconfig`. Existing commits are authored `Hippolyte Delloye <hippolytedelloye@Hippolytes-MacBook-Pro.local>` (hostname email).
**How to avoid:** `brew install gh && gh auth login` (HTTPS + browser device flow, which also sets up the git credential helper via `gh auth setup-git`), and set a repo-local `user.email` (GitHub noreply address recommended) before new commits. Leave old commits as they are; rewriting history is not worth the risk.

### Pitfall 10: Timing numbers that do not mean what they say
**What goes wrong:** qiskit is imported by Qollab's preamble **before** `main.py` runs (R5), so import cost cannot be measured from user code. It shows up as the "Compiling / initializing runtime…" phase.
**How to avoid:** report `wall_clock_s` of `main()` plus `perf_probe` timings. Note manual stopwatch time-to-first-output in `docs/QOLLAB-RUNTIME.md`. Native baseline (BasicSimulator, depth-20 ry+cx ladder, 1000 shots, this Mac): 12 qubits 0.021 s, 16 qubits 0.338 s, 20 qubits 6.486 s [VERIFIED: local run]. Pyodide is expected to be several times slower (Qollab's own docs say so).

### Pitfall 11: Compliance test passes vacuously
**How to avoid:** every gate has a negative test built in `tmp_path` (forbidden import via package, inside a function, inside try/except, via `importlib.import_module`; oversize file; three backend-construction forms; a global `backend` read; four bad signatures).

## Code Examples

All examples below were run in a scratch prototype on 2026-10-10: `23 passed`, `scripts/run_local.py` → `SMOKE TEST PASSED`, and `git archive` produced exactly `LICENSE README.md data/smoke_probe.json main.py neutron_qae/__init__.py neutron_qae/smoke.py requirements.txt`.

### `requirements.txt`
```text
# Qollab runtime requirements. Qollab reads only this file.
# Do not list numpy/scipy/matplotlib: Pyodide ships its own builds.
qiskit==2.5.2
```

### `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "neutron-qae"
version = "0.1.0"
description = "QAE vs classical Monte Carlo neutron transport through a SPARC-like first wall"
readme = "README.md"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.12"
dependencies = ["qiskit==2.5.2", "numpy>=2.0,<3", "matplotlib"]

[project.optional-dependencies]
dev = ["pytest>=9", "ruff==0.16.10", "qiskit-aer==0.17.2", "qiskit-algorithms==0.4.0"]

[tool.setuptools]
packages = ["neutron_qae"]          # REQUIRED: auto-discovery fails ("Multiple top-level packages discovered in a flat-layout: ['data', 'neutron_qae']")

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [".", "tests"]         # import main.py, neutron_qae and tests/compliance_checks.py without installing
addopts = "-ra"
markers = ["slow: long-running"]
```

### `.gitignore` and `.gitattributes`
```text
# .gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.ruff_cache/
build/
dist/
.DS_Store
.env
```
```text
# .gitattributes — files Qollab does not need. `git archive` omits them,
# keeping the upload under 100 files and free of local-only code.
.planning/ export-ignore
.claude/ export-ignore
tests/ export-ignore
scripts/ export-ignore
docs/ export-ignore
pyproject.toml export-ignore
.gitignore export-ignore
.gitattributes export-ignore
```

### `main.py`
```python
"""Qollab entry point - Phase 1 smoke test.

`backend` is a global that Qollab creates from the Select QPU dialog before this file runs.
Never create or assign it here. Qollab appends a call to main(<form values>) after this
file, so this file must not call main() itself and must not use a __name__ guard.
"""
import json
import time

from neutron_qae.smoke import backend_report, perf_probe, run_toy, runtime_report


def main(shots: int = 200, ghz_qubits: int = 6, ideal_mode: str = "none", perf_qubits: int = 12):
    t0 = time.perf_counter()
    print("=== Qollab smoke test (Phase 1) ===", flush=True)
    report = {"runtime": runtime_report(), "backend": backend_report(backend)}  # noqa: F821
    print(json.dumps(report, indent=1), flush=True)
    report["toy"] = run_toy(backend, shots=int(shots), n=int(ghz_qubits), ideal_mode=str(ideal_mode))  # noqa: F821
    report["perf"] = perf_probe(backend, qubits=int(perf_qubits))  # noqa: F821
    report["wall_clock_s"] = round(time.perf_counter() - t0, 3)
    print("QOLLAB_RUNTIME_REPORT=" + json.dumps(report), flush=True)
    try:
        from js import sendFile  # exists only inside Qollab's runtime

        sendFile("qollab_runtime_report.json", "application/json", json.dumps(report, indent=1))
    except ImportError:
        pass
    print("SMOKE TEST " + ("PASSED" if report["toy"]["accepted"] else "FAILED"), flush=True)
    return report
```

### `neutron_qae/smoke.py`
```python
"""Phase 1 smoke test: runtime probe + one IonQ-safe job on an INJECTED backend.

Nothing here creates a backend. Every function that needs one takes it as a parameter.
"""
from __future__ import annotations

import json
import sys
import time

PROBE_FILE = "data/smoke_probe.json"  # literal path: Qollab loads only files named by a literal string
IDEAL_MODES = ("none", "kwarg", "set_options")


def _version(mod_name: str, dist_name: str | None = None) -> str:
    try:
        mod = __import__(mod_name)
    except Exception as exc:  # noqa: BLE001 - record, never crash the smoke run
        return f"not importable ({type(exc).__name__})"
    v = getattr(mod, "__version__", None)
    if v:
        return str(v)
    try:
        from importlib.metadata import version

        return version(dist_name or mod_name)
    except Exception as exc:  # noqa: BLE001
        return f"unknown ({type(exc).__name__})"


def runtime_report() -> dict:
    rep = {
        "python": sys.version.split()[0],
        "python_full": sys.version,
        "platform": sys.platform,  # "emscripten" on Qollab/Pyodide
        "numpy": _version("numpy"),
        "qiskit": _version("qiskit"),
        "scipy": _version("scipy"),
        "qiskit_ionq": _version("qiskit_ionq", "qiskit-ionq"),  # installed by Qollab only for IonQ runs
    }
    try:
        import pyodide  # type: ignore[import-not-found]

        rep["pyodide"] = getattr(pyodide, "__version__", "?")
    except ImportError:
        rep["pyodide"] = None
    try:
        with open(PROBE_FILE, encoding="utf-8") as fh:
            rep["data_file_literal_path"] = json.load(fh)["probe"]
    except OSError as exc:
        rep["data_file_literal_path"] = f"FAILED: {exc}"
    return rep


def backend_report(backend) -> dict:
    cls = type(backend)
    opts = getattr(backend, "options", None)
    return {
        "class": f"{cls.__module__}.{cls.__qualname__}",
        "name": getattr(backend, "name", None),
        "options_noise_model": getattr(opts, "noise_model", None),
        "options_shots": getattr(opts, "shots", None),
        "is_ionq": is_ionq(backend),
    }


def is_ionq(backend) -> bool:
    """Detect qiskit-ionq without importing it (it is absent on the built-in simulator)."""
    return type(backend).__module__.startswith("qiskit_ionq")


def ghz(n: int):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, n, name=f"ghz{n}")
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n), range(n))
    return qc


def all_ones(n: int):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n, n, name=f"ones{n}")
    qc.x(range(n))
    qc.measure(range(n), range(n))
    return qc


def run_toy(backend, shots: int = 200, n: int = 6, ideal_mode: str = "none") -> dict:
    """ONE backend.run call carrying TWO circuits (proves the multi-circuit single job MLAE needs)."""
    from qiskit import transpile

    shots = max(2, min(int(shots), 10_000))
    n = max(2, min(int(n), 20))
    if ideal_mode not in IDEAL_MODES:
        raise ValueError(f"ideal_mode must be one of {IDEAL_MODES}, got {ideal_mode!r}")
    run_kwargs: dict = {"shots": shots}
    applied = "n/a (local ideal simulator)"
    if is_ionq(backend) and ideal_mode == "kwarg":
        run_kwargs["noise_model"] = "ideal"
        applied = "run(..., noise_model='ideal')"
    elif is_ionq(backend) and ideal_mode == "set_options":
        backend.set_options(noise_model="ideal")  # mutates the injected backend; does not create one
        applied = "backend.set_options(noise_model='ideal')"
    elif is_ionq(backend):
        applied = "none (dialog's noise model)"

    circuits = [ghz(n), all_ones(n)]
    t0 = time.perf_counter()
    tcirc = transpile(circuits, backend, optimization_level=1)  # IonQ recommends level 0-1
    t_transpile = time.perf_counter() - t0

    out = {"ideal_mode": ideal_mode, "applied": applied, "run_kwargs": run_kwargs, "n": n}
    t0 = time.perf_counter()
    try:
        job = backend.run(tcirc, **run_kwargs)  # the ONLY job this run sends
        result = job.result()
        counts = [dict(result.get_counts(i)) for i in range(len(tcirc))]
        out.update(accepted=True, error=None, counts=counts)
    except Exception as exc:  # noqa: BLE001 - AttributeError inside qiskit-ionq masks an IonQ error
        out.update(accepted=False, error=f"{type(exc).__name__}: {exc}", counts=[])
    out["transpile_s"] = round(t_transpile, 3)
    out["run_s"] = round(time.perf_counter() - t0, 3)

    if out["counts"]:
        ghz_counts, ones_counts = out["counts"]
        ideal_keys = {"0" * n, "1" * n}
        total = sum(ghz_counts.values())
        off = sum(v for k, v in ghz_counts.items() if k not in ideal_keys)
        exact_half = ghz_counts.get("0" * n) == total / 2 == ghz_counts.get("1" * n)
        out["ghz_off_ideal_fraction"] = round(off / total, 4)
        out["ones_fraction"] = round(ones_counts.get("1" * n, 0) / sum(ones_counts.values()), 4)
        out["noise_verdict"] = (
            "noisy" if off else "ideal, exact round(p*shots) (no shot noise)" if exact_half else "ideal, sampled"
        )
    return out


def perf_probe(backend, qubits: int = 12, depth: int = 20, shots: int = 1000) -> dict:
    """Pyodide speed probe. LOCAL backends only: IonQ allows one job per run."""
    if is_ionq(backend) or qubits <= 0:
        return {"skipped": "IonQ backend (one job per run) or qubits <= 0"}
    from qiskit import QuantumCircuit, transpile

    qubits = min(int(qubits), 24)
    qc = QuantumCircuit(qubits)
    for layer in range(int(depth)):
        for q in range(qubits):
            qc.ry(0.1 * (layer + 1) + 0.01 * q, q)
        for q in range(qubits - 1):
            qc.cx(q, q + 1)
    qc.measure_all()
    t0 = time.perf_counter()
    tqc = transpile(qc, backend, optimization_level=1)
    t1 = time.perf_counter()
    backend.run(tqc, shots=int(shots)).result()
    t2 = time.perf_counter()
    return {"qubits": qubits, "depth": int(depth), "cx": tqc.count_ops().get("cx", 0),
            "transpile_s": round(t1 - t0, 3), "run_s": round(t2 - t1, 3)}
```
`data/smoke_probe.json`: `{"probe": "data file loaded by literal path"}`. `neutron_qae/__init__.py`: a docstring plus `__all__ = ["smoke"]`. A tiny GHZ circuit on Forte's noise model gives a non-zero `ghz_off_ideal_fraction` with high probability at 6 qubits and 200 shots [ASSUMED: magnitude of Forte noise]. A zero off-ideal fraction with an exactly balanced split is the signature of the kwarg-ideal path.

### `scripts/run_local.py` (the allow-listed backend constructor)
```python
"""LOCAL ONLY: run main.py the way Qollab does, with an injected backend.

Allow-listed in tests/compliance_checks.py: the only place a backend is constructed.
"""
import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def make_backend(kind: str):
    if kind == "basic":
        from qiskit.providers.basic_provider import BasicSimulator
        return BasicSimulator()
    if kind == "aer":
        from qiskit_aer import AerSimulator
        return AerSimulator()
    raise SystemExit(f"unknown backend {kind!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="basic", choices=["basic", "aer"])
    ap.add_argument("--shots", type=int, default=200)
    a = ap.parse_args()
    os.chdir(ROOT)  # Qollab: project root is the working directory
    import main as entry
    entry.backend = make_backend(a.backend)   # mimic Qollab's injected global
    entry.main(shots=a.shots)
```

### `tests/compliance_checks.py` (stdlib only; mirrors Qollab's Walker)
```python
"""Static compliance checks (stdlib only). Mirrors Qollab's own import Walker:
ast-walk main.py, follow every import whose top-level name is a local file/folder,
scan EVERY node (function bodies and try/except included), collect external names."""
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

FORBIDDEN_REACHABLE = {"qiskit_aer", "qiskit_algorithms", "qiskit_ionq", "qiskit_ibm_runtime"}
MAX_FILE_BYTES = 2_000_000          # Qollab says "2 MB"; use the stricter decimal reading
MAX_QOLLAB_FILES = 100
BACKEND_CONSTRUCTORS = {"AerSimulator", "BasicSimulator", "IonQProvider", "QiskitRuntimeService",
                        "BraketLocalBackend", "BraketProvider", "GenericBackendV2", "StatevectorSimulator"}
BACKEND_FACTORY_ATTRS = {"get_backend", "backends"}
ALLOWLIST_DIRS = ("tests", "scripts")   # local-dev runners may construct backends


def _module_file(root: Path, dotted: str) -> Path | None:
    base = root.joinpath(*dotted.split("."))
    for cand in (base / "__init__.py", base.with_suffix(".py")):
        if cand.is_file():
            return cand
    return None


def _is_local(root: Path, top: str) -> bool:
    return (root / f"{top}.py").is_file() or (root / top).is_dir()


def _package_of(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        return ".".join(parts[:-1])
    return ".".join(parts[:-1])


def _imported_names(node: ast.AST, package: str):
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name
    elif isinstance(node, ast.ImportFrom):
        if node.level:
            parts = package.split(".") if package else []
            parts = parts[: len(parts) - (node.level - 1)]
            if node.module:
                parts.append(node.module)
            base = ".".join(parts)
        else:
            base = node.module or ""
        if base:
            yield base
        for alias in node.names:
            if alias.name != "*":
                yield f"{base}.{alias.name}" if base else alias.name


def reachable_modules(root: Path, entry: str = "main.py") -> tuple[list[Path], set[str]]:
    """Return (local .py files reachable from entry, external top-level names imported)."""
    root = root.resolve()
    start = root / entry
    seen, pending, externals = {start}, [start], set()
    while pending:
        path = pending.pop()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        package = _package_of(root, path)
        for node in ast.walk(tree):
            # importlib.import_module("x") / __import__("x") with a literal string
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                fn = node.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if fname in {"import_module", "__import__"}:
                    externals.add(node.args[0].value.split(".")[0])
            for name in _imported_names(node, package):
                parts = name.split(".")
                for i in range(1, len(parts) + 1):
                    dotted = ".".join(parts[:i])
                    top = parts[0]
                    if not _is_local(root, top):
                        externals.add(top)
                        break
                    f = _module_file(root, dotted)
                    if f and f not in seen:
                        seen.add(f)
                        pending.append(f)
    return sorted(seen), externals


def forbidden_imports(root: Path) -> set[str]:
    _, externals = reachable_modules(root)
    return externals & FORBIDDEN_REACHABLE


def tracked_files(root: Path) -> list[Path]:
    """Files git tracks; falls back to a directory walk outside a git checkout."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
        return [root / p for p in out.decode().split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist"}
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip and not d.endswith(".egg-info")]
            found.extend(Path(dirpath) / f for f in filenames)
        return found


def oversized_files(root: Path, limit: int = MAX_FILE_BYTES) -> list[tuple[str, int]]:
    return [(str(p.relative_to(root)), p.stat().st_size) for p in tracked_files(root)
            if p.is_file() and p.stat().st_size > limit]


def backend_constructions(root: Path) -> list[str]:
    """Calls that build a backend, in any .py file outside ALLOWLIST_DIRS."""
    hits = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if rel.parts[0] in ALLOWLIST_DIRS or any(p.startswith(".") or p in {"venv", "build"} for p in rel.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
                if name in BACKEND_CONSTRUCTORS or name in BACKEND_FACTORY_ATTRS or name.startswith("Fake"):
                    hits.append(f"{rel}:{node.lineno}: {name}(...)")
    return hits


def backend_assigned_in_main(root: Path) -> list[str]:
    """main.py must use the injected global `backend`, never assign it."""
    tree = ast.parse((root / "main.py").read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] \
            if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else []
        for t in targets:
            if isinstance(t, ast.Name) and t.id == "backend":
                hits.append(f"main.py:{node.lineno}")
        if isinstance(node, ast.Global) and "backend" in node.names:
            hits.append(f"main.py:{node.lineno}: global backend")
    return hits


def package_uses_global_backend(root: Path, package: str = "neutron_qae") -> list[str]:
    """Inside the package, `backend` must always be a function parameter, never a free global."""
    hits = []
    for path in sorted((root / package).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
            uses = any(isinstance(n, ast.Name) and n.id == "backend" and isinstance(n.ctx, ast.Load)
                       for n in ast.walk(fn))
            if uses and "backend" not in params:
                hits.append(f"{path.relative_to(root)}:{fn.lineno}: {fn.name}() reads global backend")
    return hits


def main_signature_problems(root: Path) -> list[str]:
    """Qollab builds the Run-settings form only if `def main(` is on one line at column 0,
    every parameter is annotated int/float/str/bool, and defaults are plain literals."""
    src = (root / "main.py").read_text(encoding="utf-8")
    lines = [ln for ln in src.splitlines() if ln.startswith("def main(")]
    if len(lines) != 1:
        return [f"expected exactly one 'def main(' line at column 0, found {len(lines)}"]
    if not lines[0].rstrip().endswith(":"):
        return ["def main(...) signature must fit on one line"]
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    probs = []
    for a in fn.args.args:
        ann = a.annotation
        if not (isinstance(ann, ast.Name) and ann.id in {"int", "float", "str", "bool"}):
            probs.append(f"parameter {a.arg!r} must be annotated int/float/str/bool")
    for d in fn.args.defaults:
        if not isinstance(d, ast.Constant):
            probs.append(f"default at line {d.lineno} must be a plain literal (no -x, no expressions)")
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs:
        probs.append("no *args/**kwargs/keyword-only params (Qollab passes form values positionally)")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            probs.append(f"line {node.lineno}: remove `if __name__ == ...` (Qollab calls main() itself)")
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and \
                getattr(node.value.func, "id", "") == "main":
            probs.append(f"line {node.lineno}: do not call main() at module level")
    return probs


def qollab_upload_files(root: Path) -> list[str]:
    """Tracked files that `git archive` would ship (export-ignore entries in .gitattributes removed)."""
    ignored = []
    attrs = root / ".gitattributes"
    if attrs.is_file():
        for line in attrs.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith("#") and "export-ignore" in parts[1:]:
                ignored.append(parts[0].rstrip("/"))
    files = [p.relative_to(root).as_posix() for p in tracked_files(root)]
    return [f for f in files if not any(f == i or f.startswith(i + "/") for i in ignored)]
```
`qiskit_ionq` and `qiskit_ibm_runtime` are added to the forbidden set on top of the success criterion's two, because of R4. `qollab_upload_files` returned exactly the same seven files as `git archive` in the prototype.

### `tests/test_compliance.py`
```python
"""PLAT-04 / PLAT-01 compliance gates. Each check has a negative test proving it can fail."""
from pathlib import Path

import pytest

import compliance_checks as cc

ROOT = Path(__file__).resolve().parents[1]


def test_nothing_reachable_from_main_imports_aer_or_algorithms():
    assert cc.forbidden_imports(ROOT) == set()


def test_no_committed_file_over_2mb():
    assert cc.oversized_files(ROOT) == []


def test_no_backend_constructed_outside_local_runners():
    assert cc.backend_constructions(ROOT) == []
    assert cc.backend_assigned_in_main(ROOT) == []
    assert cc.package_uses_global_backend(ROOT) == []


def test_main_signature_is_qollab_form_compatible():
    assert cc.main_signature_problems(ROOT) == []


def test_no_file_names_with_spaces():
    assert [str(p.relative_to(ROOT)) for p in cc.tracked_files(ROOT) if " " in p.name] == []


def test_every_data_file_is_referenced_by_literal_path():
    files, _ = cc.reachable_modules(ROOT)
    text = "\n".join(p.read_text(encoding="utf-8") for p in files)
    data = [p for p in (ROOT / "data").rglob("*") if p.is_file()] if (ROOT / "data").is_dir() else []
    missing = [str(p.relative_to(ROOT)) for p in data if f'"{p.relative_to(ROOT).as_posix()}"' not in text]
    assert missing == []


def test_qollab_upload_stays_under_100_files_and_ships_entry_point():
    files = cc.qollab_upload_files(ROOT)
    assert len(files) <= cc.MAX_QOLLAB_FILES
    assert {"main.py", "requirements.txt", "LICENSE"} <= set(files)
    assert not any(f.startswith(("tests/", "scripts/", ".planning/")) for f in files)


# ---- negative tests: prove each gate fires -------------------------------------------
@pytest.fixture
def fake_project(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "main.py").write_text("from pkg import core\n\ndef main(shots: int = 10):\n    core.go(backend, shots)\n")
    return tmp_path


@pytest.mark.parametrize("stmt", [
    "import qiskit_aer\n",
    "from qiskit_aer import AerSimulator\n",
    "def f():\n    from qiskit_algorithms import IterativeAmplitudeEstimation\n",
    "try:\n    import qiskit_aer\nexcept ImportError:\n    pass\n",
    "import importlib\nimportlib.import_module('qiskit_algorithms')\n",
])
def test_forbidden_import_is_detected_through_package(fake_project, stmt):
    (fake_project / "pkg" / "core.py").write_text(stmt + "\ndef go(backend, shots):\n    pass\n")
    assert cc.forbidden_imports(fake_project)


def test_oversized_file_is_detected(fake_project):
    (fake_project / "big.json").write_bytes(b"0" * (cc.MAX_FILE_BYTES + 1))
    (fake_project / "pkg" / "core.py").write_text("def go(backend, shots):\n    pass\n")
    assert cc.oversized_files(fake_project)


@pytest.mark.parametrize("code", [
    "from qiskit_aer import AerSimulator\ndef go(backend, shots):\n    b = AerSimulator()\n",
    "def go(backend, shots):\n    from qiskit.providers.basic_provider import BasicSimulator\n    return BasicSimulator()\n",
    "def go(backend, shots):\n    return provider.get_backend('simulator')\n",
])
def test_backend_construction_is_detected(fake_project, code):
    (fake_project / "pkg" / "core.py").write_text(code)
    assert cc.backend_constructions(fake_project)


def test_global_backend_read_in_package_is_detected(fake_project):
    (fake_project / "pkg" / "core.py").write_text("def go(shots):\n    return backend.run\n")
    assert cc.package_uses_global_backend(fake_project, package="pkg")


@pytest.mark.parametrize("src", [
    "def main(shots=10):\n    pass\n",
    "def main(shots: int = -1):\n    pass\n",
    "def main(\n    shots: int = 10,\n):\n    pass\n",
    "def main(shots: int = 10):\n    pass\n\nif __name__ == '__main__':\n    main()\n",
])
def test_bad_main_signature_is_detected(tmp_path, src):
    (tmp_path / "main.py").write_text(src)
    assert cc.main_signature_problems(tmp_path)
```

### `tests/test_smoke.py`
```python
"""PLAT-02 local mirror: main.main() runs end-to-end with an injected BasicSimulator."""
import os
from pathlib import Path

from qiskit.providers.basic_provider import BasicSimulator  # tests are allow-listed

ROOT = Path(__file__).resolve().parents[1]


def test_main_runs_with_injected_basic_simulator(monkeypatch):
    monkeypatch.chdir(ROOT)                     # Qollab: project root is the cwd
    import main as entry
    monkeypatch.setattr(entry, "backend", BasicSimulator(), raising=False)
    report = entry.main(shots=200, ghz_qubits=4, ideal_mode="none", perf_qubits=4)
    assert report["toy"]["accepted"]
    assert report["toy"]["ghz_off_ideal_fraction"] == 0.0     # ideal simulator
    assert report["toy"]["ones_fraction"] == 1.0
    assert report["runtime"]["data_file_literal_path"].startswith("data file")


def test_package_imports_without_qiskit_extras():
    import neutron_qae.smoke  # noqa: F401
    assert os.path.isfile(ROOT / "neutron_qae" / "smoke.py")
```

### `tests/test_docs.py` (PLAT-03 / DOCS-06; passes in the prototype against the LICENSE and README blocks below: 26 tests total)
```python
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTION = "This effort is supported by Qollab & IonQ."

def test_mit_license_present():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License") and "Permission is hereby granted, free of charge" in text

def test_readme_attribution_and_disclosure():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert ATTRIBUTION in text
    for needle in ("Qiskit", "Apache-2.0", "NumPy", "BSD-3-Clause", "Claude Code", "GSD", "MIT"):
        assert needle in text, f"disclosure missing {needle}"

def test_runtime_findings_recorded():
    text = (ROOT / "docs" / "QOLLAB-RUNTIME.md").read_text(encoding="utf-8")
    assert "QOLLAB_RUNTIME_REPORT=" in text   # at least one pasted Qollab run
```
`test_runtime_findings_recorded` will fail until the Qollab human step pastes a run. Mark it `@pytest.mark.xfail(strict=False)` until then, or add it only in the plan that records findings.

### `LICENSE` (canonical MIT text from choosealicense.com; fill year and holders)
```text
MIT License

Copyright (c) 2026 Hippolyte Delloye and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
[CITED: raw.githubusercontent.com/github/choosealicense.com/gh-pages/_licenses/mit.txt]. The copyright-holder line is a user decision: list teammates by name once known [ASSUMED].

### README disclosure section (DOCS-06), to be placed in `README.md` so it also appears on the Qollab write-up
```markdown
This effort is supported by Qollab & IonQ.

## Libraries, tools and licenses (disclosure)

| Component | Version | How we use it | License |
|-----------|---------|---------------|---------|
| Qiskit | 2.5.2 | Circuits, transpilation, BasicSimulator | Apache-2.0 |
| qiskit-ionq | 1.0.2 on Qollab (1.1.1 locally) | IonQ simulator backend, provided by Qollab's runtime | Apache-2.0 |
| NumPy | Pyodide build on Qollab (2.x) | Numerics | BSD-3-Clause (bundled parts: 0BSD, MIT, Zlib, CC0-1.0) |
| SciPy / Matplotlib | Pyodide builds | Later phases: fitting, figures | BSD-3-Clause / Matplotlib License (PSF-based) |
| qiskit-aer, qiskit-algorithms | 0.17.2, 0.4.0 | Local tests and precomputation only; never run on Qollab | Apache-2.0 |
| pytest, ruff | 9.1.1, 0.16.10 | Testing, linting | MIT |
| Pyodide | 314.0.7 | Qollab's in-browser Python runtime (not redistributed by us) | MPL-2.0 |
| Claude Code (Anthropic) | — | AI coding assistant: research, planning, code and docs drafting, reviewed by the team | Anthropic terms; outputs assigned to the user |
| GSD Core (@opengsd/gsd-core) | 1.16.0 | AI workflow framework driving planning and execution | MIT |

All third-party libraries are used under their open-source licenses, which permit use in an
MIT-licensed project with notices kept. No third-party source code is copied into this repository
(if any is vendored later, its license header and NOTICE are kept and the file is listed here).
The hackathon rules allow AI tools and open-source libraries when disclosed; this section is that disclosure.
```
License sources: installed-package metadata (`qiskit 2.5.2 | Apache-2.0`, `qiskit-ionq | Apache 2.0`, `numpy | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`, `pytest | MIT`), PyPI JSON (`qiskit-aer Apache 2.0`, `qiskit-algorithms Apache-2.0`, `ruff MIT`, matplotlib "License agreement for matplotlib versions 1.3.0 and later"), Pyodide LICENSE ("Mozilla Public License Version 2.0"), npm (`@opengsd/gsd-core 1.16.0 license 'MIT'`) [VERIFIED: tool output this session]. Anthropic Consumer Terms: "Subject to your compliance with our Terms, we assign to you all of our right, title, and interest—if any—in Outputs." (effective October 8, 2025) [CITED: anthropic.com/legal/consumer-terms]. If Hippolyte uses a Team/Enterprise/API plan, the Commercial Terms apply instead [ASSUMED]. "Confirmation the team may use them" for permissive licenses is standard practice, not legal advice [ASSUMED].

### `docs/QOLLAB-RUNTIME.md` template (the record later phases read)
```markdown
# Qollab runtime findings (Phase 1 smoke test)

## Static facts (read from Qollab's runtime code, 2026-10-10)
- Pyodide v314.0.7 (Python 3.14.2, numpy 2.4.6, scipy 1.18.0, matplotlib 3.10.8 in its lockfile)
- Qollab /py index: qiskit 2.5.2 (only wasm build), qiskit-ionq 1.0.2, qiskit-aer 0.17.2
- backend preamble: built-in = BasicSimulator(); IonQ remote sim = IonQProvider("STUB").get_backend("simulator") + set_options(noise_model="<qpu>")
- qiskit_ionq installed only when an IonQ backend is selected; qiskit_aer only when an IBM noise model is selected
- main(...) is appended with positional form values; floats can arrive as ints
- One IonQ job per run (client-enforced); 403 → "anonymous user" message; proxy rejects oversized request bodies
- anon_enabled = true on 2026-10-10 (GET https://api.qollab.xyz/api/ionq/backends/simulator/cost)

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
```

## Human-Action Runbook (the plans need these as `checkpoint:human-action` tasks)

### A. GitHub (PLAT-03)
1. `brew install gh` (Homebrew present at `/opt/homebrew/bin/brew`; formula gh 2.102.0) [VERIFIED: brew info].
2. **Human:** `gh auth login` → GitHub.com → HTTPS → "Login with a web browser" (device code). Then `gh auth setup-git`.
3. Set identity (repo-local): `git config user.name "Hippolyte Delloye"` and `git config user.email "<id>+<username>@users.noreply.github.com"` (shown at github.com/settings/emails). The email is a user choice [ASSUMED].
4. `gh repo create <repo-name> --public --source=. --remote=origin --push --description "QAE vs classical MC neutron transport through a SPARC first wall (Qollab x IonQ hackathon)"`. Flags quoted from the manual: `--source` "Specify path to local repository to use as source", `--remote` "Specify remote name for the new repository", `--push` "Push local commits to the new repository" [CITED: cli.github.com/manual/gh_repo_create]. Do **not** pass `--license mit`, since LICENSE is already committed.
5. **Human provides teammate GitHub usernames.** For each: `gh api -X PUT repos/<owner>/<repo>/collaborators/<username>`. The endpoint is `PUT /repos/{owner}/{repo}/collaborators/{username}`; `201` = invitation created, `204` = added directly; the `permission` parameter "applies only to organization-owned repositories" (personal repos give write access); invitees must accept from email or notifications [CITED: docs.github.com/en/rest/collaborators/collaborators].
6. Verify: `gh api repos/<owner>/<repo>/invitations --jq '.[].invitee.login'` [ASSUMED endpoint; the fetched page did not list it]. Then a fresh-clone check in a temp dir: `git clone https://github.com/<owner>/<repo> /tmp/x && cd /tmp/x && python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && .venv/bin/pytest -q`. This automates success criterion 3 from a teammate's point of view.
**Fallback if gh cannot be installed or authenticated:** create the repo on github.com/new (public, no README/license), then `git remote add origin https://github.com/<owner>/<repo>.git && git push -u origin main` (macOS Keychain prompts for a PAT), and add collaborators under Settings → Collaborators.

### B. Qollab (PLAT-02)
1. Commit everything, then `git archive --format=zip -o "$HOME/Desktop/qollab-smoke.zip" HEAD`.
2. **Human:** qollab.xyz → "+ New Project" → Project shape "Upload your own files" → drop the zip → the card should say Python and 7 files → Create.
3. Code tab → Run Project → Run → Select QPU **Built-in simulator** → Run settings form shows Shots / Ghz Qubits / Ideal Mode / Perf Qubits → Run → copy the `QOLLAB_RUNTIME_REPORT=` line. Optionally rerun with Perf Qubits 16 and 20 (Pyodide speed).
4. Run with **IonQ Forte 1 (remote simulator)**, Ideal Mode `none`; then Stop → Run with `kwarg`; then `set_options`. Each is a separate run, one job each. Copy each report.
5. Publish → Version name `v0.0-smoke` → Visibility "public and the new default version". In the Project Card add the GitHub repo link and tags `qiskit`, `ionq`.
6. Open `qollab.xyz/u/<username>/<project>` in a **Chrome incognito window** → Run on Qollab → Built-in simulator → Run; then IonQ Forte 1 → Run. Copy both reports; note any "anonymous user" message.
7. Paste all reports into `docs/QOLLAB-RUNTIME.md`, fill the conclusions, commit, push.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Project research assumed Qollab behaviour undocumented (LOW) | Runtime mechanics readable from Qollab's worker bundle | Verified 2026-10-10 | Most Phase 1 unknowns are now HIGH. Only server acceptance of "ideal" and Pyodide speed remain empirical |
| qiskit-ionq 1.0.2 assumed similar to 1.1.1 | Confirmed identical noise-model handling in both | 2026-10-10 local probe | Local dev on 1.1.1 is representative for payload logic |
| setuptools flat-layout auto-discovery | Must list packages explicitly | setuptools ≥ 61 behaviour | `[tool.setuptools] packages = ["neutron_qae"]` |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Qollab proxy/IonQ may reject `noise_model="ideal"` (server-side behaviour unknown) | noise_model table | Low: the smoke test measures it; Phase 4 already plans for noise-only IonQ |
| A2 | Forte noise model gives non-zero GHZ off-ideal fraction at 6 qubits / 200 shots | Code Examples | Low: a "noisy" run reading as "ideal, exact" would mislead. Cross-check with backend `options_noise_model` and the run kwarg in the same report |
| A3 | Pyodide-installed packages expose `__version__` or dist-info | Don't Hand-Roll | Low: the code falls back and prints "unknown (...)" rather than crashing |
| A4 | GitHub "Download ZIP" honours `export-ignore` like `git archive` | Don't Hand-Roll | Low: the runbook uses local `git archive`, which was verified |
| A5 | `GET repos/{o}/{r}/invitations` lists pending invites | Runbook A6 | Low: verification step only; the web UI is the fallback |
| A6 | setuptools ≥ 77 needed for PEP 639 `license = "MIT"` string | Standard Stack | Low: the editable install succeeded in the prototype with current setuptools; drop to the `license = {text = "MIT"}` form if an older setuptools complains |
| A7 | LICENSE copyright holders = "Hippolyte Delloye and contributors" | LICENSE | Medium: the user should name teammates |
| A8 | Hippolyte's Claude plan is consumer (Consumer Terms apply) | Disclosure | Low: either term set assigns or grants output rights; wording only |
| A9 | Permissive-license compatibility statement ("team may use them") | Disclosure | Low: Apache-2.0/BSD/MIT/PSF-based are standard-compatible with MIT; not legal advice |
| A10 | GitHub noreply email preferred for new commits | Runbook A3 | Privacy only; user choice |
| A11 | `sys.platform == "emscripten"` on Qollab | smoke.py comment | None: the value is reported, not asserted |

## Open Questions

1. **Does the Qollab proxy / IonQ accept `noise_model="ideal"` from the playground?**
   - Known: the client sends it (both qiskit-ionq versions). Qollab's fetch rewriter does not touch the job body; it only parses `input` for the circuit panel.
   - Unclear: server-side validation by the Qollab proxy and IonQ.
   - Recommendation: smoke runs 4b/4c. Record in `docs/QOLLAB-RUNTIME.md`.
2. **Pyodide speed for the Phase 6 live demo.**
   - Recommendation: perf runs at 12/16/20 qubits on the built-in simulator; compare with the native 0.021 / 0.338 / 6.486 s.
3. **Teammate GitHub usernames and LICENSE holder names.** Needed from Hippolyte at the GitHub checkpoint.
4. **Does a zero-parameter `def main():` get called?** The parser yields an empty default list, so probably yes, but this is not needed since the toy has parameters.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Everything | ✓ | 3.14.8 (`/Library/Frameworks/Python.framework/Versions/3.14`) | — |
| git | Repo, archive | ✓ | 2.39.3 (Apple) | — |
| git identity | Commits | ✗ (no `~/.gitconfig`; commits use hostname email) | — | Set repo-local `user.name`/`user.email` |
| GitHub CLI `gh` | PLAT-03 | ✗ | Homebrew formula 2.102.0 available | `brew install gh`; or the web UI fallback |
| Homebrew | Installing gh | ✓ | `/opt/homebrew/bin/brew` | — |
| SSH keys | git push | ✗ (`~/.ssh` absent) | — | HTTPS via `gh auth setup-git` or a PAT |
| Node (GSD tooling) | Planning commits | ✓ | `~/.local/node/bin` | — |
| Chrome (JSPI) | Qollab runs, incognito check | ✓ | 155.0.8059.39 | Firefox is installed (needs ≥ 153 for JSPI) |
| Qollab account | Publishing | Assumed ✓ (registered team) | — | — |
| Network to qollab.xyz / api.qollab.xyz / pypi.org | Research, install | ✓ | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `gh` (brew install, or web UI); git identity (set locally); SSH (HTTPS).

## Validation Architecture

Skipped: `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`. The Phase 1 test suite (compliance gates with negative tests, smoke test, docs test) is still specified above. Quick command: `pytest -q` (< 3 s in the prototype).

## Security Domain

`security_enforcement: true`, ASVS level 1, block on high.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Qollab owns auth; no app auth) | — |
| V3 Session Management | no | — |
| V4 Access Control | yes, lightly: GitHub collaborator write access, Qollab draft vs public | Invite only named teammates; personal repo gives push; Qollab: only the owner edits |
| V5 Input Validation | yes | `main()` form inputs are coerced and clamped (`shots` 2..10,000, `ghz_qubits` 2..20, `perf_qubits` ≤ 24) and `ideal_mode` is checked against an allow-list |
| V6 Cryptography | no | — |
| V8 Data Protection | yes | No secrets in code (the IonQ key is the platform's `"STUB"` rewritten by the proxy); `.env` in `.gitignore`; "Your project's code is public once you publish it, so never put an API key, token or password in it." [CITED: runtime-environment doc] |
| V10 Malicious Code / V14 Config (supply chain) | yes | Exact `qiskit==2.5.2`; dev pins; no `postinstall` scripts; one human-verify on the dev install |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API token committed to the public repo / Qollab | Information disclosure | Never needed (platform key). Pre-publish `git grep -n -i -E "token|api_key|IonQProvider\("` returns only allow-listed lines |
| Slopsquatted dependency | Tampering | Names from official docs only; legitimacy audit above; exact pin for the Qollab-facing file |
| Oversized jobs from the form (cost/queue abuse) | Denial of service | Clamping in `run_toy`/`perf_probe`; IonQ one-job rule; simulators are free |
| Personal data in git history (hostname email) | Information disclosure | Noreply email for new commits; old commits low-sensitivity |
| Untrusted remote content | Tampering | No network fetch in the core path (Qollab allows GET only) |

## Sources

### Primary (HIGH confidence)
- Qollab worker `https://qollab.xyz/_nuxt/pyworker-C7AWKy02.js` and UI chunk `BWPMdZ7B.js` (fetched 2026-10-10): Pyodide import URL, backend preamble, `main()` injection, form parser, Walker/LazyFinder source, provider package table, fetch rewriter (one job, 403, body-too-large).
- `https://qollab.xyz/py/index.json?v=27`: private wheel index contents.
- `https://api.qollab.xyz/api/ionq/backends/simulator/cost`: `{"cost":"0","anon_enabled":true}`.
- `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide-lock.json`: Python 3.14.2, numpy 2.4.6, scipy 1.18.0, matplotlib 3.10.8.
- qiskit-ionq 1.0.2 and 1.1.1 source (`ionq_backend.py`, `helpers.py`, `ionq_job.py`) plus a local payload probe.
- Local prototype: 23 pytest passes, `run_local.py` PASSED, `git archive` contents, flat-layout install error, BasicSimulator option behaviour, native perf timings.
- Qollab docs (server-rendered, fetched 2026-10-10): runtime-environment, python-qiskit-projects, compute-backends, ideal-vs-noise-model-simulators, primitives, publish, upload-your-files, project-anatomy, write-your-project-page, transpilation, error-reference, how-your-circuit-is-compiled, faq, fork-and-remix, run-your-code.
- Qollab hackathon terms `https://qollab.xyz/programs/hackathon/terms` and how-it-works.

### Secondary (MEDIUM confidence)
- GitHub CLI manual (gh repo create); GitHub REST docs (collaborators); micropip API docs; choosealicense MIT text; Anthropic Consumer Terms; PyPI JSON metadata; npm metadata for @opengsd/gsd-core.

### Tertiary (LOW confidence)
- None relied on for decisions. Server-side acceptance of `noise_model="ideal"` stays empirical (A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Pins match Qollab's own index; packaging verified by prototype.
- Architecture / runtime mechanics: HIGH. Read from Qollab's live code and executed against qiskit-ionq source. These are snapshots and can change on redeploy (bundle file names are hashed).
- Pitfalls: HIGH for client-side mechanics; MEDIUM for server-side items (anon flag, ideal acceptance, index drift).

**Research date:** 2026-10-10
**Valid until:** end of the hackathon (2026-10-11 19:00 ET). Re-check R2 (index), R12 (anon flag) and the smoke test before the final publish.
