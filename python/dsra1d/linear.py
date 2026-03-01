from __future__ import annotations

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.types import Motion

FloatArray = npt.NDArray[np.float64]


def _layer_damping(material: MaterialType, params: dict[str, float]) -> float:
    if material in {MaterialType.MKZ, MaterialType.GQH}:
        return float(np.clip(params.get("damping_min", 0.02), 0.0, 0.20))
    if material in {MaterialType.PM4SAND, MaterialType.PM4SILT}:
        return 0.05
    return 0.02


def solve_linear_sh_response(
    config: ProjectConfig,
    motion: Motion,
    *,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> tuple[FloatArray, FloatArray]:
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
        vs = float(max(cfg_layer.vs_m_s, 1.0e-6))
        dz = float(max(elem.dz_m, 1.0e-6))
        xi = _layer_damping(cfg_layer.material, cfg_layer.material_params)
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
    else:
        surface_acc = acc_rel[0, :] + acc_g
    return time, surface_acc
