from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

import dsra1d.cli.main as cli_main
from dsra1d.cli.main import app

runner = CliRunner()


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


def test_cli_init_core_default_template(tmp_path: Path) -> None:
    out = tmp_path / "template.yml"
    result = runner.invoke(app, ["init", "--out", str(out)])
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "solver_backend: nonlinear" in content
    assert "material: mkz" in content
    assert "material: gqh" in content


def test_cli_init_linear_template(tmp_path: Path) -> None:
    out = tmp_path / "linear.yml"
    result = runner.invoke(app, ["init", "--template", "linear-3layer-sand", "--out", str(out)])
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "solver_backend: linear" in content
    assert "material: elastic" in content


def test_cli_init_invalid_template_fails(tmp_path: Path) -> None:
    out = tmp_path / "bad.yml"
    result = runner.invoke(app, ["init", "--template", "does-not-exist", "--out", str(out)])
    assert result.exit_code != 0


def test_cli_validate_core_config() -> None:
    cfg = Path("examples/native/deepsoil_gqh_5layer_baseline.yml")
    result = runner.invoke(app, ["validate", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "Valid config" in result.stdout
    assert "nonlinear" in result.stdout


def test_cli_run_linear_smoke(tmp_path: Path) -> None:
    cfg = Path("examples/native/linear_3layer_sand.yml")
    motion = Path("examples/motions/sample_motion.csv")
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg),
            "--motion",
            str(motion),
            "--out",
            str(tmp_path / "run_out"),
            "--backend",
            "linear",
        ],
    )
    assert result.exit_code == 0
    assert "Completed" in result.stdout


def test_cli_quickstart_core_template(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "quickstart",
            "--out",
            str(tmp_path / "quickstart"),
            "--template",
            "mkz-gqh-eql",
            "--backend",
            "eql",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "quickstart" / "config.yml").exists()
    assert (tmp_path / "quickstart" / "quickstart_summary.json").exists()


def test_cli_batch_linear_smoke(tmp_path: Path) -> None:
    motions_dir = tmp_path / "motions"
    motions_dir.mkdir()
    source = Path("examples/motions/sample_motion.csv").read_text(encoding="utf-8")
    (motions_dir / "motion_01.csv").write_text(source, encoding="utf-8")
    (motions_dir / "motion_02.csv").write_text(source, encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "batch",
            "--config",
            "examples/native/linear_3layer_sand.yml",
            "--motions-dir",
            str(motions_dir),
            "--out",
            str(tmp_path / "batch_out"),
            "--backend",
            "linear",
            "--n-jobs",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert "runs completed" in result.stdout
