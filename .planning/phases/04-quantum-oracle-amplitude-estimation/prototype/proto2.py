import sys, time, math
sys.path.insert(0, "/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase4/scripts")
from proto1 import *  # noqa
from qiskit_aer import AerSimulator
theta = math.asin(math.sqrt(T1))
oracle = QuantumCircuit(12); oracle.z(11)
G = grover_operator(oracle, state_preparation=q1)
print("G global phase", G.global_phase, "G ops", G.count_ops())
print("G decomposed ops", G.decompose().count_ops())
def qk(k):
    c = q1.copy()
    for _ in range(k): c.compose(G, inplace=True)
    return c
maxerr=0; t=time.perf_counter()
for k in [0,1,2,3,4,8,16,32,64]:
    t0=time.perf_counter()
    tq = transpile(qk(k), basis_gates=BASIS, optimization_level=1, seed_transpiler=1)
    t1_=time.perf_counter()
    p = float(Statevector(tq).probabilities([11])[1])
    t2=time.perf_counter()
    exp_ = math.sin((2*k+1)*theta)**2
    maxerr=max(maxerr,abs(p-exp_))
    print(f"k={k:3d} cx={tq.count_ops().get('cx',0):6d} p={p:.15f} exp={exp_:.15f} diff={p-exp_:.2e} transpile={t1_-t0:.2f}s sv={t2-t1_:.2f}s")
print("max err", maxerr, "total", time.perf_counter()-t)
# Without transpile: Statevector of logical circuit directly
t0=time.perf_counter(); p=float(Statevector(qk(64)).probabilities([11])[1]); print("logical k=64 untranspiled sv diff", p-math.sin(129*theta)**2, time.perf_counter()-t0,"s")
# Aer statevector of A and Q^kA
aer = AerSimulator(method="statevector")
c = q1.copy(); c.save_statevector()
r = aer.run(transpile(c, aer)).result(); sv = r.get_statevector()
pa = float(Statevector(sv).probabilities([11])[1]) if not hasattr(sv,'probabilities') else float(sv.probabilities([11])[1])
print("Aer statevector Q1 flag", repr(pa), "diff", pa-T1)
c = q0.copy(); c.save_statevector(); sv = aer.run(transpile(c, aer)).result().get_statevector()
print("Aer statevector Q0 flag diff", float(sv.probabilities([4])[1]) - T0)
for k in [16,64]:
    c = qk(k); c.save_statevector(); t0=time.perf_counter()
    tc = transpile(c, aer); sv = aer.run(tc).result().get_statevector()
    print(f"Aer k={k} diff", float(sv.probabilities([11])[1]) - math.sin((2*k+1)*theta)**2, f"{time.perf_counter()-t0:.2f}s")
# stitched pitfall
tA = transpile(q1, basis_gates=BASIS, optimization_level=1); tG = transpile(G, basis_gates=BASIS, optimization_level=1)
st = tA.copy(); st.compose(tG, inplace=True)
print("stitched k=1 p", float(Statevector(st).probabilities([11])[1]), "expected", math.sin(3*theta)**2)
tG0 = transpile(G, basis_gates=BASIS, optimization_level=0); st = q1.copy(); st.compose(tG0, inplace=True)
print("stitched(opt0) k=1 p", float(Statevector(st).probabilities([11])[1]))
