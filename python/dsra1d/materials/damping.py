"""Small-strain damping utilities shared across all native solvers.

Provides:
- ``layer_damping``: extract small-strain damping ratio from material params.
- ``rayleigh_coefficients``: compute Rayleigh α/β from target damping and two mode frequencies.
- ``frequency_independent_element_damping``: compute per-element viscous dashpot c = 2·ξ·√(k·m).

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


def frequency_independent_element_damping(
    xi: float,
    k: float,
    m: float,
) -> float:
    """Compute frequency-independent viscous dashpot: c = 2·ξ·√(k·m)."""
    return 2.0 * float(np.clip(xi, 0.0, 0.5)) * float(np.sqrt(max(k * m, 0.0)))
