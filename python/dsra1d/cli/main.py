from __future__ import annotations

import enum
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import numpy as np
import typer
from rich import print

from dsra1d.calibration import calibrate_gqh_from_darendeli, calibrate_mkz_from_darendeli
from dsra1d.config import load_project_config, write_config_template
from dsra1d.motion import load_motion
from dsra1d.pipeline import run_analysis, run_batch


class _MaterialChoice(str, enum.Enum):
    mkz = "mkz"
    gqh = "gqh"


class RunBackendMode(str, enum.Enum):
    linear = "linear"
    eql = "eql"
    nonlinear = "nonlinear"


app = typer.Typer(help="GeoWave CLI (core-only mode)")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _can_bind_tcp(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _resolve_web_port(host: str, requested_port: int, *, scan_limit: int = 20) -> tuple[int, bool]:
    if _can_bind_tcp(host, requested_port):
        return requested_port, False

    max_scan = max(scan_limit, 0)
    for offset in range(1, max_scan + 1):
        candidate = requested_port + offset
        if candidate > 65535:
            break
        if _can_bind_tcp(host, candidate):
            return candidate, True

    print(
        "[red]No available port found for web UI.[/red] "
        f"Requested={requested_port}, scanned=+{max_scan}."
    )
    raise typer.Exit(code=6)


def _write_calibration_curve_csv(
    path: Path,
    *,
    strain: np.ndarray,
    target_modulus_reduction: np.ndarray,
    target_damping_ratio: np.ndarray,
    fitted_modulus_reduction: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("strain,target_g_reduction,target_damping_ratio,fitted_g_reduction\n")
        n = min(
            int(strain.size),
            int(target_modulus_reduction.size),
            int(target_damping_ratio.size),
            int(fitted_modulus_reduction.size),
        )
        for i in range(n):
            f.write(
                f"{float(strain[i]):.10e},"
                f"{float(target_modulus_reduction[i]):.10e},"
                f"{float(target_damping_ratio[i]):.10e},"
                f"{float(fitted_modulus_reduction[i]):.10e}\n"
            )


def _resolve_runtime_backend(requested: RunBackendMode) -> tuple[str, str]:
    backend = requested.value
    return backend, f"{backend} (forced)"


@app.command("init")
def init_config(
    template: str = typer.Option("mkz-gqh-nonlinear", "--template"),
    out: Path = typer.Option(Path("examples/configs/mkz_gqh_nonlinear.yml"), "--out"),
) -> None:
    try:
        path = write_config_template(out, template=template)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    print(f"[green]Template written:[/green] {path}")


@app.command("calibrate-darendeli")
def calibrate_darendeli(
    material: _MaterialChoice = typer.Option(..., "--material"),
    out: Path = typer.Option(..., "--out"),
    plasticity_index: float = typer.Option(0.0, "--plasticity-index", min=0.0),
    ocr: float = typer.Option(1.0, "--ocr", min=1.0e-9),
    mean_effective_stress_kpa: float = typer.Option(
        ...,
        "--mean-effective-stress-kpa",
        min=1.0e-9,
    ),
    frequency_hz: float = typer.Option(1.0, "--frequency-hz", min=1.0e-9),
    num_cycles: float = typer.Option(10.0, "--num-cycles", min=1.0e-9),
    gmax: float | None = typer.Option(None, "--gmax", min=1.0e-9),
    vs_m_s: float | None = typer.Option(None, "--vs-m-s", min=1.0e-9),
    unit_weight_kn_m3: float | None = typer.Option(
        None,
        "--unit-weight-kN-m3",
        min=1.0e-9,
    ),
    strain_min: float = typer.Option(1.0e-6, "--strain-min", min=1.0e-12),
    strain_max: float = typer.Option(1.0e-1, "--strain-max", min=1.0e-12),
    n_points: int = typer.Option(60, "--n-points", min=12),
    reload_factor: float | None = typer.Option(None, "--reload-factor", min=1.0e-9),
) -> None:
    if gmax is not None:
        gmax_value = float(gmax)
    else:
        if vs_m_s is None or unit_weight_kn_m3 is None:
            raise typer.BadParameter(
                "Provide --gmax or both --vs-m-s and --unit-weight-kN-m3."
            )
        gmax_value = (float(unit_weight_kn_m3) / 9.81) * float(vs_m_s) * float(vs_m_s)

    reload = float(reload_factor) if reload_factor is not None else (
        2.0 if material == _MaterialChoice.mkz else 1.6
    )
    if material == _MaterialChoice.mkz:
        result = calibrate_mkz_from_darendeli(
            gmax=gmax_value,
            plasticity_index=plasticity_index,
            ocr=ocr,
            mean_effective_stress_kpa=mean_effective_stress_kpa,
            frequency_hz=frequency_hz,
            num_cycles=num_cycles,
            strain_min=strain_min,
            strain_max=strain_max,
            n_points=n_points,
            reload_factor=reload,
        )
    else:
        result = calibrate_gqh_from_darendeli(
            gmax=gmax_value,
            plasticity_index=plasticity_index,
            ocr=ocr,
            mean_effective_stress_kpa=mean_effective_stress_kpa,
            frequency_hz=frequency_hz,
            num_cycles=num_cycles,
            strain_min=strain_min,
            strain_max=strain_max,
            n_points=n_points,
            reload_factor=reload,
        )

    out.mkdir(parents=True, exist_ok=True)
    mat_str = material.value
    params_path = out / f"darendeli_{mat_str}_params.json"
    curves_path = out / f"darendeli_{mat_str}_curves.csv"
    payload = {
        "material": result.material,
        "source": result.source,
        "fit_rmse": result.fit_rmse,
        "material_params": result.material_params,
        "inputs": {
            "plasticity_index": plasticity_index,
            "ocr": ocr,
            "mean_effective_stress_kpa": mean_effective_stress_kpa,
            "frequency_hz": frequency_hz,
            "num_cycles": num_cycles,
            "gmax": gmax_value,
            "strain_min": strain_min,
            "strain_max": strain_max,
            "n_points": n_points,
            "reload_factor": reload,
        },
    }
    params_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_calibration_curve_csv(
        curves_path,
        strain=result.strain,
        target_modulus_reduction=result.target_modulus_reduction,
        target_damping_ratio=result.target_damping_ratio,
        fitted_modulus_reduction=result.fitted_modulus_reduction,
    )

    print(f"[green]Darendeli calibration exported:[/green] {params_path}")
    print(f"[green]Curve CSV exported:[/green] {curves_path}")
    print(f"[cyan]Material:[/cyan] {result.material}")
    print(f"[cyan]fit_rmse:[/cyan] {result.fit_rmse:.6f}")


@app.command("validate")
def validate(
    config: Path = typer.Option(..., "--config"),
) -> None:
    cfg = load_project_config(config)
    materials = ", ".join(layer.material.value for layer in cfg.profile.layers)
    print(f"[green]Valid config[/green]: {cfg.project_name}")
    print(f"[cyan]Solver backend:[/cyan] {cfg.analysis.solver_backend}")
    print(f"[cyan]Layer materials:[/cyan] {materials}")


@app.command("run")
def run(
    config: Path = typer.Option(..., "--config"),
    motion: Path = typer.Option(..., "--motion"),
    out: Path = typer.Option(Path("out"), "--out"),
    backend: RunBackendMode = typer.Option(RunBackendMode.nonlinear, "--backend"),
) -> None:
    cfg = load_project_config(config)
    resolved_backend, backend_note = _resolve_runtime_backend(backend)
    cfg.analysis.solver_backend = resolved_backend
    print(f"[cyan]Run backend:[/cyan] {backend_note}")
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    mot = load_motion(motion, dt=dt, unit=cfg.motion.units)
    res = run_analysis(cfg, mot, output_dir=out)
    if res.status != "ok":
        print(f"[red]Run failed:[/red] {res.message}")
        raise typer.Exit(code=2)
    print(f"[green]Completed[/green]: {res.output_dir}")


@app.command("quickstart")
def quickstart(
    out: Path = typer.Option(Path("out/quickstart"), "--out"),
    template: str = typer.Option("mkz-gqh-nonlinear", "--template"),
    backend: RunBackendMode = typer.Option(RunBackendMode.nonlinear, "--backend"),
) -> None:
    repo_root = _repo_root()
    src_motion = repo_root / "examples" / "motions" / "sample_motion.csv"
    if not src_motion.exists():
        raise typer.BadParameter(f"Sample motion not found: {src_motion}")

    out.mkdir(parents=True, exist_ok=True)
    config_out = out / "config.yml"
    motion_out = out / "motion.csv"
    try:
        write_config_template(config_out, template=template)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    shutil.copy2(src_motion, motion_out)

    cfg = load_project_config(config_out)
    resolved_backend, backend_note = _resolve_runtime_backend(backend)
    cfg.analysis.solver_backend = resolved_backend
    print(f"[cyan]Quickstart backend:[/cyan] {backend_note}")
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    mot = load_motion(motion_out, dt=dt, unit=cfg.motion.units)
    res = run_analysis(cfg, mot, output_dir=out / "runs")
    summary = {
        "template": template,
        "backend": str(cfg.analysis.solver_backend),
        "backend_note": backend_note,
        "run_id": res.run_id,
        "run_status": res.status,
        "run_message": res.message,
        "run_dir": str(res.output_dir),
    }
    summary_path = out / "quickstart_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[green]Quickstart summary:[/green] {summary_path}")
    print(f"[green]Run directory:[/green] {res.output_dir}")
    if res.status != "ok":
        raise typer.Exit(code=2)


@app.command("batch")
def batch(
    config: Path = typer.Option(..., "--config"),
    motions_dir: Path = typer.Option(..., "--motions-dir"),
    n_jobs: int = typer.Option(1, "--n-jobs"),
    out: Path = typer.Option(Path("out"), "--out"),
    backend: RunBackendMode = typer.Option(RunBackendMode.nonlinear, "--backend"),
) -> None:
    cfg = load_project_config(config)
    resolved_backend, backend_note = _resolve_runtime_backend(backend)
    cfg.analysis.solver_backend = resolved_backend
    print(f"[cyan]Batch backend:[/cyan] {backend_note}")
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    files = sorted([p for p in motions_dir.iterdir() if p.is_file()])
    if not files:
        raise typer.BadParameter("No motion files found")

    motions = [load_motion(p, dt=dt, unit=cfg.motion.units) for p in files]
    batch_result = run_batch(cfg, motions, output_dir=out, n_jobs=n_jobs)
    ok = sum(1 for r in batch_result.results if r.status == "ok")
    print(f"[green]{ok}/{len(batch_result.results)}[/green] runs completed")
    if ok != len(batch_result.results):
        raise typer.Exit(code=2)


@app.command("web")
def web(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8010, "--port"),
    reload: bool = typer.Option(False, "--reload"),
    port_scan: int = typer.Option(20, "--port-scan", min=0, max=200),
) -> None:
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError as exc:
        print(
            "[red]FastAPI/uvicorn is not installed.[/red] "
            "Install with: [bold]pip install -e .[web][/bold]"
        )
        raise typer.Exit(code=4) from exc

    selected_port, shifted = _resolve_web_port(host, port, scan_limit=port_scan)
    if shifted:
        print(
            "[yellow]Port is already in use; switched web UI port automatically:[/yellow] "
            f"{port} -> {selected_port}"
        )

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "dsra1d.web.app:app",
        "--host",
        host,
        "--port",
        str(selected_port),
    ]
    if reload:
        cmd.append("--reload")
    raise typer.Exit(code=subprocess.call(cmd))


if __name__ == "__main__":
    app()
