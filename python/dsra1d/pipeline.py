from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from dsra1d.config import MaterialType, ProjectConfig, load_project_config
from dsra1d.interop.opensees import (
    OpenSeesExecutionError,
    build_layer_slices,
    probe_opensees_executable,
    read_pwp_raw,
    read_ru,
    read_surface_acc_with_time,
    render_tcl,
    run_opensees,
    validate_tcl_script,
)
from dsra1d.linear import solve_equivalent_linear_sh_response, solve_linear_sh_response
from dsra1d.materials import layer_hysteretic_proxy
from dsra1d.motion import load_motion, preprocess_motion
from dsra1d.newmark_nonlinear import (
    solve_nonlinear_implicit_newmark,
    solve_nonlinear_newmark,
)
from dsra1d.nonlinear import solve_nonlinear_sh_response
from dsra1d.post import compute_spectra, compute_transfer_function
from dsra1d.store import ResultStore, write_hdf5, write_sqlite
from dsra1d.store import load_result as _load_result
from dsra1d.types import BatchResult, Motion, RunResult


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if np.isfinite(value):
            return int(value)
        return default
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _stable_run_id(config: ProjectConfig, motion: Motion) -> str:
    config_payload = json.dumps(
        config.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
    )
    motion_digest = hashlib.sha1(
        np.asarray(motion.acc, dtype=np.float64).tobytes(order="C")
    ).hexdigest()
    payload = f"{config_payload}|{motion.dt:.12e}|{motion.acc.size}|{motion_digest}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"run-{digest}"


def _stable_motion_key(motion: Motion) -> tuple[float, str, str]:
    acc = np.asarray(motion.acc, dtype=np.float64)
    digest = hashlib.sha1(acc.tobytes(order="C")).hexdigest()
    return (round(float(motion.dt), 12), motion.unit, digest)


def _clone_run_result(result: RunResult) -> RunResult:
    return RunResult(
        run_id=result.run_id,
        output_dir=result.output_dir,
        hdf5_path=result.hdf5_path,
        sqlite_path=result.sqlite_path,
        status=result.status,
        message=result.message,
    )


def _write_mock_outputs(
    run_dir: Path,
    config: ProjectConfig,
    acc: np.ndarray,
    dt: float,
) -> None:
    has_hysteretic_total_stress = any(
        layer.material in {MaterialType.MKZ, MaterialType.GQH}
        for layer in config.profile.layers
    )
    if not has_hysteretic_total_stress:
        # Preserve benchmark-stable behavior for existing effective-stress mock suites.
        surface = 0.8 * acc
        np.savetxt(run_dir / "surface_acc.out", surface)
        ru_t = np.arange(surface.size, dtype=np.float64) * dt
        ru = np.clip(np.linspace(0.0, 0.3, surface.size), 0.0, 1.0)
        np.savetxt(run_dir / "pwp_ru.out", np.column_stack([ru_t, ru]))
        return

    pga = float(np.max(np.abs(acc))) if acc.size > 0 else 0.0
    strain_proxy = float(np.clip(pga / (9.81 * 200.0), 1.0e-6, 0.02))
    total_thickness = sum(layer.thickness_m for layer in config.profile.layers)

    weighted_reduction = 0.0
    weighted_damping = 0.0
    weighted_ru_target = 0.0
    for layer in config.profile.layers:
        weight = (
            float(layer.thickness_m / total_thickness) if total_thickness > 0.0 else 0.0
        )
        proxy = layer_hysteretic_proxy(
            material=layer.material,
            material_params=layer.material_params,
            strain_proxy=strain_proxy,
        )
        weighted_reduction += weight * proxy.reduction
        weighted_damping += weight * proxy.damping
        weighted_ru_target += weight * proxy.ru_target

    mean_reduction = float(np.clip(weighted_reduction, 0.1, 1.0))
    mean_damping = float(np.clip(weighted_damping, 0.0, 0.5))
    mean_ru_target = float(np.clip(weighted_ru_target, 0.0, 1.0))

    amplification = float(np.clip(0.25 + 1.10 * mean_reduction - 0.80 * mean_damping, 0.20, 1.20))
    surface = amplification * acc
    np.savetxt(run_dir / "surface_acc.out", surface)
    ru_t = np.arange(surface.size, dtype=np.float64) * dt
    ru = np.clip(np.linspace(0.0, mean_ru_target, surface.size), 0.0, 1.0)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([ru_t, ru]))


def _write_linear_outputs(
    run_dir: Path,
    config: ProjectConfig,
    motion: Motion,
) -> None:
    t, surface = solve_linear_sh_response(config, motion)
    if not np.all(np.isfinite(surface)):
        raise ValueError("Linear solver produced non-finite surface acceleration.")
    np.savetxt(run_dir / "surface_acc.out", np.column_stack([t, surface]))
    ru = np.zeros_like(t)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([t, ru]))


def _write_nonlinear_outputs(
    run_dir: Path,
    config: ProjectConfig,
    motion: Motion,
) -> None:
    if config.analysis.integration_scheme == "newmark":
        t, surface = solve_nonlinear_implicit_newmark(config, motion)
    elif config.analysis.integration_scheme == "verlet":
        t, surface = solve_nonlinear_newmark(config, motion)
    else:
        t, surface = solve_nonlinear_sh_response(
            config,
            motion,
            substeps=int(config.analysis.nonlinear_substeps),
        )
    if not np.all(np.isfinite(surface)):
        raise ValueError(
            "Nonlinear solver produced non-finite surface acceleration. "
            "Try a smaller dt or inspect constitutive/boundary settings."
        )
    np.savetxt(run_dir / "surface_acc.out", np.column_stack([t, surface]))
    ru = np.zeros_like(t)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([t, ru]))


def _write_eql_outputs(
    run_dir: Path,
    config: ProjectConfig,
    motion: Motion,
) -> tuple[Path, dict[str, object]]:
    response = solve_equivalent_linear_sh_response(config, motion)
    t = response.response.time
    surface = response.response.surface_acc
    if not np.all(np.isfinite(surface)):
        raise ValueError("Equivalent-linear solver produced non-finite surface acceleration.")
    np.savetxt(run_dir / "surface_acc.out", np.column_stack([t, surface]))
    ru = np.zeros_like(t)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([t, ru]))

    summary: dict[str, object] = {
        "iterations": response.iterations,
        "converged": response.converged,
        "max_change_history": response.max_change_history,
        "layer_vs_m_s": {int(k): float(v) for k, v in response.layer_vs_m_s.items()},
        "layer_damping": {int(k): float(v) for k, v in response.layer_damping.items()},
        "layer_gamma_eff": {int(k): float(v) for k, v in response.layer_gamma_eff.items()},
        "layer_max_abs_strain": {
            int(k): float(v) for k, v in response.response.layer_max_abs_strain.items()
        },
    }
    summary_path = run_dir / "eql_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path, summary


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _reference_sigma_v(config: ProjectConfig) -> float:
    total_depth = sum(layer.thickness_m for layer in config.profile.layers)
    if total_depth <= 0.0:
        return 1.0e-3
    gamma_depth_sum = sum(
        layer.unit_weight_kn_m3 * layer.thickness_m
        for layer in config.profile.layers
    )
    avg_gamma = gamma_depth_sum / total_depth
    return max(avg_gamma * total_depth * 0.5, 1.0e-3)


def _estimate_dt_from_axis(axis: np.ndarray, fallback: float) -> float:
    if axis.size > 1:
        dt = float(np.median(np.diff(axis)))
        if np.isfinite(dt) and dt > 0.0:
            return dt
    return float(fallback)


def _has_min_samples(path: Path, min_samples: int = 2) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        arr = np.loadtxt(path, ndmin=2)
    except Exception:
        return False
    if arr.ndim == 1:
        return int(arr.size) >= min_samples
    return int(arr.shape[0]) >= min_samples


def _validate_opensees_run_outputs(run_dir: Path) -> None:
    missing: list[str] = []
    surface_path = run_dir / "surface_acc.out"
    ru_path = run_dir / "pwp_ru.out"
    if not _has_min_samples(surface_path, min_samples=2):
        missing.append(surface_path.name)
    if not _has_min_samples(ru_path, min_samples=2):
        missing.append(ru_path.name)
    if missing:
        raise OpenSeesExecutionError(
            "OpenSees finished without required output files: "
            + ", ".join(missing)
        )


def _write_surface_csv(path: Path, time: np.ndarray, acc: np.ndarray, dt_s: float) -> None:
    n = int(min(time.size, acc.size))
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("time_s,acc_m_s2,delta_t_s\n")
        for i in range(n):
            f.write(f"{float(time[i]):.8f},{float(acc[i]):.10e},{float(dt_s):.8e}\n")


def _write_pwp_effective_csv(
    path: Path,
    ru_time: np.ndarray,
    ru: np.ndarray,
    delta_u: np.ndarray,
    sigma_v_eff: np.ndarray,
    dt_s: float,
) -> None:
    n = int(min(ru_time.size, ru.size))
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("time_s,ru,delta_u,sigma_v_eff,delta_t_s\n")
        for i in range(n):
            du = float(delta_u[i]) if i < delta_u.size else float("nan")
            sve = float(sigma_v_eff[i]) if i < sigma_v_eff.size else float("nan")
            f.write(
            f"{float(ru_time[i]):.8f},{float(ru[i]):.10e},{du:.10e},{sve:.10e},{float(dt_s):.8e}\n"
            )


def _summarize_opensees_failure(exc: OpenSeesExecutionError) -> str:
    raw = str(exc)
    stderr = (exc.stderr or "").strip()
    text = f"{raw}\n{stderr}"
    if "couldn't read file" in text:
        return (
            "OpenSees could not read generated Tcl/motion files. "
            "Check run directory permissions and path encoding."
        )
    if "Vector::operator/(double fact)" in text and (
        "PM4Sand" in text or "PM4Silt" in text
    ):
        return (
            "OpenSees PM4 model diverged at an early step (divide-by-zero). "
            "This usually indicates PM4 calibration/initial stress or staging mismatch. "
            "For stable runs now, use native nonlinear/eql backend, or simplify to elastic "
            "OpenSees until PM4 calibration is completed."
        )
    if "failed to converge" in text or "analyze failed" in text:
        return (
            "OpenSees analysis did not converge. "
            "Try smaller dt, more robust algorithm/test settings, and verify material parameters."
        )
    return raw


def _count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _opensees_log_diagnostics(stdout: str, stderr: str) -> dict[str, object]:
    log = f"{stdout}\n{stderr}"
    warning_count = _count_pattern(log, r"\bWARNING\b")
    failed_converge_count = _count_pattern(log, r"failed to converge")
    analyze_failed_count = _count_pattern(log, r"analyze failed")
    divide_by_zero_count = _count_pattern(log, r"divide-by-zero")
    init_count = _count_pattern(log, r"\binitialize\b")
    dynamic_fallback_failed = (
        "dynamic analysis failed after fallback attempt" in log.lower()
    )
    severity = "ok"
    if divide_by_zero_count > 0:
        severity = "critical"
    elif failed_converge_count > 0 or analyze_failed_count > 0:
        severity = "warning"
    return {
        "source": "opensees_logs",
        "severity": severity,
        "warning_count": int(warning_count),
        "failed_converge_count": int(failed_converge_count),
        "analyze_failed_count": int(analyze_failed_count),
        "divide_by_zero_count": int(divide_by_zero_count),
        "pm4_initialize_count": int(init_count),
        "dynamic_fallback_failed": bool(dynamic_fallback_failed),
    }


def _format_opensees_diag_note(diag: dict[str, object]) -> str:
    failed_conv = _as_int(diag.get("failed_converge_count", 0))
    analyze_failed = _as_int(diag.get("analyze_failed_count", 0))
    warning_count = _as_int(diag.get("warning_count", 0))
    return (
        "completed with solver warnings "
        f"(failed_to_converge={failed_conv}, "
        f"analyze_failed={analyze_failed}, warnings={warning_count})"
    )


def _adaptive_opensees_timeout_s(
    configured_timeout_s: int,
    *,
    dt_s: float,
    n_samples: int,
) -> int:
    base = int(max(configured_timeout_s, 1))
    if n_samples <= 1 or not np.isfinite(dt_s) or dt_s <= 0.0:
        return base
    duration_s = float((n_samples - 1) * dt_s)
    duration_budget = int(np.ceil(60.0 + (3.0 * duration_s)))
    sample_budget = int(np.ceil(120.0 + (0.02 * n_samples)))
    adaptive = max(base, duration_budget, sample_budget, 180)
    return int(min(adaptive, 3600))


def _opensees_output_coverage_ratio(
    run_dir: Path,
    *,
    expected_samples: int,
    dt_default: float,
) -> float:
    if expected_samples <= 0:
        return 0.0
    surface_t, surface_acc = read_surface_acc_with_time(
        run_dir / "surface_acc.out",
        dt_default=dt_default,
    )
    ru_t, ru = read_ru(run_dir / "pwp_ru.out")
    n_surface = int(min(surface_t.size, surface_acc.size))
    n_ru = int(min(ru_t.size, ru.size))
    return float(min(n_surface / expected_samples, n_ru / expected_samples))


def run_analysis(
    config: ProjectConfig,
    motion: Motion,
    output_dir: str | Path = "out",
) -> RunResult:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    run_id = _stable_run_id(config, motion)
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[tuple[str, str]] = []
    config_snapshot_path = run_dir / "config_snapshot.json"
    config_snapshot_path.write_text(
        json.dumps(
            config.model_dump(mode="json", by_alias=True),
            indent=2,
        ),
        encoding="utf-8",
    )
    artifacts.append(("config_snapshot", str(config_snapshot_path)))

    processed = preprocess_motion(motion, config.motion)
    # Mesh summary is computed early to validate profile/f_max discretization assumptions.
    slices = build_layer_slices(config)
    motion_file = run_dir / "motion_processed.csv"
    np.savetxt(motion_file, processed.acc, delimiter=",")
    artifacts.append(("motion_processed", str(motion_file)))

    # Use run-local relative paths so OpenSees execution is independent of caller cwd.
    tcl = render_tcl(
        config,
        motion_file=Path(motion_file.name),
        output_dir=Path("."),
    )
    validate_tcl_script(tcl)
    tcl_path = run_dir / "model.tcl"
    tcl_path.write_text(tcl, encoding="utf-8")
    artifacts.append(("model_tcl", str(tcl_path)))

    status = "ok"
    message = "completed"
    opensees_command: list[str] = []
    opensees_stdout_log: Path | None = None
    opensees_stderr_log: Path | None = None
    opensees_probe: dict[str, object] | None = None
    opensees_diagnostics: dict[str, object] | None = None
    eql_summary: dict[str, object] | None = None
    configured_timeout_s = int(max(config.analysis.timeout_s, 1))
    effective_timeout_s = configured_timeout_s
    timeout_recovered = False
    timeout_recovered_coverage = 0.0

    if config.analysis.solver_backend == "opensees":
        effective_timeout_s = _adaptive_opensees_timeout_s(
            configured_timeout_s,
            dt_s=float(processed.dt),
            n_samples=int(processed.acc.size),
        )
        probe = probe_opensees_executable(
            config.opensees.executable,
            extra_args=config.opensees.extra_args,
        )
        opensees_probe = {
            "available": probe.available,
            "assumed_available": probe.assumed_available,
            "resolved": str(probe.resolved) if probe.resolved is not None else "",
            "version": probe.version,
            "command": probe.command,
            "binary_sha256": probe.binary_sha256,
        }
        probe_path = run_dir / "opensees_backend_probe.json"
        probe_path.write_text(json.dumps(opensees_probe, indent=2), encoding="utf-8")
        artifacts.append(("opensees_backend_probe", str(probe_path)))

        attempt = 0
        while True:
            attempt += 1
            try:
                run_output = run_opensees(
                    executable=config.opensees.executable,
                    tcl_file=Path(tcl_path.name),
                    cwd=run_dir,
                    timeout_s=effective_timeout_s,
                    extra_args=config.opensees.extra_args,
                )
                opensees_command = run_output.command
                opensees_stdout_log = run_dir / "opensees_stdout.log"
                opensees_stderr_log = run_dir / "opensees_stderr.log"
                opensees_stdout_log.write_text(run_output.stdout, encoding="utf-8")
                opensees_stderr_log.write_text(run_output.stderr, encoding="utf-8")
                opensees_diagnostics = _opensees_log_diagnostics(
                    run_output.stdout,
                    run_output.stderr,
                )
                diagnostics_path = run_dir / "opensees_diagnostics.json"
                diagnostics_path.write_text(
                    json.dumps(opensees_diagnostics, indent=2),
                    encoding="utf-8",
                )
                artifacts.append(("opensees_diagnostics", str(diagnostics_path)))
                _validate_opensees_run_outputs(run_dir)
                break
            except OpenSeesExecutionError as exc:
                opensees_command = exc.command
                if exc.stdout:
                    opensees_stdout_log = run_dir / "opensees_stdout.log"
                    opensees_stdout_log.write_text(exc.stdout, encoding="utf-8")
                if exc.stderr:
                    opensees_stderr_log = run_dir / "opensees_stderr.log"
                    opensees_stderr_log.write_text(exc.stderr, encoding="utf-8")
                if attempt > config.analysis.retries:
                    if "timed out after" in str(exc).lower():
                        coverage = _opensees_output_coverage_ratio(
                            run_dir,
                            expected_samples=int(processed.acc.size),
                            dt_default=float(processed.dt),
                        )
                        if coverage >= 0.85:
                            timeout_recovered = True
                            timeout_recovered_coverage = coverage
                            status = "ok"
                            message = (
                                "OpenSees exceeded timeout budget "
                                f"({effective_timeout_s}s) but output files were recovered "
                                f"(coverage={coverage:.3f})."
                            )
                            break
                    status = "error"
                    message = _summarize_opensees_failure(exc)
                    # keep deterministic output shape for downstream writers
                    _write_mock_outputs(
                        run_dir=run_dir,
                        config=config,
                        acc=processed.acc,
                        dt=processed.dt,
                    )
                    break
    elif config.analysis.solver_backend == "linear":
        _write_linear_outputs(
            run_dir=run_dir,
            config=config,
            motion=processed,
        )
    elif config.analysis.solver_backend == "nonlinear":
        _write_nonlinear_outputs(
            run_dir=run_dir,
            config=config,
            motion=processed,
        )
    elif config.analysis.solver_backend == "eql":
        eql_summary_path, eql_summary = _write_eql_outputs(
            run_dir=run_dir,
            config=config,
            motion=processed,
        )
        artifacts.append(("eql_summary", str(eql_summary_path)))
    else:
        _write_mock_outputs(
            run_dir=run_dir,
            config=config,
            acc=processed.acc,
            dt=processed.dt,
        )

    surface_t, acc_surface = read_surface_acc_with_time(
        run_dir / "surface_acc.out",
        dt_default=processed.dt,
    )
    ru_t, ru = read_ru(run_dir / "pwp_ru.out")
    sigma_v_ref = _reference_sigma_v(config)
    pwp_raw_t, pwp_raw = read_pwp_raw(run_dir / "pwp_raw.out")
    if (
        pwp_raw.size == ru.size
        and pwp_raw_t.size == ru_t.size
        and np.allclose(pwp_raw_t, ru_t, rtol=1.0e-6, atol=1.0e-9)
        and np.all(np.isfinite(pwp_raw))
    ):
        delta_u = np.asarray(pwp_raw, dtype=np.float64)
    else:
        delta_u = np.asarray(ru * sigma_v_ref, dtype=np.float64)
    sigma_v_eff = np.asarray(sigma_v_ref - delta_u, dtype=np.float64)

    dt_series = _estimate_dt_from_axis(surface_t, fallback=processed.dt)
    spectra = compute_spectra(acc_surface, dt=dt_series, damping=0.05)
    transfer_freq_hz, transfer_abs = compute_transfer_function(
        processed.acc,
        acc_surface,
        dt_series,
    )
    time = surface_t

    surface_csv = run_dir / "surface_acc.csv"
    _write_surface_csv(surface_csv, time=time, acc=acc_surface, dt_s=dt_series)
    pwp_effective_csv = run_dir / "pwp_effective.csv"
    _write_pwp_effective_csv(
        pwp_effective_csv,
        ru_time=ru_t,
        ru=ru,
        delta_u=delta_u,
        sigma_v_eff=sigma_v_eff,
        dt_s=dt_series,
    )

    surface_out = run_dir / "surface_acc.out"
    pwp_out = run_dir / "pwp_ru.out"
    artifacts.append(("results_hdf5", str(run_dir / "results.h5")))
    artifacts.append(("results_sqlite", str(run_dir / "results.sqlite")))
    if surface_out.exists():
        artifacts.append(("surface_acc", str(surface_out)))
    if surface_csv.exists():
        artifacts.append(("surface_acc_csv", str(surface_csv)))
    if pwp_out.exists():
        artifacts.append(("pwp_ru", str(pwp_out)))
    if pwp_effective_csv.exists():
        artifacts.append(("pwp_effective_csv", str(pwp_effective_csv)))
    pwp_raw_out = run_dir / "pwp_raw.out"
    if pwp_raw_out.exists():
        artifacts.append(("pwp_raw", str(pwp_raw_out)))
    if opensees_stdout_log and opensees_stdout_log.exists():
        artifacts.append(("opensees_stdout", str(opensees_stdout_log)))
    if opensees_stderr_log and opensees_stderr_log.exists():
        artifacts.append(("opensees_stderr", str(opensees_stderr_log)))
    if (
        status == "ok"
        and opensees_diagnostics is not None
        and str(opensees_diagnostics.get("severity", "ok")) != "ok"
    ):
        message = _format_opensees_diag_note(opensees_diagnostics)

    h5_path = run_dir / "results.h5"
    sqlite_path = run_dir / "results.sqlite"

    if config.output.write_hdf5:
        write_hdf5(
            path=h5_path,
            time=time,
            dt_s=dt_series,
            acc_surface=acc_surface,
            ru_time=ru_t,
            acc_input=np.asarray(processed.acc, dtype=np.float64),
            ru=ru,
            delta_u=delta_u,
            sigma_v_ref=sigma_v_ref,
            sigma_v_eff=sigma_v_eff,
            spectra=spectra,
            transfer_freq_hz=transfer_freq_hz,
            transfer_abs=transfer_abs,
            mesh_layer_idx=np.array([s.index for s in slices], dtype=np.int64),
            mesh_z_top=np.array([s.z_top_m for s in slices], dtype=np.float64),
            mesh_z_bot=np.array([s.z_bot_m for s in slices], dtype=np.float64),
            mesh_dz=np.array([s.dz_m for s in slices], dtype=np.float64),
            mesh_n_sub=np.array([s.n_sublayers for s in slices], dtype=np.int64),
            eql_summary=eql_summary,
        )
    hdf5_checksums: list[tuple[str, str]] = []
    if config.output.write_hdf5 and h5_path.exists():
        hdf5_checksums.append(("results.h5", _sha256_file(h5_path)))

    if config.output.write_sqlite:
        write_sqlite(
            sqlite_path,
            run_id,
            config,
            status=status,
            message=message,
            dt=dt_series,
            acc_surface=acc_surface,
            spectra_data=spectra,
            transfer_freq_hz=transfer_freq_hz,
            transfer_abs=transfer_abs,
            ru_time=ru_t,
            ru=ru,
            delta_u=delta_u,
            sigma_v_ref=sigma_v_ref,
            sigma_v_eff=sigma_v_eff,
            mesh_slices=slices,
            eql_summary=eql_summary,
            artifacts=artifacts,
            checksums=hdf5_checksums,
        )

    checksum_map = {name: digest for name, digest in hdf5_checksums}
    if config.output.write_sqlite and sqlite_path.exists():
        sqlite_hash = _sha256_file(sqlite_path)
        checksum_map["results.sqlite"] = sqlite_hash

    run_meta_path = run_dir / "run_meta.json"
    run_meta = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "solver_backend": config.analysis.solver_backend,
        "nonlinear_substeps": int(config.analysis.nonlinear_substeps),
        "timeout_s_configured": configured_timeout_s,
        "timeout_s_effective": effective_timeout_s,
        "dt_s": float(dt_series),
        "delta_t_s": float(dt_series),
        "status": status,
        "message": message,
        "opensees_command": opensees_command,
        "input_motion": str(motion.source) if motion.source else "",
        "processed_motion": str(motion_file),
        "model_tcl": str(tcl_path),
        "config_snapshot": str(config_snapshot_path),
        "checksums": checksum_map,
    }
    if opensees_probe is not None:
        run_meta["opensees_backend_probe"] = opensees_probe
    if opensees_diagnostics is not None:
        run_meta["opensees_diagnostics"] = opensees_diagnostics
    if timeout_recovered:
        run_meta["opensees_timeout_recovered"] = {
            "recovered": True,
            "coverage_ratio": float(timeout_recovered_coverage),
            "timeout_s_effective": effective_timeout_s,
        }
    if eql_summary is not None:
        run_meta["eql"] = {
            "iterations": _as_int(eql_summary.get("iterations", 0)),
            "converged": bool(eql_summary.get("converged", False)),
        }
    run_meta_path.write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    return RunResult(
        run_id=run_id,
        output_dir=run_dir,
        hdf5_path=h5_path,
        sqlite_path=sqlite_path,
        status=status,
        message=message,
    )


def run_batch(
    config: ProjectConfig,
    motions: list[Motion],
    output_dir: str | Path = "out",
    n_jobs: int = 1,
) -> BatchResult:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not motions:
        return BatchResult(output_dir=out_dir, results=[])

    key_to_motion: dict[tuple[float, str, str], Motion] = {}
    ordered_keys: list[tuple[float, str, str]] = []
    for motion in motions:
        key = _stable_motion_key(motion)
        ordered_keys.append(key)
        if key not in key_to_motion:
            key_to_motion[key] = motion

    unique_keys = list(key_to_motion.keys())
    result_by_key: dict[tuple[float, str, str], RunResult] = {}

    if n_jobs <= 1:
        for key in unique_keys:
            result_by_key[key] = run_analysis(
                config=config,
                motion=key_to_motion[key],
                output_dir=out_dir,
            )
    else:
        with ThreadPoolExecutor(max_workers=n_jobs) as ex:
            futures = {
                ex.submit(run_analysis, config, key_to_motion[key], out_dir): key
                for key in unique_keys
            }
            for future, key in futures.items():
                result_by_key[key] = future.result()

    results = [_clone_run_result(result_by_key[key]) for key in ordered_keys]

    return BatchResult(output_dir=out_dir, results=results)


def run_analysis_from_paths(
    config_path: str | Path,
    motion_path: str | Path,
    output_dir: str | Path,
) -> RunResult:
    cfg = load_project_config(config_path)
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    mot = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
    return run_analysis(cfg, mot, output_dir)


def load_result(output_dir: str | Path) -> ResultStore:
    return _load_result(output_dir)
