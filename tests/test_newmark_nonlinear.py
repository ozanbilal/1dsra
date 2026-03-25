"""Tests for Newmark-beta implicit nonlinear solver."""
from pathlib import Path

import numpy as np
from dsra1d.config import BoundaryCondition, load_project_config
from dsra1d.motion import load_motion
from dsra1d.newmark_nonlinear import solve_nonlinear_newmark
from dsra1d.nonlinear import _ElementConstitutiveState, solve_nonlinear_sh_response
from dsra1d.config import MaterialType


def _load_mkz_config_and_motion():
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(
        Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units
    )
    return cfg, motion


def test_newmark_returns_finite_response() -> None:
    cfg, motion = _load_mkz_config_and_motion()
    time, surface = solve_nonlinear_newmark(cfg, motion)
    assert time.shape == surface.shape
    assert surface.size == motion.acc.size
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_newmark_greater_pga_than_euler() -> None:
    """Newmark should produce higher PGA than Euler (less numerical dissipation)."""
    cfg, motion = _load_mkz_config_and_motion()
    _, surface_newmark = solve_nonlinear_newmark(cfg, motion)
    _, surface_euler = solve_nonlinear_sh_response(cfg, motion)
    pga_newmark = float(np.max(np.abs(surface_newmark)))
    pga_euler = float(np.max(np.abs(surface_euler)))
    # Newmark preserves energy -> higher PGA
    assert pga_newmark > pga_euler * 0.95, (
        f"Newmark PGA {pga_newmark:.4f} should exceed Euler PGA {pga_euler:.4f}"
    )


def test_newmark_elastic_halfspace_finite() -> None:
    cfg, motion = _load_mkz_config_and_motion()
    cfg.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    time, surface = solve_nonlinear_newmark(cfg, motion)
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_newmark_rayleigh_damping_finite() -> None:
    cfg, motion = _load_mkz_config_and_motion()
    cfg.analysis.damping_mode = "rayleigh"
    cfg.analysis.rayleigh_mode_1_hz = 1.0
    cfg.analysis.rayleigh_mode_2_hz = 10.0
    time, surface = solve_nonlinear_newmark(cfg, motion)
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_tangent_modulus_mkz_correctness() -> None:
    """Tangent modulus should match finite-difference approximation."""
    state = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params={"gmax": 100000.0, "gamma_ref": 0.001, "damping_min": 0.02},
        gmax_fallback=100000.0,
        reload_factor=2.0,
    )
    # Initialize on backbone
    state.update_stress(0.0)

    for gamma in [1e-5, 1e-4, 5e-4, 1e-3, 5e-3]:
        g_t = state.tangent_modulus(gamma)
        eps = 1.0e-8
        tau_plus = 100000.0 * (gamma + eps) / (1.0 + abs(gamma + eps) / 0.001)
        tau_minus = 100000.0 * (gamma - eps) / (1.0 + abs(gamma - eps) / 0.001)
        g_fd = (tau_plus - tau_minus) / (2.0 * eps)
        assert abs(g_t - g_fd) / max(abs(g_fd), 1.0) < 0.05, (
            f"Tangent mismatch at gamma={gamma}: analytical={g_t:.1f}, FD={g_fd:.1f}"
        )


def test_newmark_darendeli_calibrated_config() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_darendeli.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(
        Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units
    )
    time, surface = solve_nonlinear_newmark(cfg, motion)
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0
