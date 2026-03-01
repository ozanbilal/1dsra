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
