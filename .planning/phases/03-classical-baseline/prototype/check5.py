import sys, time
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np, tracemalloc
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels
from mc_continuous import run_continuous
from mc_lattice import run_lattice
sp = sparc_first_wall(); k = build_kernels(sp)
for ch in (1<<16, 1<<18, 1<<20):
    t=time.perf_counter(); run_continuous(sp, 10**7, np.random.default_rng(0), chunk=ch); dc=time.perf_counter()-t
    t=time.perf_counter(); run_lattice(k, 10**7, np.random.default_rng(0), chunk=ch); dl=time.perf_counter()-t
    tracemalloc.start(); run_continuous(sp, ch, np.random.default_rng(0), chunk=ch); pk=tracemalloc.get_traced_memory()[1]/1e6; tracemalloc.stop()
    print(f"chunk {ch}: cont 1e7 {dc:.2f}s latt 1e7 {dl:.2f}s cont peak {pk:.0f} MB")
# prefix/hits for phase 5
l, hits = run_lattice(k, 10**6, np.random.default_rng(0), return_hits=True)
cs = np.cumsum(hits); print("prefix est at 1e3,1e4,1e5,1e6:", [cs[n-1]/n for n in (10**3,10**4,10**5,10**6)])
# RMSE check 50 reps at N=1e4
T1 = 0.24300446519524305
ss = np.random.SeedSequence(2026); est=[run_lattice(k, 10**4, np.random.default_rng(s)).mean for s in ss.spawn(200)]
print("RMSE 200 reps N=1e4:", np.sqrt(np.mean((np.array(est)-T1)**2)), "theory", np.sqrt(T1*(1-T1)/1e4))
