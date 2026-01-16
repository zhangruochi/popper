#!/usr/bin/env python3
"""
Deterministic generator for assumed benchmark results (placeholder numbers for paper drafting).

Key design goals:
- Single source of truth for ALL assumed numbers used in paper figures/tables.
- Fully deterministic given a seed (reproducible across runs).
- Schema aligns with generate_plots_table.py expectations.
- Covers Experiment 1/2/3 as defined in benchmark_plan.md.

Usage:
  python generate_assumed_benchmark_results.py --seed 42 --outfile assumed_results.json
  # or programmatically:
  from generate_assumed_benchmark_results import build_assumed_benchmark_results_doc
  doc = build_assumed_benchmark_results_doc(seed=42)
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Configuration constants (align with benchmark_plan.md)
# ---------------------------------------------------------------------------

METHODS = [
    {"id": "ours", "name": "Pareto-guided multi-round agentic optimization", "short": "Ours"},
    {"id": "rfd_mpnn", "name": "RFDiffusion + ProteinMPNN", "short": "RFD+MPNN", "family": "Structure"},
    {"id": "pepmlm", "name": "PepMLM (Masked LM mutation sampling)", "short": "PepMLM", "family": "Sequence"},
    {"id": "nsga2", "name": "NSGA-II on unified oracle", "short": "NSGA-II", "family": "Heuristic"},
    {"id": "qwen3", "name": "Direct Qwen3-32B (single-pass)", "short": "Qwen3-32B", "family": "LLM"},
    {"id": "deepseek", "name": "Direct DeepSeek-V3.2 (single-pass)", "short": "DeepSeek-V3.2", "family": "LLM"},
]

DATASETS = [
    {"id": "scenario_a", "name": "Scenario A (Sparse)", "task": "optimization", "notes": "Sparse SAR (e.g., 1F47, 3EQS, 3EQY, 3LNZ, 3RF3, 4CPA, 4J2L, 5UML, 5UMM, 5XCO)"},
    {"id": "scenario_b", "name": "Scenario B (Rich)", "task": "optimization", "notes": "Rich SAR (e.g., PDZ, Bcl-2, GLP-1, MDM2, PD-L1)"},
    {"id": "scenario_c", "name": "Scenario C (Cyclic)", "task": "optimization", "notes": "Cyclic peptide case study (Krpep-2d_WT)"},
]

METRICS = [
    {"id": "final_score", "name": "Final Score", "direction": "higher_is_better", "format": "float3"},
    {"id": "hr_at_k", "name": "HR@K", "direction": "higher_is_better", "format": "float3"},
    {"id": "sar_violation", "name": "SAR Violation Rate (%)", "direction": "lower_is_better", "format": "float3"},
    {"id": "constraint_satisfaction", "name": "Constraint Sat. Rate (%)", "direction": "higher_is_better", "format": "float3"},
    {"id": "hypervolume", "name": "Hypervolume", "direction": "higher_is_better", "format": "float3"},
    {"id": "plddt", "name": "pLDDT", "direction": "higher_is_better", "format": "float3"},
    {"id": "iptm", "name": "iPTM", "direction": "higher_is_better", "format": "float3"},
    {"id": "delta_g", "name": "Interface $\\Delta G$", "direction": "lower_is_better", "format": "float3"},
    {"id": "runtime", "name": "Runtime (s)", "direction": "lower_is_better", "format": "float2"},
]

SEEDS = [0, 1, 2, 3, 4]

# Per-target identifiers (for "list every dataset" requirement)
SCENARIO_A_TARGETS = [
    "1F47",
    "1GL0",
    "1GL1",
    "1KNE",
    "1SMF",
    "3EQS",
    "3EQY",
    "3LNZ",
    "3RF3",
    "4CPA",
    "4J2L",
    "5UML",
    "5UMM",
    "5XCO",
]

SCENARIO_B_TARGETS = ["PDZ", "Bcl-2", "GLP-1", "MDM2", "PD-L1"]

SCENARIO_C_TARGETS = ["Krpep-2d"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rand_around(rng: random.Random, center: float, spread: float = 0.02) -> float:
    return round(center + rng.uniform(-spread, spread), 4)


def _generate_seed_values(rng: random.Random, center: float, n: int = 5, spread: float = 0.01) -> List[float]:
    return [round(center + rng.uniform(-spread, spread), 4) for _ in range(n)]


# ---------------------------------------------------------------------------
# Experiment builders
# ---------------------------------------------------------------------------


def _build_main_results_experiment(rng: random.Random) -> Dict[str, Any]:
    """Experiment 1: Main results (final_score across scenarios)."""
    # Assumed centers per (dataset, method) — Ours always best
    centers = {
        ("scenario_a", "ours"): 0.88,
        ("scenario_a", "rfd_mpnn"): 0.81,
        ("scenario_a", "pepmlm"): 0.78,
        ("scenario_a", "nsga2"): 0.76,
        ("scenario_a", "qwen3"): 0.738,
        ("scenario_a", "deepseek"): 0.742,
        ("scenario_b", "ours"): 0.91,
        ("scenario_b", "rfd_mpnn"): 0.84,
        ("scenario_b", "pepmlm"): 0.82,
        ("scenario_b", "nsga2"): 0.79,
        ("scenario_b", "qwen3"): 0.745,
        ("scenario_b", "deepseek"): 0.751,
        ("scenario_c", "ours"): 0.85,
        ("scenario_c", "rfd_mpnn"): 0.79,
        ("scenario_c", "pepmlm"): 0.76,
        ("scenario_c", "nsga2"): 0.73,
        ("scenario_c", "qwen3"): 0.704,
        ("scenario_c", "deepseek"): 0.718,
    }
    values: Dict[str, Dict[str, List[float]]] = {}
    for ds in DATASETS:
        ds_id = ds["id"]
        values[ds_id] = {}
        for m in METHODS:
            mid = m["id"]
            c = centers.get((ds_id, mid), 0.70)
            values[ds_id][mid] = _generate_seed_values(rng, c, n=len(SEEDS), spread=0.012)
    return {
        "id": "main_results",
        "kind": "main_table",
        "title": "Main results: Final Score (Layer 1-3 composite)",
        "datasets": [d["id"] for d in DATASETS],
        "metric": "final_score",
        "methods": [m["id"] for m in METHODS],
        "values": values,
        "notes": "Assumed numbers for drafting.",
    }


def _build_sar_violation_experiment(rng: random.Random) -> Dict[str, Any]:
    """Experiment 1b: SAR Violation Rate (lower is better)."""
    centers = {
        ("scenario_a", "ours"): 0.05,
        ("scenario_a", "rfd_mpnn"): 0.28,
        ("scenario_a", "pepmlm"): 0.22,
        ("scenario_a", "nsga2"): 0.18,
        ("scenario_a", "qwen3"): 0.312,
        ("scenario_a", "deepseek"): 0.295,
        ("scenario_b", "ours"): 0.03,
        ("scenario_b", "rfd_mpnn"): 0.25,
        ("scenario_b", "pepmlm"): 0.19,
        ("scenario_b", "nsga2"): 0.15,
        ("scenario_b", "qwen3"): 0.284,
        ("scenario_b", "deepseek"): 0.267,
    }
    values: Dict[str, Dict[str, List[float]]] = {}
    for ds_id in ["scenario_a", "scenario_b"]:
        values[ds_id] = {}
        for m in METHODS:
            mid = m["id"]
            c = centers.get((ds_id, mid), 0.20)
            values[ds_id][mid] = _generate_seed_values(rng, c, n=len(SEEDS), spread=0.02)
    return {
        "id": "sar_violation",
        "kind": "main_table",
        "title": "SAR Violation Rate (lower is better)",
        "datasets": ["scenario_a", "scenario_b"],
        "metric": "sar_violation",
        "methods": [m["id"] for m in METHODS],
        "values": values,
        "notes": "Assumed.",
    }


def _build_constraint_satisfaction_experiment(rng: random.Random) -> Dict[str, Any]:
    """Experiment 2: Constraint Satisfaction Rate."""
    centers = {
        ("scenario_b", "ours"): 0.92,
        ("scenario_b", "rfd_mpnn"): 0.68,
        ("scenario_b", "pepmlm"): 0.55,
        ("scenario_b", "nsga2"): 0.85,
        ("scenario_b", "qwen3"): 0.492,
        ("scenario_b", "deepseek"): 0.518,
    }
    values: Dict[str, Dict[str, List[float]]] = {}
    for ds_id in ["scenario_b"]:
        values[ds_id] = {}
        for m in METHODS:
            mid = m["id"]
            c = centers.get((ds_id, mid), 0.60)
            values[ds_id][mid] = _generate_seed_values(rng, c, n=len(SEEDS), spread=0.03)
    return {
        "id": "constraint_satisfaction",
        "kind": "main_table",
        "title": "Constraint Satisfaction Rate",
        "datasets": ["scenario_b"],
        "metric": "constraint_satisfaction",
        "methods": [m["id"] for m in METHODS],
        "values": values,
        "notes": "Assumed.",
    }


def _build_structure_validity_experiment(rng: random.Random) -> Dict[str, Any]:
    """Experiment 3: Structural validity (pLDDT, iPTM, Delta G)."""
    metrics = ["plddt", "iptm", "delta_g"]
    centers = {
        ("scenario_b", "ours", "plddt"): 0.82,
        ("scenario_b", "rfd_mpnn", "plddt"): 0.88,
        ("scenario_b", "pepmlm", "plddt"): 0.72,
        ("scenario_b", "nsga2", "plddt"): 0.75,
        ("scenario_b", "qwen3", "plddt"): 0.612,
        ("scenario_b", "deepseek", "plddt"): 0.645,
        ("scenario_b", "ours", "iptm"): 0.78,
        ("scenario_b", "rfd_mpnn", "iptm"): 0.84,
        ("scenario_b", "pepmlm", "iptm"): 0.65,
        ("scenario_b", "nsga2", "iptm"): 0.68,
        ("scenario_b", "qwen3", "iptm"): 0.542,
        ("scenario_b", "deepseek", "iptm"): 0.584,
        ("scenario_b", "ours", "delta_g"): -12.5,
        ("scenario_b", "rfd_mpnn", "delta_g"): -11.8,
        ("scenario_b", "pepmlm", "delta_g"): -9.5,
        ("scenario_b", "nsga2", "delta_g"): -10.2,
        ("scenario_b", "qwen3", "delta_g"): -7.824,
        ("scenario_b", "deepseek", "delta_g"): -8.156,
    }
    values: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    ds_id = "scenario_b"
    values[ds_id] = {}
    for m in METHODS:
        mid = m["id"]
        values[ds_id][mid] = {}
        for met in metrics:
            c = centers.get((ds_id, mid, met), 0.70)
            spread = 0.02 if met != "delta_g" else 0.5
            values[ds_id][mid][met] = _generate_seed_values(rng, c, n=len(SEEDS), spread=spread)
            
    return {
        "id": "structure_validity",
        "kind": "multi_metric_table",
        "title": "Structural and Energetic Validity",
        "datasets": ["scenario_b"],
        "metrics": metrics,
        "methods": [m["id"] for m in METHODS],
        "values": values,
        "notes": "Assumed. RFD+MPNN expected to win on pure structure; Ours comparable on energetics.",
    }


def _build_ablation_experiment(rng: random.Random) -> Dict[str, Any]:
    """Ablation study."""
    variants = [
        {"id": "full", "name": "Ours (full)", "center": 0.91},
        {"id": "no_sar_mining", "name": "w/o SAR rule mining", "center": 0.86},
        {"id": "no_pareto", "name": "w/o Pareto parent selection", "center": 0.84},
        {"id": "no_reflection", "name": "w/o reflection", "center": 0.87},
        {"id": "no_structure", "name": "w/o structure/energy oracle", "center": 0.82},
    ]
    for v in variants:
        v["values"] = _generate_seed_values(rng, v["center"], n=len(SEEDS), spread=0.015)
    return {
        "id": "ablation",
        "kind": "ablation_table",
        "title": "Ablation study",
        "dataset": "scenario_b",
        "metric": "final_score",
        "variants": [{"id": v["id"], "name": v["name"], "values": v["values"]} for v in variants],
        "notes": "Assumed.",
    }


def _build_scaling_experiment(rng: random.Random) -> Dict[str, Any]:
    """Scaling with training data."""
    fractions = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    base_ours = [0.72, 0.78, 0.84, 0.87, 0.89, 0.91]
    base_rfd = [0.65, 0.70, 0.76, 0.80, 0.82, 0.84]
    base_pepmlm = [0.62, 0.68, 0.74, 0.78, 0.80, 0.82]
    series = [
        {"method": "ours", "y": [_rand_around(rng, v, 0.01) for v in base_ours]},
        {"method": "rfd_mpnn", "y": [_rand_around(rng, v, 0.01) for v in base_rfd]},
        {"method": "pepmlm", "y": [_rand_around(rng, v, 0.01) for v in base_pepmlm]},
    ]
    return {
        "id": "scaling_data",
        "kind": "scaling_curve",
        "title": "Scaling with training data",
        "dataset": "scenario_b",
        "metric": "final_score",
        "x": {"name": "Training data fraction", "values": fractions},
        "series": series,
        "notes": "Assumed.",
    }


def _build_robustness_experiment(rng: random.Random) -> Dict[str, Any]:
    """Robustness to missing feedback."""
    miss_levels = [0.0, 0.1, 0.2, 0.3, 0.4]
    base_ours = [0.91, 0.88, 0.84, 0.79, 0.74]
    base_rfd = [0.84, 0.78, 0.71, 0.62, 0.52]
    base_pepmlm = [0.82, 0.76, 0.68, 0.58, 0.48]
    series = [
        {"method": "ours", "y": [_rand_around(rng, v, 0.015) for v in base_ours]},
        {"method": "rfd_mpnn", "y": [_rand_around(rng, v, 0.015) for v in base_rfd]},
        {"method": "pepmlm", "y": [_rand_around(rng, v, 0.015) for v in base_pepmlm]},
    ]
    return {
        "id": "robustness_missing",
        "kind": "robustness_curve",
        "title": "Robustness to missing feedback",
        "dataset": "scenario_b",
        "metric": "final_score",
        "x": {"name": "Missingness level", "values": miss_levels},
        "series": series,
        "notes": "Assumed.",
    }


def _build_efficiency_experiment(rng: random.Random) -> Dict[str, Any]:
    """Accuracy-runtime tradeoff."""
    points = [
        {"method": "ours", "x": _rand_around(rng, 120, 10), "y": _rand_around(rng, 0.91, 0.01)},
        {"method": "rfd_mpnn", "x": _rand_around(rng, 280, 20), "y": _rand_around(rng, 0.84, 0.01)},
        {"method": "pepmlm", "x": _rand_around(rng, 45, 5), "y": _rand_around(rng, 0.82, 0.01)},
        {"method": "nsga2", "x": _rand_around(rng, 60, 8), "y": _rand_around(rng, 0.79, 0.01)},
        {"method": "qwen3", "x": _rand_around(rng, 12, 2), "y": _rand_around(rng, 0.745, 0.01)},
        {"method": "deepseek", "x": _rand_around(rng, 18, 3), "y": _rand_around(rng, 0.751, 0.01)},
    ]
    return {
        "id": "efficiency_runtime",
        "kind": "efficiency_scatter",
        "title": "Accuracy-runtime tradeoff",
        "dataset": "scenario_b",
        "x_metric": "runtime",
        "y_metric": "final_score",
        "points": points,
        "notes": "Assumed.",
    }


def _build_per_target_heatmap_experiment(rng: random.Random, scenario_id: str, targets: List[str]) -> Dict[str, Any]:
    """
    Per-target heatmap of final score (mean over seeds).
    This is the highest-density way to "list every dataset" in a single figure.
    """
    # Scenario difficulty shifts the centers slightly.
    base_shift = {"scenario_a": -0.03, "scenario_b": 0.00, "scenario_c": -0.05}.get(scenario_id, 0.0)
    method_offsets = {
        "ours": 0.06,
        "rfd_mpnn": 0.00,
        "pepmlm": -0.01,
        "nsga2": -0.03,
        "qwen3": -0.075,
        "deepseek": -0.065,
    }
    values: Dict[str, Dict[str, float]] = {}
    for t in targets:
        # Target-specific jitter so rows differ
        t_j = rng.uniform(-0.03, 0.03)
        values[t] = {}
        for m in METHODS:
            mid = m["id"]
            center = 0.84 + base_shift + t_j + method_offsets.get(mid, 0.0)
            # Clamp to [0,1] for scores
            v = max(0.0, min(1.0, _rand_around(rng, center, 0.02)))
            values[t][mid] = v
    return {
        "id": f"per_target_heatmap_{scenario_id}",
        "kind": "heatmap_matrix",
        "title": f"Per-target performance ({scenario_id})",
        "dataset": scenario_id,
        "metric": "final_score",
        "rows": targets,
        "cols": [m["id"] for m in METHODS],
        "values": values,
        "notes": "Assumed per-target mean scores for high-density reporting.",
    }


def _build_pareto_dashboard_experiment(rng: random.Random) -> Dict[str, Any]:
    """
    Nature-style: show dense candidate cloud + Pareto front + round trajectory.
    We generate synthetic candidate-level points for scenario_b / PD-L1.
    """
    points: List[Dict[str, Any]] = []
    rounds = list(range(1, 7))

    # Centers per method for the three objectives.
    # Values are in [0,1] for scores, with plausible trade-offs.
    centers = {
        "ours": (0.82, 0.84, 0.78),
        "rfd_mpnn": (0.74, 0.88, 0.60),
        "pepmlm": (0.70, 0.72, 0.66),
        "nsga2": (0.76, 0.78, 0.74),
        "qwen3": (0.65, 0.58, 0.56),
        "deepseek": (0.67, 0.62, 0.60),
    }

    for mid, (p0, s0, d0) in centers.items():
        for r in rounds:
            # Simple improvement trend across rounds (ours and nsga2 improve more)
            trend = {
                "ours": 0.018,
                "nsga2": 0.010,
                "rfd_mpnn": 0.006,
                "pepmlm": 0.004,
                "qwen3": 0.0018,
                "deepseek": 0.0022,
            }.get(mid, 0.005)
            pr = max(0.0, min(1.0, p0 + trend * (r - 1) + rng.uniform(-0.04, 0.04)))
            sr = max(0.0, min(1.0, s0 + trend * 0.6 * (r - 1) + rng.uniform(-0.04, 0.04)))
            dr = max(0.0, min(1.0, d0 + trend * 0.4 * (r - 1) + rng.uniform(-0.05, 0.05)))

            # 18 candidates per round per method (keeps JSON size reasonable)
            for _ in range(18):
                points.append(
                    {
                        "method": mid,
                        "round": r,
                        "potency_score": max(0.0, min(1.0, pr + rng.uniform(-0.05, 0.05))),
                        "structural_quality_score": max(0.0, min(1.0, sr + rng.uniform(-0.05, 0.05))),
                        "developability_score": max(0.0, min(1.0, dr + rng.uniform(-0.06, 0.06))),
                    }
                )

    return {
        "id": "pareto_dashboard_scenario_b",
        "kind": "pareto_dashboard",
        "title": "Pareto trade-offs and convergence (Scenario B / PD-L1)",
        "dataset": "scenario_b",
        "target": "PD-L1",
        "objectives": ["potency_score", "structural_quality_score", "developability_score"],
        "points": points,
        "notes": "Assumed candidate-level clouds used to render Nature-style multi-panel Pareto dashboard.",
    }


def _build_constraint_distributions_experiment(rng: random.Random) -> Dict[str, Any]:
    """
    Distribution plots for constraint governance (Scenario B).
    Includes charge distribution and invalid fraction (constraint violation).
    """
    by_method: Dict[str, Any] = {}
    n = 400
    for m in METHODS:
        mid = m["id"]
        # Ours is tightly controlled; others drift.
        charge_mu = {"ours": 0.4, "nsga2": 0.8, "rfd_mpnn": 1.8, "pepmlm": 1.2, "qwen3": 2.5, "deepseek": 2.3}.get(mid, 1.2)
        charge = [max(0.0, rng.gauss(charge_mu, 0.7)) for _ in range(n)]
        # Map to total charge count approximately (0..10)
        total_charge = [min(10, int(round(c * 2.0))) for c in charge]

        # Violation: total charge > 4 and/or aggregation risk high (simulated)
        agg_high_p = {"ours": 0.06, "nsga2": 0.10, "rfd_mpnn": 0.22, "pepmlm": 0.18, "qwen3": 0.32, "deepseek": 0.28}.get(mid, 0.15)
        agg_high = [rng.random() < agg_high_p for _ in range(n)]
        violated = [(tc > 4) or ah for tc, ah in zip(total_charge, agg_high)]

        by_method[mid] = {
            "total_charge": total_charge,
            "aggregation_high": [1 if x else 0 for x in agg_high],
            "violated": [1 if x else 0 for x in violated],
        }

    return {
        "id": "constraint_distributions_scenario_b",
        "kind": "constraint_distributions",
        "title": "Constraint governance distributions (Scenario B)",
        "dataset": "scenario_b",
        "by_method": by_method,
        "notes": "Assumed distributions: total charge, aggregation risk, and overall violation flags.",
    }


def _build_runtime_breakdown_experiment(rng: random.Random) -> Dict[str, Any]:
    """
    Stacked runtime breakdown for Scenario B (seconds).
    Nature-style: show what we pay for interpretability/verification.
    """
    components = ["llm_planning", "structure_prediction", "energy_scoring", "misc_io"]
    values: Dict[str, Dict[str, float]] = {}
    for m in METHODS:
        mid = m["id"]
        # Assumed runtime: ours is moderate, structure baseline high, direct LLM low.
        base = {"ours": 160, "rfd_mpnn": 340, "pepmlm": 55, "nsga2": 90, "qwen3": 12, "deepseek": 18}.get(mid, 100)
        llm = base * (0.22 if mid == "ours" else 0.10)
        structure = base * (0.45 if mid in ("ours", "rfd_mpnn") else 0.05)
        energy = base * (0.25 if mid in ("ours", "rfd_mpnn", "nsga2") else 0.03)
        misc = max(1.0, base - (llm + structure + energy))
        # small jitter
        values[mid] = {
            "llm_planning": round(llm + rng.uniform(-5, 5), 2),
            "structure_prediction": round(structure + rng.uniform(-8, 8), 2),
            "energy_scoring": round(energy + rng.uniform(-6, 6), 2),
            "misc_io": round(misc + rng.uniform(-3, 3), 2),
        }
    return {
        "id": "runtime_breakdown_scenario_b",
        "kind": "runtime_breakdown",
        "title": "Runtime breakdown (Scenario B)",
        "dataset": "scenario_b",
        "components": components,
        "values": values,
        "notes": "Assumed stacked runtime to contextualize verification cost.",
    }


def _build_system_overview_experiment() -> Dict[str, Any]:
    """
    System diagram (modes + tools) as a figure asset.
    """
    return {
        "id": "system_overview",
        "kind": "system_diagram",
        "title": "System overview: bounded modes and tool-orchestrated optimization",
        "notes": "Diagram-only experiment.",
    }


# ---------------------------------------------------------------------------
# Asset declarations
# ---------------------------------------------------------------------------


def _build_assets() -> List[Dict[str, Any]]:
    return [
        # Tables
        {
            "id": "tab_main_results",
            "type": "table",
            "source_experiment": "main_results",
            "output": {"latex": "assets/tables/tab_main_results.tex", "png": "assets/tables/tab_main_results.png"},
            "style": {"caption": "Comparison of optimized lead quality across three benchmarking scenarios (Assumed). Scenario A: Sparse SAR (e.g., SKEMPI 2.0); Scenario B: Rich SAR (PD-L1); Scenario C: Cyclic case study (Krpep-2d).", "label": "tab:main_results", "highlight_best": True, "highlight_second": True},
        },
        {
            "id": "tab_sar_violation",
            "type": "table",
            "source_experiment": "sar_violation",
            "output": {"latex": "assets/tables/tab_sar_violation.tex", "png": "assets/tables/tab_sar_violation.png"},
            "style": {"caption": "SAR Violation Rate (Assumed). Fraction of generated candidates that mutate known critical conserved residues.", "label": "tab:sar_violation", "highlight_best": True},
        },
        {
            "id": "tab_constraint_satisfaction",
            "type": "table",
            "source_experiment": "constraint_satisfaction",
            "output": {"latex": "assets/tables/tab_constraint_satisfaction.tex", "png": "assets/tables/tab_constraint_satisfaction.png"},
            "style": {"caption": "Multi-objective constraint satisfaction rate (Assumed). Percentage of high-affinity candidates meeting all developability criteria (Net Charge $\\in [-2, +2]$ and Low Aggregation Risk).", "label": "tab:csr", "highlight_best": True},
        },
        {
            "id": "tab_structure_validity",
            "type": "table",
            "source_experiment": "structure_validity",
            "output": {"latex": "assets/tables/tab_structure_validity.tex", "png": "assets/tables/tab_structure_validity.png"},
            "style": {"caption": "Structural and Energetic Validity (Assumed). All values evaluated by independent Boltz-2 oracle.", "label": "tab:structure_validity", "highlight_best": True},
        },
        {
            "id": "tab_ablation",
            "type": "table",
            "source_experiment": "ablation",
            "output": {"latex": "assets/tables/tab_ablation.tex", "png": "assets/tables/tab_ablation.png"},
            "style": {"caption": "Ablation study on Scenario B (Assumed). Shows the impact of each core architectural component on final optimization performance.", "label": "tab:ablation", "highlight_best": True},
        },
        # Figures
        {
            "id": "fig_main_bar",
            "type": "figure",
            "plot": "grouped_bar",
            "source_experiment": "main_results",
            "output": {"pdf": "assets/figs/fig_main_bar.pdf", "png": "assets/figs/fig_main_bar.png"},
            "style": {"title": "Optimization Performance across Scenarios (Assumed)", "xlabel": "Scenario", "ylabel": "Final Score (Composite)", "legend": True},
        },
        {
            "id": "fig_scaling",
            "type": "figure",
            "plot": "line",
            "source_experiment": "scaling_data",
            "output": {"pdf": "assets/figs/fig_scaling.pdf", "png": "assets/figs/fig_scaling.png"},
            "style": {"title": "Scaling with Data (Assumed)", "xlabel": "Training data fraction", "ylabel": "Final Score", "legend": True},
        },
        {
            "id": "fig_robustness",
            "type": "figure",
            "plot": "line",
            "source_experiment": "robustness_missing",
            "output": {"pdf": "assets/figs/fig_robustness.pdf", "png": "assets/figs/fig_robustness.png"},
            "style": {"title": "Robustness to Missing Feedback (Assumed)", "xlabel": "Missingness level", "ylabel": "Final Score", "legend": True},
        },
        {
            "id": "fig_efficiency",
            "type": "figure",
            "plot": "scatter",
            "source_experiment": "efficiency_runtime",
            "output": {"pdf": "assets/figs/fig_efficiency.pdf", "png": "assets/figs/fig_efficiency.png"},
            "style": {"title": "Accuracy-Runtime Tradeoff (Assumed)", "xlabel": "Runtime (s)", "ylabel": "Final Score", "legend": False},
        },
        # Nature-style rich figures
        {
            "id": "fig_system_overview",
            "type": "figure",
            "plot": "system_diagram",
            "source_experiment": "system_overview",
            "output": {"pdf": "assets/figs/fig_system_overview.pdf", "png": "assets/figs/fig_system_overview.png"},
            "style": {"title": "System Overview (Assumed)"},
        },
        {
            "id": "fig_per_target_heatmap_scenario_a",
            "type": "figure",
            "plot": "heatmap",
            "source_experiment": "per_target_heatmap_scenario_a",
            "output": {"pdf": "assets/figs/fig_per_target_heatmap_scenario_a.pdf", "png": "assets/figs/fig_per_target_heatmap_scenario_a.png"},
            "style": {"title": "Per-target Results (Scenario A / Sparse) (Assumed)", "xlabel": "Method", "ylabel": "Target", "cmap": "viridis"},
        },
        {
            "id": "fig_per_target_heatmap_scenario_b",
            "type": "figure",
            "plot": "heatmap",
            "source_experiment": "per_target_heatmap_scenario_b",
            "output": {"pdf": "assets/figs/fig_per_target_heatmap_scenario_b.pdf", "png": "assets/figs/fig_per_target_heatmap_scenario_b.png"},
            "style": {"title": "Per-target Results (Scenario B / Rich) (Assumed)", "xlabel": "Method", "ylabel": "Target", "cmap": "viridis"},
        },
        {
            "id": "fig_per_target_heatmap_scenario_c",
            "type": "figure",
            "plot": "heatmap",
            "source_experiment": "per_target_heatmap_scenario_c",
            "output": {"pdf": "assets/figs/fig_per_target_heatmap_scenario_c.pdf", "png": "assets/figs/fig_per_target_heatmap_scenario_c.png"},
            "style": {"title": "Per-target Results (Scenario C / Cyclic) (Assumed)", "xlabel": "Method", "ylabel": "Target", "cmap": "viridis"},
        },
        {
            "id": "fig_pareto_dashboard",
            "type": "figure",
            "plot": "pareto_dashboard",
            "source_experiment": "pareto_dashboard_scenario_b",
            "output": {"pdf": "assets/figs/fig_pareto_dashboard.pdf", "png": "assets/figs/fig_pareto_dashboard.png"},
            "style": {"title": "Pareto Trade-offs and Convergence (Scenario B / PD-L1) (Assumed)"},
        },
        {
            "id": "fig_constraint_distributions",
            "type": "figure",
            "plot": "constraint_distributions",
            "source_experiment": "constraint_distributions_scenario_b",
            "output": {"pdf": "assets/figs/fig_constraint_distributions.pdf", "png": "assets/figs/fig_constraint_distributions.png"},
            "style": {"title": "Constraint Governance Distributions (Scenario B) (Assumed)"},
        },
        {
            "id": "fig_runtime_breakdown",
            "type": "figure",
            "plot": "stacked_bar",
            "source_experiment": "runtime_breakdown_scenario_b",
            "output": {"pdf": "assets/figs/fig_runtime_breakdown.pdf", "png": "assets/figs/fig_runtime_breakdown.png"},
            "style": {"title": "Runtime Breakdown (Scenario B) (Assumed)", "xlabel": "Method", "ylabel": "Seconds", "legend": True},
        },
    ]


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_assumed_benchmark_results_doc(seed: int = 42) -> Dict[str, Any]:
    """
    Build the complete assumed_results document deterministically.

    Args:
        seed: Random seed for reproducibility.

    Returns:
        Dict matching generate_plots_table.py schema.
    """
    rng = random.Random(seed)

    experiments = [
        _build_main_results_experiment(rng),
        _build_sar_violation_experiment(rng),
        _build_constraint_satisfaction_experiment(rng),
        _build_structure_validity_experiment(rng),
        _build_ablation_experiment(rng),
        _build_scaling_experiment(rng),
        _build_robustness_experiment(rng),
        _build_efficiency_experiment(rng),
        _build_per_target_heatmap_experiment(rng, "scenario_a", SCENARIO_A_TARGETS),
        _build_per_target_heatmap_experiment(rng, "scenario_b", SCENARIO_B_TARGETS),
        _build_per_target_heatmap_experiment(rng, "scenario_c", SCENARIO_C_TARGETS),
        _build_pareto_dashboard_experiment(rng),
        _build_constraint_distributions_experiment(rng),
        _build_runtime_breakdown_experiment(rng),
        _build_system_overview_experiment(),
    ]

    return {
        "__schema_version__": "1.1",
        "__assumed_notice__": "ALL numbers are ASSUMED placeholders for drafting. Replace with real results later.",
        "paper": {
            "title_working": "Pareto-Guided Multi-Round Agentic Optimization with Interpretable SAR Rule Mining",
            "paper_type": "Algorithm",
            "method": {"id": "ours", "name": "Pareto-guided multi-round agentic optimization", "short": "Ours"},
        },
        "baselines": [m for m in METHODS if m["id"] != "ours"],
        "datasets": DATASETS,
        "metrics": METRICS,
        "assumptions": {
            "seeds": SEEDS,
            "protocol": {
                "split": "Project-internal (Assumed)",
                "hardware": "1xGPU (Assumed)",
                "structure_oracle": "Boltz-2",
                "training_budget": "Fixed evaluation budget (Assumed)",
            },
        },
        "experiments": experiments,
        "assets": _build_assets(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate assumed benchmark results JSON.")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    ap.add_argument("--outfile", type=str, default=None, help="Output JSON path (default: stdout)")
    args = ap.parse_args()

    doc = build_assumed_benchmark_results_doc(seed=args.seed)
    text = json.dumps(doc, indent=2, ensure_ascii=False)

    if args.outfile:
        Path(args.outfile).write_text(text, encoding="utf-8")
        print(f"[OK] Written to {args.outfile}")
    else:
        print(text)


if __name__ == "__main__":
    main()

