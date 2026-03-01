from __future__ import annotations

import numpy as np
import numpy.typing as npt

from dsra1d.config import MaterialType, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials import gqh_backbone_stress, mkz_backbone_stress
from dsra1d.types import Motion

FloatArray = npt.NDArray[np.float64]


def _layer_damping(material: MaterialType, params: dict[str, float]) -> float:
    if material in {MaterialType.MKZ, MaterialType.GQH}:
        return float(np.clip(params.get("damping_min", 0.02), 0.0, 0.30))
    if material in {MaterialType.PM4SAND, MaterialType.PM4SILT}:
        return 0.05
    return 0.02


def _element_stress(
    material: MaterialType,
    params: dict[str, float],
    gamma: float,
    gmax_fallback: float,
) -> float:
    if material == MaterialType.MKZ:
        gmax = float(params.get("gmax", gmax_fallback))
        gamma_ref = float(params.get("gamma_ref", 1.0e-3))
        tau_max_raw = params.get("tau_max")
        tau_max = float(tau_max_raw) if tau_max_raw is not None else None
        tau = mkz_backbone_stress(
            np.array([gamma], dtype=np.float64),
            gmax=gmax,
            gamma_ref=gamma_ref,
            tau_max=tau_max,
        )
        return float(tau[0])

    if material == MaterialType.GQH:
        gmax = float(params.get("gmax", gmax_fallback))
        gamma_ref = float(params.get("gamma_ref", 1.0e-3))
        tau_max_raw = params.get("tau_max")
        tau_max = float(tau_max_raw) if tau_max_raw is not None else None
        tau = gqh_backbone_stress(
            np.array([gamma], dtype=np.float64),
            gmax=gmax,
            gamma_ref=gamma_ref,
            a1=float(params.get("a1", 1.0)),
            a2=float(params.get("a2", 0.0)),
            m=float(params.get("m", 1.0)),
            tau_max=tau_max,
        )
        return float(tau[0])

    return gmax_fallback * gamma


def solve_nonlinear_sh_response(
    config: ProjectConfig,
    motion: Motion,
    *,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
    substeps: int = 4,
) -> tuple[FloatArray, FloatArray]:
    if motion.acc.size < 2:
        raise ValueError("Motion must contain at least 2 samples for nonlinear response.")
    if substeps < 1:
        raise ValueError("substeps must be >= 1.")

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
    c_elem = np.zeros(n_elem, dtype=np.float64)
    dz_elem = np.zeros(n_elem, dtype=np.float64)
    gmax_elem = np.zeros(n_elem, dtype=np.float64)
    mat_elem: list[MaterialType] = []
    params_elem: list[dict[str, float]] = []

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
        c_elem[j] = c_j
        dz_elem[j] = dz
        gmax_elem[j] = g_mod
        mat_elem.append(cfg_layer.material)
        params_elem.append(cfg_layer.material_params)

    m_diag_full = np.zeros(n_nodes, dtype=np.float64)
    m_diag_full[0] += 0.5 * m_elem[0]
    m_diag_full[-1] += 0.5 * m_elem[-1]
    for j in range(n_elem - 1):
        m_diag_full[j + 1] += 0.5 * (m_elem[j] + m_elem[j + 1])
    m_diag = m_diag_full[:n_free]
    if np.any(m_diag <= 0.0):
        raise ValueError("Non-positive nodal mass encountered in nonlinear solver.")

    c_full = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    for j in range(n_elem):
        i0 = j
        i1 = j + 1
        c = c_elem[j]
        c_full[i0, i0] += c
        c_full[i0, i1] -= c
        c_full[i1, i0] -= c
        c_full[i1, i1] += c
    c_mat = c_full[:n_free, :n_free]

    dt = float(motion.dt)
    dt_sub = dt / float(substeps)
    acc_g = np.asarray(motion.acc, dtype=np.float64)
    n_steps = acc_g.size
    time = np.arange(n_steps, dtype=np.float64) * dt

    u = np.zeros((n_free,), dtype=np.float64)
    v = np.zeros((n_free,), dtype=np.float64)
    a_rel_hist = np.zeros((n_free, n_steps), dtype=np.float64)

    for i in range(n_steps):
        ag = float(acc_g[i])
        for _ in range(substeps):
            u_full = np.zeros((n_nodes,), dtype=np.float64)
            u_full[:n_free] = u
            f_int_full = np.zeros((n_nodes,), dtype=np.float64)
            for j in range(n_elem):
                dz = float(max(dz_elem[j], 1.0e-9))
                gamma = float((u_full[j] - u_full[j + 1]) / dz)
                tau = _element_stress(
                    mat_elem[j],
                    params_elem[j],
                    gamma,
                    gmax_fallback=float(gmax_elem[j]),
                )
                force = tau * area
                f_int_full[j] += force
                f_int_full[j + 1] -= force
            f_int = f_int_full[:n_free]
            f_ext = -m_diag * ag
            a = (f_ext - (c_mat @ v) - f_int) / m_diag
            v = v + dt_sub * a
            u = u + dt_sub * v
        a_rel_hist[:, i] = a

    if n_free == 0:
        surface_acc = acc_g.copy()
    else:
        surface_acc = a_rel_hist[0, :] + acc_g
    return time, surface_acc
