from __future__ import annotations

from pathlib import Path

from dsra1d.benchmark import run_benchmark_suite


def test_benchmark_core_es_passes(tmp_path: Path) -> None:
    report = run_benchmark_suite("core-es", tmp_path)
    assert report["all_passed"] is True
    assert int(report["skipped"]) == 0
    assert int(report["ran"]) == 3
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 3
    for case in cases:
        assert isinstance(case, dict)
        assert case["passed"] is True
        constraints = case["constraints"]
        assert isinstance(constraints, dict)
        assert constraints["ru_bounds_ok"] is True
        deterministic = case["deterministic"]
        assert isinstance(deterministic, dict)
        assert deterministic["ok"] is True
        dt_sensitivity = case["dt_sensitivity"]
        assert isinstance(dt_sensitivity, dict)
        assert dt_sensitivity["enabled"] is True
        assert dt_sensitivity["passed"] is True


def test_benchmark_opensees_parity_skips_without_binary(tmp_path: Path) -> None:
    report = run_benchmark_suite("opensees-parity", tmp_path)
    assert report["all_passed"] is True
    assert int(report["skipped"]) >= 1
    assert int(report["ran"]) >= 0
    cases = report["cases"]
    assert isinstance(cases, list)
    assert any(isinstance(c, dict) and c.get("status") == "skipped" for c in cases)
