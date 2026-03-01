from __future__ import annotations

from pathlib import Path

import numpy as np

from dsra1d.types import Motion


def load_motion(path: str | Path, dt: float, unit: str = "m/s2") -> Motion:
    path_obj = Path(path)
    raw = np.loadtxt(path_obj, delimiter=",", ndmin=1)
    if raw.ndim > 1:
        acc = raw[:, -1]
    else:
        acc = raw
    return Motion(dt=dt, acc=acc.astype(np.float64), unit=unit, source=path_obj)
