"""LOCAL ONLY, optional: re-derives neutron_qae.nuclear_data.MICRO_14MEV from ENDF/B-VIII.0.

Never imported by neutron_qae or main.py. Run with python -I. On python.org macOS builds set
SSL_CERT_FILE=/etc/ssl/cert.pem for --download.

Usage:
    python -I scripts/derive_cross_sections.py --endf-dir DIR [--check] [--sha256-table]
    python -I scripts/derive_cross_sections.py --download DIR [--check] [--sha256-table]

--endf-dir reads the 36 isotopic files named in nuclear_data.PROVENANCE from DIR and never
touches the network. --download first fetches the missing ones of those 36 members from the
NNDC ENDF/B-VIII.0 neutrons zip (HTTPS range requests to www.nndc.bnl.gov only) into DIR.

Method (docs/PHYSICS.md "Derivation and replication"): MF3 MT1/MT2/MT16 interpolated at the
energy with each file's interpolation law; mubar_lab from MF4/MT2 with the exact CM-to-lab
transform; isotopes weighted by natural abundance, mubar weighted by sigma_el.

ENDF files are untrusted text: numbers are parsed only with float() (via fnum), never with
eval, exec or pickle. The parser functions are consolidated from the Phase 2 research
prototype (.planning/phases/02-problem-spec-kernels-contract/prototype/scripts/).
"""
import argparse
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from numpy.polynomial import legendre as L

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neutron_qae import nuclear_data as nd  # noqa: E402

ZIP_URL = "https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip"
MEMBER_DIR = "ENDF-B-VIII.0_neutrons"
REL_TOL, N2N_ABS_TOL = 1e-5, 1e-4


# ---- ENDF-6 reader (from the research prototype endf_xs_lib.py) -------------------------

def fnum(s):
    s = s.strip()
    if not s: return 0.0
    m = re.match(r"^([+-]?[0-9.]+)([+-][0-9]+)$", s)
    if m and "e" not in s.lower(): return float(m.group(1) + "e" + m.group(2))
    return float(s)


def lines_of(path):
    out = {}
    with open(path, encoding="latin-1") as fh:
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


def mf3(rec, mt, e):
    if (3, mt) not in rec: return None
    v = fields(rec[(3, mt)])
    t, _ = tab1(v, 6)
    return interp(t, e), t["c2"]


# ---- exact elastic mean lab cosine (from the research prototype mubar.py) ---------------

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


def mubar(rec, E):
    """(mubar_cm, mubar_lab, LCT, E0, E1) for elastic at E; rec from lines_of (parsed once)."""
    A = fnum(fields(rec[(1,451)][:1])[1])
    lct, ds = dists(rec)
    es = np.array([d[0] for d in ds]); k = int(np.searchsorted(es, E)) - 1
    k = min(max(k, 0), len(ds)-2)
    (e0, k0, p0), (e1, k1, p1) = ds[k], ds[k+1]
    w = (E - e0)/(e1 - e0)
    f = (1-w)*pdf(k0, p0) + w*pdf(k1, p1)
    return (*means(f, A, lct), lct, e0, e1)


# ---- HTTPS range reader (from the research prototype fetch_endf.py) ----------------------

class HttpFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url; self.pos = 0
        req = urllib.request.Request(url, method="HEAD")
        self.size = int(urllib.request.urlopen(req, timeout=60).headers["Content-Length"])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        data = urllib.request.urlopen(req, timeout=120).read()
        self.pos += len(data); return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


# ---- derivation --------------------------------------------------------------------------

def isotope_files():
    """The 36 isotopic files behind MICRO_14MEV: dicts with file, element, A, MAT, abundance."""
    out = []
    for el, rows in nd.PROVENANCE.items():
        z = nd.ATOMIC_NUMBER[el]
        for isotope, mat, _evaluation, _date in rows:
            a = int(isotope.split("-")[1])
            out.append({"file": f"n-{z:03d}_{el}_{a:03d}.endf", "element": el, "A": a, "MAT": mat,
                        "abundance": nd.ABUNDANCE[el][a]})
    return out


def download(dest):
    """Fetch only the missing ones of the 36 named members from ZIP_URL into dest."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    missing = [f["file"] for f in isotope_files() if not (dest / f["file"]).is_file()]
    if not missing:
        return
    with zipfile.ZipFile(io.BufferedReader(HttpFile(ZIP_URL), buffer_size=1 << 20)) as z:
        for name in missing:
            data = z.read(f"{MEMBER_DIR}/{name}")
            (dest / name).write_bytes(data)
            print(f"downloaded {name} ({len(data)} bytes)", file=sys.stderr)


def isotope_values(path, energy_ev):
    """sigma_t (MT1), sigma_el (MT2), sigma_n2n (MT16, 0.0 if absent), mubar_lab and sha256 of one file."""
    path = Path(path)
    rec = lines_of(path)
    n2n = mf3(rec, 16, energy_ev)
    return {
        "sigma_t": mf3(rec, 1, energy_ev)[0],
        "sigma_el": mf3(rec, 2, energy_ev)[0],
        "sigma_n2n": n2n[0] if n2n is not None else 0.0,
        "mubar_lab": float(mubar(rec, energy_ev)[1]),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def elemental(values):
    """Abundance-weighted element values from {file: isotope_values} (mubar weighted by sigma_el)."""
    out = {}
    for el in nd.PROVENANCE:
        iso = [(f["abundance"], values[f["file"]]) for f in isotope_files() if f["element"] == el]
        sigma_el = sum(a * v["sigma_el"] for a, v in iso)
        out[el] = {
            "sigma_t": sum(a * v["sigma_t"] for a, v in iso),
            "sigma_el": sigma_el,
            "mubar_lab": sum(a * v["sigma_el"] * v["mubar_lab"] for a, v in iso) / sigma_el,
            "sigma_n2n": sum(a * v["sigma_n2n"] for a, v in iso),
        }
    return out


def check(derived):
    """(max rel dev of sigma_t/sigma_el/mubar vs MICRO_14MEV, max abs dev of sigma_n2n, offenders)."""
    worst_rel, worst_abs, bad = 0.0, 0.0, []
    for el, (sigma_t, sigma_el, mu) in nd.MICRO_14MEV.items():
        d = derived[el]
        rel = max(abs(d["sigma_t"] / sigma_t - 1), abs(d["sigma_el"] / sigma_el - 1), abs(d["mubar_lab"] / mu - 1))
        dev = abs(d["sigma_n2n"] - nd.SIGMA_N2N_14MEV[el])
        print(f"{el:3s} max rel dev {rel:.2e}  n2n abs dev {dev:.2e}")
        worst_rel, worst_abs = max(worst_rel, rel), max(worst_abs, dev)
        if rel > REL_TOL or dev > N2N_ABS_TOL:
            bad.append(el)
    return worst_rel, worst_abs, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--endf-dir", metavar="DIR", help="directory holding the 36 isotopic ENDF files (no network)")
    src.add_argument("--download", metavar="DIR", help="fetch missing files from NNDC into DIR, then derive")
    ap.add_argument("--energy-ev", type=float, default=nd.ENERGY_EV)
    ap.add_argument("--check", action="store_true", help="compare with MICRO_14MEV / SIGMA_N2N_14MEV")
    ap.add_argument("--sha256-table", action="store_true", help="print one markdown row per parsed file")
    args = ap.parse_args(argv)

    directory = Path(args.download or args.endf_dir)
    if args.download:
        download(directory)
    files = isotope_files()
    for f in files:
        if not (directory / f["file"]).is_file():
            print(f"missing isotope file: {directory / f['file']}", file=sys.stderr)
            return 1
    values = {f["file"]: isotope_values(directory / f["file"], args.energy_ev) for f in files}
    derived = elemental(values)
    print(json.dumps(derived, indent=1))
    if args.sha256_table:
        for f in files:
            print(f"| {f['file']} | {f['MAT']} | {values[f['file']]['sha256']} |")
    if args.check:
        worst_rel, worst_abs, bad = check(derived)
        if bad:
            print(f"MICRO_14MEV NOT REPRODUCED for {', '.join(bad)} "
                  f"(max rel dev {worst_rel:.2e}, max n2n abs dev {worst_abs:.2e})")
            return 1
        print(f"MICRO_14MEV REPRODUCED (max rel dev {worst_rel:.2e}, max n2n abs dev {worst_abs:.2e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
