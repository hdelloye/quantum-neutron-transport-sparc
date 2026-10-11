# Handoff for teammates

This repository holds the Quantum Neutron Transport project for the Qollab x IonQ Hackathon: a classical Monte Carlo and a Qiskit amplitude-estimation circuit that estimate the same neutron transmission through a SPARC-like first wall. Start with [README.md](README.md) (what the project does, how to run it, the results and the limitations), then read this file to pick up the work. This file stays on GitHub; it is export-ignored and never uploaded to Qollab.

## Module owners

Every row is owned by Hippolyte Delloye for now. To take a row over, edit this table in a pull request and put your name in the Owner column.

| Module | Area | Owner | Tests |
|---|---|---|---|
| main.py | Qollab entry point: quick, qae and smoke modes, form validation | Hippolyte Delloye | tests/test_main_quick.py, tests/test_main_qae.py, tests/test_compliance.py |
| neutron_qae/smoke.py | Phase 1 Qollab runtime smoke test | Hippolyte Delloye | tests/test_smoke.py |
| neutron_qae/nuclear_data.py | cited 14.1 MeV ENDF/B-VIII.0 cross sections, material compositions | Hippolyte Delloye | tests/test_nuclear_data.py, tests/test_physics_doc.py |
| neutron_qae/problem.py | ProblemSpec: SPARC first-wall geometry and one-group materials | Hippolyte Delloye | tests/test_problem.py |
| neutron_qae/kernels.py | frozen Kernels contract v1 | Hippolyte Delloye | tests/test_kernels_contract.py, tests/test_kernels_golden.py |
| neutron_qae/exact.py | exact lattice solver (T0, T1) | Hippolyte Delloye | tests/test_exact.py |
| neutron_qae/random_source.py | injected random source for every Monte Carlo engine | Hippolyte Delloye | tests/test_random_source.py |
| neutron_qae/mc_continuous.py | continuous Woodcock delta-tracking Monte Carlo (physics reference) | Hippolyte Delloye | tests/test_mc_continuous.py |
| neutron_qae/mc_lattice.py | matched lattice Monte Carlo (classical baseline) | Hippolyte Delloye | tests/test_mc_lattice.py |
| neutron_qae/oracle.py | state preparation A (Q0, Q1, Q1lite) behind the contract gate | Hippolyte Delloye | tests/test_oracle.py |
| neutron_qae/grover.py | Grover powers, transpile-once, resource table | Hippolyte Delloye | tests/test_grover.py, tests/test_quantum_doc.py |
| neutron_qae/mlae.py | maximum-likelihood amplitude estimation, cost N_A | Hippolyte Delloye | tests/test_mlae.py |
| neutron_qae/runners.py | analytic, backend and IonQ one-circuit runners; IonQ record schema | Hippolyte Delloye | tests/test_runners.py, tests/test_ionq_records.py |
| neutron_qae/artifacts.py | result artifacts: literal data/ paths, schemas, Markdown tables | Hippolyte Delloye | tests/test_artifacts.py, tests/test_results_doc.py |
| neutron_qae/analysis.py | RMSE series, log-log fits, cost at a target, chi-square | Hippolyte Delloye | tests/test_analysis.py, tests/test_studies.py |
| neutron_qae/figures.py | matplotlib figures from the artifact JSON | Hippolyte Delloye | tests/test_artifacts.py, tests/test_main_quick.py |
| scripts/ | local tools: run_local, sweeps, render_figures, freeze_kernels, ingest_ionq_records, qae_local | Hippolyte Delloye | tests/test_ingest_ionq_records.py, tests/test_studies.py |
| data/ | committed results (JSON plus PNG), IonQ records | Hippolyte Delloye | tests/test_artifacts.py, tests/test_compliance.py |

## Run the tests

```bash
git clone https://github.com/hdelloye/quantum-neutron-transport-sparc.git
cd quantum-neutron-transport-sparc
python3.14 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"            # qiskit, qiskit-aer, qiskit-algorithms, pytest, ruff
.venv/bin/python -m pytest -q                           # default suite, under 30 s
NEUTRON_QAE_SLOW=1 .venv/bin/python -m pytest -q -m slow   # slow checks: figure re-render, full quick run
.venv/bin/python scripts/freeze_kernels.py              # contract check: prints GOLDEN OK kernels_v1.json
.venv/bin/python scripts/render_figures.py --check      # re-render the four PNGs from data/: RENDER CHECK OK 4
.venv/bin/python scripts/run_local.py                   # quick mode, as on Qollab: QUICK MODE OK
.venv/bin/python scripts/run_local.py --mode qae --seed 2026   # Phase 4 QAE run: QAE RUN COMPLETED
.venv/bin/python scripts/run_local.py --mode smoke      # Phase 1 smoke test: SMOKE TEST PASSED
```

- Always call tools as `.venv/bin/python -m pytest` and `.venv/bin/python -m pip`: if the checkout path contains spaces, the console-script shebangs in the venv break, while `python -m` always works.
- `tests/test_compliance.py` enforces the Qollab rules on every run: nothing reachable from `main.py` imports qiskit-aer or qiskit-algorithms, no committed file over 2 MB, no backend constructed outside `scripts/run_local.py`, a one-line Qollab-compatible `main()` signature, no whitespace in paths, every data file referenced by a literal path, and an upload under 100 files that ships `main.py`.
- The sweep scripts write to `data/` by default. For a trial run use `--profile quick --out-dir <scratch directory>` so the committed full-profile files are never overwritten.

## The frozen Kernels contract

`neutron_qae/kernels.py` defines `KERNELS_CONTRACT_VERSION = "1"` and `build_kernels(sparc_first_wall())`, the only source of the physics tables: `first_collision`, `scatter_ratio`, `flight` and `back_exit_rows` (shapes and meanings in [docs/PHYSICS.md](docs/PHYSICS.md), section "Kernels contract v1"). The values are frozen in `tests/golden/kernels_v1.json`, and T1 = 0.24300446519524305 is checked at rtol 1e-12. The classical Monte Carlo and the quantum oracle both import these kernels; neither side ever rebuilds its own tables.

To change the contract (any change to a table, the quadrature, the outcome order, the register layout or the problem inputs):
1. edit the code and bump `KERNELS_CONTRACT_VERSION` in `neutron_qae/kernels.py`;
2. regenerate the golden file with `.venv/bin/python scripts/freeze_kernels.py --write --force`;
3. rerun the contract tests of both branches (classical: `tests/test_mc_lattice.py`, `tests/test_exact.py`; quantum: `tests/test_oracle.py`, `tests/test_grover.py`) and the whole suite;
4. update docs/PHYSICS.md and name the change and the new T1 in the commit message.

## Qollab rules

The rules every module follows are listed in README, section "Rules every module follows", and enforced by tests/test_compliance.py. Two more apply when you touch the Qollab side:
- IonQ backends on Qollab accept one job per run and one bare circuit per job (`ionq.circuit.v1`); never pass a list of circuits to an IonQ backend.
- Qollab copies README.md into the project write-up only when a project is created. To change the write-up of an existing project, edit it on Qollab, or create a fresh project from a new `git archive` bundle.

## What is left

1. **Add teammates as collaborators (PLAT-03).** Once their GitHub usernames are known: `gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/<username> -f permission=push` (201 means invited, 204 already a collaborator, 404 a wrong spelling).
2. **Investigate the IonQ ideal-simulator discrepancy.** The three IonQ Forte 1 runs give an estimate 6.4 sigma below T1 and the k = 1 and k = 2 points deviate beyond shot noise. The circuits Qollab's browser transpiled differ from the local transpile by one gate per application of A (WR-01). Record, per run, the submitted circuit's own statevector P(flag) and a QASM hash, then re-run k = 0, 1 and 2.
3. **Enable noisy IonQ runs (CR-01).** `main.py` refuses `ideal_mode = none` because qiskit-ionq returns round(p x shots) counts that do not sum to shots. The fix belongs in `neutron_qae/runners.py`: keep the raw counts, enforce the shot sum only for sampled records, relax `validate_ionq_record` accordingly and add a rounding fake to the tests.
4. **Harden `scripts/ingest_ionq_records.py` (WR-02, ingest half).** Catch OverflowError and RecursionError on malformed pasted records; `main.py` already survives a malformed `data/ionq_runs.json`.
5. **K = 2 contract v2 (QC-08).** About 20 qubits, local only; a contract change, so follow the procedure above.
6. **Interactive front end (v2).** A Qollab JS project type that imports this same Python package and lets visitors change the wall and the shot budget.
7. **Absorption split by material (PD-14).** Report where absorbed neutrons stop, per material.
8. **Open deferred items.** `.planning/phases/04-quantum-oracle-amplitude-estimation/deferred-items.md` lists a ruff TRY004 note on the fake IonQ backend in tests/test_smoke.py.
