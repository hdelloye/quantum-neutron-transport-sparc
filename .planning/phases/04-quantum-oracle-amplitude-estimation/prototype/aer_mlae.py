import sys, math, time
sys.path.insert(0, "/private/tmp/claude-501/-Users-hippolytedelloye/e3624457-04b5-453d-b4a4-7c5b36b6b203/scratchpad/phase4/scripts")


from build import *
from mlae_proto import mle_theta, n_a
from qiskit import ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.providers.basic_provider import BasicSimulator
from qiskit_algorithms import MaximumLikelihoodAmplitudeEstimation, EstimationProblem
theta = math.asin(math.sqrt(T1))
oracle = QuantumCircuit(12); oracle.z(11)
q1, _t = build_q1(K); G = grover_operator(oracle, state_preparation=q1)
def circ(k):
    c = q1.copy()
    for _ in range(k): c.compose(G, inplace=True)
    cr = ClassicalRegister(1, "flag"); c.add_register(cr); c.measure(11, cr[0]); c.name=f"AQ{k}"
    return c
cache = {}
def tcirc(k):
    if k not in cache: cache[k] = transpile(circ(k), basis_gates=BASIS, optimization_level=1, seed_transpiler=1)
    return cache[k]
aer = AerSimulator(method="statevector")
for M, shots_each, R in [(3,100,30),(5,100,30),(7,100,20)]:
    ks = [0] + [2**j for j in range(M-1)]
    tc = [tcirc(k) for k in ks]
    errs=[]; t=time.perf_counter()
    for r in range(R):
        res = aer.run(tc, shots=shots_each, seed_simulator=1000*M+r).result()
        hits = [res.get_counts(i).get("1", 0) for i in range(len(ks))]
        a = math.sin(mle_theta(ks, hits, [shots_each]*len(ks)))**2; errs.append(a-T1)
    errs=np.array(errs)
    print(f"Aer MLAE M={M} kmax={ks[-1]} shots/k={shots_each} N_A={n_a(ks,[shots_each]*len(ks))} first_est={T1+errs[0]:.6f} RMSE(R={R})={np.sqrt(np.mean(errs**2)):.3e} mean_err={errs.mean():+.2e} time/est={(time.perf_counter()-t)/R:.2f}s")
# compute_mle on Aer counts with qiskit (one job)
ks=[0,1,2,4,8]; res = aer.run([tcirc(k) for k in ks], shots=200, seed_simulator=5).result()
counts=[res.get_counts(i) for i in range(len(ks))]
print("counts keys", [sorted(c) for c in counts])
prob = EstimationProblem(q1, objective_qubits=[11])
tq = MaximumLikelihoodAmplitudeEstimation(ks).compute_mle(counts, prob)
hits=[c.get("1",0) for c in counts]
print("qiskit compute_mle a", math.sin(tq)**2, "vendored", math.sin(mle_theta(ks,hits,[200]*5))**2, "exact", T1)
# BasicSimulator one list job
bs = BasicSimulator(); t=time.perf_counter()
res = bs.run([tcirc(k) for k in ks], shots=200, seed_simulator=5).result()
hits=[res.get_counts(i).get("1",0) for i in range(len(ks))]
print("BasicSimulator list job hits", hits, f"{time.perf_counter()-t:.2f}s", "est", math.sin(mle_theta(ks,hits,[200]*5))**2)
