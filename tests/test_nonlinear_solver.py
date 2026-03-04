from pathlib import Path

import numpy as np
from dsra1d.config import load_project_config
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
