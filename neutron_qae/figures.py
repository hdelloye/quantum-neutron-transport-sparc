"""Figures rendered from committed artifact JSON only (PD-30).

Every figure is drawn from an artifact dict that ``artifacts.load_artifact`` returned, never
from sweep state, so a figure re-renders without rerunning its sweep. ``matplotlib.pyplot`` is
imported lazily inside the functions, and this module never selects a backend and never calls
``show``: scripts and tests select Agg, and Phase 6 shows the same figures in Qollab's console.
Only long-standing matplotlib calls are used (Pyodide ships 3.10; local is 3.11.2); a test
allowlists them. ``bbox_inches="tight"`` is not used, so pixel size = figsize x dpi.

Palette (validated all-pairs on the light surface, CVD worst 9.2): classical blue circles with
a solid line; analytic MLAE orange squares with a solid line; Aer green open diamonds with no
line (contrast 2.74:1, so it always carries its own marker and legend entry); exact or
reference values near-black; secondary text and the IonQ marker grey ("X"); fitted lines
dashed in the series colour; the reference sqrt(T1 (1 - T1) / N) dotted grey.

The comparison is sampling complexity only: no figure text claims a wall-clock speedup.
"""
from __future__ import annotations

import math
import numbers
import os
import textwrap

from neutron_qae import artifacts

DEFAULT_DPI = 110
MIN_DPI = 50
MAX_DPI = 200
FIGSIZE_ONE = (7.0, 4.6)
FIGSIZE_TWO = (9.0, 4.0)

SURFACE = "#fcfcfb"
CLASSICAL = "#2a78d6"
MLAE_ANALYTIC = "#eb6834"
MLAE_AER = "#1baf7a"
EXACT = "#0b0b0b"
SECONDARY = "#52514e"
GRID = "#d9d8d4"
LINE_WIDTH = 1.5
MARKER_SIZE = 5.5
IONQ_MARKER_SIZE = 9
BAND_ALPHA = 0.15


def _check_dpi(dpi) -> int:
    if isinstance(dpi, bool) or not isinstance(dpi, numbers.Integral) or not MIN_DPI <= dpi <= MAX_DPI:
        raise ValueError(f"dpi must be an integer in {MIN_DPI}..{MAX_DPI}, got {dpi!r}")
    return int(dpi)


def _fit_line(ax, fit, color, label):
    xs = [fit["cost_min"], fit["cost_max"]]
    ys = [10 ** (fit["intercept"] + fit["slope"] * math.log10(x)) for x in xs]
    ax.plot(xs, ys, linestyle="--", color=color, linewidth=1.0,
            label=f"{label}: slope {fit['slope']:.2f} +- {fit['slope_se']:.2f}")


def render_scaling(doc):
    """Headline log-log RMSE versus cost figure from a ``scaling_rmse`` artifact dict."""
    import matplotlib.pyplot as plt

    series = doc["results"]["series"]
    params = doc["parameters"]
    t1 = params["reference_T1"]
    fig, ax = plt.subplots(figsize=FIGSIZE_ONE, facecolor=SURFACE, subplot_kw={"facecolor": SURFACE})
    ax.set_xscale("log")
    ax.set_yscale("log")

    cl = series["classical_lattice"]
    ax.fill_between(cl["cost"], cl["abs_err_q16"], cl["abs_err_q84"], color=CLASSICAL, alpha=BAND_ALPHA,
                    linewidth=0, label="classical 16-84 percentile of |error|")
    ax.plot(cl["cost"], [math.sqrt(t1 * (1 - t1) / n) for n in cl["cost"]], linestyle=":", color=SECONDARY,
            linewidth=LINE_WIDTH, label="reference sqrt(T1 (1 - T1) / N)")
    ax.plot(cl["cost"], cl["rmse"], marker="o", linestyle="-", color=CLASSICAL, linewidth=LINE_WIDTH,
            markersize=MARKER_SIZE, label="classical lattice MC (histories)")
    _fit_line(ax, cl["fit"], CLASSICAL, "classical lattice MC")

    ml = series["mlae_analytic"]
    ax.plot(ml["cost"], ml["rmse"], marker="s", linestyle="-", color=MLAE_ANALYTIC, linewidth=LINE_WIDTH,
            markersize=MARKER_SIZE, label="MLAE analytic (exact theta, Binomial shots)")
    _fit_line(ax, ml["fit"], MLAE_ANALYTIC, "MLAE analytic, M >= 2")

    aer = series.get("mlae_aer")
    if aer is not None:
        ax.plot(aer["cost"], aer["rmse"], marker="D", linestyle="none", color=MLAE_AER,
                markerfacecolor="none", markeredgewidth=1.2, markersize=MARKER_SIZE + 1,
                label="MLAE Aer cross-check (transpiled Q1 circuits)")
        _fit_line(ax, aer["fit"], MLAE_AER, "MLAE Aer, M >= 2")

    marker = doc["results"].get("ionq_marker")
    if marker is not None:
        # One labelled marker, annotated in place (its label is long; the legend stays compact).
        ax.plot([marker["n_A"]], [marker["abs_err"]], marker="X", linestyle="none", color=SECONDARY,
                markersize=IONQ_MARKER_SIZE)
        ax.text(marker["n_A"] * 1.3, marker["abs_err"], textwrap.fill(marker["label"], 56), fontsize=6.5,
                color=SECONDARY, va="center", ha="left")

    ax.grid(True, which="major", color=GRID, linewidth=0.5)
    ax.set_xlabel("cost: histories N (classical) or applications of A, N_A = sum shots (2k+1) (MLAE)")
    ax.set_ylabel(f"RMSE vs exact T1 ({params['repetitions']} repetitions)")
    ax.set_title("K = 1 transmission, 10 cm SPARC wall: RMSE vs cost\n"
                 "sampling complexity only; analytic MLAE, Aer cross-check", fontsize=10)
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    return fig


RENDERERS = {"scaling_rmse": render_scaling}


def render_file(kind, json_path, png_path, dpi=DEFAULT_DPI) -> dict:
    """Render ``kind`` from the JSON file on disk to ``png_path``; return path, bytes, width, height."""
    dpi = _check_dpi(dpi)
    if kind not in RENDERERS:
        raise ValueError(f"no renderer for kind {kind!r}; known: {sorted(RENDERERS)}")
    doc = artifacts.load_artifact(json_path, kind)
    import matplotlib.pyplot as plt

    fig = RENDERERS[kind](doc)
    try:
        fig.savefig(png_path, dpi=dpi, format="png", facecolor=SURFACE)
    finally:
        plt.close(fig)
    width, height = artifacts.png_dimensions(png_path)
    return {"path": str(png_path), "bytes": os.path.getsize(png_path), "width": width, "height": height}
