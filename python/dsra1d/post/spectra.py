from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Spectra:
    periods: np.ndarray
    psa: np.ndarray


def _sdof_response(acc: np.ndarray, dt: float, omega: float, xi: float) -> np.ndarray:
    n = int(acc.shape[0])
    if n == 0:
        return np.array([], dtype=np.float64)
    if dt <= 0.0:
        raise ValueError("dt must be > 0 for SDOF response.")
    if omega <= 0.0:
        raise ValueError("omega must be > 0 for SDOF response.")

    # Relative displacement response of:
    # u¨ + 2*xi*omega*u˙ + omega^2*u = -ag(t)
    u = np.zeros(n, dtype=np.float64)
    v = np.zeros(n, dtype=np.float64)
    a_rel = np.zeros(n, dtype=np.float64)

    beta = 0.25
    gamma = 0.5
    k = omega**2
    c = 2.0 * xi * omega
    p = -np.asarray(acc, dtype=np.float64)

    # Initial state: u0=v0=0
    a_rel[0] = p[0] - c * v[0] - k * u[0]

    m_eff = 1.0 + gamma * dt * c + beta * dt * dt * k
    for i in range(n - 1):
        u_pred = u[i] + dt * v[i] + (0.5 - beta) * dt * dt * a_rel[i]
        v_pred = v[i] + (1.0 - gamma) * dt * a_rel[i]
        a_next = (p[i + 1] - c * v_pred - k * u_pred) / m_eff
        u[i + 1] = u_pred + beta * dt * dt * a_next
        v[i + 1] = v_pred + gamma * dt * a_next
        a_rel[i + 1] = a_next

    return u


def compute_spectra(
    signal: np.ndarray,
    dt: float,
    damping: float = 0.05,
    periods: np.ndarray | None = None,
) -> Spectra:
    if periods is None:
        periods = np.logspace(np.log10(0.05), np.log10(4.0), 80)

    psa = np.zeros_like(periods, dtype=np.float64)
    for idx, t in enumerate(periods):
        omega = 2.0 * np.pi / t
        u = _sdof_response(signal, dt, omega, damping)
        psa[idx] = np.max(np.abs(u)) * omega**2

    return Spectra(periods=periods, psa=psa)


def compute_transfer_function(
    input_signal: np.ndarray,
    output_signal: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    if dt <= 0.0:
        raise ValueError("dt must be > 0 for transfer function.")
    n = min(int(input_signal.size), int(output_signal.size))
    if n < 2:
        return np.array([0.0], dtype=np.float64), np.array([0.0], dtype=np.float64)

    x = np.asarray(input_signal[:n], dtype=np.float64)
    y = np.asarray(output_signal[:n], dtype=np.float64)
    x = x - float(np.mean(x))
    y = y - float(np.mean(y))

    x_fft = np.fft.rfft(x)
    y_fft = np.fft.rfft(y)
    freq = np.fft.rfftfreq(n, d=dt)
    denom = np.maximum(np.abs(x_fft), 1.0e-12)
    h_abs = np.abs(y_fft) / denom
    if h_abs.size > 0:
        h_abs[0] = 0.0
    return freq.astype(np.float64), h_abs.astype(np.float64)
