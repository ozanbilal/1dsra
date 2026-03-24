from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "scaffold_deepsoil_compare_manifest.py"
    )
    spec = importlib.util.spec_from_file_location(
        "scaffold_deepsoil_compare_manifest",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_run(
    root: Path,
    parent_name: str,
    run_name: str,
    *,
    status: str = "ok",
    backend: str = "nonlinear",
    with_results: bool = True,
) -> Path:
    run_dir = root / parent_name / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "status": status,
                "solver_backend": backend,
            }
        ),
        encoding="utf-8",
    )
    if with_results:
        (run_dir / "results.h5").write_text("", encoding="utf-8")
    return run_dir


def test_scaffold_manifest_filters_incomplete_runs_and_relativizes_paths(
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    runs_root = tmp_path / "runs"
    manifest_path = tmp_path / "manifests" / "deepsoil_manifest.json"
    reference_root = tmp_path / "references" / "deepsoil"

    complete_run = _write_run(
        runs_root,
        "mkz_suite",
        "run-001",
        status="ok",
        backend="nonlinear",
        with_results=True,
    )
    _write_run(
        runs_root,
        "mkz_suite",
        "run-002",
        status="failed",
        backend="nonlinear",
        with_results=False,
    )

    payload = module.scaffold_manifest(
        runs_root=runs_root,
        out_path=manifest_path,
        deepsoil_reference_root=reference_root,
        include_profile=True,
        include_hysteresis=True,
        include_incomplete=False,
    )

    assert len(payload["cases"]) == 1
    case = payload["cases"][0]
    assert case["name"] == "mkz-suite-nonlinear"
    assert case["run"] == "../runs/mkz_suite/run-001"
    assert case["surface_csv"] == "../references/deepsoil/mkz-suite-nonlinear/surface.csv"
    assert case["psa_csv"] == "../references/deepsoil/mkz-suite-nonlinear/psa.csv"
    assert case["profile_csv"] == "../references/deepsoil/mkz-suite-nonlinear/profile.csv"
    assert (
        case["hysteresis_csv"]
        == "../references/deepsoil/mkz-suite-nonlinear/hysteresis_layer1.csv"
    )
    assert case["hysteresis_layer"] == 0
    assert manifest_path.exists()
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["cases"][0]["run"] == case["run"]
    assert complete_run.exists()


def test_scaffold_manifest_generates_unique_case_names_and_optional_fields(
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    runs_root = tmp_path / "runs"
    manifest_path = tmp_path / "deepsoil_manifest.json"
    reference_root = tmp_path / "refs"

    _write_run(runs_root, "suite", "run-001", backend="eql")
    _write_run(runs_root, "suite", "run-002", backend="eql")

    payload = module.scaffold_manifest(
        runs_root=runs_root,
        out_path=manifest_path,
        deepsoil_reference_root=reference_root,
        include_profile=False,
        include_hysteresis=False,
        include_incomplete=True,
    )

    names = [case["name"] for case in payload["cases"]]
    assert names == ["suite-eql", "suite-eql-2"]
    assert "profile_csv" not in payload["cases"][0]
    assert "hysteresis_csv" not in payload["cases"][0]


def test_main_writes_manifest_and_reports_case_count(tmp_path: Path, capsys) -> None:
    module = _load_script_module()
    runs_root = tmp_path / "runs"
    manifest_path = tmp_path / "output" / "generated.json"
    reference_root = tmp_path / "refs"

    _write_run(runs_root, "linear_suite", "run-001", backend="linear")

    code = module.main(
        [
            "--runs-root",
            str(runs_root),
            "--out",
            str(manifest_path),
            "--deepsoil-reference-root",
            str(reference_root),
            "--no-profile",
            "--no-hysteresis",
        ]
    )

    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["manifest_path"] == str(manifest_path.resolve())
    assert result["case_count"] == 1
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["cases"][0]["name"] == "linear-suite-linear"
    assert "profile_csv" not in payload["cases"][0]
