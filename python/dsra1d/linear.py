from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from dsra1d.config import BoundaryCondition, MaterialType, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials import (
    bounded_damping_from_reduction,
    gqh_modulus_reduction_from_params,
    mkz_modulus_reduction,
)
from dsra1d.materials.damping import (
    layer_damping as _layer_damping,
    modal_matched_damping_matrix as _modal_matched_damping_matrix,
    rayleigh_coefficients as _rayleigh_coefficients,
)
from dsra1d.motion import build_boundary_excitation
from dsra1d.types import Motion

FloatArray = npt.NDArray[np.float64]


def _solver_column_area(config: ProjectConfig) -> float:
    legacy = getattr(config, "opensees", None)
    if legacy is not None:
        width = float(getattr(legacy, "column_width_m", 1.0))
        thickness = float(getattr(legacy, "thickness_m", 1.0))
        area = width * thickness
        if np.isfinite(area) and area > 0.0:
            return area
    return 1.0


@dataclass(slots=True, frozen=True)
class ShearBeamResponse:
    time: FloatArray
    surface_acc: FloatArray
    element_max_abs_strain: FloatArray
    layer_max_abs_strain: dict[int, float]
    node_depth_m: FloatArray
    nodal_displacement_m: FloatArray


@dataclass(slots=True, frozen=True)
class EquivalentLinearResponse:
    response: ShearBeamResponse
    iterations: int
    converged: bool
    max_change_history: list[float]
    layer_vs_m_s: dict[int, float]
    layer_damping: dict[int, float]
    layer_gamma_eff: dict[int, float]


def _integrate_acc_to_velocity(acc: FloatArray, dt: float) -> FloatArray:
    vel = np.zeros_like(acc, dtype=np.float64)
    if acc.size < 2 or dt <= 0.0:
        return vel
    vel[1:] = np.cumsum(0.5 * (acc[1:] + acc[:-1]) * dt, dtype=np.float64)
    return vel


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
    area = _solver_column_area(config)

    n_elem = len(element_slices)
    n_nodes = n_elem + 1
    use_elastic_halfspace = config.boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE
    n_free = n_nodes if use_elastic_halfspace else (n_nodes - 1)

    m_elem = np.zeros(n_elem, dtype=np.float64)
    k_elem = np.zeros(n_elem, dtype=np.float64)
    xi_elem = np.zeros(n_elem, dtype=np.float64)

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
        m_elem[j] = m_j
        k_elem[j] = k_j
        xi_elem[j] = xi

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
        k_full[i0, i0] += k
        k_full[i0, i1] -= k
        k_full[i1, i0] -= k
        k_full[i1, i1] += k

    if use_elastic_halfspace:
        bedrock = config.effective_bedrock()
        base_rho = float(max(bedrock.unit_weight_kn_m3 / 9.81, 1.0e-6))
        base_vs = float(max(bedrock.vs_m_s, 1.0e-6))
        dashpot_c = base_rho * base_vs * area
        c_full[-1, -1] += dashpot_c

    k_mat = k_full[:n_free, :n_free]
    m_mat = np.diag(m_diag)

    if config.analysis.damping_mode == "rayleigh":
        xi_target = float(np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12)))
        alpha, beta_rayleigh = _rayleigh_coefficients(
            damping_ratio=xi_target,
            mode_1_hz=config.analysis.rayleigh_mode_1_hz,
            mode_2_hz=config.analysis.rayleigh_mode_2_hz,
        )
        c_mat = (alpha * m_mat) + (beta_rayleigh * k_mat)
    else:
        xi_target = float(np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12)))
        c_mat = _modal_matched_damping_matrix(m_diag, k_mat, xi_target)
        if use_elastic_halfspace:
            c_mat = c_mat.copy()
            c_mat[-1, -1] += dashpot_c

    dt = float(motion.dt)
    excitation = build_boundary_excitation(config, motion.acc)
    rigid_input_acc = np.asarray(excitation.within_acceleration_m_s2, dtype=np.float64)
    incident_input_acc = np.asarray(excitation.incident_acceleration_m_s2, dtype=np.float64)
    n_steps = rigid_input_acc.size
    time = np.arange(n_steps, dtype=np.float64) * dt

    beta = 0.25
    gamma = 0.50
    a0 = 1.0 / (beta * dt * dt)
    a1 = gamma / (beta * dt)
    a2 = 1.0 / (beta * dt)
    a3 = (1.0 / (2.0 * beta)) - 1.0
    a4 = (gamma / beta) - 1.0
    a5 = dt * ((gamma / (2.0 * beta)) - 1.0)

    if use_elastic_halfspace:
        bedrock = config.effective_bedrock()
        base_rho = float(max(bedrock.unit_weight_kn_m3 / 9.81, 1.0e-6))
        base_vs = float(max(bedrock.vs_m_s, 1.0e-6))
        input_vel = _integrate_acc_to_velocity(incident_input_acc, dt)
        force = np.zeros((n_free, n_steps), dtype=np.float64)
        force[-1, :] = 2.0 * base_rho * base_vs * area * input_vel
    else:
        force = -np.outer(m_diag, rigid_input_acc)
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
        surface_acc = rigid_input_acc.copy()
        u_full = np.zeros((n_nodes, n_steps), dtype=np.float64)
    else:
        if use_elastic_halfspace:
            surface_acc = acc_rel[0, :]
        else:
            surface_acc = acc_rel[0, :] + rigid_input_acc
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

    node_depth_m = np.zeros(n_nodes, dtype=np.float64)
    for j, elem in enumerate(element_slices):
        node_depth_m[j + 1] = node_depth_m[j] + float(max(elem.dz_m, 0.0))

    return ShearBeamResponse(
        time=time,
        surface_acc=surface_acc,
        element_max_abs_strain=elem_max_abs,
        layer_max_abs_strain=layer_max_abs,
        node_depth_m=node_depth_m,
        nodal_displacement_m=u_full,
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
                g_reduction = float(
                    gqh_modulus_reduction_from_params(
                        np.array([gamma_eff], dtype=np.float64),
                        layer.material_params,
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


# ---------------------------------------------------------------------------
# Frequency-domain transfer function (Thomson-Haskell propagator matrix)
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class FrequencyDomainResult:
    """Result of frequency-domain 1D SH site response."""

    freq_hz: FloatArray
    transfer_function: FloatArray  # complex H(f)
    surface_acc: FloatArray  # time-domain surface acceleration
    time: FloatArray


def solve_frequency_domain_sh(
    config: ProjectConfig,
    motion: Motion,
    *,
    layer_vs_m_s: dict[int, float] | None = None,
    layer_damping: dict[int, float] | None = None,
) -> FrequencyDomainResult:
    """1D SH site response via Thomson-Haskell propagator matrix in frequency domain.

    Layers are numbered 0 (surface) to N-1 (deepest).  The transfer function
    H(f) = u_surface / u_input is computed at each frequency using propagator
    matrices, then applied to the input motion FFT.

    For rigid base: input = base motion (within).
    For elastic halfspace: input = outcrop motion.
    """
    cfg_layers = config.profile.layers
    use_elastic_halfspace = config.boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE
    n_layers = len(cfg_layers)

    # Build layer properties
    h = np.zeros(n_layers, dtype=np.float64)
    rho_arr = np.zeros(n_layers, dtype=np.float64)
    vs_arr = np.zeros(n_layers, dtype=np.float64)
    xi_arr = np.zeros(n_layers, dtype=np.float64)

    for i, layer in enumerate(cfg_layers):
        h[i] = float(layer.thickness_m)
        rho_arr[i] = float(max(layer.unit_weight_kn_m3 / 9.81, 1.0e-6))
        if layer_vs_m_s is not None:
            vs_arr[i] = float(max(layer_vs_m_s.get(i + 1, layer.vs_m_s), 1.0e-6))
        else:
            vs_arr[i] = float(max(layer.vs_m_s, 1.0e-6))
        if layer_damping is not None:
            xi_arr[i] = float(np.clip(
                layer_damping.get(i + 1, _layer_damping(layer.material, layer.material_params)),
                0.0, 0.5,
            ))
        else:
            xi_arr[i] = float(np.clip(_layer_damping(layer.material, layer.material_params), 0.0, 0.5))

    # FFT of input motion
    dt = float(motion.dt)
    acc_input = np.asarray(motion.acc, dtype=np.float64)
    n_samples = acc_input.size
    n_fft = int(2 ** np.ceil(np.log2(n_samples)))
    freq = np.fft.rfftfreq(n_fft, d=dt)
    fft_input = np.fft.rfft(acc_input, n=n_fft)

    # Precompute complex shear modulus and impedance per layer
    # G* = G(1 + 2iD),  Vs* = sqrt(G*/rho),  Z = rho * Vs*
    g_star = np.array(
        [rho_arr[j] * vs_arr[j] ** 2 * (1.0 + 2.0j * xi_arr[j]) for j in range(n_layers)],
        dtype=np.complex128,
    )
    vs_star = np.sqrt(g_star / rho_arr)
    z_arr = rho_arr * vs_star  # complex impedance

    n_freq = len(freq)
    transfer = np.ones(n_freq, dtype=np.complex128)

    for fi in range(n_freq):
        omega = 2.0 * np.pi * freq[fi]
        if omega < 1.0e-12:
            transfer[fi] = 1.0 + 0.0j
            continue

        # Propagator matrix method (Kramer 1996, Sec. 7.2.1)
        # State vector s = [u, tau] at each interface.
        # Layer j propagator (bottom to top):
        #   s_top = P_j * s_bottom
        #   P_j = [[cos(kh), sin(kh)/(kG*)], [-kG*sin(kh), cos(kh)]]
        #
        # Boundary conditions:
        #   Surface (top of layer 0): tau = 0
        #   Rigid base (bottom of layer N-1): u = u_input
        #   Elastic HS: tau_base = Z_hs * i*omega * u_base (radiation)
        #
        # Strategy: propagate two independent basis solutions from base to
        # surface and combine to satisfy tau_surface = 0.
        #
        # Basis 1: s_base = [1, 0]  (unit displacement, zero stress)
        # Basis 2: s_base = [0, 1]  (zero displacement, unit stress)
        # At surface: s = a*P_total*[1,0] + b*P_total*[0,1]
        # Require tau_surface = 0 => a*P21 + b*P22 = 0 => b = -a*P21/P22
        # u_surface = a*P11 + b*P12 = a*(P11 - P21*P12/P22)

        # Compute total propagator matrix P = P_0 * P_1 * ... * P_{N-1}
        p_total = np.eye(2, dtype=np.complex128)
        for j in range(n_layers - 1, -1, -1):
            k_star = omega / vs_star[j]
            phase = k_star * h[j]
            cos_p = np.cos(phase)
            sin_p = np.sin(phase)
            kg = k_star * g_star[j]
            if abs(kg) < 1.0e-30:
                continue
            p_j = np.array([
                [cos_p, sin_p / kg],
                [-kg * sin_p, cos_p],
            ], dtype=np.complex128)
            p_total = p_j @ p_total

        p11, p12 = p_total[0, 0], p_total[0, 1]
        p21, p22 = p_total[1, 0], p_total[1, 1]

        if use_elastic_halfspace:
            # At base: tau_base = Z_hs * i*omega * u_base (radiation condition)
            # s_base = [u_base, Z_hs*i*omega*u_base] = u_base * [1, Z_hs*i*omega]
            # At surface: s = P * s_base = u_base * [P11 + Z*iw*P12, P21 + Z*iw*P22]
            # tau_surface = 0 => always satisfied since single free param u_base
            # H = u_surface / u_outcrop
            # u_outcrop = 2 * A_incident; u_base = A_inc + A_ref
            # tau_base = Z_hs*iw*(A_inc - A_ref) = Z_hs*iw*u_base (if A_ref absorbed)
            # For within motion: H = (P11 + Z*iw*P12) / 1
            # For outcrop: divide by 2
            z_hs = z_arr[-1]
            ziw = z_hs * 1.0j * omega
            u_surf = p11 + ziw * p12
            # tau_surf_check = p21 + ziw * p22  # should be ~0 at free surface
            # Outcrop = 2 * incident => H = u_surf / 2
            transfer[fi] = u_surf / 2.0
        else:
            # Rigid base: u_base = u_input, tau_base = unknown reaction
            # s_base = [1, tau_r], s_surface = [P11 + tau_r*P12, P21 + tau_r*P22]
            # tau_surface = 0 => tau_r = -P21/P22
            # u_surface = P11 - P21*P12/P22
            if abs(p22) > 1.0e-30:
                transfer[fi] = p11 - p21 * p12 / p22
            else:
                transfer[fi] = p11

    # Apply transfer function
    fft_surface = fft_input * transfer
    surface_acc_full = np.fft.irfft(fft_surface, n=n_fft)
    surface_acc = surface_acc_full[:n_samples]
    time = np.arange(n_samples, dtype=np.float64) * dt

    return FrequencyDomainResult(
        freq_hz=freq,
        transfer_function=transfer,
        surface_acc=surface_acc,
        time=time,
    )
