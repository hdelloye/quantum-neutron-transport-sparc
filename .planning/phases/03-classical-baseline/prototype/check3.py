import sys, time, math
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels
from neutron_qae.exact import transmission_within, exit_row_distribution_k1, bitstring_probabilities_k1
from mc_continuous import run_continuous
from mc_lattice import run_lattice
sp = sparc_first_wall(); k = build_kernels(sp)
T1 = transmission_within(k, 1); ex = exit_row_distribution_k1(k)
N = 10**8
t = time.perf_counter(); r = run_continuous(sp, N, np.random.default_rng(11)); print("cont 1e8", round(time.perf_counter()-t,1), "s")
T1m, s1 = r.within(1); print(f"T<=1 {T1m:.7f}+-{s1:.7f} vs {T1:.7f} z={(T1m-T1)/s1:+.2f}; T_all {r.transmission:.7f}+-{r.transmission_se:.7f}; T_all-T1={r.transmission-T1:.6f} ({(r.transmission-T1)/r.transmission_se:.1f} sd); coverage {T1/r.transmission:.5f}")
p = r.row_counts_le1 / N; se = np.sqrt(p*(1-p)/N)
print("row  exact_k1      cont<=1      z")
for i in range(sp.ny): print(i, f"{ex[i]:.6e} {p[i]:.6e} {(p[i]-ex[i])/max(se[i],1e-300):+.1f}")
chi = np.sum((r.row_counts_le1 - N*ex)**2 / (N*ex)); print("chi2 cont<=1 rows vs exact (16 bins):", round(chi,1))
t = time.perf_counter(); l = run_lattice(k, N, np.random.default_rng(12)); print("latt 1e8", round(time.perf_counter()-t,1), "s", f"mean {l.mean:.7f} z={(l.mean-T1)/l.se:+.2f}")
chi = np.sum((l.row_counts - N*ex)**2 / (N*ex)); print("chi2 lattice rows vs exact:", round(chi,1))
# bitstring check
l2 = run_lattice(k, 4*10**6, np.random.default_rng(3), return_bitstrings=True)
P = np.zeros(2048)
for s_, p_, _ in bitstring_probabilities_k1(k): P[s_] = p_
c = np.bincount(l2.bitstrings, minlength=2048); m = P > 0
print("bitstrings outside support:", int(c[~m].sum()), "chi2", round(float(np.sum((c[m]-4e6*P[m])**2/(4e6*P[m]))),1), "dof", int(m.sum())-1)
