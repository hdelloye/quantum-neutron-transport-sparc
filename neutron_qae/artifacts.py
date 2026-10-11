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
HISTOGRAM_FILE = "data/exit_histograms.json"
HISTOGRAM_FIGURE = "data/fig_exit_histograms.png"
TRUNCATION_FILE = "data/truncation_bias.json"
TRUNCATION_FIGURE = "data/fig_truncation_bias.png"
THICKNESS_FILE = "data/thickness_study.json"
THICKNESS_FIGURE = "data/fig_thickness_ratio.png"

# kind -> (JSON path, PNG path); only implemented kinds are registered.
ARTIFACTS = {
    "scaling_rmse": (SCALING_FILE, SCALING_FIGURE),
    "exit_histograms": (HISTOGRAM_FILE, HISTOGRAM_FIGURE),
    "truncation_bias": (TRUNCATION_FILE, TRUNCATION_FIGURE),
    "thickness_study": (THICKNESS_FILE, THICKNESS_FIGURE),
}
HISTOGRAM_LABEL = "circuit validation, not speedup evidence"
MIN_FULL_HISTOGRAM_SHOTS = 1_000_000
MIN_FULL_TRUNCATION_HISTORIES = 10_000_000
# problem.MODELS written as literals: this module stays stdlib-only (a test pins the equality).
CROSS_SECTION_MODELS = ("transport_corrected", "isotropic_raw")

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


# ---------------------------------------------------------------- kind: exit_histograms

def _validate_count_block(b, field, shots, rows):
    _dict(b, field)
    rc = _get(b, "row_counts", field)
    if not isinstance(rc, list) or len(rc) != rows:
        _fail(f"{field}.row_counts", f"must be a list of {rows} integers")
    for i, c in enumerate(rc):
        _int(c, f"{field}.row_counts[{i}]", 0)
    none = _int(_get(b, "no_back_exit", field), f"{field}.no_back_exit", 0)
    got = _get(b, "shots", field)
    if not _is_int(got) or got != shots:
        _fail(f"{field}.shots", f"must equal parameters.shots {shots}, got {got!r}")
    if sum(rc) + none != shots:
        _fail(f"{field}.no_back_exit", f"row_counts sum {sum(rc)} + no_back_exit {none} must equal shots {shots}")
    return rc


def _validate_chi2(c, field):
    _dict(c, field)
    _num(_get(c, "value", field), f"{field}.value", 0)
    _int(_get(c, "dof", field), f"{field}.dof", 1)
    _num(_get(c, "bound", field), f"{field}.bound", positive=True)


def _validate_histograms(doc):
    p = doc["parameters"]
    full = doc["profile"] == "full"
    if _get(p, "model", "parameters") != "Q1":
        _fail("parameters.model", f"must be 'Q1', got {p['model']!r}")
    k = _get(p, "k", "parameters")
    if not _is_int(k) or k != 0:
        _fail("parameters.k", f"must be 0 (A only, direct sampling), got {k!r}")
    shots = _int(_get(p, "shots", "parameters"), "parameters.shots", MIN_FULL_HISTOGRAM_SHOTS if full else 1)
    rows = _get(p, "rows", "parameters")
    if not _is_int(rows) or rows != 16:
        _fail("parameters.rows", f"must be 16, got {rows!r}")
    _str(_get(p, "backend", "parameters"), "parameters.backend")
    _int(_get(p, "aer_seed_simulator", "parameters"), "parameters.aer_seed_simulator", 0)

    r = doc["results"]
    _validate_count_block(_get(r, "classical", "results"), "results.classical", shots, rows)
    q = _get(r, "quantum", "results")
    _validate_count_block(q, "results.quantum", shots, rows)
    for key in ("flag_hits", "outside_support", "flag_mismatch", "distinct_strings"):
        _int(_get(q, key, "results.quantum"), f"results.quantum.{key}", 0)
    if q["flag_hits"] > shots:
        _fail("results.quantum.flag_hits", f"must be <= shots {shots}, got {q['flag_hits']}")
    e = _dict(_get(r, "exact", "results"), "results.exact")
    pr = _get(e, "row_probabilities", "results.exact")
    if not isinstance(pr, list) or len(pr) != rows:
        _fail("results.exact.row_probabilities", f"must be a list of {rows} numbers")
    for i, x in enumerate(pr):
        _num(x, f"results.exact.row_probabilities[{i}]", 0)
    t1 = _num(_get(e, "T1", "results.exact"), "results.exact.T1")
    if not 0.0 < t1 < 1.0:
        _fail("results.exact.T1", f"must lie in (0, 1), got {t1!r}")
    if abs(math.fsum(pr) - t1) > 1e-12:
        _fail("results.exact.row_probabilities", f"must sum to T1 within 1e-12 (sum {math.fsum(pr)!r}, T1 {t1!r})")
    pn = _num(_get(e, "no_back_exit_probability", "results.exact"), "results.exact.no_back_exit_probability", 0)
    if abs(pn - (1.0 - t1)) > 1e-12:
        _fail("results.exact.no_back_exit_probability", f"must equal 1 - T1 within 1e-12, got {pn!r}")
    chi2 = _dict(_get(r, "chi2", "results"), "results.chi2")
    for key in ("classical_vs_quantum", "classical_vs_exact", "quantum_vs_exact"):
        _validate_chi2(_get(chi2, key, "results.chi2"), f"results.chi2.{key}")
    if _get(r, "label", "results") != HISTOGRAM_LABEL:
        _fail("results.label", f"must be exactly {HISTOGRAM_LABEL!r}, got {r['label']!r}")


# ---------------------------------------------------------------- kind: truncation_bias

_TRUNCATION_NUMS = ("T0", "T1", "T_full", "T_full_se", "within0", "within0_se", "within1", "within1_se",
                    "bias", "bias_se", "bias_z", "coverage")


def _validate_case_id(c, field):
    _dict(c, field)
    model = _get(c, "model", field)
    if model not in CROSS_SECTION_MODELS:
        _fail(f"{field}.model", f"must be one of {CROSS_SECTION_MODELS}, got {model!r}")
    width = _num(_get(c, "width_cm", field), f"{field}.width_cm")
    if not width > 2.0:
        _fail(f"{field}.width_cm", f"must be > 2.0 (the W layer), got {width!r}")
    return model, width


def _validate_truncation(doc):
    p = doc["parameters"]
    full = doc["profile"] == "full"
    _int(_get(p, "histories_per_case", "parameters"), "parameters.histories_per_case",
         MIN_FULL_TRUNCATION_HISTORIES if full else 1)
    cases = _get(p, "cases", "parameters")
    if not isinstance(cases, list) or not cases:
        _fail("parameters.cases", "must be a non-empty list")
    ids = [_validate_case_id(c, f"parameters.cases[{i}]") for i, c in enumerate(cases)]
    res = _get(doc["results"], "cases", "results")
    if not isinstance(res, list) or len(res) != len(ids):
        _fail("results.cases", f"must be a list of {len(ids)} cases (same order as parameters.cases)")
    for i, c in enumerate(res):
        f = f"results.cases[{i}]"
        if _validate_case_id(c, f) != ids[i]:
            _fail(f, f"model/width_cm must match parameters.cases[{i}] {ids[i]}")
        v = {key: _num(_get(c, key, f), f"{f}.{key}") for key in _TRUNCATION_NUMS}
        for key in ("T0", "T1", "T_full", "within0", "within1"):
            if not 0.0 <= v[key] <= 1.0:
                _fail(f"{f}.{key}", f"must lie in [0, 1], got {v[key]!r}")
        if not v["T_full"] > 0:
            _fail(f"{f}.T_full", "must be > 0")
        for key in ("T_full_se", "within0_se", "within1_se", "bias_se"):
            if not v[key] > 0:
                _fail(f"{f}.{key}", f"must be > 0, got {v[key]!r}")
        if abs(v["bias"] - (v["T_full"] - v["T1"])) > 1e-15:
            _fail(f"{f}.bias", "must equal T_full - T1 within 1e-15")
        if abs(v["coverage"] - v["T1"] / v["T_full"]) > 1e-12:
            _fail(f"{f}.coverage", "must equal T1 / T_full within 1e-12")
        if abs(v["bias_z"] - v["bias"] / v["bias_se"]) > 1e-9 * max(1.0, abs(v["bias_z"])):
            _fail(f"{f}.bias_z", "must equal bias / bias_se")
        orders = _get(c, "order_fractions", f)
        if not isinstance(orders, list) or not orders:
            _fail(f"{f}.order_fractions", "must be a non-empty list of numbers")
        for j, x in enumerate(orders):
            _num(x, f"{f}.order_fractions[{j}]", 0)


# ---------------------------------------------------------------- kind: thickness_study

def _validate_target(t, field, rmse_expected, full, require_bracketed):
    _dict(t, field)
    rmse = _num(_get(t, "rmse", field), f"{field}.rmse", positive=True)
    if rmse_expected is not None and abs(rmse - rmse_expected) > 1e-15 * rmse_expected:
        _fail(f"{field}.rmse", f"must equal {rmse_expected!r} within 1e-15 relative, got {rmse!r}")
    bracketed = _get(t, "bracketed", field)
    if not isinstance(bracketed, bool):
        _fail(f"{field}.bracketed", f"must be a bool, got {bracketed!r}")
    if require_bracketed and full and not bracketed:
        _fail(f"{field}.bracketed", "must be true in the full profile (costs are never extrapolated)")
    for key in ("n_classical", "n_mlae", "ratio"):
        v = _get(t, key, field)
        if v is None and not bracketed:
            continue
        _num(v, f"{field}.{key}", positive=True)
    if bracketed and abs(t["ratio"] - t["n_classical"] / t["n_mlae"]) > 1e-12 * t["ratio"]:
        _fail(f"{field}.ratio", "must equal n_classical / n_mlae")


def _validate_thickness(doc):
    p = doc["parameters"]
    full = doc["profile"] == "full"
    widths = _get(p, "widths_cm", "parameters")
    if not isinstance(widths, list) or not widths:
        _fail("parameters.widths_cm", "must be a non-empty list of numbers")
    for i, w in enumerate(widths):
        if not _num(w, f"parameters.widths_cm[{i}]") > 2.0:
            _fail(f"parameters.widths_cm[{i}]", f"must be > 2.0 (the W layer), got {w!r}")
        if i and not w > widths[i - 1]:
            _fail("parameters.widths_cm", "must be strictly ascending")
    t_rel = _num(_get(p, "target_rel_rmse", "parameters"), "parameters.target_rel_rmse", positive=True)
    if not t_rel < 1.0:
        _fail("parameters.target_rel_rmse", f"must lie in (0, 1), got {t_rel!r}")
    _num(_get(p, "target_abs_rmse", "parameters"), "parameters.target_abs_rmse", positive=True)
    reps = _int(_get(p, "repetitions", "parameters"), "parameters.repetitions", MIN_FULL_REPETITIONS if full else 2)
    classical_n = _ascending_ints(_get(p, "classical_N", "parameters"), "parameters.classical_N")
    m_max = _int(_get(p, "mlae_M_max", "parameters"), "parameters.mlae_M_max", 2)
    _int(_get(p, "shots_per_power", "parameters"), "parameters.shots_per_power", 1)
    _int(_get(p, "min_expected_events", "parameters"), "parameters.min_expected_events", 1)
    if not _is_int(_get(p, "fit_min_M", "parameters")) or p["fit_min_M"] != 2:
        _fail("parameters.fit_min_M", f"must be 2, got {p['fit_min_M']!r}")
    series_params = {"repetitions": reps, "fit_min_M": 2}

    r = doc["results"]
    walls = _get(r, "walls", "results")
    if not isinstance(walls, list) or len(walls) != len(widths):
        _fail("results.walls", f"must be a list of {len(widths)} walls (same order as parameters.widths_cm)")
    for i, w in enumerate(walls):
        f = f"results.walls[{i}]"
        _dict(w, f)
        if _num(_get(w, "width_cm", f), f"{f}.width_cm") != float(widths[i]):
            _fail(f"{f}.width_cm", f"must equal parameters.widths_cm[{i}] {widths[i]!r}")
        t0 = _num(_get(w, "T0", f), f"{f}.T0", positive=True)
        t1 = _num(_get(w, "T1", f), f"{f}.T1", positive=True)
        if not t0 <= t1 < 1.0:
            _fail(f"{f}.T1", f"must satisfy T0 <= T1 < 1, got T0 {t0!r}, T1 {t1!r}")
        if not _num(_get(w, "contract_abs_diff", f), f"{f}.contract_abs_diff", 0) <= 1e-12:
            _fail(f"{f}.contract_abs_diff", "must be <= 1e-12 (the oracle contract)")
        series = _dict(_get(w, "series", f), f"{f}.series")
        for name in ("classical_lattice", "mlae_analytic"):
            try:
                _validate_series(name, _get(series, name, f"{f}.series"), series_params)
            except ValueError as exc:
                raise ValueError(f"{f}: {exc}") from None
        if series["classical_lattice"]["cost"] != classical_n:
            _fail(f"{f}.series.classical_lattice.cost", "must equal parameters.classical_N")
        if len(series["mlae_analytic"]["cost"]) != m_max:
            _fail(f"{f}.series.mlae_analytic.M", f"must run to parameters.mlae_M_max {m_max}")
        tr = _get(w, "target_rel", f)
        _validate_target(tr, f"{f}.target_rel", t_rel * t1, full, True)
        _num(_get(tr, "n_classical_theory", f"{f}.target_rel"), f"{f}.target_rel.n_classical_theory", positive=True)
        _validate_target(_get(w, "target_abs", f), f"{f}.target_abs", p["target_abs_rmse"], full, False)
    trend = _dict(_get(r, "trend", "results"), "results.trend")
    if not isinstance(_get(trend, "ratio_increases_as_T1_falls", "results.trend"), bool):
        _fail("results.trend.ratio_increases_as_T1_falls", "must be a bool")
    for key in ("ratio_span", "loglog_slope_ratio_vs_T1"):
        v = _get(trend, key, "results.trend")
        if v is not None:
            _num(v, f"results.trend.{key}")


_VALIDATORS = {"scaling_rmse": _validate_scaling, "exit_histograms": _validate_histograms,
               "truncation_bias": _validate_truncation, "thickness_study": _validate_thickness}


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


# ---------------------------------------------------------------- Markdown formatters (PD-32)
#
# Docs are generated from data: docs/RESULTS.md and README.md embed the exact text these functions
# return for the committed JSON, and tests/test_results_doc.py fails on any drift. Stdlib only and
# matplotlib-free, so main.py can print the same tables on Qollab. No trailing newline.

_SERIES_TITLE = {"classical_lattice": "Classical lattice MC", "mlae_analytic": "MLAE, analytic runner",
                 "mlae_aer": "MLAE, Aer circuit simulation"}


def _table(header, rows) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _format_scaling(doc) -> str:
    p, r = doc["parameters"], doc["results"]
    rows = []
    for name in ("classical_lattice", "mlae_analytic", "mlae_aer"):
        s = r["series"].get(name)
        if s is None:
            continue
        fit = s["fit"]
        rows.append([_SERIES_TITLE[name], s["cost_unit"], str(fit["points"]),
                     f"{fit['cost_min']:,} to {fit['cost_max']:,}", f"{fit['slope']:.3f}", f"{fit['slope_se']:.3f}"])
    parts = [_table(["Series", "Cost unit", "Points fitted", "Cost range fitted", "Fitted slope", "Slope SE"], rows)]
    m = r["ionq_marker"]
    if m is not None:
        source = m["label"].split(",")[0]
        parts.append(f"{source} marker (execution proof, not in any fit): N_A = {m['n_A']:,}, "
                     f"|a_hat - T1| = {m['abs_err']:.2e}, z = {m['z']:.2f}")
    parts.append(f"Repetitions per point: {p['repetitions']}; seed {doc['provenance']['seed']}; "
                 f"{p['shots_per_power']} shots per Grover power; exact T1 = {p['reference_T1']!r}.")
    return "\n\n".join(parts)


_FORMATTERS = {"scaling_rmse": _format_scaling}


def format_markdown(doc) -> str:
    """Markdown table(s) for a validated artifact; the text docs/RESULTS.md embeds verbatim."""
    validate_artifact(doc)
    kind = doc["kind"]
    if kind not in _FORMATTERS:
        raise ValueError(f"kind: no Markdown formatter for {kind!r}")
    return _FORMATTERS[kind](doc)


def headline_sentence(doc) -> str:
    """One sentence with the fitted slopes (+- SE) of the scaling_rmse series, built from the JSON."""
    validate_artifact(doc)
    if doc["kind"] != "scaling_rmse":
        raise ValueError(f"kind: headline_sentence needs 'scaling_rmse', got {doc['kind']!r}")
    p, series = doc["parameters"], doc["results"]["series"]
    parts = []
    c = series["classical_lattice"]["fit"]
    parts.append(f"{c['slope']:.2f} +- {c['slope_se']:.2f} (classical lattice MC, {c['points']} points)")
    for name, m_max in (("mlae_analytic", p["mlae_M_max"]), ("mlae_aer", p["aer_M_max"])):
        s = series.get(name)
        if s is None:
            continue
        f = s["fit"]
        parts.append(f"{f['slope']:.2f} +- {f['slope_se']:.2f} ({_SERIES_TITLE[name]}, M = {p['fit_min_M']}..{m_max})")
    return "Fitted slopes: " + ", ".join(parts) + "."
