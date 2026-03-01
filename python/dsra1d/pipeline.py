from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from dsra1d.config import ProjectConfig, load_project_config
from dsra1d.interop.opensees import (
    OpenSeesExecutionError,
    build_layer_slices,
    read_ru,
    read_surface_acc_with_time,
    render_tcl,
    run_opensees,
    validate_tcl_script,
)
from dsra1d.motion import load_motion, preprocess_motion
from dsra1d.post import compute_spectra
from dsra1d.store import ResultStore, write_hdf5, write_sqlite
from dsra1d.store import load_result as _load_result
from dsra1d.types import BatchResult, Motion, RunResult


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


def _write_mock_outputs(run_dir: Path, acc: np.ndarray, dt: float) -> None:
    surface = 0.8 * acc
    np.savetxt(run_dir / "surface_acc.out", surface)
    ru_t = np.arange(surface.size, dtype=np.float64) * dt
    ru = np.clip(np.linspace(0.0, 0.3, surface.size), 0.0, 1.0)
    np.savetxt(run_dir / "pwp_ru.out", np.column_stack([ru_t, ru]))


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
                    _write_mock_outputs(run_dir, processed.acc, processed.dt)
                    break
    else:
        _write_mock_outputs(run_dir, processed.acc, processed.dt)

    surface_t, acc_surface = read_surface_acc_with_time(
        run_dir / "surface_acc.out",
        dt_default=processed.dt,
    )
    ru_t, ru = read_ru(run_dir / "pwp_ru.out")
    spectra = compute_spectra(acc_surface, dt=processed.dt, damping=0.05)
    time = surface_t

    surface_out = run_dir / "surface_acc.out"
    pwp_out = run_dir / "pwp_ru.out"
    if surface_out.exists():
        artifacts.append(("surface_acc", str(surface_out)))
    if pwp_out.exists():
        artifacts.append(("pwp_ru", str(pwp_out)))
    if opensees_stdout_log and opensees_stdout_log.exists():
        artifacts.append(("opensees_stdout", str(opensees_stdout_log)))
    if opensees_stderr_log and opensees_stderr_log.exists():
        artifacts.append(("opensees_stderr", str(opensees_stderr_log)))

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
    }
    run_meta_path.write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    artifacts.append(("run_meta", str(run_meta_path)))

    h5_path = run_dir / "results.h5"
    sqlite_path = run_dir / "results.sqlite"

    if config.output.write_hdf5:
        write_hdf5(
            h5_path,
            time,
            acc_surface,
            ru_t,
            ru,
            spectra,
            mesh_layer_idx=np.array([s.index for s in slices], dtype=np.int64),
            mesh_z_top=np.array([s.z_top_m for s in slices], dtype=np.float64),
            mesh_z_bot=np.array([s.z_bot_m for s in slices], dtype=np.float64),
            mesh_dz=np.array([s.dz_m for s in slices], dtype=np.float64),
            mesh_n_sub=np.array([s.n_sublayers for s in slices], dtype=np.int64),
        )
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
            ru_time=ru_t,
            ru=ru,
            mesh_slices=slices,
            artifacts=artifacts,
        )

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

    if n_jobs <= 1:
        results = [run_analysis(config=config, motion=m, output_dir=out_dir) for m in motions]
        return BatchResult(output_dir=out_dir, results=results)

    with ThreadPoolExecutor(max_workers=n_jobs) as ex:
        futures = [ex.submit(run_analysis, config, m, out_dir) for m in motions]
        results = [f.result() for f in futures]

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
