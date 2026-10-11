import sys, time, math, tracemalloc
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from neutron_qae.problem import sparc_first_wall, ProblemSpec, Material
from neutron_qae.kernels import build_kernels
from neutron_qae.exact import transmission_within
from mc_continuous import run_continuous, BACK
from mc_lattice import run_lattice
from random_source import HashCounterSource, ScriptedSource, RandomSource
sp = sparc_first_wall(); k = build_kernels(sp); T1 = transmission_within(k, 1)
# reproducibility
a, ha = run_continuous(sp, 50000, np.random.default_rng(5), histories=True)
b, hb = run_continuous(sp, 50000, np.random.default_rng(5), histories=True)
print("repro cont:", all(np.array_equal(x, y, equal_nan=True) for x, y in zip(ha, hb)))
c, hc = run_continuous(sp, 50000, np.random.default_rng(5), histories=True, chunk=10000)
print("chunk-size changes histories:", not all(np.array_equal(x, y, equal_nan=True) for x, y in zip(ha, hc)))
l1 = run_lattice(k, 50000, np.random.default_rng(5), return_bitstrings=True); l2 = run_lattice(k, 50000, np.random.default_rng(5), return_bitstrings=True)
print("repro latt:", np.array_equal(l1.bitstrings, l2.bitstrings))
print("Generator is RandomSource:", isinstance(np.random.default_rng(1), RandomSource))
# hash source
h = HashCounterSource(); t = time.perf_counter(); r = run_continuous(sp, 200000, h); dt = time.perf_counter()-t
T1m, s1 = r.within(1); print(f"hash cont 2e5 {dt:.2f}s T<=1 z={(T1m-T1)/s1:+.2f} calls={h.calls} drawn={h.drawn}")
h = HashCounterSource(b"x"); l = run_lattice(k, 200000, h); print(f"hash latt z={(l.mean-T1)/l.se:+.2f} drawn={h.drawn}")
# scripted: lattice uncollided
s = ScriptedSource([0.99, 0.5, 0.5, 0.5]); l = run_lattice(k, 1, s, return_bitstrings=True)
print("scripted latt:", l.transmitted, l.row_counts.argmax(), int(l.bitstrings[0]), bin(int(l.bitstrings[0])), "consumed", s.pos)
s = ScriptedSource([0.95]); r, hh = run_continuous(sp, 1, s, histories=True); print("scripted cont uncollided fate", hh[0], "ncol", hh[1], "y", hh[2], "consumed", s.pos)
s = ScriptedSource([0.10, 0.01, 0.0, 0.95]); r, hh = run_continuous(sp, 1, s, histories=True); print("scripted cont scatter phi=0 then exit: fate", hh[0], "ncol", hh[1], "y", hh[2], "consumed", s.pos)
# analytic: pure absorber two-layer
pa = ProblemSpec(front=Material("A", sp.front.sigma_t, 0.0), back=Material("B", sp.back.sigma_t, 0.0))
r = run_continuous(pa, 400000, np.random.default_rng(1)); print("pure absorber T", r.transmission, "exp", math.exp(-float(pa.tau_x(10))), "z", (r.transmission-math.exp(-float(pa.tau_x(10))))/r.transmission_se, "fates", r.fate_counts)
ps = ProblemSpec(front=Material("A", sp.front.sigma_t, sp.front.sigma_t), back=Material("B", sp.back.sigma_t, sp.back.sigma_t))
r = run_continuous(ps, 200000, np.random.default_rng(1)); print("pure scatterer fates", r.fate_counts, "sum", r.fate_counts.sum(), "iters", r.iterations)
# isotropic_raw
spr = sparc_first_wall("isotropic_raw"); kr = build_kernels(spr); r = run_continuous(spr, 4*10**6, np.random.default_rng(2))
print("raw: T_all", r.transmission, "T<=1", r.within(1), "exact T1", transmission_within(kr, 1), "T0", r.within(0), kr.first_collision[-1], "iters", r.iterations)
# timing 1e5 and memory
for n in (10**5,):
    ts=[]
    for i in range(5):
        t=time.perf_counter(); run_continuous(sp, n, np.random.default_rng(i)); ts.append(time.perf_counter()-t)
    print("cont 1e5 best", min(ts))
    ts=[]
    for i in range(5):
        t=time.perf_counter(); run_lattice(k, n, np.random.default_rng(i)); ts.append(time.perf_counter()-t)
    print("latt 1e5 best", min(ts))
tracemalloc.start(); run_continuous(sp, 1<<20, np.random.default_rng(0)); print("cont peak MB per 2^20 chunk", tracemalloc.get_traced_memory()[1]/1e6); tracemalloc.stop()
tracemalloc.start(); run_lattice(k, 1<<20, np.random.default_rng(0)); print("latt peak MB per 2^20 chunk", tracemalloc.get_traced_memory()[1]/1e6); tracemalloc.stop()
