# Results (Phase 5)

This page reports the Phase 5 scaling study. It compares two estimators of the same quantity: the matched discrete lattice Monte Carlo (the classical baseline) and maximum-likelihood amplitude estimation (MLAE) on the Q1 circuit. Both estimate the K = 1 lattice transmission T1 of the 10 cm SPARC first-wall slab, the probability that a 14 MeV neutron leaves through the back face after at most one collision. The exact lattice answer T1 = 0.24300446519524305 is the truth every error is measured against. Cost is counted in the unit each method actually spends: histories for the classical Monte Carlo, applications of the state preparation A for MLAE. The quantum numbers come from an ideal analytic runner (exact angle, binomial shot draws) and from Aer simulation of the transpiled circuits. This is a comparison of sampling complexity only: it measures how error falls with cost on an ideal simulator, and it is not a wall-clock comparison.

Every number in the tables below is the verbatim output of `neutron_qae.artifacts.format_markdown` (and `headline_sentence`) on the committed JSON under `data/`; `tests/test_results_doc.py` fails if this page and the data drift apart.

## Headline: RMSE versus cost

![RMSE versus cost](../data/fig_scaling_rmse.png)

- **Cost.** Classical: the number of histories N. MLAE: N_A = sum over the Grover powers k of shots x (2k + 1), the number of applications of A. One application of A and one classical history are the same unit of work in this comparison: one sampled neutron path.
- **RMSE.** For each cost, 100 independent repetitions estimate T1; RMSE = sqrt(mean((estimate - T1)^2)). The shaded band is the 16th to 84th percentile of |estimate - T1|.
- **Fits.** Ordinary least squares of log10 RMSE on log10 cost. The classical fit uses all points; the MLAE fits start at M = 2 (at least one Grover power). Monte Carlo predicts a slope of -0.5; ideal amplitude estimation predicts -1.

Fitted slopes: -0.50 +- 0.01 (classical lattice MC, 13 points), -1.02 +- 0.03 (MLAE, analytic runner, M = 2..11), -1.03 +- 0.05 (MLAE, Aer circuit simulation, M = 2..9).

| Series | Cost unit | Points fitted | Cost range fitted | Fitted slope | Slope SE |
|---|---|---|---|---|---|
| Classical lattice MC | histories | 13 | 100 to 1,000,000 | -0.498 | 0.005 |
| MLAE, analytic runner | applications of A | 10 | 1,200 to 617,100 | -1.015 | 0.029 |
| MLAE, Aer circuit simulation | applications of A | 8 | 1,200 to 155,700 | -1.031 | 0.048 |

IonQ Forte 1 marker (execution proof, not in any fit): N_A = 9,000, |a_hat - T1| = 1.43e-02, z = -6.38

Repetitions per point: 100; seed 2026; 300 shots per Grover power; exact T1 = 0.24300446519524305.

Reading notes:

- **The band.** The 16-84 percentile band of |error| shows the spread of single runs, not only their RMSE.
- **The M = 3 to 4 plateau.** The MLAE curve flattens between M = 3 and M = 4. With T1 = 0.243, theta = asin(sqrt(T1)) is about 0.515 rad, so 3 theta (k = 1) and 9 theta (k = 4) both sit near odd multiples of pi/2. There the flag probability is close to 1 and barely changes with theta, so 300 shots at k = 1 and k = 4 carry little information and adding k = 4 at M = 4 hardly lowers the error. The curve recovers once k = 8 enters at M = 5.
- **The Aer cross-check.** The Aer series simulates the transpiled Q1 circuits shot by shot. Its RMSE stays within about 0.8 to 1.2 times the analytic runner's at every M, and its slope agrees within one standard error, so the analytic runner is a faithful stand-in for the circuits.
- **The IonQ marker.** The X marker is the |error| of one IonQ Forte 1 estimate (k = 0, 1, 2, 1000 shots each, ideal noise model, N_A = 9,000). It is an execution proof: the real circuits run on IonQ's service through Qollab. The estimate is 6.4 sigma off T1 and the cause is open (the k = 1 and k = 2 points depart from the exact circuit far beyond shot noise). It is not an RMSE, and it is not in any fit.

## Exit-position histograms (circuit validation, not speedup evidence)

![Exit-position histograms](../data/fig_exit_histograms.png)

What was sampled: the back-face exit row (16 rows of the 10 cm wall, plus a 17th category for "no back-face exit") of 1,000,000 classical lattice histories and of 1,000,000 shots of the Q1 state preparation A run directly (k = 0, no Grover power) on Aer. The two sample sizes are matched. Both samples go through the same row sampler (`mc_lattice.sample_exit_rows`): the lattice engine's 11-bit strings and the circuit's measured bit strings are mapped to rows by one function, so any disagreement comes from the circuit, not from bookkeeping. Agreement is judged by chi-square sums over the 17 categories against the bound dof + 5 sqrt(2 dof); per-row z-scores are not used.

| Comparison | Chi-square | dof | Bound (dof + 5 sqrt(2 dof)) |
|---|---|---|---|
| Classical vs quantum | 16.46 | 16 | 44.28 |
| Classical vs exact | 17.01 | 16 | 44.28 |
| Quantum vs exact | 13.14 | 16 | 44.28 |

Samples: 1,000,000 each (matched); zero-amplitude strings: 0; flag mismatches: 0. Label: circuit validation, not speedup evidence.

Why this is not speedup evidence: sampling A directly is ordinary Monte Carlo on a quantum computer. Its histogram converges as 1/sqrt(N), exactly like the classical one. The figure shows that the circuit encodes the same physics as the classical engine, row by row; any gain in sampling complexity comes only from amplitude estimation (the Headline section), not from this figure.

## Truncation bias of the K = 1 estimand

![Truncation bias](../data/fig_truncation_bias.png)

Both the lattice Monte Carlo and the circuit compute T1, the transmission with at most one collision (K = 1). The continuous Woodcock delta-tracking Monte Carlo follows every collision order, so T_full - T1 is the bias of that truncation. Each case uses 2e7 continuous histories; T0 and T1 are exact.

| Model | Wall (cm) | T0 (exact) | T1 (exact) | T_full (continuous) | Bias T_full - T1 | Bias / SE | K = 1 coverage |
|---|---|---|---|---|---|---|---|
| transport_corrected | 6 | 0.40634 | 0.41939 | 0.41987 +- 0.00011 | 4.80e-04 | 4.4 | 99.89% |
| transport_corrected | 10 | 0.23257 | 0.24300 | 0.24377 +- 0.00010 | 7.63e-04 | 7.9 | 99.69% |
| transport_corrected | 15 | 0.11578 | 0.12224 | 0.12277 +- 0.00007 | 5.32e-04 | 7.3 | 99.57% |
| transport_corrected | 20 | 0.05764 | 0.06131 | 0.06161 +- 0.00005 | 3.04e-04 | 5.6 | 99.51% |
| transport_corrected | 30 | 0.01428 | 0.01536 | 0.01553 +- 0.00003 | 1.69e-04 | 6.1 | 98.91% |
| isotropic_raw | 10 | 0.08675 | 0.11006 | 0.12247 +- 0.00007 | 1.24e-02 | 169.2 | 89.87% |

- Under the transport-corrected one-group model, K = 1 covers about 99.7% of the 10 cm transmission (99.69%). The coverage falls slowly with thickness, to about 98.9% at 30 cm, as collisions beyond the first carry more of the transmission through thicker walls.
- The bias is small in absolute terms but statistically resolved (several standard errors at every wall): the circuit estimates a slightly truncated quantity, and this table states by how much.
- The isotropic_raw row (about 89.9% coverage at 10 cm) is a model-dependence disclosure only; the circuit does not use that model.
- One-group physics is a separate limit: the remaining model error against full ENDF angular and energy distributions is not measured here.

## Wall-thickness rare-event study

![Wall-thickness study](../data/fig_thickness_ratio.png)

The same matched comparison is repeated on five walls (6, 10, 15, 20 and 30 cm). For each wall, the cost each method needs to reach 1% relative RMSE (RMSE = 0.01 T1) is read off its measured RMSE-versus-cost curve by log-log interpolation between measured points, never by extrapolation. The ratio is classical cost divided by MLAE cost.

| Wall (cm) | T1 (exact) | Classical N at 1% rel. RMSE | MLAE N_A at 1% rel. RMSE | Ratio | Ratio at 1e-3 abs. RMSE |
|---|---|---|---|---|---|
| 6 | 0.41939 | 11,384 | 5,709 | 1.99 | 18.10 |
| 10 | 0.24300 | 30,457 | 7,135 | 4.27 | 13.96 |
| 15 | 0.12224 | 67,051 | 8,634 | 7.77 | 10.07 |
| 20 | 0.061310 | 173,706 | 11,176 | 15.54 | 9.57 |
| 30 | 0.015357 | 594,814 | 23,022 | 25.84 | 5.04 |

- **A relative-error statement.** At a fixed relative RMSE eps, classical Monte Carlo needs about (1 - T) / (T eps^2) histories, while MLAE needs about 1 / (eps sqrt(T)) applications of A. As the transmission T falls, the classical cost grows faster, so the ratio grows from 1.99 at 6 cm to 25.84 at 30 cm.
- **The absolute-target ratio shrinks.** At a fixed absolute RMSE of 1e-3 the ordering reverses: the ratio falls from 18.10 at 6 cm to 5.04 at 30 cm, because a rarer event has a smaller variance in absolute terms. Both columns come from the same curves; which one matters depends on whether the question is asked in relative or absolute accuracy.
- **Interpolation, never extrapolation.** Every cost in the table lies between two measured points of its curve.
- **A parameter sweep, not a design study.** Thicker walls keep the 2 cm tungsten armor and add steel, with the 10 cm lateral extent unchanged. They make transmission rarer; they are not SPARC design variants.

## Reproduce

Every artifact comes from one local script run with seed 2026 from a clean, committed tree (the JSON records the commit, the command line, library versions and timings). Measured run times on the development Mac (Apple Silicon, Python 3.14):

```bash
.venv/bin/python scripts/sweep_scaling.py --seed 2026      # data/scaling_rmse.json, about 71 s (analytic MLAE 45 s, Aer 20 s)
.venv/bin/python scripts/sweep_histograms.py --seed 2026   # data/exit_histograms.json, about 1.3 s
.venv/bin/python scripts/sweep_truncation.py --seed 2026   # data/truncation_bias.json, about 11 s
.venv/bin/python scripts/sweep_thickness.py --seed 2026    # data/thickness_study.json, about 75 s
.venv/bin/python scripts/render_figures.py                 # re-render all four PNGs from the JSON
.venv/bin/python scripts/render_figures.py --check         # compare fresh renders with the committed PNGs
```

The figures re-render from the JSON under `data/` without rerunning any sweep, and the tables on this page are regenerated from the same JSON by `neutron_qae.artifacts.format_markdown`. For a seconds-long smoke run add `--profile quick --out-dir <scratch directory>`; quick output must never overwrite the committed full-profile files.

## Limits of this evidence

- **Ideal simulation only.** The quantum curves come from an ideal analytic runner and from Aer statevector simulation. No noise model and no hardware run enters any fit.
- **Sampling complexity, not wall-clock time.** The claim is about error against the number of applications of A versus histories. There is no wall-clock comparison and not a quantum-advantage claim: a lattice history costs well under a microsecond here (1e8 histories in about 5.5 s), while one application of A on hardware costs a full circuit execution.
- **IonQ.** The IonQ Forte 1 runs are an execution proof: the real circuits ran on IonQ's service through Qollab. Their three-power estimate is 6.4 sigma off T1, the cause is open, and the result is not in any fit.
- **Physics model.** One-group, transport-corrected cross sections at 14.1 MeV. The model error against full energy-dependent transport is a separate limit, not measured here.
- **K = 1 truncation.** Both methods estimate the at-most-one-collision transmission T1; the Truncation bias section gives its coverage (about 99.7% at 10 cm).
- **Circuit size.** Q1 is a 12-qubit circuit. The deep Grover powers behind the scaling curve (up to k = 512 for the analytic runner and k = 128 on Aer) exist only in simulation; the hardware-scale runs reach k = 2.
