"""Prototype vendored MLAE (numpy + optional scipy) and comparison vs qiskit-algorithms 0.4.0."""
import math, time
import numpy as np

EPS = 1e-15

def n_evals(ks):
    return max(10000, int(np.pi / 2 * 1000 * 2 * max(ks)))

def loglik(theta, ks, hits, shots):
    theta = np.asarray(theta, dtype=float)[..., None]
    ang = (2 * np.asarray(ks) + 1) * theta
    h = np.asarray(hits, float); n = np.asarray(shots, float)
    with np.errstate(divide="ignore"):
        return np.sum(h * np.log(np.sin(ang) ** 2) + (n - h) * np.log(np.cos(ang) ** 2), axis=-1)

def mle_theta(ks, hits, shots, refine=True):
    grid = np.linspace(EPS, np.pi / 2 - EPS, n_evals(ks))
    ll = loglik(grid, ks, hits, shots)
    i = int(np.argmax(ll))
    th = grid[i]
    if refine:
        lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
        # golden-section search on [lo, hi], numpy only
        g = (math.sqrt(5) - 1) / 2
        a, b = lo, hi
        c, d = b - g * (b - a), a + g * (b - a)
        fc, fd = loglik(c, ks, hits, shots), loglik(d, ks, hits, shots)
        for _ in range(200):
            if b - a < 1e-15: break
            if fc > fd: b, d, fd = d, c, fc; c = b - g * (b - a); fc = loglik(c, ks, hits, shots)
            else: a, c, fc = c, d, fd; d = a + g * (b - a); fd = loglik(d, ks, hits, shots)
        cand = (a + b) / 2
        if loglik(cand, ks, hits, shots) >= ll[i]: th = cand
    return float(th)

def n_a(ks, shots):
    return int(sum(int(s) * (2 * int(k) + 1) for k, s in zip(ks, shots)))

if __name__ == "__main__":
    from scipy.optimize import brute
    from qiskit import QuantumCircuit
    from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation, EstimationProblem
    T1 = 0.24300446519524305; th0 = math.asin(math.sqrt(T1))
    rng = np.random.default_rng(1)
    A = QuantumCircuit(1); A.ry(2*th0, 0)
    prob = EstimationProblem(A, objective_qubits=[0])
    worst_default = worst_same = 0
    for M in range(1, 9):
        ks = [0] + [2**j for j in range(M - 1)]
        for shots_each in (10, 100, 1000):
            shots = [shots_each]*len(ks)
            hits = [int(rng.binomial(s, math.sin((2*k+1)*th0)**2)) for k, s in zip(ks, shots)]
            counts = [{"1": h, "0": s - h} for h, s in zip(hits, shots)]
            ql = MaximumLikelihoodAmplitudeEstimation(ks)
            tq = ql.compute_mle(counts, prob)
            tv = mle_theta(ks, hits, shots)
            tg = mle_theta(ks, hits, shots, refine=False)
            # same minimizer as qiskit, our loglik
            tb = brute(lambda t: -loglik(np.atleast_1d(t)[0], ks, hits, shots), [[EPS, np.pi/2-EPS]], Ns=n_evals(ks))[0]
            worst_default = max(worst_default, abs(math.sin(tv)**2 - math.sin(tq)**2))
            worst_same = max(worst_same, abs(tb - tq))
            print(f"M={M} ks={ks[-1]:3d} shots={shots_each:4d} N_A={n_a(ks,shots):7d} a_qiskit={math.sin(tq)**2:.10f} a_vendored={math.sin(tv)**2:.10f} d_a={math.sin(tv)**2-math.sin(tq)**2:+.2e} grid-only d_a={math.sin(tg)**2-math.sin(tq)**2:+.2e} same-minimizer dθ={tb-tq:+.1e} LL(v)-LL(q)={loglik(tv,ks,hits,shots)-loglik(tq,ks,hits,shots):+.2e}")
    print("worst |Δa| default:", worst_default, " worst |Δθ| same minimizer:", worst_same)
