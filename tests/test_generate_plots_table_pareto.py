import importlib.util
import sys
from pathlib import Path


def _load_module():
    mod_path = Path(__file__).resolve().parents[1] / "generate_plots_table.py"
    spec = importlib.util.spec_from_file_location("generate_plots_table", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_hypervolume_fraction_single_point_exact():
    m = _load_module()

    hv = m._hypervolume_fraction(points=[(0.5, 0.5, 0.5)])  # noqa: SLF001
    assert abs(hv - 0.125) < 1e-12

    hv0 = m._hypervolume_fraction(points=[(0.0, 0.0, 0.0)])  # noqa: SLF001
    assert abs(hv0 - 0.0) < 1e-12

    hv1 = m._hypervolume_fraction(points=[(1.0, 1.0, 1.0)])  # noqa: SLF001
    assert abs(hv1 - 1.0) < 1e-12


def test_pareto_ranks_front0():
    m = _load_module()

    # Maximize all three objectives.
    pts = [
        (1.0, 0.0, 0.0),  # non-dominated
        (0.0, 1.0, 0.0),  # non-dominated
        (0.0, 0.0, 1.0),  # non-dominated
        (0.0, 0.0, 0.0),  # dominated by all above
    ]
    ranks = m._pareto_ranks(pts)  # noqa: SLF001
    assert ranks[:3] == [0, 0, 0]
    assert ranks[3] >= 1


