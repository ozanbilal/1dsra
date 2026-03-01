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
