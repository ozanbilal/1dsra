import json
import sqlite3
from pathlib import Path

import h5py
from dsra1d.config import load_project_config
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis, run_batch


def test_run_analysis_mock(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)

    assert result.hdf5_path.exists()
    assert result.sqlite_path.exists()

    with h5py.File(result.hdf5_path, "r") as h5:
        assert "/mesh/layer_idx" in h5
        assert "/mesh/dz" in h5
        assert "/pwp/delta_u" in h5
        assert "/pwp/sigma_v_ref" in h5
        assert "/pwp/sigma_v_eff" in h5
        assert h5["/mesh/layer_idx"].shape[0] >= 1

    conn = sqlite3.connect(result.sqlite_path)
    try:
        n_mesh = conn.execute("SELECT COUNT(*) FROM mesh_slices").fetchone()[0]
        n_artifacts = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        n_checksums = conn.execute("SELECT COUNT(*) FROM checksums").fetchone()[0]
        n_pwp_effective = conn.execute("SELECT COUNT(*) FROM pwp_effective_stats").fetchone()[0]
    finally:
        conn.close()
    assert n_mesh >= 1
    assert n_artifacts >= 4
    assert n_checksums >= 1
    assert n_pwp_effective >= 1
    assert (result.output_dir / "run_meta.json").exists()
    run_meta = json.loads((result.output_dir / "run_meta.json").read_text(encoding="utf-8"))
    checksums = run_meta.get("checksums", {})
    assert isinstance(checksums, dict)
    assert "results.h5" in checksums
    assert "results.sqlite" in checksums

    store = load_result(result.output_dir)
    assert store.acc_surface.size > 0
    assert store.spectra_periods.size == 80


def test_run_analysis_opensees_missing_executable_fallback(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.opensees.executable = "OpenSees_DOES_NOT_EXIST"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)

    assert result.status == "error"
    assert "OpenSees executable not found" in result.message
    assert result.hdf5_path.exists()
    assert result.sqlite_path.exists()
    assert (result.output_dir / "run_meta.json").exists()


def test_run_id_is_stable_and_config_sensitive(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    r1 = run_analysis(cfg, motion, output_dir=tmp_path / "runs")
    r2 = run_analysis(cfg, motion, output_dir=tmp_path / "runs")
    assert r1.run_id == r2.run_id

    cfg_changed = cfg.model_copy(deep=True)
    cfg_changed.seed = cfg.seed + 1
    r3 = run_analysis(cfg_changed, motion, output_dir=tmp_path / "runs")
    assert r3.run_id != r1.run_id


def test_run_batch_deduplicates_identical_motions(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion1 = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    motion2 = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    batch = run_batch(cfg, [motion1, motion2], output_dir=tmp_path / "batch", n_jobs=2)
    assert len(batch.results) == 2
    assert batch.results[0].run_id == batch.results[1].run_id
    assert batch.results[0].status == "ok"
    run_dirs = [p for p in (tmp_path / "batch").iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
