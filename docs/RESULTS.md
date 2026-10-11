# Results (Phase 5)

This page reports the Phase 5 scaling study. It compares two estimators of the same quantity: the matched discrete lattice Monte Carlo (the classical baseline) and maximum-likelihood amplitude estimation (MLAE) on the Q1 circuit. Both estimate the K = 1 lattice transmission T1 of the 10 cm SPARC first-wall slab, the probability that a 14 MeV neutron leaves through the back face after at most one collision. The exact lattice answer T1 = 0.24300446519524305 is the truth every error is measured against. Cost is counted in the unit each method actually spends: histories for the classical Monte Carlo, applications of the state preparation A for MLAE. The quantum numbers come from an ideal analytic runner (exact angle, binomial shot draws) and from Aer simulation of the transpiled circuits. This is a sampling-complexity comparison only: it measures how error falls with cost on an ideal simulator, and it is not a wall-clock comparison.

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
