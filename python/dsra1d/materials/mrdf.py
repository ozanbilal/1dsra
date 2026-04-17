"""MRDF (Modulus Reduction Damping Fit) correction for nonlinear hysteretic models.

Implements the Phillips-Hashash (2009) approach: at each strain amplitude γ_a,
the Masing-predicted hysteretic damping D_Masing(γ_a) is compared against a
target damping curve D_target(γ_a).  A correction factor F(γ_a) = D_target /
D_Masing is computed and stored as fitted polynomial coefficients for fast
runtime evaluation.

During time-domain analysis, the Masing branch stress deviation is scaled by F
so that the hysteresis loop area matches the target damping at the current
strain amplitude.

References
----------
Phillips, C. and Hashash, Y.M.A. (2009). Damping formulation for nonlinear
1D site response analyses. *Soil Dynamics and Earthquake Engineering*, 29(7),
1143-1158.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType
from dsra1d.materials.hysteretic import generate_masing_loop

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True, frozen=True)
class MRDFCoefficients:
    """Fitted polynomial coefficients for MRDF correction factor F(γ).

    F is evaluated as::

        x = ln(γ / γ_ref)
        F = clip(p1 + p2·x + p3·x², 0, F_MAX)

    where ``F_MAX`` defaults to 1.5.
    """

    p1: float
    p2: float
    p3: float
    gamma_ref: float
    mode: str = "poly"


F_MAX: float = 1.5


# ---------------------------------------------------------------------------
# Masing damping ratio from loop area
# ---------------------------------------------------------------------------

def compute_masing_damping_ratio(
    material: MaterialType,
    material_params: Mapping[str, float],
    strain_amplitudes: FloatArray,
) -> FloatArray:
    """Compute hysteretic damping ratio from Masing loop area at each strain amplitude.

    D = W_loop / (4 π W_elastic)
    where W_elastic = ½ G_sec γ_a²  and  G_sec = τ_max / γ_a.
    """
    result = np.zeros_like(strain_amplitudes, dtype=np.float64)
    for i, ga in enumerate(strain_amplitudes):
        if ga <= 0.0:
            continue
        loop = generate_masing_loop(material, material_params, strain_amplitude=float(ga))
        w_loop = loop.energy_dissipation
        # Secant modulus at peak strain
        tau_peak = float(np.max(np.abs(loop.stress)))
        if tau_peak < 1.0e-15:
            continue
        g_sec = tau_peak / float(ga)
        w_elastic = 0.5 * g_sec * float(ga) ** 2
        if w_elastic < 1.0e-20:
            continue
        result[i] = w_loop / (4.0 * np.pi * w_elastic)
    return result


# ---------------------------------------------------------------------------
# MRDF correction table
# ---------------------------------------------------------------------------

def compute_mrdf_correction_table(
    material: MaterialType,
    material_params: Mapping[str, float],
    target_damping: FloatArray,
    target_strain: FloatArray,
    n_points: int = 40,
) -> tuple[FloatArray, FloatArray]:
    """Compute F(γ) = D_target / D_Masing at log-spaced strain amplitudes.

    Returns (strain_amplitudes, correction_factors) arrays.
    """
    s_min = float(np.min(target_strain[target_strain > 0]))
    s_max = float(np.max(target_strain))
    strains = np.logspace(np.log10(max(s_min, 1.0e-7)), np.log10(s_max), n_points)

    # Masing damping
    d_masing = compute_masing_damping_ratio(material, material_params, strains)

    # Interpolate target damping to same strain grid
    d_target = np.interp(strains, target_strain, target_damping)

    # Correction factor
    f_raw = np.where(d_masing > 1.0e-10, d_target / d_masing, 1.0)
    f_clipped = np.clip(f_raw, 0.0, F_MAX)

    return strains, f_clipped


# ---------------------------------------------------------------------------
# Polynomial fit
# ---------------------------------------------------------------------------

def fit_mrdf_coefficients(
    strain_amplitudes: FloatArray,
    correction_factors: FloatArray,
    gamma_ref: float,
) -> MRDFCoefficients:
    """Fit F(γ) as a quadratic polynomial in ln(γ/γ_ref).

    Returns frozen ``MRDFCoefficients`` dataclass.
    """
    if gamma_ref <= 0.0:
        raise ValueError("gamma_ref must be > 0.")

    mask = strain_amplitudes > 0.0
    x = np.log(strain_amplitudes[mask] / gamma_ref)
    y = correction_factors[mask]

    if len(x) < 3:
        return MRDFCoefficients(p1=1.0, p2=0.0, p3=0.0, gamma_ref=gamma_ref)

    # Least-squares fit: y = p3*x^2 + p2*x + p1
    coeffs = np.polyfit(x, y, deg=2)
    p3, p2, p1 = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

    return MRDFCoefficients(p1=p1, p2=p2, p3=p3, gamma_ref=gamma_ref)


# ---------------------------------------------------------------------------
# Runtime evaluation
# ---------------------------------------------------------------------------

def evaluate_mrdf_factor(
    coeffs: MRDFCoefficients,
    strain_amplitude: float,
    *,
    g_over_gmax: float | None = None,
) -> float:
    """Evaluate F(γ) from fitted coefficients, clipped to [0, F_MAX]."""
    if strain_amplitude <= 0.0:
        return 1.0
    if coeffs.mode == "uiuc":
        if g_over_gmax is None:
            raise ValueError("g_over_gmax is required for MRDF-UIUC evaluation.")
        g_ratio = float(np.clip(g_over_gmax, 0.0, 1.0))
        f = coeffs.p1 - coeffs.p2 * np.power(1.0 - g_ratio, coeffs.p3)
        return float(np.clip(f, 0.0, F_MAX))
    x = np.log(strain_amplitude / max(coeffs.gamma_ref, 1.0e-15))
    f = coeffs.p1 + coeffs.p2 * x + coeffs.p3 * x * x
    return float(np.clip(f, 0.0, F_MAX))


def evolve_mrdf_factor_with_branch_progress(
    target_factor: float,
    branch_progress: float,
    *,
    exponent: float = 2.0,
) -> float:
    """Evolve an MRDF factor from 1.0 at reversal toward a target factor over branch progress.

    This is an experimental helper for parity studies. ``branch_progress`` is expected
    in ``[0, 1]`` where 0 is the reversal point and 1 is a full excursion relative to
    the current governing strain-history scale.
    """
    progress = float(np.clip(branch_progress, 0.0, 1.0))
    effective_exponent = max(float(exponent), 1.0e-6)
    weight = progress**effective_exponent
    evolved = 1.0 + (float(target_factor) - 1.0) * weight
    return float(np.clip(evolved, 0.0, F_MAX))


# ---------------------------------------------------------------------------
# Convenience: build MRDFCoefficients from material_params dict
# ---------------------------------------------------------------------------

def mrdf_coefficients_from_params(
    params: Mapping[str, float],
) -> MRDFCoefficients | None:
    """Extract MRDF coefficients from material_params if present.

    Returns None when ``mrdf_p1`` is not in *params*.
    """
    p1 = params.get("mrdf_p1")
    if p1 is None:
        return None
    return MRDFCoefficients(
        p1=float(p1),
        p2=float(params.get("mrdf_p2", 0.0)),
        p3=float(params.get("mrdf_p3", 0.0)),
        gamma_ref=float(params.get("gamma_ref", 1.0e-3)),
        mode="uiuc",
    )
