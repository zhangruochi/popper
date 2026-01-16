import importlib.util
import sys
from pathlib import Path


def _load_module():
    mod_path = Path(__file__).resolve().parents[1] / "generate_plots_table.py"
    spec = importlib.util.spec_from_file_location("generate_plots_table", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Needed for dataclasses resolution when generate_plots_table.py uses
    # `from __future__ import annotations` (string annotations).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_prepare_heatmap_row_delta_to_best_sets_row_max_to_zero():
    m = _load_module()

    rows = ["t1", "t2"]
    cols = ["m1", "m2"]
    vmap = {
        "t1": {"m1": 0.9, "m2": 0.8},
        "t2": {"m1": 0.5, "m2": 0.7},
    }

    data, vmin, vmax = m._prepare_heatmap_data(  # noqa: SLF001
        rows=rows,
        cols=cols,
        vmap=vmap,
        normalize="row_delta_best",
        vmin=None,
        vmax=None,
        robust=False,
        q_low=0.05,
        q_high=0.95,
    )

    assert data.shape == (2, 2)
    # Each row's best method should become 0.0, others are negative gaps.
    assert abs(float(data[0, 0]) - 0.0) < 1e-12
    assert abs(float(data[0, 1]) - (-0.1)) < 1e-12
    assert abs(float(data[1, 1]) - 0.0) < 1e-12
    assert abs(float(data[1, 0]) - (-0.2)) < 1e-12
    assert abs(float(vmax) - 0.0) < 1e-12
    assert float(vmin) < 0.0


def test_prepare_heatmap_robust_quantile_sets_vmin_vmax():
    m = _load_module()

    rows = ["t1", "t2"]
    cols = ["m1", "m2"]
    vmap = {
        "t1": {"m1": 0.0, "m2": 1.0},
        "t2": {"m1": 2.0, "m2": 3.0},
    }

    data, vmin, vmax = m._prepare_heatmap_data(  # noqa: SLF001
        rows=rows,
        cols=cols,
        vmap=vmap,
        normalize="none",
        vmin=None,
        vmax=None,
        robust=True,
        q_low=0.0,
        q_high=1.0,
    )

    assert data.shape == (2, 2)
    assert abs(float(vmin) - 0.0) < 1e-12
    assert abs(float(vmax) - 3.0) < 1e-12


