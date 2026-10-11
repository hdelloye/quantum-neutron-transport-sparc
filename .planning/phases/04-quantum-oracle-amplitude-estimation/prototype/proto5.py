import sys, time, math, json, gzip
sys.path.insert(0, "/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase4/scripts")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from proto1 import *  # noqa
from qiskit import ClassicalRegister
from qiskit_ionq import IonQProvider
from qiskit_ionq.helpers import qiskit_to_ionq
import qiskit_ionq; print("qiskit_ionq", qiskit_ionq.__version__)
be = IonQProvider("STUB").get_backend("simulator")
be.set_options(noise_model="ideal")
print("backend", be.name, "basis gates", len(be.basis_gates), "num_qubits", be.num_qubits)
print("target ops sample:", sorted(be.target.operation_names)[:60])
def circ(A, t, k, measure_all=False):
    oracle = QuantumCircuit(A.num_qubits); oracle.z(t)
    G = grover_operator(oracle, state_preparation=A)
    c = A.copy()
    for _ in range(k): c.compose(G, inplace=True)
    if measure_all:
        c.measure_all()
    else:
        cr = ClassicalRegister(1, "flag"); c.add_register(cr); c.measure(t, cr[0])
    c.name = f"AQ{k}"
    return c
for name, A, t in [("Q0",q0,t0),("Q1",q1,t1),("Q1lite",q1l,t1l)]:
    for k in [0,1,2,4,8]:
        c = circ(A, t, k, measure_all=(k==0 and name=="Q1"))
        tc = transpile(c, basis_gates=BASIS, optimization_level=1, seed_transpiler=1)
        maxctrl = max((getattr(i.operation,"num_ctrl_qubits",0) for i in tc.data), default=0)
        body = qiskit_to_ionq(tc, be, passed_args={"shots": 1000, "noise_model":"ideal"})
        n_gates = len(json.loads(body)["input"]["circuit"])
        print(f"{name} k={k}: cx={tc.count_ops().get('cx',0)} gates_json={n_gates} max_ctrl={maxctrl} body_bytes={len(body)} gzip={len(gzip.compress(body.encode()))}")
# what does transpile(c, ionq backend) do?
c = circ(q1, t1, 1)
t0_=time.perf_counter()
try:
    tc = transpile(c, be, optimization_level=1)
    print("transpile(c, ionq_backend) ops", dict(tc.count_ops()), "max ctrl", max(getattr(i.operation,'num_ctrl_qubits',0) for i in tc.data), f"{time.perf_counter()-t0_:.2f}s")
except Exception as e:
    print("transpile(c, ionq backend) failed", type(e).__name__, e)
