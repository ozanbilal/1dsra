from __future__ import annotations

from pathlib import Path

import numpy as np

from dsra1d.types import Motion
from dsra1d.units import SI_ACCEL_UNIT, accel_factor_to_si


def _load_numeric_series(path_obj: Path) -> np.ndarray:
    try:
        raw = np.loadtxt(path_obj, delimiter=",", ndmin=1)
    except ValueError:
        raw = np.loadtxt(path_obj, delimiter=None, ndmin=1)
    return np.asarray(raw, dtype=np.float64)


def load_motion(path: str | Path, dt: float, unit: str = "m/s2") -> Motion:
    path_obj = Path(path)
    raw = _load_numeric_series(path_obj)
    if raw.ndim > 1:
        acc = raw[:, -1]
    else:
        acc = raw
    acc_si = acc * accel_factor_to_si(unit)
    return Motion(dt=dt, acc=acc_si.astype(np.float64), unit=SI_ACCEL_UNIT, source=path_obj)
