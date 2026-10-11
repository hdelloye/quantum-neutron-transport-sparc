import sys, time, math
sys.path.insert(0, "/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase4/scripts")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from proto1 import *  # noqa
from qiskit_aer import AerSimulator
theta = math.asin(math.sqrt(T1))
oracle = QuantumCircuit(12); oracle.z(11)
G = grover_operator(oracle, state_preparation=q1)
def qk(k):
    c = q1.copy()
    for _ in range(k): c.compose(G, inplace=True)
    return c
aer = AerSimulator(method="statevector")
# what does transpile(c, aer) leave?
c = qk(1); tc = transpile(c, aer); print("transpile(c, aer) ops", dict(tc.count_ops()))
for k in [1,16,64]:
    c = qk(k); tc = transpile(c, basis_gates=BASIS, optimization_level=1); tc.save_statevector(); t0=time.perf_counter()
    sv = aer.run(tc).result().get_statevector()
    print(f"Aer(BASIS) k={k} diff", float(sv.probabilities([11])[1]) - math.sin((2*k+1)*theta)**2, f"{time.perf_counter()-t0:.2f}s")
# shot-based Aer runner
for k in [0,1,2,4,8]:
    c = qk(k); c.measure_all(); tc = transpile(c, basis_gates=BASIS, optimization_level=1)
    t0=time.perf_counter(); counts = aer.run(tc, shots=1000, seed_simulator=11).result().get_counts(); dt=time.perf_counter()-t0
    h = sum(v for kk,v in counts.items() if kk[0]=='1')  # qubit 11 is leftmost in 12-bit key
    print(f"Aer shots k={k} hits={h}/1000 expected={1000*math.sin((2*k+1)*theta)**2:.1f} t={dt:.3f}s nkeys={len(counts)}")
# measure only flag
c = qk(8); tc = transpile(c, basis_gates=BASIS, optimization_level=1)
from qiskit import ClassicalRegister
m = tc.copy(); cr = ClassicalRegister(1,"flag"); m.add_register(cr); m.measure(11, cr[0])
t0=time.perf_counter(); counts = aer.run(m, shots=1000, seed_simulator=11).result().get_counts(); print("flag-only counts", counts, f"{time.perf_counter()-t0:.3f}s")
# stitched pitfall
tA = transpile(q1, basis_gates=BASIS, optimization_level=1); tG = transpile(G, basis_gates=BASIS, optimization_level=1)
st = tA.copy(); st.compose(tG, inplace=True)
print("stitched opt1 k=1 p", float(Statevector(st).probabilities([11])[1]), "expected", math.sin(3*theta)**2)
tG0 = transpile(G, basis_gates=BASIS, optimization_level=0); st = q1.copy(); st.compose(tG0, inplace=True)
print("stitched opt0 k=1 p", float(Statevector(st).probabilities([11])[1]))
# Basic simulator
from qiskit.providers.basic_provider import BasicSimulator
bs = BasicSimulator()
for k in [0,1,2]:
    c = qk(k); tc = transpile(c, basis_gates=BASIS, optimization_level=1); m = tc.copy(); cr = ClassicalRegister(1,"flag"); m.add_register(cr); m.measure(11, cr[0])
    t0=time.perf_counter(); counts = bs.run(m, shots=1000, seed_simulator=3).result().get_counts(); print(f"BasicSim k={k}", counts, f"{time.perf_counter()-t0:.3f}s")
    t0=time.perf_counter(); tcb = transpile(c, bs, optimization_level=1); print("  transpile(c, BasicSimulator) ops", dict(tcb.count_ops()), f"{time.perf_counter()-t0:.2f}s")
