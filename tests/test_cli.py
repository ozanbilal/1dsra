import json
from pathlib import Path

import dsra1d.benchmark as benchmark_mod
import dsra1d.cli.main as cli_main
import pytest
import typer
from dsra1d.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_validate() -> None:
    cfg = Path("examples/configs/effective_stress.yml")
    result = runner.invoke(app, ["validate", "--config", str(cfg)])
    assert result.exit_code == 0


def test_cli_resolve_web_port_prefers_requested(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_can_bind_tcp", lambda host, port: True)
    port, shifted = cli_main._resolve_web_port("127.0.0.1", 8010, scan_limit=5)
    assert port == 8010
    assert shifted is False


def test_cli_resolve_web_port_scans_next_available(monkeypatch) -> None:
    blocked = {8010, 8011}
    monkeypatch.setattr(cli_main, "_can_bind_tcp", lambda host, port: port not in blocked)
    port, shifted = cli_main._resolve_web_port("127.0.0.1", 8010, scan_limit=5)
    assert port == 8012
    assert shifted is True


def test_cli_resolve_web_port_fails_when_no_ports(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_can_bind_tcp", lambda host, port: False)
    with pytest.raises(typer.Exit) as exc:
        cli_main._resolve_web_port("127.0.0.1", 8010, scan_limit=1)
    assert exc.value.exit_code == 6


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


def test_cli_init_mkz_gqh_eql_template(tmp_path: Path) -> None:
    out = tmp_path / "mkz_gqh_eql.yml"
    result = runner.invoke(app, ["init", "--template", "mkz-gqh-eql", "--out", str(out)])
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "solver_backend: eql" in content


def test_cli_init_mkz_gqh_nonlinear_template(tmp_path: Path) -> None:
    out = tmp_path / "mkz_gqh_nonlinear.yml"
    result = runner.invoke(
        app,
        ["init", "--template", "mkz-gqh-nonlinear", "--out", str(out)],
    )
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "solver_backend: nonlinear" in content


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


def test_cli_init_pm4sand_calibration_template(tmp_path: Path) -> None:
    out = tmp_path / "pm4sand_calibration.yml"
    result = runner.invoke(
        app,
        [
            "init",
            "--template",
            "pm4sand-calibration",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "project_name: pm4sand-calibration-template" in content
    assert "material: pm4sand" in content
    assert "pm4_validation_profile: strict_plus" in content


def test_cli_init_pm4silt_calibration_template(tmp_path: Path) -> None:
    out = tmp_path / "pm4silt_calibration.yml"
    result = runner.invoke(
        app,
        [
            "init",
            "--template",
            "pm4silt-calibration",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "project_name: pm4silt-calibration-template" in content
    assert "material: pm4silt" in content
    assert "pm4_validation_profile: strict_plus" in content


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
            "--backend",
            "auto",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "dt_check" / "dt_check_summary.json").exists()


def test_cli_validate_check_backend_missing_executable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DSRA1D_OPENSEES_EXE_OVERRIDE", raising=False)
    monkeypatch.delenv("DSRA1D_OPENSEES_EXTRA_ARGS_OVERRIDE", raising=False)
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


def test_cli_validate_check_backend_prints_probe_info(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "opensees_probe.yml"
    cfg.write_text(
        """
project_name: probe-opensees
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
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )

    class _Probe:
        available = True
        resolved = Path("C:/OpenSees/OpenSees.exe")
        version = "OpenSees 3.x"
        binary_sha256 = "a" * 64

    monkeypatch.setattr(
        cli_main,
        "probe_opensees_executable",
        lambda *args, **kwargs: _Probe(),
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
    assert result.exit_code == 0
    assert "OpenSees executable" in result.stdout
    assert "OpenSees version probe" in result.stdout


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
    report = json.loads(
        (tmp_path / "bench" / "benchmark_opensees-parity.json").read_text(
            encoding="utf-8"
        )
    )
    policy = report["policy"]
    assert isinstance(policy, dict)
    assert policy["require_opensees"] is False
    assert float(policy["min_execution_coverage"]) == 0.0


def test_cli_benchmark_require_explicit_checks_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_run_suite(
        *,
        suite: str,
        output_dir: Path,
        require_backend_version_regex: str | None = None,
        require_backend_sha256: str | None = None,
    ):
        _ = suite
        _ = require_backend_version_regex
        _ = require_backend_sha256
        output_dir.mkdir(parents=True, exist_ok=True)
        return {
            "suite": "opensees-parity",
            "cases": [
                {
                    "name": "parity01",
                    "status": "ok",
                    "passed": True,
                    "checks_explicit": False,
                }
            ],
            "all_passed": True,
            "skipped": 0,
            "ran": 1,
            "total_cases": 1,
            "skipped_backend": 0,
            "backend_ready": True,
            "execution_coverage": 1.0,
            "backend_missing_cases": [],
        }

    monkeypatch.setattr(cli_main, "run_benchmark_suite", fake_run_suite)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "opensees-parity",
            "--out",
            str(tmp_path / "bench"),
            "--require-explicit-checks",
        ],
    )
    assert result.exit_code == 12


def test_cli_validate_check_backend_fingerprint_requirement_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = tmp_path / "opensees_probe_req.yml"
    cfg.write_text(
        """
project_name: probe-opensees-req
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
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )

    class _Probe:
        available = True
        resolved = Path("C:/OpenSees/OpenSees.exe")
        version = "OpenSees 3.7.0"
        binary_sha256 = "a" * 64
        command = ()
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        cli_main,
        "probe_opensees_executable",
        lambda *args, **kwargs: _Probe(),
    )
    result = runner.invoke(
        app,
        [
            "validate",
            "--config",
            str(cfg),
            "--check-backend",
            "--require-backend-version-regex",
            r"OpenSees\s+3\.8",
        ],
    )
    assert result.exit_code == 5


def test_cli_lock_golden_writes_expected_schema(tmp_path: Path) -> None:
    report = {
        "suite": "opensees-parity",
        "all_passed": True,
        "skipped": 0,
        "cases": [
            {
                "name": "parity01",
                "status": "ok",
                "actual": {
                    "pga": 0.12,
                    "ru_max": 0.42,
                    "delta_u_max": 11.5,
                    "sigma_v_eff_min": 35.0,
                },
                "expected": {
                    "constraints": {"ru_min": 0.0, "ru_max": 1.0},
                    "deterministic": True,
                    "dt_sensitivity": {"threshold": 3.0},
                },
            }
        ],
    }
    report_path = tmp_path / "benchmark_opensees-parity.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    golden_path = tmp_path / "golden_metrics.json"
    result = runner.invoke(
        app,
        [
            "lock-golden",
            "--benchmark-report",
            str(report_path),
            "--golden-out",
            str(golden_path),
            "--metrics",
            "pga,ru_max",
            "--rel-tol",
            "0.1",
            "--abs-tol-min",
            "1e-6",
        ],
    )
    assert result.exit_code == 0
    assert golden_path.exists()
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert "parity01" in golden
    case = golden["parity01"]
    assert isinstance(case, dict)
    checks = case["checks"]
    assert isinstance(checks, dict)
    assert "pga" in checks
    assert "ru_max" in checks
    assert abs(float(checks["pga"]["expected"]) - 0.12) < 1.0e-12
    assert abs(float(checks["ru_max"]["expected"]) - 0.42) < 1.0e-12


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
            "--backend",
            "auto",
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


def test_cli_run_auto_fallback_to_mock_when_opensees_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = tmp_path / "opensees_missing.yml"
    cfg.write_text(
        """
project_name: auto-fallback
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
motion:
  units: m/s2
opensees:
  executable: OpenSees_DOES_NOT_EXIST
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_main, "resolve_opensees_executable", lambda _: None)
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg),
            "--motion",
            "examples/motions/sample_motion.csv",
            "--out",
            str(tmp_path / "out"),
            "--backend",
            "auto",
        ],
    )
    assert result.exit_code == 0
    assert "auto-fallback" in result.stdout


def test_cli_run_config_mode_fails_when_opensees_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = tmp_path / "opensees_missing_config.yml"
    cfg.write_text(
        """
project_name: config-missing
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
motion:
  units: m/s2
opensees:
  executable: OpenSees_DOES_NOT_EXIST
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_main, "resolve_opensees_executable", lambda _: None)
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg),
            "--motion",
            "examples/motions/sample_motion.csv",
            "--out",
            str(tmp_path / "out"),
            "--backend",
            "config",
        ],
    )
    assert result.exit_code == 5
    assert "--backend auto" in result.stdout


def test_cli_run_linear_backend_forced(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            "examples/configs/effective_stress.yml",
            "--motion",
            "examples/motions/sample_motion.csv",
            "--out",
            str(tmp_path / "out"),
            "--backend",
            "linear",
        ],
    )
    assert result.exit_code == 0
    assert "linear (forced)" in result.stdout


def test_cli_run_eql_backend_forced(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            "examples/configs/mkz_gqh_mock.yml",
            "--motion",
            "examples/motions/sample_motion.csv",
            "--out",
            str(tmp_path / "out"),
            "--backend",
            "eql",
        ],
    )
    assert result.exit_code == 0
    assert "eql (forced)" in result.stdout


def test_cli_run_nonlinear_backend_forced(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            "examples/configs/mkz_gqh_mock.yml",
            "--motion",
            "examples/motions/sample_motion.csv",
            "--out",
            str(tmp_path / "out"),
            "--backend",
            "nonlinear",
        ],
    )
    assert result.exit_code == 0
    assert "nonlinear (forced)" in result.stdout


def test_cli_quickstart_auto_runs_and_writes_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(cli_main, "resolve_opensees_executable", lambda _: None)
    out_dir = tmp_path / "quickstart"
    result = runner.invoke(
        app,
        [
            "quickstart",
            "--out",
            str(out_dir),
            "--template",
            "effective-stress-strict-plus",
            "--backend",
            "auto",
        ],
    )
    assert result.exit_code == 0
    summary_path = out_dir / "quickstart_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["run_status"] == "ok"
    assert summary["verify_ok"] is True
    assert summary["backend"] == "mock"


def test_cli_quickstart_config_fails_when_opensees_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(cli_main, "resolve_opensees_executable", lambda _: None)
    out_dir = tmp_path / "quickstart_cfg"
    result = runner.invoke(
        app,
        [
            "quickstart",
            "--out",
            str(out_dir),
            "--template",
            "effective-stress-strict-plus",
            "--backend",
            "config",
        ],
    )
    assert result.exit_code == 5


def test_cli_quickstart_mkz_gqh_eql_runs(tmp_path: Path) -> None:
    out_dir = tmp_path / "quickstart_mkz_eql"
    result = runner.invoke(
        app,
        [
            "quickstart",
            "--out",
            str(out_dir),
            "--template",
            "mkz-gqh-eql",
            "--backend",
            "eql",
        ],
    )
    assert result.exit_code == 0
    summary_path = out_dir / "quickstart_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["run_status"] == "ok"
    assert summary["verify_ok"] is True
    assert summary["backend"] == "eql"


def test_cli_quickstart_mkz_gqh_nonlinear_runs(tmp_path: Path) -> None:
    out_dir = tmp_path / "quickstart_mkz_nl"
    result = runner.invoke(
        app,
        [
            "quickstart",
            "--out",
            str(out_dir),
            "--template",
            "mkz-gqh-nonlinear",
            "--backend",
            "nonlinear",
        ],
    )
    assert result.exit_code == 0
    summary_path = out_dir / "quickstart_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["run_status"] == "ok"
    assert summary["verify_ok"] is True
    assert summary["backend"] == "nonlinear"


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
            "--backend",
            "auto",
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


def test_cli_summarize_strict_signoff_passes_with_input_dir(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "campaign_release"
    campaign_dir.mkdir(parents=True, exist_ok=True)
    policy_sha = str(
        cli_main._load_release_signoff_policy().get("opensees_fingerprint", "")
    ).strip()
    benchmark_report = {
        "suite": "release-signoff",
        "all_passed": True,
        "skipped": 0,
        "ran": 18,
        "total_cases": 18,
        "skipped_backend": 0,
        "backend_ready": True,
        "backend_fingerprint_ok": True,
        "execution_coverage": 1.0,
        "policy": {
            "fail_on_skip": True,
            "require_runs": 18,
            "require_opensees": True,
            "min_execution_coverage": 1.0,
            "require_backend_sha256": policy_sha,
        },
        "backend_probe": {"binary_sha256": policy_sha},
        "cases": [],
    }
    verify_batch_report = {
        "ok": True,
        "total_runs": 18,
        "passed_runs": 18,
        "failed_runs": 0,
        "policy": {
            "require_runs": 18,
            "conditions": {"verify_ok": True, "no_failed_runs": True, "require_runs_ok": True},
            "passed": True,
        },
        "reports": {},
    }
    (campaign_dir / "benchmark_release-signoff.json").write_text(
        json.dumps(benchmark_report, indent=2),
        encoding="utf-8",
    )
    (campaign_dir / "verify_batch_report.json").write_text(
        json.dumps(verify_batch_report, indent=2),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "summarize",
            "--input",
            str(campaign_dir),
            "--strict-signoff",
        ],
    )
    assert result.exit_code == 0
    summary_json = campaign_dir / "campaign_summary.json"
    assert summary_json.exists()
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    signoff = summary.get("signoff")
    assert isinstance(signoff, dict)
    assert signoff.get("passed") is True


def test_cli_summarize_strict_signoff_fails_when_campaign_not_release_signoff(
    tmp_path: Path,
) -> None:
    campaign_dir = tmp_path / "campaign_bad"
    campaign_dir.mkdir(parents=True, exist_ok=True)
    benchmark_report = {
        "suite": "core-es",
        "all_passed": True,
        "skipped": 0,
        "ran": 3,
        "total_cases": 3,
        "execution_coverage": 1.0,
        "backend_fingerprint_ok": True,
        "policy": {
            "fail_on_skip": False,
            "require_runs": 3,
            "require_opensees": False,
            "min_execution_coverage": 0.0,
        },
        "cases": [],
    }
    verify_batch_report = {
        "ok": True,
        "total_runs": 3,
        "passed_runs": 3,
        "failed_runs": 0,
        "policy": {
            "require_runs": 3,
            "conditions": {"verify_ok": True, "no_failed_runs": True, "require_runs_ok": True},
            "passed": True,
        },
        "reports": {},
    }
    (campaign_dir / "benchmark_core-es.json").write_text(
        json.dumps(benchmark_report, indent=2),
        encoding="utf-8",
    )
    (campaign_dir / "verify_batch_report.json").write_text(
        json.dumps(verify_batch_report, indent=2),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "summarize",
            "--input",
            str(campaign_dir),
            "--strict-signoff",
        ],
    )
    assert result.exit_code == 13


def test_cli_summarize_strict_signoff_fails_when_backend_probe_assumed(
    tmp_path: Path,
) -> None:
    campaign_dir = tmp_path / "campaign_assumed_probe"
    campaign_dir.mkdir(parents=True, exist_ok=True)
    policy_sha = str(
        cli_main._load_release_signoff_policy().get("opensees_fingerprint", "")
    ).strip()
    benchmark_report = {
        "suite": "release-signoff",
        "all_passed": True,
        "skipped": 0,
        "ran": 18,
        "total_cases": 18,
        "skipped_backend": 0,
        "backend_ready": True,
        "backend_fingerprint_ok": True,
        "execution_coverage": 1.0,
        "policy": {
            "fail_on_skip": True,
            "require_runs": 18,
            "require_opensees": True,
            "min_execution_coverage": 1.0,
            "require_backend_sha256": policy_sha,
        },
        "backend_probe": {"binary_sha256": policy_sha, "assumed_available": True},
        "cases": [],
    }
    verify_batch_report = {
        "ok": True,
        "total_runs": 18,
        "passed_runs": 18,
        "failed_runs": 0,
        "policy": {
            "require_runs": 18,
            "conditions": {"verify_ok": True, "no_failed_runs": True, "require_runs_ok": True},
            "passed": True,
        },
        "reports": {},
    }
    (campaign_dir / "benchmark_release-signoff.json").write_text(
        json.dumps(benchmark_report, indent=2),
        encoding="utf-8",
    )
    (campaign_dir / "verify_batch_report.json").write_text(
        json.dumps(verify_batch_report, indent=2),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "summarize",
            "--input",
            str(campaign_dir),
            "--strict-signoff",
        ],
    )
    assert result.exit_code == 13
    summary = json.loads((campaign_dir / "campaign_summary.json").read_text(encoding="utf-8"))
    signoff = summary.get("signoff", {})
    assert signoff.get("passed") is False
    conditions = signoff.get("conditions", {})
    assert conditions.get("backend_probe_not_assumed") is False


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
    benchmark_report = json.loads((out_dir / "benchmark_core-es.json").read_text(encoding="utf-8"))
    verify_report = json.loads((out_dir / "verify_batch_report.json").read_text(encoding="utf-8"))
    summary_report = json.loads((out_dir / "campaign_summary.json").read_text(encoding="utf-8"))
    assert isinstance(benchmark_report["policy"], dict)
    assert isinstance(verify_report["policy"], dict)
    assert isinstance(summary_report["policy"], dict)
    verify_policy = verify_report["policy"]
    assert isinstance(verify_policy.get("conditions"), dict)


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


def test_cli_campaign_core_eql_writes_all_reports(tmp_path: Path) -> None:
    out_dir = tmp_path / "campaign_eql"
    result = runner.invoke(
        app,
        [
            "campaign",
            "--suite",
            "core-eql",
            "--out",
            str(out_dir),
            "--require-runs",
            "3",
            "--verify-require-runs",
            "3",
        ],
    )
    assert result.exit_code == 0
    assert (out_dir / "benchmark_core-eql.json").exists()
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
    benchmark_path = out_dir / "benchmark_opensees-parity.json"
    assert benchmark_path.exists()
    benchmark_report = json.loads(benchmark_path.read_text(encoding="utf-8"))
    policy = benchmark_report["policy"]
    assert isinstance(policy, dict)
    assert policy["require_opensees"] is True


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
    benchmark_path = out_dir / "benchmark_opensees-parity.json"
    assert benchmark_path.exists()
