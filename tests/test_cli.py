import json
from pathlib import Path

import dsra1d.benchmark as benchmark_mod
from dsra1d.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_validate() -> None:
    cfg = Path("examples/configs/effective_stress.yml")
    result = runner.invoke(app, ["validate", "--config", str(cfg)])
    assert result.exit_code == 0


def test_cli_init(tmp_path: Path) -> None:
    out = tmp_path / "template.yml"
    result = runner.invoke(app, ["init", "--template", "effective-stress", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_cli_init_mkz_gqh_template(tmp_path: Path) -> None:
    out = tmp_path / "mkz_gqh.yml"
    result = runner.invoke(app, ["init", "--template", "mkz-gqh-mock", "--out", str(out)])
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "material: mkz" in content
    assert "material: gqh" in content


def test_cli_init_effective_stress_strict_plus_template(tmp_path: Path) -> None:
    out = tmp_path / "effective_stress_strict_plus.yml"
    result = runner.invoke(
        app,
        [
            "init",
            "--template",
            "effective-stress-strict-plus",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "pm4_validation_profile: strict_plus" in content
    assert "boundary_condition: elastic_halfspace" in content


def test_cli_init_invalid_template_fails(tmp_path: Path) -> None:
    out = tmp_path / "bad.yml"
    result = runner.invoke(app, ["init", "--template", "does-not-exist", "--out", str(out)])
    assert result.exit_code != 0


def test_cli_dt_check(tmp_path: Path) -> None:
    cfg = Path("examples/configs/effective_stress.yml")
    motion = Path("examples/motions/sample_motion.csv")
    result = runner.invoke(
        app,
        [
            "dt-check",
            "--config",
            str(cfg),
            "--motion",
            str(motion),
            "--out",
            str(tmp_path / "dt_check"),
            "--threshold",
            "5.0",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "dt_check" / "dt_check_summary.json").exists()


def test_cli_validate_check_backend_missing_executable(tmp_path: Path) -> None:
    cfg = tmp_path / "missing_opensees.yml"
    cfg.write_text(
        """
project_name: missing-opensees
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
analysis:
  solver_backend: opensees
opensees:
  executable: OpenSees_DOES_NOT_EXIST
""".strip(),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "validate",
            "--config",
            str(cfg),
            "--check-backend",
        ],
    )
    assert result.exit_code == 5


def test_cli_render_tcl_writes_artifacts(tmp_path: Path) -> None:
    cfg = Path("examples/configs/effective_stress.yml")
    motion = Path("examples/motions/sample_motion.csv")
    out_dir = tmp_path / "tcl_out"
    result = runner.invoke(
        app,
        [
            "render-tcl",
            "--config",
            str(cfg),
            "--motion",
            str(motion),
            "--out",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    tcl_path = out_dir / "model.tcl"
    motion_path = out_dir / "motion_processed.csv"
    assert tcl_path.exists()
    assert motion_path.exists()
    tcl = tcl_path.read_text(encoding="utf-8")
    assert "model BasicBuilder -ndm 2 -ndf 3" in tcl
    assert "element quadUP" in tcl


def test_cli_benchmark_require_runs_strict_fails(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "core-es",
            "--out",
            str(tmp_path / "bench"),
            "--require-runs",
            "99",
        ],
    )
    assert result.exit_code == 7


def test_cli_benchmark_fail_on_skip_fails_when_backend_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", lambda _: None)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "opensees-parity",
            "--out",
            str(tmp_path / "bench"),
            "--fail-on-skip",
        ],
    )
    assert result.exit_code == 7


def test_cli_benchmark_require_opensees_fails_when_backend_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", lambda _: None)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "opensees-parity",
            "--out",
            str(tmp_path / "bench"),
            "--require-opensees",
        ],
    )
    assert result.exit_code == 10


def test_cli_benchmark_min_execution_coverage_fails_when_no_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", lambda _: None)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "opensees-parity",
            "--out",
            str(tmp_path / "bench"),
            "--min-execution-coverage",
            "0.5",
        ],
    )
    assert result.exit_code == 11


def test_cli_benchmark_min_execution_coverage_invalid_value_fails(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "core-es",
            "--out",
            str(tmp_path / "bench"),
            "--min-execution-coverage",
            "1.5",
        ],
    )
    assert result.exit_code != 0


def test_cli_benchmark_opensees_executable_option_overrides_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seen: list[str] = []

    def fake_resolve(executable: str):
        seen.append(executable)
        return None

    monkeypatch.setenv("DSRA1D_OPENSEES_EXE_OVERRIDE", "FROM_ENV")
    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", fake_resolve)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "opensees-parity",
            "--out",
            str(tmp_path / "bench"),
            "--opensees-executable",
            "FROM_OPTION",
        ],
    )
    assert result.exit_code == 0
    assert "Benchmark coverage:" in result.stdout
    assert seen
    assert all(val == "FROM_OPTION" for val in seen)


def test_cli_verify_passes_for_run(tmp_path: Path) -> None:
    cfg = Path("examples/configs/effective_stress.yml")
    motion = Path("examples/motions/sample_motion.csv")
    run_result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg),
            "--motion",
            str(motion),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert run_result.exit_code == 0

    run_dirs = [p for p in (tmp_path / "out").iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
    result = runner.invoke(
        app,
        [
            "verify",
            "--in",
            str(run_dirs[0]),
        ],
    )
    assert result.exit_code == 0
    assert (run_dirs[0] / "verify_report.json").exists()


def test_cli_verify_batch_passes(tmp_path: Path) -> None:
    cfg = Path("examples/configs/effective_stress.yml")
    motion = Path("examples/motions/sample_motion.csv")
    run_result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg),
            "--motion",
            str(motion),
            "--out",
            str(tmp_path / "out"),
        ],
    )
    assert run_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "verify-batch",
            "--in",
            str(tmp_path / "out"),
            "--require-runs",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "out" / "verify_batch_report.json").exists()


def test_cli_verify_batch_missing_path_fails(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "verify-batch",
            "--in",
            str(tmp_path / "does_not_exist"),
            "--require-runs",
            "1",
        ],
    )
    assert result.exit_code == 9


def test_cli_summarize_writes_outputs(tmp_path: Path) -> None:
    benchmark_report = {
        "suite": "opensees-parity",
        "all_passed": True,
        "skipped": 1,
        "ran": 2,
        "cases": [
            {"name": "case01", "status": "ok", "passed": True},
            {
                "name": "case02",
                "status": "skipped",
                "reason": "OpenSees executable not found: OpenSees",
                "passed": True,
            },
        ],
    }
    verify_batch_report = {
        "ok": True,
        "total_runs": 1,
        "passed_runs": 1,
        "failed_runs": 0,
        "reports": {"run-1": {"ok": True, "checks": {}}},
    }
    bench_path = tmp_path / "benchmark.json"
    verify_path = tmp_path / "verify_batch_report.json"
    bench_path.write_text(json.dumps(benchmark_report), encoding="utf-8")
    verify_path.write_text(json.dumps(verify_batch_report), encoding="utf-8")

    out_dir = tmp_path / "summary"
    result = runner.invoke(
        app,
        [
            "summarize",
            "--benchmark-report",
            str(bench_path),
            "--verify-batch-report",
            str(verify_path),
            "--out",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    summary_json = out_dir / "campaign_summary.json"
    summary_md = out_dir / "campaign_summary.md"
    assert summary_json.exists()
    assert summary_md.exists()


def test_cli_campaign_core_es_writes_all_reports(tmp_path: Path) -> None:
    out_dir = tmp_path / "campaign"
    result = runner.invoke(
        app,
        [
            "campaign",
            "--suite",
            "core-es",
            "--out",
            str(out_dir),
            "--require-runs",
            "3",
            "--verify-require-runs",
            "3",
        ],
    )
    assert result.exit_code == 0
    assert "Benchmark coverage:" in result.stdout
    assert (out_dir / "benchmark_core-es.json").exists()
    assert (out_dir / "verify_batch_report.json").exists()
    assert (out_dir / "campaign_summary.json").exists()
    assert (out_dir / "campaign_summary.md").exists()


def test_cli_campaign_core_hyst_writes_all_reports(tmp_path: Path) -> None:
    out_dir = tmp_path / "campaign_hyst"
    result = runner.invoke(
        app,
        [
            "campaign",
            "--suite",
            "core-hyst",
            "--out",
            str(out_dir),
            "--require-runs",
            "3",
            "--verify-require-runs",
            "3",
        ],
    )
    assert result.exit_code == 0
    assert (out_dir / "benchmark_core-hyst.json").exists()
    assert (out_dir / "verify_batch_report.json").exists()
    assert (out_dir / "campaign_summary.json").exists()
    assert (out_dir / "campaign_summary.md").exists()


def test_cli_campaign_require_opensees_fails_when_backend_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", lambda _: None)
    out_dir = tmp_path / "campaign_parity"
    result = runner.invoke(
        app,
        [
            "campaign",
            "--suite",
            "opensees-parity",
            "--out",
            str(out_dir),
            "--require-opensees",
            "--verify-require-runs",
            "1",
        ],
    )
    assert result.exit_code == 10


def test_cli_campaign_min_execution_coverage_fails_when_no_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", lambda _: None)
    out_dir = tmp_path / "campaign_parity_cov"
    result = runner.invoke(
        app,
        [
            "campaign",
            "--suite",
            "opensees-parity",
            "--out",
            str(out_dir),
            "--min-execution-coverage",
            "0.5",
            "--verify-require-runs",
            "1",
        ],
    )
    assert result.exit_code == 11
