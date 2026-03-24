from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from dsra1d.benchmark import CORE_RELEASE_SIGNOFF_SUITES


def _write_case_list(repo_root: Path, suite: str, n_cases: int) -> None:
    path = repo_root / "benchmarks" / suite / "cases" / "case_list.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": [{"name": f"{suite}-{i}"} for i in range(n_cases)]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_policy(
    repo_root: Path,
    *,
    suites: list[str],
    require_runs: int,
    min_execution_coverage: float = 1.0,
    fail_on_skip: bool = True,
    require_explicit_checks: bool = True,
    require_opensees: bool = True,
    require_deepsoil_compare: bool = False,
    require_deepsoil_profile: bool = False,
    require_deepsoil_hysteresis: bool = False,
) -> Path:
    path = repo_root / "benchmarks" / "policies" / "release_signoff.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["component_suites:"]
    for suite in suites:
        lines.append(f"  - {suite}")
    lines.extend(
        [
            "",
            f"require_runs: {require_runs}",
            f"min_execution_coverage: {min_execution_coverage}",
            f"fail_on_skip: {'true' if fail_on_skip else 'false'}",
            f"require_explicit_checks: {'true' if require_explicit_checks else 'false'}",
            f"require_opensees: {'true' if require_opensees else 'false'}",
            f"require_deepsoil_compare: {'true' if require_deepsoil_compare else 'false'}",
            f"require_deepsoil_profile: {'true' if require_deepsoil_profile else 'false'}",
            (
                "require_deepsoil_hysteresis: "
                f"{'true' if require_deepsoil_hysteresis else 'false'}"
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _run(repo_root: Path, policy_path: Path) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_release_policy_consistency.py"
    cmd = [
        sys.executable,
        str(script),
        "--repo-root",
        str(repo_root),
        "--policy",
        str(policy_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_release_policy_consistency_script_passes(tmp_path: Path) -> None:
    suites = list(CORE_RELEASE_SIGNOFF_SUITES)
    for suite in suites:
        _write_case_list(tmp_path, suite, 2)
    expected_runs = len(suites) * 2
    policy_path = _write_policy(tmp_path, suites=suites, require_runs=expected_runs)

    result = _run(tmp_path, policy_path)
    assert result.returncode == 0, result.stderr


def test_release_policy_consistency_script_fails_on_suite_mismatch(tmp_path: Path) -> None:
    suites = list(CORE_RELEASE_SIGNOFF_SUITES)
    for suite in suites:
        _write_case_list(tmp_path, suite, 1)
    bad_suites = suites[:-1]
    policy_path = _write_policy(tmp_path, suites=bad_suites, require_runs=len(suites))

    result = _run(tmp_path, policy_path)
    assert result.returncode != 0
    assert "component_suites mismatch" in (result.stderr + result.stdout)


def test_release_policy_consistency_script_fails_on_require_runs_mismatch(tmp_path: Path) -> None:
    suites = list(CORE_RELEASE_SIGNOFF_SUITES)
    for suite in suites:
        _write_case_list(tmp_path, suite, 1)
    policy_path = _write_policy(tmp_path, suites=suites, require_runs=999)

    result = _run(tmp_path, policy_path)
    assert result.returncode != 0
    assert "require_runs mismatch" in (result.stderr + result.stdout)


def test_release_policy_consistency_script_requires_deepsoil_compare_for_profile_flags(
    tmp_path: Path,
) -> None:
    suites = list(CORE_RELEASE_SIGNOFF_SUITES)
    for suite in suites:
        _write_case_list(tmp_path, suite, 1)
    policy_path = _write_policy(
        tmp_path,
        suites=suites,
        require_runs=len(suites),
        require_deepsoil_compare=False,
        require_deepsoil_profile=True,
    )

    result = _run(tmp_path, policy_path)
    assert result.returncode != 0
    assert "require_deepsoil_compare must be true" in (result.stderr + result.stdout)
