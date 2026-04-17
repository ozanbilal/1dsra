from pathlib import Path

import numpy as np
from dsra1d.config import BedrockProperties, BoundaryCondition, load_project_config
from dsra1d.motion import load_motion
from dsra1d.nonlinear import solve_nonlinear_sh_response
from dsra1d.pipeline import run_analysis
from dsra1d.verify import verify_run


def test_nonlinear_solver_returns_finite_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "nonlinear"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    time, surface = solve_nonlinear_sh_response(cfg, motion)
    assert time.shape == surface.shape
    assert surface.size == motion.acc.size
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_run_analysis_nonlinear_backend_writes_verifiable_outputs(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "nonlinear"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    result = run_analysis(cfg, motion, output_dir=tmp_path)
    assert result.status == "ok"
    report = verify_run(result.output_dir)
    assert report.ok is True


def test_nonlinear_solver_reload_factor_changes_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    _, surface_default = solve_nonlinear_sh_response(cfg, motion)

    cfg_changed = cfg.model_copy(deep=True)
    cfg_changed.profile.layers[0].material_params["reload_factor"] = 1.0
    cfg_changed.profile.layers[1].material_params["reload_factor"] = 1.0
    _, surface_changed = solve_nonlinear_sh_response(cfg_changed, motion)

    assert surface_default.shape == surface_changed.shape
    # Non-Masing factor change should alter the surface response.
    assert not np.allclose(surface_default, surface_changed)


def test_nonlinear_solver_rayleigh_update_matrix_returns_finite_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.analysis.solver_backend = "nonlinear"
    cfg.analysis.damping_mode = "rayleigh"
    cfg.analysis.rayleigh_mode_1_hz = 1.0
    cfg.analysis.rayleigh_mode_2_hz = 10.0
    cfg.analysis.rayleigh_update_matrix = True
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    time, surface = solve_nonlinear_sh_response(cfg, motion)
    assert time.shape == surface.shape
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_nonlinear_solver_elastic_halfspace_changes_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.boundary_condition = BoundaryCondition.RIGID
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    _, surface_rigid = solve_nonlinear_sh_response(cfg, motion)

    cfg_halfspace = cfg.model_copy(deep=True)
    cfg_halfspace.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    _, surface_halfspace = solve_nonlinear_sh_response(cfg_halfspace, motion)

    assert surface_rigid.shape == surface_halfspace.shape
    assert np.all(np.isfinite(surface_halfspace))
    assert not np.allclose(surface_rigid, surface_halfspace)


def test_nonlinear_solver_bedrock_damping_ratio_does_not_change_time_domain_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    cfg_zero = cfg.model_copy(deep=True)
    cfg_zero.profile.bedrock = BedrockProperties(
        name="Rock",
        vs_m_s=760.0,
        unit_weight_kN_m3=25.0,
        damping_ratio=0.0,
    )
    _, surface_zero = solve_nonlinear_sh_response(cfg_zero, motion)

    cfg_damped = cfg.model_copy(deep=True)
    cfg_damped.profile.bedrock = BedrockProperties(
        name="Rock",
        vs_m_s=760.0,
        unit_weight_kN_m3=25.0,
        damping_ratio=0.02,
    )
    _, surface_damped = solve_nonlinear_sh_response(cfg_damped, motion)

    assert surface_zero.shape == surface_damped.shape
    assert np.all(np.isfinite(surface_zero))
    assert np.all(np.isfinite(surface_damped))
    assert np.allclose(surface_zero, surface_damped)


def test_nonlinear_solver_viscous_damping_update_changes_response() -> None:
    """Viscous damping update (secant-stiffness based) should alter nonlinear response."""
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.analysis.damping_mode = "frequency_independent"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    cfg_on = cfg.model_copy(deep=True)
    cfg_on.analysis.viscous_damping_update = True
    _, surface_on = solve_nonlinear_sh_response(cfg_on, motion)

    cfg_off = cfg.model_copy(deep=True)
    cfg_off.analysis.viscous_damping_update = False
    _, surface_off = solve_nonlinear_sh_response(cfg_off, motion)

    assert surface_on.shape == surface_off.shape
    assert np.all(np.isfinite(surface_on))
    assert np.all(np.isfinite(surface_off))
    # Updated damping should produce different response from fixed damping.
    assert not np.allclose(surface_on, surface_off)


def test_nonlinear_solver_viscous_damping_update_elastic_halfspace() -> None:
    """Viscous damping update should work with elastic halfspace boundary."""
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.analysis.damping_mode = "frequency_independent"
    cfg.analysis.viscous_damping_update = True
    cfg.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    time, surface = solve_nonlinear_sh_response(cfg, motion)
    assert time.shape == surface.shape
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_nonlinear_solver_accepts_darendeli_calibrated_config() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_darendeli.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    time, surface = solve_nonlinear_sh_response(cfg, motion)
    assert time.shape == surface.shape
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0
