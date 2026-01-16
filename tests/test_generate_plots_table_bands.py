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


def test_mean_std_bands_round_major():
    m = _load_module()

    # Round-major: T x S
    y = [
        [1.0, 2.0],
        [3.0, 4.0],
    ]
    means, stds = m._mean_std_bands(y, orientation="round_major")  # noqa: SLF001

    assert means == [1.5, 3.5]
    # Sample std of [1,2] and [3,4] is sqrt(0.5).
    assert abs(stds[0] - (0.5**0.5)) < 1e-12
    assert abs(stds[1] - (0.5**0.5)) < 1e-12


def test_mean_std_bands_seed_major():
    m = _load_module()

    # Seed-major: S x T
    y = [
        [1.0, 3.0],
        [2.0, 4.0],
    ]
    means, stds = m._mean_std_bands(y, orientation="seed_major")  # noqa: SLF001

    assert means == [1.5, 3.5]
    assert abs(stds[0] - (0.5**0.5)) < 1e-12
    assert abs(stds[1] - (0.5**0.5)) < 1e-12


