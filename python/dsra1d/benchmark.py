from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from dsra1d.config import ProjectConfig, load_project_config
from dsra1d.interop.opensees import resolve_opensees_executable
from dsra1d.motion import load_motion
from dsra1d.pipeline import run_analysis
from dsra1d.types import Motion, RunResult


def _load_case_outputs(hdf5_path: Path) -> dict[str, np.ndarray]:
    with h5py.File(hdf5_path, "r") as h5:
        acc = np.array(h5["/signals/surface_acc"], dtype=np.float64)
        ru = np.array(h5["/pwp/ru"], dtype=np.float64)
        delta_u = (
            np.array(h5["/pwp/delta_u"], dtype=np.float64)
            if "/pwp/delta_u" in h5
            else np.array([], dtype=np.float64)
        )
        sigma_v_eff = (
            np.array(h5["/pwp/sigma_v_eff"], dtype=np.float64)
            if "/pwp/sigma_v_eff" in h5
            else np.array([], dtype=np.float64)
        )
        transfer_freq_hz = (
            np.array(h5["/spectra/freq_hz"], dtype=np.float64)
            if "/spectra/freq_hz" in h5
            else np.array([], dtype=np.float64)
        )
        transfer_abs = (
            np.array(h5["/spectra/transfer_abs"], dtype=np.float64)
            if "/spectra/transfer_abs" in h5
            else np.array([], dtype=np.float64)
        )
    return {
        "surface_acc": acc,
        "ru": ru,
        "delta_u": delta_u,
        "sigma_v_eff": sigma_v_eff,
        "transfer_freq_hz": transfer_freq_hz,
        "transfer_abs": transfer_abs,
    }


def _load_psa(hdf5_path: Path) -> np.ndarray:
    with h5py.File(hdf5_path, "r") as h5:
        return np.array(h5["/spectra/psa"], dtype=np.float64)


def _result_signature(series: dict[str, np.ndarray]) -> str:
    hasher = hashlib.sha1()
    for key in sorted(series):
        hasher.update(key.encode("utf-8"))
        hasher.update(series[key].tobytes(order="C"))
    return hasher.hexdigest()


def _build_check_specs(
    expected: dict[str, Any],
    actual_metrics: dict[str, float],
) -> dict[str, dict[str, float]]:
    checks_raw = expected.get("checks")
    if isinstance(checks_raw, dict):
        return {
            name: {
                "expected": float(
                    spec.get(
                        "expected",
                        actual_metrics.get(name, float("nan")),
                    )
                ),
                "abs_tol": float(spec.get("abs_tol", 0.0)),
                "rel_tol": float(spec.get("rel_tol", 0.0)),
            }
            for name, spec in checks_raw.items()
            if isinstance(spec, dict)
        }

    tolerance = float(expected.get("tolerance", 0.0))
    pga_expected_default = actual_metrics.get("pga", float("nan"))
    return {
        "pga": {
            "expected": float(expected.get("pga_expected", pga_expected_default)),
            "abs_tol": tolerance,
            "rel_tol": 0.0,
        },
        "ru_max": {
            "expected": float(
                expected.get("ru_max_expected", actual_metrics.get("ru_max", float("nan")))
            ),
            "abs_tol": tolerance,
            "rel_tol": 0.0,
        },
    }


def _evaluate_metric(
    actual: float,
    expected: float,
    abs_tol: float,
    rel_tol: float,
) -> dict[str, float | bool]:
    diff = abs(actual - expected)
    limit = max(abs_tol, rel_tol * max(abs(expected), 1.0e-12))
    passed = diff <= limit
    return {
        "actual": actual,
        "expected": expected,
        "diff": diff,
        "abs_tol": abs_tol,
        "rel_tol": rel_tol,
        "passed": passed,
    }


def _as_float(value: object, default: float) -> float:
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


def _evaluate_constraints(
    constraints: dict[str, object],
    *,
    ru: np.ndarray,
    delta_u: np.ndarray,
    sigma_v_eff: np.ndarray,
    actual_metrics: dict[str, float],
) -> tuple[dict[str, float | bool], bool]:
    ru_min_limit = _as_float(constraints.get("ru_min", 0.0), 0.0)
    ru_max_limit = _as_float(constraints.get("ru_max", 1.0), 1.0)
    ru_min = float(actual_metrics.get("ru_min", float("nan")))
    ru_max = float(actual_metrics.get("ru_max", float("nan")))
    ru_bounds_ok = (ru_min >= ru_min_limit) and (ru_max <= ru_max_limit)

    delta_u_min_limit = _as_float(constraints.get("delta_u_min", float("-inf")), float("-inf"))
    sigma_v_eff_min_limit = _as_float(
        constraints.get("sigma_v_eff_min", float("-inf")),
        float("-inf"),
    )
    pga_min_limit = _as_float(constraints.get("pga_min", float("-inf")), float("-inf"))
    pga_max_limit = _as_float(constraints.get("pga_max", float("inf")), float("inf"))

    delta_u_min_actual = float(np.min(delta_u)) if delta_u.size > 0 else float("nan")
    sigma_v_eff_min_actual = (
        float(np.min(sigma_v_eff)) if sigma_v_eff.size > 0 else float("nan")
    )
    pga_actual = float(actual_metrics.get("pga", float("nan")))

    delta_u_min_ok = (
        True
        if delta_u.size == 0 and np.isneginf(delta_u_min_limit)
        else (delta_u_min_actual >= delta_u_min_limit)
    )
    sigma_v_eff_min_ok = (
        True
        if sigma_v_eff.size == 0 and np.isneginf(sigma_v_eff_min_limit)
        else (sigma_v_eff_min_actual >= sigma_v_eff_min_limit)
    )
    pga_bounds_ok = (pga_actual >= pga_min_limit) and (pga_actual <= pga_max_limit)

    monotonic_requested = bool(constraints.get("ru_monotonic_nondecreasing", False))
    if monotonic_requested and ru.size > 1:
        ru_mono_ok = bool(np.all(np.diff(ru) >= -1.0e-10))
    else:
        ru_mono_ok = True

    result: dict[str, float | bool] = {
        "ru_min_limit": ru_min_limit,
        "ru_max_limit": ru_max_limit,
        "ru_bounds_ok": ru_bounds_ok,
        "delta_u_min_limit": delta_u_min_limit,
        "delta_u_min_actual": delta_u_min_actual,
        "delta_u_min_ok": delta_u_min_ok,
        "sigma_v_eff_min_limit": sigma_v_eff_min_limit,
        "sigma_v_eff_min_actual": sigma_v_eff_min_actual,
        "sigma_v_eff_min_ok": sigma_v_eff_min_ok,
        "pga_min_limit": pga_min_limit,
        "pga_max_limit": pga_max_limit,
        "pga_bounds_ok": pga_bounds_ok,
        "ru_monotonic_requested": monotonic_requested,
        "ru_monotonic_ok": ru_mono_ok,
    }
    all_ok = (
        ru_bounds_ok
        and delta_u_min_ok
        and sigma_v_eff_min_ok
        and pga_bounds_ok
        and ru_mono_ok
    )
    return result, all_ok


def _run_case(
    cfg: ProjectConfig,
    motion_path: Path,
    output_dir: Path,
) -> tuple[RunResult, Motion]:
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
    return run_analysis(cfg, motion, output_dir), motion


def _evaluate_dt_sensitivity(
    cfg: ProjectConfig,
    motion_path: Path,
    output_dir: Path,
    base_hdf5_path: Path,
    threshold: float,
) -> dict[str, float | bool | str]:
    base_psa = _load_psa(base_hdf5_path)
    cfg_half = cfg.model_copy(deep=True)
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    cfg_half.analysis.dt = dt / 2.0

    half_run, _ = _run_case(cfg_half, motion_path, output_dir)
    half_psa = _load_psa(half_run.hdf5_path)

    if base_psa.shape != half_psa.shape:
        return {
            "enabled": True,
            "passed": False,
            "reason": "shape_mismatch",
            "threshold": threshold,
            "max_relative_psa_diff": float("inf"),
            "mean_relative_psa_diff": float("inf"),
            "base_dt": dt,
            "half_dt": cfg_half.analysis.dt,
            "half_run_id": half_run.run_id,
        }

    denom = np.maximum(np.abs(half_psa), 1.0e-10)
    rel = np.abs(base_psa - half_psa) / denom
    max_rel = float(np.max(rel))
    mean_rel = float(np.mean(rel))
    passed = max_rel <= threshold
    return {
        "enabled": True,
        "passed": passed,
        "threshold": threshold,
        "max_relative_psa_diff": max_rel,
        "mean_relative_psa_diff": mean_rel,
        "base_dt": dt,
        "half_dt": cfg_half.analysis.dt,
        "half_run_id": half_run.run_id,
    }


def run_benchmark_suite(
    suite: str,
    output_dir: Path,
) -> dict[str, object]:
    if suite not in {"core-es", "core-hyst", "core-linear", "core-eql", "opensees-parity"}:
        raise ValueError(f"Unknown suite: {suite}")

    repo_root = Path(__file__).resolve().parents[2]
    suite_dir = repo_root / "benchmarks" / suite
    cases_path = suite_dir / "cases" / "case_list.json"
    golden_path = suite_dir / "golden" / "golden_metrics.json"

    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    golden = json.loads(golden_path.read_text(encoding="utf-8"))

    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "suite": suite,
        "cases": [],
        "all_passed": True,
    }
    skipped_count = 0
    skipped_backend_count = 0
    ran_count = 0
    total_cases = len(cases)
    backend_missing_cases: list[str] = []

    for case in cases:
        cfg = load_project_config(suite_dir / case["config"])
        exe_override = os.getenv("DSRA1D_OPENSEES_EXE_OVERRIDE", "").strip()
        if exe_override and cfg.analysis.solver_backend == "opensees":
            cfg.opensees.executable = exe_override
        motion_path = suite_dir / case["motion"]

        if cfg.analysis.solver_backend == "opensees":
            resolved = resolve_opensees_executable(cfg.opensees.executable)
            if resolved is None:
                report_case = {
                    "name": case["name"],
                    "status": "skipped",
                    "reason": f"OpenSees executable not found: {cfg.opensees.executable}",
                    "passed": True,
                    "skip_kind": "missing_opensees",
                }
                cast_cases = report["cases"]
                if isinstance(cast_cases, list):
                    cast_cases.append(report_case)
                skipped_count += 1
                skipped_backend_count += 1
                backend_missing_cases.append(str(case.get("name", "unknown")))
                continue

        run_result, motion = _run_case(cfg, motion_path, output_dir)
        ran_count += 1
        series = _load_case_outputs(run_result.hdf5_path)
        acc = series["surface_acc"]
        ru = series["ru"]
        delta_u = series["delta_u"]
        sigma_v_eff = series["sigma_v_eff"]
        transfer_freq_hz = series["transfer_freq_hz"]
        transfer_abs = series["transfer_abs"]
        pga = float(np.max(np.abs(acc)))
        ru_max = float(np.max(ru))
        ru_min = float(np.min(ru))
        delta_u_max = float(np.max(delta_u)) if delta_u.size > 0 else float("nan")
        sigma_v_eff_min = float(np.min(sigma_v_eff)) if sigma_v_eff.size > 0 else float("nan")
        transfer_abs_max = float(np.max(transfer_abs)) if transfer_abs.size > 0 else float("nan")
        if transfer_abs.size > 1 and transfer_freq_hz.size == transfer_abs.size:
            idx_peak = int(np.argmax(transfer_abs))
            transfer_peak_freq_hz = float(transfer_freq_hz[idx_peak])
        else:
            transfer_peak_freq_hz = float("nan")
        actual_metrics = {
            "pga": pga,
            "ru_max": ru_max,
            "ru_min": ru_min,
            "delta_u_max": delta_u_max,
            "sigma_v_eff_min": sigma_v_eff_min,
            "transfer_abs_max": transfer_abs_max,
            "transfer_peak_freq_hz": transfer_peak_freq_hz,
        }
        signature = _result_signature(series)

        expected = golden.get(case["name"], {})
        checks = _build_check_specs(expected, actual_metrics=actual_metrics)
        check_results: dict[str, dict[str, float | bool]] = {}
        all_checks_ok = True
        for name, spec in checks.items():
            actual = float(actual_metrics.get(name, float("nan")))
            if np.isnan(actual):
                result = {
                    "actual": actual,
                    "expected": spec["expected"],
                    "diff": float("inf"),
                    "abs_tol": spec["abs_tol"],
                    "rel_tol": spec["rel_tol"],
                    "passed": False,
                }
            else:
                result = _evaluate_metric(
                    actual=actual,
                    expected=spec["expected"],
                    abs_tol=spec["abs_tol"],
                    rel_tol=spec["rel_tol"],
                )
            check_results[name] = result
            all_checks_ok = all_checks_ok and bool(result["passed"])

        constraints = expected.get("constraints", {})
        if not isinstance(constraints, dict):
            constraints = {}
        constraint_results, constraints_ok = _evaluate_constraints(
            constraints,
            ru=ru,
            delta_u=delta_u,
            sigma_v_eff=sigma_v_eff,
            actual_metrics=actual_metrics,
        )

        deterministic = bool(expected.get("deterministic", False))
        deterministic_ok = True
        signature_repeat = signature
        if deterministic:
            rerun = run_analysis(cfg, motion, output_dir)
            series2 = _load_case_outputs(rerun.hdf5_path)
            signature_repeat = _result_signature(series2)
            deterministic_ok = signature == signature_repeat

        dt_spec = expected.get("dt_sensitivity")
        dt_result: dict[str, float | bool | str]
        if isinstance(dt_spec, dict):
            threshold = float(dt_spec.get("threshold", 1.0))
            dt_result = _evaluate_dt_sensitivity(
                cfg=cfg,
                motion_path=motion_path,
                output_dir=output_dir,
                base_hdf5_path=run_result.hdf5_path,
                threshold=threshold,
            )
        else:
            dt_result = {"enabled": False, "passed": True}

        case_passed = (
            run_result.status == "ok"
            and all_checks_ok
            and constraints_ok
            and deterministic_ok
            and bool(dt_result["passed"])
        )

        report_case = {
            "name": case["name"],
            "run_id": run_result.run_id,
            "status": run_result.status,
            "actual": actual_metrics,
            "expected": expected,
            "checks": check_results,
            "constraints": constraint_results,
            "deterministic": {
                "enabled": deterministic,
                "ok": deterministic_ok,
                "signature": signature,
                "signature_repeat": signature_repeat,
            },
            "dt_sensitivity": dt_result,
            "passed": case_passed and run_result.status == "ok",
        }
        cast_cases = report["cases"]
        if isinstance(cast_cases, list):
            cast_cases.append(report_case)
        if not report_case["passed"]:
            report["all_passed"] = False

    report["skipped"] = skipped_count
    report["ran"] = ran_count
    report["total_cases"] = total_cases
    report["skipped_backend"] = skipped_backend_count
    report["backend_ready"] = skipped_backend_count == 0
    report["execution_coverage"] = (
        float(ran_count) / float(total_cases)
        if total_cases > 0
        else 0.0
    )
    report["backend_missing_cases"] = backend_missing_cases
    return report
