import sys, time, math
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels
from neutron_qae.exact import transmission_within
from mc_continuous import run_continuous
from mc_lattice import run_lattice
sp = sparc_first_wall(); k = build_kernels(sp)
T0e = float(k.first_collision[-1]); T1 = transmission_within(k, 1)
z0, z1, zl = [], [], []
for seed in range(300):
    r = run_continuous(sp, 20000, np.random.default_rng(seed))
    a, s = r.within(0); z0.append((a - T0e) / s); a, s = r.within(1); z1.append((a - T1) / s)
    l = run_lattice(k, 20000, np.random.default_rng(seed)); zl.append((l.mean - T1) / l.se)
for name, z in (("T0", z0), ("T<=1", z1), ("lattice", zl)):
    z = np.array(z); print(f"{name}: mean z {z.mean():+.3f} (se {1/math.sqrt(len(z)):.3f}) std z {z.std(ddof=1):.3f} max|z| {np.abs(z).max():.2f}")
