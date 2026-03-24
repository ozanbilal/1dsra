from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import yaml
from dsra1d.benchmark import CORE_RELEASE_SIGNOFF_SUITES


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _load_yaml(path: Path) -> dict[str, object]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path for CI checks
        raise SystemExit(f"Failed to read YAML: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected YAML mapping: {path}")
    return payload


def _load_case_count(repo_root: Path, suite: str) -> int:
    path = repo_root / "benchmarks" / suite / "cases" / "case_list.json"
    _require(path.exists(), f"Missing case_list for suite '{suite}': {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path for CI checks
        raise SystemExit(f"Failed to read JSON: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object in {path}")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise SystemExit(f"Expected 'cases' list in {path}")
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate release_signoff policy consistency against benchmark suite "
            "definition and case matrix."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=Path("."),
        type=Path,
        help="Repository root path.",
    )
    parser.add_argument(
        "--policy",
        default=Path("benchmarks/policies/release_signoff.yml"),
        type=Path,
        help="Release signoff policy YAML path (relative to repo root unless absolute).",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    policy_path = args.policy if args.policy.is_absolute() else (repo_root / args.policy)
    _require(policy_path.exists(), f"Policy path does not exist: {policy_path}")
    policy = _load_yaml(policy_path)

    expected_suites = list(CORE_RELEASE_SIGNOFF_SUITES)
    policy_suites_raw = policy.get("component_suites")
    _require(
        isinstance(policy_suites_raw, list),
        "policy component_suites must be a list",
    )
    assert isinstance(policy_suites_raw, list)
    policy_suites = [str(v) for v in policy_suites_raw]
    _require(
        policy_suites == expected_suites,
        (
            "policy component_suites mismatch. "
            f"expected={expected_suites}, got={policy_suites}"
        ),
    )

    case_counts = {suite: _load_case_count(repo_root, suite) for suite in expected_suites}
    expected_runs = int(sum(case_counts.values()))
    policy_require_runs_raw = policy.get("require_runs", 0)
    _require(
        isinstance(policy_require_runs_raw, (int, float, str))
        and not isinstance(policy_require_runs_raw, bool),
        "policy require_runs must be numeric",
    )
    policy_require_runs = int(cast(int | float | str, policy_require_runs_raw))
    _require(
        policy_require_runs == expected_runs,
        (
            "policy require_runs mismatch. "
            f"expected={expected_runs} from case lists, got={policy_require_runs}"
        ),
    )

    _require(bool(policy.get("fail_on_skip", False)), "policy fail_on_skip must be true")
    _require(
        bool(policy.get("require_explicit_checks", False)),
        "policy require_explicit_checks must be true",
    )
    _require(bool(policy.get("require_opensees", False)), "policy require_opensees must be true")
    min_cov_raw = policy.get("min_execution_coverage", 0.0)
    _require(
        isinstance(min_cov_raw, (int, float, str)) and not isinstance(min_cov_raw, bool),
        "policy min_execution_coverage must be numeric",
    )
    min_cov = float(cast(int | float | str, min_cov_raw))
    _require(min_cov >= 1.0, "policy min_execution_coverage must be >= 1.0")
    require_deepsoil_compare = bool(policy.get("require_deepsoil_compare", False))
    require_deepsoil_profile = bool(policy.get("require_deepsoil_profile", False))
    require_deepsoil_hysteresis = bool(policy.get("require_deepsoil_hysteresis", False))
    _require(
        (not require_deepsoil_profile and not require_deepsoil_hysteresis)
        or require_deepsoil_compare,
        (
            "policy require_deepsoil_compare must be true when "
            "require_deepsoil_profile or require_deepsoil_hysteresis is enabled"
        ),
    )

    print("Release policy consistency validated.")
    print(f"- policy: {policy_path}")
    print(f"- component_suites: {policy_suites}")
    print(f"- case_counts: {case_counts}")
    print(f"- require_runs: {policy_require_runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
