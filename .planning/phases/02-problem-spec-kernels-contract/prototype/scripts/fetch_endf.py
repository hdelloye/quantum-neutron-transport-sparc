"""Extract selected ENDF/B-VIII.0 neutron files from the NNDC zip via HTTP range requests."""
import io, re, sys, urllib.request, zipfile
URL = "https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip"
OUT = sys.argv[1]
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
f = io.BufferedReader(HttpFile(URL), buffer_size=1 << 20)
z = zipfile.ZipFile(f)
names = z.namelist()
want = re.compile(r"n-0(06_C_01[23]|15_P_031|16_S_03[2346])\.endf$")
sel = [n for n in names if want.search(n)]
print(len(names), "members;", len(sel), "selected")
for n in sel:
    data = z.read(n)
    open(f"{OUT}/{n.split('/')[-1]}", "wb").write(data)
    print(n, len(data))
