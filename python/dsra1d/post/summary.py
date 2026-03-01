from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import cast


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


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
    if constraints and not bool(constraints.get("ru_bounds_ok", True)):
        return "ru_constraint_fail"

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
        checksum_keys = [
            "checksum_h5_meta_match",
            "checksum_h5_sqlite_match",
            "checksum_sqlite_meta_match",
        ]
        if any((k in checks) and (not bool(checks.get(k, True))) for k in checksum_keys):
            return "checksum_mismatch"
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


def summarize_campaign(
    benchmark_report: dict[str, object],
    verify_batch_report: dict[str, object] | None = None,
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

    summary: dict[str, object] = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "suite": str(benchmark_report.get("suite", "")),
        "benchmark": {
            "all_passed": bool(benchmark_report.get("all_passed", False)),
            "skipped": _as_int(benchmark_report.get("skipped", 0)),
            "ran": _as_int(benchmark_report.get("ran", 0)),
            "total_cases": len(cases_raw),
            "classification_counts": dict(benchmark_classes),
            "failed_or_nonpass_cases": failed_cases,
        },
    }
    if verify_batch_report is not None:
        summary["verify_batch"] = {
            "ok": bool(verify_batch_report.get("ok", False)),
            "total_runs": _as_int(verify_batch_report.get("total_runs", 0)),
            "passed_runs": _as_int(verify_batch_report.get("passed_runs", 0)),
            "failed_runs": _as_int(verify_batch_report.get("failed_runs", 0)),
            "classification_counts": dict(verify_classes),
            "failed_or_nonpass_runs": failed_runs,
        }
    return summary


def render_summary_markdown(summary: dict[str, object]) -> str:
    benchmark = _as_dict(summary.get("benchmark"))
    lines: list[str] = []
    lines.append("# 1DSRA Campaign Summary")
    lines.append("")
    lines.append(f"- Generated: `{summary.get('generated_utc', '')}`")
    lines.append(f"- Suite: `{summary.get('suite', '')}`")
    lines.append(
        "- Benchmark: "
        f"all_passed={benchmark.get('all_passed')} "
        f"total_cases={benchmark.get('total_cases')} "
        f"ran={benchmark.get('ran')} "
        f"skipped={benchmark.get('skipped')}"
    )
    bench_counts = _as_dict(benchmark.get("classification_counts"))
    if bench_counts:
        lines.append("- Benchmark classifications:")
        for key in sorted(bench_counts):
            lines.append(f"  - `{key}`: {bench_counts[key]}")

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

    return "\n".join(lines) + "\n"
