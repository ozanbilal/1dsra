from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Spectra:
    periods: np.ndarray
    psa: np.ndarray


def _sdof_response(acc: np.ndarray, dt: float, omega: float, xi: float) -> np.ndarray:
    n = acc.shape[0]
    u = np.zeros(n, dtype=np.float64)
    v = np.zeros(n, dtype=np.float64)

    beta = 0.25
    gamma = 0.5
    k = omega**2
    c = 2 * xi * omega

    a0 = 1.0 / (beta * dt**2)
    a1 = gamma / (beta * dt)
    a4 = (gamma / beta) - 1.0

    keff = k + a0 + a1 * c

    for i in range(1, n):
        p_eff = -acc[i] + a0 * u[i - 1] + c * (a1 * u[i - 1] + a4 * v[i - 1])
        u[i] = p_eff / keff
        v[i] = a1 * (u[i] - u[i - 1]) - a4 * v[i - 1]

    return u


def compute_spectra(
    signal: np.ndarray,
    dt: float,
    damping: float = 0.05,
    periods: np.ndarray | None = None,
) -> Spectra:
    if periods is None:
        periods = np.linspace(0.05, 4.0, 80)

    psa = np.zeros_like(periods, dtype=np.float64)
    for idx, t in enumerate(periods):
        omega = 2.0 * np.pi / t
        u = _sdof_response(signal, dt, omega, damping)
        psa[idx] = np.max(np.abs(u)) * omega**2

    return Spectra(periods=periods, psa=psa)
