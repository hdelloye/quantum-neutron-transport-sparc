"""LOCAL ONLY: K = 1 truncation bias per wall and model (PD-28) -> data/truncation_bias.json + PNG.

    scripts/sweep_truncation.py --profile quick --seed 2026   # 1,000,000 histories per case
    scripts/sweep_truncation.py --seed 2026                   # full profile, 20,000,000 per case

For each case (transport_corrected at 6, 10, 15, 20, 30 cm, then isotropic_raw at 10 cm) the
exact lattice T0 and T1 are compared with the continuous delta-tracking transmission: within(0)
and within(1) check T0 and T1; the full transmission (all collision orders) minus T1 is the
truncation bias of the K = 1 estimand that both the lattice MC and the circuit compute.
"""
from __future__ import annotations

import os
import sys
import time

import matplotlib

matplotlib.use("Agg")

import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import sweep_common

from neutron_qae.exact import transmission_within
from neutron_qae.kernels import build_kernels
from neutron_qae.mc_continuous import run_continuous
from neutron_qae.problem import sparc_first_wall

SCRIPT = "scripts/sweep_truncation.py"
PROFILES = {"quick": {"histories": 1_000_000}, "full": {"histories": 20_000_000}}
CASES = (("transport_corrected", 6.0), ("transport_corrected", 10.0), ("transport_corrected", 15.0),
         ("transport_corrected", 20.0), ("transport_corrected", 30.0), ("isotropic_raw", 10.0))
NOTES = [
    ("within(0) and within(1) are checked against T0 and T1; the full transmission includes all collision "
     "orders, so T_full - T1 is the truncation bias of the K = 1 estimand that both the lattice MC and the "
     "circuit compute"),
    ("under the transport-corrected model K = 1 covers about 99.7% of the 10 cm transmission; isotropic_raw "
     "is shown only to disclose model dependence"),
    "one-group physics: the remaining model error against ENDF angular distributions is a separate limitation",
    ("bias_se = T_full_se (T1 is exact); coverage = T1 / T_full; thicker walls keep 2.0 cm W and add steel "
     "with the 10 cm lateral extent unchanged"),
    "sampling complexity only: this table quantifies an approximation and makes no speedup claim",
]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = sweep_common.base_parser(__doc__.splitlines()[0])
    args = ap.parse_args(argv)
    os.chdir(sweep_common.ROOT)
    n = PROFILES[args.profile]["histories"]
    timings = {}
    t_all = time.perf_counter()
    out = []
    for (model, width), child in zip(CASES, np.random.SeedSequence(args.seed).spawn(len(CASES)), strict=True):
        spec = sparc_first_wall(model, width_x=width)
        k = build_kernels(spec)
        t0, t1 = transmission_within(k, 0), transmission_within(k, 1)
        t = time.perf_counter()
        res = run_continuous(spec, n, child)
        timings[f"{model}_{width:g}cm"] = time.perf_counter() - t
        w0, s0 = res.within(0)
        w1, s1 = res.within(1)
        t_full, se = float(res.transmission), float(res.transmission_se)
        bias = t_full - t1
        out.append({
            "model": model, "width_cm": float(width), "T0": float(t0), "T1": float(t1),
            "T_full": t_full, "T_full_se": se, "within0": w0, "within0_se": s0, "within1": w1, "within1_se": s1,
            "bias": bias, "bias_se": se, "bias_z": bias / se, "coverage": t1 / t_full,
            "order_fractions": [float(x) for x in res.order_fractions],
        })
    timings["total"] = time.perf_counter() - t_all
    parameters = {
        "histories_per_case": n,
        "cases": [{"model": m, "width_cm": float(w)} for m, w in CASES],
        "engine": "mc_continuous.run_continuous (Woodcock delta tracking, all collision orders, max_order 8)",
        "reference": "exact.transmission_within(build_kernels(spec), K) for K = 0, 1",
        "seeding": "children = SeedSequence(seed).spawn(6) in case order; run_continuous(spec, n, children[i])",
    }
    doc = {
        "schema": "neutron_qae.artifact",
        "schema_version": 1,
        "kind": "truncation_bias",
        "profile": args.profile,
        "provenance": sweep_common.provenance(args.seed, SCRIPT, argv, timings),
        "parameters": parameters,
        "results": {"cases": out},
        "notes": list(NOTES),
    }
    sweep_common.finish(doc, "truncation_bias", args.out_dir, args.dpi)
    tc = [c for c in out if c["model"] == "transport_corrected"]
    c10 = next(c for c in tc if c["width_cm"] == 10.0)
    iso = next(c for c in out if c["model"] == "isotropic_raw")
    print(f"SWEEP truncation_bias profile={args.profile} seed={args.seed} coverage_10cm={c10['coverage']:.4f} "
          f"min_coverage={min(c['coverage'] for c in tc):.4f} iso_coverage={iso['coverage']:.4f} "
          f"total_s={timings['total']:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
