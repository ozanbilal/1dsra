from __future__ import annotations

from pathlib import Path

import dsra1d.benchmark as benchmark_mod
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
        actual = case["actual"]
        assert isinstance(actual, dict)
        assert "delta_u_max" in actual
        assert "sigma_v_eff_min" in actual
        checks = case["checks"]
        assert isinstance(checks, dict)
        assert checks["delta_u_max"]["passed"] is True
        assert checks["sigma_v_eff_min"]["passed"] is True
        constraints = case["constraints"]
        assert isinstance(constraints, dict)
        assert constraints["ru_bounds_ok"] is True
        assert constraints["delta_u_min_ok"] is True
        assert constraints["sigma_v_eff_min_ok"] is True
        assert constraints["pga_bounds_ok"] is True
        assert constraints["ru_monotonic_ok"] is True
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
    assert int(report["skipped"]) >= 3
    assert int(report["ran"]) >= 0
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) >= 3
    assert any(isinstance(c, dict) and c.get("status") == "skipped" for c in cases)


def test_benchmark_opensees_uses_executable_override_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seen: list[str] = []

    def fake_resolve(executable: str):
        seen.append(executable)
        return None

    monkeypatch.setattr(benchmark_mod, "resolve_opensees_executable", fake_resolve)
    monkeypatch.setenv("DSRA1D_OPENSEES_EXE_OVERRIDE", "OVERRIDE_EXE")
    report = benchmark_mod.run_benchmark_suite("opensees-parity", tmp_path)
    assert report["all_passed"] is True
    assert seen
    assert all(v == "OVERRIDE_EXE" for v in seen)


def test_benchmark_core_hyst_passes(tmp_path: Path) -> None:
    report = run_benchmark_suite("core-hyst", tmp_path)
    assert report["all_passed"] is True
    assert int(report["skipped"]) == 0
    assert int(report["ran"]) == 3
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 3
    for case in cases:
        assert isinstance(case, dict)
        assert case["passed"] is True
        actual = case["actual"]
        assert isinstance(actual, dict)
        assert "delta_u_max" in actual
        assert "sigma_v_eff_min" in actual
