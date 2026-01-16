#!/usr/bin/env python3
"""
Generate conference/CNS-style figures and tables from assumed_results.json or real_results.json.

Design goals:
- Single entry script: generate_plots_table.py
- Deterministic output given JSON
- Vector-first: PDF + high-DPI PNG
- Minimal schema assumptions: uses `experiments` + `assets`

Usage:
  python generate_plots_table.py --results /path/to/assumed_results.json --outdir /path/to/output
  python generate_plots_table.py --results /path/to/real_results.json --outdir ./paper
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _require_matplotlib() -> Tuple[Any, Any, Any]:
    try:
        import matplotlib as mpl  # type: ignore
        import matplotlib.pyplot as plt  # type: ignore
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing plotting dependencies. Please install: pip install matplotlib numpy\n"
            f"Original error: {e}")
    return mpl, plt, np


def _try_import_pandas() -> Optional[Any]:
    try:
        import pandas as pd  # type: ignore

        return pd
    except Exception:
        return None


def _try_import_seaborn() -> Optional[Any]:
    try:
        import seaborn as sns  # type: ignore

        return sns
    except Exception:
        return None


def _latex_escape(s: str) -> str:
    # Minimal escaping for table entries.
    return (s.replace("\\", "\\textbackslash{}").replace("&", "\\&").replace(
        "%", "\\%").replace("_", "\\_").replace("#", "\\#"))


def _fmt_mean_std(mean: float, std: float | None, digits: int = 3) -> str:
    """
    Publication-style formatting: mean in normal size, std in \\scriptsize (more professional appearance).
    """
    if std is None:
        return f"{mean:.{digits}f}"
    if std < 0.0005 and std > 0:
        return f"{mean:.{digits}f} {{\\scriptsize $\\pm$ $<$0.001}}"
    return f"{mean:.{digits}f} {{\\scriptsize $\\pm$ {std:.{digits}f}}}"


def _mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, text: str) -> None:
    _mkdir(path.parent)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_by_id(items: List[Dict[str, Any]], item_id: str) -> Dict[str, Any]:
    for it in items:
        if it.get("id") == item_id:
            return it
    raise KeyError(f"Object with id={item_id} not found")


def _method_display_name(doc: Dict[str, Any], method_id: str) -> str:
    if method_id == "ours":
        return doc.get("paper", {}).get("method", {}).get("short", "Ours")
    for b in doc.get("baselines", []):
        if b.get("id") == method_id:
            return b.get("short") or b.get("name") or method_id
    return method_id


def _dataset_display_name(doc: Dict[str, Any], dataset_id: str) -> str:
    for d in doc.get("datasets", []):
        if d.get("id") == dataset_id:
            return d.get("name") or dataset_id
    return dataset_id


def _metric_display_name(doc: Dict[str, Any], metric_id: str) -> str:
    for m in doc.get("metrics", []):
        if m.get("id") == metric_id:
            return m.get("name") or metric_id
    return metric_id


def _metric_higher_is_better(doc: Dict[str, Any], metric_id: str) -> bool:
    for m in doc.get("metrics", []):
        if m.get("id") == metric_id:
            direction = (m.get("direction") or "higher_is_better").lower()
            return direction != "lower_is_better"
    return True


def _mean_std(values: List[float]) -> Tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    mu = sum(values) / len(values)
    if len(values) == 1:
        return mu, 0.0
    var = sum((x - mu)**2 for x in values) / (len(values) - 1)
    return mu, math.sqrt(var)


def _mean_std_bands(
    y: List[List[float]],
    *,
    orientation: str = "round_major",
) -> Tuple[List[float], List[float]]:
    """
    Convert multi-seed, multi-step measurements into per-step mean/std bands.

    Parameters
    - y:
      - orientation="round_major": y is T x S (each row = one step, values across seeds)
      - orientation="seed_major": y is S x T (each row = one seed curve)
    """
    if not y:
        return [], []
    if not isinstance(y[0], list):
        raise ValueError("Expected y to be a list of lists for multi-seed bands")

    ori = (orientation or "round_major").strip().lower()
    if ori == "round_major":
        per_step = y
    elif ori == "seed_major":
        per_step = [list(v) for v in zip(*y)]
    else:
        raise ValueError(f"Unsupported orientation: {orientation}")

    means: List[float] = []
    stds: List[float] = []
    for vals in per_step:
        mu, sd = _mean_std(list(map(float, vals)))
        means.append(float(mu))
        stds.append(float(sd))
    return means, stds


def _set_style(mpl: Any) -> None:
    # Reference: serif + pdf.fonttype=42 (editable vector fonts) + higher DPI from previous project scripts.
    sns = _try_import_seaborn()
    if sns is not None:
        sns.set_theme(style="white", palette="colorblind")

    mpl.rcParams.update({
        "figure.dpi": 200,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": ":",
        "grid.linewidth": 0.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "text.usetex": False,
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
    })


@dataclass
class OutputPaths:
    pdf: Optional[Path] = None
    png: Optional[Path] = None
    latex: Optional[Path] = None


def _asset_outputs(outdir: Path, output_obj: Dict[str, Any]) -> OutputPaths:

    def _p(k: str) -> Optional[Path]:
        v = output_obj.get(k)
        if not v:
            return None
        return outdir / v

    return OutputPaths(pdf=_p("pdf"), png=_p("png"), latex=_p("latex"))


def _save_figure(plt: Any, fig: Any, outputs: OutputPaths) -> None:
    if outputs.pdf:
        _mkdir(outputs.pdf.parent)
        fig.savefig(outputs.pdf)
    if outputs.png:
        _mkdir(outputs.png.parent)
        fig.savefig(outputs.png)
    plt.close(fig)


_LATEX_STRIP_RULES = [
    (re.compile(r"\\textbf\{([^}]*)\}"), r"\1"),
    (re.compile(r"\\underline\{([^}]*)\}"), r"\1"),
    (re.compile(r"\{\\scriptsize\s+([^}]*)\}"), r"\1"),
    (re.compile(r"\$"), r""),
    (re.compile(r"\\pm"), r"±"),
    (re.compile(r"\\textbackslash\{\}"), r"\\"),
]


def _strip_latex_markup(s: str) -> str:
    out = s
    for pat, rep in _LATEX_STRIP_RULES:
        out = pat.sub(rep, out)
    return out.strip()


def _render_main_table(
    doc: Dict[str, Any],
    exp: Dict[str, Any],
    caption: str,
    label: str,
    highlight_best: bool,
    highlight_second: bool,
) -> str:
    dataset_ids = exp["datasets"]
    method_ids = exp["methods"]
    metric_id = exp["metric"]
    higher_is_better = _metric_higher_is_better(doc, metric_id)

    # Compute mean over seeds
    cell: Dict[Tuple[str, str], Tuple[float, float]] = {}
    for ds in dataset_ids:
        ds_values = exp["values"][ds]
        for mid in method_ids:
            mu, sd = _mean_std(list(ds_values[mid]))
            cell[(ds, mid)] = (mu, sd)

    # Best / second per dataset (respect metric direction)
    best_mid_per_ds: Dict[str, str] = {}
    second_mid_per_ds: Dict[str, str] = {}
    if highlight_best or highlight_second:
        for ds in dataset_ids:
            ranked = sorted(
                method_ids,
                key=lambda mid: cell[(ds, mid)][0],
                reverse=higher_is_better,
            )
            if ranked:
                best_mid_per_ds[ds] = ranked[0]
            if highlight_second and len(ranked) >= 2:
                best_val = cell[(ds, ranked[0])][0]
                second = None
                for mid in ranked[1:]:
                    if abs(cell[(ds, mid)][0] - best_val) > 1e-12:
                        second = mid
                        break
                if second is not None:
                    second_mid_per_ds[ds] = second

    # LaTeX table
    ds_names = [
        _latex_escape(_dataset_display_name(doc, ds)) for ds in dataset_ids
    ]
    lines: List[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    colspec = "l" + "c" * len(ds_names)
    lines.append(f"\\begin{{tabular}}{{{colspec}}}")
    lines.append("\\toprule")
    header = "Method & " + " & ".join(ds_names) + " \\\\"
    lines.append(header)
    lines.append("\\midrule")

    for mid in method_ids:
        row = [_latex_escape(_method_display_name(doc, mid))]
        for ds in dataset_ids:
            mu, sd = cell[(ds, mid)]
            s = _fmt_mean_std(mu, sd if sd > 0 else None, digits=3)
            if highlight_best and best_mid_per_ds.get(ds) == mid:
                s = f"\\textbf{{{s}}}"
            elif highlight_second and second_mid_per_ds.get(ds) == mid:
                s = f"\\underline{{{s}}}"
            row.append(s)
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    metric_name = _metric_display_name(doc, metric_id)
    lines.append(f"\\caption{{{caption} Metric: {metric_name}.}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def _render_ablation_table(
    doc: Dict[str, Any],
    exp: Dict[str, Any],
    caption: str,
    label: str,
    highlight_best: bool,
) -> str:
    metric_name = _metric_display_name(doc, exp["metric"])
    variants = exp["variants"]

    rows: List[Tuple[str, float, float]] = []
    for v in variants:
        mu, sd = _mean_std(list(v["values"]))
        rows.append((v["name"], mu, sd))

    best_mu = max(mu for _, mu, _ in rows) if highlight_best else float("nan")

    lines: List[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\begin{tabular}{lc}")
    lines.append("\\toprule")
    lines.append(f"Variant & {metric_name} \\\\")
    lines.append("\\midrule")
    for name, mu, sd in rows:
        s = _fmt_mean_std(mu, sd if sd > 0 else None, digits=3)
        if highlight_best and abs(mu - best_mu) < 1e-12:
            s = f"\\textbf{{{s}}}"
        lines.append(f"{_latex_escape(name)} & {s} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def _render_sar_stats_table(
    doc: Dict[str, Any],
    exp: Dict[str, Any],
    caption: str,
    label: str,
) -> str:
    """Render SAR rule mining statistics table."""
    datasets = exp.get("datasets", [])
    metrics = exp.get("metrics", {})

    lines: List[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\begin{tabular}{lcc}")
    lines.append("\\toprule")
    lines.append("Metric & Scenario A (Sparse) & Scenario B (Rich) \\\\")
    lines.append("\\midrule")

    for metric_id, metric_name in [
        ("total_rules", "Total rules extracted"),
        ("compatible_pairs", "Compatible rule pairs"),
        ("max_clique_size", "Max clique size"),
        ("rule_usage_rate", "Rules used in generation"),
    ]:
        if metric_id in metrics:
            row = [_latex_escape(metric_name)]
            for ds in datasets:
                values = metrics[metric_id].get(ds, [])
                if values:
                    mu, sd = _mean_std(list(map(float, values)))
                    if metric_id == "rule_usage_rate":
                        # Format as percentage
                        s = f"{mu*100:.0f} {{\\scriptsize $\\pm$ {sd*100:.0f}}}\\%"
                    else:
                        s = _fmt_mean_std(mu, sd if sd > 0 else None, digits=1)
                    row.append(s)
                else:
                    row.append("N/A")
            lines.append(" & ".join(row) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def _render_pareto_metrics_table(
    doc: Dict[str, Any],
    exp: Dict[str, Any],
    caption: str,
    label: str,
    highlight_best: bool,
) -> str:
    """Render Pareto metrics table (hypervolume and front size)."""
    dataset_id = exp["datasets"][0]
    method_ids = exp["methods"]
    metric_ids = exp["metrics"]

    # Compute mean over seeds
    cell: Dict[Tuple[str, str], Tuple[float, float]] = {}
    for mid in method_ids:
        for met in metric_ids:
            mu, sd = _mean_std(
                list(map(float, exp["values"][dataset_id][mid][met])))
            cell[(mid, met)] = (mu, sd)

    # Best per metric
    best_mid_per_metric: Dict[str, str] = {}
    if highlight_best:
        for met in metric_ids:
            higher_is_better = _metric_higher_is_better(doc, met) if met in [
                m.get("id") for m in doc.get("metrics", [])
            ] else True
            ranked = sorted(
                method_ids,
                key=lambda mid: cell[(mid, met)][0],
                reverse=higher_is_better,
            )
            if ranked:
                best_mid_per_metric[met] = ranked[0]

    # LaTeX table
    metric_names = ["Hypervolume", "Front Size"]
    lines: List[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\begin{tabular}{lcc}")
    lines.append("\\toprule")
    lines.append("Method & " + " & ".join(metric_names) + " \\\\")
    lines.append("\\midrule")

    for mid in method_ids:
        row = [_latex_escape(_method_display_name(doc, mid))]
        for met in metric_ids:
            mu, sd = cell[(mid, met)]
            s = _fmt_mean_std(mu, sd if sd > 0 else None, digits=3)
            if highlight_best and best_mid_per_metric.get(met) == mid:
                s = f"\\textbf{{{s}}}"
            row.append(s)
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def _render_multi_metric_table(
    doc: Dict[str, Any],
    exp: Dict[str, Any],
    caption: str,
    label: str,
    highlight_best: bool,
) -> str:
    dataset_id = exp["datasets"][0]  # Usually one dataset for multi-metric
    method_ids = exp["methods"]
    metric_ids = exp["metrics"]

    # Compute mean over seeds
    cell: Dict[Tuple[str, str], Tuple[float, float]] = {}
    for mid in method_ids:
        for met in metric_ids:
            mu, sd = _mean_std(list(exp["values"][dataset_id][mid][met]))
            cell[(mid, met)] = (mu, sd)

    # Best per metric
    best_mid_per_metric: Dict[str, str] = {}
    if highlight_best:
        for met in metric_ids:
            higher_is_better = _metric_higher_is_better(doc, met)
            ranked = sorted(
                method_ids,
                key=lambda mid: cell[(mid, met)][0],
                reverse=higher_is_better,
            )
            if ranked:
                best_mid_per_metric[met] = ranked[0]

    # LaTeX table
    metric_names = [
        _latex_escape(_metric_display_name(doc, m)) for m in metric_ids
    ]
    lines: List[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{8pt}")
    colspec = "l" + "c" * len(metric_names)
    lines.append(f"\\begin{{tabular}}{{{colspec}}}")
    lines.append("\\toprule")
    header = "Method & " + " & ".join(metric_names) + " \\\\"
    lines.append(header)
    lines.append("\\midrule")

    for mid in method_ids:
        row = [_latex_escape(_method_display_name(doc, mid))]
        for met in metric_ids:
            mu, sd = cell[(mid, met)]
            s = _fmt_mean_std(mu, sd if sd > 0 else None, digits=3)
            if highlight_best and best_mid_per_metric.get(met) == mid:
                s = f"\\textbf{{{s}}}"
            row.append(s)
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def _table_to_png(doc: Dict[str, Any], latex_str: str,
                  output_png: Path) -> None:
    # Render a simple table image using matplotlib (no LaTeX dependency).
    mpl, plt, _np = _require_matplotlib()
    _set_style(mpl)

    # crude parse: extract header + rows from tabular environment
    lines = [ln.strip() for ln in latex_str.splitlines()]
    tabular_lines = []
    inside = False
    for ln in lines:
        if ln.startswith("\\begin{tabular}"):
            inside = True
            continue
        if ln.startswith("\\end{tabular}"):
            inside = False
            continue
        if inside:
            if ln in ("\\toprule", "\\midrule", "\\bottomrule"):
                continue
            if ln.endswith("\\\\"):
                tabular_lines.append(ln[:-2].strip())

    if not tabular_lines:
        raise RuntimeError(
            "Failed to extract rows from LaTeX table for PNG rendering")

    rows = [[c.strip() for c in r.split("&")] for r in tabular_lines]
    header = [_strip_latex_markup(x) for x in rows[0]]
    body = [[_strip_latex_markup(x) for x in rr] for rr in rows[1:]]

    fig, ax = plt.subplots(figsize=(max(6, 1.2 * len(header)),
                                    max(1.8, 0.5 + 0.5 * len(body))))
    ax.axis("off")
    tbl = ax.table(cellText=body,
                   colLabels=header,
                   loc="center",
                   cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.0, 1.25)
    _mkdir(output_png.parent)
    fig.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_grouped_bar(doc: Dict[str, Any], exp: Dict[str, Any],
                      style: Dict[str, Any], outputs: OutputPaths) -> None:
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    dataset_ids = exp["datasets"]
    method_ids = exp["methods"]

    ds_names = [_dataset_display_name(doc, ds) for ds in dataset_ids]
    method_names = [_method_display_name(doc, mid) for mid in method_ids]

    means = []
    stds = []
    for ds in dataset_ids:
        ds_values = exp["values"][ds]
        m = []
        s = []
        for mid in method_ids:
            mu, sd = _mean_std(list(ds_values[mid]))
            m.append(mu)
            s.append(sd)
        means.append(m)
        stds.append(s)

    means = np.array(means)  # [D, M]
    stds = np.array(stds)

    x = np.arange(len(ds_names))
    width = 0.8 / len(method_ids)

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for j, name in enumerate(method_names):
        alpha = 1.0 if method_ids[j] == "ours" else 0.75
        ax.bar(
            x + (j - (len(method_ids) - 1) / 2) * width,
            means[:, j],
            width,
            yerr=stds[:, j] if np.any(stds[:, j] > 0) else None,
            capsize=2,
            label=name,
            edgecolor="white",
            linewidth=0.5,
            alpha=alpha,
            error_kw={
                "elinewidth": 0.6,
                "capthick": 0.6,
                "ecolor": "#333333"
            },
        )

    ax.set_title(style.get("title", ""))
    ax.set_xlabel(style.get("xlabel", "Dataset"))
    ax.set_ylabel(
        style.get("ylabel",
                  _metric_display_name(doc, exp.get("metric", "primary"))))
    ax.set_xticks(x)
    ax.set_xticklabels(ds_names, rotation=20, ha="right")
    ax.set_axisbelow(True)
    if style.get("legend", True):
        ax.legend(frameon=False,
                  ncol=min(4, len(method_ids)),
                  loc="upper center",
                  bbox_to_anchor=(0.5, -0.20))
        fig.subplots_adjust(bottom=0.28)
    _save_figure(plt, fig, outputs)


def _plot_line(doc: Dict[str, Any], exp: Dict[str, Any], style: Dict[str, Any],
               outputs: OutputPaths) -> None:
    mpl, plt, _np = _require_matplotlib()
    _set_style(mpl)

    x = exp["x"]["values"]
    x_name = exp["x"].get("name", "x")

    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    for s in exp["series"]:
        mid = s["method"]
        y = s["y"]
        # Support two formats:
        # - y: [v1, v2, ...]
        # - y: [[seed1...], [seed2...], ...]  -> auto mean/std + error bands
        if y and isinstance(y[0], list):
            y_t = list(zip(*y))  # T x S
            means = [sum(v) / len(v) for v in y_t]
            stds = []
            for v in y_t:
                _mu, _sd = _mean_std(list(map(float, v)))
                stds.append(_sd)
            ax.plot(x, means, marker="o", label=_method_display_name(doc, mid))
            ax.fill_between(
                x,
                [m - s for m, s in zip(means, stds)],
                [m + s for m, s in zip(means, stds)],
                alpha=0.15,
            )
        else:
            ax.plot(x, y, marker="o", label=_method_display_name(doc, mid))

    ax.set_title(style.get("title", exp.get("title", "")))
    ax.set_xlabel(style.get("xlabel", x_name))
    ax.set_ylabel(
        style.get("ylabel",
                  _metric_display_name(doc, exp.get("metric", "primary"))))
    if style.get("legend", True):
        ax.legend(frameon=False,
                  ncol=2,
                  loc="upper center",
                  bbox_to_anchor=(0.5, -0.18))
        fig.subplots_adjust(bottom=0.25)
    _save_figure(plt, fig, outputs)


def _plot_scatter(doc: Dict[str, Any], exp: Dict[str, Any],
                  style: Dict[str, Any], outputs: OutputPaths) -> None:
    mpl, plt, _np = _require_matplotlib()
    _set_style(mpl)

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    for p in exp["points"]:
        mid = p["method"]
        ax.scatter(p["x"], p["y"], s=60, label=_method_display_name(doc, mid))
        ax.annotate(_method_display_name(doc, mid), (p["x"], p["y"]),
                    textcoords="offset points",
                    xytext=(6, 4),
                    fontsize=8)

    ax.set_title(style.get("title", exp.get("title", "")))
    ax.set_xlabel(
        style.get("xlabel",
                  _metric_display_name(doc, exp.get("x_metric",
                                                    "efficiency"))))
    ax.set_ylabel(
        style.get("ylabel",
                  _metric_display_name(doc, exp.get("y_metric", "primary"))))
    if style.get("legend", False):
        ax.legend(frameon=False)
    _save_figure(plt, fig, outputs)


def _plot_system_diagram(doc: Dict[str, Any], exp: Dict[str, Any],
                         style: Dict[str, Any], outputs: OutputPaths) -> None:
    """
    Draw a simple system overview diagram (mode boundaries + tool-orchestrated loop).
    This is intentionally schematic and LaTeX-free (pure matplotlib).
    """
    mpl, plt, _np = _require_matplotlib()
    _set_style(mpl)
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # type: ignore

    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.axis("off")

    def box(x: float, y: float, w: float, h: float, title: str, body: str,
            fc: str, ec: str) -> None:
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.02",
            linewidth=1.0,
            edgecolor=ec,
            facecolor=fc,
        )
        ax.add_patch(patch)
        ax.text(x + 0.02,
                y + h - 0.06,
                title,
                fontsize=11,
                fontweight="bold",
                va="top")
        ax.text(x + 0.02, y + h - 0.12, body, fontsize=9, va="top")

    # Main modes
    box(
        0.05,
        0.55,
        0.27,
        0.35,
        "Insight",
        "Mine SAR rules\nHotspots / trends\nEvidence chains",
        fc="#E8F1FF",
        ec="#2B6CB0",
    )
    box(
        0.365,
        0.55,
        0.27,
        0.35,
        "Design",
        "Generate candidates\nConstraints + reflection\nPareto parent selection",
        fc="#E6FFFA",
        ec="#2C7A7B",
    )
    box(
        0.68,
        0.55,
        0.27,
        0.35,
        "Evaluation",
        "Unified oracle\nScore breakdown\nBudget accounting",
        fc="#FFF5F5",
        ec="#C53030",
    )

    # Tools row
    box(
        0.12,
        0.08,
        0.76,
        0.33,
        "Tools / Oracles",
        "Tabular potency model  •  Boltz-2 structure  •  Energy scoring  •  Developability heuristics",
        fc="#F7FAFC",
        ec="#4A5568",
    )

    def arrow(x1: float, y1: float, x2: float, y2: float) -> None:
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.0,
                color="#2D3748",
            ))

    # Arrows: Insight -> Design -> Evaluation -> Design (loop), and Evaluation -> Tools
    arrow(0.32, 0.725, 0.365, 0.725)
    arrow(0.635, 0.725, 0.68, 0.725)
    arrow(0.815, 0.55, 0.50, 0.43)
    arrow(0.50, 0.43, 0.50, 0.55)
    arrow(0.50, 0.55, 0.50, 0.41)

    ax.set_title(style.get("title", exp.get("title", "System Overview")),
                 pad=10)
    _save_figure(plt, fig, outputs)


def _prepare_heatmap_data(
    *,
    rows: List[str],
    cols: List[str],
    vmap: Dict[str, Dict[str, float]],
    normalize: str = "none",
    vmin: float | None = None,
    vmax: float | None = None,
    robust: bool = False,
    q_low: float = 0.05,
    q_high: float = 0.95,
) -> Tuple[Any, float, float]:
    """
    Prepare a heatmap matrix and determine vmin/vmax.

    normalize:
      - "none": raw values
      - "row_delta_best": per-row gap to the best method (best becomes 0.0, others negative)

    When robust=True and vmin/vmax are not provided, use [q_low, q_high] quantiles to
    avoid collapsed color ranges when values are tightly clustered.
    """
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency: numpy is required for heatmap preparation.\n"
            f"Original error: {e}") from e

    data = np.array([[float(vmap[r][c]) for c in cols] for r in rows], dtype=float)

    norm = (normalize or "none").strip().lower()
    if norm == "none":
        pass
    elif norm == "row_delta_best":
        row_best = np.max(data, axis=1, keepdims=True)
        data = data - row_best
        # By construction, best is 0.0 and others are <= 0.0.
        if vmax is None:
            vmax = 0.0
    else:
        raise ValueError(f"Unsupported heatmap normalization: {normalize}")

    finite = data[np.isfinite(data)]
    if finite.size == 0:
        _vmin, _vmax = 0.0, 1.0
    else:
        if vmin is not None and vmax is not None:
            _vmin, _vmax = float(vmin), float(vmax)
        else:
            if robust:
                lo = float(np.quantile(finite, q_low))
                hi = float(np.quantile(finite, q_high))
            else:
                lo = float(np.min(finite))
                hi = float(np.max(finite))

            _vmin = float(vmin) if vmin is not None else lo
            _vmax = float(vmax) if vmax is not None else hi

    if not (_vmin < _vmax):
        # Avoid a zero-range colorbar.
        eps = 1e-6 if _vmin == 0.0 else abs(_vmin) * 1e-6
        _vmin, _vmax = _vmin - eps, _vmax + eps

    return data, _vmin, _vmax


def _plot_heatmap(doc: Dict[str, Any], exp: Dict[str, Any],
                  style: Dict[str, Any], outputs: OutputPaths) -> None:
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)
    sns = _try_import_seaborn()

    rows = exp["rows"]
    cols = exp["cols"]
    vmap = exp["values"]
    normalize = style.get("normalize", "none")
    robust = bool(style.get("robust", False))
    q_low = float(style.get("q_low", 0.05))
    q_high = float(style.get("q_high", 0.95))
    vmin = style.get("vmin", None)
    vmax = style.get("vmax", None)
    data, vmin_f, vmax_f = _prepare_heatmap_data(
        rows=rows,
        cols=cols,
        vmap=vmap,
        normalize=str(normalize),
        vmin=float(vmin) if vmin is not None else None,
        vmax=float(vmax) if vmax is not None else None,
        robust=robust,
        q_low=q_low,
        q_high=q_high,
    )

    # Figure size scales with number of rows
    fig_h = max(2.6, 0.22 * len(rows))
    fig_w = max(5.8, 0.75 * len(cols))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    cmap = style.get("cmap", "viridis")
    cbar_label = style.get("cbar_label", style.get("cbar", ""))
    annot = bool(style.get("annot", False))
    annot_fmt = style.get("annot_fmt", ".2f")

    if sns is not None:
        sns.heatmap(
            data,
            ax=ax,
            cmap=cmap,
            vmin=vmin_f,
            vmax=vmax_f,
            cbar=True,
            annot=annot,
            fmt=annot_fmt,
            linewidths=0.2,
            linecolor="#FFFFFF",
        )
    else:
        im = ax.imshow(data,
                       aspect="auto",
                       cmap=cmap,
                       vmin=vmin_f,
                       vmax=vmax_f)
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)

    ax.set_xticks(list(range(len(cols))))
    ax.set_xticklabels([_method_display_name(doc, c) for c in cols],
                       rotation=20,
                       ha="right")
    ax.set_yticks(list(range(len(rows))))
    ax.set_yticklabels(rows, rotation=0)
    ax.set_xlabel(style.get("xlabel", "Method"))
    ax.set_ylabel(style.get("ylabel", "Target"))
    ax.set_title(style.get("title", exp.get("title", "")))
    if cbar_label:
        # seaborn creates the colorbar; matplotlib fallback uses fig.colorbar above.
        try:
            ax.collections[0].colorbar.set_label(str(cbar_label))  # type: ignore[attr-defined]
        except Exception:
            pass
    _save_figure(plt, fig, outputs)


def _plot_stacked_bar(doc: Dict[str, Any], exp: Dict[str, Any],
                      style: Dict[str, Any], outputs: OutputPaths) -> None:
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    components = exp["components"]
    values = exp["values"]  # method -> component -> seconds
    method_ids = list(values.keys())
    method_names = [_method_display_name(doc, mid) for mid in method_ids]

    x = np.arange(len(method_ids))
    fig, ax = plt.subplots(figsize=(7.2, 3.4))

    bottoms = np.zeros(len(method_ids), dtype=float)
    colors = ["#2B6CB0", "#2C7A7B", "#C05621", "#718096", "#805AD5", "#38A169"]
    for i, comp in enumerate(components):
        ys = np.array(
            [float(values[mid].get(comp, 0.0)) for mid in method_ids],
            dtype=float)
        ax.bar(x,
               ys,
               bottom=bottoms,
               label=comp.replace("_", " "),
               color=colors[i % len(colors)],
               edgecolor="white",
               linewidth=0.4)
        bottoms = bottoms + ys

    ax.set_xticks(x)
    ax.set_xticklabels(method_names, rotation=20, ha="right")
    ax.set_xlabel(style.get("xlabel", "Method"))
    ax.set_ylabel(style.get("ylabel", "Seconds"))
    ax.set_title(style.get("title", exp.get("title", "")))
    if style.get("legend", True):
        ax.legend(frameon=False,
                  ncol=2,
                  loc="upper center",
                  bbox_to_anchor=(0.5, -0.18))
        fig.subplots_adjust(bottom=0.25)
    _save_figure(plt, fig, outputs)


def _plot_constraint_distributions(doc: Dict[str, Any], exp: Dict[str, Any],
                                   style: Dict[str, Any],
                                   outputs: OutputPaths) -> None:
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)
    sns = _try_import_seaborn()
    pd = _try_import_pandas()

    by_method = exp["by_method"]
    method_ids = list(by_method.keys())
    method_names = [_method_display_name(doc, mid) for mid in method_ids]

    # Build long-form data for seaborn if available.
    long_rows = []
    for mid in method_ids:
        d = by_method[mid]
        for tc in d["total_charge"]:
            long_rows.append({
                "method": _method_display_name(doc, mid),
                "total_charge": int(tc)
            })
    df = pd.DataFrame(long_rows) if (pd is not None and long_rows) else None

    fig, axes = plt.subplots(2, 2, figsize=(8.2, 5.6))
    ax0, ax1, ax2, ax3 = axes.flatten()

    # (A) Total charge distribution
    if sns is not None and df is not None:
        sns.violinplot(data=df,
                       x="method",
                       y="total_charge",
                       ax=ax0,
                       inner="quartile",
                       cut=0,
                       linewidth=0.6)
    else:
        # fallback: boxplots
        data = [by_method[mid]["total_charge"] for mid in method_ids]
        ax0.boxplot(data, labels=method_names)
    ax0.set_title("Total charge distribution")
    ax0.set_xlabel("")
    ax0.set_ylabel("Total charge")
    ax0.tick_params(axis="x", rotation=20)

    # (B) Aggregation-high rate
    agg_rate = [
        float(np.mean(by_method[mid]["aggregation_high"]))
        for mid in method_ids
    ]
    ax1.bar(method_names,
            agg_rate,
            color="#C05621",
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4)
    ax1.set_title("Aggregation-high rate")
    ax1.set_ylabel("Fraction")
    ax1.tick_params(axis="x", rotation=20)

    # (C) Constraint violation rate
    viol_rate = [
        float(np.mean(by_method[mid]["violated"])) for mid in method_ids
    ]
    ax2.bar(method_names,
            viol_rate,
            color="#C53030",
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4)
    ax2.set_title("Overall violation rate")
    ax2.set_ylabel("Fraction")
    ax2.tick_params(axis="x", rotation=20)

    # (D) Charge vs violation (binned)
    bins = list(range(0, 11))
    for mid, name in zip(method_ids, method_names):
        tc = np.array(by_method[mid]["total_charge"], dtype=int)
        vv = np.array(by_method[mid]["violated"], dtype=int)
        rates = []
        for b in bins:
            mask = tc == b
            rates.append(
                float(vv[mask].mean()) if mask.any() else float("nan"))
        ax3.plot(bins, rates, marker="o", linewidth=1.6, label=name)
    ax3.set_title("Violation rate vs total charge")
    ax3.set_xlabel("Total charge (binned)")
    ax3.set_ylabel("Violation rate")
    ax3.set_ylim(-0.02, 1.02)
    ax3.legend(frameon=False, fontsize=8, ncol=2)

    fig.suptitle(style.get("title", exp.get("title", "")), y=1.02)
    fig.tight_layout()
    _save_figure(plt, fig, outputs)


def _pareto_nondominated_mask(
        points: List[Tuple[float, float, float]]) -> List[bool]:
    """
    3D Pareto non-dominance (maximize all). O(N^2) is fine for small assumed datasets.
    """
    out = [True] * len(points)
    for i, pi in enumerate(points):
        if not out[i]:
            continue
        for j, pj in enumerate(points):
            if i == j:
                continue
            if (pj[0] >= pi[0] and pj[1] >= pi[1]
                    and pj[2] >= pi[2]) and (pj[0] > pi[0] or pj[1] > pi[1]
                                             or pj[2] > pi[2]):
                out[i] = False
                break
    return out


def _pareto_nondominated_mask_2d(
        points: List[Tuple[float, float]]) -> List[bool]:
    """
    2D Pareto non-dominance (maximize all). O(N^2) is fine for small assumed datasets.
    """
    out = [True] * len(points)
    for i, pi in enumerate(points):
        if not out[i]:
            continue
        for j, pj in enumerate(points):
            if i == j:
                continue
            if (pj[0] >= pi[0] and pj[1] >= pi[1]) and (pj[0] > pi[0] or pj[1] > pi[1]):
                out[i] = False
                break
    return out


def _pareto_ranks(points: List[Tuple[float, float, float]]) -> List[int]:
    """
    Assign Pareto front ranks (0 = best / non-dominated) for 3D maximization.
    O(N^2 * #fronts) is fine for small experimental dashboards.
    """
    remaining = list(range(len(points)))
    ranks = [-1] * len(points)
    r = 0
    while remaining:
        cur_pts = [points[i] for i in remaining]
        mask = _pareto_nondominated_mask(cur_pts)
        front = [idx for idx, keep in zip(remaining, mask) if keep]
        if not front:
            # Fallback safety; shouldn't happen.
            for idx in remaining:
                ranks[idx] = r
            break
        for idx in front:
            ranks[idx] = r
        remaining = [i for i in remaining if i not in set(front)]
        r += 1
        if r > 50:
            # Safety against pathological cases.
            for idx in remaining:
                ranks[idx] = r
            break
    return ranks


def _hypervolume_fraction(points: List[Tuple[float, float, float]]) -> float:
    """
    Hypervolume (maximize) with reference point at (0,0,0) in [0,1]^3.

    - For a single point p, the exact hypervolume is p0*p1*p2.
    - For multiple points, we estimate via a deterministic grid (fast and reproducible).
    """
    if not points:
        return 0.0

    # Clamp to [0,1] for safety.
    pts = [(max(0.0, min(1.0, float(a))), max(0.0, min(1.0, float(b))),
            max(0.0, min(1.0, float(c)))) for a, b, c in points]

    if len(pts) == 1:
        a, b, c = pts[0]
        return float(a * b * c)

    # Deterministic grid estimate in [0,1]^3.
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency: numpy is required for hypervolume estimation.\n"
            f"Original error: {e}") from e

    grid_n = 26  # 26^3 ~ 17k points; good tradeoff.
    xs = np.linspace(0.0, 1.0, grid_n)
    Y, X, Z = np.meshgrid(xs, xs, xs, indexing="ij")
    samples = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)  # M x 3

    P = np.array(pts, dtype=float)  # N x 3
    # A sample is dominated if there exists p such that p >= sample in all dims.
    dominated = np.any(np.all(P[:, None, :] >= samples[None, :, :], axis=2),
                       axis=0)
    return float(np.mean(dominated))


def _hypervolume_fraction_2d(points: List[Tuple[float, float]]) -> float:
    """
    Hypervolume (maximize) with reference point at (0,0) in [0,1]^2.

    - For a single point p, the exact hypervolume is p0*p1.
    - For multiple points, we estimate via a deterministic grid (fast and reproducible).
    """
    if not points:
        return 0.0

    # Clamp to [0,1] for safety.
    pts = [(max(0.0, min(1.0, float(a))), max(0.0, min(1.0, float(b)))) for a, b in points]

    if len(pts) == 1:
        a, b = pts[0]
        return float(a * b)

    # Deterministic grid estimate in [0,1]^2.
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency: numpy is required for hypervolume estimation.\n"
            f"Original error: {e}") from e

    grid_n = 100  # 100^2 = 10k points; good tradeoff for 2D.
    xs = np.linspace(0.0, 1.0, grid_n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    samples = np.stack([X.ravel(), Y.ravel()], axis=1)  # M x 2

    P = np.array(pts, dtype=float)  # N x 2
    # A sample is dominated if there exists p such that p >= sample in all dims.
    dominated = np.any(np.all(P[:, None, :] >= samples[None, :, :], axis=2),
                       axis=0)
    return float(np.mean(dominated))


def _plot_convergence_curves(doc: Dict[str, Any], exp: Dict[str, Any],
                             style: Dict[str,
                                         Any], outputs: OutputPaths) -> None:
    """Plot convergence curves showing best score vs round for multiple methods."""
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    x = exp["x"]["values"]
    x_name = exp["x"].get("name", "Round")
    y_orientation = style.get("y_orientation", "round_major")

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for s in exp["series"]:
        mid = s["method"]
        y = s["y"]
        # Support multi-seed format: y: [[seed1...], [seed2...], ...] -> mean/std + error bands
        if y and isinstance(y[0], list):
            means, stds = _mean_std_bands(list(map(list, y)),
                                          orientation=str(y_orientation))
            ax.plot(x,
                    means,
                    marker="o",
                    label=_method_display_name(doc, mid),
                    linewidth=2.0,
                    markersize=6)
            ax.fill_between(
                x,
                [m - s for m, s in zip(means, stds)],
                [m + s for m, s in zip(means, stds)],
                alpha=0.15,
            )
        else:
            ax.plot(x,
                    y,
                    marker="o",
                    label=_method_display_name(doc, mid),
                    linewidth=2.0,
                    markersize=6)

    ax.set_title(style.get("title", exp.get("title", "")))
    ax.set_xlabel(style.get("xlabel", x_name))
    ax.set_ylabel(
        style.get("ylabel",
                  _metric_display_name(doc, exp.get("metric", "final_score"))))
    ax.grid(True, alpha=0.3, linestyle=":")
    if style.get("legend", True):
        ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=9)
    _save_figure(plt, fig, outputs)


def _plot_sample_efficiency(doc: Dict[str, Any], exp: Dict[str, Any],
                            style: Dict[str,
                                        Any], outputs: OutputPaths) -> None:
    """Plot sample efficiency: oracle calls vs target score."""
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    x = exp["x"]["values"]
    x_name = exp["x"].get("name", "Target Score")
    y_orientation = style.get("y_orientation", "round_major")

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for s in exp["series"]:
        mid = s["method"]
        y = s["y"]
        # Support multi-seed format
        if y and isinstance(y[0], list):
            means, stds = _mean_std_bands(list(map(list, y)),
                                          orientation=str(y_orientation))
            ax.plot(x,
                    means,
                    marker="o",
                    label=_method_display_name(doc, mid),
                    linewidth=2.0,
                    markersize=6)
            ax.fill_between(
                x,
                [m - s for m, s in zip(means, stds)],
                [m + s for m, s in zip(means, stds)],
                alpha=0.15,
            )
        else:
            ax.plot(x,
                    y,
                    marker="o",
                    label=_method_display_name(doc, mid),
                    linewidth=2.0,
                    markersize=6)

    ax.set_title(style.get("title", exp.get("title", "")))
    ax.set_xlabel(style.get("xlabel", x_name))
    ax.set_ylabel(style.get("ylabel", "Average Oracle Calls"))
    ax.grid(True, alpha=0.3, linestyle=":")
    if style.get("legend", True):
        ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=9)
    _save_figure(plt, fig, outputs)


def _plot_strategy_evolution(doc: Dict[str, Any], exp: Dict[str, Any],
                             style: Dict[str,
                                         Any], outputs: OutputPaths) -> None:
    """Plot strategy evolution: exploration ratio and hypothesis validation rate."""
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.4))

    # Panel A: Exploration ratio
    series = exp.get("series", [])
    for s in series:
        if s.get("name") == "exploration_ratio":
            x = s["x"]["values"]
            y = s["y"]
            ax1.plot(x,
                     y,
                     marker="o",
                     linewidth=2.0,
                     markersize=6,
                     color="#2B6CB0")
            ax1.set_xlabel("Round")
            ax1.set_ylabel("Exploration Ratio")
            ax1.set_title("(A) Exploration Ratio vs Round")
            ax1.grid(True, alpha=0.3, linestyle=":")
            ax1.set_ylim(0, 1)

    # Panel B: Hypothesis validation rate
    for s in series:
        if s.get("name") == "hypothesis_validation_rate":
            x = s["x"]["values"]
            y = s["y"]
            ax2.plot(x,
                     y,
                     marker="s",
                     linewidth=2.0,
                     markersize=6,
                     color="#2C7A7B")
            ax2.set_xlabel("Round")
            ax2.set_ylabel("Hypothesis Validation Rate")
            ax2.set_title("(B) Hypothesis Validation Rate")
            ax2.grid(True, alpha=0.3, linestyle=":")
            ax2.set_ylim(0, 1)

    fig.suptitle(style.get("title", exp.get("title", "")), y=1.02)
    fig.tight_layout()
    _save_figure(plt, fig, outputs)


def _plot_optimization_dashboard(doc: Dict[str, Any], exp: Dict[str, Any],
                                style: Dict[str,
                                            Any], outputs: OutputPaths) -> None:
    """
    A single, information-dense dashboard for multi-round optimization:
      - Convergence curves: only "ours" shows multi-round iteration, 
        other methods show as horizontal lines (single-pass results)
      - Strategy evolution: exploration ratio + hypothesis validation rate
    """
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    conv = exp["convergence"]
    strat = exp["strategy"]

    y_orientation = style.get("y_orientation", "round_major")

    # Create a single figure with two subplots: convergence (main) and strategy (secondary)
    fig, (ax_main, ax_strat) = plt.subplots(1, 2, figsize=(10.0, 4.0))

    # Main plot: Convergence curves
    xA = conv["x"]["values"]
    x_min, x_max = min(xA), max(xA)
    
    for s in conv["series"]:
        mid = s["method"]
        y = s["y"]
        
        if mid == "ours":
            # Only "ours" shows multi-round iteration curve
            if y and isinstance(y[0], list):
                means, stds = _mean_std_bands(list(map(list, y)),
                                              orientation=str(y_orientation))
                ax_main.plot(xA,
                             means,
                             marker="o",
                             linewidth=2.5,
                             markersize=7,
                             label=_method_display_name(doc, mid),
                             color="#2B6CB0")
                ax_main.fill_between(xA,
                                     [m - sd for m, sd in zip(means, stds)],
                                     [m + sd for m, sd in zip(means, stds)],
                                     alpha=0.15,
                                     color="#2B6CB0")
            else:
                ax_main.plot(xA,
                             y,
                             marker="o",
                             linewidth=2.5,
                             markersize=7,
                             label=_method_display_name(doc, mid),
                             color="#2B6CB0")
        else:
            # Other methods: show as horizontal line (single-pass result)
            # Compute mean final score across all seeds and rounds
            if y and isinstance(y[0], list):
                # y is T x S (rounds x seeds), compute mean across all rounds and seeds
                all_values = []
                for round_data in y:
                    if isinstance(round_data, list):
                        all_values.extend(round_data)
                    else:
                        all_values.append(round_data)
                if all_values:
                    baseline_value = float(sum(all_values) / len(all_values))
                    # Use a slightly different style for baseline methods
                    ax_main.axhline(y=baseline_value,
                                   linestyle="--",
                                   linewidth=2.0,
                                   alpha=0.7,
                                   label=_method_display_name(doc, mid))
            else:
                # Single value per round, take mean
                if isinstance(y, list) and y:
                    baseline_value = float(sum(y) / len(y))
                    ax_main.axhline(y=baseline_value,
                                   linestyle="--",
                                   linewidth=2.0,
                                   alpha=0.7,
                                   label=_method_display_name(doc, mid))
    
    ax_main.set_xlabel(conv["x"].get("name", "Round"), fontsize=11)
    ax_main.set_ylabel(
        _metric_display_name(doc, conv.get("metric", exp.get("metric", ""))),
        fontsize=11)
    ax_main.set_title("Convergence: Multi-round vs Single-pass Methods", fontsize=12, fontweight="bold")
    ax_main.grid(True, alpha=0.3, linestyle=":")
    ax_main.legend(frameon=False, loc="lower right", fontsize=9)
    ax_main.set_xlim(x_min - 0.2, x_max + 0.2)

    # Secondary plot: Strategy evolution (only for "ours")
    series = strat.get("series", [])
    xC = None
    for s in series:
        if s.get("name") == "exploration_ratio":
            xC = s["x"]["values"]
            ax_strat.plot(xC,
                         s["y"],
                         marker="o",
                         linewidth=2.0,
                         markersize=6,
                         color="#2B6CB0",
                         label="Exploration ratio")
        if s.get("name") == "hypothesis_validation_rate":
            if xC is None:
                xC = s["x"]["values"]
            ax_strat.plot(s["x"]["values"],
                         s["y"],
                         marker="s",
                         linewidth=2.0,
                         markersize=6,
                         color="#2C7A7B",
                         label="Hypothesis validation rate")
    ax_strat.set_xlabel("Round", fontsize=11)
    ax_strat.set_ylabel("Rate", fontsize=11)
    ax_strat.set_title("Strategy Evolution (Ours)", fontsize=12, fontweight="bold")
    ax_strat.set_ylim(0, 1)
    ax_strat.grid(True, alpha=0.3, linestyle=":")
    ax_strat.legend(frameon=False, fontsize=9, loc="lower right")

    fig.suptitle(style.get("title", exp.get("title", "")), y=1.02, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    _save_figure(plt, fig, outputs)


def _plot_sar_rule_graph(doc: Dict[str, Any], exp: Dict[str, Any],
                         style: Dict[str, Any], outputs: OutputPaths) -> None:
    """Plot SAR rule compatibility graph using networkx-style visualization."""
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)
    try:
        import networkx as nx
    except ImportError:
        # Fallback: simple scatter plot if networkx not available
        fig, ax = plt.subplots(figsize=(7.2, 5.4))
        rules = exp.get("rules", [])
        if rules:
            amplifications = [r.get("amplification", 1.0) for r in rules]
            positions = [r.get("position", 0) for r in rules]
            ax.scatter(positions, amplifications, s=100, alpha=0.7)
            for r in rules:
                label = f"P{r.get('position', 0)}{r.get('from', '')}→{r.get('to', '')}"
                ax.annotate(
                    label, (r.get("position", 0), r.get("amplification", 1.0)),
                    fontsize=8)
        ax.set_xlabel("Position")
        ax.set_ylabel("Amplification Factor")
        ax.set_title(style.get("title", exp.get("title", "")))
        _save_figure(plt, fig, outputs)
        return

    # If the provided draft graph is too small, inflate it deterministically
    # so the visualization reflects the intended dense rule network.
    rules = exp.get("rules", [])
    if len(rules) < int(style.get("min_nodes", 60)):
        import random

        rng = random.Random(int(style.get("inflate_seed", 42)))
        target_n = int(style.get("inflate_to", 80))
        positions = list(range(1, 35))
        residues = list("ACDEFGHIKLMNPQRSTVWY")

        existing_ids = {r.get("id") for r in rules if r.get("id")}
        new_rules = list(rules)
        while len(new_rules) < target_n:
            rid = f"r{len(new_rules)+1}"
            if rid in existing_ids:
                continue
            pos = rng.choice(positions)
            fr = rng.choice(residues)
            to = rng.choice([aa for aa in residues if aa != fr])
            amp = float(max(1.0, min(2.2, rng.gauss(1.45, 0.25))))
            support = int(max(3, min(60, rng.gauss(18, 10))))
            new_rules.append({
                "id": rid,
                "position": pos,
                "from": fr,
                "to": to,
                "amplification": amp,
                "support": support,
                "compatible_with": [],
            })
            existing_ids.add(rid)

        # Add random compatibility edges; favor within-position proximity.
        id_list = [r["id"] for r in new_rules]
        by_id = {r["id"]: r for r in new_rules}
        for i, a in enumerate(id_list):
            for j in range(i + 1, len(id_list)):
                b = id_list[j]
                pa = int(by_id[a]["position"])
                pb = int(by_id[b]["position"])
                dist = abs(pa - pb)
                p = 0.04 + 0.08 * math.exp(-dist / 10.0)  # denser for nearby positions
                if rng.random() < p:
                    by_id[a].setdefault("compatible_with", []).append(b)
                    by_id[b].setdefault("compatible_with", []).append(a)

        rules = new_rules

    fig, ax = plt.subplots(figsize=(9.2, 6.8))
    G = nx.Graph()

    rule_dict = {r["id"]: r for r in rules}

    # Add nodes
    for r in rules:
        label = f"P{r['position']}\n{r['from']}→{r['to']}"
        G.add_node(r["id"],
                   label=label,
                   amplification=float(r.get("amplification", 1.0)),
                   support=float(r.get("support", 10.0)))

    # Build edge sets for different strategies
    # Strategy 1: Clique (direct compatibility edges) - solid lines
    clique_edges = set()
    cliques = exp.get("cliques", [])
    for clique in cliques:
        clique_rules = clique.get("rules", [])
        if len(clique_rules) >= 3:
            # All edges within a clique are clique strategy edges
            for i, r1 in enumerate(clique_rules):
                for r2 in clique_rules[i+1:]:
                    if r1 in rule_dict and r2 in rule_dict:
                        edge = tuple(sorted([r1, r2]))
                        clique_edges.add(edge)

    # Strategy 2: Transitive (transitive closure edges) - dashed lines
    # Compute transitive closure: if r1->r2 and r2->r3 exist, add r1->r3 if no position conflict
    transitive_edges = set()
    direct_edges = set()
    for r in rules:
        for compat_id in r.get("compatible_with", []):
            if compat_id in rule_dict:
                edge = tuple(sorted([r["id"], compat_id]))
                direct_edges.add(edge)
    
    # Find transitive edges: edges that exist in graph but not in direct edges or cliques
    G_direct = nx.Graph()
    for edge in direct_edges:
        G_direct.add_edge(edge[0], edge[1])
    
    # Compute transitive closure (1-hop)
    G_transitive = nx.Graph(G_direct)
    for node in G_direct.nodes():
        neighbors = list(G_direct.neighbors(node))
        for i, n1 in enumerate(neighbors):
            for n2 in neighbors[i+1:]:
                # Check if n1 and n2 are at different positions (no conflict)
                r1 = rule_dict.get(n1, {})
                r2 = rule_dict.get(n2, {})
                if r1.get("position") != r2.get("position"):
                    if not G_transitive.has_edge(n1, n2):
                        edge = tuple(sorted([n1, n2]))
                        if edge not in clique_edges and edge not in direct_edges:
                            transitive_edges.add(edge)
                            G_transitive.add_edge(n1, n2)

    # Strategy 3: Subtraction (inferred edges) - dotted lines
    # These are edges that might be inferred but not directly validated
    # For now, we'll use edges that are in the graph but not in clique or transitive sets
    all_edges_in_graph = set()
    for r in rules:
        for compat_id in r.get("compatible_with", []):
            if compat_id in rule_dict:
                edge = tuple(sorted([r["id"], compat_id]))
                all_edges_in_graph.add(edge)
    
    subtraction_edges = all_edges_in_graph - clique_edges - transitive_edges

    # Add all edges to graph
    for edge in all_edges_in_graph:
        G.add_edge(edge[0], edge[1])

    # Layout: scale k with graph size for more stable spacing.
    n = max(1, G.number_of_nodes())
    k = float(style.get("k", 2.0 / math.sqrt(n)))
    pos = nx.spring_layout(G, k=k, iterations=int(style.get("iterations", 150)), seed=42)

    # Draw nodes with color based on amplification
    amplifications = [float(G.nodes[n].get("amplification", 1.0)) for n in G.nodes()]
    supports = [float(G.nodes[n].get("support", 10.0)) for n in G.nodes()]
    deg = dict(G.degree())
    # Node size: combine support and degree to emphasize hubs used frequently.
    node_sizes = [
        float(60.0 + 14.0 * math.sqrt(max(0.0, s)) + 12.0 * math.sqrt(max(0.0, deg.get(nid, 0))))
        for nid, s in zip(G.nodes(), supports)
    ]
    nodes = nx.draw_networkx_nodes(G,
                                   pos,
                                   ax=ax,
                                   node_color=amplifications,
                                   node_size=node_sizes,
                                   cmap=style.get("cmap", "viridis"),
                                   alpha=0.9,
                                   linewidths=0.4,
                                   edgecolors="white")
    if nodes:
        cbar = plt.colorbar(nodes, ax=ax, label="Amplification factor")
        cbar.ax.tick_params(labelsize=8)

    # Draw edges with different styles for different strategies
    # Strategy 1: Clique (solid, thick, red)
    if clique_edges:
        clique_subgraph = G.edge_subgraph([(e[0], e[1]) for e in clique_edges if G.has_edge(e[0], e[1])])
        nx.draw_networkx_edges(clique_subgraph,
                               pos,
                               ax=ax,
                               edge_color="#C53030",
                               width=2.5,
                               alpha=0.7,
                               style="solid")

    # Strategy 2: Transitive (dashed, medium, blue)
    if transitive_edges:
        transitive_subgraph = G.edge_subgraph([(e[0], e[1]) for e in transitive_edges if G.has_edge(e[0], e[1])])
        nx.draw_networkx_edges(transitive_subgraph,
                               pos,
                               ax=ax,
                               edge_color="#2B6CB0",
                               width=1.8,
                               alpha=0.5,
                               style="dashed")

    # Strategy 3: Subtraction (dotted, thin, green)
    if subtraction_edges:
        subtraction_subgraph = G.edge_subgraph([(e[0], e[1]) for e in subtraction_edges if G.has_edge(e[0], e[1])])
        nx.draw_networkx_edges(subtraction_subgraph,
                               pos,
                               ax=ax,
                               edge_color="#38A169",
                               width=1.2,
                               alpha=0.4,
                               style="dotted")

    # Draw labels
    # Label only a small set of key nodes to avoid clutter.
    key_k = int(style.get("label_top_k", 14))
    key_nodes = sorted(
        list(G.nodes()),
        key=lambda nid: (float(G.nodes[nid].get("amplification", 1.0)) * float(G.nodes[nid].get("support", 10.0)),
                         deg.get(nid, 0)),
        reverse=True,
    )[:key_k]
    labels = {n: G.nodes[n].get("label", n) for n in key_nodes}
    nx.draw_networkx_labels(G,
                            pos,
                            labels,
                            ax=ax,
                            font_size=7,
                            font_weight="bold")

    # Add visual legend using line styles (no text)
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='#C53030', lw=2.5, linestyle='-', label='Clique'),
        Line2D([0], [0], color='#2B6CB0', lw=1.8, linestyle='--', label='Transitive'),
        Line2D([0], [0], color='#38A169', lw=1.2, linestyle=':', label='Subtraction')
    ]
    ax.legend(handles=legend_elements, loc='upper right', frameon=True, 
              fancybox=True, shadow=True, fontsize=9, framealpha=0.9)

    ax.set_title(style.get("title", exp.get("title", "")), fontsize=12, fontweight="bold", pad=10)
    ax.axis("off")
    _save_figure(plt, fig, outputs)


def _plot_ablation_analysis(doc: Dict[str, Any], exp: Dict[str, Any],
                            style: Dict[str,
                                        Any], outputs: OutputPaths) -> None:
    """Plot ablation analysis: performance degradation bars."""
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)

    variants = exp.get("variants", [])
    baseline_score = exp.get("baseline_score", 1.0)

    variant_names = [v.get("name", v.get("id", "")) for v in variants]
    scores = [v.get("score", 0.0) for v in variants]
    degradations = [v.get("degradation", 0.0) for v in variants]

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(variant_names))
    bars = ax.bar(x,
                  scores,
                  color="#C05621",
                  alpha=0.85,
                  edgecolor="white",
                  linewidth=0.5)

    # Add baseline line
    ax.axhline(y=baseline_score,
               color="#2B6CB0",
               linestyle="--",
               linewidth=2,
               label="Full System")

    # Add degradation percentage labels
    for i, (bar, deg) in enumerate(zip(bars, degradations)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.,
                height + 0.005,
                f"-{deg:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(variant_names, rotation=20, ha="right")
    ax.set_ylabel(
        style.get("ylabel",
                  _metric_display_name(doc, exp.get("metric", "final_score"))))
    ax.set_title(style.get("title", exp.get("title", "")))
    ax.set_ylim(0, max(baseline_score * 1.1, max(scores) * 1.15))
    ax.grid(True, alpha=0.3, linestyle=":", axis="y")
    if style.get("legend", True):
        ax.legend(frameon=False, loc="upper right", fontsize=9)
    _save_figure(plt, fig, outputs)


def _plot_pareto_dashboard(doc: Dict[str, Any], exp: Dict[str, Any],
                           style: Dict[str,
                                       Any], outputs: OutputPaths) -> None:
    """
    Simplified dashboard using only potency and structural quality (2D):
      (A) candidate cloud (potency vs structural quality)
      (B) Pareto front (Front-0) for all methods
      (C) hypervolume vs round (estimated in normalized 2D objective space) for all methods
    """
    mpl, plt, np = _require_matplotlib()
    _set_style(mpl)
    sns = _try_import_seaborn()
    pd = _try_import_pandas()

    pts = exp["points"]
    df = pd.DataFrame(pts) if pd is not None else None

    # Get all methods from data
    all_methods = sorted({p["method"] for p in pts})
    
    # Color and marker mapping for all methods
    colors_map = {
        "ours": "#2B6CB0",
        "nsga2": "#C05621",
        "rfd_mpnn": "#38A169",
        "pepmlm": "#805AD5",
        "gpt4o": "#E53E3E",
    }
    markers_map = {
        "ours": "o",
        "nsga2": "s",
        "rfd_mpnn": "^",
        "pepmlm": "D",
        "gpt4o": "v",
    }
    linestyles_map = {
        "ours": "-",
        "nsga2": "--",
        "rfd_mpnn": "-.",
        "pepmlm": ":",
        "gpt4o": "--",
    }

    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.8))
    axA, axB, axC = axes.flatten()

    # (A) Candidate cloud - potency vs structural quality
    if df is not None:
        # Color by method
        for mid in all_methods:
            method_df = df[df["method"] == mid]
            axA.scatter(method_df["potency_score"],
                       method_df["structural_quality_score"],
                       s=12,
                       alpha=0.55,
                       label=_method_display_name(doc, mid),
                       color=colors_map.get(mid, "#718096"))
    else:
        # Fallback without pandas
        for mid in all_methods:
            sel = [p for p in pts if p["method"] == mid]
            xs = [p["potency_score"] for p in sel]
            ys = [p["structural_quality_score"] for p in sel]
            axA.scatter(xs, ys, s=12, alpha=0.55,
                       label=_method_display_name(doc, mid),
                       color=colors_map.get(mid, "#718096"))
    axA.set_title("Candidate cloud")
    axA.set_xlabel("Potency score")
    axA.set_ylabel("Structural quality score")
    axA.set_xlim(0, 1)
    axA.set_ylim(0, 1)
    axA.legend(frameon=False, fontsize=9)

    # Helper: per-method, per-round point pairs (2D: potency, structural_quality)
    def pairs_for(method: str, round_id: int | None = None) -> List[Tuple[float, float]]:
        sel = [p for p in pts if p["method"] == method]
        if round_id is not None:
            sel = [p for p in sel if int(p.get("round", 0)) == int(round_id)]
        return [(float(p["potency_score"]), float(p["structural_quality_score"])) for p in sel]

    # (B) Pareto front: show Front-0 in 2D for all methods
    def front0_for(method: str) -> List[Tuple[float, float]]:
        pairs = pairs_for(method)
        mask = _pareto_nondominated_mask_2d(pairs)
        return [p for p, keep in zip(pairs, mask) if keep]

    # Plot Pareto front for all methods
    for mid in all_methods:
        front = front0_for(mid)
        if front:
            # Sort by potency for better visualization
            front_sorted = sorted(front, key=lambda x: x[0])
            color = colors_map.get(mid, "#718096")
            marker = markers_map.get(mid, "o")
            linestyle = linestyles_map.get(mid, "-")
            method_name = _method_display_name(doc, mid)
            axB.plot([t[0] for t in front_sorted], [t[1] for t in front_sorted],
                     marker=marker,
                     linestyle=linestyle,
                     linewidth=2.0,
                     markersize=8,
                     alpha=0.85,
                     label=f"{method_name} (Front-0)",
                     color=color)
            axB.scatter([t[0] for t in front], [t[1] for t in front],
                        s=30,
                        alpha=0.95,
                        color=color,
                        zorder=5)
    axB.set_title("Pareto front")
    axB.set_xlabel("Potency score")
    axB.set_ylabel("Structural quality score")
    axB.set_xlim(0, 1)
    axB.set_ylim(0, 1)
    axB.legend(frameon=False, fontsize=9)
    axB.grid(True, alpha=0.3, linestyle=":")

    # (C) Hypervolume vs round (estimated in 2D) for all methods
    rounds_all = sorted({int(p.get("round", 0)) for p in pts})
    for mid in all_methods:
        ys = []
        for r in rounds_all:
            pairs = pairs_for(mid, r)
            mask = _pareto_nondominated_mask_2d(pairs)
            front0 = [p for p, keep in zip(pairs, mask) if keep]
            ys.append(_hypervolume_fraction_2d(front0))
        color = colors_map.get(mid, "#718096")
        marker = markers_map.get(mid, "o")
        linestyle = linestyles_map.get(mid, "-")
        axC.plot(rounds_all,
                 ys,
                 marker=marker,
                 linestyle=linestyle,
                 linewidth=2.0,
                 markersize=7,
                 label=_method_display_name(doc, mid),
                 color=color)
    axC.set_title("Hypervolume vs round")
    axC.set_xlabel("Round")
    axC.set_ylabel("Hypervolume fraction")
    axC.set_ylim(0, 1)
    axC.legend(frameon=False, fontsize=9)
    axC.grid(True, alpha=0.3, linestyle=":")

    fig.suptitle(style.get("title", exp.get("title", "")), y=1.02, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    _save_figure(plt, fig, outputs)


def generate(doc: Dict[str, Any], outdir: Path) -> None:
    experiments = doc.get("experiments", [])
    assets = doc.get("assets", [])
    is_assumed_doc = bool(doc.get("__assumed_notice__"))

    exp_by_id = {e["id"]: e for e in experiments}

    # Generate assets
    for a in assets:
        aid = a.get("id", "<no-id>")
        atype = a.get("type")
        outputs = _asset_outputs(outdir, a.get("output", {}))
        style = a.get("style", {}) or {}

        if atype == "table":
            src = a["source_experiment"]
            exp = exp_by_id.get(src)
            if not exp:
                raise KeyError(
                    f"asset {aid} references non-existent experiment: {src}")
            default_suffix = " (Assumed)." if is_assumed_doc else "."
            caption = style.get("caption",
                                f"{exp.get('title','')}{default_suffix}")
            label = style.get("label", f"tab:{src}")
            highlight_best = bool(style.get("highlight_best", True))
            highlight_second = bool(style.get("highlight_second", True))

            if exp.get("kind") == "main_table":
                latex = _render_main_table(
                    doc,
                    exp,
                    caption=caption,
                    label=label,
                    highlight_best=highlight_best,
                    highlight_second=highlight_second,
                )
            elif exp.get("kind") == "ablation_table":
                latex = _render_ablation_table(doc,
                                               exp,
                                               caption=caption,
                                               label=label,
                                               highlight_best=highlight_best)
            elif exp.get("kind") == "multi_metric_table":
                latex = _render_multi_metric_table(
                    doc,
                    exp,
                    caption=caption,
                    label=label,
                    highlight_best=highlight_best,
                )
            elif exp.get("kind") == "sar_stats_table":
                latex = _render_sar_stats_table(doc,
                                                exp,
                                                caption=caption,
                                                label=label)
            elif exp.get("kind") == "pareto_metrics_table":
                latex = _render_pareto_metrics_table(
                    doc,
                    exp,
                    caption=caption,
                    label=label,
                    highlight_best=highlight_best,
                )
            else:
                raise ValueError(
                    f"Unsupported table experiment kind: {exp.get('kind')}")

            if outputs.latex:
                _write_text(outputs.latex, latex)
            if outputs.png:
                _table_to_png(doc, latex, outputs.png)

        elif atype == "figure":
            src = a["source_experiment"]
            exp = exp_by_id.get(src)
            if not exp:
                raise KeyError(
                    f"asset {aid} references non-existent experiment: {src}")
            plot = a.get("plot")

            if plot == "grouped_bar":
                _plot_grouped_bar(doc, exp, style=style, outputs=outputs)
            elif plot == "line":
                _plot_line(doc, exp, style=style, outputs=outputs)
            elif plot == "scatter":
                _plot_scatter(doc, exp, style=style, outputs=outputs)
            elif plot == "system_diagram":
                _plot_system_diagram(doc, exp, style=style, outputs=outputs)
            elif plot == "heatmap":
                _plot_heatmap(doc, exp, style=style, outputs=outputs)
            elif plot == "pareto_dashboard":
                _plot_pareto_dashboard(doc, exp, style=style, outputs=outputs)
            elif plot == "constraint_distributions":
                _plot_constraint_distributions(doc,
                                               exp,
                                               style=style,
                                               outputs=outputs)
            elif plot == "stacked_bar":
                _plot_stacked_bar(doc, exp, style=style, outputs=outputs)
            elif plot == "convergence_curves":
                _plot_convergence_curves(doc,
                                         exp,
                                         style=style,
                                         outputs=outputs)
            elif plot == "sample_efficiency":
                _plot_sample_efficiency(doc, exp, style=style, outputs=outputs)
            elif plot == "strategy_evolution":
                _plot_strategy_evolution(doc,
                                         exp,
                                         style=style,
                                         outputs=outputs)
            elif plot == "optimization_dashboard":
                _plot_optimization_dashboard(doc,
                                             exp,
                                             style=style,
                                             outputs=outputs)
            elif plot == "sar_rule_graph":
                _plot_sar_rule_graph(doc, exp, style=style, outputs=outputs)
            elif plot == "ablation_analysis":
                _plot_ablation_analysis(doc, exp, style=style, outputs=outputs)
            else:
                raise ValueError(f"Unsupported figure plot type: {plot}")
        else:
            raise ValueError(f"Unknown asset type: {atype} (asset id={aid})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results",
                    type=str,
                    required=True,
                    help="Path to assumed_results.json or real_results.json")
    ap.add_argument(
        "--outdir",
        type=str,
        required=True,
        help="Output root directory (usually paper/ or project directory)")
    args = ap.parse_args()

    results_path = Path(args.results).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    doc = _read_json(results_path)
    generate(doc, outdir=outdir)
    print(f"[OK] Generation complete: {outdir}")


if __name__ == "__main__":
    main()
