from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "run_release_deepsoil_compare.py"
    )
    spec = importlib.util.spec_from_file_location("run_release_deepsoil_compare", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_release_deepsoil_compare_skips_when_manifest_missing_and_not_required(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()
    campaign_dir = tmp_path / "campaign"
    policy_path = tmp_path / "release_signoff.yml"
    policy_path.write_text(
        "\n".join(
            [
                "require_deepsoil_compare: false",
                "require_deepsoil_profile: false",
                "require_deepsoil_hysteresis: false",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "missing_manifest.json"

    code = module.main(
        [
            "--campaign-dir",
            str(campaign_dir),
            "--policy",
            str(policy_path),
            "--manifest",
            str(manifest_path),
        ]
    )

    assert code == 0
    assert "not configured; skipping" in capsys.readouterr().out


def test_run_release_deepsoil_compare_fails_when_manifest_missing_and_required(
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    campaign_dir = tmp_path / "campaign"
    policy_path = tmp_path / "release_signoff.yml"
    policy_path.write_text(
        "\n".join(
            [
                "require_deepsoil_compare: true",
                "require_deepsoil_profile: false",
                "require_deepsoil_hysteresis: false",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "missing_manifest.json"

    try:
        module.main(
            [
                "--campaign-dir",
                str(campaign_dir),
                "--policy",
                str(policy_path),
                "--manifest",
                str(manifest_path),
            ]
        )
    except SystemExit as exc:
        assert "required by policy but not found" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected SystemExit for missing required manifest.")


def test_run_release_deepsoil_compare_runs_batch_when_manifest_exists(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    campaign_dir = tmp_path / "campaign"
    policy_path = tmp_path / "release_signoff.yml"
    policy_path.write_text("require_deepsoil_compare: false\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"cases": []}', encoding="utf-8")

    @dataclass
    class _Artifacts:
        json_path: Path
        markdown_path: Path

    @dataclass
    class _Result:
        total_cases: int
        passed_cases: int
        failed_cases: int
        artifacts: _Artifacts

    called: dict[str, Path] = {}

    def _fake_compare(manifest_path_arg: Path, *, out_dir: Path):
        called["manifest"] = Path(manifest_path_arg)
        called["out"] = Path(out_dir)
        return _Result(
            total_cases=2,
            passed_cases=2,
            failed_cases=0,
            artifacts=_Artifacts(
                json_path=Path(out_dir) / "deepsoil_compare_batch.json",
                markdown_path=Path(out_dir) / "deepsoil_compare_batch.md",
            ),
        )

    monkeypatch.setattr(module, "compare_deepsoil_manifest", _fake_compare)

    code = module.main(
        [
            "--campaign-dir",
            str(campaign_dir),
            "--policy",
            str(policy_path),
            "--manifest",
            str(manifest_path),
        ]
    )

    assert code == 0
    assert called["manifest"] == manifest_path
    assert called["out"] == campaign_dir
    out = capsys.readouterr().out
    assert "DEEPSOIL release compare completed." in out
    assert "Cases: 2" in out
