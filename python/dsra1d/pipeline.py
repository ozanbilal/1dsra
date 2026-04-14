from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from dsra1d.config import ProjectConfig, load_project_config
from dsra1d.interop.opensees import (
    build_layer_slices,
    read_pwp_raw,
    read_ru,
    read_surface_acc_with_time,
)
from dsra1d.linear import solve_equivalent_linear_sh_response, solve_linear_sh_response
from dsra1d.motion import effective_input_acceleration, load_motion, preprocess_motion
from dsra1d.newmark_nonlinear import (
    solve_nonlinear_implicit_newmark,
    solve_nonlinear_newmark,
)
from dsra1d.nonlinear import solve_nonlinear_sh_response
from dsra1d.post import compute_spectra, compute_transfer_function
from dsra1d.post.layer_response import (
    derive_layer_response_histories,
    write_layer_response_outputs,
)
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


def _write_linear_outputs(
    run_dir: Path,
    config: ProjectConfig,
    motion: Motion,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    t, surface = solve_linear_sh_response(config, motion)
    if not np.all(np.isfinite(surface)):
        raise ValueError("Linear solver produced non-finite surface acceleration.")
    np.savetxt(run_dir / "surface_acc.out", np.column_stack([t, surface]))
    ru = np.zeros_like(t)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([t, ru]))
    return None, None


def _write_nonlinear_outputs(
    run_dir: Path,
    config: ProjectConfig,
    motion: Motion,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    if config.analysis.integration_scheme == "newmark":
        output = solve_nonlinear_implicit_newmark(
            config,
            motion,
            return_nodal_displacement=True,
        )
    elif config.analysis.integration_scheme == "verlet":
        output = solve_nonlinear_newmark(
            config,
            motion,
            return_nodal_displacement=True,
        )
    else:
        output = solve_nonlinear_sh_response(
            config,
            motion,
            substeps=int(config.analysis.nonlinear_substeps),
            return_nodal_displacement=True,
        )
    if len(output) == 4:
        t, surface, node_depth_m, nodal_displacement_m = output
    else:
        t, surface = output
        node_depth_m = None
        nodal_displacement_m = None
    if not np.all(np.isfinite(surface)):
        raise ValueError(
            "Nonlinear solver produced non-finite surface acceleration. "
            "Try a smaller dt or inspect constitutive/boundary settings."
        )
    np.savetxt(run_dir / "surface_acc.out", np.column_stack([t, surface]))
    ru = np.zeros_like(t)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([t, ru]))
    return node_depth_m, nodal_displacement_m


def _write_eql_outputs(
    run_dir: Path,
    config: ProjectConfig,
    motion: Motion,
) -> tuple[Path, dict[str, object], np.ndarray | None, np.ndarray | None]:
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
    return (
        summary_path,
        summary,
        np.asarray(response.response.node_depth_m, dtype=np.float64),
        np.asarray(response.response.nodal_displacement_m, dtype=np.float64),
    )


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
    applied_input_acc = effective_input_acceleration(config, processed.acc)
    slices = build_layer_slices(config)
    motion_file = run_dir / "motion_processed.csv"
    motion_time = np.arange(processed.acc.size, dtype=np.float64) * float(processed.dt)
    np.savetxt(
        motion_file,
        np.column_stack([motion_time, np.asarray(processed.acc, dtype=np.float64)]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )
    artifacts.append(("motion_processed", str(motion_file)))

    status = "ok"
    message = "completed"
    eql_summary: dict[str, object] | None = None
    node_depth_m: np.ndarray | None = None
    nodal_displacement_m: np.ndarray | None = None
    configured_timeout_s = int(max(config.analysis.timeout_s, 1))
    effective_timeout_s = configured_timeout_s

    if config.analysis.solver_backend == "linear":
        node_depth_m, nodal_displacement_m = _write_linear_outputs(
            run_dir=run_dir,
            config=config,
            motion=processed,
        )
    elif config.analysis.solver_backend == "nonlinear":
        node_depth_m, nodal_displacement_m = _write_nonlinear_outputs(
            run_dir=run_dir,
            config=config,
            motion=processed,
        )
    elif config.analysis.solver_backend == "eql":
        eql_summary_path, eql_summary, node_depth_m, nodal_displacement_m = _write_eql_outputs(
            run_dir=run_dir,
            config=config,
            motion=processed,
        )
        artifacts.append(("eql_summary", str(eql_summary_path)))
    else:
        raise ValueError(
            f"Unsupported solver_backend '{config.analysis.solver_backend}'. "
            "GeoWave core mode supports only linear, eql, and nonlinear."
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
    if (
        config.analysis.solver_backend == "nonlinear"
        and node_depth_m is not None
        and nodal_displacement_m is not None
    ):
        layer_histories = derive_layer_response_histories(
            config,
            node_depth_m=np.asarray(node_depth_m, dtype=np.float64),
            nodal_displacement_m=np.asarray(nodal_displacement_m, dtype=np.float64),
        )
        layer_output_files, layer_summary_path = write_layer_response_outputs(
            run_dir,
            time_s=time,
            histories=layer_histories,
        )
        for kind, path in layer_output_files:
            artifacts.append((kind, str(path)))
        if layer_summary_path is not None and layer_summary_path.exists():
            artifacts.append(("layer_response_summary", str(layer_summary_path)))

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
            acc_applied_input=np.asarray(applied_input_acc, dtype=np.float64),
            input_dt_s=float(processed.dt),
            node_depth_m=node_depth_m,
            nodal_displacement_m=nodal_displacement_m,
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
        "input_dt_s": float(processed.dt),
        "status": status,
        "message": message,
        "input_motion": str(motion.source) if motion.source else "",
        "processed_motion": str(motion_file),
        "config_snapshot": str(config_snapshot_path),
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
