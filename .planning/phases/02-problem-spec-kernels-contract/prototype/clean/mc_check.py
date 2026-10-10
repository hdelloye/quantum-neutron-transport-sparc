import sys, os, math, numpy as np
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here); sys.path.insert(1, os.path.join(here, "..", "proto"))
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels
from neutron_qae.exact import transmission_within
from cmc import run
for model in ("transport_corrected", "isotropic_raw"):
    sp = sparc_first_wall(model); k = build_kernels(sp)
    T0, T1 = transmission_within(k, 0), transmission_within(k, 1)
    r = run(sp, 8_000_000, np.random.default_rng(2026))
    se1 = math.sqrt(r["T_le1"]*(1-r["T_le1"])/r["n"]); se0 = math.sqrt(T0*(1-T0)/r["n"])
    print(f"{model}: exact T0={T0:.6f} T1={T1:.6f} | MC(8e6) T_le0={r['T_le0']:.6f} ({(r['T_le0']-T0)/se0:+.2f} sd)  T_le1={r['T_le1']:.6f} ({(r['T_le1']-T1)/se1:+.2f} sd)  T_le2={r['T_le2']:.6f} T_all={r['T_all']:.6f}  cov K0={r['T_le0']/r['T_all']:.3f} K1={r['T_le1']/r['T_all']:.3f} K2={r['T_le2']/r['T_all']:.3f}")
