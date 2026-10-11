import sys, time, math
sys.path.insert(0, "/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase4/scripts")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from proto1 import *  # noqa
from qiskit.quantum_info import Operator
theta = math.asin(math.sqrt(T1))
oracle = QuantumCircuit(12); oracle.z(11)
# Hypothesis: state_preparation vs state_preparation_dg synthesized inconsistently when transpiled separately
sp = StatePreparation(x_amplitudes(K))
c1 = QuantumCircuit(5); c1.append(sp, range(5))
c2 = QuantumCircuit(5); c2.append(sp.inverse(), range(5))
U1 = Operator(transpile(c1, basis_gates=BASIS, optimization_level=0)); U2 = Operator(transpile(c2, basis_gates=BASIS, optimization_level=0))
print("SP: transpiled(sp) @ transpiled(sp_dg) == I ?", np.allclose((U1.compose(U2)).data, np.eye(32), atol=1e-9))
print("SP: Operator(sp)@Operator(sp.inverse()) == I ?", np.allclose(Operator(c1).compose(Operator(c2)).data, np.eye(32), atol=1e-9))
# UCRY
u = UCRYGate([float(2*np.arcsin(np.sqrt(c))) for c in K.scatter_ratio])
c1 = QuantumCircuit(5); c1.append(u, range(5)); c2 = QuantumCircuit(5); c2.append(u.inverse(), range(5))
U1 = Operator(transpile(c1, basis_gates=BASIS, optimization_level=0)); U2 = Operator(transpile(c2, basis_gates=BASIS, optimization_level=0))
print("UCRY: transpiled(u) @ transpiled(u_dg) == I ?", np.allclose((U1.compose(U2)).data, np.eye(32), atol=1e-9))
# Robust recipe: A_basis first, then grover from A_basis
tA = transpile(q1, basis_gates=BASIS, optimization_level=1, seed_transpiler=1)
tA.global_phase = tA.global_phase  # keep
Gb = grover_operator(oracle, state_preparation=tA)
tGb = transpile(Gb, basis_gates=BASIS, optimization_level=1)
st = tA.copy(); st.compose(tGb, inplace=True)
print("A_basis stitched k=1 p", float(Statevector(st).probabilities([11])[1]), "expected", math.sin(3*theta)**2)
st = tA.copy()
for _ in range(16): st.compose(tGb, inplace=True)
print("A_basis stitched k=16 diff", float(Statevector(st).probabilities([11])[1]) - math.sin(33*theta)**2, "cx", st.count_ops().get('cx'))
# what does G's zero reflection compile to (12 qubits, 11-control mcx)?
z = QuantumCircuit(12); 
Gz = grover_operator(oracle, state_preparation=QuantumCircuit(12))
tz = transpile(Gz, basis_gates=BASIS, optimization_level=1)
print("zero-reflection-only grover (A=identity) cx:", tz.count_ops().get('cx'), "depth", tz.depth())
print("tGb cx", tGb.count_ops().get('cx'), "vs 2*A cx", 2*tA.count_ops().get('cx'))
print("grover_operator signature:")
import inspect; print(inspect.signature(grover_operator))
