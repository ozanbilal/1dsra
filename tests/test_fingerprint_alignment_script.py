from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _write_policy(path: Path, fingerprint: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "component_suites:",
                "  - core-es",
                f'opensees_fingerprint: "{fingerprint}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_matrix(path: Path, fingerprint: str) -> None:
    header = "| suite | case_count | reference_basis | tolerance_policy | binary_fingerprint |"
    divider = "|---|---:|---|---|---|"
    row = f"| `opensees-parity` | 6 | ref | tol | `{fingerprint}` |"
    path.write_text(
        "\n".join(
            [
                "# Scientific Confidence Matrix",
                "",
                header,
                divider,
                row,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _run(
    expected_sha: str,
    policy_path: Path,
    matrix_path: Path,
) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_fingerprint_alignment.py"
    cmd = [
        sys.executable,
        str(script),
        "--expected-sha",
        expected_sha,
        "--policy",
        str(policy_path),
        "--matrix",
        str(matrix_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_fingerprint_alignment_script_passes_when_all_match(tmp_path: Path) -> None:
    sha = "a" * 64
    policy_path = tmp_path / "benchmarks" / "policies" / "release_signoff.yml"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    _write_policy(policy_path, sha)
    _write_matrix(matrix_path, sha)

    result = _run(sha, policy_path, matrix_path)
    assert result.returncode == 0, result.stderr


def test_fingerprint_alignment_script_fails_on_policy_mismatch(tmp_path: Path) -> None:
    expected = "b" * 64
    policy = "c" * 64
    matrix = expected
    policy_path = tmp_path / "benchmarks" / "policies" / "release_signoff.yml"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    _write_policy(policy_path, policy)
    _write_matrix(matrix_path, matrix)

    result = _run(expected, policy_path, matrix_path)
    assert result.returncode != 0
    assert "release_signoff.yml opensees_fingerprint" in (result.stderr + result.stdout)


def test_fingerprint_alignment_script_fails_on_matrix_mismatch(tmp_path: Path) -> None:
    expected = "d" * 64
    policy = expected
    matrix = "e" * 64
    policy_path = tmp_path / "benchmarks" / "policies" / "release_signoff.yml"
    matrix_path = tmp_path / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    _write_policy(policy_path, policy)
    _write_matrix(matrix_path, matrix)

    result = _run(expected, policy_path, matrix_path)
    assert result.returncode != 0
    assert "SCIENTIFIC_CONFIDENCE_MATRIX.md opensees-parity binary_fingerprint" in (
        result.stderr + result.stdout
    )
