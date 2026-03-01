import sqlite3
from pathlib import Path

from dsra1d.config import load_project_config
from dsra1d.motion import load_motion
from dsra1d.pipeline import run_analysis
from dsra1d.verify import verify_batch, verify_run


def test_verify_run_passes_for_fresh_output(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    report = verify_run(result.output_dir)
    assert report.ok is True
    assert report.checks["metrics_delta_u_max_match"] is True
    assert report.checks["metrics_sigma_v_ref_match"] is True
    assert report.checks["metrics_sigma_v_eff_min_match"] is True
    assert report.checks["pwp_effective_table_readable"] is True
    assert report.checks["pwp_effective_rows_match"] is True
    assert report.checks["pwp_effective_time_start_match"] is True
    assert report.checks["pwp_effective_time_end_match"] is True
    assert report.checks["pwp_effective_delta_u_max_match"] is True
    assert report.checks["pwp_effective_sigma_v_eff_min_match"] is True


def test_verify_run_detects_metric_tamper(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    with sqlite3.connect(result.sqlite_path) as conn:
        conn.execute(
            "UPDATE metrics SET value = value + 1.0 WHERE name = 'pga'"
        )
        conn.commit()

    report = verify_run(result.output_dir)
    assert report.ok is False
    assert report.checks["metrics_pga_match"] is False


def test_verify_run_detects_pwp_effective_table_tamper(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    with sqlite3.connect(result.sqlite_path) as conn:
        conn.execute(
            "UPDATE pwp_effective_stats SET sigma_v_eff = sigma_v_eff + 1.0 WHERE run_id = ?",
            (result.run_id,),
        )
        conn.commit()

    report = verify_run(result.output_dir)
    assert report.ok is False
    assert report.checks["pwp_effective_sigma_v_eff_min_match"] is False


def test_verify_batch_passes_for_multiple_runs(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    _ = run_analysis(cfg, motion, output_dir=tmp_path / "runs")
    cfg2 = cfg.model_copy(deep=True)
    cfg2.seed = cfg.seed + 123
    _ = run_analysis(cfg2, motion, output_dir=tmp_path / "runs")

    report = verify_batch(tmp_path / "runs", require_runs=2)
    assert report.ok is True
    assert report.total_runs == 2
    assert report.failed_runs == 0


def test_verify_batch_require_runs_fails_when_insufficient(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    _ = run_analysis(cfg, motion, output_dir=tmp_path / "runs")
    report = verify_batch(tmp_path / "runs", require_runs=2)
    assert report.ok is False
    assert report.total_runs == 1


def test_verify_batch_handles_missing_path(tmp_path: Path) -> None:
    report = verify_batch(tmp_path / "missing_runs")
    assert report.ok is False
    assert report.total_runs == 0
    assert "_batch" in report.reports


def test_verify_run_handles_corrupted_hdf5(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    result.hdf5_path.write_bytes(b"corrupted")
    report = verify_run(result.output_dir)
    assert report.ok is False
    assert report.checks.get("hdf5_readable") is False
