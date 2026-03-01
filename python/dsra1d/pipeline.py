from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from dsra1d.config import MaterialType, ProjectConfig, load_project_config
from dsra1d.interop.opensees import (
    OpenSeesExecutionError,
    build_layer_slices,
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

    processed = preprocess_motion(motion, config.motion)
    # Mesh summary is computed early to validate profile/f_max discretization assumptions.
    slices = build_layer_slices(config)
    motion_file = run_dir / "motion_processed.csv"
    np.savetxt(motion_file, processed.acc, delimiter=",")
    artifacts.append(("motion_processed", str(motion_file)))

    tcl = render_tcl(config, motion_file=motion_file, output_dir=run_dir)
    validate_tcl_script(tcl)
    tcl_path = run_dir / "model.tcl"
    tcl_path.write_text(tcl, encoding="utf-8")
    artifacts.append(("model_tcl", str(tcl_path)))

    status = "ok"
    message = "completed"
    opensees_command: list[str] = []
    opensees_stdout_log: Path | None = None
    opensees_stderr_log: Path | None = None
    eql_summary: dict[str, object] | None = None

    if config.analysis.solver_backend == "opensees":
        attempt = 0
        while True:
            attempt += 1
            try:
                run_output = run_opensees(
                    executable=config.opensees.executable,
                    tcl_file=tcl_path,
                    cwd=run_dir,
                    timeout_s=config.analysis.timeout_s,
                    extra_args=config.opensees.extra_args,
                )
                opensees_command = run_output.command
                opensees_stdout_log = run_dir / "opensees_stdout.log"
                opensees_stderr_log = run_dir / "opensees_stderr.log"
                opensees_stdout_log.write_text(run_output.stdout, encoding="utf-8")
                opensees_stderr_log.write_text(run_output.stderr, encoding="utf-8")
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
                    status = "error"
                    message = str(exc)
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

    spectra = compute_spectra(acc_surface, dt=processed.dt, damping=0.05)
    transfer_freq_hz, transfer_abs = compute_transfer_function(
        processed.acc,
        acc_surface,
        processed.dt,
    )
    time = surface_t

    surface_out = run_dir / "surface_acc.out"
    pwp_out = run_dir / "pwp_ru.out"
    artifacts.append(("results_hdf5", str(run_dir / "results.h5")))
    artifacts.append(("results_sqlite", str(run_dir / "results.sqlite")))
    if surface_out.exists():
        artifacts.append(("surface_acc", str(surface_out)))
    if pwp_out.exists():
        artifacts.append(("pwp_ru", str(pwp_out)))
    pwp_raw_out = run_dir / "pwp_raw.out"
    if pwp_raw_out.exists():
        artifacts.append(("pwp_raw", str(pwp_raw_out)))
    if opensees_stdout_log and opensees_stdout_log.exists():
        artifacts.append(("opensees_stdout", str(opensees_stdout_log)))
    if opensees_stderr_log and opensees_stderr_log.exists():
        artifacts.append(("opensees_stderr", str(opensees_stderr_log)))

    h5_path = run_dir / "results.h5"
    sqlite_path = run_dir / "results.sqlite"

    if config.output.write_hdf5:
        write_hdf5(
            h5_path,
            time,
            acc_surface,
            ru_t,
            ru,
            delta_u,
            sigma_v_ref,
            sigma_v_eff,
            spectra,
            transfer_freq_hz,
            transfer_abs,
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
            dt=processed.dt,
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
        "status": status,
        "message": message,
        "opensees_command": opensees_command,
        "input_motion": str(motion.source) if motion.source else "",
        "processed_motion": str(motion_file),
        "model_tcl": str(tcl_path),
        "checksums": checksum_map,
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
