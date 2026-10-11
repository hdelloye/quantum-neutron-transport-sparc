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


def _sample_text(n) -> str:
    """'1e6' for an exact power of ten, else the comma-grouped integer."""
    e = math.floor(math.log10(n))
    m = n / 10 ** e
    if m == int(m) and m < 10:
        return f"{int(m)}e{e}" if m > 1 else f"1e{e}"
    return f"{n:,}"


def render_exit_histograms(doc):
    """Overlaid back-face exit-row histograms (log y) from an ``exit_histograms`` artifact dict.

    Circuit validation only: both histograms converge as 1 / sqrt(N); the title says so.
    """
    import matplotlib.pyplot as plt

    r = doc["results"]
    p = doc["parameters"]
    shots = p["shots"]
    rows = list(range(p["rows"]))
    fig, ax = plt.subplots(figsize=FIGSIZE_ONE, facecolor=SURFACE, subplot_kw={"facecolor": SURFACE})
    ax.set_yscale("log")
    cl = [c / shots for c in r["classical"]["row_counts"]]
    qu = [c / shots for c in r["quantum"]["row_counts"]]
    ax.step(rows, cl, where="mid", color=CLASSICAL, linewidth=LINE_WIDTH,
            label=f"classical lattice MC ({shots:,} histories)")
    ax.step(rows, qu, where="mid", color=MLAE_ANALYTIC, linewidth=LINE_WIDTH, linestyle="--",
            label=f"Q1 direct sampling, k = 0, Aer ({shots:,} shots)")
    ax.plot(rows, r["exact"]["row_probabilities"], marker="o", linestyle="none", color=EXACT,
            markersize=MARKER_SIZE - 1.5, label="exact K = 1 distribution")
    c = r["chi2"]
    box = "\n".join([
        f"chi-square, 16 rows + no exit, dof {c['classical_vs_quantum']['dof']}:",
        f"  classical vs quantum {c['classical_vs_quantum']['value']:.2f}",
        f"  classical vs exact {c['classical_vs_exact']['value']:.2f}",
        f"  quantum vs exact {c['quantum_vs_exact']['value']:.2f}",
        f"  bound dof + 5 sqrt(2 dof) = {c['classical_vs_quantum']['bound']:.2f}",
    ])
    ax.text(0.015, 0.97, box, transform=ax.transAxes, fontsize=7, color=SECONDARY, va="top", ha="left",
            bbox={"facecolor": SURFACE, "edgecolor": GRID, "boxstyle": "round,pad=0.3"})
    ax.set_xticks(rows)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    positive = [v for v in cl + qu + list(r["exact"]["row_probabilities"]) if v > 0]
    ax.set_ylim(min(positive) / 2, max(positive) * 25)     # headroom for the text box and legend
    ax.grid(True, which="major", color=GRID, linewidth=0.5)
    ax.set_xlabel("exit row on the back face (0 = y in [0, 0.625) cm; row 8 = beam line)")
    ax.set_ylabel("fraction of samples")
    ax.set_title("Back-face exit rows: lattice MC vs direct sampling of Q1 (k = 0, Aer), "
                 f"{_sample_text(shots)} samples each\n" + r["label"], fontsize=9)
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    return fig


def render_truncation_bias(doc):
    """Two panels from a ``truncation_bias`` artifact dict: transmissions vs wall; K = 1 coverage vs wall."""
    import matplotlib.pyplot as plt

    cases = doc["results"]["cases"]
    tc = [c for c in cases if c["model"] == "transport_corrected"]
    other = [c for c in cases if c["model"] != "transport_corrected"]
    n = doc["parameters"]["histories_per_case"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_TWO, facecolor=SURFACE,
                                   subplot_kw={"facecolor": SURFACE})
    w = [c["width_cm"] for c in tc]
    ax1.set_yscale("log")
    ax1.plot(w, [c["T0"] for c in tc], linestyle=":", marker="o", markersize=3, color=SECONDARY,
             linewidth=LINE_WIDTH, label="T0 exact (uncollided)")
    ax1.plot(w, [c["T1"] for c in tc], linestyle="-", marker="o", markersize=MARKER_SIZE, color=CLASSICAL,
             linewidth=LINE_WIDTH, label="T1 exact (K = 1, the estimand)")
    ax1.errorbar(w, [c["T_full"] for c in tc], yerr=[c["T_full_se"] for c in tc], marker="s", linestyle="none",
                 color=MLAE_ANALYTIC, markersize=MARKER_SIZE - 1, capsize=2,
                 label="T_full continuous MC (all orders)")
    ax1.grid(True, which="major", color=GRID, linewidth=0.5)
    ax1.set_xlabel("wall thickness, cm (2.0 cm W + steel)")
    ax1.set_ylabel("transmission (transport-corrected)")
    ax1.legend(fontsize=7, loc="lower left")

    ax2.errorbar(w, [100 * c["coverage"] for c in tc],
                 yerr=[100 * c["T1"] * c["T_full_se"] / c["T_full"] ** 2 for c in tc], marker="o",
                 linestyle="-", color=CLASSICAL, linewidth=LINE_WIDTH, markersize=MARKER_SIZE, capsize=2,
                 label="transport_corrected")
    for c in other:
        y = 100 * c["coverage"]
        ax2.errorbar([c["width_cm"]], [y], yerr=[100 * c["T1"] * c["T_full_se"] / c["T_full"] ** 2],
                     marker="X", linestyle="none", color=SECONDARY, markersize=IONQ_MARKER_SIZE - 1, capsize=2)
        ax2.text(c["width_cm"] + 0.8, y, f"{c['model']} (not used by the circuit): {y:.1f}%", fontsize=7,
                 color=SECONDARY, va="center", ha="left")
    for c in tc:
        ax2.text(c["width_cm"], 100 * c["coverage"] + 0.6, f"{100 * c['coverage']:.2f}%", fontsize=6.5,
                 color=SECONDARY, ha="center", va="bottom")
    ys = [100 * c["coverage"] for c in cases]
    ax2.set_ylim(min(ys) - 2.0, 101.5)
    ax2.set_xlim(min(c["width_cm"] for c in cases) - 2.0, max(c["width_cm"] for c in cases) + 2.5)
    ax2.grid(True, which="major", color=GRID, linewidth=0.5)
    ax2.set_xlabel("wall thickness, cm")
    ax2.set_ylabel("K = 1 coverage, % of full transmission")
    ax2.legend(fontsize=7, loc="lower right")
    fig.suptitle("Truncation: transmission within K collisions vs full continuous transmission "
                 f"({_sample_text(n)} histories per case)", fontsize=10)
    fig.tight_layout()
    return fig


def _rmse_text(x) -> str:
    """'1e-3' for an exact power of ten, else the general format."""
    e = round(math.log10(x))
    return f"1e{e}" if math.isclose(10.0 ** e, x, rel_tol=1e-12) else f"{x:g}"


def render_thickness_study(doc):
    """Two log-log panels from a ``thickness_study`` artifact dict: cost at 1% relative RMSE vs T1; ratio vs T1."""
    import matplotlib.pyplot as plt

    walls = doc["results"]["walls"]
    eps = doc["parameters"]["target_rel_rmse"]
    t_abs = doc["parameters"]["target_abs_rmse"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_TWO, facecolor=SURFACE,
                                   subplot_kw={"facecolor": SURFACE})
    rel = [w for w in walls if w["target_rel"]["bracketed"]]
    t1 = [w["T1"] for w in rel]
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.plot(t1, [w["target_rel"]["n_classical"] for w in rel], marker="o", linestyle="none", color=CLASSICAL,
             markersize=MARKER_SIZE, label="classical lattice MC (measured), histories")
    t_all = [w["T1"] for w in walls]
    ax1.plot(t_all, [w["target_rel"]["n_classical_theory"] for w in walls], linestyle=":", color=CLASSICAL,
             linewidth=LINE_WIDTH, label=f"classical theory (1 - T1) / (T1 {eps:g}^2)")
    ax1.plot(t1, [w["target_rel"]["n_mlae"] for w in rel], marker="s", linestyle="none", color=MLAE_ANALYTIC,
             markersize=MARKER_SIZE, label="MLAE analytic (measured), applications of A")
    for w in rel:
        for key in ("n_classical", "n_mlae"):
            ax1.text(w["T1"] * 1.06, w["target_rel"][key], f"{w['width_cm']:g} cm", fontsize=7, color=SECONDARY,
                     va="center", ha="left")
    ax1.grid(True, which="major", color=GRID, linewidth=0.5)
    ax1.set_xlabel("exact transmission T1 (thicker wall to the left)")
    ax1.set_ylabel(f"cost to reach {100 * eps:g}% relative RMSE")
    ax1.legend(fontsize=7, loc="best")

    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.plot(t1, [w["target_rel"]["ratio"] for w in rel], marker="o", linestyle="-", color=CLASSICAL,
             linewidth=LINE_WIDTH, markersize=MARKER_SIZE, label=f"{100 * eps:g}% relative RMSE: ratio grows")
    ab = [w for w in walls if w["target_abs"]["bracketed"]]
    ax2.plot([w["T1"] for w in ab], [w["target_abs"]["ratio"] for w in ab], marker="X", linestyle="--",
             color=SECONDARY, linewidth=1.0, markersize=MARKER_SIZE + 1,
             label=f"fixed absolute RMSE {_rmse_text(t_abs)} (disclosure): ratio shrinks")
    for w in rel:
        ax2.text(w["T1"] * 1.06, w["target_rel"]["ratio"], f"{w['target_rel']['ratio']:.3g} ({w['width_cm']:g} cm)",
                 fontsize=7, color=SECONDARY, va="center", ha="left")
    ax2.grid(True, which="major", color=GRID, linewidth=0.5)
    ax2.set_xlabel("exact transmission T1 (thicker wall to the left)")
    ax2.set_ylabel("classical histories / MLAE applications of A")
    shown = [w["target_rel"]["ratio"] for w in rel] + [w["target_abs"]["ratio"] for w in ab]
    if shown:
        ax2.set_ylim(min(shown) / 2.5, max(shown) * 1.6)      # room for the legend below the data
    ax2.legend(fontsize=7, loc="lower left")
    for ax in (ax1, ax2):
        ax.set_xlim(min(t_all) / 1.6, max(t_all) * 2.2)
        ax.set_xticks([], minor=True)
        ax.set_xticks(t_all, [f"{t:.3g}" for t in t_all])
    ws = [w["width_cm"] for w in walls]
    fig.suptitle(f"Rare-event study: walls {min(ws):g}-{max(ws):g} cm (2 cm W + steel), {100 * eps:g}% relative "
                 "RMSE, analytic MLAE", fontsize=10)
    fig.tight_layout()
    return fig


RENDERERS = {"scaling_rmse": render_scaling, "exit_histograms": render_exit_histograms,
             "truncation_bias": render_truncation_bias, "thickness_study": render_thickness_study}


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
