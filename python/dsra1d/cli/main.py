from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import typer
from rich import print

from dsra1d.benchmark import run_benchmark_suite
from dsra1d.config import load_project_config, write_config_template
from dsra1d.interop.opensees import resolve_opensees_executable
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis, run_batch
from dsra1d.post import write_report

app = typer.Typer(help="1DSRA CLI")


@app.command("init")
def init_config(
    template: str = typer.Option("effective-stress", "--template"),
    out: Path = typer.Option(Path("examples/configs/effective_stress.yml"), "--out"),
) -> None:
    if template != "effective-stress":
        raise typer.BadParameter("Only template=effective-stress is currently supported")
    path = write_config_template(out)
    print(f"[green]Template written:[/green] {path}")


@app.command("validate")
def validate(
    config: Path = typer.Option(..., "--config"),
    check_backend: bool = typer.Option(False, "--check-backend"),
) -> None:
    cfg = load_project_config(config)
    if check_backend and cfg.analysis.solver_backend == "opensees":
        resolved = resolve_opensees_executable(cfg.opensees.executable)
        if resolved is None:
            print(
                "[red]OpenSees executable not found:[/red] "
                f"{cfg.opensees.executable}"
            )
            raise typer.Exit(code=5)
        print(f"[green]OpenSees executable[/green]: {resolved}")
    print(f"[green]Valid config[/green]: {cfg.project_name}")


@app.command("run")
def run(
    config: Path = typer.Option(..., "--config"),
    motion: Path = typer.Option(..., "--motion"),
    out: Path = typer.Option(Path("out"), "--out"),
) -> None:
    cfg = load_project_config(config)
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    mot = load_motion(motion, dt=dt, unit=cfg.motion.units)
    res = run_analysis(cfg, mot, output_dir=out)
    if res.status != "ok":
        print(f"[red]Run failed:[/red] {res.message}")
        raise typer.Exit(code=2)
    print(f"[green]Completed[/green]: {res.output_dir}")


@app.command("batch")
def batch(
    config: Path = typer.Option(..., "--config"),
    motions_dir: Path = typer.Option(..., "--motions-dir"),
    n_jobs: int = typer.Option(1, "--n-jobs"),
    out: Path = typer.Option(Path("out"), "--out"),
) -> None:
    cfg = load_project_config(config)
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    files = sorted([p for p in motions_dir.iterdir() if p.is_file()])
    if not files:
        raise typer.BadParameter("No motion files found")

    motions = [load_motion(p, dt=dt, unit=cfg.motion.units) for p in files]
    batch_result = run_batch(cfg, motions, output_dir=out, n_jobs=n_jobs)
    ok = sum(1 for r in batch_result.results if r.status == "ok")
    print(f"[green]{ok}/{len(batch_result.results)}[/green] runs completed")


@app.command("benchmark")
def benchmark(
    suite: str = typer.Option("core-es", "--suite"),
    out: Path = typer.Option(Path("out/benchmarks"), "--out"),
    fail_on_skip: bool = typer.Option(False, "--fail-on-skip"),
    require_runs: int = typer.Option(0, "--require-runs"),
) -> None:
    report = run_benchmark_suite(suite=suite, output_dir=out)
    report_path = out / f"benchmark_{suite}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[green]Benchmark report:[/green] {report_path}")
    if not bool(report.get("all_passed", False)):
        raise typer.Exit(code=3)
    skipped_raw = report.get("skipped", 0)
    ran_raw = report.get("ran", 0)
    skipped = int(skipped_raw) if isinstance(skipped_raw, (int, float, str)) else 0
    ran = int(ran_raw) if isinstance(ran_raw, (int, float, str)) else 0
    if fail_on_skip and skipped > 0:
        print(f"[red]Benchmark strict policy failed:[/red] skipped={skipped}")
        raise typer.Exit(code=7)
    if ran < require_runs:
        print(
            "[red]Benchmark strict policy failed:[/red] "
            f"ran={ran}, require_runs={require_runs}"
        )
        raise typer.Exit(code=7)


@app.command("report")
def report(
    input_dir: Path = typer.Option(..., "--in"),
    output_format: str = typer.Option("html,pdf", "--format"),
    out: Path | None = typer.Option(None, "--out"),
) -> None:
    result = load_result(input_dir)
    out_dir = out or input_dir
    formats = [s.strip().lower() for s in output_format.split(",") if s.strip()]
    written = write_report(result, out_dir=out_dir, formats=formats)
    print("[green]Report files:[/green]")
    for p in written:
        print(f"- {p}")


@app.command("dt-check")
def dt_check(
    config: Path = typer.Option(..., "--config"),
    motion: Path = typer.Option(..., "--motion"),
    out: Path = typer.Option(Path("out/dt_check"), "--out"),
    threshold: float = typer.Option(0.25, "--threshold"),
) -> None:
    cfg = load_project_config(config)
    dt_base = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    out.mkdir(parents=True, exist_ok=True)

    mot_base = load_motion(motion, dt=dt_base, unit=cfg.motion.units)
    res_base = run_analysis(cfg, mot_base, output_dir=out / "base")

    cfg_half = cfg.model_copy(deep=True)
    cfg_half.analysis.dt = dt_base / 2.0
    mot_half = load_motion(motion, dt=cfg_half.analysis.dt, unit=cfg_half.motion.units)
    res_half = run_analysis(cfg_half, mot_half, output_dir=out / "half")

    rs_base = load_result(res_base.output_dir)
    rs_half = load_result(res_half.output_dir)

    if rs_base.spectra_psa.shape != rs_half.spectra_psa.shape:
        print("[red]dt-check failed:[/red] spectra shape mismatch")
        raise typer.Exit(code=8)

    denom = np.maximum(np.abs(rs_half.spectra_psa), 1.0e-10)
    rel = np.abs(rs_base.spectra_psa - rs_half.spectra_psa) / denom
    max_rel = float(np.max(rel))
    mean_rel = float(np.mean(rel))

    summary = {
        "dt_base": dt_base,
        "dt_half": cfg_half.analysis.dt,
        "max_relative_psa_diff": max_rel,
        "mean_relative_psa_diff": mean_rel,
        "threshold": threshold,
        "base_status": res_base.status,
        "half_status": res_half.status,
        "base_run_dir": str(res_base.output_dir),
        "half_run_dir": str(res_half.output_dir),
    }
    summary_path = out / "dt_check_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[green]dt-check summary:[/green] {summary_path}")
    print(f"max_relative_psa_diff={max_rel:.6f}, threshold={threshold:.6f}")

    if max_rel > threshold:
        raise typer.Exit(code=6)


@app.command("ui")
def ui(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8501, "--port"),
    headless: bool = typer.Option(False, "--headless"),
) -> None:
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:
        print(
            "[red]Streamlit is not installed.[/red] "
            "Install with: [bold]pip install -e .[ui][/bold]"
        )
        raise typer.Exit(code=4) from exc

    app_path = Path(__file__).resolve().parents[1] / "ui" / "app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        str(headless).lower(),
    ]
    raise typer.Exit(code=subprocess.call(cmd))


if __name__ == "__main__":
    app()
