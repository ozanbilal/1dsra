from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_release_artifacts(
    campaign_dir: Path,
    observed_sha256: str,
    *,
    probe_assumed_available: bool = False,
    require_deepsoil_compare: bool = False,
    require_deepsoil_profile: bool = False,
    require_deepsoil_hysteresis: bool = False,
    deepsoil_compare_present: bool = True,
    deepsoil_compare_passed: bool = True,
    deepsoil_profile_required_ok: bool = True,
    deepsoil_hysteresis_required_ok: bool = True,
) -> None:
    campaign_dir.mkdir(parents=True, exist_ok=True)
    (campaign_dir / "benchmark_release-signoff.json").write_text(
        json.dumps(
            {
                "suite": "release-signoff",
                "all_passed": True,
                "ran": 18,
                "total_cases": 18,
                "skipped": 0,
                "execution_coverage": 1.0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (campaign_dir / "verify_batch_report.json").write_text(
        json.dumps(
            {
                "ok": True,
                "total_runs": 18,
                "passed_runs": 18,
                "failed_runs": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (campaign_dir / "campaign_summary.json").write_text(
        json.dumps(
            {
                "suite": "release-signoff",
                "policy": {"campaign": {"passed": True}},
                "signoff": {
                    "strict_signoff": True,
                    "passed": True,
                    "policy": {
                        "require_deepsoil_compare": require_deepsoil_compare,
                        "require_deepsoil_profile": require_deepsoil_profile,
                        "require_deepsoil_hysteresis": require_deepsoil_hysteresis,
                    },
                    "conditions": {
                        "backend_probe_not_assumed": not probe_assumed_available,
                        "deepsoil_compare_present": deepsoil_compare_present,
                        "deepsoil_compare_passed": deepsoil_compare_passed,
                        "deepsoil_profile_required_ok": deepsoil_profile_required_ok,
                        "deepsoil_hysteresis_required_ok": deepsoil_hysteresis_required_ok,
                    },
                    "observed": {
                        "backend_probe_sha256": observed_sha256,
                        "backend_probe_assumed_available": probe_assumed_available,
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (campaign_dir / "campaign_summary.md").write_text(
        "# Campaign Summary\n\nsignoff: pass\n",
        encoding="utf-8",
    )


def _write_matrix(path: Path, fingerprint: str) -> None:
    header = (
        "| suite | case_count | reference_basis | tolerance_policy | "
        "binary_fingerprint | last_verified_utc | confidence_tier | status_notes |"
    )
    row = (
        f"| `opensees-parity` | 6 | ref | tol | `{fingerprint}` | "
        "`2026-03-04T00:00:00Z` | Medium | notes |"
    )
    path.write_text(
        "\n".join(
            [
                "# Scientific Confidence Matrix",
                "",
                "Last updated: 2026-03-04",
                "",
                header,
                "|---|---:|---|---|---|---|---|---|",
                row,
            ]
        ),
        encoding="utf-8",
    )


def _run_checker(
    campaign_dir: Path,
    matrix_path: Path,
    require_fingerprint: bool,
) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_release_signoff.py"
    cmd = [
        sys.executable,
        str(script),
        "--campaign-dir",
        str(campaign_dir),
        "--matrix",
        str(matrix_path),
    ]
    if require_fingerprint:
        cmd.append("--require-fingerprint")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_signoff_checker_passes_without_fingerprint_requirement(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "campaign"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    observed_sha = "a" * 64
    _write_release_artifacts(campaign_dir, observed_sha)
    _write_matrix(matrix_path, "pending_release_sha256")

    result = _run_checker(campaign_dir, matrix_path, require_fingerprint=False)
    assert result.returncode == 0, result.stderr


def test_release_signoff_checker_requires_exact_sha_match(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "campaign"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    observed_sha = "b" * 64
    _write_release_artifacts(campaign_dir, observed_sha)
    _write_matrix(matrix_path, observed_sha)

    result = _run_checker(campaign_dir, matrix_path, require_fingerprint=True)
    assert result.returncode == 0, result.stderr


def test_release_signoff_checker_fails_on_sha_mismatch(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "campaign"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    observed_sha = "c" * 64
    _write_release_artifacts(campaign_dir, observed_sha)
    _write_matrix(matrix_path, "d" * 64)

    result = _run_checker(campaign_dir, matrix_path, require_fingerprint=True)
    assert result.returncode != 0
    assert "must match signoff observed backend sha256" in (result.stderr + result.stdout)


def test_release_signoff_checker_fails_when_probe_is_assumed(tmp_path: Path) -> None:
    campaign_dir = tmp_path / "campaign"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    observed_sha = "e" * 64
    _write_release_artifacts(campaign_dir, observed_sha, probe_assumed_available=True)
    _write_matrix(matrix_path, observed_sha)

    result = _run_checker(campaign_dir, matrix_path, require_fingerprint=True)
    assert result.returncode != 0
    assert "backend_probe_not_assumed" in (result.stderr + result.stdout)


def test_release_signoff_checker_fails_when_required_deepsoil_compare_missing(
    tmp_path: Path,
) -> None:
    campaign_dir = tmp_path / "campaign"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    observed_sha = "f" * 64
    _write_release_artifacts(
        campaign_dir,
        observed_sha,
        require_deepsoil_compare=True,
        deepsoil_compare_present=False,
    )
    _write_matrix(matrix_path, observed_sha)

    result = _run_checker(campaign_dir, matrix_path, require_fingerprint=True)
    assert result.returncode != 0
    assert "deepsoil_compare_present" in (result.stderr + result.stdout)
