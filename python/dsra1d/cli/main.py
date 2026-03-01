from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import numpy as np
import typer
from rich import print

from dsra1d.benchmark import run_benchmark_suite
from dsra1d.config import load_project_config, write_config_template
from dsra1d.interop.opensees import resolve_opensees_executable
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis, run_batch
from dsra1d.post import render_summary_markdown, summarize_campaign, write_report
from dsra1d.verify import verify_batch, verify_run

app = typer.Typer(help="1DSRA CLI")


def _load_json_mapping(path: Path) -> dict[str, object]:
    if not path.exists():
        raise typer.BadParameter(f"Path not found: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON file: {path} ({exc})") from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter(f"JSON root must be object: {path}")
    return cast(dict[str, object], parsed)


def _enforce_benchmark_strict_policy(
    report: dict[str, object],
    *,
    fail_on_skip: bool,
    require_runs: int,
) -> None:
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
    _enforce_benchmark_strict_policy(
        report,
        fail_on_skip=fail_on_skip,
        require_runs=require_runs,
    )


@app.command("campaign")
def campaign(
    suite: str = typer.Option("opensees-parity", "--suite"),
    out: Path = typer.Option(Path("out/campaign"), "--out"),
    fail_on_skip: bool = typer.Option(False, "--fail-on-skip"),
    require_runs: int = typer.Option(0, "--require-runs"),
    verify_require_runs: int = typer.Option(1, "--verify-require-runs"),
    tolerance: float = typer.Option(1.0e-8, "--tolerance"),
    require_checksums: bool = typer.Option(True, "--require-checksums/--allow-missing-checksums"),
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    report = run_benchmark_suite(suite=suite, output_dir=out)
    benchmark_path = out / f"benchmark_{suite}.json"
    benchmark_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[green]Benchmark report:[/green] {benchmark_path}")

    verify = verify_batch(
        out,
        tolerance=tolerance,
        require_checksums=require_checksums,
        require_runs=verify_require_runs,
    )
    verify_path = out / "verify_batch_report.json"
    verify_path.write_text(json.dumps(verify.as_dict(), indent=2), encoding="utf-8")
    print(f"[green]Verify batch report:[/green] {verify_path}")

    summary = summarize_campaign(report, verify.as_dict())
    summary_json = out / "campaign_summary.json"
    summary_md = out / "campaign_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(render_summary_markdown(summary), encoding="utf-8")
    print(f"[green]Campaign summary JSON:[/green] {summary_json}")
    print(f"[green]Campaign summary Markdown:[/green] {summary_md}")

    if not bool(report.get("all_passed", False)):
        raise typer.Exit(code=3)
    _enforce_benchmark_strict_policy(
        report,
        fail_on_skip=fail_on_skip,
        require_runs=require_runs,
    )
    if not verify.ok:
        print("[red]Batch verification failed[/red]")
        raise typer.Exit(code=9)


@app.command("summarize")
def summarize(
    benchmark_report: Path = typer.Option(..., "--benchmark-report"),
    verify_batch_report: Path | None = typer.Option(None, "--verify-batch-report"),
    out: Path = typer.Option(Path("out/summary"), "--out"),
) -> None:
    benchmark_data = _load_json_mapping(benchmark_report)
    verify_data = (
        _load_json_mapping(verify_batch_report)
        if verify_batch_report is not None
        else None
    )
    summary = summarize_campaign(benchmark_data, verify_data)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "campaign_summary.json"
    markdown_path = out / "campaign_summary.md"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown_path.write_text(
        render_summary_markdown(summary),
        encoding="utf-8",
    )
    print(f"[green]Campaign summary JSON:[/green] {json_path}")
    print(f"[green]Campaign summary Markdown:[/green] {markdown_path}")


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


@app.command("verify")
def verify(
    input_dir: Path = typer.Option(..., "--in"),
    tolerance: float = typer.Option(1.0e-8, "--tolerance"),
    require_checksums: bool = typer.Option(True, "--require-checksums/--allow-missing-checksums"),
) -> None:
    report = verify_run(
        input_dir,
        tolerance=tolerance,
        require_checksums=require_checksums,
    )
    report_path = input_dir / "verify_report.json"
    report_path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    print(f"[green]Verify report:[/green] {report_path}")
    if not report.ok:
        print("[red]Verification failed[/red]")
        raise typer.Exit(code=9)
    print("[green]Verification passed[/green]")


@app.command("verify-batch")
def verify_batch_cmd(
    input_dir: Path = typer.Option(..., "--in"),
    tolerance: float = typer.Option(1.0e-8, "--tolerance"),
    require_checksums: bool = typer.Option(True, "--require-checksums/--allow-missing-checksums"),
    require_runs: int = typer.Option(1, "--require-runs"),
) -> None:
    report = verify_batch(
        input_dir,
        tolerance=tolerance,
        require_checksums=require_checksums,
        require_runs=require_runs,
    )
    if input_dir.exists():
        report_base = input_dir
    elif input_dir.parent.exists():
        report_base = input_dir.parent
    else:
        report_base = Path.cwd()
    report_path = report_base / "verify_batch_report.json"
    report_path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    print(f"[green]Verify batch report:[/green] {report_path}")
    print(
        f"total_runs={report.total_runs}, "
        f"passed={report.passed_runs}, failed={report.failed_runs}"
    )
    if not report.ok:
        print("[red]Batch verification failed[/red]")
        raise typer.Exit(code=9)
    print("[green]Batch verification passed[/green]")


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
