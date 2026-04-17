from __future__ import annotations

import numpy as np
import pytest
from dsra1d.config import MaterialType
from dsra1d.materials import mkz_backbone_stress
from dsra1d.materials.mrdf import mrdf_coefficients_from_params
from dsra1d.nonlinear import _ElementConstitutiveState, simulate_hysteretic_stress_path


def _closed_strain_cycle(gamma_amp: float, n: int = 120) -> np.ndarray:
    up = np.linspace(0.0, gamma_amp, n, dtype=np.float64)
    down = np.linspace(gamma_amp, -gamma_amp, 2 * n, dtype=np.float64)[1:]
    back = np.linspace(-gamma_amp, gamma_amp, 2 * n, dtype=np.float64)[1:]
    return np.concatenate([up, down, back])


def test_mkz_monotonic_loading_matches_backbone() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0012,
        "reload_factor": 2.0,
    }
    strain = np.linspace(0.0, 0.004, 200, dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_expected = mkz_backbone_stress(
        strain,
        gmax=70000.0,
        gamma_ref=0.0012,
    )
    assert np.allclose(tau, tau_expected, rtol=1.0e-6, atol=1.0e-9)


def test_hysteretic_cycle_has_positive_energy_dissipation() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
    }
    strain = _closed_strain_cycle(0.005, n=120)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    energy = float(abs(np.trapezoid(tau, strain)))
    assert energy > 1.0e-6


def test_reload_factor_changes_hysteretic_response() -> None:
    params_masing = {
        "gmax": 90000.0,
        "gamma_ref": 0.0011,
        "a1": 1.0,
        "a2": 0.3,
        "m": 2.0,
        "reload_factor": 2.0,
    }
    params_non_masing = dict(params_masing)
    params_non_masing["reload_factor"] = 1.0
    strain = _closed_strain_cycle(0.0045, n=100)
    tau_masing = simulate_hysteretic_stress_path(
        MaterialType.GQH,
        params_masing,
        strain,
        gmax_fallback=90000.0,
    )
    tau_non_masing = simulate_hysteretic_stress_path(
        MaterialType.GQH,
        params_non_masing,
        strain,
        gmax_fallback=90000.0,
    )
    assert not np.allclose(tau_masing, tau_non_masing)
    energy_masing = float(abs(np.trapezoid(tau_masing, strain)))
    energy_non_masing = float(abs(np.trapezoid(tau_non_masing, strain)))
    assert abs(energy_masing - energy_non_masing) > 1.0e-6


def test_mrdf_zero_factor_uses_local_translated_reference_branch() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
    }
    strain = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_rev = float(
        mkz_backbone_stress(
            np.array([0.0040], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    )
    tau_delta = float(
        mkz_backbone_stress(
            np.array([0.0020], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    )
    expected = tau_rev - tau_delta
    assert tau[2] == pytest.approx(expected, rel=1.0e-8, abs=1.0e-10)


def test_mrdf_uiuc_factor_depends_on_historical_max_strain() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    low_history = np.array([0.0, 0.0020, 0.0010], dtype=np.float64)
    high_history = np.array([0.0, 0.0040, 0.0030], dtype=np.float64)
    tau_low = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        low_history,
        gmax_fallback=70000.0,
    )
    tau_high = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        high_history,
        gmax_fallback=70000.0,
    )
    assert abs(tau_high[-1] - tau_low[-1]) > 1.0e-6


def test_mrdf_secant_reference_blend_uses_reversal_secant_branch() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
        "reload_reference_blend": 1.0,
    }
    strain = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_rev = float(
        mkz_backbone_stress(
            np.array([0.0040], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    )
    g_sec_hist = float(
        mkz_backbone_stress(
            np.array([0.0040], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    ) / 0.0040
    expected = tau_rev + (g_sec_hist * (0.0020 - 0.0040))
    assert tau[2] == pytest.approx(expected, rel=1.0e-8, abs=1.0e-10)


def test_mrdf_secant_reference_blend_stiffens_unload_branch_relative_to_local_anchor() -> None:
    params_local = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
        "reload_reference_blend": 0.0,
    }
    params_global = dict(params_local)
    params_global["reload_reference_blend"] = 1.0
    strain = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)
    tau_local = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_local,
        strain,
        gmax_fallback=70000.0,
    )
    tau_global = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_global,
        strain,
        gmax_fallback=70000.0,
    )
    assert tau_global[2] > tau_local[2]


def test_mrdf_reference_mode_uses_latched_secant_gref_bridge() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
        "mrdf_reference_mode_code": 1.0,
    }
    strain = np.array([0.0, 0.0040, 0.0030, 0.0020], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_rev = float(
        mkz_backbone_stress(
            np.array([0.0040], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    )
    g_ref = 70000.0 / (1.0 + (0.0040 / 0.0010))
    expected = np.array(
        [
            0.0,
            tau_rev,
            tau_rev - (g_ref * 0.0010),
            tau_rev - (g_ref * 0.0020),
        ],
        dtype=np.float64,
    )
    assert np.allclose(tau, expected, rtol=1.0e-8, atol=1.0e-10)


def test_nested_mrdf_memory_records_reversal_branches() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 2.0,
    }
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    for gamma in np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010, 0.0005], dtype=np.float64):
        state.update_stress(float(gamma))
    assert state.branch_counter == 2
    assert state.active_branch_id is not None
    assert len(state.branch_stack) == 2


def test_nested_mrdf_memory_returns_backbone_tangent_when_replaying() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 2.0,
    }
    strain = np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010, 0.0005], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    assert np.all(np.isfinite(tau))
    tangent = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    for gamma in strain:
        tangent.update_stress(float(gamma))
    assert all(np.isfinite([tangent.tangent_modulus(float(value)) for value in strain]))


def test_nested_mrdf_memory_switches_active_branch_to_replayed_branch() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 2.0,
    }
    # Deterministic zig-zag path that triggers prior-branch intersections.
    strain = np.array(
        [
            0.0,
            0.0019058810230192771,
            0.0000034470734585,
            0.0009077673265064,
            0.0017852456856078,
            0.0019376080007696,
            0.0030600802958863,
            0.0014620657593723,
            0.0024237117493855,
            0.0015577970751360,
            0.0021561924219755,
            0.0027889690621490,
            0.0047523697417713,
            0.0060000000000000,
            0.0060000000000000,
            0.0040571417148893,
            0.0037369970511949,
            0.0021612991339445,
            0.0003184334948418,
            0.0014227530950358,
            0.0016412172954206,
        ],
        dtype=np.float64,
    )
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    replay_switch_count = 0
    for gamma in strain:
        state.update_stress(float(gamma))
        if (
            state.branch_stack
            and state.active_branch_id is not None
            and state.active_branch_id != state.branch_stack[-1].branch_id
        ):
            replay_switch_count += 1
    assert replay_switch_count > 0


def test_mode3_reversal_tangent_is_g0_at_reversal_point() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 3.0,
        "adaptive_reload_mode_code": 1.0,
        "adaptive_tangent_mode_code": 1.0,
        "reload_reference_blend": 1.0,
    }
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    for gamma in np.array([0.0, 0.0040, 0.0020], dtype=np.float64):
        state.update_stress(float(gamma))
    _, tangent, _, _, branch_state = state.peek_branch_response(0.0040)
    assert branch_state is not None
    assert tangent == pytest.approx(70000.0, rel=1.0e-8, abs=1.0e-8)


def test_mode3_latches_gamma_m_global_from_history() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 3.0,
    }
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    for gamma in np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010], dtype=np.float64):
        state.update_stress(float(gamma))
    _, _, _, _, branch_state = state.peek_branch_response(0.0005)
    assert branch_state is not None
    assert branch_state.gamma_m_global == pytest.approx(0.0040, rel=1.0e-8, abs=1.0e-10)


def test_mode4_restores_tangent_without_changing_translated_tau_anchor() -> None:
    base_params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    current = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=dict(base_params),
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(base_params),
    )
    mode4_params = dict(base_params)
    mode4_params["mrdf_reference_mode_code"] = 4.0
    mode4 = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=mode4_params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(mode4_params),
    )
    history = np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010], dtype=np.float64)
    for gamma in history:
        current.update_stress(float(gamma))
        mode4.update_stress(float(gamma))

    target = 0.0005
    tau_current, kt_current, _, _, branch_current = current.peek_branch_response(target)
    tau_mode4, kt_mode4, _, _, branch_mode4 = mode4.peek_branch_response(target)
    assert branch_current is not None
    assert branch_mode4 is not None
    assert branch_current.branch_kind == "translated_local_bridge"
    assert branch_mode4.branch_kind == "translated_local_tangent_restore_bridge"
    assert tau_mode4 == pytest.approx(tau_current, rel=1.0e-10, abs=1.0e-10)
    assert branch_mode4.f_mrdf == pytest.approx(branch_current.f_mrdf, rel=1.0e-10, abs=1.0e-10)
    assert branch_mode4.g_t_ref > branch_current.g_t_ref
    assert kt_mode4 > kt_current
    assert kt_mode4 < 70000.0


def test_mode5_evolves_f_mrdf_from_reversal_toward_history_target() -> None:
    base_params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    current = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=dict(base_params),
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(base_params),
    )
    mode5_params = dict(base_params)
    mode5_params["mrdf_reference_mode_code"] = 5.0
    mode5 = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=mode5_params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(mode5_params),
    )
    history = np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010], dtype=np.float64)
    for gamma in history:
        current.update_stress(float(gamma))
        mode5.update_stress(float(gamma))

    _, _, _, _, branch_at_reversal = mode5.peek_branch_response(-0.0030)
    assert branch_at_reversal is not None
    assert branch_at_reversal.branch_kind == "translated_local_progressive_f_bridge"
    assert branch_at_reversal.f_mrdf == pytest.approx(1.0, rel=1.0e-10, abs=1.0e-10)

    target = 0.0005
    tau_current, kt_current, _, _, branch_current = current.peek_branch_response(target)
    tau_mode5, kt_mode5, _, _, branch_mode5 = mode5.peek_branch_response(target)
    assert branch_current is not None
    assert branch_mode5 is not None
    assert branch_current.branch_kind == "translated_local_bridge"
    assert branch_mode5.branch_kind == "translated_local_progressive_f_bridge"
    assert branch_mode5.f_mrdf > branch_current.f_mrdf
    assert branch_mode5.f_mrdf < 1.0
    assert np.isfinite(tau_current)
    assert np.isfinite(tau_mode5)
    assert kt_mode5 > kt_current
    assert kt_mode5 < 70000.0


def test_mode6_evolves_translated_branch_curvature_from_g0_to_local_branch() -> None:
    base_params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    current = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=dict(base_params),
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(base_params),
    )
    mode6_params = dict(base_params)
    mode6_params["mrdf_reference_mode_code"] = 6.0
    mode6 = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=mode6_params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(mode6_params),
    )
    history = np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010], dtype=np.float64)
    for gamma in history:
        current.update_stress(float(gamma))
        mode6.update_stress(float(gamma))

    _, _, _, _, branch_at_reversal_current = current.peek_branch_response(-0.0030)
    _, _, _, _, branch_at_reversal = mode6.peek_branch_response(-0.0030)
    assert branch_at_reversal_current is not None
    assert branch_at_reversal is not None
    assert branch_at_reversal.branch_kind == "translated_curvature_progressive_bridge"
    assert branch_at_reversal_current.branch_kind == "translated_local_bridge"
    assert branch_at_reversal.f_mrdf == pytest.approx(
        branch_at_reversal_current.f_mrdf,
        rel=1.0e-10,
        abs=1.0e-10,
    )
    assert branch_at_reversal.g_t_ref == pytest.approx(70000.0, rel=1.0e-10, abs=1.0e-10)

    target = 0.0005
    tau_current, kt_current, _, _, branch_current = current.peek_branch_response(target)
    tau_mode6, kt_mode6, _, _, branch_mode6 = mode6.peek_branch_response(target)
    assert branch_current is not None
    assert branch_mode6 is not None
    assert branch_current.branch_kind == "translated_local_bridge"
    assert branch_mode6.branch_kind == "translated_curvature_progressive_bridge"
    assert branch_mode6.f_mrdf == pytest.approx(branch_current.f_mrdf, rel=1.0e-10, abs=1.0e-10)
    assert branch_mode6.g_t_ref > branch_current.g_t_ref
    assert branch_mode6.g_t_ref < 70000.0
    assert np.isfinite(tau_current)
    assert np.isfinite(tau_mode6)
    assert kt_mode6 > kt_current
    assert kt_mode6 < 70000.0


def test_mode7_combines_curvature_progression_with_tangent_restore() -> None:
    base_params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    mode6_params = dict(base_params)
    mode6_params["mrdf_reference_mode_code"] = 6.0
    mode6 = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=mode6_params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(mode6_params),
    )
    mode7_params = dict(base_params)
    mode7_params["mrdf_reference_mode_code"] = 7.0
    mode7 = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=mode7_params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(mode7_params),
    )
    history = np.array([0.0, 0.0040, 0.0020, -0.0030, -0.0010], dtype=np.float64)
    for gamma in history:
        mode6.update_stress(float(gamma))
        mode7.update_stress(float(gamma))

    target = 0.0005
    tau_mode6, kt_mode6, _, _, branch_mode6 = mode6.peek_branch_response(target)
    tau_mode7, kt_mode7, _, _, branch_mode7 = mode7.peek_branch_response(target)
    assert branch_mode6 is not None
    assert branch_mode7 is not None
    assert branch_mode6.branch_kind == "translated_curvature_progressive_bridge"
    assert branch_mode7.branch_kind == "translated_curvature_tangent_restore_bridge"
    assert branch_mode7.f_mrdf == pytest.approx(branch_mode6.f_mrdf, rel=1.0e-10, abs=1.0e-10)
    assert np.isfinite(tau_mode6)
    assert np.isfinite(tau_mode7)
    assert branch_mode7.g_t_ref > branch_mode6.g_t_ref
    assert kt_mode7 > kt_mode6
    assert kt_mode7 < 70000.0


def test_peek_branch_response_matches_update_and_tangent() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 3.0,
    }
    strain = np.array(
        [
            0.0,
            0.0019058810230192771,
            0.0000034470734585,
            0.0009077673265064,
            0.0017852456856078,
            0.0019376080007696,
            0.0030600802958863,
            0.0014620657593723,
            0.0024237117493855,
            0.0015577970751360,
            0.0021561924219755,
            0.0027889690621490,
            0.0047523697417713,
            0.0060000000000000,
            0.0060000000000000,
            0.0040571417148893,
            0.0037369970511949,
            0.0021612991339445,
            0.0003184334948418,
            0.0014227530950358,
        ],
        dtype=np.float64,
    )
    target = 0.0016412172954206
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    for gamma in strain:
        state.update_stress(float(gamma))

    tau_peek, kt_peek, branch_id_peek, _, _ = state.peek_branch_response(target)
    assert state.tangent_modulus(target) == pytest.approx(kt_peek, rel=1.0e-10, abs=1.0e-10)

    tau_update = state.update_stress(target)
    assert tau_update == pytest.approx(tau_peek, rel=1.0e-10, abs=1.0e-10)
    assert state.last_selected_branch_id == branch_id_peek


def test_mrdf_reference_mode_latches_gref_for_entire_branch_until_next_reversal() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
        "mrdf_reference_mode_code": 1.0,
    }
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=params,
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    for gamma in np.array([0.0, 0.0040, 0.0020, -0.0050], dtype=np.float64):
        state.update_stress(float(gamma))
    expected_gref = 70000.0 / (1.0 + (0.0040 / 0.0010))
    assert state.mrdf_bridge_g_ref == pytest.approx(expected_gref, rel=1.0e-8, abs=1.0e-10)


def test_reload_branch_latches_to_backbone_after_true_intersection() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.4,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    strain = np.array(
        [0.0, 0.0020, -0.0005, -0.00025, 0.0, 0.0005, 0.0010, 0.0015, 0.0020, 0.0025],
        dtype=np.float64,
    )
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_backbone = mkz_backbone_stress(
        strain,
        gmax=70000.0,
        gamma_ref=0.0010,
    )
    assert tau[-2] == pytest.approx(float(tau_backbone[-2]), rel=1.0e-8, abs=1.0e-10)
    assert tau[-1] == pytest.approx(float(tau_backbone[-1]), rel=1.0e-8, abs=1.0e-10)


def test_adaptive_reload_rule_changes_hysteretic_response() -> None:
    params_fixed = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    params_adaptive = dict(params_fixed)
    params_adaptive["adaptive_reload_mode_code"] = 1.0
    params_adaptive["adaptive_reload_exponent"] = 0.5
    strain = _closed_strain_cycle(0.0045, n=100)
    tau_fixed = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_fixed,
        strain,
        gmax_fallback=70000.0,
    )
    tau_adaptive = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_adaptive,
        strain,
        gmax_fallback=70000.0,
    )
    assert not np.allclose(tau_fixed, tau_adaptive)


def test_adaptive_tangent_floor_stiffens_branch_tangent_without_changing_backbone() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    strain_path = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)

    fixed = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=dict(params),
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    adaptive = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params={
            **params,
            "adaptive_tangent_mode_code": 1.0,
            "adaptive_tangent_strength": 0.4,
            "adaptive_tangent_exponent": 1.0,
        },
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(
            {
                **params,
                "adaptive_tangent_mode_code": 1.0,
                "adaptive_tangent_strength": 0.4,
                "adaptive_tangent_exponent": 1.0,
            }
        ),
    )

    for gamma in strain_path:
        fixed.update_stress(float(gamma))
        adaptive.update_stress(float(gamma))

    tangent_fixed = fixed.tangent_modulus(float(strain_path[-1]))
    tangent_adaptive = adaptive.tangent_modulus(float(strain_path[-1]))
    assert tangent_adaptive >= tangent_fixed


def test_elastic_path_reduces_to_linear_stress() -> None:
    strain = np.array([0.0, 1.0e-4, 2.0e-4, -1.0e-4, 3.0e-4], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.ELASTIC,
        {},
        strain,
        gmax_fallback=12345.0,
    )
    assert np.allclose(tau, 12345.0 * strain, rtol=0.0, atol=1.0e-12)
