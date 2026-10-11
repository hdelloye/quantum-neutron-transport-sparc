import sys
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels, BACK, FRONT, LATERAL, COLLIDE
from mc_continuous import run_continuous
sp = sparc_first_wall(); k = build_kernels(sp); N = 4*10**6
r, (fate, ncol, yex, fcx) = run_continuous(sp, N, np.random.default_rng(99), histories=True)
col = np.where(np.isnan(fcx), sp.nx, np.minimum(np.floor(np.nan_to_num(fcx) / sp.dx).astype(int), sp.nx - 1))
c = np.bincount(col, minlength=sp.nx + 1); e = N * k.first_collision
print("first-collision column chi2 (17 bins):", round(float(np.sum((c - e) ** 2 / e)), 1))
w = k.first_collision[:sp.nx] * k.scatter_ratio
for o, name, code in ((BACK, "back", 0), (FRONT, "front", 1), (LATERAL, "lateral", 2)):
    ex = float(np.sum(w * k.flight[:, :, o].mean(axis=1)))
    mc = np.count_nonzero((fate == code) & (ncol == 1)) / N; se = np.sqrt(mc * (1 - mc) / N)
    print(f"exactly-1-collision {name}: kernels {ex:.6e} MC {mc:.6e} z {(mc - ex) / se:+.2f}")
ex = float(np.sum(w * k.flight[:, :, COLLIDE].mean(axis=1))); mc = np.count_nonzero(ncol >= 2) / N; se = np.sqrt(mc*(1-mc)/N)
print(f"P(>=2 real collisions): kernels {ex:.6e} MC {mc:.6e} z {(mc-ex)/se:+.2f}")
ex = float(np.sum(k.first_collision[:sp.nx] * (1 - k.scatter_ratio))); mc = np.count_nonzero((fate == 3) & (ncol == 1)) / N; se = np.sqrt(mc*(1-mc)/N)
print(f"absorbed at 1st collision: kernels {ex:.6e} MC {mc:.6e} z {(mc-ex)/se:+.2f}")
