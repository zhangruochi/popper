from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from local_agent.analysis.pareto_dashboard import make_pareto_dashboard_figure


@dataclass(frozen=True)
class ParetoDashboardSpec:
    objectives: list[str]
    round_col: str = "round"
    pareto_rank_col: str = "pareto_rank"
    score_col: str = "final_score"


def _dominates_max(a: np.ndarray, b: np.ndarray) -> bool:
    """
    Returns True if a dominates b under maximization.
    a dominates b if a >= b in all dims and a > b in at least one dim.
    """
    return bool(np.all(a >= b) and np.any(a > b))


def pareto_ranks_max(points: np.ndarray) -> np.ndarray:
    """
    Compute Pareto ranks via fast non-dominated sorting (O(N^2 * D), small-N friendly).

    - points: (N, D) objective values, all maximized.
    - returns: (N,) integer ranks (0 is best/non-dominated front).
    """
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2:
        raise ValueError(f"points must be 2D array; got {pts.ndim}D")
    n = pts.shape[0]
    if n == 0:
        return np.zeros((0,), dtype=int)

    dominates: list[list[int]] = [[] for _ in range(n)]
    dominated_count = np.zeros(n, dtype=int)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if _dominates_max(pts[i], pts[j]):
                dominates[i].append(j)
            elif _dominates_max(pts[j], pts[i]):
                dominated_count[i] += 1

    ranks = np.full(n, -1, dtype=int)
    current_front = [i for i in range(n) if dominated_count[i] == 0]
    rank = 0
    while current_front:
        next_front: list[int] = []
        for p in current_front:
            ranks[p] = rank
            for q in dominates[p]:
                dominated_count[q] -= 1
                if dominated_count[q] == 0:
                    next_front.append(q)
        rank += 1
        current_front = next_front

    if np.any(ranks < 0):
        # Should never happen, but keep a safe fallback.
        ranks[ranks < 0] = int(np.nanmax(ranks))
    return ranks


def _find_experiment(doc: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    for exp in doc.get("experiments", []) or []:
        if exp.get("id") == experiment_id:
            return exp
    raise KeyError(f"Experiment id={experiment_id} not found in results doc")


def build_pareto_dashboard_df(
    points: Iterable[dict[str, Any]],
    spec: ParetoDashboardSpec,
) -> pd.DataFrame:
    rows = []
    for p in points:
        row: dict[str, Any] = {}
        row[spec.round_col] = int(p[spec.round_col])
        for obj in spec.objectives:
            row[obj] = float(p[obj])
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No points provided for Pareto dashboard")

    # Per-round Pareto ranks (more interpretable than global ranks across rounds).
    pareto_rank = np.zeros(len(df), dtype=int)
    for r, idx in df.groupby(spec.round_col).groups.items():
        pts = df.loc[idx, spec.objectives].to_numpy(dtype=float)
        pareto_rank[idx] = pareto_ranks_max(pts)
    df[spec.pareto_rank_col] = pareto_rank.astype(int)

    # A simple scalar for highlighting in the dashboard panel (used only for top-k emphasis).
    df[spec.score_col] = df[spec.objectives].mean(axis=1)
    return df


def generate_pareto_dashboard_from_results_doc(
    doc: dict[str, Any],
    experiment_id: str,
    out_png: Path,
    out_pdf: Path | None = None,
    title: str = "Pareto Dashboard",
    max_lines_parallel: int = 400,
) -> None:
    exp = _find_experiment(doc, experiment_id=experiment_id)
    objectives = list(exp.get("objectives") or ["potency_score", "structural_quality_score", "developability_score"])
    points = exp.get("points") or []
    spec = ParetoDashboardSpec(objectives=objectives)

    df = build_pareto_dashboard_df(points=points, spec=spec)

    fig = make_pareto_dashboard_figure(
        df=df,
        objectives=objectives,
        round_col=spec.round_col,
        pareto_rank_col=spec.pareto_rank_col,
        score_col=spec.score_col,
        title=title,
        max_lines_parallel=max_lines_parallel,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300)
    if out_pdf is not None:
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_pdf)


