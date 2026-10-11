import sys, math, time
sys.path.insert(0, "/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase4/scripts")
import numpy as np
from mlae_proto import mle_theta, n_a
T1 = 0.24300446519524305; th0 = math.asin(math.sqrt(T1))
rng = np.random.default_rng(2026)
def run_analytic(ks, shots):
    return [int(rng.binomial(s, math.sin((2*k+1)*th0)**2)) for k, s in zip(ks, shots)]
def study(schedule_fn, label, Ms, shots_each=100, R=200):
    xs, ys = [], []
    for M in Ms:
        ks = schedule_fn(M); shots = [shots_each]*len(ks)
        t = time.perf_counter()
        est = np.array([math.sin(mle_theta(ks, run_analytic(ks, shots), shots))**2 for _ in range(R)])
        rmse = float(np.sqrt(np.mean((est - T1)**2))); NA = n_a(ks, shots)
        xs.append(NA); ys.append(rmse)
        print(f"{label} M={M} kmax={ks[-1]:4d} N_A={NA:8d} RMSE={rmse:.3e} classical={math.sqrt(T1*(1-T1)/NA):.3e} ratio={math.sqrt(T1*(1-T1)/NA)/rmse:.2f} ({time.perf_counter()-t:.1f}s)")
    sl = np.polyfit(np.log(xs), np.log(ys), 1)[0]; print(f"{label} fitted slope {sl:.3f}")
study(lambda M: [0] + [2**j for j in range(M-1)], "EXP", range(1, 10))
study(lambda M: list(range(M)), "LIN", [1,2,4,8,16,32])
