# Quantum oracle and amplitude estimation (Phase 4)

This document describes the circuits, the estimator and the IonQ protocol that Phase 4 added under `neutron_qae/`: `oracle.py` (the state preparation A), `grover.py` (Grover powers and resources), `mlae.py` (the estimator) and `runners.py` (the backends). `main.py` runs them in its `qae` mode. The physics behind the numbers is in [PHYSICS.md](PHYSICS.md).

## Register layout

Every random choice of the K = 1 lattice model gets its own fresh register. Qubit i is bit i of the bit string that `exact.py` enumerates. The layout string is quoted verbatim from `exact.REGISTER_LAYOUT`:

```text
x(5) | a(1)<<5 | phi(4)<<6 | e(1)<<10, little-endian (bit i = Qiskit qubit i)
```

| Model | Qubits | Flag qubit | Registers (qubit indices) | Flag probability |
|---|---|---|---|---|
| Q0 | 5 | 4 | x(0-4): first-collision column; x = 16 means uncollided | T0 (no collision allowed) |
| Q1 | 12 | 11 | x(0-4) a(5) phi(6-9) e(10) T(11) | T1 = 0.24300446519524305 |
| Q1lite | 8 | 7 | x(0-4) a(5) e(6) T(7) | T1 (escape angle averaged over phi) |

- x is one `StatePreparation` of the square-rooted first-collision distribution (17 outcomes padded to 32 amplitudes).
- a and e are `UCRYGate` multiplexers controlled on x[0:4], and e is also controlled on phi. phi is 4 Hadamards, giving 16 uniform direction bins.
- The flag is T = x4 OR (NOT x4 AND a AND e). It is always the highest qubit.
- **The x = 16 rule:** the rotations controlled on x[0:4] see 0000 when x = 16 (uncollided), so that branch rotates a and e exactly like column 0. This is `exact.py`'s `col = x % nx` convention. It is harmless because T = 1 whenever x4 = 1.
- Q1 is the headline model. **Q1lite** exists only as the IonQ size fallback (see the size ladder below). It has no direction bits, so its strings cannot feed the exit-row histogram. Its flag probability is still exactly T1.
- Q1 uses 12 of the 24 qubits allowed. There is no phase-estimation, ancilla or step-counter register.

## Contract gate

`oracle.make_problem(model)` is the only source of circuits for the runners and for `main.py`. It builds A and computes the flag probability from qiskit's exact `Statevector`. It raises `ContractError` unless that probability equals the exact lattice value `exact.transmission_within(kernels, K)` within `CONTRACT_TOL = 1e-12`, with K = 0 for Q0 and K = 1 for Q1 and Q1lite. The measured difference is 3.5e-15 for Q1 and Q1lite and 3.2e-15 for Q0. Every QAE run, on the Built-in simulator or on IonQ, prints this check before it sends a job.

## Resource table

Each row is one full transpile of the logical circuit, done by `grover.resource_table()` and printed by `.venv/bin/python scripts/qae_local.py resources`. A test checks that this text equals the code's output.

| Model | Circuit | Qubits | CX | Depth | Size | Max controls |
|---|---|---|---|---|---|---|
| Q0 | A | 5 | 26 | 82 | 89 | 1 |
| Q0 | A·Q^1 | 5 | 100 | 270 | 304 | 1 |
| Q0 | A·Q^2 | 5 | 174 | 458 | 519 | 1 |
| Q1 | A | 12 | 313 | 518 | 543 | 1 |
| Q1 | A·Q^1 | 12 | 1503 | 2532 | 3001 | 1 |
| Q1 | A·Q^2 | 12 | 2693 | 4546 | 5459 | 1 |
| Q1lite | A | 8 | 73 | 166 | 187 | 1 |
| Q1lite | A·Q^1 | 8 | 399 | 757 | 996 | 1 |
| Q1lite | A·Q^2 | 8 | 725 | 1348 | 1805 | 1 |

These figures come from qiskit 2.5.2 with `seed_transpiler` 1, `optimization_level` 1 and basis cx, rz, ry, rx, h, x, sx. Every gate has at most 1 control, far below IonQ's 7-control limit, and every circuit is within the 24-qubit budget. The estimated IonQ request bodies (about 56 bytes per gate, every qubit measured) are 31, 169 and 306 KB for Q1 at k = 0, 1 and 2.

## Grover powers and the transpile-once rule

- The Grover operator is Q = `grover_operator(oracle, state_preparation=A)`, where the oracle is Z on the flag. This is the `grover_operator()` function; the `GroverOperator` class is deprecated since Qiskit 2.1.
- After A·Q^k the flag reads 1 with probability sin^2((2k + 1) theta), where a = sin^2 theta. For Q1 that is 0.243 at k = 0, 0.9994 at k = 1, 0.286 at k = 2 and 0.995 at k = 4.
- **Transpile-once rule:**
  - `grover.power_circuit` composes the logical A·Q^k first, including its measurements.
  - `grover.transpile_once` then transpiles it once, to the explicit basis above.
  - Transpiling A and Q separately and stitching them gives the wrong amplitudes. At k = 1 it measured P(flag) = 0.958 instead of 0.9994. The standalone Q synthesis treats qubits that are idle at its start as clean ancillas, which is false mid-circuit.
- **No backend target:** the code never calls `transpile(c, backend)`.
  - The IonQ target leaves an 11-control `mcx`, which IonQ rejects.
  - The Aer target leaves `multiplexer` instructions that crash Aer at deep powers.
  - The explicit basis works on Aer, the Built-in simulator and IonQ alike.

## Maximum-likelihood amplitude estimation

`neutron_qae/mlae.py` was written for this project; no qiskit-algorithms source is copied into it. It follows qiskit-algorithms 0.4.0's conventions, so the two give identical results on identical counts.

- **Likelihood.** For records (k_i, n_i shots, h_i hits):

  L(theta) = sum_i [h_i log sin^2((2k_i + 1) theta) + (n_i - h_i) log cos^2((2k_i + 1) theta)]

  It uses 0 log 0 = 0, so a record with no hits, or with every shot a hit, never produces NaN.
- **Maximiser.**
  - First a grid search over [1e-15, pi/2 - 1e-15], using qiskit-algorithms' grid size.
  - Then a golden-section refinement between the neighbouring grid points. The refined point is kept only if its likelihood is at least as high as the grid maximum.
- **Standard error.** The Fisher bound: se_a = |sin(2 theta)| / sqrt(sum 4 n_k (2k + 1)^2).
- **Parity with qiskit-algorithms 0.4.0 under the same minimizer.**
  - A brute-force search over our likelihood equals qiskit's `compute_mle` exactly.
  - qiskit run with our minimizer equals our estimate exactly.
  - qiskit's default minimizer (scipy `brute` with an `fmin` finish, xtol 1e-4) can stop up to 4e-5 in a short of the maximum, always at a lower likelihood. Our refinement does not.
- **Records.** They are sorted before evaluation, so the order of runs does not matter. Records marked `sampled: false` are refused (see the IonQ protocol below).

## Cost: applications of A

The honest cost of an amplitude-estimation run is the number of applications of A:

N_A = sum over records of shots (2k + 1)

One shot of A·Q^k applies A once plus k Grover steps, each holding A and A-dagger, so it costs 2k + 1. A shot of A alone (k = 0) costs 1, which is the same unit as one classical history: one sample of the transport model, measured once.

qiskit-algorithms reports `num_oracle_queries = shots x sum k` instead. That count drops A and A-dagger and treats k = 0 as free. On the schedule k = 0, 1, 2, 4 at 100 shots per power, N_A = 1,800 while `num_oracle_queries` = 700. This project uses only N_A.

## Runners

All runners share one interface, `run(ks, shots) -> list[PowerResult]`, so the estimator does not care where the counts came from.

- **`AnalyticRunner(p, rng)`:** draws Binomial(shots, sin^2((2k + 1) theta)) with no circuit, from the contract-checked p. Phase 5 uses it for the long error-vs-N_A sweeps. QAE-04 tests check that it agrees with Aer hit for hit, within statistics.
- **`BackendRunner(backend, problem)`:** runs one list job of A·Q^k circuits on an injected local backend.
  - On Qollab this is the Built-in simulator; `main.py` uses k = 0, 1, 2, 4.
  - Locally it is Aer, injected from `tests/` and `scripts/` only. Aer is never imported by code `main.py` reaches.
  - It refuses an IonQ backend.
- **`IonQRunner(backend, problem, ideal_mode)`:** sends exactly one bare A·Q^k circuit, with every qubit measured, in one `backend.run` call. It never uses a list or a Sampler, and it never retries.

No package module constructs a backend; the backend is always a parameter.

## IonQ protocol on Qollab

Qollab allows one job per Run, and its IonQ proxy accepts only one circuit per job (`ionq.circuit.v1`). An IonQ Run therefore executes exactly one A·Q^k circuit, and the IonQ estimate is assembled from several Runs.

1. Sign in, pick `IonQ Forte 1` in Select QPU and keep `mode = qae`, `model = Q1`, `shots = 1000`, `ideal_mode = set_options`.
2. Run once each with `k = 0`, then `k = 1`, then `k = 2`. Every Run prints one `IONQ_RECORD=` line (compact JSON) and ends with `IONQ RUN ACCEPTED` or `IONQ RUN FAILED: <error>`.
3. **Why k = 0 is required:**
   - A single power k >= 1 is ambiguous, because sin^2((2k + 1) theta) has 2k + 1 maxima on [0, pi/2].
   - The k = 0 record pins the branch, so the IonQ-only estimate needs a sampled k = 0 record.
   - k = 0 alone already gives a = hits/shots with N_A = shots, and the console prints that estimate.
4. **Noise models (`ideal_mode`):**
   - `set_options` calls `backend.set_options(noise_model="ideal")` before the run. qiskit-ionq then samples the counts, giving real Binomial statistics, and the record has `sampled: true`.
   - `none` keeps the Forte 1 noise model. qiskit-ionq then returns round(p x shots) counts, which are not samples. These records are kept with `sampled: false` and reported, but the estimator refuses them.
   - The `noise_model="ideal"` run keyword also gives rounded counts, so `main()` rejects `ideal_mode = kwarg`.
5. **Size ladder:** the proxy rejects request bodies above an unknown size, with the message "Circuit size is too large". Submit k = 0 (31 KB) first, then k = 1 (169 KB), then k = 2 (306 KB). If a Run is rejected, repeat that k with `model = Q1lite` (57 KB at k = 1, 103 KB at k = 2). Every record carries `body_bytes_est`, so the limit gets bracketed.
6. Save the console output verbatim to a text file and run `.venv/bin/python scripts/ingest_ionq_records.py PASTE`. The script:
   - validates every record and stores it exactly as printed, in `data/ionq_runs.json`;
   - lists failed attempts without storing them;
   - refuses records from anything other than a real `qiskit_ionq` backend;
   - prints the IonQ-only MLAE estimate.

   The Built-in run then shows that estimate to logged-out judges.

## IonQ results

Three IonQ Forte 1 runs on Qollab (2026-10-11): model Q1, `ideal_mode = set_options`, 1000 shots each, all accepted and sampled. They are stored verbatim in `data/ionq_runs.json`. The full record (run table, verbatim console lines, size ladder, timings, analysis) is in [docs/QOLLAB-RUNTIME.md](QOLLAB-RUNTIME.md), section "Phase 4 IonQ runs (2026-10-11)".

| k | CX | hits / 1000 | P(flag) measured | sin^2((2k + 1) theta) | Exact binomial tail probability | run_s |
|---|---|---|---|---|---|---|
| 0 | 313 | 267 | 0.267 | 0.2430 | P(X >= 267) = 4.3e-02 | 11.96 |
| 1 | 1,503 | 988 | 0.988 | 0.9994 | P(X <= 988) = 2.1e-12 | 22.29 |
| 2 | 2,693 | 349 | 0.349 | 0.2859 | P(X >= 349) = 8.6e-06 | 22.55 |

- **IonQ-only MLAE estimate (k = 0, 1, 2).** a_hat = 0.228671, |a_hat - T1| = 1.43e-02, Fisher se = 2.24e-03, z = -6.38, N_A = 9,000.
  - This misses the planned 4-sigma check. The check was not loosened and no record was dropped: `test_ionq_only_estimate_within_4_sigma` carries a strict xfail that matches only these three exact records.
  - The k = 0 record alone gives 0.267 (N_A = 1,000), which is +1.77 binomial sigma from T1 = 0.24300.
- **Why it misses: the k = 1 and k = 2 points are not shot noise.**
  - No single theta fits all three points: the deviance is 14.6 on 2 degrees of freedom (p = 6.7e-04).
  - IonQ returned 3, 20 and 42 shots (k = 0, 1, 2) on 12-bit outcomes that the exact statevector of the same transpiled circuit gives probability below 1e-9.
  - Locally, the same transpiled circuits reproduce sin^2((2k + 1) theta) exactly.
  - IonQ's own probability panel, as rendered by Qollab, showed the same shifts (relayed from Hippolyte's screen with the paste).
  - The deviation therefore arises in IonQ's ideal cloud simulation of the submitted circuit, or in its submission path. Rounding the rotation angles locally does not reproduce it, so the cause is open.
- **Size ladder.** Every body was accepted up to 306,656 bytes (k = 2), so Q1lite was not needed.
- **Noise-model runs.** None were run (the optional R4/R5).
- **Built-in path.** The same upload ran the full Built-in QAE in the browser: a_hat = 0.242072, se = 1.26e-03, N_A = 18,000, in 1.41 s.

## What this evidence does and does not show

- **The argument is sampling complexity only.** The MLAE error falls roughly as 1/N_A, while classical Monte Carlo falls as 1/sqrt(N) for the same unit of cost. It says nothing about neutrons being "quantum", and nothing about wall-clock time: no wall-clock or quantum-advantage claim is made.
- **The full 1/N_A curve comes from simulation, not IonQ.** It comes from the analytic and Aer runners in Phase 5, and the QAE-04 tests check that the analytic emulator matches Aer.
- **What IonQ shows.** The IonQ runs prove that the real 12-qubit circuit executes through Qollab's one-circuit IonQ path. Together, the k = 0, 1, 2 records give a three-power IonQ-only estimate with its N_A. That estimate is 6.4 sigma below T1 because IonQ's ideal simulation of the deeper Grover circuits departs from the exact circuit (see "IonQ results"), so the IonQ data are an execution proof, not an accuracy result.
- **Noise-model runs.** IonQ runs under the Forte 1 noise model are reported for honesty, as rounded probabilities. They are not used for statistics; with about 1.5k two-qubit gates at k = 1, noise is expected to wash out the amplification.
