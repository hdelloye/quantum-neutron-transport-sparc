import json, sys
xs = json.load(open(sys.argv[1])); mb = json.load(open(sys.argv[2]))
NA = 6.02214076e23
ab = {  # NIST isotopic compositions (mole fraction)
 "C": {12: .9893, 13: .0107}, "Si": {28: .92223, 29: .04685, 30: .03092}, "P": {31: 1.0},
 "S": {32: .9499, 33: .0075, 34: .0425, 36: .0001}, "Cr": {50: .04345, 52: .83789, 53: .09501, 54: .02365},
 "Mn": {55: 1.0}, "Fe": {54: .05845, 56: .91754, 57: .02119, 58: .00282},
 "Ni": {58: .68077, 60: .26223, 61: .011399, 62: .036346, 64: .009255},
 "Mo": {92: .1453, 94: .0915, 95: .1584, 96: .1667, 97: .0960, 98: .2439, 100: .0982},
 "W": {180: .0012, 182: .2650, 183: .1431, 184: .3064, 186: .2843}}
aw = {"C": 12.011, "Si": 28.085, "P": 30.973761998, "S": 32.06, "Cr": 51.9961, "Mn": 54.938044,
      "Fe": 55.845, "Ni": 58.6934, "Mo": 95.95, "W": 183.84}
Z = {"C": 6, "Si": 14, "P": 15, "S": 16, "Cr": 24, "Mn": 25, "Fe": 26, "Ni": 28, "Mo": 42, "W": 74}
mats = {
 "WHA_97W2Ni1Fe": (18.5, {"W": .97, "Ni": .02, "Fe": .01}),
 "SS316_PNNL": (8.00, {"C": .0008, "Mn": .02, "P": .00045, "S": .0003, "Si": .01, "Cr": .17, "Ni": .12, "Mo": .025, "Fe": .65345}),
}
def fname(el, A): return f"n-{Z[el]:03d}_{el}_{A:03d}.endf"
out = {}
for m, (rho, wf) in mats.items():
    tot = {k: 0.0 for k in ("t", "el", "nonel", "inel", "n2n", "n3n", "cap", "disap", "tr")}
    Ns = {}
    for el, w in wf.items():
        N_el = rho * w * NA / aw[el] * 1e-24   # atoms / (barn cm)
        Ns[el] = N_el
        for A, f in ab[el].items():
            r = xs[fname(el, A)]; mu = mb[fname(el, A)]["mubar_lab"]
            N = N_el * f
            t, e = r["mt1"], r["mt2"]
            tot["t"] += N*t; tot["el"] += N*e; tot["nonel"] += N*(t-e); tot["inel"] += N*r.get("mt4", 0)
            tot["n2n"] += N*r.get("mt16", 0); tot["n3n"] += N*r.get("mt17", 0); tot["cap"] += N*r.get("mt102", 0)
            tot["disap"] += N*sum(r.get(f"mt{k}", 0) for k in (102, 103, 104, 105, 106, 107, 108, 111, 112))
            tot["tr"] += N*(t - mu*e)
    out[m] = dict(rho=rho, N=Ns, Ntot=sum(Ns.values()), **{f"Sigma_{k}": v for k, v in tot.items()})
    o = out[m]
    print(f"\n{m}: rho={rho}  N_total={o['Ntot']:.5e} atoms/b-cm  N={ {k: round(v,6) for k,v in Ns.items()} }")
    for k in ("t", "el", "nonel", "inel", "n2n", "n3n", "cap", "disap", "tr"):
        print(f"  Sigma_{k:6s} = {o['Sigma_'+k]:.5f} /cm")
    print(f"  mfp_total = {1/o['Sigma_t']:.3f} cm ; el/t = {o['Sigma_el']/o['Sigma_t']:.4f} ; mubar_eff = {(o['Sigma_t']-o['Sigma_tr'])/o['Sigma_el']:.4f}")
    print(f"  transport-corrected: Sigma_tr = {o['Sigma_tr']:.5f}, Sigma_s,tr=(1-mu)Sigma_el = {o['Sigma_el']-(o['Sigma_t']-o['Sigma_tr']):.5f}, c_tr = {(o['Sigma_el']-(o['Sigma_t']-o['Sigma_tr']))/o['Sigma_tr']:.4f}, mfp_tr = {1/o['Sigma_tr']:.3f}")
json.dump(out, open(sys.argv[3], "w"), indent=1)
W, S = out["WHA_97W2Ni1Fe"], out["SS316_PNNL"]
print("\nOptical depths (true total): W 2cm =", round(2*W["Sigma_t"], 4), " SS 8cm =", round(8*S["Sigma_t"], 4), " total =", round(2*W["Sigma_t"]+8*S["Sigma_t"], 4))
import math
print("uncollided T = exp(-tau) =", math.exp(-(2*W["Sigma_t"]+8*S["Sigma_t"])))
print("Optical depths (transport corr): W", round(2*W["Sigma_tr"],4), "SS", round(8*S["Sigma_tr"],4), "unc_tr =", math.exp(-(2*W["Sigma_tr"]+8*S["Sigma_tr"])))
