from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType

FloatArray = npt.NDArray[np.float64]


def _to_float_array(strain: npt.ArrayLike) -> FloatArray:
    return np.asarray(strain, dtype=np.float64)


def mkz_modulus_reduction(
    strain: npt.ArrayLike,
    gamma_ref: float,
    g_reduction_min: float = 0.0,
) -> FloatArray:
    if gamma_ref <= 0.0:
        raise ValueError("gamma_ref must be > 0.")
    gamma = np.abs(_to_float_array(strain))
    reduction = 1.0 / (1.0 + (gamma / gamma_ref))
    if g_reduction_min > 0.0:
        reduction = np.maximum(reduction, g_reduction_min)
    return reduction


def mkz_backbone_stress(
    strain: npt.ArrayLike,
    gmax: float,
    gamma_ref: float,
    tau_max: float | None = None,
    g_reduction_min: float = 0.0,
) -> FloatArray:
    if gmax <= 0.0:
        raise ValueError("gmax must be > 0.")
    reduction = mkz_modulus_reduction(strain, gamma_ref, g_reduction_min=g_reduction_min)
    strain_arr = _to_float_array(strain)
    tau = gmax * strain_arr * reduction
    if tau_max is not None:
        if tau_max <= 0.0:
            raise ValueError("tau_max must be > 0 when provided.")
        tau = np.sign(tau) * np.minimum(np.abs(tau), tau_max)
    return tau


def gqh_modulus_reduction(
    strain: npt.ArrayLike,
    gamma_ref: float,
    a1: float = 1.0,
    a2: float = 0.0,
    m: float = 1.0,
    g_reduction_min: float = 0.0,
) -> FloatArray:
    if gamma_ref <= 0.0:
        raise ValueError("gamma_ref must be > 0.")
    if a1 <= 0.0:
        raise ValueError("a1 must be > 0.")
    if a2 < 0.0:
        raise ValueError("a2 must be >= 0.")
    if m <= 0.0:
        raise ValueError("m must be > 0.")
    r = np.abs(_to_float_array(strain)) / gamma_ref
    denom = 1.0 + (a1 * r) + (a2 * np.power(r, m))
    reduction = 1.0 / denom
    if g_reduction_min > 0.0:
        reduction = np.maximum(reduction, g_reduction_min)
    return reduction


def gqh_backbone_stress(
    strain: npt.ArrayLike,
    gmax: float,
    gamma_ref: float,
    a1: float = 1.0,
    a2: float = 0.0,
    m: float = 1.0,
    tau_max: float | None = None,
    g_reduction_min: float = 0.0,
) -> FloatArray:
    if gmax <= 0.0:
        raise ValueError("gmax must be > 0.")
    reduction = gqh_modulus_reduction(
        strain, gamma_ref=gamma_ref, a1=a1, a2=a2, m=m,
        g_reduction_min=g_reduction_min,
    )
    strain_arr = _to_float_array(strain)
    tau = gmax * strain_arr * reduction
    if tau_max is not None:
        if tau_max <= 0.0:
            raise ValueError("tau_max must be > 0 when provided.")
        tau = np.sign(tau) * np.minimum(np.abs(tau), tau_max)
    return tau


def bounded_damping_from_reduction(
    reduction: npt.ArrayLike,
    damping_min: float = 0.01,
    damping_max: float = 0.15,
) -> FloatArray:
    if not (0.0 <= damping_min <= 0.5):
        raise ValueError("damping_min must be in [0, 0.5].")
    if not (0.0 <= damping_max <= 0.5):
        raise ValueError("damping_max must be in [0, 0.5].")
    if damping_min > damping_max:
        raise ValueError("damping_min must be <= damping_max.")
    red = np.clip(_to_float_array(reduction), 0.0, 1.0)
    damp = damping_min + (1.0 - red) * (damping_max - damping_min)
    return np.clip(damp, damping_min, damping_max)


@dataclass(slots=True, frozen=True)
class LayerHystereticProxy:
    reduction: float
    damping: float
    ru_target: float


@dataclass(slots=True, frozen=True)
class HystereticLoop:
    strain: FloatArray
    stress: FloatArray
    strain_amplitude: float
    energy_dissipation: float


def generate_masing_loop(
    material: MaterialType,
    material_params: Mapping[str, float],
    *,
    strain_amplitude: float,
    n_points_per_branch: int = 120,
) -> HystereticLoop:
    if material not in {MaterialType.MKZ, MaterialType.GQH}:
        raise ValueError("generate_masing_loop supports only MKZ and GQH materials.")
    if strain_amplitude <= 0.0:
        raise ValueError("strain_amplitude must be > 0.")
    if n_points_per_branch < 3:
        raise ValueError("n_points_per_branch must be >= 3.")

    gmax = float(material_params.get("gmax", 0.0))
    gamma_ref = float(material_params.get("gamma_ref", 0.0))
    tau_max = material_params.get("tau_max")
    tau_cap = float(tau_max) if tau_max is not None else None
    if gmax <= 0.0:
        raise ValueError("material_params['gmax'] must be > 0.")
    if gamma_ref <= 0.0:
        raise ValueError("material_params['gamma_ref'] must be > 0.")

    def _backbone(abs_strain: FloatArray) -> FloatArray:
        if material == MaterialType.MKZ:
            return mkz_backbone_stress(
                abs_strain,
                gmax=gmax,
                gamma_ref=gamma_ref,
                tau_max=tau_cap,
            )
        return gqh_backbone_stress(
            abs_strain,
            gmax=gmax,
            gamma_ref=gamma_ref,
            a1=float(material_params.get("a1", 1.0)),
            a2=float(material_params.get("a2", 0.0)),
            m=float(material_params.get("m", 1.0)),
            tau_max=tau_cap,
        )

    n = int(n_points_per_branch)
    gamma_pos = np.linspace(0.0, strain_amplitude, n, dtype=np.float64)
    tau_pos = _backbone(gamma_pos)

    gamma_unload = np.linspace(strain_amplitude, -strain_amplitude, n, dtype=np.float64)
    d_unload = np.abs(strain_amplitude - gamma_unload) / 2.0
    tau_unload = tau_pos[-1] - 2.0 * _backbone(d_unload)

    gamma_reload = np.linspace(-strain_amplitude, strain_amplitude, n, dtype=np.float64)
    tau_neg = -tau_pos[-1]
    d_reload = np.abs(-strain_amplitude - gamma_reload) / 2.0
    tau_reload = tau_neg + 2.0 * _backbone(d_reload)

    strain = np.concatenate([gamma_pos, gamma_unload[1:], gamma_reload[1:]])
    stress = np.concatenate([tau_pos, tau_unload[1:], tau_reload[1:]])
    energy = float(abs(np.trapezoid(stress, strain)))
    return HystereticLoop(
        strain=strain,
        stress=stress,
        strain_amplitude=float(strain_amplitude),
        energy_dissipation=energy,
    )


def layer_hysteretic_proxy(
    material: MaterialType,
    material_params: Mapping[str, float],
    strain_proxy: float,
) -> LayerHystereticProxy:
    strain = max(float(strain_proxy), 1.0e-9)
    if material == MaterialType.MKZ:
        gamma_ref = float(material_params.get("gamma_ref", 0.001))
        g_red = float(mkz_modulus_reduction(np.array([strain]), gamma_ref=gamma_ref)[0])
        damping = float(
            bounded_damping_from_reduction(
                np.array([g_red]),
                damping_min=float(material_params.get("damping_min", 0.01)),
                damping_max=float(material_params.get("damping_max", 0.12)),
            )[0]
        )
        ru_target = float(np.clip(0.01 + 0.10 * (1.0 - g_red), 0.0, 0.20))
        return LayerHystereticProxy(reduction=g_red, damping=damping, ru_target=ru_target)

    if material == MaterialType.GQH:
        gamma_ref = float(material_params.get("gamma_ref", 0.001))
        g_red = float(
            gqh_modulus_reduction(
                np.array([strain]),
                gamma_ref=gamma_ref,
                a1=float(material_params.get("a1", 1.0)),
                a2=float(material_params.get("a2", 0.0)),
                m=float(material_params.get("m", 1.0)),
            )[0]
        )
        damping = float(
            bounded_damping_from_reduction(
                np.array([g_red]),
                damping_min=float(material_params.get("damping_min", 0.01)),
                damping_max=float(material_params.get("damping_max", 0.12)),
            )[0]
        )
        ru_target = float(np.clip(0.01 + 0.12 * (1.0 - g_red), 0.0, 0.25))
        return LayerHystereticProxy(reduction=g_red, damping=damping, ru_target=ru_target)

    if material == MaterialType.ELASTIC:
        return LayerHystereticProxy(reduction=0.95, damping=0.01, ru_target=0.01)

    # Effective-stress materials keep stronger pore-pressure potential in mock mode.
    return LayerHystereticProxy(reduction=0.75, damping=0.08, ru_target=0.35)
