import sys
sys.path.insert(0, "/Users/hippolytedelloye/Desktop/Quantum Computing Hackathon")
import numpy as np
from qiskit import QuantumCircuit, ClassicalRegister, transpile
from qiskit.circuit.library import StatePreparation, UCRYGate, grover_operator
from neutron_qae.problem import sparc_first_wall
from neutron_qae.kernels import build_kernels, BACK
from neutron_qae.exact import transmission_within
K = build_kernels(sparc_first_wall()); T0 = transmission_within(K, 0); T1 = transmission_within(K, 1)
BASIS = ["cx","rz","ry","rx","h","x","sx"]
def x_amplitudes(k):
    a = np.zeros(32); a[:17] = np.sqrt(k.first_collision); return a
def build_q0(k):
    qc = QuantumCircuit(5, name="A_Q0"); qc.append(StatePreparation(x_amplitudes(k)), range(5)); return qc, 4
def build_q1(k):
    qc = QuantumCircuit(12, name="A_Q1"); X, A_, PH, E, T = [0,1,2,3,4], 5, [6,7,8,9], 10, 11
    qc.append(StatePreparation(x_amplitudes(k)), X)
    qc.append(UCRYGate([float(2*np.arcsin(np.sqrt(c))) for c in k.scatter_ratio]), [A_] + X[:4])
    qc.h(PH)
    qc.append(UCRYGate([float(2*np.arcsin(np.sqrt(k.flight[j, b, BACK]))) for b in range(16) for j in range(16)]), [E] + X[:4] + PH)
    qc.cx(X[4], T); qc.x(X[4]); qc.mcx([X[4], A_, E], T); qc.x(X[4])
    return qc, T
def aqk(A, t, k, measure="flag"):
    oracle = QuantumCircuit(A.num_qubits); oracle.z(t)
    G = grover_operator(oracle, state_preparation=A)
    c = A.copy()
    for _ in range(k): c.compose(G, inplace=True)
    if measure == "flag":
        cr = ClassicalRegister(1, "flag"); c.add_register(cr); c.measure(t, cr[0])
    elif measure == "all":
        c.measure_all()
    c.name = f"AQ{k}"
    return c
