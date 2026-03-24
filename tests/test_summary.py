from __future__ import annotations

from dsra1d.post import render_summary_markdown, summarize_campaign


def test_summarize_campaign_benchmark_only() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "opensees-parity",
        "all_passed": False,
        "skipped": 1,
        "ran": 2,
        "total_cases": 3,
        "skipped_backend": 1,
        "backend_ready": False,
        "execution_coverage": 2.0 / 3.0,
        "backend_missing_cases": ["case_skip"],
        "policy": {
            "fail_on_skip": True,
            "require_runs": 2,
            "require_opensees": True,
            "min_execution_coverage": 0.5,
        },
        "cases": [
            {"name": "case_pass", "status": "ok", "passed": True},
            {"name": "case_skip", "status": "skipped", "reason": "OpenSees executable not found"},
            {
                "name": "case_metric_fail",
                "status": "ok",
                "passed": False,
                "checks": {"pga": {"passed": False}},
            },
        ],
    }
    summary = summarize_campaign(benchmark_report)

    benchmark = summary["benchmark"]
    assert isinstance(benchmark, dict)
    assert benchmark["total_cases"] == 3
    assert benchmark["skipped_backend"] == 1
    assert benchmark["backend_ready"] is False
    assert benchmark["execution_coverage"] == 2.0 / 3.0
    assert benchmark["backend_missing_cases"] == ["case_skip"]
    counts = benchmark["classification_counts"]
    assert isinstance(counts, dict)
    assert counts["passed"] == 1
    assert counts["skipped_missing_executable"] == 1
    assert counts["metric_mismatch"] == 1

    nonpass = benchmark["failed_or_nonpass_cases"]
    assert isinstance(nonpass, list)
    assert sorted(nonpass) == ["case_metric_fail", "case_skip"]
    policy = summary["policy"]
    assert isinstance(policy, dict)
    bench_policy = policy["benchmark"]
    assert isinstance(bench_policy, dict)
    assert bench_policy["passed"] is False


def test_summarize_campaign_classifies_generic_constraint_fail() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "core-hyst",
        "all_passed": False,
        "skipped": 0,
        "ran": 1,
        "cases": [
            {
                "name": "case_constraint_fail",
                "status": "ok",
                "passed": False,
                "constraints": {
                    "ru_bounds_ok": True,
                    "delta_u_min_ok": False,
                },
            }
        ],
    }
    summary = summarize_campaign(benchmark_report)
    benchmark = summary["benchmark"]
    assert isinstance(benchmark, dict)
    counts = benchmark["classification_counts"]
    assert isinstance(counts, dict)
    assert counts["constraint_fail"] == 1


def test_summarize_campaign_with_verify_batch() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "core-es",
        "all_passed": True,
        "skipped": 0,
        "ran": 2,
        "cases": [
            {"name": "case01", "status": "ok", "passed": True},
            {"name": "case02", "status": "ok", "passed": True},
        ],
    }
    verify_batch_report: dict[str, object] = {
        "ok": False,
        "total_runs": 2,
        "passed_runs": 1,
        "failed_runs": 1,
        "reports": {
            "run_ok": {"ok": True, "checks": {}},
            "run_bad": {
                "ok": False,
                "checks": {
                    "files_present": True,
                    "run_id_meta_vs_sqlite": False,
                },
            },
        },
        "policy": {"require_runs": 2},
    }
    summary = summarize_campaign(
        benchmark_report=benchmark_report,
        verify_batch_report=verify_batch_report,
    )

    verify = summary["verify_batch"]
    assert isinstance(verify, dict)
    counts = verify["classification_counts"]
    assert isinstance(counts, dict)
    assert counts["passed"] == 1
    assert counts["run_id_mismatch"] == 1
    failed_runs = verify["failed_or_nonpass_runs"]
    assert isinstance(failed_runs, list)
    assert failed_runs == ["run_bad"]
    policy = summary["policy"]
    assert isinstance(policy, dict)
    assert isinstance(policy["verify_batch"], dict)
    assert policy["verify_batch"]["passed"] is False
    assert isinstance(policy["campaign"], dict)
    assert policy["campaign"]["passed"] is False


def test_summarize_campaign_with_deepsoil_compare() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "core-hyst",
        "all_passed": True,
        "skipped": 0,
        "ran": 2,
        "cases": [
            {"name": "case01", "status": "ok", "passed": True},
            {"name": "case02", "status": "ok", "passed": True},
        ],
    }
    deepsoil_compare_report: dict[str, object] = {
        "total_cases": 2,
        "passed_cases": 1,
        "failed_cases": 1,
        "policy": {
            "surface_corrcoef_min": 0.95,
            "surface_nrmse_max": 0.2,
            "psa_nrmse_max": 0.2,
            "pga_pct_diff_abs_max": 20.0,
            "profile_nrmse_max": 0.25,
            "hysteresis_stress_nrmse_max": 0.25,
            "hysteresis_energy_pct_diff_abs_max": 25.0,
        },
        "cases": [
            {"name": "deepsoil-ok", "passed": True, "checks": {}},
            {
                "name": "deepsoil-bad",
                "passed": False,
                "checks": {
                    "surface_corrcoef_min": True,
                    "surface_nrmse_max": False,
                    "psa_nrmse_max": True,
                    "pga_pct_diff_abs_max": True,
                },
            },
        ],
    }

    summary = summarize_campaign(
        benchmark_report=benchmark_report,
        deepsoil_compare_report=deepsoil_compare_report,
    )

    deepsoil = summary["deepsoil_compare"]
    assert isinstance(deepsoil, dict)
    assert deepsoil["failed_cases"] == 1
    counts = deepsoil["classification_counts"]
    assert isinstance(counts, dict)
    assert counts["passed"] == 1
    assert counts["surface_nrmse_fail"] == 1

    policy = summary["policy"]
    assert isinstance(policy, dict)
    deepsoil_policy = policy["deepsoil_compare"]
    assert isinstance(deepsoil_policy, dict)
    assert deepsoil_policy["passed"] is False
    assert deepsoil_policy["profile_nrmse_max"] == 0.25
    campaign_policy = policy["campaign"]
    assert isinstance(campaign_policy, dict)
    assert campaign_policy["passed"] is False


def test_render_summary_markdown_contains_key_sections() -> None:
    summary: dict[str, object] = {
        "generated_utc": "2026-03-01T00:00:00+00:00",
        "suite": "core-es",
        "benchmark": {
            "all_passed": True,
            "total_cases": 2,
            "ran": 2,
            "skipped": 0,
            "skipped_backend": 0,
            "backend_ready": True,
            "execution_coverage": 1.0,
            "backend_missing_cases": [],
            "classification_counts": {"passed": 2},
        },
        "verify_batch": {
            "ok": True,
            "total_runs": 2,
            "failed_runs": 0,
            "classification_counts": {"passed": 2},
        },
        "deepsoil_compare": {
            "total_cases": 2,
            "passed_cases": 2,
            "failed_cases": 0,
            "classification_counts": {"passed": 2},
        },
        "policy": {
            "benchmark": {
                "passed": True,
                "fail_on_skip": False,
                "require_runs": 0,
                "require_opensees": False,
                "min_execution_coverage": 0.0,
            },
            "verify_batch": {"passed": True, "require_runs": 0},
            "deepsoil_compare": {
                "passed": True,
                "surface_corrcoef_min": 0.95,
                "surface_nrmse_max": 0.2,
                "psa_nrmse_max": 0.2,
                "pga_pct_diff_abs_max": 20.0,
            },
            "campaign": {"passed": True},
        },
    }
    md = render_summary_markdown(summary)
    assert "# StrataWave Campaign Summary" in md
    assert "Suite: `core-es`" in md
    assert "backend_ready=True" in md
    assert "execution_coverage=1.0" in md
    assert "Benchmark policy:" in md
    assert "Verify policy:" in md
    assert "DEEPSOIL compare:" in md
    assert "DEEPSOIL compare policy:" in md
    assert "Campaign policy:" in md
    assert "Benchmark classifications" in md
    assert "Verify classifications" in md


def test_render_summary_markdown_lists_backend_missing_cases() -> None:
    summary: dict[str, object] = {
        "generated_utc": "2026-03-01T00:00:00+00:00",
        "suite": "opensees-parity",
        "benchmark": {
            "all_passed": True,
            "total_cases": 3,
            "ran": 0,
            "skipped": 3,
            "skipped_backend": 3,
            "backend_ready": False,
            "execution_coverage": 0.0,
            "backend_missing_cases": ["parity01", "parity02"],
            "classification_counts": {"skipped_missing_executable": 3},
        },
    }
    md = render_summary_markdown(summary)
    assert "Benchmark backend missing cases" in md
    assert "`parity01`" in md


def test_summarize_campaign_computes_execution_coverage_fallback() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "core-es",
        "all_passed": True,
        "skipped": 1,
        "ran": 3,
        "cases": [
            {"name": "a", "status": "ok", "passed": True},
            {"name": "b", "status": "ok", "passed": True},
            {"name": "c", "status": "ok", "passed": True},
            {"name": "d", "status": "skipped", "reason": "placeholder"},
        ],
    }
    summary = summarize_campaign(benchmark_report=benchmark_report)
    benchmark = summary["benchmark"]
    assert isinstance(benchmark, dict)
    assert benchmark["total_cases"] == 4
    assert benchmark["execution_coverage"] == 0.75


def test_summarize_campaign_policy_passes_when_requirements_met() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "opensees-parity",
        "all_passed": True,
        "skipped": 0,
        "ran": 3,
        "total_cases": 3,
        "backend_ready": True,
        "execution_coverage": 1.0,
        "policy": {
            "fail_on_skip": True,
            "require_runs": 3,
            "require_opensees": True,
            "min_execution_coverage": 1.0,
        },
        "cases": [
            {"name": "c1", "status": "ok", "passed": True},
            {"name": "c2", "status": "ok", "passed": True},
            {"name": "c3", "status": "ok", "passed": True},
        ],
    }
    verify_batch_report: dict[str, object] = {
        "ok": True,
        "total_runs": 3,
        "passed_runs": 3,
        "failed_runs": 0,
        "reports": {
            "r1": {"ok": True, "checks": {}},
            "r2": {"ok": True, "checks": {}},
            "r3": {"ok": True, "checks": {}},
        },
        "policy": {"require_runs": 3},
    }
    summary = summarize_campaign(benchmark_report, verify_batch_report)
    policy = summary["policy"]
    assert isinstance(policy, dict)
    assert isinstance(policy["benchmark"], dict)
    assert policy["benchmark"]["passed"] is True
    assert isinstance(policy["verify_batch"], dict)
    assert policy["verify_batch"]["passed"] is True
    assert isinstance(policy["campaign"], dict)
    assert policy["campaign"]["passed"] is True


def test_summarize_campaign_preserves_verify_policy_conditions() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "core-es",
        "all_passed": True,
        "skipped": 0,
        "ran": 1,
        "cases": [{"name": "case01", "status": "ok", "passed": True}],
    }
    verify_batch_report: dict[str, object] = {
        "ok": False,
        "total_runs": 0,
        "passed_runs": 0,
        "failed_runs": 0,
        "reports": {"_batch": {"ok": False, "reason": "Path not found"}},
        "policy": {
            "require_runs": 1,
            "conditions": {
                "verify_ok": False,
                "no_failed_runs": True,
                "require_runs_ok": False,
                "path_exists": False,
                "is_directory": False,
            },
            "passed": False,
        },
    }
    summary = summarize_campaign(benchmark_report, verify_batch_report)
    policy = summary["policy"]
    assert isinstance(policy, dict)
    verify_policy = policy["verify_batch"]
    assert isinstance(verify_policy, dict)
    conditions = verify_policy["conditions"]
    assert isinstance(conditions, dict)
    assert conditions["path_exists"] is False
    assert conditions["is_directory"] is False
    assert verify_policy["passed"] is False


def test_summarize_campaign_classifies_pwp_effective_mismatch() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "core-es",
        "all_passed": True,
        "skipped": 0,
        "ran": 1,
        "cases": [{"name": "case01", "status": "ok", "passed": True}],
    }
    verify_batch_report: dict[str, object] = {
        "ok": False,
        "total_runs": 1,
        "passed_runs": 0,
        "failed_runs": 1,
        "reports": {
            "run_bad": {
                "ok": False,
                "checks": {
                    "files_present": True,
                    "run_id_meta_vs_sqlite": True,
                    "pwp_effective_rows_match": False,
                },
            }
        },
    }
    summary = summarize_campaign(
        benchmark_report=benchmark_report,
        verify_batch_report=verify_batch_report,
    )
    verify = summary["verify_batch"]
    assert isinstance(verify, dict)
    counts = verify["classification_counts"]
    assert isinstance(counts, dict)
    assert counts["pwp_effective_mismatch"] == 1

