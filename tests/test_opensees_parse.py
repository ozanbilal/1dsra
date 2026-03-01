from pathlib import Path

import numpy as np
from dsra1d.interop.opensees.parse import read_ru, read_surface_acc, read_surface_acc_with_time


def test_read_surface_acc_two_column_time_series(tmp_path: Path) -> None:
    p = tmp_path / "surface_acc.out"
    p.write_text("0.00 0.10\n0.01 -0.20\n0.02 0.05\n", encoding="utf-8")

    t, acc = read_surface_acc_with_time(p, dt_default=0.01)
    assert np.allclose(t, np.array([0.00, 0.01, 0.02]))
    assert np.allclose(acc, np.array([0.10, -0.20, 0.05]))
    assert np.allclose(read_surface_acc(p), acc)


def test_read_surface_acc_single_column_fallback_time(tmp_path: Path) -> None:
    p = tmp_path / "surface_acc_single.out"
    p.write_text("0.10\n-0.20\n0.05\n", encoding="utf-8")

    t, acc = read_surface_acc_with_time(p, dt_default=0.02)
    assert np.allclose(t, np.array([0.00, 0.02, 0.04]))
    assert np.allclose(acc, np.array([0.10, -0.20, 0.05]))


def test_read_ru_two_column_series(tmp_path: Path) -> None:
    p = tmp_path / "pwp_ru.out"
    p.write_text("0.00 0.01\n0.01 0.03\n0.02 0.08\n", encoding="utf-8")
    t, ru = read_ru(p)
    assert np.allclose(t, np.array([0.00, 0.01, 0.02]))
    assert np.allclose(ru, np.array([0.01, 0.03, 0.08]))
