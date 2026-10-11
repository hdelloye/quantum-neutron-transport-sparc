"""LOCAL ONLY: turn a verbatim Qollab console paste into validated IonQ records (PD-20).

    scripts/ingest_ionq_records.py PASTE [--out PATH] [--allow-fake]

Every line containing ``IONQ_RECORD=`` is parsed (the JSON after the first occurrence). Failed
attempts (``accepted: false``) are listed and not stored. Each accepted record is validated with
``runners.validate_ionq_record`` and, unless ``--allow-fake``, must come from a real qiskit-ionq
backend (``backend_class`` starts with ``qiskit_ionq.`` and has no ``Fake``). Records are stored
exactly as parsed, merged idempotently with the output file (an identical record is a duplicate,
a different record with the same (timestamp, model, k, shots, ideal_mode) is an error), sorted by
timestamp and written atomically. Any error exits 2 and leaves the output file untouched.

``--allow-fake`` exists for tests and refuses to write the repo's data/ionq_runs.json.
No eval, exec or network: stdlib plus neutron_qae only.
"""
import argparse
import json
import math
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neutron_qae import runners

MARKER = "IONQ_RECORD="


def fail(msg: str):
    print(f"INGEST ERROR: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(2)


def _key(rec: dict) -> tuple:
    return (rec["timestamp"], rec["model"], rec["k"], rec["shots"], rec["ideal_mode"])


def parse_paste(text: str) -> list[tuple[int, object]]:
    """(line number, parsed JSON) for every line holding the marker; exits 2 on a malformed line."""
    out = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if MARKER not in line:
            continue
        payload = line.split(MARKER, 1)[1].strip()
        try:
            out.append((lineno, json.loads(payload)))
        except json.JSONDecodeError as exc:
            fail(f"line {lineno}: {MARKER} payload is not valid JSON ({exc})")
    return out


def check_record(lineno: int, rec, allow_fake: bool) -> dict:
    try:
        runners.validate_ionq_record(rec)
    except ValueError as exc:
        fail(f"line {lineno}: {exc}")
    cls = rec["backend_class"]
    if not allow_fake and (not isinstance(cls, str) or not cls.startswith("qiskit_ionq.") or "Fake" in cls):
        fail(f"line {lineno}: backend_class {cls!r} is not a real qiskit-ionq backend (use --allow-fake in tests)")
    return rec


def estimate_line(records: list[dict]) -> str:
    res = runners.ionq_estimate(records)
    if res is None:
        return "IONQ ESTIMATE none (needs a sampled k = 0 record)"
    from neutron_qae.oracle import make_problem

    t1 = make_problem("Q1").reference
    z = (res.a_hat - t1) / res.se if res.se > 0 else math.inf
    return (f"IONQ ESTIMATE a={res.a_hat:.6f} err={res.a_hat - t1:+.2e} se={res.se:.2e} z={z:+.2f} "
            f"N_A={res.n_A} ks={list(res.ks)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paste", help="text file holding the pasted Qollab console output")
    ap.add_argument("--out", default=str(ROOT / runners.IONQ_RUNS_FILE))
    ap.add_argument("--allow-fake", action="store_true", help="accept FakeIonQSimulator records (tests only)")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out)
    if a.allow_fake and out.resolve() == (ROOT / runners.IONQ_RUNS_FILE).resolve():
        fail(f"--allow-fake never writes the repo's {runners.IONQ_RUNS_FILE}")

    try:
        text = pathlib.Path(a.paste).read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read paste {a.paste}: {exc}")

    new, failed = [], 0
    for lineno, rec in parse_paste(text):
        if isinstance(rec, dict) and rec.get("accepted") is False:
            failed += 1
            print(f"FAILED ATTEMPT model={rec.get('model')} k={rec.get('k')} error={rec.get('error')}", flush=True)
            continue
        new.append((lineno, check_record(lineno, rec, a.allow_fake)))

    try:
        existing = runners.load_ionq_records(str(out)) if out.exists() else []
    except ValueError as exc:
        fail(f"existing {out} is invalid: {exc}")
    by_key = {_key(rec): rec for rec in existing}
    merged = list(existing)
    added = dup = 0
    for lineno, rec in new:
        key = _key(rec)
        if key in by_key:
            if by_key[key] == rec:
                dup += 1
                continue
            fail(f"line {lineno}: a different record with the same (timestamp, model, k, shots, ideal_mode) "
                 f"{key} is already stored")
        by_key[key] = rec
        merged.append(rec)
        added += 1
    merged.sort(key=lambda rec: rec["timestamp"])

    if added or not out.exists():
        payload = json.dumps(merged, indent=1, sort_keys=True) + "\n"
        size = len(payload.encode("utf-8"))
        if size > runners.MAX_RECORDS_BYTES:
            fail(f"{out} would be {size} bytes, above the {runners.MAX_RECORDS_BYTES}-byte limit")
        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=out.name + ".", suffix=".tmp", dir=out.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, out)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    sampled = sum(1 for rec in merged if rec["sampled"])
    print(f"INGESTED {added} new, {dup} duplicate, {failed} failed attempt(s); {len(merged)} records "
          f"({sampled} sampled) -> {out}", flush=True)
    print(estimate_line(merged), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
