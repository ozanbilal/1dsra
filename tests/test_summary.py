from __future__ import annotations

from dsra1d.post import render_summary_markdown, summarize_campaign


def test_summarize_campaign_benchmark_only() -> None:
    benchmark_report: dict[str, object] = {
        "suite": "opensees-parity",
        "all_passed": False,
        "skipped": 1,
        "ran": 2,
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
    counts = benchmark["classification_counts"]
    assert isinstance(counts, dict)
    assert counts["passed"] == 1
    assert counts["skipped_missing_executable"] == 1
    assert counts["metric_mismatch"] == 1

    nonpass = benchmark["failed_or_nonpass_cases"]
    assert isinstance(nonpass, list)
    assert sorted(nonpass) == ["case_metric_fail", "case_skip"]


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


def test_render_summary_markdown_contains_key_sections() -> None:
    summary: dict[str, object] = {
        "generated_utc": "2026-03-01T00:00:00+00:00",
        "suite": "core-es",
        "benchmark": {
            "all_passed": True,
            "total_cases": 2,
            "ran": 2,
            "skipped": 0,
            "classification_counts": {"passed": 2},
        },
        "verify_batch": {
            "ok": True,
            "total_runs": 2,
            "failed_runs": 0,
            "classification_counts": {"passed": 2},
        },
    }
    md = render_summary_markdown(summary)
    assert "# 1DSRA Campaign Summary" in md
    assert "Suite: `core-es`" in md
    assert "Benchmark classifications" in md
    assert "Verify classifications" in md
