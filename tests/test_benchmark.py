from __future__ import annotations

from pathlib import Path

import dsra1d.benchmark as benchmark_mod
from dsra1d.benchmark import run_benchmark_suite


def test_benchmark_core_es_passes(tmp_path: Path) -> None:
    report = run_benchmark_suite("core-es", tmp_path)
    assert report["all_passed"] is True
    assert int(report["skipped"]) == 0
    assert int(report["ran"]) == 3
    assert int(report["total_cases"]) == 3
    assert int(report["skipped_backend"]) == 0
    assert report["backend_ready"] is True
    assert float(report["execution_coverage"]) == 1.0
    backend_missing = report["backend_missing_cases"]
    assert isinstance(backend_missing, list)
    assert len(backend_missing) == 0
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
    assert int(report["skipped"]) >= 6
    assert int(report["skipped_backend"]) >= 6
    assert report["backend_ready"] is False
    assert report["backend_fingerprint_ok"] is False
    assert int(report["ran"]) >= 0
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) >= 6
    assert any(isinstance(c, dict) and c.get("status") == "skipped" for c in cases)
    assert any(
        isinstance(c, dict) and c.get("skip_kind") == "missing_opensees"
        for c in cases
    )
    backend_missing = report["backend_missing_cases"]
    assert isinstance(backend_missing, list)
    assert len(backend_missing) >= 6
    backend_probe = report.get("backend_probe")
    assert isinstance(backend_probe, dict)
    assert "available" in backend_probe
    assert "version" in backend_probe
    assert "binary_sha256" in backend_probe


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


def test_benchmark_opensees_parity_skips_on_probe_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _Probe:
        available = False
        resolved = Path("/usr/bin/opensees")
        version = "probe failed"
        command = ("/usr/bin/opensees", "-version")
        binary_sha256 = "0" * 64

    monkeypatch.setattr(
        benchmark_mod,
        "probe_opensees_executable",
        lambda *_args, **_kwargs: _Probe(),
    )
    monkeypatch.setattr(
        benchmark_mod,
        "resolve_opensees_executable",
        lambda _exe: Path("/usr/bin/opensees"),
    )
    report = benchmark_mod.run_benchmark_suite("opensees-parity", tmp_path)
    assert report["all_passed"] is True
    assert int(report["ran"]) == 0
    assert int(report["skipped_backend"]) >= 6
    assert report["backend_ready"] is False
    assert report["backend_fingerprint_ok"] is False
    cases = report["cases"]
    assert isinstance(cases, list)
    assert all(isinstance(c, dict) and c.get("skip_kind") == "probe_failed" for c in cases)


def test_benchmark_opensees_parity_fingerprint_requirement_applied(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _Probe:
        available = True
        resolved = Path("/usr/bin/opensees")
        version = "OpenSees 3.7.0"
        command = ("/usr/bin/opensees", "-version")
        binary_sha256 = "a" * 64

    monkeypatch.setattr(
        benchmark_mod,
        "probe_opensees_executable",
        lambda *_args, **_kwargs: _Probe(),
    )
    monkeypatch.setattr(
        benchmark_mod,
        "resolve_opensees_executable",
        lambda _exe: Path("/usr/bin/opensees"),
    )
    report = benchmark_mod.run_benchmark_suite(
        "opensees-parity",
        tmp_path,
        require_backend_version_regex=r"OpenSees\\s+3\\.8",
        require_backend_sha256="b" * 64,
    )
    assert report["all_passed"] is True
    assert report["backend_ready"] is False
    assert report["backend_fingerprint_ok"] is False
    assert int(report["ran"]) == 0
    cases = report["cases"]
    assert isinstance(cases, list)
    assert all(isinstance(c, dict) and c.get("skip_kind") == "probe_failed" for c in cases)
    backend_probe = report.get("backend_probe")
    assert isinstance(backend_probe, dict)
    req = backend_probe.get("requirements")
    assert isinstance(req, dict)
    assert req.get("ok") is False
    errors = req.get("errors")
    assert isinstance(errors, list)
    assert len(errors) >= 1


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


def test_benchmark_core_linear_passes(tmp_path: Path) -> None:
    report = run_benchmark_suite("core-linear", tmp_path)
    assert report["all_passed"] is True
    assert int(report["skipped"]) == 0
    assert int(report["ran"]) == 3
    assert int(report["total_cases"]) == 3
    assert int(report["skipped_backend"]) == 0
    assert report["backend_ready"] is True
    assert float(report["execution_coverage"]) == 1.0
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 3
    for case in cases:
        assert isinstance(case, dict)
        assert case["passed"] is True
        actual = case["actual"]
        assert isinstance(actual, dict)
        assert "transfer_abs_max" in actual
        assert "transfer_peak_freq_hz" in actual
        checks = case["checks"]
        assert isinstance(checks, dict)
        assert checks["pga"]["passed"] is True
        assert checks["ru_max"]["passed"] is True
        assert checks["delta_u_max"]["passed"] is True
        assert checks["sigma_v_eff_min"]["passed"] is True
        assert checks["transfer_abs_max"]["passed"] is True
        assert checks["transfer_peak_freq_hz"]["passed"] is True


def test_benchmark_core_eql_passes(tmp_path: Path) -> None:
    report = run_benchmark_suite("core-eql", tmp_path)
    assert report["all_passed"] is True
    assert int(report["skipped"]) == 0
    assert int(report["ran"]) == 3
    assert int(report["total_cases"]) == 3
    assert int(report["skipped_backend"]) == 0
    assert report["backend_ready"] is True
    assert float(report["execution_coverage"]) == 1.0
    cases = report["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 3
    for case in cases:
        assert isinstance(case, dict)
        assert case["passed"] is True
        actual = case["actual"]
        assert isinstance(actual, dict)
        assert "transfer_abs_max" in actual
        assert "transfer_peak_freq_hz" in actual
        checks = case["checks"]
        assert isinstance(checks, dict)
        assert checks["pga"]["passed"] is True
        assert checks["ru_max"]["passed"] is True
        assert checks["delta_u_max"]["passed"] is True
        assert checks["sigma_v_eff_min"]["passed"] is True
        assert checks["transfer_abs_max"]["passed"] is True
        assert checks["transfer_peak_freq_hz"]["passed"] is True
