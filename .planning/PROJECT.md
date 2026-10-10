# Quantum Neutron Transport: SPARC First Wall

## What This Is

A hybrid classical plus quantum Monte Carlo neutron transport simulation of a 2D slab representing the first wall of MIT/CFS's SPARC tokamak, built for the Qollab × IonQ Hackathon (Quantum Impact theme). A classical Python Monte Carlo tracks 14 MeV neutrons through a tungsten-armored steel wall; a Qiskit quantum amplitude estimation (QAE) circuit estimates the same transmission fraction on IonQ's simulator within 24 qubits. The deliverable compares the two: error versus number of shots, plus overlaid exit-position histograms. Built by Hippolyte first, then handed to teammates via GitHub.

## Core Value

Show, on a real fusion-relevant transport problem, that quantum amplitude estimation reaches a target accuracy with fewer samples than classical Monte Carlo, with an honest classical baseline sitting next to it.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Classical Monte Carlo transport engine (Python) for a 2D slab, 10 cm thick × 10 cm wide, 16 × 16 grid
- [ ] Two-layer SPARC first-wall geometry: 2 cm tungsten heavy alloy (plasma side) + 8 cm 316 stainless steel, material determined by column index
- [ ] One-group 14 MeV neutron physics: fixed total, scattering and absorption cross sections per material; isotropic scattering; particle lost on exit through any face
- [ ] Three classical solvers: continuous Monte Carlo (physics reference), discrete lattice Monte Carlo on the same kernels (like-for-like baseline), exact lattice enumeration (ground truth); outputs: transmission and absorption fractions, exit-position histogram, collision-order breakdown, standard errors
- [ ] Pluggable random-bit source on the classical engine (numpy PRNG by default) so the engine never owns its randomness
- [ ] Qiskit state-preparation circuit where one quantum step is one collision (kernels precomputed from cross sections), every random choice consumes fresh qubits, transmission within K collisions flagged on an ancilla (Q0 ≈ 5 qubits, Q1 ≈ 12 qubits)
- [ ] Maximum-likelihood amplitude estimation (vendored numpy) of the transmission fraction from one multi-circuit job, total ≤ 24 qubits, runnable without error on the IonQ simulator through Qollab
- [ ] Sweep producing an RMSE-versus-N_A plot (N_A = Σ shots·(2k+1), ≥ 50 repetitions, against the exact discrete value) showing 1/sqrt(N) classical versus 1/N QAE scaling
- [ ] Overlaid exit-position histograms, classical versus quantum, at matched shot counts
- [ ] Runnable top-level `main.py` (Qollab runs Pyodide in the judge's browser; notebooks are not run) that completes from a logged-out Qollab browser
- [ ] Documentation covering the four judging criteria (novelty, technical execution, impact, documentation), the attribution line "This effort is supported by Qollab & IonQ.", library disclosure, MIT license, and replication instructions
- [ ] Modular repository layout so teammates can pick up the classical engine, the quantum circuits, or the writeup independently

### Out of Scope

- HTML/Java interactive visualization — deferred to v2; the team will build it after the core comparison is working
- Qubit-sourced random bits as the "quantum version" — the judging rules explicitly exclude projects whose quantum contribution is a random number generator, and on a simulator the bits are classical anyway
- Plasma turbulence or any nonlinear plasma simulation — quantum evolution is linear; published nonlinear-Vlasov quantum algorithms show worse-than-classical scaling and do not fit 24 qubits
- Multigroup or continuous-energy neutron physics — costs qubits the budget does not have; one-group is sufficient to demonstrate the scaling argument
- 3D geometry or finer than 16 × 16 grid — position register would exceed the qubit budget
- Real IonQ hardware runs — the hackathon provides the simulator; hardware noise would confound the scaling comparison
- Anisotropic scattering, fission, (n,2n) multiplication — real for 14 MeV in tungsten but out of scope for v1

## Context

- **Hackathon:** Qollab × IonQ, 48-hour build window Oct 9 7:00 PM ET to Oct 11 7:00 PM ET 2026. Theme: Quantum Impact (hybrid classical + quantum, strong classical baseline, show where the quantum subroutine improves efficiency). Judged on novelty, technical execution, impact, documentation. Must be Qiskit, MIT licensed, published and runnable on Qollab.xyz, with a demo video and repo link.
- **Novelty claim (checked against literature 2026-10-09, corrected after research):** prior art is Olivier & Nowak (arXiv:2410.19489, 2024: quantum-walk particle transport in 2D shielding, emulation only, no amplitude estimation), Lee, Lee & Kim (Phys. Rev. D 111, 116001, 2025: quantum walk + QAE for 10 MeV photon transport on the Qiskit simulator), and Miao, Jin & Sone (arXiv:2607.10772, 2026: QAE for two nuclear-engineering expectations, no transport). Defensible claim: "first end-to-end QAE estimate of a neutron transport tally through a two-material fusion first wall, with measured error-versus-oracle-query scaling against a matched classical baseline." Do NOT claim "first quantum neutron transport", "quantum advantage" or any wall-clock speedup.
- **Physical motivation:** ~80% of D-T fusion energy leaves as 14 MeV neutrons. Transport through the first wall sets wall lifetime (displacement damage, helium embrittlement), tritium breeding ratio in the blanket, HTS magnet shielding budget, activation inventory and heat deposition. Current practice is classical Monte Carlo (MCNP, OpenMC) where deep-penetration quantities are rare events and error falls as 1/sqrt(N).
- **SPARC materials:** plasma-facing components and first-wall tiles are tungsten and tungsten heavy alloy, uncooled, inside a 316 stainless steel vacuum vessel (CFS blog; ORNL/CFS report Pub181138; APS DPP 2021).
- **Physics scale:** 14 MeV mean free path ~3 cm in tungsten, ~6 cm in steel, so a 10 cm slab gives several collisions and a measurable transmitted fraction.
- **Qubit budget (corrected after research):** a step-by-step walk with reused direction qubits is wrong physics (coherent interference) and one-cell steps would need ~60 qubits. Instead one quantum step = one collision, with collision-to-collision kernels precomputed from the cross sections and fresh qubits for every random choice. Prototyped: Q0 (uncollided only) ≈ 5 qubits; Q1 (beam at mid-height, ≤ 1 collision) 12 qubits, 313 CX in A, 1,188 CX per Grover step, flag probability matches the exact sum to 1e-15; Q1-Y (uniform source) 16 qubits, 4,153 CX; K = 2 ≈ 20 qubits, local-only stretch. No step counter and no phase-estimation qubits (MLAE/IAE add zero).
- **Team workflow:** Hippolyte builds first, then pushes to GitHub for friends to continue. Modularity and documentation are first-class, not afterthoughts.
- **Prior state:** the folder held two empty placeholder files (a .tex and a .py). No prior code exists; everything is built inside the window.
- **Platform constraint (from research):** Qollab runs projects as Pyodide/Python 3.14 in the judge's browser from a top-level `main.py` with `backend` injected; one job per run on IonQ backends (so iterative AE is out, MLAE is in); `qiskit>=2.5.2` installed, qiskit-aer only behind a toggle; data files ≤ 2 MB loaded by literal path; GET-only network; logged-out running depends on a server flag. Every IonQ simulator on Qollab applies a noise model, so the headline scaling plot is an ideal local (Aer/analytic) result and the IonQ run proves execution. Test locally to stay off the shared queue.

## Constraints

- **Tech stack**: Python for the classical engine, Qiskit for the quantum circuits — hackathon rules require Qiskit; classical baseline in plain Python/numpy
- **Hardware**: ≤ 24 qubits — IonQ simulator limit available through Qollab
- **Timeline**: Submission by Oct 11 2026, 7:00 PM ET — hard hackathon deadline; partial submissions still eligible
- **License**: MIT, with attribution line and disclosure of all external libraries and AI tools used
- **Platform**: Must run without error on the Qollab-provided IonQ simulator, from a logged-out browser
- **Scaling honesty**: The speedup argument is sampling complexity (1/N vs 1/sqrt(N)), never "neutrons are quantum so qubits model them better"

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| QAE speedup as the quantum contribution, not qubit-sourced randomness | Rulebook excludes RNG-only projects; simulator bits are classical anyway; QAE gives a real citable advantage | — Pending |
| Neutron transport over plasma turbulence | Transport is linear and stochastic (QAE fits); turbulence is nonlinear and published quantum approaches scale worse than classical | — Pending |
| SPARC first wall as the real-world anchor | Real machine, real materials (tungsten + 316 SS), real design question (first-wall-to-blanket transmission) | — Pending |
| 2D slab 10 × 10 cm, 16 × 16 grid | Coarse enough that collision-to-collision kernels and the exact enumeration stay small; 2.0 cm W boundary falls inside column 4 and is handled by the kernels | — Pending |
| One quantum step = one collision, fresh qubits per random choice | Reused coin qubits give a coherent walk (wrong answer); one-cell steps need ~60 qubits; collision kernels make Q1 fit in 12 qubits | — Pending |
| MLAE (vendored) as the estimator, cost counted as N_A = Σ shots·(2k+1) | Qollab IonQ backends accept one job per run; Qiskit's `num_oracle_queries` undercounts; honest 1/N plot needs applications of A | — Pending |
| Three classical solvers (continuous, lattice, exact) | Classical and quantum must estimate the same quantity; exact lattice value is the truth for both error curves | — Pending |
| Phase 1 = Qollab smoke test + compliance | Platform behaviour is undocumented and can zero the submission; compliance items keep a partial submission eligible | — Pending |
| One-group 14 MeV physics | Multigroup costs qubits; one-group is enough to show the scaling | — Pending |
| Headline figure is error-vs-shots, histograms are supporting | The scaling plot is the evidence for the Core Value; histograms make it visual | — Pending |
| Classical engine takes its random source as a parameter | Keeps the engine identical across experiments; also lets a future RNG section reuse it | — Pending |
| Interactive front end deferred to v2 | Core comparison must work first; teammates build the UI after handoff | — Pending |
| 2026-10-10 note (01-03): MLAE on Qollab IonQ cannot be one multi-circuit job | Qollab's IonQ proxy accepts only `ionq.circuit.v1` and allows one job per Run, so an IonQ Run carries exactly one circuit; the MLAE row above holds for local/Built-in runs only. Ideal IonQ runs via `set_options(noise_model="ideal")` (sampled) | ⚠️ Revisit in Phase 4 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-10 after research and roadmap*
