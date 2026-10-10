"""Exact elastic mean scattering cosine (CM and LAB) at energy E from MF4/MT2."""
import sys, glob, os, json
import numpy as np
from numpy.polynomial import legendre as L
sys.path.insert(0, os.path.dirname(__file__))
from endf_xs_lib import lines_of, fields, fnum, tab1

MU = np.linspace(-1, 1, 200001)

def dists(rec):
    v = fields(rec[(4, 2)])
    ltt = int(fnum(v[3])); i = 6
    lct = int(fnum(v[i+3])); i += 6
    out = []  # (E, kind, payload)
    def leg(i):
        nr, ne = int(fnum(v[i+4])), int(fnum(v[i+5])); i += 6
        i += 2*nr; i = ((i+5)//6)*6
        for _ in range(ne):
            en = fnum(v[i+1]); nl = int(fnum(v[i+4])); i += 6
            a = [fnum(v[i+k]) for k in range(nl)]; i += nl; i = ((i+5)//6)*6
            out.append((en, "leg", a))
        return i
    def tab(i):
        nr, ne = int(fnum(v[i+4])), int(fnum(v[i+5])); i += 6
        i += 2*nr; i = ((i+5)//6)*6
        for _ in range(ne):
            t, i = tab1(v, i); out.append((t["c2"], "tab", (np.array(t["x"]), np.array(t["y"]))))
        return i
    if ltt == 1: leg(i)
    elif ltt == 2: tab(i)
    elif ltt == 3: i = leg(i); tab(i)
    return lct, out

def pdf(kind, payload):
    if kind == "leg":
        c = np.array([1.0] + list(payload)); l = np.arange(len(c))
        return L.legval(MU, (2*l+1)/2*c)
    x, y = payload
    return np.interp(MU, x, y)

def means(f, A, lct):
    f = np.clip(f, 0, None); norm = np.trapezoid(f, MU)
    mc = np.trapezoid(MU*f, MU)/norm
    if lct == 1: return mc, mc
    muL = (1 + A*MU)/np.sqrt(A*A + 2*A*MU + 1)
    return mc, np.trapezoid(muL*f, MU)/norm

def mubar(path, E):
    rec = lines_of(path); A = fnum(fields(rec[(1,451)][:1])[1])
    lct, ds = dists(rec)
    es = np.array([d[0] for d in ds]); k = int(np.searchsorted(es, E)) - 1
    k = min(max(k, 0), len(ds)-2)
    (e0, k0, p0), (e1, k1, p1) = ds[k], ds[k+1]
    w = (E - e0)/(e1 - e0)
    f = (1-w)*pdf(k0, p0) + w*pdf(k1, p1)
    return (*means(f, A, lct), lct, e0, e1)

if __name__ == "__main__":
    E = float(sys.argv[2])
    res = {}
    for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.endf"))):
        mc, ml, lct, e0, e1 = mubar(p, E)
        res[os.path.basename(p)] = dict(mubar_cm=mc, mubar_lab=ml, lct=lct)
        print(f"{os.path.basename(p):20s} mu_cm={mc:.4f} mu_lab={ml:.4f} LCT={lct} bracket=({e0/1e6:.2f},{e1/1e6:.2f}) MeV")
    json.dump(res, open(sys.argv[3], "w"), indent=1)
