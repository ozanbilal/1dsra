"""Implicit Newmark nonlinear solver for 1D SH site response.

This module provides two nonlinear solvers:

1. ``solve_nonlinear_implicit_newmark`` — **True implicit Newmark-beta** (β=0.25,
   γ=0.5, average acceleration) using tangent-stiffness linearisation at each
   time step.  This is the DEEPSOIL-equivalent integration approach: the
   equilibrium equation  M·a + C·v + F_int(u) = F_ext  is solved implicitly at
   each time step by linearising F_int around the current displacement.

2. ``solve_nonlinear_newmark`` — Symplectic velocity-Verlet (explicit).  Kept
   for regression comparison but produces severe under-amplification (~0.74×)
   on MKZ profiles because the explicit forward projection overshoots strain
   and causes excessive constitutive softening.

Root-cause analysis showed that the explicit integrators (both forward-Euler and
velocity-Verlet) produce identical 0.74× amplification on the same profile where
the linear implicit Newmark produces 6.77×.  The issue is NOT numerical
dissipation but rather uncontrolled strain overshoot in the explicit schemes:
large ground-acceleration impulses cause large displacement increments, which
drive MKZ into the softened regime, reducing internal resistance and allowing
even larger displacements in a positive-feedback loop.  The implicit scheme
naturally prevents this by solving a linearised equilibrium that accounts for
the tangent stiffness.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import numpy.typing as npt

from dsra1d.config import BoundaryCondition, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials.mrdf import mrdf_coefficients_from_params
from dsra1d.motion import effective_input_acceleration
from dsra1d.nonlinear import (
    _ElementConstitutiveState,
    _assemble_tridiagonal_from_element_values,
    _integrate_acc_to_velocity,
    _layer_damping,
    _modal_matched_damping_matrix,
    _rayleigh_coefficients,
)
from dsra1d.types import Motion

FloatArray = npt.NDArray[np.float64]


def _collect_element_branch_response(
    states: list[_ElementConstitutiveState],
    u_free: FloatArray,
    dz_elem: FloatArray,
    n_elem: int,
    n_nodes: int,
    n_free: int,
    *,
    step_index: int | None = None,
    substep_index: int | None = None,
    audit_layer_index: int | None = None,
    audit_rows: list[dict[str, float | int | None]] | None = None,
) -> list[dict[str, float | int | None]]:
    u_full = np.zeros(n_nodes, dtype=np.float64)
    u_full[:n_free] = u_free
    rows: list[dict[str, float | int | None]] = []
    for j in range(n_elem):
        dz = float(max(dz_elem[j], 1.0e-9))
        gamma_j = float((u_full[j] - u_full[j + 1]) / dz)
        tau, kt_exact, branch_id, reason_code, branch_state = states[j].peek_branch_response(gamma_j)
        row: dict[str, float | int | None] = {
            "layer_index": j,
            "gamma": gamma_j,
            "tau": float(tau),
            "kt_exact": float(kt_exact),
            "branch_id": branch_id,
            "reason_code": int(reason_code),
            "gamma_m_global": (
                float(branch_state.gamma_m_global) if branch_state is not None else None
            ),
            "f_mrdf": float(branch_state.f_mrdf) if branch_state is not None else None,
            "g_ref": float(branch_state.g_ref) if branch_state is not None else None,
            "g_t_ref": float(branch_state.g_t_ref) if branch_state is not None else None,
            "reload_factor": float(branch_state.reload_factor) if branch_state is not None else None,
            "branch_kind": branch_state.branch_kind if branch_state is not None else None,
        }
        rows.append(row)
        should_audit = audit_rows is not None and (
            audit_layer_index is None or j == audit_layer_index
        )
        if should_audit:
            audit_rows.append(
                {
                    "step": -1 if step_index is None else int(step_index),
                    "substep": -1 if substep_index is None else int(substep_index),
                    **row,
                }
            )
    return rows


def _write_tangent_audit_csv(
    path: Path,
    rows: list[dict[str, float | int | None]],
) -> None:
    def _fmt_optional(value: float | int | None) -> str:
        if value is None:
            return ""
        return f"{float(value):.10e}"

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            "step,substep,layer_index,gamma,tau,kt_exact,branch_id,reason_code,"
            "gamma_m_global,f_mrdf,g_ref,g_t_ref,reload_factor,branch_kind\n"
        )
        for row in rows:
            f.write(
                f"{int(row.get('step', -1))},"
                f"{int(row.get('substep', -1))},"
                f"{int(row.get('layer_index', -1))},"
                f"{float(row.get('gamma', float('nan'))):.10e},"
                f"{float(row.get('tau', float('nan'))):.10e},"
                f"{float(row.get('kt_exact', float('nan'))):.10e},"
                f"{'' if row.get('branch_id') is None else int(row['branch_id'])},"
                f"{int(row.get('reason_code', -1))},"
                f"{_fmt_optional(row.get('gamma_m_global'))},"
                f"{_fmt_optional(row.get('f_mrdf'))},"
                f"{_fmt_optional(row.get('g_ref'))},"
                f"{_fmt_optional(row.get('g_t_ref'))},"
                f"{_fmt_optional(row.get('reload_factor'))},"
                f"{'' if row.get('branch_kind') is None else str(row['branch_kind'])}\n"
            )


def _write_boundary_audit_csv(
    path: Path,
    rows: list[dict[str, float]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            "step,time_s,input_acc_m_s2,input_vel_m_s,incident_force,base_relative_velocity_m_s,"
            "dashpot_force,net_boundary_force,base_relative_displacement_m,"
            "base_relative_acceleration_m_s2,surface_acceleration_m_s2,impedance_c\n"
        )
        for row in rows:
            f.write(
                f"{int(row['step'])},"
                f"{float(row['time_s']):.10e},"
                f"{float(row['input_acc_m_s2']):.10e},"
                f"{float(row['input_vel_m_s']):.10e},"
                f"{float(row['incident_force']):.10e},"
                f"{float(row['base_relative_velocity_m_s']):.10e},"
                f"{float(row['dashpot_force']):.10e},"
                f"{float(row['net_boundary_force']):.10e},"
                f"{float(row['base_relative_displacement_m']):.10e},"
                f"{float(row['base_relative_acceleration_m_s2']):.10e},"
                f"{float(row['surface_acceleration_m_s2']):.10e},"
                f"{float(row['impedance_c']):.10e}\n"
            )


def _solver_column_area(config: ProjectConfig) -> float:
    legacy = getattr(config, "opensees", None)
    if legacy is not None:
        width = float(getattr(legacy, "column_width_m", 1.0))
        thickness = float(getattr(legacy, "thickness_m", 1.0))
        area = width * thickness
        if np.isfinite(area) and area > 0.0:
            return area
    return 1.0


# ---------------------------------------------------------------------------
# Helper: assemble tangent stiffness from constitutive states
# ---------------------------------------------------------------------------

def _assemble_tangent_stiffness(
    states: list[_ElementConstitutiveState],
    u_free: FloatArray,
    dz_elem: FloatArray,
    area: float,
    n_elem: int,
    n_nodes: int,
    n_free: int,
    *,
    step_index: int | None = None,
    substep_index: int | None = None,
    audit_layer_index: int | None = None,
    audit_rows: list[dict[str, float | int | None]] | None = None,
) -> FloatArray:
    """Build global tangent-stiffness matrix K_t from element tangent moduli.

    Each element's tangent modulus G_t is obtained from
    ``state.tangent_modulus(gamma)`` which does NOT mutate constitutive state.
    """
    k_t_elem = np.zeros(n_elem, dtype=np.float64)
    branch_rows = _collect_element_branch_response(
        states,
        u_free,
        dz_elem,
        n_elem,
        n_nodes,
        n_free,
        step_index=step_index,
        substep_index=substep_index,
        audit_layer_index=audit_layer_index,
        audit_rows=audit_rows,
    )
    for j, row in enumerate(branch_rows):
        dz = float(max(dz_elem[j], 1.0e-9))
        g_t = float(row["kt_exact"])
        k_t_elem[j] = max(g_t * area / dz, 1.0e-9)
    k_t_full = _assemble_tridiagonal_from_element_values(k_t_elem, n_nodes)
    return k_t_full[:n_free, :n_free]


# ---------------------------------------------------------------------------
# Helper: evaluate internal forces WITHOUT mutating constitutive state
# ---------------------------------------------------------------------------

def _evaluate_f_int_readonly(
    states: list[_ElementConstitutiveState],
    u_free: FloatArray,
    dz_elem: FloatArray,
    area: float,
    n_elem: int,
    n_nodes: int,
    n_free: int,
) -> FloatArray:
    """Compute internal force vector from CURRENT constitutive state.

    Uses ``state.tau_prev`` (the stress from the last ``update_stress`` call)
    rather than calling ``update_stress`` again, so the state is untouched.
    For the very first step (no previous update), falls back to backbone stress
    evaluated at current strain.
    """
    f_int = np.zeros(n_nodes, dtype=np.float64)
    u_full = np.zeros(n_nodes, dtype=np.float64)
    u_full[:n_free] = u_free
    for j in range(n_elem):
        dz = float(max(dz_elem[j], 1.0e-9))
        gamma_j = float((u_full[j] - u_full[j + 1]) / dz)
        if states[j].initialized:
            # Use stored stress from last update
            tau = states[j].tau_prev
        else:
            # First call: backbone stress at zero strain → 0
            tau = states[j]._backbone(gamma_j)
        force = tau * area
        f_int[j] += force
        f_int[j + 1] -= force
    return f_int[:n_free]


# ---------------------------------------------------------------------------
# Helper: evaluate internal forces AND update constitutive state
# ---------------------------------------------------------------------------

def _evaluate_internal_forces(
    states: list[_ElementConstitutiveState],
    u_full: FloatArray,
    dz_elem: FloatArray,
    area: float,
    n_elem: int,
    n_nodes: int,
) -> FloatArray:
    """Compute internal force vector AND update constitutive state."""
    f_int = np.zeros(n_nodes, dtype=np.float64)
    for j in range(n_elem):
        dz = float(max(dz_elem[j], 1.0e-9))
        gamma = float((u_full[j] - u_full[j + 1]) / dz)
        tau = states[j].update_stress(gamma)
        force = tau * area
        f_int[j] += force
        f_int[j + 1] -= force
    return f_int


# ---------------------------------------------------------------------------
# Helper: update damping from secant stiffness
# ---------------------------------------------------------------------------

def _update_viscous_damping(
    states: list[_ElementConstitutiveState],
    u_free: FloatArray,
    dz_elem: FloatArray,
    xi_elem: FloatArray,
    m_elem: FloatArray,
    area: float,
    n_elem: int,
    n_nodes: int,
    n_free: int,
    dashpot_c: float,
    use_elastic_halfspace: bool,
) -> FloatArray:
    """Recompute viscous damping matrix from current secant stiffness."""
    u_full = np.zeros(n_nodes, dtype=np.float64)
    u_full[:n_free] = u_free
    c_upd = np.zeros(n_elem, dtype=np.float64)
    for j in range(n_elem):
        dz = float(max(dz_elem[j], 1.0e-9))
        gamma_j = float((u_full[j] - u_full[j + 1]) / dz)
        tau_j = states[j].tau_prev
        if abs(gamma_j) > 1.0e-10:
            g_sec = abs(tau_j / gamma_j)
        else:
            g_sec = states[j].gmax_fallback
        k_sec_j = max(g_sec * area / dz, 1.0e-9)
        c_upd[j] = 2.0 * xi_elem[j] * np.sqrt(max(k_sec_j * m_elem[j], 1.0e-12))
    c_full = _assemble_tridiagonal_from_element_values(c_upd, n_nodes)
    if use_elastic_halfspace:
        c_full[-1, -1] += dashpot_c
    return c_full[:n_free, :n_free]


# ===================================================================
# PRIMARY SOLVER: True implicit Newmark-beta (DEEPSOIL-equivalent)
# ===================================================================

def solve_nonlinear_implicit_newmark(
    config: ProjectConfig,
    motion: Motion,
    *,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
    substeps: int | None = None,
    return_nodal_displacement: bool = False,
    _tangent_audit_layer: int | None = None,
    _tangent_audit_path: str | Path | None = None,
    _boundary_audit_path: str | Path | None = None,
) -> tuple[FloatArray, FloatArray] | tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Solve nonlinear 1-D SH response using implicit Newmark-beta integration.

    Uses the average-acceleration method (β=0.25, γ=0.5) which is
    unconditionally stable and second-order accurate.  At each time step the
    equation of motion is linearised using the tangent stiffness from the
    current constitutive state, matching the DEEPSOIL integration approach.

    Parameters
    ----------
    config : ProjectConfig
        Analysis configuration with soil profile and analysis control.
    motion : Motion
        Input acceleration time series (in SI units, m/s²).
    points_per_wavelength : float
        Mesh discretisation parameter.
    min_dz_m : float
        Minimum element thickness.
    substeps : int or None
        Number of substeps per time step.  If None, uses
        ``config.analysis.nonlinear_substeps``.

    Returns
    -------
    time, surface_acc : tuple of arrays
    """
    if motion.acc.size < 2:
        raise ValueError("Motion must contain at least 2 samples.")

    n_sub = substeps if substeps is not None else int(config.analysis.nonlinear_substeps)
    if n_sub < 1:
        n_sub = 1

    # ---- mesh ----
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
    use_elastic_halfspace = (
        config.boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE
    )
    n_free = n_nodes if use_elastic_halfspace else (n_nodes - 1)
    if n_free == 0:
        t = np.arange(motion.acc.size, dtype=np.float64) * float(motion.dt)
        if not return_nodal_displacement:
            return t, motion.acc.copy()
        node_depth_m = np.zeros(n_nodes, dtype=np.float64)
        nodal_displacement_m = np.zeros((n_nodes, motion.acc.size), dtype=np.float64)
        return t, motion.acc.copy(), node_depth_m, nodal_displacement_m

    # ---- element properties ----
    m_elem = np.zeros(n_elem, dtype=np.float64)
    k_elem = np.zeros(n_elem, dtype=np.float64)
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
        m_elem[j] = rho * area * dz
        k_elem[j] = g_mod * area / dz
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

    # ---- global mass (lumped diagonal) ----
    m_diag_full = np.zeros(n_nodes, dtype=np.float64)
    m_diag_full[0] += 0.5 * m_elem[0]
    m_diag_full[-1] += 0.5 * m_elem[-1]
    for j in range(n_elem - 1):
        m_diag_full[j + 1] += 0.5 * (m_elem[j] + m_elem[j + 1])
    m_diag = m_diag_full[:n_free]
    if np.any(m_diag <= 0.0):
        raise ValueError("Non-positive nodal mass encountered.")
    m_mat = np.diag(m_diag)

    # ---- initial damping matrix ----
    dashpot_c = 0.0
    base_rho = 0.0
    base_vs = 0.0
    if use_elastic_halfspace:
        bedrock = config.effective_bedrock()
        base_rho = float(max(bedrock.unit_weight_kn_m3 / 9.81, 1.0e-6))
        base_vs = float(max(bedrock.vs_m_s, 1.0e-6))
        dashpot_c = base_rho * base_vs * area

    # ---- damping mode ----
    use_rayleigh = config.analysis.damping_mode == "rayleigh"
    viscous_update = not use_rayleigh and bool(config.analysis.viscous_damping_update)
    if use_rayleigh:
        xi_target = float(
            np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12))
        )
        alpha_r, beta_r = _rayleigh_coefficients(
            xi_target,
            config.analysis.rayleigh_mode_1_hz,
            config.analysis.rayleigh_mode_2_hz,
        )
        k_init_full = _assemble_tridiagonal_from_element_values(k_elem, n_nodes)
        c_mat = (alpha_r * m_mat) + (beta_r * k_init_full[:n_free, :n_free])
    else:
        xi_target = float(
            np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12))
        )
        k_init_full = _assemble_tridiagonal_from_element_values(k_elem, n_nodes)
        c_mat = _modal_matched_damping_matrix(m_diag, k_init_full[:n_free, :n_free], xi_target)
        if use_elastic_halfspace:
            c_mat = c_mat.copy()
            c_mat[-1, -1] += dashpot_c

    # ---- Newmark constants (average acceleration: beta=0.25, gamma=0.5) ----
    dt = float(motion.dt)
    dt_sub = dt / float(n_sub)
    beta_nm = 0.25
    gamma_nm = 0.50
    a0 = 1.0 / (beta_nm * dt_sub * dt_sub)
    a1 = gamma_nm / (beta_nm * dt_sub)
    a2 = 1.0 / (beta_nm * dt_sub)
    a3 = (1.0 / (2.0 * beta_nm)) - 1.0
    a4 = (gamma_nm / beta_nm) - 1.0
    a5 = dt_sub * ((gamma_nm / (2.0 * beta_nm)) - 1.0)

    # ---- external force array ----
    acc_g = effective_input_acceleration(config, motion.acc)
    n_steps = acc_g.size
    time = np.arange(n_steps, dtype=np.float64) * dt
    input_vel = _integrate_acc_to_velocity(acc_g, dt) if use_elastic_halfspace else None

    # ---- state vectors ----
    u = np.zeros(n_free, dtype=np.float64)
    v = np.zeros(n_free, dtype=np.float64)
    a_rel = np.zeros(n_free, dtype=np.float64)
    a_rel_hist = np.zeros((n_free, n_steps), dtype=np.float64)
    u_hist_full = np.zeros((n_nodes, n_steps), dtype=np.float64)
    tangent_audit_rows: list[dict[str, float | int | None]] | None = (
        [] if _tangent_audit_path is not None else None
    )
    boundary_audit_rows: list[dict[str, float]] | None = (
        [] if (_boundary_audit_path is not None and use_elastic_halfspace) else None
    )

    # ---- initial internal force (zero displacement → zero) ----
    f_int_prev = np.zeros(n_free, dtype=np.float64)

    def _append_boundary_audit(step_index: int) -> None:
        if (
            boundary_audit_rows is None
            or input_vel is None
            or n_free <= 0
            or not use_elastic_halfspace
        ):
            return
        base_idx = n_free - 1
        incident_force = 2.0 * base_rho * base_vs * area * float(input_vel[step_index])
        base_relative_velocity = float(v[base_idx])
        dashpot_force = float(dashpot_c * base_relative_velocity)
        boundary_audit_rows.append(
            {
                "step": float(step_index),
                "time_s": float(time[step_index]),
                "input_acc_m_s2": float(acc_g[step_index]),
                "input_vel_m_s": float(input_vel[step_index]),
                "incident_force": float(incident_force),
                "base_relative_velocity_m_s": base_relative_velocity,
                "dashpot_force": dashpot_force,
                "net_boundary_force": float(incident_force - dashpot_force),
                "base_relative_displacement_m": float(u[base_idx]),
                "base_relative_acceleration_m_s2": float(a_rel[base_idx]),
                "surface_acceleration_m_s2": float(a_rel[0]),
                "impedance_c": float(dashpot_c),
            }
        )

    # ---- compute initial acceleration from initial conditions ----
    # At t=0: M*a0 + C*v0 + F_int(u0) = F_ext(0) → a0 = F_ext(0) / M
    if use_elastic_halfspace:
        assert input_vel is not None
        f_ext_0 = np.zeros(n_free, dtype=np.float64)
        f_ext_0[-1] = 2.0 * base_rho * base_vs * area * float(input_vel[0])
    else:
        f_ext_0 = -m_diag * float(acc_g[0])
    rhs0 = f_ext_0 - (c_mat @ v) - f_int_prev
    a_rel = rhs0 / m_diag
    a_rel_hist[:, 0] = a_rel
    u_hist_full[:n_free, 0] = u
    _append_boundary_audit(0)

    # ---- implicit Newmark time integration ----
    for i in range(1, n_steps):
        ag = float(acc_g[i])

        for substep_idx in range(n_sub):
            # 1) Assemble tangent stiffness from current constitutive state
            k_t = _assemble_tangent_stiffness(
                constitutive_states, u, dz_elem, area,
                n_elem, n_nodes, n_free,
                step_index=i,
                substep_index=substep_idx,
                audit_layer_index=_tangent_audit_layer,
                audit_rows=tangent_audit_rows,
            )

            # 2) Update damping if viscous update mode
            c_step = c_mat
            if viscous_update:
                k_sec = _assemble_tangent_stiffness(
                    constitutive_states, u, dz_elem, area,
                    n_elem, n_nodes, n_free,
                )
                xi_target = float(
                    np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12))
                )
                c_step = _modal_matched_damping_matrix(m_diag, k_sec, xi_target)
                if use_elastic_halfspace:
                    c_step = c_step.copy()
                    c_step[-1, -1] += dashpot_c

            # 3) Effective stiffness: K_eff = K_t + a0*M + a1*C
            k_eff = k_t + (a0 * m_mat) + (a1 * c_step)

            # 4) External force at current step
            if use_elastic_halfspace:
                assert input_vel is not None
                f_ext = np.zeros(n_free, dtype=np.float64)
                f_ext[-1] = 2.0 * base_rho * base_vs * area * float(input_vel[i])
            else:
                f_ext = -m_diag * ag

            # 5) RHS: F_ext + M_terms + C_terms + K_t*u_n - F_int(u_n)
            #    The (K_t*u_n - F_int) term corrects for linearisation error
            rhs = (
                f_ext
                + (m_mat @ ((a0 * u) + (a2 * v) + (a3 * a_rel)))
                + (c_step @ ((a1 * u) + (a4 * v) + (a5 * a_rel)))
                + (k_t @ u)
                - f_int_prev
            )

            # 6) Solve for new displacement
            u_new = np.linalg.solve(k_eff, rhs)

            # 7) Newmark update for acceleration and velocity
            a_new = (a0 * (u_new - u)) - (a2 * v) - (a3 * a_rel)
            v_new = v + dt_sub * ((1.0 - gamma_nm) * a_rel + gamma_nm * a_new)

            # 8) Update constitutive states from new displacement
            u_full = np.zeros(n_nodes, dtype=np.float64)
            u_full[:n_free] = u_new
            f_int_full = _evaluate_internal_forces(
                constitutive_states, u_full, dz_elem, area, n_elem, n_nodes,
            )
            f_int_prev = f_int_full[:n_free]

            # 9) Advance state
            u = u_new
            v = v_new
            a_rel = a_new

        a_rel_hist[:, i] = a_rel
        u_hist_full[:n_free, i] = u
        _append_boundary_audit(i)

    # ---- check for non-finite response ----
    if not np.all(np.isfinite(a_rel_hist)):
        raise ValueError(
            "Non-finite surface response detected in implicit Newmark nonlinear solver."
        )
    if tangent_audit_rows is not None and _tangent_audit_path is not None:
        _write_tangent_audit_csv(Path(_tangent_audit_path), tangent_audit_rows)
    if boundary_audit_rows is not None and _boundary_audit_path is not None:
        _write_boundary_audit_csv(Path(_boundary_audit_path), boundary_audit_rows)

    # ---- surface acceleration ----
    if use_elastic_halfspace:
        surface_acc = a_rel_hist[0, :]
    else:
        surface_acc = a_rel_hist[0, :] + acc_g

    if not return_nodal_displacement:
        return time, surface_acc

    node_depth_m = np.zeros(n_nodes, dtype=np.float64)
    for j, elem in enumerate(element_slices):
        node_depth_m[j + 1] = node_depth_m[j] + float(max(elem.dz_m, 0.0))
    return time, surface_acc, node_depth_m, u_hist_full


# ===================================================================
# LEGACY: Velocity-Verlet explicit solver (kept for regression)
# ===================================================================

def solve_nonlinear_newmark(
    config: ProjectConfig,
    motion: Motion,
    *,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
    substeps: int | None = None,
    return_nodal_displacement: bool = False,
) -> tuple[FloatArray, FloatArray] | tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Solve nonlinear 1-D SH response using velocity-Verlet integration.

    .. deprecated::
        This solver produces ~0.74× amplification on MKZ profiles due to
        explicit strain overshoot.  Use ``solve_nonlinear_implicit_newmark``
        instead.
    """
    if motion.acc.size < 2:
        raise ValueError("Motion must contain at least 2 samples.")

    n_sub = substeps if substeps is not None else int(config.analysis.nonlinear_substeps)
    if n_sub < 1:
        n_sub = 1

    # ---- mesh ----
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
    use_elastic_halfspace = (
        config.boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE
    )
    n_free = n_nodes if use_elastic_halfspace else (n_nodes - 1)

    # ---- element properties ----
    m_elem = np.zeros(n_elem, dtype=np.float64)
    k_elem = np.zeros(n_elem, dtype=np.float64)
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
        m_elem[j] = rho * area * dz
        k_elem[j] = g_mod * area / dz
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

    # ---- global mass (lumped diagonal) ----
    m_diag_full = np.zeros(n_nodes, dtype=np.float64)
    m_diag_full[0] += 0.5 * m_elem[0]
    m_diag_full[-1] += 0.5 * m_elem[-1]
    for j in range(n_elem - 1):
        m_diag_full[j + 1] += 0.5 * (m_elem[j] + m_elem[j + 1])
    m_diag = m_diag_full[:n_free]
    if np.any(m_diag <= 0.0):
        raise ValueError("Non-positive nodal mass encountered.")

    # ---- initial damping matrix ----
    dashpot_c = 0.0
    base_rho = 0.0
    base_vs = 0.0
    if use_elastic_halfspace:
        bedrock = config.effective_bedrock()
        base_rho = float(max(bedrock.unit_weight_kn_m3 / 9.81, 1.0e-6))
        base_vs = float(max(bedrock.vs_m_s, 1.0e-6))
        dashpot_c = base_rho * base_vs * area

    # ---- damping mode ----
    use_rayleigh = config.analysis.damping_mode == "rayleigh"
    viscous_update = (
        not use_rayleigh and bool(config.analysis.viscous_damping_update)
    )
    m_mat = np.diag(m_diag)
    if use_rayleigh:
        xi_target = float(
            np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12))
        )
        alpha_r, beta_r = _rayleigh_coefficients(
            xi_target,
            config.analysis.rayleigh_mode_1_hz,
            config.analysis.rayleigh_mode_2_hz,
        )
        k_init_full = _assemble_tridiagonal_from_element_values(k_elem, n_nodes)
        c_mat = (alpha_r * m_mat) + (beta_r * k_init_full[:n_free, :n_free])
    else:
        xi_target = float(
            np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12))
        )
        k_init_full = _assemble_tridiagonal_from_element_values(k_elem, n_nodes)
        c_mat = _modal_matched_damping_matrix(m_diag, k_init_full[:n_free, :n_free], xi_target)
        if use_elastic_halfspace:
            c_mat = c_mat.copy()
            c_mat[-1, -1] += dashpot_c

    # ---- time stepping setup ----
    dt = float(motion.dt)
    dt_sub = dt / float(n_sub)
    acc_g = effective_input_acceleration(config, motion.acc)
    n_steps = acc_g.size
    time = np.arange(n_steps, dtype=np.float64) * dt
    input_vel = _integrate_acc_to_velocity(acc_g, dt) if use_elastic_halfspace else None

    # ---- state vectors ----
    u = np.zeros(n_free, dtype=np.float64)
    vel = np.zeros(n_free, dtype=np.float64)
    a_prev = np.zeros(n_free, dtype=np.float64)
    a_rel_hist = np.zeros((n_free, n_steps), dtype=np.float64)
    u_hist_full = np.zeros((n_nodes, n_steps), dtype=np.float64)

    # ---- velocity-Verlet time integration ----
    for i in range(n_steps):
        ag = float(acc_g[i])
        for _ in range(n_sub):
            v_half = vel + 0.5 * dt_sub * a_prev
            u = u + dt_sub * v_half

            u_full = np.zeros(n_nodes, dtype=np.float64)
            u_full[:n_free] = u
            f_int_full = _evaluate_internal_forces(
                constitutive_states, u_full, dz_elem, area, n_elem, n_nodes
            )
            f_int = f_int_full[:n_free]

            if use_elastic_halfspace:
                assert input_vel is not None
                f_ext = np.zeros_like(m_diag)
                f_ext[-1] = 2.0 * base_rho * base_vs * area * float(input_vel[i])
            else:
                f_ext = -m_diag * ag

            c_step = c_mat
            if viscous_update:
                k_sec = _assemble_tangent_stiffness(
                    constitutive_states, u, dz_elem, area,
                    n_elem, n_nodes, n_free,
                )
                xi_target = float(
                    np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12))
                )
                c_step = _modal_matched_damping_matrix(m_diag, k_sec, xi_target)
                if use_elastic_halfspace:
                    c_step = c_step.copy()
                    c_step[-1, -1] += dashpot_c

            a_new = (f_ext - (c_step @ v_half) - f_int) / m_diag
            vel = v_half + 0.5 * dt_sub * a_new
            a_prev = a_new

        a_rel_hist[:, i] = a_prev
        u_hist_full[:n_free, i] = u

    # ---- surface acceleration ----
    if n_free == 0:
        surface_acc = acc_g.copy()
    elif use_elastic_halfspace:
        surface_acc = a_rel_hist[0, :]
    else:
        surface_acc = a_rel_hist[0, :] + acc_g

    if not return_nodal_displacement:
        return time, surface_acc

    node_depth_m = np.zeros(n_nodes, dtype=np.float64)
    for j, elem in enumerate(element_slices):
        node_depth_m[j + 1] = node_depth_m[j] + float(max(elem.dz_m, 0.0))
    return time, surface_acc, node_depth_m, u_hist_full
