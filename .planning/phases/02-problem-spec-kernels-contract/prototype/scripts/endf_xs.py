"""Minimal ENDF-6 reader: MF1/MT451 header, MF3 TAB1 cross sections, MF4/MT2 Legendre/tabulated angular data."""
import math, re, sys, json, glob, os
import numpy as np

def fnum(s):
    s = s.strip()
    if not s: return 0.0
    m = re.match(r"^([+-]?[0-9.]+)([+-][0-9]+)$", s)
    if m and "e" not in s.lower(): return float(m.group(1) + "e" + m.group(2))
    return float(s)

def lines_of(path):
    out = {}
    with open(path) as fh:
        for ln in fh:
            ln = ln.rstrip("\n").ljust(80)
            try: mf = int(ln[70:72]); mt = int(ln[72:75])
            except ValueError: continue
            if mt == 0: continue
            out.setdefault((mf, mt), []).append(ln[:66])
    return out

def fields(lines):
    vals = []
    for ln in lines:
        for i in range(6): vals.append(ln[11*i:11*i+11])
    return vals

def tab1(vals, i):
    c1, c2 = fnum(vals[i]), fnum(vals[i+1]); l1, l2, nr, np_ = (int(fnum(vals[i+k])) for k in range(2, 6))
    i += 6
    nbt = [int(fnum(vals[i+2*k])) for k in range(nr)]; itp = [int(fnum(vals[i+2*k+1])) for k in range(nr)]
    i += 2*nr; i = ((i + 5)//6)*6
    xs = [fnum(vals[i+2*k]) for k in range(np_)]; ys = [fnum(vals[i+2*k+1]) for k in range(np_)]
    i += 2*np_; i = ((i + 5)//6)*6
    return dict(c1=c1, c2=c2, l1=l1, l2=l2, nbt=nbt, itp=itp, x=xs, y=ys), i

def interp(t, e):
    x, y = t["x"], t["y"]
    if e < x[0] or e > x[-1]: return 0.0
    k = int(np.searchsorted(x, e, side="right")) - 1
    k = min(max(k, 0), len(x) - 2)
    # interpolation law for interval k (1-based point index k+2)
    law = 2
    for nb, it in zip(t["nbt"], t["itp"]):
        if k + 2 <= nb: law = it; break
    x0, x1, y0, y1 = x[k], x[k+1], y[k], y[k+1]
    if x1 == x0: return y1
    if law == 1: return y0
    if law == 2: return y0 + (y1 - y0) * (e - x0) / (x1 - x0)
    if law == 3: return y0 + (y1 - y0) * math.log(e/x0) / math.log(x1/x0)
    if law == 4: return y0 * math.exp(math.log(y1/y0) * (e - x0)/(x1 - x0)) if y0 > 0 and y1 > 0 else y0 + (y1-y0)*(e-x0)/(x1-x0)
    if law == 5: return y0 * math.exp(math.log(y1/y0) * math.log(e/x0)/math.log(x1/x0)) if y0 > 0 and y1 > 0 else 0.0
    raise ValueError(law)

def header(rec):
    v = fields(rec[(1, 451)][:5])
    awr = fnum(v[1])
    text = rec[(1, 451)]
    # descriptive lines start after 4 CONT records (ENDF-6 format)
    desc = " | ".join(l.strip() for l in text[4:7])
    return awr, desc

def mf3(rec, mt, e):
    if (3, mt) not in rec: return None
    v = fields(rec[(3, mt)])
    t, _ = tab1(v, 6)
    return interp(t, e), t["c2"]

def mubar_cm(rec, e):
    """<mu> in CM (or lab if LCT=1) for elastic from MF4/MT2."""
    if (4, 2) not in rec: return None, None
    v = fields(rec[(4, 2)])
    ltt = int(fnum(v[3])); i = 6
    li, lct = int(fnum(v[i+2])), int(fnum(v[i+3])); i += 6
    def legendre_block(i):
        # TAB2 header: C1 C2 L1 L2 NR NE ; interp pairs ; then NE LIST records
        nr, ne = int(fnum(v[i+4])), int(fnum(v[i+5])); i += 6
        i += 2*nr; i = ((i+5)//6)*6
        es, a1s = [], []
        for _ in range(ne):
            en = fnum(v[i+1]); nl = int(fnum(v[i+4])); i += 6
            coeffs = [fnum(v[i+k]) for k in range(nl)]; i += nl; i = ((i+5)//6)*6
            es.append(en); a1s.append(coeffs[0] if nl else 0.0)
        return es, a1s, i
    def tab_block(i):
        nr, ne = int(fnum(v[i+4])), int(fnum(v[i+5])); i += 6
        i += 2*nr; i = ((i+5)//6)*6
        es, mus = [], []
        for _ in range(ne):
            t, i = tab1(v, i)
            mu = np.array(t["x"]); f = np.array(t["y"])
            es.append(t["c2"]); mus.append(float(np.trapezoid(mu*f, mu) / np.trapezoid(f, mu)))
        return es, mus, i
    if ltt == 1:
        es, a, i = legendre_block(i)
    elif ltt == 2:
        es, a, i = tab_block(i)
    elif ltt == 3:
        es1, a1, i = legendre_block(i)
        es2, a2, i = tab_block(i)
        es, a = es1 + es2, a1 + a2
    else:
        return None, lct
    return float(np.interp(e, es, a)), lct

def mu_lab_from_cm(mubar_c, A):
    # first-order (P1 truncated) CM distribution f(mu)=1/2(1+3 a1 mu); exact average of lab cosine numerically
    mu = np.linspace(-1, 1, 20001)
    f = 0.5 * (1 + 3 * mubar_c * mu)
    f = np.clip(f, 0, None)
    muL = (1 + A*mu) / np.sqrt(A*A + 2*A*mu + 1)
    return float(np.trapezoid(muL*f, mu) / np.trapezoid(f, mu))

E = float(sys.argv[2]) if len(sys.argv) > 2 else 14.1e6
res = {}
for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.endf"))):
    rec = lines_of(path)
    awr, desc = header(rec)
    r = {"awr": awr, "desc": desc}
    for mt in (1, 2, 3, 4, 5, 16, 17, 22, 28, 102, 103, 104, 105, 106, 107, 108, 111, 112):
        out = mf3(rec, mt, E)
        if out is not None: r[f"mt{mt}"] = out[0]
    # disappearance-type sums from partials if MT103/107 absent
    for base, lo in ((103, 600), (104, 650), (105, 700), (106, 750), (107, 800)):
        if f"mt{base}" not in r:
            s = sum(mf3(rec, mt, E)[0] for mt in range(lo, lo+50) if (3, mt) in rec)
            if s: r[f"mt{base}"] = s
    mc, lct = mubar_cm(rec, E)
    r["mubar_elastic"] = mc; r["lct"] = lct
    if mc is not None:
        r["mubar_elastic_lab"] = mu_lab_from_cm(mc, awr) if lct == 2 else mc
    res[os.path.basename(path)] = r
json.dump(res, open(sys.argv[3], "w"), indent=1)
for k, r in res.items():
    print(f"{k:22s} A={r['awr']:8.3f} tot={r.get('mt1',0):7.4f} el={r.get('mt2',0):7.4f} nonel={r.get('mt1',0)-r.get('mt2',0):7.4f} "
          f"inel={r.get('mt4',0):7.4f} n2n={r.get('mt16',0):7.4f} n3n={r.get('mt17',0):7.4f} cap={r.get('mt102',0):.5f} "
          f"np={r.get('mt103',0):.4f} na={r.get('mt107',0):.4f} mu_cm={r['mubar_elastic']} lct={r['lct']} mu_lab={r.get('mubar_elastic_lab')}")
