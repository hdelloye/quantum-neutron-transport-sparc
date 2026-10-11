import sys, time, math
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels
from neutron_qae.exact import transmission_within, exit_row_distribution_k1
from mc_continuous import run_continuous
from mc_lattice import run_lattice
sp = sparc_first_wall(); k = build_kernels(sp)
tau = float(sp.tau_x(sp.width_x)); T0e = math.exp(-tau); T1 = transmission_within(k, 1)
print("Sigma_t W,SS", sp.front.sigma_t, sp.back.sigma_t, "Sigma_s", sp.front.sigma_s, sp.back.sigma_s)
print("tau", repr(tau), "exp(-tau)", repr(T0e), "first_collision[16]", repr(float(k.first_collision[-1])), "T1", repr(T1))
print("rejection: SS/maj", sp.back.sigma_t / max(sp.front.sigma_t, sp.back.sigma_t))
for n in (10**5, 10**6, 10**7):
    t = time.perf_counter(); r = run_continuous(sp, n, np.random.default_rng(2026)); dt = time.perf_counter() - t
    T0, s0 = r.within(0); T1m, s1 = r.within(1)
    print(f"cont n={n:.0e} {dt:.2f}s iters={r.iterations} T={r.transmission:.6f}+-{r.transmission_se:.6f} A={r.absorption:.6f} "
          f"fates={r.fate_counts.tolist()} T0={T0:.6f} ({(T0-T0e)/s0:+.2f}sd) T<=1={T1m:.6f} ({(T1m-T1)/s1:+.2f}sd) orders={r.order_counts.tolist()}")
for n in (10**5, 10**6, 10**7):
    t = time.perf_counter(); r = run_lattice(k, n, np.random.default_rng(2026)); dt = time.perf_counter() - t
    print(f"latt n={n:.0e} {dt:.3f}s mean={r.mean:.6f}+-{r.se:.6f} ({(r.mean-T1)/r.se:+.2f}sd)")
