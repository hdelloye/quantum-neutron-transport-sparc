"""Committed result artifacts: literal data/ paths, envelope schema, loader and validator (PD-24).

An artifact is one JSON document under ``data/`` holding the summary statistics of a local
sweep (never raw histories), plus the PNG figure rendered from that JSON. Every artifact uses
the envelope schema ``neutron_qae.artifact`` version 1 with the keys ``schema``,
``schema_version``, ``kind``, ``profile`` (quick or full), ``provenance``, ``parameters``,
``results`` and ``notes``, and is validated per kind.

Why the literal paths live here: Qollab ships a data file to the browser only when its path
appears as a literal string in a module reachable from ``main.py``. This module is that place,
and ``main.py`` imports it through one line. It therefore imports only the standard library,
is Pyodide-safe, and does no I/O at import time.

Integrity is a size cap (checked before reading) + the schema + the recorded seed and
provenance; floats are never hashed. JSON is written with sorted keys, indent 1,
``allow_nan=False`` and a trailing newline, so ``dumps_artifact(load_artifact(p))`` reproduces
the committed text byte for byte. NaN and Infinity are rejected on load as well.
"""
from __future__ import annotations

import json
import math
import numbers
import os
import struct
import tempfile

ARTIFACT_SCHEMA = "neutron_qae.artifact"
ARTIFACT_SCHEMA_VERSION = 1
PROFILES = ("quick", "full")
MAX_ARTIFACT_BYTES = 2_000_000       # Qollab's per-file limit, decimal reading
JSON_BUDGET_BYTES = 500_000
PNG_BUDGET_BYTES = 400_000
MIN_FULL_REPETITIONS = 50

SCALING_FILE = "data/scaling_rmse.json"
SCALING_FIGURE = "data/fig_scaling_rmse.png"

# kind -> (JSON path, PNG path); only implemented kinds are registered.
ARTIFACTS = {"scaling_rmse": (SCALING_FILE, SCALING_FIGURE)}

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_HEX = set("0123456789abcdef")
_ENVELOPE_KEYS = ("schema", "schema_version", "kind", "profile", "provenance", "parameters", "results", "notes")
_SERIES_COST_UNIT = {"classical_lattice": "histories", "mlae_analytic": "applications of A",
                     "mlae_aer": "applications of A"}
_SERIES_RUNNER = {"classical_lattice": "lattice", "mlae_analytic": "analytic", "mlae_aer": "aer"}


# ---------------------------------------------------------------- field checks

def _fail(field, why):
    raise ValueError(f"{field}: {why}")


def _is_int(v) -> bool:
    return isinstance(v, numbers.Integral) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, numbers.Real) and not isinstance(v, bool) and math.isfinite(float(v))


def _dict(doc, field):
    if not isinstance(doc, dict):
        _fail(field, f"must be an object, got {type(doc).__name__}")
    return doc


def _get(d, key, field):
    if key not in d:
        _fail(f"{field}.{key}" if field else key, "missing")
    return d[key]


def _int(v, field, minimum=None):
    if not _is_int(v):
        _fail(field, f"must be an integer, got {v!r}")
    if minimum is not None and v < minimum:
        _fail(field, f"must be >= {minimum}, got {v!r}")
    return int(v)


def _num(v, field, minimum=None, positive=False):
    if not _is_num(v):
        _fail(field, f"must be a finite number, got {v!r}")
    if positive and not v > 0:
        _fail(field, f"must be > 0, got {v!r}")
    if minimum is not None and v < minimum:
        _fail(field, f"must be >= {minimum}, got {v!r}")
    return float(v)


def _str(v, field):
    if not isinstance(v, str) or not v:
        _fail(field, f"must be a non-empty string, got {v!r}")
    return v


def _ascending_ints(v, field, minimum=1):
    if not isinstance(v, list) or not v:
        _fail(field, "must be a non-empty list of integers")
    for i, x in enumerate(v):
        _int(x, f"{field}[{i}]", minimum)
    for i in range(1, len(v)):
        if not v[i] > v[i - 1]:
            _fail(field, f"must be strictly ascending (duplicate or descending value {v[i]!r} at index {i})")
    return v


def _num_list(v, field, n, minimum=None, positive=False):
    if not isinstance(v, list):
        _fail(field, "must be a list of numbers")
    if len(v) != n:
        _fail(field, f"must have {n} entries (the length of cost), got {len(v)}")
    for i, x in enumerate(v):
        _num(x, f"{field}[{i}]", minimum, positive)
    return v


# ---------------------------------------------------------------- envelope

def _validate_provenance(prov):
    f = "provenance"
    _dict(prov, f)
    seed = _get(prov, "seed", f)
    _int(seed, "provenance.seed", 0)
    head = _get(prov, "git_head", f)
    if not isinstance(head, str) or len(head) != 40 or not set(head) <= _HEX:
        _fail("provenance.git_head", f"must be 40 lowercase hex characters, got {head!r}")
    if not isinstance(_get(prov, "git_dirty", f), bool):
        _fail("provenance.git_dirty", "must be a bool")
    script = _get(prov, "script", f)
    if not isinstance(script, str) or not script.startswith("scripts/"):
        _fail("provenance.script", f"must be a repo-relative path starting with 'scripts/', got {script!r}")
    argv = _get(prov, "argv", f)
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        _fail("provenance.argv", "must be a list of strings")
    created = _get(prov, "created_utc", f)
    if not isinstance(created, str) or not created.endswith("Z"):
        _fail("provenance.created_utc", f"must be a UTC timestamp ending in 'Z', got {created!r}")
    versions = _dict(_get(prov, "versions", f), "provenance.versions")
    for k, v in versions.items():
        if not isinstance(k, str) or not isinstance(v, str):
            _fail("provenance.versions", f"must map str to str, got {k!r}: {v!r}")
    _str(_get(prov, "platform", f), "provenance.platform")
    timings = _dict(_get(prov, "timings_s", f), "provenance.timings_s")
    for k, v in timings.items():
        if not isinstance(k, str):
            _fail("provenance.timings_s", f"keys must be strings, got {k!r}")
        _num(v, f"provenance.timings_s.{k}", 0)


def validate_artifact(doc, kind=None) -> dict:
    """Validate an artifact document (envelope, then the kind); ValueError naming the field."""
    _dict(doc, "artifact")
    for key in _ENVELOPE_KEYS:
        _get(doc, key, "")
    if doc["schema"] != ARTIFACT_SCHEMA:
        _fail("schema", f"must be {ARTIFACT_SCHEMA!r}, got {doc['schema']!r}")
    if not _is_int(doc["schema_version"]) or doc["schema_version"] != ARTIFACT_SCHEMA_VERSION:
        _fail("schema_version", f"must be {ARTIFACT_SCHEMA_VERSION}, got {doc['schema_version']!r}")
    if doc["kind"] not in _VALIDATORS:
        _fail("kind", f"must be a registered kind {sorted(_VALIDATORS)}, got {doc['kind']!r}")
    if kind is not None and doc["kind"] != kind:
        _fail("kind", f"expected {kind!r}, got {doc['kind']!r}")
    if doc["profile"] not in PROFILES:
        _fail("profile", f"must be one of {PROFILES}, got {doc['profile']!r}")
    _validate_provenance(doc["provenance"])
    _dict(doc["parameters"], "parameters")
    _dict(doc["results"], "results")
    notes = doc["notes"]
    if not isinstance(notes, list) or not notes:
        _fail("notes", "must be a non-empty list of strings")
    for i, n in enumerate(notes):
        _str(n, f"notes[{i}]")
    _VALIDATORS[doc["kind"]](doc)
    return doc


# ---------------------------------------------------------------- kind: scaling_rmse

def _validate_fit(fit, field, cost, M=None, min_M=None):
    _dict(fit, field)
    for key in ("slope", "intercept", "slope_se"):
        _num(_get(fit, key, field), f"{field}.{key}")
    points = _int(_get(fit, "points", field), f"{field}.points", 3)
    idx = [i for i in range(len(cost)) if M is None or min_M is None or M[i] >= min_M]
    if points != len(idx):
        _fail(f"{field}.points", f"must equal the {len(idx)} fitted series points, got {points}")
    if _get(fit, "cost_min", field) != cost[idx[0]] or _get(fit, "cost_max", field) != cost[idx[-1]]:
        _fail(f"{field}.cost_min", f"cost_min/cost_max must match the fitted range {cost[idx[0]]}..{cost[idx[-1]]}")


def _validate_series(name, s, params):
    f = f"results.series.{name}"
    _dict(s, f)
    cost = _ascending_ints(_get(s, "cost", f), f"{f}.cost")
    n = len(cost)
    _num_list(_get(s, "rmse", f), f"{f}.rmse", n, positive=True)
    _num_list(_get(s, "mean_error", f), f"{f}.mean_error", n)
    q16 = _num_list(_get(s, "abs_err_q16", f), f"{f}.abs_err_q16", n, minimum=0)
    q84 = _num_list(_get(s, "abs_err_q84", f), f"{f}.abs_err_q84", n, minimum=0)
    for i, (lo, hi) in enumerate(zip(q16, q84)):
        if lo > hi:
            _fail(f"{f}.abs_err_q16[{i}]", f"must be <= abs_err_q84[{i}] ({lo!r} > {hi!r})")
    reps = _get(s, "repetitions", f)
    if not _is_int(reps) or reps != params["repetitions"]:
        _fail(f"{f}.repetitions", f"must equal parameters.repetitions {params['repetitions']}, got {reps!r}")
    if _get(s, "cost_unit", f) != _SERIES_COST_UNIT[name]:
        _fail(f"{f}.cost_unit", f"must be {_SERIES_COST_UNIT[name]!r}, got {s['cost_unit']!r}")
    if _get(s, "runner", f) != _SERIES_RUNNER[name]:
        _fail(f"{f}.runner", f"must be {_SERIES_RUNNER[name]!r}, got {s['runner']!r}")
    M = None
    if name != "classical_lattice":
        M = _get(s, "M", f)
        if not isinstance(M, list) or M != list(range(1, n + 1)) or not all(_is_int(m) for m in M):
            _fail(f"{f}.M", f"must be the consecutive integers 1..{n}, got {M!r}")
        _int(_get(s, "shots_per_power", f), f"{f}.shots_per_power", 1)
        if _get(s, "schedule", f) != "exponential":
            _fail(f"{f}.schedule", f"must be 'exponential', got {s['schedule']!r}")
    _validate_fit(_get(s, "fit", f), f"{f}.fit", cost, M, params["fit_min_M"] if M is not None else None)


def _validate_ionq_marker(m):
    f = "results.ionq_marker"
    _dict(m, f)
    label = _str(_get(m, "label", f), f"{f}.label")
    if "execution proof" not in label or "not in any fit" not in label:
        _fail(f"{f}.label", "must contain 'execution proof' and 'not in any fit'")
    _int(_get(m, "n_A", f), f"{f}.n_A", 1)
    for key in ("a_hat", "se", "abs_err", "z"):
        _num(_get(m, key, f), f"{f}.{key}")
    ks = _get(m, "ks", f)
    if not isinstance(ks, list) or not all(_is_int(k) for k in ks):
        _fail(f"{f}.ks", "must be a list of integers")
    if _get(m, "in_fit", f) is not False:
        _fail(f"{f}.in_fit", "must be exactly false: the IonQ estimate is never in a fit")


def _validate_scaling(doc):
    p = doc["parameters"]
    full = doc["profile"] == "full"
    if _get(p, "model", "parameters") != "Q1":
        _fail("parameters.model", f"must be 'Q1', got {p['model']!r}")
    _num(_get(p, "width_x_cm", "parameters"), "parameters.width_x_cm", positive=True)
    t1 = _num(_get(p, "reference_T1", "parameters"), "parameters.reference_T1")
    if not 0.0 < t1 < 1.0:
        _fail("parameters.reference_T1", f"must lie in (0, 1), got {t1!r}")
    _int(_get(p, "repetitions", "parameters"), "parameters.repetitions",
         MIN_FULL_REPETITIONS if full else 2)
    _int(_get(p, "shots_per_power", "parameters"), "parameters.shots_per_power", 1)
    if _get(p, "schedule", "parameters") != "exponential":
        _fail("parameters.schedule", f"must be 'exponential', got {p['schedule']!r}")
    _ascending_ints(_get(p, "classical_N", "parameters"), "parameters.classical_N")
    _int(_get(p, "mlae_M_max", "parameters"), "parameters.mlae_M_max", 2)
    aer_m = _get(p, "aer_M_max", "parameters")
    if aer_m is None:
        if full:
            _fail("parameters.aer_M_max", "must be an integer >= 2 in the full profile")
    else:
        _int(aer_m, "parameters.aer_M_max", 2)
    if not _is_int(_get(p, "fit_min_M", "parameters")) or p["fit_min_M"] != 2:
        _fail("parameters.fit_min_M", f"must be 2, got {p['fit_min_M']!r}")

    r = doc["results"]
    series = _dict(_get(r, "series", "results"), "results.series")
    for name in ("classical_lattice", "mlae_analytic"):
        _validate_series(name, _get(series, name, "results.series"), p)
    aer = _get(series, "mlae_aer", "results.series")
    if aer is None:
        if full:
            _fail("results.series.mlae_aer", "is required (not null) in the full profile")
    else:
        _validate_series("mlae_aer", aer, p)
        if len(aer["cost"]) < 3:
            _fail("results.series.mlae_aer.cost", f"needs at least 3 points, got {len(aer['cost'])}")
    extra = set(series) - set(_SERIES_RUNNER)
    if extra:
        _fail("results.series", f"unknown series {sorted(extra)}")
    if series["classical_lattice"]["cost"] != p["classical_N"]:
        _fail("results.series.classical_lattice.cost", "must equal parameters.classical_N")
    if len(series["mlae_analytic"]["cost"]) != p["mlae_M_max"]:
        _fail("results.series.mlae_analytic.M", f"must run to parameters.mlae_M_max {p['mlae_M_max']}")
    if aer is not None and aer_m is not None and len(aer["cost"]) != aer_m:
        _fail("results.series.mlae_aer.M", f"must run to parameters.aer_M_max {aer_m}")
    marker = _get(r, "ionq_marker", "results")
    if marker is not None:
        _validate_ionq_marker(marker)


_VALIDATORS = {"scaling_rmse": _validate_scaling}


# ---------------------------------------------------------------- I/O

def dumps_artifact(doc) -> str:
    """Validated, canonical JSON text (sorted keys, indent 1, no NaN, trailing newline)."""
    validate_artifact(doc)
    text = json.dumps(doc, sort_keys=True, indent=1, allow_nan=False) + "\n"
    size = len(text.encode("utf-8"))
    if size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"artifact is {size} bytes, above the {MAX_ARTIFACT_BYTES}-byte limit")
    return text


def write_artifact(doc, path) -> int:
    """Atomically write the canonical JSON to ``path``; return the byte count."""
    data = dumps_artifact(doc).encode("utf-8")
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return len(data)


def _reject_constant(name):
    raise ValueError(f"artifact JSON contains the non-finite constant {name}; NaN and Infinity are not allowed")


def load_artifact(path, kind=None) -> dict:
    """Size-checked, NaN-free, validated artifact from ``path`` (plain JSON only)."""
    size = os.stat(path).st_size
    if size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"{path} is {size} bytes, above the {MAX_ARTIFACT_BYTES}-byte limit")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.strip():
        raise ValueError(f"{path} is empty")
    try:
        doc = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from None
    return validate_artifact(doc, kind)


def png_dimensions(path) -> tuple[int, int]:
    """(width, height) in pixels from the PNG IHDR chunk."""
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != _PNG_SIGNATURE or head[12:16] != b"IHDR":
        raise ValueError(f"{path} is not a PNG file with an IHDR chunk")
    width, height = struct.unpack(">II", head[16:24])
    return int(width), int(height)
