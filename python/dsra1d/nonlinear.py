from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from dsra1d.config import BoundaryCondition, MaterialType, ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials import (
    gqh_backbone_stress_from_params,
    gqh_modulus_reduction_from_params,
    mkz_backbone_stress,
    mkz_modulus_reduction,
)
from dsra1d.materials.damping import (
    layer_damping as _layer_damping,
    modal_matched_damping_matrix as _modal_matched_damping_matrix,
    rayleigh_coefficients as _rayleigh_coefficients,
)
from dsra1d.materials.mrdf import (
    MRDFCoefficients,
    evaluate_mrdf_factor,
    evolve_mrdf_factor_with_branch_progress,
    mrdf_coefficients_from_params,
)
from dsra1d.motion import effective_input_acceleration
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
        tau = gqh_backbone_stress_from_params(
            np.array([gamma], dtype=np.float64),
            params,
            gmax_fallback=gmax_fallback,
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
class _ReplayBranch:
    branch_id: int
    parent_branch_id: int | None
    gamma_rev: float
    tau_rev: float
    gamma_m_global: float
    reload_factor: float
    f_mrdf: float
    direction: int
    branch_kind: str
    g_over_gmax: float
    g_ref: float
    g_t_ref: float
    mode: str
    keeps_reversal_tangent: bool


@dataclass(slots=True)
class _MrdfBridgeState:
    gamma_hist: float
    g_over_gmax: float
    f_mrdf: float
    g_ref: float
    tau_ref: float
    g_t_ref: float
    mode: str
    keeps_reversal_tangent: bool = False


@dataclass(slots=True)
class _DirectBranchState:
    branch_id: int | None
    parent_branch_id: int | None
    gamma_rev: float
    tau_rev: float
    gamma_m_global: float
    reload_factor: float
    f_mrdf: float
    direction: int
    branch_kind: str
    g_over_gmax: float
    g_ref: float
    g_t_ref: float
    mode: str
    keeps_reversal_tangent: bool


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
    gamma_max_seen: float = 0.0
    follow_backbone_until_reversal: bool = False
    mrdf_bridge_gamma_hist: float = 0.0
    mrdf_bridge_g_over_gmax: float = 1.0
    mrdf_bridge_factor: float = 1.0
    mrdf_bridge_g_ref: float = 0.0
    branch_stack: list[_ReplayBranch] = field(default_factory=list)
    branch_lookup: dict[int, _ReplayBranch] = field(default_factory=dict)
    branch_counter: int = 0
    active_branch_id: int | None = None
    last_selected_branch_id: int | None = None

    def _backbone(self, gamma: float) -> float:
        return _element_backbone_stress(
            self.material,
            self.params,
            gamma,
            gmax_fallback=self.gmax_fallback,
        )

    def _reduction(self, gamma: float) -> float:
        gamma_arr = np.array([gamma], dtype=np.float64)
        if self.material == MaterialType.MKZ:
            return float(
                mkz_modulus_reduction(
                    gamma_arr,
                    gamma_ref=float(self.params.get("gamma_ref", 1.0e-3)),
                    g_reduction_min=float(self.params.get("g_reduction_min", 0.0)),
                )[0]
            )
        if self.material == MaterialType.GQH:
            return float(
                gqh_modulus_reduction_from_params(
                    gamma_arr,
                    self.params,
                    gmax_fallback=self.gmax_fallback,
                )[0]
            )
        return 1.0

    def _reload_reference_blend(self) -> float:
        raw = self.params.get("reload_reference_blend", 0.0)
        try:
            blend = float(raw)
        except (TypeError, ValueError):
            blend = 0.0
        return float(np.clip(blend, 0.0, 1.0))

    def _mrdf_reference_mode_code(self) -> float:
        raw = self.params.get("mrdf_reference_mode_code", 0.0)
        try:
            mode = float(raw)
        except (TypeError, ValueError):
            mode = 0.0
        return mode

    def _tangent_floor(self) -> float:
        gmax = float(self.params.get("gmax", self.gmax_fallback))
        g_red_min = float(self.params.get("g_reduction_min", 0.0))
        return max(gmax * g_red_min, gmax * 1.0e-4)

    def _current_g0(self) -> float:
        return max(float(self.params.get("gmax", self.gmax_fallback)), 1.0e-12)

    def _mrdf_reference_preserves_tangent(self) -> bool:
        """Enable experimental mode where MRDF scaling is applied around a Gmax tangent anchor."""
        mode_code = self._mrdf_reference_mode_code()
        return 1.5 <= mode_code < 3.0

    def _nested_mrdf_memory_enabled(self) -> bool:
        """Enable branch replay experiments (mode>=2) without changing default behavior."""
        mode_code = self._mrdf_reference_mode_code()
        return 2.0 <= mode_code < 4.0

    def _reversal_tangent_preserving_mrdf_enabled(self) -> bool:
        mode_code = self._mrdf_reference_mode_code()
        return 3.0 <= mode_code < 4.0

    def _translated_local_tangent_restore_mrdf_enabled(self) -> bool:
        mode_code = self._mrdf_reference_mode_code()
        return 4.0 <= mode_code < 5.0

    def _progressive_f_mrdf_enabled(self) -> bool:
        mode_code = self._mrdf_reference_mode_code()
        return 5.0 <= mode_code < 6.0

    def _translated_branch_curvature_enabled(self) -> bool:
        mode_code = self._mrdf_reference_mode_code()
        return 6.0 <= mode_code < 7.0

    def _translated_branch_curvature_tangent_restore_enabled(self) -> bool:
        mode_code = self._mrdf_reference_mode_code()
        return 7.0 <= mode_code < 8.0

    def _translated_local_tangent_restore_weight(
        self,
        *,
        f_mrdf: float,
    ) -> float:
        return float(np.clip(1.0 - f_mrdf, 0.0, 1.0))

    def _mrdf_branch_progress(
        self,
        gamma: float,
        *,
        gamma_hist: float,
    ) -> float:
        if gamma_hist <= self.eps_gamma:
            return 0.0
        return float(
            np.clip(
                abs(gamma - self.gamma_rev) / max(gamma_hist, self.eps_gamma),
                0.0,
                1.0,
            )
        )

    def _translated_branch_curvature_weight(
        self,
        *,
        branch_progress: float,
    ) -> float:
        raw = self.params.get("translated_curvature_exponent", 2.0)
        try:
            exponent = float(raw)
        except (TypeError, ValueError):
            exponent = 2.0
        exponent = max(exponent, 1.0e-6)
        progress = float(np.clip(branch_progress, 0.0, 1.0))
        return float(progress**exponent)

    def _build_branch(self, bridge: _MrdfBridgeState, *, parent_branch_id: int | None) -> _ReplayBranch:
        return _ReplayBranch(
            branch_id=self.branch_counter + 1,
            parent_branch_id=parent_branch_id,
            gamma_rev=self.gamma_rev,
            tau_rev=self.tau_rev,
            gamma_m_global=max(bridge.gamma_hist, self.eps_gamma),
            reload_factor=self._effective_reload_factor(),
            f_mrdf=bridge.f_mrdf,
            direction=self.direction if self.direction != 0 else 1,
            branch_kind=bridge.mode,
            g_over_gmax=bridge.g_over_gmax,
            g_ref=bridge.g_ref,
            g_t_ref=bridge.g_t_ref,
            mode=bridge.mode,
            keeps_reversal_tangent=bridge.keeps_reversal_tangent,
        )

    def _build_direct_branch_state(
        self,
        *,
        bridge: _MrdfBridgeState | None,
        reload_factor: float,
        g_t_2x: float,
    ) -> _DirectBranchState:
        gamma_hist = max(
            self.gamma_max_seen,
            abs(self.gamma_prev),
            abs(self.gamma_rev),
            self.eps_gamma,
        )
        if bridge is None:
            g_over_gmax = self._reduction(gamma_hist)
            f_mrdf = 1.0
            g_ref = max(g_t_2x, self._tangent_floor())
            g_t_ref = g_ref
            mode = "translated_masing"
            keeps_tangent = False
        else:
            g_over_gmax = bridge.g_over_gmax
            f_mrdf = bridge.f_mrdf
            g_ref = bridge.g_ref
            g_t_ref = bridge.g_t_ref
            mode = bridge.mode
            keeps_tangent = bridge.keeps_reversal_tangent
            gamma_hist = max(bridge.gamma_hist, self.eps_gamma)
        return _DirectBranchState(
            branch_id=None,
            parent_branch_id=self.active_branch_id,
            gamma_rev=self.gamma_rev,
            tau_rev=self.tau_rev,
            gamma_m_global=gamma_hist,
            reload_factor=reload_factor,
            f_mrdf=f_mrdf,
            direction=self.direction if self.direction != 0 else 1,
            branch_kind=mode,
            g_over_gmax=g_over_gmax,
            g_ref=g_ref,
            g_t_ref=g_t_ref,
            mode=mode,
            keeps_reversal_tangent=keeps_tangent,
        )

    def _translated_branch_terms(
        self,
        branch: _ReplayBranch,
        gamma: float,
    ) -> tuple[float, float, float]:
        delta_gamma = gamma - branch.gamma_rev
        abs_delta_gamma = abs(delta_gamma)
        branch_sign = 1.0 if delta_gamma >= 0.0 else -1.0
        reload_factor = max(branch.reload_factor, 1.0e-12)
        shifted_gamma = abs_delta_gamma / reload_factor
        delta_tau_2x = branch_sign * reload_factor * self._backbone(shifted_gamma)
        g_t_2x = self._backbone_tangent(shifted_gamma)
        return delta_gamma, delta_tau_2x, g_t_2x

    def _eval_branch_response(
        self,
        branch: _ReplayBranch,
        gamma: float,
    ) -> tuple[float, float]:
        delta_gamma, delta_tau_2x, g_t_2x = self._translated_branch_terms(branch, gamma)
        tangent_floor = self._tangent_floor()
        if branch.branch_kind == "reversal_tangent_preserving":
            g0 = self._current_g0()
            tau = branch.tau_rev + (g0 * delta_gamma) + (
                branch.f_mrdf * (delta_tau_2x - (g0 * delta_gamma))
            )
            kt = g0 + (branch.f_mrdf * (g_t_2x - g0))
            return tau, max(kt, tangent_floor)

        tau_2x = branch.tau_rev + delta_tau_2x
        tau_ref = branch.tau_rev + (branch.g_ref * delta_gamma)
        tau = tau_ref + (branch.f_mrdf * (tau_2x - tau_ref))
        g_t_branch = max(branch.g_t_ref + branch.f_mrdf * (g_t_2x - branch.g_t_ref), tangent_floor)
        if branch.keeps_reversal_tangent:
            return tau, g_t_branch
        g_t_floor_adaptive = self._adaptive_tangent_floor(
            gamma,
            g_t_ref=branch.g_t_ref,
            f_mrdf=branch.f_mrdf,
            tangent_floor=tangent_floor,
        )
        return tau, max(g_t_branch, g_t_floor_adaptive)

    def _eval_branch_stress(
        self,
        branch: _ReplayBranch,
        gamma: float,
    ) -> float:
        return self._eval_branch_response(branch, gamma)[0]

    def _eval_branch_tangent(
        self,
        branch: _ReplayBranch,
        gamma: float,
    ) -> float:
        return self._eval_branch_response(branch, gamma)[1]

    def _active_replay_branch(self, *, mutate: bool = False) -> _ReplayBranch | None:
        if not self.branch_stack:
            return None
        if self.active_branch_id is None:
            if mutate:
                self.active_branch_id = self.branch_stack[-1].branch_id
            return self.branch_stack[-1]
        branch = self.branch_lookup.get(self.active_branch_id)
        if branch is not None:
            return branch
        # Fallback for stale ids; keep behavior deterministic.
        if mutate:
            self.active_branch_id = self.branch_stack[-1].branch_id
        return self.branch_stack[-1]

    def _capture_mrdf_bridge_state(self) -> None:
        if self.mrdf_coeffs is None:
            return
        if abs(self._mrdf_reference_mode_code()) < 0.5:
            return
        gamma_hist = max(
            self.gamma_max_seen,
            abs(self.gamma_prev),
            abs(self.gamma_rev),
            self.eps_gamma,
        )
        g_over_gmax = self._reduction(gamma_hist)
        f_mrdf = evaluate_mrdf_factor(
            self.mrdf_coeffs,
            gamma_hist,
            g_over_gmax=g_over_gmax,
        )
        gmax = float(self.params.get("gmax", self.gmax_fallback))
        self.mrdf_bridge_gamma_hist = gamma_hist
        self.mrdf_bridge_g_over_gmax = g_over_gmax
        self.mrdf_bridge_factor = f_mrdf
        self.mrdf_bridge_g_ref = max(gmax * g_over_gmax, self._tangent_floor())

    def _record_reversal_branch(self, gamma: float) -> None:
        if self.mrdf_coeffs is None:
            return
        if not self._nested_mrdf_memory_enabled():
            return
        bridge = self._mrdf_bridge_state(gamma)
        if bridge is None:
            return
        parent = self.active_branch_id
        branch = self._build_branch(bridge, parent_branch_id=parent)
        self.branch_counter = branch.branch_id
        self.branch_stack.append(branch)
        self.branch_lookup[branch.branch_id] = branch
        self.active_branch_id = branch.branch_id

    def _replay_candidate_chain(self, active: _ReplayBranch) -> list[_ReplayBranch]:
        candidates: list[_ReplayBranch] = []
        parent_id = active.parent_branch_id
        while parent_id is not None:
            parent = self.branch_lookup.get(parent_id)
            if parent is None:
                break
            if parent.direction == active.direction:
                candidates.append(parent)
            parent_id = parent.parent_branch_id
        return candidates

    def _find_replay_branch(self, gamma: float) -> _ReplayBranch | None:
        if not self._nested_mrdf_memory_enabled():
            return None
        if len(self.branch_stack) < 2:
            return None
        active = self._active_replay_branch(mutate=False)
        if active is None:
            return None

        tau_prev_active = self._eval_branch_stress(active, self.gamma_prev)
        tau_curr_active = self._eval_branch_stress(active, gamma)
        for branch in self._replay_candidate_chain(active):
            tau_prev_prior = self._eval_branch_stress(branch, self.gamma_prev)
            tau_curr_prior = self._eval_branch_stress(branch, gamma)
            if not (np.isfinite(tau_prev_active) and np.isfinite(tau_curr_active) and np.isfinite(tau_prev_prior) and np.isfinite(tau_curr_prior)):
                continue
            diff_prev = tau_prev_active - tau_prev_prior
            diff_curr = tau_curr_active - tau_curr_prior
            if diff_prev == 0.0 or diff_curr == 0.0 or diff_prev * diff_curr < 0.0:
                return branch
        return None

    def _resolve_replay_branch(self, gamma: float) -> tuple[_ReplayBranch | None, int]:
        """
        Resolve the branch that should be used at the given strain.

        Returns tuple of (branch, reason), where reason code is used for debugging:
        0=new-backbone/monotonic, 1=active branch, 2=replayed branch.
        """
        candidate = self._active_replay_branch(mutate=False)
        if candidate is None:
            return None, 1

        if self._nested_mrdf_memory_enabled():
            replay = self._find_replay_branch(gamma)
            if replay is not None:
                return replay, 2
        return candidate, 1

    def _mrdf_bridge_state(self, gamma: float) -> _MrdfBridgeState | None:
        if self.mrdf_coeffs is None:
            return None

        delta_gamma = gamma - self.gamma_rev
        abs_delta_gamma = abs(delta_gamma)
        branch_sign = 1.0 if delta_gamma >= 0.0 else -1.0
        mode_code = self._mrdf_reference_mode_code()
        keeps_tangent = self._mrdf_reference_preserves_tangent()

        if abs(mode_code) >= 0.5 and self.has_reversal and not (
            self._translated_local_tangent_restore_mrdf_enabled()
            or self._progressive_f_mrdf_enabled()
            or self._translated_branch_curvature_enabled()
            or self._translated_branch_curvature_tangent_restore_enabled()
        ):
            gamma_hist = max(self.mrdf_bridge_gamma_hist, self.eps_gamma)
            g_over_gmax = float(np.clip(self.mrdf_bridge_g_over_gmax, 0.0, 1.0))
            f_mrdf = float(np.clip(self.mrdf_bridge_factor, 0.0, 1.5))
            if self._reversal_tangent_preserving_mrdf_enabled():
                g0 = self._current_g0()
                tau_ref = self.tau_rev + (g0 * delta_gamma)
                return _MrdfBridgeState(
                    gamma_hist=gamma_hist,
                    g_over_gmax=g_over_gmax,
                    f_mrdf=f_mrdf,
                    g_ref=g0,
                    tau_ref=tau_ref,
                    g_t_ref=g0,
                    mode="reversal_tangent_preserving",
                    keeps_reversal_tangent=True,
                )
            if keeps_tangent:
                g_ref = max(
                    self._current_g0(),
                    self._tangent_floor(),
                )
                tau_ref = self.tau_rev + (g_ref * delta_gamma)
                mode = "latched_exact_tangent_bridge"
            else:
                g_ref = max(self.mrdf_bridge_g_ref, self._tangent_floor())
                tau_ref = self.tau_rev + (g_ref * delta_gamma)
                mode = "latched_secant_bridge"
            return _MrdfBridgeState(
                gamma_hist=gamma_hist,
                g_over_gmax=g_over_gmax,
                f_mrdf=f_mrdf,
                g_ref=g_ref,
                tau_ref=tau_ref,
                g_t_ref=g_ref,
                mode=mode,
                keeps_reversal_tangent=keeps_tangent,
            )

        gamma_hist = max(
            self.gamma_max_seen,
            abs(self.gamma_prev),
            abs(gamma),
            abs(self.gamma_rev),
        )
        g_over_gmax = self._reduction(gamma_hist)
        f_mrdf = evaluate_mrdf_factor(
            self.mrdf_coeffs,
            gamma_hist,
            g_over_gmax=g_over_gmax,
        )
        if self._progressive_f_mrdf_enabled():
            branch_progress = self._mrdf_branch_progress(gamma, gamma_hist=gamma_hist)
            f_mrdf = evolve_mrdf_factor_with_branch_progress(
                f_mrdf,
                branch_progress,
                exponent=2.0,
            )
        if keeps_tangent:
            g_ref = max(
                float(self.params.get("gmax", self.gmax_fallback)),
                self._tangent_floor(),
            )
            tau_ref = self.tau_rev + (g_ref * delta_gamma)
            mode = "exact_tangent_bridge"
            g_t_ref = g_ref
            g_t_ref_secant = g_ref
        else:
            blend = self._reload_reference_blend()
            tau_ref_local = self.tau_rev + (
                branch_sign * self._backbone(abs_delta_gamma)
            )
            tau_ref_secant = self._secant_reference_stress(delta_gamma, g_over_gmax)
            tau_ref = ((1.0 - blend) * tau_ref_local) + (blend * tau_ref_secant)
            g_t_ref_local = self._backbone_tangent(abs_delta_gamma)
            g_t_ref_secant = max(float(self.params.get("gmax", self.gmax_fallback)) * g_over_gmax, self._tangent_floor())
            g_t_ref = ((1.0 - blend) * g_t_ref_local) + (blend * g_t_ref_secant)
            if self._translated_local_tangent_restore_mrdf_enabled():
                restore_weight = self._translated_local_tangent_restore_weight(f_mrdf=f_mrdf)
                g_t_ref = ((1.0 - restore_weight) * g_t_ref) + (restore_weight * self._current_g0())
                mode = "translated_local_tangent_restore_bridge"
            elif self._progressive_f_mrdf_enabled():
                mode = "translated_local_progressive_f_bridge"
            elif self._translated_branch_curvature_enabled() or self._translated_branch_curvature_tangent_restore_enabled():
                branch_progress = self._mrdf_branch_progress(gamma, gamma_hist=gamma_hist)
                curvature_weight = self._translated_branch_curvature_weight(
                    branch_progress=branch_progress,
                )
                g0 = self._current_g0()
                tau_ref_g0 = self.tau_rev + (g0 * delta_gamma)
                tau_ref = ((1.0 - curvature_weight) * tau_ref_g0) + (
                    curvature_weight * tau_ref
                )
                g_t_ref = ((1.0 - curvature_weight) * g0) + (
                    curvature_weight * g_t_ref
                )
                if self._translated_branch_curvature_tangent_restore_enabled():
                    restore_weight = self._translated_local_tangent_restore_weight(
                        f_mrdf=f_mrdf,
                    )
                    g_t_ref = ((1.0 - restore_weight) * g_t_ref) + (
                        restore_weight * g0
                    )
                    mode = "translated_curvature_tangent_restore_bridge"
                else:
                    mode = "translated_curvature_progressive_bridge"
            else:
                mode = "translated_local_bridge"
        if keeps_tangent:
            g_ref = max(g_t_ref, self._tangent_floor())
        else:
            g_ref = max(g_t_ref_secant, self._tangent_floor())
        return _MrdfBridgeState(
            gamma_hist=gamma_hist,
            g_over_gmax=g_over_gmax,
            f_mrdf=f_mrdf,
            g_ref=g_ref,
            tau_ref=tau_ref,
            g_t_ref=g_t_ref,
            mode=mode,
            keeps_reversal_tangent=keeps_tangent,
        )

    def _eval_direct_branch_response(
        self,
        gamma: float,
    ) -> tuple[float, float, _DirectBranchState]:
        delta_gamma = gamma - self.gamma_rev
        abs_delta_gamma = abs(delta_gamma)
        branch_sign = 1.0 if delta_gamma >= 0.0 else -1.0
        reload_factor = self._effective_reload_factor()
        shifted_gamma = abs_delta_gamma / max(reload_factor, 1.0e-12)
        tau_2x = self.tau_rev + (branch_sign * reload_factor * self._backbone(shifted_gamma))
        g_t_2x = self._backbone_tangent(shifted_gamma)
        bridge = self._mrdf_bridge_state(gamma)
        branch_state = self._build_direct_branch_state(
            bridge=bridge,
            reload_factor=reload_factor,
            g_t_2x=g_t_2x,
        )
        if bridge is None:
            return tau_2x, g_t_2x, branch_state

        tangent_floor = self._tangent_floor()
        if bridge.mode in {"translated_local_bridge", "translated_local_tangent_restore_bridge"}:
            tau = bridge.tau_ref + (bridge.f_mrdf * (tau_2x - bridge.tau_ref))
            kt = max(bridge.g_t_ref + bridge.f_mrdf * (g_t_2x - bridge.g_t_ref), tangent_floor)
            if bridge.keeps_reversal_tangent:
                return tau, kt, branch_state
            g_t_floor_adaptive = self._adaptive_tangent_floor(
                gamma,
                g_t_ref=bridge.g_t_ref,
                f_mrdf=bridge.f_mrdf,
                tangent_floor=tangent_floor,
            )
            return tau, max(kt, g_t_floor_adaptive), branch_state

        tau_ref = self.tau_rev + (bridge.g_ref * delta_gamma)
        tau = tau_ref + (bridge.f_mrdf * (tau_2x - tau_ref))
        kt = max(bridge.g_t_ref + bridge.f_mrdf * (g_t_2x - bridge.g_t_ref), tangent_floor)
        if bridge.keeps_reversal_tangent:
            return tau, kt, branch_state
        g_t_floor_adaptive = self._adaptive_tangent_floor(
            gamma,
            g_t_ref=bridge.g_t_ref,
            f_mrdf=bridge.f_mrdf,
            tangent_floor=tangent_floor,
        )
        return tau, max(kt, g_t_floor_adaptive), branch_state

    def peek_branch_response(
        self,
        gamma: float,
    ) -> tuple[float, float, int | None, int, _ReplayBranch | _DirectBranchState | None]:
        if self.material not in {MaterialType.MKZ, MaterialType.GQH}:
            tau = self._backbone(gamma)
            return tau, self.gmax_fallback, None, 0, None

        if not self.initialized:
            tau = self._backbone(gamma)
            return tau, self._backbone_tangent(gamma), None, 0, None

        if not self.has_reversal:
            tau = self._backbone(gamma)
            return tau, self._backbone_tangent(gamma), None, 0, None

        if self.follow_backbone_until_reversal:
            tau = self._signed_backbone(gamma)
            return tau, self._backbone_tangent(gamma), None, 0, None

        branch_state: _ReplayBranch | None = None
        branch_id: int | None = None
        reason_code = 1
        if self._nested_mrdf_memory_enabled():
            branch_state, reason_code = self._resolve_replay_branch(gamma)
            if branch_state is not None:
                tau, kt = self._eval_branch_response(branch_state, gamma)
                branch_id = branch_state.branch_id
            else:
                tau, kt, branch_state = self._eval_direct_branch_response(gamma)
        else:
            tau, kt, branch_state = self._eval_direct_branch_response(gamma)

        if self._should_follow_backbone(gamma, tau):
            tau = self._signed_backbone(gamma)
            return tau, self._backbone_tangent(gamma), None, 0, None

        return tau, kt, branch_id, reason_code, branch_state

    def _secant_reference_stress(self, delta_gamma: float, g_over_gmax: float) -> float:
        """DEEPSOIL-style MRDF reference branch based on secant modulus at γ_k."""
        gmax = float(self.params.get("gmax", self.gmax_fallback))
        g_sec = max(gmax * float(np.clip(g_over_gmax, 0.0, 1.0)), 0.0)
        return self.tau_rev + (g_sec * delta_gamma)

    def _backbone_tangent(self, gamma: float) -> float:
        gmax = float(self.params.get("gmax", self.gmax_fallback))
        gamma_ref = float(self.params.get("gamma_ref", 1.0e-3))
        tangent_floor = self._tangent_floor()
        ag = abs(gamma)
        if self.material == MaterialType.GQH:
            if {"tau_max", "theta1", "theta2", "theta3", "theta4", "theta5"}.issubset(self.params):
                step = max(ag * 1.0e-4, 1.0e-8)
                tau_p = float(
                    gqh_backbone_stress_from_params(
                        np.array([ag + step], dtype=np.float64),
                        self.params,
                        gmax_fallback=self.gmax_fallback,
                    )[0]
                )
                tau_m = float(
                    gqh_backbone_stress_from_params(
                        np.array([max(ag - step, 0.0)], dtype=np.float64),
                        self.params,
                        gmax_fallback=self.gmax_fallback,
                    )[0]
                )
                tangent = (tau_p - tau_m) / max(2.0 * step, 1.0e-12)
                return max(float(tangent), tangent_floor)
            a1 = float(self.params.get("a1", 1.0))
            a2 = float(self.params.get("a2", 0.0))
            m = float(self.params.get("m", 1.0))
            r = ag / max(gamma_ref, 1.0e-15)
            denom = 1.0 + a1 * r + a2 * (r**m)
            return max(gmax / (denom * denom), tangent_floor)
        if self.material == MaterialType.MKZ:
            ratio = ag / max(gamma_ref, 1.0e-15)
            denom = 1.0 + ratio
            return max(gmax / (denom * denom), tangent_floor)
        return self.gmax_fallback

    def _effective_reload_factor(self) -> float:
        base = max(self.reload_factor, 1.0e-6)
        if self._reversal_tangent_preserving_mrdf_enabled():
            return base
        mode_code_raw = self.params.get("adaptive_reload_mode_code", 0.0)
        try:
            mode_code = float(mode_code_raw)
        except (TypeError, ValueError):
            mode_code = 0.0
        if abs(mode_code) < 0.5:
            return base
        if abs(self.gamma_rev) <= self.eps_gamma or abs(self.tau_rev) <= self.eps_gamma:
            return base
        g_sec_rev = abs(self.tau_rev / self.gamma_rev)
        g_t_rev = self._backbone_tangent(self.gamma_rev)
        if not np.isfinite(g_sec_rev) or not np.isfinite(g_t_rev) or g_sec_rev <= 0.0 or g_t_rev <= 0.0:
            return base
        ratio = float(np.clip(g_sec_rev / g_t_rev, 0.25, 16.0))
        exponent_raw = self.params.get("adaptive_reload_exponent", 0.5)
        try:
            exponent = float(exponent_raw)
        except (TypeError, ValueError):
            exponent = 0.5
        exponent = float(np.clip(exponent, 0.0, 2.0))
        factor = ratio**exponent
        if mode_code < 0.0:
            k_eff = base / max(factor, 1.0e-12)
        else:
            k_eff = base * factor
        return float(np.clip(k_eff, 0.5, 4.0))

    def _adaptive_tangent_floor(
        self,
        gamma: float,
        *,
        g_t_ref: float,
        f_mrdf: float,
        tangent_floor: float,
    ) -> float:
        mode_code_raw = self.params.get("adaptive_tangent_mode_code", 0.0)
        try:
            mode_code = float(mode_code_raw)
        except (TypeError, ValueError):
            mode_code = 0.0
        if abs(mode_code) < 0.5:
            return tangent_floor
        if abs(self.gamma_rev) <= self.eps_gamma or abs(self.tau_rev) <= self.eps_gamma:
            return tangent_floor

        strength_raw = self.params.get("adaptive_tangent_strength", 0.0)
        try:
            strength = float(strength_raw)
        except (TypeError, ValueError):
            strength = 0.0
        strength = float(np.clip(strength, 0.0, 1.0))
        if strength <= 0.0:
            return tangent_floor

        exponent_raw = self.params.get("adaptive_tangent_exponent", 1.0)
        try:
            exponent = float(exponent_raw)
        except (TypeError, ValueError):
            exponent = 1.0
        exponent = float(np.clip(exponent, 0.0, 3.0))

        g_sec_rev = abs(self.tau_rev / self.gamma_rev)
        if not np.isfinite(g_sec_rev) or g_sec_rev <= 0.0:
            return tangent_floor

        gamma_hist = max(
            self.gamma_max_seen,
            abs(gamma),
            abs(self.gamma_prev),
            abs(self.gamma_rev),
            self.eps_gamma,
        )
        branch_progress = float(np.clip(abs(gamma - self.gamma_rev) / gamma_hist, 0.0, 1.0))
        mrdf_softening = float(np.clip(1.0 - f_mrdf, 0.0, 1.0))

        if mode_code < 0.0:
            g_target = max(float(self.params.get("gmax", self.gmax_fallback)) * self._reduction(gamma_hist), tangent_floor)
        else:
            g_target = max(g_sec_rev, tangent_floor)

        ratio = float(np.clip(g_target / max(g_t_ref, tangent_floor), 1.0, 8.0))
        ratio_gain = (ratio - 1.0) / ratio
        weight = strength * mrdf_softening * (branch_progress**exponent) * ratio_gain
        return max(g_t_ref + weight * max(g_target - g_t_ref, 0.0), tangent_floor)

    def _signed_backbone(self, gamma: float) -> float:
        if abs(gamma) <= self.eps_gamma:
            return 0.0
        return float(np.sign(gamma) * self._backbone(abs(gamma)))

    def _should_follow_backbone(self, gamma: float, tau_trial: float) -> bool:
        if abs(gamma) <= self.eps_gamma or self.direction == 0:
            return False
        if abs(gamma) < (max(self.gamma_max_seen, abs(self.gamma_rev)) - 1.0e-12):
            return False
        gamma_sign = _strain_direction(gamma, self.eps_gamma)
        if gamma_sign == 0 or gamma_sign != self.direction:
            return False
        tau_backbone = self._signed_backbone(gamma)
        tau_sign = _strain_direction(tau_trial, self.eps_gamma)
        backbone_sign = _strain_direction(tau_backbone, self.eps_gamma)
        if tau_sign == 0 or backbone_sign == 0 or tau_sign != backbone_sign:
            return False
        tau_prev_backbone = self._signed_backbone(self.gamma_prev)
        prev_gap = abs(self.tau_prev) - abs(tau_prev_backbone)
        curr_gap = abs(tau_trial) - abs(tau_backbone)
        # DeepSoil-style branch locking should happen only when the reload branch
        # actually intersects the backbone, not merely when the trial point is
        # locally close to it. Require a sign change in the branch-vs-backbone gap.
        return prev_gap < -1.0e-8 and curr_gap >= -1.0e-10

    def update_stress(self, gamma: float) -> float:
        if self.material not in {MaterialType.MKZ, MaterialType.GQH}:
            tau = self._backbone(gamma)
            self.gamma_prev = gamma
            self.tau_prev = tau
            self.gamma_max_seen = max(self.gamma_max_seen, abs(gamma))
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
            self.gamma_max_seen = abs(gamma)
            self.follow_backbone_until_reversal = False
            self.initialized = True
            return tau

        delta_gamma = gamma - self.gamma_prev
        new_direction = _strain_direction(delta_gamma, self.eps_gamma)
        if new_direction != 0 and new_direction != self.direction:
            self.gamma_rev = self.gamma_prev
            self.tau_rev = self.tau_prev
            self.direction = new_direction
            self.has_reversal = True
            self.follow_backbone_until_reversal = False
            self._capture_mrdf_bridge_state()
            self._record_reversal_branch(gamma)

        if self.direction == 0:
            self.direction = 1 if gamma >= self.gamma_prev else -1

        tau, _, branch_id, reason_code, _ = self.peek_branch_response(gamma)
        if reason_code == 0:
            self.follow_backbone_until_reversal = self.has_reversal
            self.last_selected_branch_id = None
        else:
            self.last_selected_branch_id = branch_id
            if self._nested_mrdf_memory_enabled() and branch_id is not None:
                self.active_branch_id = branch_id

        self.gamma_prev = gamma
        self.tau_prev = tau
        self.gamma_max_seen = max(self.gamma_max_seen, abs(gamma))
        return tau

    def tangent_modulus(self, gamma: float) -> float:
        """Return d(tau)/d(gamma) at given strain WITHOUT mutating state."""
        if self.material not in {MaterialType.MKZ, MaterialType.GQH}:
            return self.gmax_fallback
        return self.peek_branch_response(gamma)[1]


def solve_nonlinear_sh_response(
    config: ProjectConfig,
    motion: Motion,
    *,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
    substeps: int = 4,
    return_nodal_displacement: bool = False,
) -> tuple[FloatArray, FloatArray] | tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
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
    area = _solver_column_area(config)

    n_elem = len(element_slices)
    n_nodes = n_elem + 1
    use_elastic_halfspace = config.boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE
    n_free = n_nodes if use_elastic_halfspace else (n_nodes - 1)

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
        m_j = rho * area * dz
        k_j = g_mod * area / dz
        m_elem[j] = m_j
        k_elem[j] = k_j
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
    dashpot_c = 0.0
    if use_elastic_halfspace:
        bedrock = config.effective_bedrock()
        base_rho = float(max(bedrock.unit_weight_kn_m3 / 9.81, 1.0e-6))
        base_vs = float(max(bedrock.vs_m_s, 1.0e-6))
        dashpot_c = base_rho * base_vs * area
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
        xi_target = float(np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12)))
        alpha_rayleigh = 0.0
        beta_rayleigh = 0.0
        c_rayleigh_const = _modal_matched_damping_matrix(m_diag, k_initial, xi_target)
        if use_elastic_halfspace:
            c_rayleigh_const = c_rayleigh_const.copy()
            c_rayleigh_const[-1, -1] += dashpot_c
        rayleigh_update_matrix = False

    dt = float(motion.dt)
    dt_sub = dt / float(substeps)
    acc_g = effective_input_acceleration(config, motion.acc)
    n_steps = acc_g.size
    time = np.arange(n_steps, dtype=np.float64) * dt
    input_vel = _integrate_acc_to_velocity(acc_g, dt) if use_elastic_halfspace else None

    u = np.zeros((n_free,), dtype=np.float64)
    v = np.zeros((n_free,), dtype=np.float64)
    a_rel_hist = np.zeros((n_free, n_steps), dtype=np.float64)
    u_hist_full = np.zeros((n_nodes, n_steps), dtype=np.float64)
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
                k_sec_full = _assemble_tridiagonal_from_element_values(k_sec_elem, n_nodes)
                k_sec = k_sec_full[:n_free, :n_free]
                if rayleigh_update_matrix:
                    c_step = (alpha_rayleigh * m_mat) + (beta_rayleigh * k_sec)
                elif viscous_damping_update:
                    c_step = _modal_matched_damping_matrix(m_diag, k_sec, xi_target)
                    if use_elastic_halfspace:
                        c_step = c_step.copy()
                        c_step[-1, -1] += dashpot_c
                else:
                    c_step = c_rayleigh_const
            else:
                c_step = c_rayleigh_const
            a_curr = (f_ext - (c_step @ v) - f_int) / m_diag
            v = v + dt_sub * a_curr
            u = u + dt_sub * v
            a_prev = a_curr
        a_rel_hist[:, i] = a_prev
        u_hist_full[:n_free, i] = u

    if n_free == 0:
        surface_acc = acc_g.copy()
    else:
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
