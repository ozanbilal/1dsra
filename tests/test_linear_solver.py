from pathlib import Path

import numpy as np
from dsra1d.config import load_project_config
from dsra1d.linear import solve_equivalent_linear_sh_response, solve_linear_sh_response
from dsra1d.motion import load_motion
from dsra1d.pipeline import run_analysis
from dsra1d.verify import verify_run


def test_linear_solver_returns_finite_response() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    time, surface = solve_linear_sh_response(cfg, motion)
    assert time.shape == surface.shape
    assert surface.size == motion.acc.size
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_run_analysis_linear_backend_writes_verifiable_outputs(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "linear"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    result = run_analysis(cfg, motion, output_dir=tmp_path)
    assert result.status == "ok"
    report = verify_run(result.output_dir)
    assert report.ok is True


def test_eql_solver_returns_finite_response_and_iterations() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "eql"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    eql = solve_equivalent_linear_sh_response(cfg, motion)
    assert eql.iterations >= 1
    assert isinstance(eql.converged, bool)
    assert len(eql.max_change_history) == eql.iterations
    assert eql.response.time.shape == eql.response.surface_acc.shape
    assert eql.response.surface_acc.size == motion.acc.size
    assert np.all(np.isfinite(eql.response.surface_acc))
    assert float(np.std(eql.response.surface_acc)) > 0.0


def test_run_analysis_eql_backend_writes_summary_artifact(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "eql"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    result = run_analysis(cfg, motion, output_dir=tmp_path)
    assert result.status == "ok"
    assert (result.output_dir / "eql_summary.json").exists()
