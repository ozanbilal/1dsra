from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials import (
    bounded_damping_from_reduction,
    gqh_modulus_reduction,
    mkz_modulus_reduction,
)
from dsra1d.types import Motion

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True, frozen=True)
class ShearBeamResponse:
    time: FloatArray
    surface_acc: FloatArray
    element_max_abs_strain: FloatArray
    layer_max_abs_strain: dict[int, float]


@dataclass(slots=True, frozen=True)
class EquivalentLinearResponse:
    response: ShearBeamResponse
    iterations: int
    converged: bool
    max_change_history: list[float]
    layer_vs_m_s: dict[int, float]
    layer_damping: dict[int, float]
    layer_gamma_eff: dict[int, float]


def _layer_damping(material: MaterialType, params: dict[str, float]) -> float:
    if material in {MaterialType.MKZ, MaterialType.GQH}:
        return float(np.clip(params.get("damping_min", 0.02), 0.0, 0.20))
    if material in {MaterialType.PM4SAND, MaterialType.PM4SILT}:
        return 0.05
    return 0.02


def _solve_shear_beam_response(
    config: ProjectConfig,
    motion: Motion,
    *,
    layer_vs_m_s: dict[int, float] | None = None,
    layer_damping: dict[int, float] | None = None,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> ShearBeamResponse:
    if motion.acc.size < 2:
        raise ValueError("Motion must contain at least 2 samples for linear response.")

    layer_slices = build_layer_slices(
        config,
        points_per_wavelength=points_per_wavelength,
        min_dz_m=min_dz_m,
    )
    element_slices = build_element_slices(layer_slices)
    if not element_slices:
        raise ValueError("Profile discretization produced zero elements.")

    layer_by_idx = {layer.index: layer for layer in layer_slices}
    cfg_layers = config.profile.layers
    area = float(config.opensees.column_width_m * config.opensees.thickness_m)
    if area <= 0.0:
        area = 1.0

    n_elem = len(element_slices)
    n_nodes = n_elem + 1
    n_free = n_nodes - 1  # base-fixed model

    m_elem = np.zeros(n_elem, dtype=np.float64)
    k_elem = np.zeros(n_elem, dtype=np.float64)
    c_elem = np.zeros(n_elem, dtype=np.float64)

    for j, elem in enumerate(element_slices):
        layer_slice = layer_by_idx[elem.layer_index]
        cfg_layer = cfg_layers[layer_slice.index - 1]
        rho = float(max(cfg_layer.unit_weight_kn_m3 / 9.81, 1.0e-6))
        if layer_vs_m_s is not None:
            vs_layer = layer_vs_m_s.get(layer_slice.index, cfg_layer.vs_m_s)
        else:
            vs_layer = cfg_layer.vs_m_s
        vs = float(max(vs_layer, 1.0e-6))
        dz = float(max(elem.dz_m, 1.0e-6))
        if layer_damping is not None:
            xi_layer = layer_damping.get(
                layer_slice.index,
                _layer_damping(cfg_layer.material, cfg_layer.material_params),
            )
        else:
            xi_layer = _layer_damping(cfg_layer.material, cfg_layer.material_params)
        xi = float(np.clip(xi_layer, 0.0, 0.5))
        g_mod = rho * vs * vs
        m_j = rho * area * dz
        k_j = g_mod * area / dz
        c_j = 2.0 * xi * np.sqrt(max(k_j * m_j, 1.0e-12))
        m_elem[j] = m_j
        k_elem[j] = k_j
        c_elem[j] = c_j

    m_diag_full = np.zeros(n_nodes, dtype=np.float64)
    m_diag_full[0] += 0.5 * m_elem[0]
    m_diag_full[-1] += 0.5 * m_elem[-1]
    for j in range(n_elem - 1):
        m_diag_full[j + 1] += 0.5 * (m_elem[j] + m_elem[j + 1])
    m_diag = m_diag_full[:n_free]

    k_full = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    c_full = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    for j in range(n_elem):
        i0 = j
        i1 = j + 1
        k = k_elem[j]
        c = c_elem[j]
        k_full[i0, i0] += k
        k_full[i0, i1] -= k
        k_full[i1, i0] -= k
        k_full[i1, i1] += k
        c_full[i0, i0] += c
        c_full[i0, i1] -= c
        c_full[i1, i0] -= c
        c_full[i1, i1] += c

    k_mat = k_full[:n_free, :n_free]
    c_mat = c_full[:n_free, :n_free]
    m_mat = np.diag(m_diag)

    dt = float(motion.dt)
    acc_g = np.asarray(motion.acc, dtype=np.float64)
    n_steps = acc_g.size
    time = np.arange(n_steps, dtype=np.float64) * dt

    beta = 0.25
    gamma = 0.50
    a0 = 1.0 / (beta * dt * dt)
    a1 = gamma / (beta * dt)
    a2 = 1.0 / (beta * dt)
    a3 = (1.0 / (2.0 * beta)) - 1.0
    a4 = (gamma / beta) - 1.0
    a5 = dt * ((gamma / (2.0 * beta)) - 1.0)

    force = -np.outer(m_diag, acc_g)
    u = np.zeros((n_free, n_steps), dtype=np.float64)
    v = np.zeros((n_free, n_steps), dtype=np.float64)
    acc_rel = np.zeros((n_free, n_steps), dtype=np.float64)
    if n_free > 0:
        rhs0 = force[:, 0] - (c_mat @ v[:, 0]) - (k_mat @ u[:, 0])
        acc_rel[:, 0] = np.linalg.solve(m_mat, rhs0)

    k_eff = k_mat + (a0 * m_mat) + (a1 * c_mat)
    k_eff_inv = np.linalg.inv(k_eff)

    for i in range(1, n_steps):
        rhs = (
            force[:, i]
            + (m_mat @ ((a0 * u[:, i - 1]) + (a2 * v[:, i - 1]) + (a3 * acc_rel[:, i - 1])))
            + (c_mat @ ((a1 * u[:, i - 1]) + (a4 * v[:, i - 1]) + (a5 * acc_rel[:, i - 1])))
        )
        u[:, i] = k_eff_inv @ rhs
        acc_rel[:, i] = (
            (a0 * (u[:, i] - u[:, i - 1]))
            - (a2 * v[:, i - 1])
            - (a3 * acc_rel[:, i - 1])
        )
        v[:, i] = v[:, i - 1] + dt * (
            (1.0 - gamma) * acc_rel[:, i - 1] + gamma * acc_rel[:, i]
        )

    if n_free == 0:
        surface_acc = acc_g.copy()
        u_full = np.zeros((n_nodes, n_steps), dtype=np.float64)
    else:
        surface_acc = acc_rel[0, :] + acc_g
        u_full = np.zeros((n_nodes, n_steps), dtype=np.float64)
        u_full[:n_free, :] = u

    elem_max_abs = np.zeros(n_elem, dtype=np.float64)
    layer_max_abs: dict[int, float] = {}
    for j, elem in enumerate(element_slices):
        dz = float(max(elem.dz_m, 1.0e-9))
        gamma_t = (u_full[j, :] - u_full[j + 1, :]) / dz
        gamma_max = float(np.max(np.abs(gamma_t)))
        elem_max_abs[j] = gamma_max
        prev = layer_max_abs.get(elem.layer_index, 0.0)
        layer_max_abs[elem.layer_index] = max(prev, gamma_max)

    return ShearBeamResponse(
        time=time,
        surface_acc=surface_acc,
        element_max_abs_strain=elem_max_abs,
        layer_max_abs_strain=layer_max_abs,
    )


def solve_linear_sh_response(
    config: ProjectConfig,
    motion: Motion,
    *,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> tuple[FloatArray, FloatArray]:
    response = _solve_shear_beam_response(
        config=config,
        motion=motion,
        points_per_wavelength=points_per_wavelength,
        min_dz_m=min_dz_m,
    )
    return response.time, response.surface_acc


def solve_equivalent_linear_sh_response(
    config: ProjectConfig,
    motion: Motion,
    *,
    max_iterations: int = 12,
    convergence_tol: float = 0.03,
    strain_ratio: float = 0.65,
    relaxation: float = 0.6,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> EquivalentLinearResponse:
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1.")
    if not (0.0 < convergence_tol < 1.0):
        raise ValueError("convergence_tol must be within (0, 1).")
    if not (0.0 < strain_ratio <= 1.0):
        raise ValueError("strain_ratio must be within (0, 1].")
    if not (0.0 < relaxation <= 1.0):
        raise ValueError("relaxation must be within (0, 1].")

    base_vs: dict[int, float] = {
        idx: float(max(layer.vs_m_s, 1.0e-6))
        for idx, layer in enumerate(config.profile.layers, start=1)
    }
    cur_vs = dict(base_vs)
    cur_damping: dict[int, float] = {
        idx: _layer_damping(layer.material, layer.material_params)
        for idx, layer in enumerate(config.profile.layers, start=1)
    }
    cur_gamma_eff: dict[int, float] = {idx: 0.0 for idx in base_vs}
    max_change_history: list[float] = []
    converged = False
    last_response: ShearBeamResponse | None = None

    for iteration in range(1, max_iterations + 1):
        response = _solve_shear_beam_response(
            config=config,
            motion=motion,
            layer_vs_m_s=cur_vs,
            layer_damping=cur_damping,
            points_per_wavelength=points_per_wavelength,
            min_dz_m=min_dz_m,
        )
        last_response = response

        next_vs: dict[int, float] = {}
        next_damping: dict[int, float] = {}
        next_gamma_eff: dict[int, float] = {}
        max_change = 0.0

        for idx, layer in enumerate(config.profile.layers, start=1):
            gamma_max = float(response.layer_max_abs_strain.get(idx, 0.0))
            gamma_eff = max(float(strain_ratio * gamma_max), 1.0e-9)
            next_gamma_eff[idx] = gamma_eff
            g_reduction = 1.0
            damping_new = _layer_damping(layer.material, layer.material_params)

            if layer.material == MaterialType.MKZ:
                gamma_ref = float(layer.material_params.get("gamma_ref", 0.001))
                g_reduction = float(
                    mkz_modulus_reduction(
                        np.array([gamma_eff], dtype=np.float64),
                        gamma_ref=gamma_ref,
                    )[0]
                )
                g_reduction = float(np.clip(g_reduction, 0.05, 1.0))
                damping_new = float(
                    bounded_damping_from_reduction(
                        np.array([g_reduction], dtype=np.float64),
                        damping_min=float(layer.material_params.get("damping_min", 0.01)),
                        damping_max=float(layer.material_params.get("damping_max", 0.12)),
                    )[0]
                )
            elif layer.material == MaterialType.GQH:
                gamma_ref = float(layer.material_params.get("gamma_ref", 0.001))
                g_reduction = float(
                    gqh_modulus_reduction(
                        np.array([gamma_eff], dtype=np.float64),
                        gamma_ref=gamma_ref,
                        a1=float(layer.material_params.get("a1", 1.0)),
                        a2=float(layer.material_params.get("a2", 0.0)),
                        m=float(layer.material_params.get("m", 1.0)),
                    )[0]
                )
                g_reduction = float(np.clip(g_reduction, 0.05, 1.0))
                damping_new = float(
                    bounded_damping_from_reduction(
                        np.array([g_reduction], dtype=np.float64),
                        damping_min=float(layer.material_params.get("damping_min", 0.01)),
                        damping_max=float(layer.material_params.get("damping_max", 0.12)),
                    )[0]
                )

            vs_target = float(max(base_vs[idx] * np.sqrt(g_reduction), 1.0e-6))
            vs_prev = float(cur_vs[idx])
            vs_updated = float((1.0 - relaxation) * vs_prev + relaxation * vs_target)
            rel_change = abs(vs_updated - vs_prev) / max(vs_prev, 1.0e-9)
            max_change = max(max_change, rel_change)
            next_vs[idx] = vs_updated
            next_damping[idx] = float(np.clip(damping_new, 0.0, 0.5))

        cur_vs = next_vs
        cur_damping = next_damping
        cur_gamma_eff = next_gamma_eff
        max_change_history.append(float(max_change))
        if max_change < convergence_tol and iteration >= 2:
            converged = True
            break

    if last_response is None:
        raise RuntimeError("EQL solver did not produce a response.")

    return EquivalentLinearResponse(
        response=last_response,
        iterations=len(max_change_history),
        converged=converged,
        max_change_history=max_change_history,
        layer_vs_m_s=cur_vs,
        layer_damping=cur_damping,
        layer_gamma_eff=cur_gamma_eff,
    )
