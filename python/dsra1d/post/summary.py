from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import cast


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _as_str_list(value: object) -> list[str]:
    return [str(v) for v in _as_list(value)]


def _classify_benchmark_case(case: dict[str, object]) -> str:
    status = str(case.get("status", ""))
    if status == "skipped":
        reason = str(case.get("reason", "")).lower()
        if "executable not found" in reason:
            return "skipped_missing_executable"
        return "skipped_other"

    if bool(case.get("passed", False)):
        return "passed"

    if status not in {"ok", "skipped"}:
        return "runtime_error"

    checks = _as_dict(case.get("checks"))
    for _, check_obj in checks.items():
        check = _as_dict(check_obj)
        if bool(check) and not bool(check.get("passed", True)):
            return "metric_mismatch"

    constraints = _as_dict(case.get("constraints"))
    if constraints:
        if not bool(constraints.get("ru_bounds_ok", True)):
            return "ru_constraint_fail"
        constraint_ok_flags = [
            key for key in constraints if key.endswith("_ok")
        ]
        if any(not bool(constraints.get(key, True)) for key in constraint_ok_flags):
            return "constraint_fail"

    deterministic = _as_dict(case.get("deterministic"))
    if deterministic and not bool(deterministic.get("ok", True)):
        return "determinism_fail"

    dt_sensitivity = _as_dict(case.get("dt_sensitivity"))
    if dt_sensitivity and not bool(dt_sensitivity.get("passed", True)):
        return "dt_sensitivity_fail"

    return "failed_other"


def _classify_verify_run(report: dict[str, object]) -> str:
    if bool(report.get("ok", False)):
        return "passed"

    checks = _as_dict(report.get("checks"))
    if checks:
        if "hdf5_readable" in checks and not bool(checks.get("hdf5_readable", True)):
            return "hdf5_unreadable"
        if "sqlite_readable" in checks and not bool(checks.get("sqlite_readable", True)):
            return "sqlite_unreadable"
        if "unexpected_error" in checks and not bool(checks.get("unexpected_error", True)):
            return "unexpected_error"
        if not bool(checks.get("files_present", True)):
            return "missing_files"
        if not bool(checks.get("run_id_meta_vs_sqlite", True)):
            return "run_id_mismatch"
        metric_keys = [k for k in checks if k.startswith("metrics_")]
        if any(not bool(checks.get(k, True)) for k in metric_keys):
            return "metric_mismatch"
        pwp_effective_keys = [k for k in checks if k.startswith("pwp_effective_")]
        if any(not bool(checks.get(k, True)) for k in pwp_effective_keys):
            return "pwp_effective_mismatch"
        checksum_keys = [
            "checksum_h5_meta_match",
            "checksum_h5_sqlite_match",
            "checksum_sqlite_meta_match",
        ]
        if any((k in checks) and (not bool(checks.get(k, True))) for k in checksum_keys):
            return "checksum_mismatch"
    return "failed_other"


def _classify_deepsoil_case(case: dict[str, object]) -> str:
    if bool(case.get("passed", False)):
        return "passed"
    checks = _as_dict(case.get("checks"))
    if not checks:
        return "failed_other"
    if not _as_bool(checks.get("surface_corrcoef_min"), default=True):
        return "surface_corrcoef_fail"
    if not _as_bool(checks.get("surface_nrmse_max"), default=True):
        return "surface_nrmse_fail"
    if not _as_bool(checks.get("psa_nrmse_max"), default=True):
        return "psa_nrmse_fail"
    if not _as_bool(checks.get("pga_pct_diff_abs_max"), default=True):
        return "pga_pct_diff_fail"
    if not _as_bool(checks.get("profile_nrmse_max"), default=True):
        return "profile_nrmse_fail"
    if not _as_bool(checks.get("hysteresis_stress_nrmse_max"), default=True):
        return "hysteresis_stress_nrmse_fail"
    if not _as_bool(checks.get("hysteresis_energy_pct_diff_abs_max"), default=True):
        return "hysteresis_energy_pct_diff_fail"
    return "failed_other"


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def summarize_campaign(
    benchmark_report: dict[str, object],
    verify_batch_report: dict[str, object] | None = None,
    deepsoil_compare_report: dict[str, object] | None = None,
) -> dict[str, object]:
    cases_raw = _as_list(benchmark_report.get("cases"))
    benchmark_classes: Counter[str] = Counter()
    failed_cases: list[str] = []
    for case_obj in cases_raw:
        case = _as_dict(case_obj)
        cls = _classify_benchmark_case(case)
        benchmark_classes[cls] += 1
        if cls != "passed":
            failed_cases.append(str(case.get("name", "unknown")))

    verify_classes: Counter[str] = Counter()
    failed_runs: list[str] = []
    if verify_batch_report is not None:
        reports = _as_dict(verify_batch_report.get("reports"))
        for run_name, rep_obj in reports.items():
            rep = _as_dict(rep_obj)
            cls = _classify_verify_run(rep)
            verify_classes[cls] += 1
            if cls != "passed":
                failed_runs.append(str(run_name))

    deepsoil_classes: Counter[str] = Counter()
    failed_deepsoil_cases: list[str] = []
    if deepsoil_compare_report is not None:
        deepsoil_cases = _as_list(deepsoil_compare_report.get("cases"))
        for case_obj in deepsoil_cases:
            case = _as_dict(case_obj)
            cls = _classify_deepsoil_case(case)
            deepsoil_classes[cls] += 1
            if cls != "passed":
                failed_deepsoil_cases.append(str(case.get("name", "unknown")))

    benchmark_total_cases = _as_int(benchmark_report.get("total_cases", len(cases_raw)))
    benchmark_ran = _as_int(benchmark_report.get("ran", 0))
    benchmark_skipped = _as_int(benchmark_report.get("skipped", 0))
    benchmark_skipped_backend = _as_int(benchmark_report.get("skipped_backend", 0))
    benchmark_backend_ready = bool(
        benchmark_report.get("backend_ready", benchmark_skipped_backend == 0)
    )
    benchmark_execution_coverage = benchmark_report.get("execution_coverage")
    if not isinstance(benchmark_execution_coverage, (int, float)):
        denom = benchmark_total_cases if benchmark_total_cases > 0 else 1
        benchmark_execution_coverage = benchmark_ran / denom
    backend_missing_cases = _as_str_list(benchmark_report.get("backend_missing_cases"))
    backend_fingerprint_ok = _as_bool(
        benchmark_report.get("backend_fingerprint_ok"),
        default=True,
    )
    benchmark_policy_raw = _as_dict(benchmark_report.get("policy"))
    fail_on_skip = _as_bool(benchmark_policy_raw.get("fail_on_skip"), default=False)
    require_runs = _as_int(benchmark_policy_raw.get("require_runs", 0))
    require_opensees = _as_bool(
        benchmark_policy_raw.get("require_opensees"),
        default=False,
    )
    min_execution_coverage = _as_float(
        benchmark_policy_raw.get("min_execution_coverage", 0.0),
        default=0.0,
    )
    benchmark_conditions = {
        "all_passed": bool(benchmark_report.get("all_passed", False)),
        "fail_on_skip_ok": (not fail_on_skip) or (benchmark_skipped == 0),
        "require_runs_ok": benchmark_ran >= require_runs,
        "require_opensees_ok": (not require_opensees) or benchmark_backend_ready,
        "min_execution_coverage_ok": benchmark_execution_coverage >= min_execution_coverage,
        "backend_fingerprint_ok": backend_fingerprint_ok,
    }
    benchmark_policy_passed = all(benchmark_conditions.values())

    summary: dict[str, object] = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "suite": str(benchmark_report.get("suite", "")),
        "benchmark": {
            "all_passed": bool(benchmark_report.get("all_passed", False)),
            "skipped": benchmark_skipped,
            "ran": benchmark_ran,
            "total_cases": benchmark_total_cases,
            "skipped_backend": benchmark_skipped_backend,
            "backend_ready": benchmark_backend_ready,
            "execution_coverage": float(benchmark_execution_coverage),
            "backend_missing_cases": backend_missing_cases,
            "backend_fingerprint_ok": backend_fingerprint_ok,
            "classification_counts": dict(benchmark_classes),
            "failed_or_nonpass_cases": failed_cases,
        },
        "policy": {
            "benchmark": {
                "fail_on_skip": fail_on_skip,
                "require_runs": require_runs,
                "require_opensees": require_opensees,
                "min_execution_coverage": min_execution_coverage,
                "require_backend_version_regex": str(
                    benchmark_policy_raw.get("require_backend_version_regex", "")
                ),
                "require_backend_sha256": str(
                    benchmark_policy_raw.get("require_backend_sha256", "")
                ),
                "conditions": benchmark_conditions,
                "passed": benchmark_policy_passed,
            }
        },
    }
    if verify_batch_report is not None:
        verify_policy_raw = _as_dict(verify_batch_report.get("policy"))
        verify_require_runs = _as_int(verify_policy_raw.get("require_runs", 0))
        verify_ok = bool(verify_batch_report.get("ok", False))
        verify_total_runs = _as_int(verify_batch_report.get("total_runs", 0))
        verify_conditions_raw = _as_dict(verify_policy_raw.get("conditions"))
        verify_conditions = {
            str(k): _as_bool(v)
            for k, v in verify_conditions_raw.items()
        }
        require_runs_ok = verify_total_runs >= verify_require_runs
        verify_conditions["verify_ok"] = verify_ok
        verify_conditions["require_runs_ok"] = require_runs_ok
        verify_conditions["verify_require_runs_ok"] = require_runs_ok
        verify_policy_passed = all(verify_conditions.values())
        summary["verify_batch"] = {
            "ok": verify_ok,
            "total_runs": verify_total_runs,
            "passed_runs": _as_int(verify_batch_report.get("passed_runs", 0)),
            "failed_runs": _as_int(verify_batch_report.get("failed_runs", 0)),
            "classification_counts": dict(verify_classes),
            "failed_or_nonpass_runs": failed_runs,
        }
        summary_policy = _as_dict(summary.get("policy"))
        summary_policy["verify_batch"] = {
            "require_runs": verify_require_runs,
            "conditions": verify_conditions,
            "passed": verify_policy_passed,
        }
        summary_policy["campaign"] = {
            "passed": benchmark_policy_passed and verify_policy_passed,
        }
        summary["policy"] = summary_policy
    if deepsoil_compare_report is not None:
        deepsoil_cases_raw = _as_list(deepsoil_compare_report.get("cases"))
        deepsoil_total_cases = _as_int(
            deepsoil_compare_report.get("total_cases", len(deepsoil_cases_raw))
        )
        deepsoil_passed_cases = _as_int(deepsoil_compare_report.get("passed_cases", 0))
        deepsoil_failed_cases = _as_int(deepsoil_compare_report.get("failed_cases", 0))
        deepsoil_policy_raw = _as_dict(deepsoil_compare_report.get("policy"))
        deepsoil_policy = {
            "surface_corrcoef_min": _as_float(
                deepsoil_policy_raw.get("surface_corrcoef_min"),
                0.95,
            ),
            "surface_nrmse_max": _as_float(
                deepsoil_policy_raw.get("surface_nrmse_max"),
                0.20,
            ),
            "psa_nrmse_max": _as_float(
                deepsoil_policy_raw.get("psa_nrmse_max"),
                0.20,
            ),
            "pga_pct_diff_abs_max": _as_float(
                deepsoil_policy_raw.get("pga_pct_diff_abs_max"),
                20.0,
            ),
            "profile_nrmse_max": deepsoil_policy_raw.get("profile_nrmse_max"),
            "hysteresis_stress_nrmse_max": deepsoil_policy_raw.get(
                "hysteresis_stress_nrmse_max"
            ),
            "hysteresis_energy_pct_diff_abs_max": deepsoil_policy_raw.get(
                "hysteresis_energy_pct_diff_abs_max"
            ),
        }
        deepsoil_policy_passed = (
            deepsoil_failed_cases == 0
            and deepsoil_passed_cases == deepsoil_total_cases
        )
        summary["deepsoil_compare"] = {
            "total_cases": deepsoil_total_cases,
            "passed_cases": deepsoil_passed_cases,
            "failed_cases": deepsoil_failed_cases,
            "classification_counts": dict(deepsoil_classes),
            "failed_or_nonpass_cases": failed_deepsoil_cases,
        }
        summary_policy = _as_dict(summary.get("policy"))
        summary_policy["deepsoil_compare"] = {
            **deepsoil_policy,
            "passed": deepsoil_policy_passed,
        }
        campaign_policy = _as_dict(summary_policy.get("campaign"))
        if campaign_policy:
            campaign_policy["passed"] = bool(
                campaign_policy.get("passed", False)
            ) and deepsoil_policy_passed
        else:
            campaign_policy = {"passed": benchmark_policy_passed and deepsoil_policy_passed}
        summary_policy["campaign"] = campaign_policy
        summary["policy"] = summary_policy
    return summary


def render_summary_markdown(summary: dict[str, object]) -> str:
    benchmark = _as_dict(summary.get("benchmark"))
    lines: list[str] = []
    lines.append("# StrataWave Campaign Summary")
    lines.append("")
    lines.append(f"- Generated: `{summary.get('generated_utc', '')}`")
    lines.append(f"- Suite: `{summary.get('suite', '')}`")
    lines.append(
        "- Benchmark: "
        f"all_passed={benchmark.get('all_passed')} "
        f"total_cases={benchmark.get('total_cases')} "
        f"ran={benchmark.get('ran')} "
        f"skipped={benchmark.get('skipped')} "
        f"skipped_backend={benchmark.get('skipped_backend')} "
        f"backend_ready={benchmark.get('backend_ready')} "
        f"backend_fingerprint_ok={benchmark.get('backend_fingerprint_ok')} "
        f"execution_coverage={benchmark.get('execution_coverage')}"
    )
    backend_missing_cases = _as_str_list(benchmark.get("backend_missing_cases"))
    if backend_missing_cases:
        lines.append("- Benchmark backend missing cases:")
        for case_name in backend_missing_cases:
            lines.append(f"  - `{case_name}`")
    bench_counts = _as_dict(benchmark.get("classification_counts"))
    if bench_counts:
        lines.append("- Benchmark classifications:")
        for key in sorted(bench_counts):
            lines.append(f"  - `{key}`: {bench_counts[key]}")

    policy = _as_dict(summary.get("policy"))
    benchmark_policy = _as_dict(policy.get("benchmark"))
    if benchmark_policy:
        lines.append(
            "- Benchmark policy: "
            f"passed={benchmark_policy.get('passed')} "
            f"fail_on_skip={benchmark_policy.get('fail_on_skip')} "
            f"require_runs={benchmark_policy.get('require_runs')} "
            f"require_opensees={benchmark_policy.get('require_opensees')} "
            f"min_execution_coverage={benchmark_policy.get('min_execution_coverage')} "
            "require_backend_version_regex="
            f"{benchmark_policy.get('require_backend_version_regex')} "
            f"require_backend_sha256={benchmark_policy.get('require_backend_sha256')}"
        )

    verify_batch = _as_dict(summary.get("verify_batch"))
    if verify_batch:
        lines.append(
            "- Verify batch: "
            f"ok={verify_batch.get('ok')} "
            f"total_runs={verify_batch.get('total_runs')} "
            f"failed_runs={verify_batch.get('failed_runs')}"
        )
        verify_counts = _as_dict(verify_batch.get("classification_counts"))
        if verify_counts:
            lines.append("- Verify classifications:")
            for key in sorted(verify_counts):
                lines.append(f"  - `{key}`: {verify_counts[key]}")
        verify_policy = _as_dict(policy.get("verify_batch"))
        if verify_policy:
            lines.append(
                "- Verify policy: "
                f"passed={verify_policy.get('passed')} "
                f"require_runs={verify_policy.get('require_runs')}"
            )
    deepsoil_compare = _as_dict(summary.get("deepsoil_compare"))
    if deepsoil_compare:
        lines.append(
            "- DEEPSOIL compare: "
            f"total_cases={deepsoil_compare.get('total_cases')} "
            f"passed_cases={deepsoil_compare.get('passed_cases')} "
            f"failed_cases={deepsoil_compare.get('failed_cases')}"
        )
        deepsoil_counts = _as_dict(deepsoil_compare.get("classification_counts"))
        if deepsoil_counts:
            lines.append("- DEEPSOIL compare classifications:")
            for key in sorted(deepsoil_counts):
                lines.append(f"  - `{key}`: {deepsoil_counts[key]}")
        deepsoil_policy = _as_dict(policy.get("deepsoil_compare"))
        if deepsoil_policy:
            lines.append(
                "- DEEPSOIL compare policy: "
                f"passed={deepsoil_policy.get('passed')} "
                f"surface_corrcoef_min={deepsoil_policy.get('surface_corrcoef_min')} "
                f"surface_nrmse_max={deepsoil_policy.get('surface_nrmse_max')} "
                f"psa_nrmse_max={deepsoil_policy.get('psa_nrmse_max')} "
                f"pga_pct_diff_abs_max={deepsoil_policy.get('pga_pct_diff_abs_max')} "
                f"profile_nrmse_max={deepsoil_policy.get('profile_nrmse_max')} "
                "hysteresis_stress_nrmse_max="
                f"{deepsoil_policy.get('hysteresis_stress_nrmse_max')} "
                "hysteresis_energy_pct_diff_abs_max="
                f"{deepsoil_policy.get('hysteresis_energy_pct_diff_abs_max')}"
            )
    campaign_policy = _as_dict(policy.get("campaign"))
    if campaign_policy:
        lines.append(f"- Campaign policy: passed={campaign_policy.get('passed')}")

    return "\n".join(lines) + "\n"

