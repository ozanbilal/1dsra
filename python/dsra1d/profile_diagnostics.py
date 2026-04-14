from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType
from dsra1d.materials.hysteretic import (
    gqh_mode_from_params,
    gqh_modulus_reduction_from_params,
    mkz_modulus_reduction,
)

FloatArray = npt.NDArray[np.float64]

WATER_UNIT_WEIGHT_KN_M3 = 9.81


@dataclass(slots=True, frozen=True)
class LayerStressState:
    index: int
    z_top_m: float
    z_bottom_m: float
    z_mid_m: float
    thickness_m: float
    sigma_v0_mid_kpa: float
    pore_water_pressure_kpa: float
    sigma_v_eff_mid_kpa: float


@dataclass(slots=True, frozen=True)
class LayerProfileDiagnostics:
    index: int
    name: str
    material: str
    thickness_m: float
    unit_weight_kn_m3: float
    vs_m_s: float
    z_top_m: float
    z_bottom_m: float
    z_mid_m: float
    sigma_v0_mid_kpa: float
    sigma_v_eff_mid_kpa: float
    pore_water_pressure_kpa: float
    small_strain_damping_ratio: float | None
    max_frequency_hz: float | None
    implied_strength_kpa: float | None
    normalized_implied_strength: float | None
    implied_friction_angle_deg: float | None
    gqh_mode: str | None = None


def _layer_value(layer: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(layer, dict) and name in layer:
            return layer[name]
        if hasattr(layer, name):
            return getattr(layer, name)
    return default


def _layer_material_params(layer: Any) -> dict[str, float]:
    params_raw = _layer_value(layer, "material_params", default={}) or {}
    if isinstance(params_raw, dict):
        out: dict[str, float] = {}
        for key, value in params_raw.items():
            try:
                out[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        return out
    return {}


def _layer_material(layer: Any) -> MaterialType:
    raw = _layer_value(layer, "material", default=MaterialType.ELASTIC)
    if isinstance(raw, MaterialType):
        return raw
    return MaterialType(str(raw))


def gmax_from_vs_unit_weight(vs_m_s: float, unit_weight_kn_m3: float) -> float:
    vs = max(float(vs_m_s), 1.0e-9)
    unit_weight = max(float(unit_weight_kn_m3), 1.0e-9)
    density_t_m3 = unit_weight / WATER_UNIT_WEIGHT_KN_M3
    return float(max(density_t_m3 * vs * vs, 1.0e-9))


def mean_effective_stress_from_k0(
    sigma_v_eff_mid_kpa: float,
    k0: float,
) -> float:
    sigma_v = max(float(sigma_v_eff_mid_kpa), 0.0)
    k0_value = max(float(k0), 0.0)
    return float(sigma_v * (1.0 + (2.0 * k0_value)) / 3.0)


def compute_layer_stress_states(
    layers: list[Any],
    *,
    water_table_depth_m: float | None = None,
) -> list[LayerStressState]:
    states: list[LayerStressState] = []
    depth_top = 0.0
    sigma_total_top = 0.0
    water_depth = None if water_table_depth_m is None else float(water_table_depth_m)

    for idx, layer in enumerate(layers):
        thickness_m = max(float(_layer_value(layer, "thickness_m", "thickness", default=0.0)), 0.0)
        unit_weight_kn_m3 = max(
            float(_layer_value(layer, "unit_weight_kn_m3", "unit_weight_kN_m3", "unit_weight", default=0.0)),
            0.0,
        )
        depth_bot = depth_top + thickness_m
        z_mid = depth_top + (0.5 * thickness_m)
        sigma_v0_mid = sigma_total_top + (0.5 * thickness_m * unit_weight_kn_m3)
        if water_depth is None:
            pore_pressure = 0.0
        else:
            pore_pressure = max(z_mid - water_depth, 0.0) * WATER_UNIT_WEIGHT_KN_M3
        sigma_v_eff = max(sigma_v0_mid - pore_pressure, 0.0)
        states.append(
            LayerStressState(
                index=idx,
                z_top_m=float(depth_top),
                z_bottom_m=float(depth_bot),
                z_mid_m=float(z_mid),
                thickness_m=float(thickness_m),
                sigma_v0_mid_kpa=float(sigma_v0_mid),
                pore_water_pressure_kpa=float(pore_pressure),
                sigma_v_eff_mid_kpa=float(sigma_v_eff),
            )
        )
        depth_top = depth_bot
        sigma_total_top += thickness_m * unit_weight_kn_m3
    return states


def _material_modulus_reduction(
    material: MaterialType,
    params: dict[str, float],
    strain: FloatArray,
    *,
    gmax_fallback: float,
) -> FloatArray:
    if material == MaterialType.MKZ:
        gamma_ref = float(params.get("gamma_ref", 1.0e-3))
        return mkz_modulus_reduction(
            strain,
            gamma_ref=gamma_ref,
            g_reduction_min=float(params.get("g_reduction_min", 0.0)),
        )
    if material == MaterialType.GQH:
        return gqh_modulus_reduction_from_params(
            strain,
            params,
            gmax_fallback=gmax_fallback,
        )
    return np.ones_like(strain, dtype=np.float64)


def compute_implied_strength_diagnostics(
    *,
    material: MaterialType,
    params: dict[str, float],
    vs_m_s: float,
    unit_weight_kn_m3: float,
    sigma_v_eff_mid_kpa: float,
    strain: FloatArray | None = None,
) -> tuple[float | None, float | None, float | None]:
    gmax_kpa = float(params.get("gmax", gmax_from_vs_unit_weight(vs_m_s, unit_weight_kn_m3)))
    if gmax_kpa <= 0.0:
        return None, None, None
    strain_values = (
        np.asarray(strain, dtype=np.float64)
        if strain is not None
        else np.logspace(-6, -1, 80, dtype=np.float64)
    )
    strain_values = strain_values[np.isfinite(strain_values) & (strain_values > 0.0)]
    if strain_values.size == 0:
        return None, None, None

    reduction = _material_modulus_reduction(
        material,
        params,
        strain_values,
        gmax_fallback=gmax_kpa,
    )
    tau_curve = gmax_kpa * reduction * strain_values
    implied_strength = float(np.max(tau_curve)) if tau_curve.size else None
    if implied_strength is None:
        return None, None, None
    sigma_eff = max(float(sigma_v_eff_mid_kpa), 0.0)
    if sigma_eff <= 0.0:
        return implied_strength, None, None
    normalized = float(implied_strength / sigma_eff)
    phi_deg = float(np.degrees(np.arctan(normalized)))
    return implied_strength, normalized, phi_deg


def compute_profile_diagnostics(
    layers: list[Any],
    *,
    water_table_depth_m: float | None = None,
    strain: FloatArray | None = None,
) -> list[LayerProfileDiagnostics]:
    states = compute_layer_stress_states(
        layers,
        water_table_depth_m=water_table_depth_m,
    )
    out: list[LayerProfileDiagnostics] = []
    for idx, (layer, state) in enumerate(zip(layers, states, strict=False)):
        unit_weight_kn_m3 = max(
            float(_layer_value(layer, "unit_weight_kn_m3", "unit_weight_kN_m3", "unit_weight", default=0.0)),
            0.0,
        )
        vs_m_s = max(float(_layer_value(layer, "vs_m_s", "vs", default=0.0)), 0.0)
        thickness_m = max(float(_layer_value(layer, "thickness_m", "thickness", default=0.0)), 0.0)
        material = _layer_material(layer)
        params = _layer_material_params(layer)
        damping_min = params.get("damping_min")
        f_max = (vs_m_s / (4.0 * thickness_m)) if thickness_m > 0.0 and vs_m_s > 0.0 else None
        implied_strength, normalized_strength, implied_phi = compute_implied_strength_diagnostics(
            material=material,
            params=params,
            vs_m_s=vs_m_s,
            unit_weight_kn_m3=unit_weight_kn_m3,
            sigma_v_eff_mid_kpa=state.sigma_v_eff_mid_kpa,
            strain=strain,
        )
        gqh_mode = gqh_mode_from_params(params) if material == MaterialType.GQH else None
        out.append(
            LayerProfileDiagnostics(
                index=idx,
                name=str(_layer_value(layer, "name", default=f"Layer {idx + 1}")),
                material=material.value,
                thickness_m=thickness_m,
                unit_weight_kn_m3=unit_weight_kn_m3,
                vs_m_s=vs_m_s,
                z_top_m=state.z_top_m,
                z_bottom_m=state.z_bottom_m,
                z_mid_m=state.z_mid_m,
                sigma_v0_mid_kpa=state.sigma_v0_mid_kpa,
                sigma_v_eff_mid_kpa=state.sigma_v_eff_mid_kpa,
                pore_water_pressure_kpa=state.pore_water_pressure_kpa,
                small_strain_damping_ratio=float(damping_min) if damping_min is not None else None,
                max_frequency_hz=float(f_max) if f_max is not None else None,
                implied_strength_kpa=implied_strength,
                normalized_implied_strength=normalized_strength,
                implied_friction_angle_deg=implied_phi,
                gqh_mode=gqh_mode,
            )
        )
    return out
