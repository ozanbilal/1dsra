"""Small-strain damping utilities shared across all native solvers.

Provides:
- ``layer_damping``: extract small-strain damping ratio from material params.
- ``rayleigh_coefficients``: compute Rayleigh α/β from target damping and two mode frequencies.
- ``estimate_modal_frequencies_hz``: estimate the lowest system frequencies from M and K.
- ``modal_matched_damping_matrix``: build a global viscous damping matrix that
  matches the requested damping ratio at the first one or two system modes.
- ``frequency_independent_element_damping``: legacy per-element dashpot helper.

These are the single source of truth; linear, EQL, and nonlinear solvers
all delegate here instead of carrying private copies.
"""
from __future__ import annotations

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType

FloatArray = npt.NDArray[np.float64]


def layer_damping(material: MaterialType, params: dict[str, float]) -> float:
    """Return small-strain damping ratio for a layer based on its material type."""
    if material in {MaterialType.MKZ, MaterialType.GQH}:
        return float(np.clip(params.get("damping_min", 0.02), 0.0, 0.30))
    if material in {MaterialType.PM4SAND, MaterialType.PM4SILT}:
        return 0.05
    return 0.02


def rayleigh_coefficients(
    damping_ratio: float,
    mode_1_hz: float,
    mode_2_hz: float,
) -> tuple[float, float]:
    """Compute Rayleigh damping coefficients (α, β) from a target damping ratio.

    Uses two-frequency formulation:
        α = 2·ξ·ω₁·ω₂ / (ω₁ + ω₂)
        β = 2·ξ / (ω₁ + ω₂)
    """
    xi = float(np.clip(damping_ratio, 0.0, 0.5))
    f1 = float(max(mode_1_hz, 1.0e-6))
    f2 = float(max(mode_2_hz, 1.0e-6))
    if f2 <= f1:
        f2 = f1 + 1.0e-6
    w1 = 2.0 * np.pi * f1
    w2 = 2.0 * np.pi * f2
    denom = w1 + w2
    if denom <= 0.0:
        return 0.0, 0.0
    alpha = (2.0 * xi * w1 * w2) / denom
    beta = (2.0 * xi) / denom
    return float(alpha), float(beta)


def estimate_modal_frequencies_hz(
    m_diag: npt.ArrayLike,
    k_mat: npt.ArrayLike,
    *,
    max_modes: int = 2,
) -> FloatArray:
    """Estimate the lowest positive natural frequencies of the M-K system.

    The generalized eigenproblem K phi = w² M phi is converted to the
    symmetric standard form using the lumped mass diagonal.
    """
    m = np.asarray(m_diag, dtype=np.float64).reshape(-1)
    k = np.asarray(k_mat, dtype=np.float64)
    if m.size == 0 or k.size == 0:
        return np.array([], dtype=np.float64)
    if k.shape != (m.size, m.size):
        raise ValueError("k_mat must be square with the same dimension as m_diag.")

    m_safe = np.maximum(m, 1.0e-12)
    inv_sqrt_m = 1.0 / np.sqrt(m_safe)
    dyn = (inv_sqrt_m[:, None] * k) * inv_sqrt_m[None, :]
    dyn = 0.5 * (dyn + dyn.T)
    eigvals = np.linalg.eigvalsh(dyn)
    eigvals = np.sort(np.real(eigvals[np.isfinite(eigvals) & (eigvals > 1.0e-12)]))
    if eigvals.size == 0:
        return np.array([], dtype=np.float64)
    omega = np.sqrt(eigvals[: max(int(max_modes), 1)])
    return omega / (2.0 * np.pi)


def modal_matched_damping_matrix(
    m_diag: npt.ArrayLike,
    k_mat: npt.ArrayLike,
    damping_ratio: float,
) -> FloatArray:
    """Build a global viscous damping matrix for ``frequency_independent`` mode.

    The previous per-element dashpot approximation under-damped the important
    system modes, especially the first mode.  This helper instead matches the
    requested damping ratio at the first one or two natural frequencies of the
    assembled system via a Rayleigh-form global matrix.
    """
    m = np.asarray(m_diag, dtype=np.float64).reshape(-1)
    k = np.asarray(k_mat, dtype=np.float64)
    if k.shape != (m.size, m.size):
        raise ValueError("k_mat must be square with the same dimension as m_diag.")
    xi = float(np.clip(damping_ratio, 0.0, 0.5))
    if m.size == 0 or xi <= 0.0:
        return np.zeros_like(k, dtype=np.float64)

    freqs = estimate_modal_frequencies_hz(m, k, max_modes=2)
    if freqs.size == 0:
        return np.zeros_like(k, dtype=np.float64)

    if freqs.size == 1 or freqs[1] <= freqs[0] * (1.0 + 1.0e-6):
        omega = 2.0 * np.pi * float(freqs[0])
        alpha = 2.0 * xi * omega
        beta = 0.0
    else:
        alpha, beta = rayleigh_coefficients(
            damping_ratio=xi,
            mode_1_hz=float(freqs[0]),
            mode_2_hz=float(freqs[1]),
        )
    return (alpha * np.diag(m)) + (beta * k)


def frequency_independent_element_damping(
    xi: float,
    k: float,
    m: float,
) -> float:
    """Compute frequency-independent viscous dashpot: c = 2·ξ·√(k·m)."""
    return 2.0 * float(np.clip(xi, 0.0, 0.5)) * float(np.sqrt(max(k * m, 0.0)))
