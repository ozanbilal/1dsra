import json
import sqlite3
from pathlib import Path

import dsra1d.pipeline as pipeline_mod
import h5py
import numpy as np
from dsra1d.config import load_project_config
from dsra1d.interop.opensees.runner import OpenSeesExecutionError, OpenSeesRunOutput
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis, run_batch
from dsra1d.types import Motion


def test_run_analysis_mock(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "mock"
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
        assert "/spectra/freq_hz" in h5
        assert "/spectra/transfer_abs" in h5
        assert h5["/mesh/layer_idx"].shape[0] >= 1

    conn = sqlite3.connect(result.sqlite_path)
    try:
        n_mesh = conn.execute("SELECT COUNT(*) FROM mesh_slices").fetchone()[0]
        n_artifacts = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        n_checksums = conn.execute("SELECT COUNT(*) FROM checksums").fetchone()[0]
        n_pwp_effective = conn.execute("SELECT COUNT(*) FROM pwp_effective_stats").fetchone()[0]
        n_transfer = conn.execute("SELECT COUNT(*) FROM transfer_function").fetchone()[0]
    finally:
        conn.close()
    assert n_mesh >= 1
    assert n_artifacts >= 4
    assert n_checksums >= 1
    assert n_pwp_effective >= 1
    assert n_transfer >= 1
    assert (result.output_dir / "run_meta.json").exists()
    assert (result.output_dir / "config_snapshot.json").exists()
    run_meta = json.loads((result.output_dir / "run_meta.json").read_text(encoding="utf-8"))
    checksums = run_meta.get("checksums", {})
    assert isinstance(checksums, dict)
    assert "results.h5" in checksums
    assert "results.sqlite" in checksums
    assert "config_snapshot" in run_meta

    store = load_result(result.output_dir)
    assert store.acc_surface.size > 0
    assert store.spectra_periods.size == 80
    assert store.transfer_freq_hz.size > 0
    assert store.transfer_abs.size == store.transfer_freq_hz.size
    assert store.ru.size > 0
    assert store.delta_u.size > 0
    assert store.sigma_v_eff.size > 0


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


def test_run_analysis_opensees_missing_required_outputs_falls_back(tmp_path, monkeypatch) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.opensees.executable = "OpenSees"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    def _fake_run_opensees(executable, tcl_file, cwd, timeout_s, extra_args=None):
        _ = (executable, tcl_file, cwd, timeout_s, extra_args)
        return OpenSeesRunOutput(
            returncode=0,
            stdout="fake ok",
            stderr="",
            command=["OpenSees", str(tcl_file)],
        )

    monkeypatch.setattr(pipeline_mod, "run_opensees", _fake_run_opensees)
    result = run_analysis(cfg, motion, output_dir=tmp_path / "opensees-missing-outs")
    assert result.status == "error"
    assert "required output files" in result.message


def test_run_analysis_opensees_pm4_divergence_has_actionable_message(tmp_path, monkeypatch) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.opensees.executable = "OpenSees"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    def _fake_run_opensees(executable, tcl_file, cwd, timeout_s, extra_args=None):
        _ = (executable, tcl_file, cwd, timeout_s, extra_args)
        raise OpenSeesExecutionError(
            "OpenSees failed with code -3",
            stderr="PM4Sand ...\nVector::operator/(double fact) - divide-by-zero error coming",
            command=["OpenSees", str(tcl_file)],
        )

    monkeypatch.setattr(pipeline_mod, "run_opensees", _fake_run_opensees)
    result = run_analysis(cfg, motion, output_dir=tmp_path / "opensees-diverged")
    assert result.status == "error"
    assert "PM4 model diverged" in result.message


def test_run_analysis_opensees_ok_with_warning_diagnostics(tmp_path, monkeypatch) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.opensees.executable = "OpenSees"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    def _fake_run_opensees(executable, tcl_file, cwd, timeout_s, extra_args=None):
        _ = (executable, tcl_file, timeout_s, extra_args)
        t = np.arange(motion.acc.size, dtype=np.float64) * float(motion.dt)
        np.savetxt(Path(cwd) / "surface_acc.out", np.column_stack([t, motion.acc]))
        np.savetxt(
            Path(cwd) / "pwp_ru.out",
            np.column_stack([t, np.zeros_like(t)]),
        )
        return OpenSeesRunOutput(
            returncode=0,
            stdout="OpenSees run complete",
            stderr=(
                "WARNING: CTestNormDispIncr::test() - failed to converge\n"
                "OpenSees > analyze failed, returned: -3 error flag\n"
            ),
            command=["OpenSees", str(tcl_file)],
        )

    monkeypatch.setattr(pipeline_mod, "run_opensees", _fake_run_opensees)
    result = run_analysis(cfg, motion, output_dir=tmp_path / "opensees-warn")
    assert result.status == "ok"
    assert "completed with solver warnings" in result.message
    run_meta = json.loads((result.output_dir / "run_meta.json").read_text(encoding="utf-8"))
    diag = run_meta.get("opensees_diagnostics")
    assert isinstance(diag, dict)
    assert int(diag.get("failed_converge_count", 0)) >= 1
    assert int(diag.get("analyze_failed_count", 0)) >= 1


def test_run_analysis_opensees_uses_adaptive_timeout_budget(tmp_path, monkeypatch) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.analysis.timeout_s = 180
    cfg.opensees.executable = "OpenSees"
    motion = Motion(
        dt=0.01,
        acc=np.zeros(20000, dtype=np.float64),
        unit="m/s2",
        source=Path("synthetic_long_motion.csv"),
    )
    seen_timeout: dict[str, int] = {}

    def _fake_run_opensees(executable, tcl_file, cwd, timeout_s, extra_args=None):
        _ = (executable, extra_args)
        seen_timeout["value"] = int(timeout_s)
        t = np.arange(motion.acc.size, dtype=np.float64) * float(motion.dt)
        np.savetxt(Path(cwd) / "surface_acc.out", np.column_stack([t, motion.acc]))
        np.savetxt(
            Path(cwd) / "pwp_ru.out",
            np.column_stack([t, np.zeros_like(t)]),
        )
        return OpenSeesRunOutput(
            returncode=0,
            stdout="OpenSees run complete",
            stderr="",
            command=["OpenSees", str(tcl_file)],
        )

    monkeypatch.setattr(pipeline_mod, "run_opensees", _fake_run_opensees)
    result = run_analysis(cfg, motion, output_dir=tmp_path / "opensees-timeout-adaptive")
    assert result.status == "ok"
    assert seen_timeout["value"] > 180
    run_meta = json.loads((result.output_dir / "run_meta.json").read_text(encoding="utf-8"))
    assert int(run_meta.get("timeout_s_configured", 0)) == 180
    assert int(run_meta.get("timeout_s_effective", 0)) == seen_timeout["value"]


def test_run_analysis_opensees_timeout_with_outputs_recovers(tmp_path, monkeypatch) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.opensees.executable = "OpenSees"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    def _fake_run_opensees(executable, tcl_file, cwd, timeout_s, extra_args=None):
        _ = (executable, timeout_s, extra_args)
        t = np.arange(motion.acc.size, dtype=np.float64) * float(motion.dt)
        np.savetxt(Path(cwd) / "surface_acc.out", np.column_stack([t, motion.acc]))
        np.savetxt(
            Path(cwd) / "pwp_ru.out",
            np.column_stack([t, np.zeros_like(t)]),
        )
        raise OpenSeesExecutionError(
            "OpenSees timed out after 180s for script model.tcl.",
            command=["OpenSees", str(tcl_file)],
        )

    monkeypatch.setattr(pipeline_mod, "run_opensees", _fake_run_opensees)
    result = run_analysis(cfg, motion, output_dir=tmp_path / "opensees-timeout-recovered")
    assert result.status == "ok"
    assert "output files were recovered" in result.message
    run_meta = json.loads((result.output_dir / "run_meta.json").read_text(encoding="utf-8"))
    recovered = run_meta.get("opensees_timeout_recovered", {})
    assert isinstance(recovered, dict)
    assert recovered.get("recovered") is True


def test_run_id_is_stable_and_config_sensitive(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "mock"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    r1 = run_analysis(cfg, motion, output_dir=tmp_path / "runs")
    r2 = run_analysis(cfg, motion, output_dir=tmp_path / "runs")
    assert r1.run_id == r2.run_id
    with h5py.File(r2.hdf5_path, "r") as h5:
        n_pwp_h5 = int(h5["/pwp/time"].shape[0])
    conn = sqlite3.connect(r2.sqlite_path)
    try:
        n_pwp_sql = conn.execute(
            "SELECT COUNT(*) FROM pwp_effective_stats WHERE run_id = ?",
            (r2.run_id,),
        ).fetchone()[0]
        n_metrics_sql = conn.execute(
            "SELECT COUNT(*) FROM metrics WHERE run_id = ?",
            (r2.run_id,),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n_pwp_sql == n_pwp_h5
    assert n_metrics_sql == 5

    cfg_changed = cfg.model_copy(deep=True)
    cfg_changed.seed = cfg.seed + 1
    r3 = run_analysis(cfg_changed, motion, output_dir=tmp_path / "runs")
    assert r3.run_id != r1.run_id


def test_run_batch_deduplicates_identical_motions(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "mock"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion1 = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    motion2 = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    batch = run_batch(cfg, [motion1, motion2], output_dir=tmp_path / "batch", n_jobs=2)
    assert len(batch.results) == 2
    assert batch.results[0].run_id == batch.results[1].run_id
    assert batch.results[0].status == "ok"
    run_dirs = [p for p in (tmp_path / "batch").iterdir() if p.is_dir()]
    assert len(run_dirs) == 1


def test_run_analysis_mock_mkz_profile(tmp_path: Path) -> None:
    cfg_path = tmp_path / "mkz_mock.yml"
    cfg_path.write_text(
        """
project_name: mkz-mock-run
profile:
  layers:
    - name: crust
      thickness_m: 4.0
      unit_weight_kN_m3: 18.5
      vs_m_s: 190.0
      material: mkz
      material_params:
        gmax: 70000.0
        gamma_ref: 0.001
        damping_min: 0.01
        damping_max: 0.10
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    cfg = load_project_config(cfg_path)
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path / "mkz-out")
    assert result.status == "ok"
    store = load_result(result.output_dir)
    assert store.ru.size > 0
    assert float(store.ru.max()) <= 0.25


def test_run_analysis_eql_persists_hdf5_and_sqlite_summary(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_eql.yml"))
    cfg.analysis.solver_backend = "eql"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path / "eql-out")
    assert result.status == "ok"

    with h5py.File(result.hdf5_path, "r") as h5:
        assert "/eql/iterations" in h5
        assert "/eql/converged" in h5
        assert "/eql/max_change_history" in h5
        assert "/eql/layer_idx" in h5

    conn = sqlite3.connect(result.sqlite_path)
    try:
        eql_summary_rows = conn.execute("SELECT COUNT(*) FROM eql_summary").fetchone()[0]
        eql_layers_rows = conn.execute("SELECT COUNT(*) FROM eql_layers").fetchone()[0]
        eql_metrics_rows = conn.execute(
            "SELECT COUNT(*) FROM metrics WHERE name IN ('eql_iterations', 'eql_converged')"
        ).fetchone()[0]
    finally:
        conn.close()
    assert eql_summary_rows == 1
    assert eql_layers_rows >= 1
    assert eql_metrics_rows == 2


def test_run_analysis_nonlinear_nonfinite_response_raises_clear_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    def _fake_solver(config, motion_obj, **kwargs):
        _ = (config, motion_obj, kwargs)
        t = np.arange(4, dtype=np.float64) * dt
        surface = np.array([0.0, np.nan, 1.0, 2.0], dtype=np.float64)
        return t, surface

    monkeypatch.setattr(pipeline_mod, "solve_nonlinear_sh_response", _fake_solver)
    monkeypatch.setattr(pipeline_mod, "solve_nonlinear_implicit_newmark", _fake_solver)

    try:
        run_analysis(cfg, motion, output_dir=tmp_path / "nonfinite-out")
    except ValueError as exc:
        assert "Nonlinear solver produced non-finite surface acceleration" in str(exc)
    else:
        raise AssertionError("Expected run_analysis to raise a clear non-finite solver error.")


def test_run_analysis_nonlinear_forwards_configured_substeps(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.analysis.nonlinear_substeps = 12
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    seen: dict[str, int] = {}

    def _fake_solver(config, motion_obj, **kwargs):
        _ = (motion_obj,)
        # New implicit solver reads substeps from config directly,
        # old Euler solver receives it as kwarg.
        seen["substeps"] = int(
            kwargs.get("substeps", config.analysis.nonlinear_substeps)
        )
        t = np.arange(motion.acc.size, dtype=np.float64) * dt
        return t, 0.5 * motion.acc

    monkeypatch.setattr(pipeline_mod, "solve_nonlinear_sh_response", _fake_solver)
    monkeypatch.setattr(pipeline_mod, "solve_nonlinear_implicit_newmark", _fake_solver)

    result = run_analysis(cfg, motion, output_dir=tmp_path / "nonlinear-substeps")
    assert result.status == "ok"
    assert seen["substeps"] == 12
    run_meta = json.loads((result.output_dir / "run_meta.json").read_text(encoding="utf-8"))
    assert int(run_meta.get("nonlinear_substeps", 0)) == 12
