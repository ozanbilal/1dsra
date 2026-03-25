from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from dsra1d.config import BoundaryCondition, MaterialType, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials import gqh_backbone_stress, mkz_backbone_stress
from dsra1d.materials.damping import (
    layer_damping as _layer_damping,
    rayleigh_coefficients as _rayleigh_coefficients,
)
from dsra1d.materials.mrdf import MRDFCoefficients, evaluate_mrdf_factor, mrdf_coefficients_from_params
from dsra1d.types import Motion

FloatArray = npt.NDArray[np.float64]


def _integrate_acc_to_velocity(acc: FloatArray, dt: float) -> FloatArray:
    vel = np.zeros_like(acc, dtype=np.float64)
    if acc.size < 2 or dt <= 0.0:
        return vel
    vel[1:] = np.cumsum(0.5 * (acc[1:] + acc[:-1]) * dt, dtype=np.float64)
    return vel


def _assemble_tridiagonal_from_element_values(
    elem_values: npt.ArrayLike,
    n_nodes: int,
) -> FloatArray:
    values = np.asarray(elem_values, dtype=np.float64)
    mat = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    for j, val_raw in enumerate(values):
        i0 = j
        i1 = j + 1
        val = float(max(val_raw, 0.0))
        mat[i0, i0] += val
        mat[i0, i1] -= val
        mat[i1, i0] -= val
        mat[i1, i1] += val
    return mat


def _element_backbone_stress(
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
        g_red_min = float(params.get("g_reduction_min", 0.0))
        tau = mkz_backbone_stress(
            np.array([gamma], dtype=np.float64),
            gmax=gmax,
            gamma_ref=gamma_ref,
            tau_max=tau_max,
            g_reduction_min=g_red_min,
        )
        return float(tau[0])

    if material == MaterialType.GQH:
        gmax = float(params.get("gmax", gmax_fallback))
        gamma_ref = float(params.get("gamma_ref", 1.0e-3))
        tau_max_raw = params.get("tau_max")
        tau_max = float(tau_max_raw) if tau_max_raw is not None else None
        g_red_min = float(params.get("g_reduction_min", 0.0))
        tau = gqh_backbone_stress(
            np.array([gamma], dtype=np.float64),
            gmax=gmax,
            gamma_ref=gamma_ref,
            a1=float(params.get("a1", 1.0)),
            a2=float(params.get("a2", 0.0)),
            m=float(params.get("m", 1.0)),
            tau_max=tau_max,
            g_reduction_min=g_red_min,
        )
        return float(tau[0])

    return gmax_fallback * gamma


def _strain_direction(delta_gamma: float, eps: float) -> int:
    if delta_gamma > eps:
        return 1
    if delta_gamma < -eps:
        return -1
    return 0


@dataclass(slots=True)
class _ElementConstitutiveState:
    material: MaterialType
    params: dict[str, float]
    gmax_fallback: float
    reload_factor: float
    mrdf_coeffs: MRDFCoefficients | None = None
    eps_gamma: float = 1.0e-12
    initialized: bool = False
    direction: int = 0
    gamma_prev: float = 0.0
    tau_prev: float = 0.0
    gamma_rev: float = 0.0
    tau_rev: float = 0.0
    has_reversal: bool = False

    def _backbone(self, gamma: float) -> float:
        return _element_backbone_stress(
            self.material,
            self.params,
            gamma,
            gmax_fallback=self.gmax_fallback,
        )

    def update_stress(self, gamma: float) -> float:
        if self.material not in {MaterialType.MKZ, MaterialType.GQH}:
            tau = self._backbone(gamma)
            self.gamma_prev = gamma
            self.tau_prev = tau
            self.initialized = True
            return tau

        if not self.initialized:
            tau = self._backbone(gamma)
            delta_gamma = gamma - self.gamma_prev
            self.direction = _strain_direction(delta_gamma, self.eps_gamma)
            if self.direction == 0:
                self.direction = 1 if gamma >= 0.0 else -1
            self.gamma_prev = gamma
            self.tau_prev = tau
            self.gamma_rev = 0.0
            self.tau_rev = 0.0
            self.initialized = True
            return tau

        delta_gamma = gamma - self.gamma_prev
        new_direction = _strain_direction(delta_gamma, self.eps_gamma)
        if new_direction != 0 and new_direction != self.direction:
            self.gamma_rev = self.gamma_prev
            self.tau_rev = self.tau_prev
            self.direction = new_direction
            self.has_reversal = True

        if self.direction == 0:
            self.direction = 1 if gamma >= self.gamma_prev else -1

        if not self.has_reversal:
            tau = self._backbone(gamma)
        else:
            # Generalized Masing-type branch update.
            # reload_factor=2.0 -> classical Masing,
            # reload_factor!=2.0 -> non-Masing approximation.
            k = max(self.reload_factor, 1.0e-6)
            shifted_gamma = (gamma - self.gamma_rev) / k
            tau_masing = self.tau_rev + (k * self._backbone(shifted_gamma))

            if self.mrdf_coeffs is not None:
                # Phillips-Hashash MRDF correction:
                # tau = tau_bb + F * (tau_masing - tau_bb)
                # F < 1 at large strains reduces loop area to match target damping
                gamma_amp = abs(gamma - self.gamma_rev) / 2.0
                f_mrdf = evaluate_mrdf_factor(self.mrdf_coeffs, gamma_amp)
                tau_bb = self._backbone(gamma)
                tau = tau_bb + f_mrdf * (tau_masing - tau_bb)
            else:
                tau = tau_masing

        self.gamma_prev = gamma
        self.tau_prev = tau
        return tau

    def tangent_modulus(self, gamma: float) -> float:
        """Return d(tau)/d(gamma) at given strain WITHOUT mutating state."""
        if self.material not in {MaterialType.MKZ, MaterialType.GQH}:
            return self.gmax_fallback

        gmax = float(self.params.get("gmax", self.gmax_fallback))
        gamma_ref = float(self.params.get("gamma_ref", 1.0e-3))
        g_red_min = float(self.params.get("g_reduction_min", 0.0))
        # Tangent floor from G/Gmax floor: ensures tangent >= gmax * g_reduction_min
        tangent_floor = max(gmax * g_red_min, gmax * 1.0e-4)

        def _backbone_tangent(g: float) -> float:
            ag = abs(g)
            if self.material == MaterialType.GQH:
                a1 = float(self.params.get("a1", 1.0))
                a2 = float(self.params.get("a2", 0.0))
                m = float(self.params.get("m", 1.0))
                r = ag / max(gamma_ref, 1.0e-15)
                denom = 1.0 + a1 * r + a2 * (r ** m)
                return max(gmax / (denom * denom), tangent_floor)
            # MKZ: G_t = gmax / (1 + |gamma|/gamma_ref)^2
            ratio = ag / max(gamma_ref, 1.0e-15)
            denom = 1.0 + ratio
            return max(gmax / (denom * denom), tangent_floor)

        if not self.has_reversal:
            return _backbone_tangent(gamma)
        # Masing branch: tangent at shifted strain
        k = max(self.reload_factor, 1.0e-6)
        shifted = (gamma - self.gamma_rev) / k
        g_t_masing = _backbone_tangent(shifted)
        if self.mrdf_coeffs is not None:
            gamma_amp = abs(gamma - self.gamma_rev) / 2.0
            f_mrdf = evaluate_mrdf_factor(self.mrdf_coeffs, gamma_amp)
            g_t_bb = _backbone_tangent(gamma)
            return g_t_bb + f_mrdf * (g_t_masing - g_t_bb)
        return g_t_masing


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
    use_elastic_halfspace = config.boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE
    n_free = n_nodes if use_elastic_halfspace else (n_nodes - 1)

    m_elem = np.zeros(n_elem, dtype=np.float64)
    k_elem = np.zeros(n_elem, dtype=np.float64)
    c_elem = np.zeros(n_elem, dtype=np.float64)
    xi_elem = np.zeros(n_elem, dtype=np.float64)
    dz_elem = np.zeros(n_elem, dtype=np.float64)
    constitutive_states: list[_ElementConstitutiveState] = []

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
        xi_elem[j] = xi
        dz_elem[j] = dz
        reload_factor_raw = cfg_layer.material_params.get("reload_factor", 2.0)
        reload_factor = float(np.clip(reload_factor_raw, 0.5, 4.0))
        constitutive_states.append(
            _ElementConstitutiveState(
                material=cfg_layer.material,
                params=cfg_layer.material_params,
                gmax_fallback=g_mod,
                reload_factor=reload_factor,
                mrdf_coeffs=mrdf_coefficients_from_params(cfg_layer.material_params),
            )
        )

    m_diag_full = np.zeros(n_nodes, dtype=np.float64)
    m_diag_full[0] += 0.5 * m_elem[0]
    m_diag_full[-1] += 0.5 * m_elem[-1]
    for j in range(n_elem - 1):
        m_diag_full[j + 1] += 0.5 * (m_elem[j] + m_elem[j + 1])
    m_diag = m_diag_full[:n_free]
    if np.any(m_diag <= 0.0):
        raise ValueError("Non-positive nodal mass encountered in nonlinear solver.")
    m_mat = np.diag(m_diag)
    c_full = _assemble_tridiagonal_from_element_values(c_elem, n_nodes)
    dashpot_c = 0.0
    if use_elastic_halfspace:
        base_layer = cfg_layers[-1]
        base_rho = float(max(base_layer.unit_weight_kn_m3 / 9.81, 1.0e-6))
        base_vs = float(max(base_layer.vs_m_s, 1.0e-6))
        dashpot_c = base_rho * base_vs * area
        c_full[-1, -1] += dashpot_c
    c_mat = c_full[:n_free, :n_free]
    k_initial_full = _assemble_tridiagonal_from_element_values(k_elem, n_nodes)
    k_initial = k_initial_full[:n_free, :n_free]

    use_rayleigh = config.analysis.damping_mode == "rayleigh"
    viscous_damping_update = (
        not use_rayleigh and bool(config.analysis.viscous_damping_update)
    )
    if use_rayleigh:
        xi_target = float(np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12)))
        alpha_rayleigh, beta_rayleigh = _rayleigh_coefficients(
            damping_ratio=xi_target,
            mode_1_hz=config.analysis.rayleigh_mode_1_hz,
            mode_2_hz=config.analysis.rayleigh_mode_2_hz,
        )
        c_rayleigh_const = (alpha_rayleigh * m_mat) + (beta_rayleigh * k_initial)
        rayleigh_update_matrix = bool(config.analysis.rayleigh_update_matrix)
    else:
        alpha_rayleigh = 0.0
        beta_rayleigh = 0.0
        c_rayleigh_const = c_mat
        rayleigh_update_matrix = False

    dt = float(motion.dt)
    dt_sub = dt / float(substeps)
    acc_g = np.asarray(motion.acc, dtype=np.float64)
    n_steps = acc_g.size
    time = np.arange(n_steps, dtype=np.float64) * dt
    input_vel = _integrate_acc_to_velocity(acc_g, dt) if use_elastic_halfspace else None

    u = np.zeros((n_free,), dtype=np.float64)
    v = np.zeros((n_free,), dtype=np.float64)
    a_rel_hist = np.zeros((n_free, n_steps), dtype=np.float64)
    a_prev = np.zeros((n_free,), dtype=np.float64)

    need_secant = rayleigh_update_matrix or viscous_damping_update

    for i in range(n_steps):
        ag = float(acc_g[i])
        for _ in range(substeps):
            u_full = np.zeros((n_nodes,), dtype=np.float64)
            u_full[:n_free] = u
            f_int_full = np.zeros((n_nodes,), dtype=np.float64)
            k_sec_elem = np.zeros(n_elem, dtype=np.float64) if need_secant else None
            for j in range(n_elem):
                dz = float(max(dz_elem[j], 1.0e-9))
                gamma = float((u_full[j] - u_full[j + 1]) / dz)
                tau = constitutive_states[j].update_stress(gamma)
                force = tau * area
                f_int_full[j] += force
                f_int_full[j + 1] -= force
                if k_sec_elem is not None:
                    if abs(gamma) > 1.0e-10:
                        g_sec = abs(float(tau) / gamma)
                    else:
                        g_sec = constitutive_states[j].gmax_fallback
                    k_sec_elem[j] = max(g_sec * area / dz, 1.0e-9)
            f_int = f_int_full[:n_free]
            if use_elastic_halfspace:
                assert input_vel is not None
                f_ext = np.zeros_like(m_diag)
                f_ext[-1] = 2.0 * base_rho * base_vs * area * input_vel[i]
            else:
                f_ext = -m_diag * ag
            if k_sec_elem is not None:
                if rayleigh_update_matrix:
                    k_sec_full = _assemble_tridiagonal_from_element_values(k_sec_elem, n_nodes)
                    k_sec = k_sec_full[:n_free, :n_free]
                    c_step = (alpha_rayleigh * m_mat) + (beta_rayleigh * k_sec)
                elif viscous_damping_update:
                    # DEEPSOIL-equivalent: update viscous damping from secant stiffness
                    c_updated = np.zeros(n_elem, dtype=np.float64)
                    for j in range(n_elem):
                        c_updated[j] = 2.0 * xi_elem[j] * np.sqrt(
                            max(k_sec_elem[j] * m_elem[j], 1.0e-12)
                        )
                    c_step_full = _assemble_tridiagonal_from_element_values(c_updated, n_nodes)
                    if use_elastic_halfspace:
                        c_step_full[-1, -1] += dashpot_c
                    c_step = c_step_full[:n_free, :n_free]
                else:
                    c_step = c_rayleigh_const
            else:
                c_step = c_rayleigh_const
            a_curr = (f_ext - (c_step @ v) - f_int) / m_diag
            v = v + dt_sub * a_curr
            u = u + dt_sub * v
            a_prev = a_curr
        a_rel_hist[:, i] = a_prev

    if n_free == 0:
        surface_acc = acc_g.copy()
    else:
        if use_elastic_halfspace:
            surface_acc = a_rel_hist[0, :]
        else:
            surface_acc = a_rel_hist[0, :] + acc_g
    return time, surface_acc


def simulate_hysteretic_stress_path(
    material: MaterialType,
    material_params: dict[str, float],
    strain_path: npt.ArrayLike,
    *,
    gmax_fallback: float,
) -> FloatArray:
    """Simulate stress response for a prescribed strain path using nonlinear constitutive state."""
    gamma = np.asarray(strain_path, dtype=np.float64)
    if gamma.size == 0:
        raise ValueError("strain_path must contain at least one sample.")
    if gmax_fallback <= 0.0:
        raise ValueError("gmax_fallback must be > 0.")

    reload_factor_raw = material_params.get("reload_factor", 2.0)
    reload_factor = float(np.clip(reload_factor_raw, 0.5, 4.0))
    state = _ElementConstitutiveState(
        material=material,
        params=material_params,
        gmax_fallback=gmax_fallback,
        reload_factor=reload_factor,
        mrdf_coeffs=mrdf_coefficients_from_params(material_params),
    )
    tau = np.zeros_like(gamma)
    for i, g in enumerate(gamma):
        tau[i] = state.update_stress(float(g))
    return tau
