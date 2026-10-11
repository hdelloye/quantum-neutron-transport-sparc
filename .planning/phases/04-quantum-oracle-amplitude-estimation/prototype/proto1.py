import sys, time, math
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import StatePreparation, UCRYGate, grover_operator
from qiskit.quantum_info import Statevector
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels, BACK
from neutron_qae.exact import transmission_within, bitstring_probabilities_k1

K = build_kernels(sparc_first_wall())
T0 = transmission_within(K, 0); T1 = transmission_within(K, 1)
print("T0", repr(T0), "T1", repr(T1))

def x_amplitudes(k):
    a = np.zeros(32); a[:17] = np.sqrt(k.first_collision); return a

def build_q0(k):
    qc = QuantumCircuit(5, name="A_Q0")
    qc.append(StatePreparation(x_amplitudes(k)), range(5))
    return qc, 4

def build_q1(k, with_phi=True):
    if with_phi:
        qc = QuantumCircuit(12, name="A_Q1")
        X, A_, PH, E, T = [0,1,2,3,4], 5, [6,7,8,9], 10, 11
    else:
        qc = QuantumCircuit(8, name="A_Q1lite")
        X, A_, E, T = [0,1,2,3,4], 5, 6, 7
    qc.append(StatePreparation(x_amplitudes(k)), X)
    qc.append(UCRYGate([float(2*np.arcsin(np.sqrt(c))) for c in k.scatter_ratio]), [A_] + X[:4])
    if with_phi:
        qc.h(PH)
        ang = [float(2*np.arcsin(np.sqrt(k.flight[j, b, BACK]))) for b in range(16) for j in range(16)]
        qc.append(UCRYGate(ang), [E] + X[:4] + PH)
    else:
        ang = [float(2*np.arcsin(np.sqrt(k.flight[j, :, BACK].mean()))) for j in range(16)]
        qc.append(UCRYGate(ang), [E] + X[:4])
    qc.cx(X[4], T); qc.x(X[4]); qc.mcx([X[4], A_, E], T); qc.x(X[4])
    return qc, T

def flagp(qc, t):
    sv = Statevector(qc)
    return float(sv.probabilities([t])[1])

q0, t0 = build_q0(K); p0 = flagp(q0, t0)
print("Q0 flag", repr(p0), "diff vs T0", p0 - T0, "vs exp(-tau)", p0 - math.exp(-float(K.spec.tau_x(10.0))))
q1, t1 = build_q1(K); p1 = flagp(q1, t1)
print("Q1 flag", repr(p1), "diff", p1 - T1)
q1l, t1l = build_q1(K, False); p1l = flagp(q1l, t1l)
print("Q1lite flag", repr(p1l), "diff", p1l - T1)

# per-bitstring check (11 low bits) vs exact enumeration
sv = Statevector(q1); probs = sv.probabilities(list(range(11)))
ent = bitstring_probabilities_k1(K)
ref = np.zeros(2048)
for s,p,t in ent: ref[s]=p
print("max per-bitstring diff", np.abs(probs-ref).max())
# check T flag consistency per string
pfull = sv.probabilities()  # 4096
mism = 0
for s,p,t in ent:
    if p>1e-15:
        on = pfull[s | (1<<11)]; off = pfull[s]
        if (t and off>1e-14) or ((not t) and on>1e-14): mism+=1
print("flag mismatches", mism)
# no measure / reset, invertible
for name, qc in [("Q0",q0),("Q1",q1)]:
    ops = set(i.operation.name for i in qc.decompose(reps=6).data)
    print(name, "ops after decompose", sorted(ops))
    inv = qc.inverse()
    from qiskit.quantum_info import Operator
    if qc.num_qubits <= 12:
        I = Operator(qc).compose(Operator(inv))
        print(name, "A A^-1 = I ?", np.allclose(I.data, np.eye(2**qc.num_qubits), atol=1e-10))

BASIS = ["cx","rz","ry","rx","h","x","sx"]
def res(qc, label):
    t=time.perf_counter(); tq = transpile(qc, basis_gates=BASIS, optimization_level=1, seed_transpiler=7); dt=time.perf_counter()-t
    ops = tq.count_ops()
    print(f"{label}: qubits={tq.num_qubits} cx={ops.get('cx',0)} depth={tq.depth()} size={tq.size()} 2q-depth={tq.depth(lambda i: i.operation.num_qubits==2)} transpile_s={dt:.2f}")
    return tq
for name, qc, t in [("Q0",q0,t0),("Q1",q1,t1),("Q1lite",q1l,t1l)]:
    res(qc, name+" A")
    oracle = QuantumCircuit(qc.num_qubits); oracle.z(t)
    G = grover_operator(oracle, state_preparation=qc)
    res(G, name+" Q")
    for kk in (1,2):
        c = qc.copy()
        for _ in range(kk): c.compose(G, inplace=True)
        res(c, f"{name} Q^{kk}A")
