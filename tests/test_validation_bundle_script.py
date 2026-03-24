# ruff: noqa
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_build_validation_bundle_script(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "scripts").mkdir(parents=True)
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "examples" / "output" / "deepsoil_equivalent" / "smoke").mkdir(parents=True)
    (repo_root / "out" / "campaign_core_es_local").mkdir(parents=True)
    (repo_root / "out" / "benchmarks_parity").mkdir(parents=True)

    source_script = Path(__file__).resolve().parents[1] / "scripts" / "build_validation_bundle.py"
    target_script = repo_root / "scripts" / "build_validation_bundle.py"
    target_script.write_text(source_script.read_text(encoding="utf-8"), encoding="utf-8")

    (repo_root / "SCIENTIFIC_CONFIDENCE_MATRIX.md").write_text(
        "# Scientific Confidence Matrix\n\nplaceholder\n",
        encoding="utf-8",
    )
    (repo_root / "docs" / "PM4_CALIBRATION_VALIDATION.md").write_text(
        "# PM4 Guide\n\nplaceholder\n",
        encoding="utf-8",
    )
    (repo_root / "docs" / "RELEASE_SIGNOFF_CHECKLIST.md").write_text(
        "# Release Checklist\n\nplaceholder\n",
        encoding="utf-8",
    )
    smoke_summary = {
        "passed": True,
        "passed_cases": 4,
        "total_cases": 4,
        "cases": [
            {"name": "linear", "run_dir": str(repo_root / "missing" / "linear")},
            {"name": "eql", "run_dir": str(repo_root / "missing" / "eql")},
            {"name": "nonlinear", "run_dir": str(repo_root / "missing" / "nonlinear")},
            {
                "name": "effective_stress",
                "run_dir": str(repo_root / "missing" / "effective_stress"),
            },
        ],
    }
    smoke_path = repo_root / "examples" / "output" / "deepsoil_equivalent" / "smoke" / "smoke_summary.json"
    smoke_path.write_text(json.dumps(smoke_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    campaign_summary = {
        "suite": "core-es",
        "benchmark": {"all_passed": True},
        "policy": {"campaign": {"passed": True}},
    }
    campaign_path = repo_root / "out" / "campaign_core_es_local" / "campaign_summary.json"
    campaign_path.write_text(json.dumps(campaign_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    parity_summary = {"suite": "opensees-parity", "ran": 0, "skipped": 1, "all_passed": True}
    parity_path = repo_root / "out" / "benchmarks_parity" / "benchmark_opensees-parity.json"
    parity_path.write_text(json.dumps(parity_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    out_dir = repo_root / "docs" / "reports" / "validation" / "latest"
    subprocess.run(
        ["python", str(target_script), "--repo-root", str(repo_root), "--out-dir", str(out_dir)],
        check=True,
    )

    bundle_json_path = out_dir / "validation_bundle.json"
    bundle_md_path = out_dir / "validation_report.md"
    bundle_pdf_path = out_dir / "validation_report.pdf"
    assert bundle_json_path.exists()
    assert bundle_md_path.exists()
    assert bundle_pdf_path.exists()

    payload = json.loads(bundle_json_path.read_text(encoding="utf-8"))
    assert payload["evidence"]["smoke"]["status"] == "done"
    assert payload["evidence"]["opensees_parity"]["status"] == "partial"
    assert any(
        row["component"] == "OpenSees effective-stress adapter"
        for row in payload["status_matrix"]
    )


