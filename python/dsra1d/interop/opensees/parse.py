from __future__ import annotations

from pathlib import Path

import numpy as np


def _load_matrix(path: Path) -> np.ndarray:
    arr = np.loadtxt(path, ndmin=2)
    return np.asarray(arr, dtype=np.float64)


def read_surface_acc_with_time(
    path: Path,
    dt_default: float,
) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        t = np.array([0.0, dt_default], dtype=np.float64)
        acc = np.zeros(2, dtype=np.float64)
        return t, acc

    arr = _load_matrix(path)
    if arr.shape[1] == 1:
        acc = arr[:, 0]
        t = np.arange(acc.size, dtype=np.float64) * dt_default
        return t, acc

    t = arr[:, 0]
    acc = arr[:, 1]
    return np.asarray(t, dtype=np.float64), np.asarray(acc, dtype=np.float64)


def read_surface_acc(path: Path) -> np.ndarray:
    _, acc = read_surface_acc_with_time(path, dt_default=1.0)
    return acc


def read_ru(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        return np.array([0.0]), np.array([0.0])
    arr = _load_matrix(path)
    if arr.shape[1] == 1:
        t = np.arange(arr.shape[0], dtype=np.float64)
        ru = arr[:, 0]
    else:
        t = arr[:, 0]
        ru = arr[:, 1]
    return np.asarray(t, dtype=np.float64), np.asarray(ru, dtype=np.float64)


def read_pwp_raw(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        return np.array([0.0]), np.array([0.0])
    arr = _load_matrix(path)
    if arr.shape[1] == 1:
        t = np.arange(arr.shape[0], dtype=np.float64)
        pwp = arr[:, 0]
    else:
        t = arr[:, 0]
        pwp = arr[:, 1]
    return np.asarray(t, dtype=np.float64), np.asarray(pwp, dtype=np.float64)
