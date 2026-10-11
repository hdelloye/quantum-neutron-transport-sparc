## Deferred Items

- ruff TRY004 in tests/test_smoke.py (pre-existing since Phase 1)
  status: open
  **What:** `ruff check tests/test_smoke.py` flags the `raise RuntimeError("Only job type ionq.circuit.v1 is supported")` inside the inline fake IonQ backend (TRY004 prefers TypeError for a type check). The RuntimeError is deliberate: it mimics Qollab's HTTP 400. Found during 04-03 Task 1. The line is unchanged since Phase 1, so 04-03 left it alone. Fix: add `# noqa: TRY004 - mimics Qollab's HTTP 400`.
