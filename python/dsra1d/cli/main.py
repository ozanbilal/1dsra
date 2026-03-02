from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
from math import isfinite
from pathlib import Path
from typing import Literal, cast

import numpy as np
import typer
from rich import print

from dsra1d.benchmark import run_benchmark_suite
from dsra1d.config import ProjectConfig, load_project_config, write_config_template
from dsra1d.interop.opensees import (
    probe_opensees_executable,
    render_tcl,
    resolve_opensees_executable,
    validate_backend_probe_requirements,
    validate_tcl_script,
)
from dsra1d.motion import load_motion, preprocess_motion
from dsra1d.pipeline import load_result, run_analysis, run_batch
from dsra1d.post import render_summary_markdown, summarize_campaign, write_report
from dsra1d.verify import verify_batch, verify_run

app = typer.Typer(help="1DSRA CLI")
RunBackendMode = Literal[
    "config",
    "auto",
    "opensees",
    "mock",
    "linear",
    "eql",
    "nonlinear",
]


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


def _apply_runtime_backend(
    cfg: ProjectConfig,
    *,
    backend: RunBackendMode,
    opensees_executable: str | None,
) -> tuple[ProjectConfig, str]:
    cfg_run = cfg.model_copy(deep=True)
    if opensees_executable:
        cfg_run.opensees.executable = opensees_executable

    if backend == "mock":
        cfg_run.analysis.solver_backend = "mock"
        return cfg_run, "mock (forced)"

    if backend == "linear":
        cfg_run.analysis.solver_backend = "linear"
        return cfg_run, "linear (forced)"

    if backend == "eql":
        cfg_run.analysis.solver_backend = "eql"
        return cfg_run, "eql (forced)"

    if backend == "nonlinear":
        cfg_run.analysis.solver_backend = "nonlinear"
        return cfg_run, "nonlinear (forced)"

    if backend == "opensees":
        cfg_run.analysis.solver_backend = "opensees"
        resolved = resolve_opensees_executable(cfg_run.opensees.executable)
        if resolved is None:
            print(
                "[red]OpenSees executable not found:[/red] "
                f"{cfg_run.opensees.executable}. "
                "Use [bold]--backend auto[/bold] to fallback to mock."
            )
            raise typer.Exit(code=5)
        cfg_run.opensees.executable = str(resolved)
        return cfg_run, f"opensees ({resolved})"

    if backend == "auto":
        if cfg_run.analysis.solver_backend == "opensees":
            resolved = resolve_opensees_executable(cfg_run.opensees.executable)
            if resolved is None:
                cfg_run.analysis.solver_backend = "mock"
                return cfg_run, "mock (auto-fallback: OpenSees missing)"
            cfg_run.opensees.executable = str(resolved)
            return cfg_run, f"opensees ({resolved})"
        return cfg_run, str(cfg_run.analysis.solver_backend)

    # backend == "config"
    if cfg_run.analysis.solver_backend == "opensees":
        resolved = resolve_opensees_executable(cfg_run.opensees.executable)
        if resolved is None:
            print(
                "[red]OpenSees executable not found:[/red] "
                f"{cfg_run.opensees.executable}. "
                "Use [bold]--backend auto[/bold] or [bold]--backend mock[/bold]."
            )
            raise typer.Exit(code=5)
        cfg_run.opensees.executable = str(resolved)
        return cfg_run, f"opensees ({resolved})"
    return cfg_run, str(cfg_run.analysis.solver_backend)


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


def _enforce_backend_ready_policy(
    report: dict[str, object],
    *,
    suite: str,
    require_opensees: bool,
) -> None:
    if not require_opensees:
        return
    if suite != "opensees-parity":
        return
    backend_ready_raw = report.get("backend_ready", True)
    backend_ready = bool(backend_ready_raw)
    skipped_backend_raw = report.get("skipped_backend", 0)
    skipped_backend = (
        int(skipped_backend_raw)
        if isinstance(skipped_backend_raw, (int, float, str))
        else 0
    )
    if not backend_ready or skipped_backend > 0:
        print(
            "[red]OpenSees backend policy failed:[/red] "
            f"backend_ready={backend_ready}, skipped_backend={skipped_backend}"
        )
        raise typer.Exit(code=10)


def _enforce_execution_coverage_policy(
    report: dict[str, object],
    *,
    min_execution_coverage: float,
) -> None:
    coverage_raw = report.get("execution_coverage", 0.0)
    if isinstance(coverage_raw, (int, float)):
        coverage = float(coverage_raw)
    elif isinstance(coverage_raw, str):
        try:
            coverage = float(coverage_raw)
        except ValueError:
            coverage = 0.0
    else:
        coverage = 0.0
    if coverage < min_execution_coverage:
        print(
            "[red]Execution coverage policy failed:[/red] "
            f"execution_coverage={coverage:.3f}, "
            f"min_execution_coverage={min_execution_coverage:.3f}"
        )
        raise typer.Exit(code=11)


def _enforce_explicit_checks_policy(
    report: dict[str, object],
    *,
    require_explicit_checks: bool,
) -> None:
    if not require_explicit_checks:
        return
    cases_raw = report.get("cases")
    if not isinstance(cases_raw, list):
        print("[red]Explicit checks policy failed:[/red] benchmark report has no cases list")
        raise typer.Exit(code=12)
    executed: list[dict[str, object]] = [
        case
        for case in cases_raw
        if isinstance(case, dict) and str(case.get("status", "")) == "ok"
    ]
    missing: list[str] = []
    for case in executed:
        explicit = bool(case.get("checks_explicit", False))
        if not explicit:
            missing.append(str(case.get("name", "unknown")))
    if missing:
        print(
            "[red]Explicit checks policy failed:[/red] "
            f"{len(missing)} executed case(s) without explicit checks: {missing}"
        )
        raise typer.Exit(code=12)


def _run_benchmark_with_optional_override(
    suite: str,
    out: Path,
    opensees_executable: str | None,
    require_backend_version_regex: str | None,
    require_backend_sha256: str | None,
) -> dict[str, object]:
    env_key = "DSRA1D_OPENSEES_EXE_OVERRIDE"
    old_value = os.environ.get(env_key)
    try:
        if opensees_executable:
            os.environ[env_key] = opensees_executable
        return run_benchmark_suite(
            suite=suite,
            output_dir=out,
            require_backend_version_regex=require_backend_version_regex,
            require_backend_sha256=require_backend_sha256,
        )
    finally:
        if opensees_executable:
            if old_value is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = old_value


def _parse_opensees_extra_args_override(raw: str) -> list[str]:
    value = raw.strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        posix_mode = os.name != "nt"
        return shlex.split(value, posix=posix_mode)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _apply_opensees_env_override(cfg: ProjectConfig) -> ProjectConfig:
    if cfg.analysis.solver_backend != "opensees":
        return cfg
    override_exe = os.getenv("DSRA1D_OPENSEES_EXE_OVERRIDE", "").strip()
    override_extra_raw = os.getenv("DSRA1D_OPENSEES_EXTRA_ARGS_OVERRIDE", "")
    override_extra = _parse_opensees_extra_args_override(override_extra_raw)
    if override_exe:
        cfg.opensees.executable = override_exe
    if override_extra:
        cfg.opensees.extra_args = override_extra
    return cfg


def _annotate_benchmark_policy(
    report: dict[str, object],
    *,
    fail_on_skip: bool,
    require_runs: int,
    require_opensees: bool,
    min_execution_coverage: float,
    require_explicit_checks: bool,
    require_backend_version_regex: str | None,
    require_backend_sha256: str | None,
) -> None:
    report["policy"] = {
        "fail_on_skip": fail_on_skip,
        "require_runs": require_runs,
        "require_opensees": require_opensees,
        "min_execution_coverage": min_execution_coverage,
        "require_explicit_checks": require_explicit_checks,
        "require_backend_version_regex": require_backend_version_regex or "",
        "require_backend_sha256": (require_backend_sha256 or "").lower(),
    }


def _annotate_verify_policy(
    verify_report: dict[str, object],
    *,
    require_runs: int,
) -> None:
    policy_raw = verify_report.get("policy")
    policy: dict[str, object] = dict(policy_raw) if isinstance(policy_raw, dict) else {}
    conditions_raw = policy.get("conditions")
    conditions: dict[str, bool] = (
        {str(k): bool(v) for k, v in conditions_raw.items()}
        if isinstance(conditions_raw, dict)
        else {}
    )

    total_runs_raw = verify_report.get("total_runs", 0)
    failed_runs_raw = verify_report.get("failed_runs", 0)
    if isinstance(total_runs_raw, (int, float)):
        total_runs = int(total_runs_raw)
    elif isinstance(total_runs_raw, str) and total_runs_raw.isdigit():
        total_runs = int(total_runs_raw)
    else:
        total_runs = 0
    if isinstance(failed_runs_raw, (int, float)):
        failed_runs = int(failed_runs_raw)
    elif isinstance(failed_runs_raw, str) and failed_runs_raw.isdigit():
        failed_runs = int(failed_runs_raw)
    else:
        failed_runs = 0

    conditions["verify_ok"] = bool(verify_report.get("ok", False))
    conditions["no_failed_runs"] = failed_runs == 0
    conditions["require_runs_ok"] = total_runs >= require_runs
    policy["require_runs"] = require_runs
    policy["conditions"] = conditions
    policy["passed"] = all(bool(v) for v in conditions.values())
    verify_report["policy"] = policy


def _print_benchmark_coverage(report: dict[str, object]) -> None:
    total_raw = report.get("total_cases", 0)
    ran_raw = report.get("ran", 0)
    skipped_backend_raw = report.get("skipped_backend", 0)
    coverage_raw = report.get("execution_coverage", 0.0)
    backend_ready = bool(report.get("backend_ready", True))
    total = int(total_raw) if isinstance(total_raw, (int, float, str)) else 0
    ran = int(ran_raw) if isinstance(ran_raw, (int, float, str)) else 0
    skipped_backend = (
        int(skipped_backend_raw)
        if isinstance(skipped_backend_raw, (int, float, str))
        else 0
    )
    if isinstance(coverage_raw, (int, float)):
        coverage = float(coverage_raw)
    elif isinstance(coverage_raw, str):
        try:
            coverage = float(coverage_raw)
        except ValueError:
            coverage = 0.0
    else:
        coverage = 0.0
    print(
        "[cyan]Benchmark coverage:[/cyan] "
        f"ran={ran}/{total}, "
        f"backend_ready={backend_ready}, "
        f"skipped_backend={skipped_backend}, "
        f"execution_coverage={coverage:.3f}"
    )


VALID_GOLDEN_METRICS: set[str] = {
    "pga",
    "ru_max",
    "delta_u_max",
    "sigma_v_eff_min",
    "transfer_abs_max",
    "transfer_peak_freq_hz",
}


def _parse_metric_names(raw: str) -> list[str]:
    parsed = [item.strip() for item in raw.split(",") if item.strip()]
    if not parsed:
        raise typer.BadParameter("At least one metric must be provided.")
    unknown = sorted(set(parsed) - VALID_GOLDEN_METRICS)
    if unknown:
        raise typer.BadParameter(
            f"Unknown metric(s): {unknown}. Valid metrics: {sorted(VALID_GOLDEN_METRICS)}"
        )
    return parsed


def _default_golden_path_from_suite(suite: str) -> Path:
    return _repo_root() / "benchmarks" / suite / "golden" / "golden_metrics.json"


def _build_locked_golden(
    benchmark_report: dict[str, object],
    *,
    metrics: list[str],
    rel_tol: float,
    abs_tol_min: float,
) -> dict[str, object]:
    cases_raw = benchmark_report.get("cases")
    if not isinstance(cases_raw, list):
        raise typer.BadParameter("benchmark report does not contain a valid 'cases' list.")

    locked: dict[str, object] = {}
    for case in cases_raw:
        if not isinstance(case, dict):
            continue
        if str(case.get("status", "")) != "ok":
            continue
        name = str(case.get("name", "")).strip()
        if not name:
            continue

        actual_raw = case.get("actual")
        if not isinstance(actual_raw, dict):
            continue
        actual = {str(k): float(v) for k, v in actual_raw.items() if isinstance(v, (int, float))}

        expected_raw = case.get("expected")
        expected = expected_raw if isinstance(expected_raw, dict) else {}
        constraints_raw = expected.get("constraints")
        constraints = constraints_raw if isinstance(constraints_raw, dict) else {}
        deterministic = bool(expected.get("deterministic", True))
        dt_spec_raw = expected.get("dt_sensitivity")
        dt_spec = dt_spec_raw if isinstance(dt_spec_raw, dict) else {"threshold": 5.0}

        checks: dict[str, dict[str, float]] = {}
        for metric in metrics:
            value = actual.get(metric)
            if value is None or not isfinite(value):
                continue
            abs_tol = max(abs_tol_min, abs(value) * rel_tol)
            checks[metric] = {
                "expected": float(value),
                "abs_tol": float(abs_tol),
                "rel_tol": 0.0,
            }

        if not checks:
            continue
        locked[name] = {
            "checks": checks,
            "constraints": constraints,
            "deterministic": deterministic,
            "dt_sensitivity": dt_spec,
        }

    if not locked:
        raise typer.BadParameter(
            "No executable cases with finite metrics found in benchmark report."
        )
    return locked


@app.command("init")
def init_config(
    template: str = typer.Option("effective-stress", "--template"),
    out: Path = typer.Option(Path("examples/configs/effective_stress.yml"), "--out"),
) -> None:
    try:
        path = write_config_template(out, template=template)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    print(f"[green]Template written:[/green] {path}")


@app.command("validate")
def validate(
    config: Path = typer.Option(..., "--config"),
    check_backend: bool = typer.Option(False, "--check-backend"),
    require_backend_version_regex: str | None = typer.Option(
        None,
        "--require-backend-version-regex",
    ),
    require_backend_sha256: str | None = typer.Option(
        None,
        "--require-backend-sha256",
    ),
) -> None:
    cfg = load_project_config(config)
    cfg = _apply_opensees_env_override(cfg)
    if check_backend and cfg.analysis.solver_backend == "opensees":
        effective_version_regex = (
            require_backend_version_regex
            if require_backend_version_regex is not None
            else cfg.opensees.require_version_regex
        )
        effective_sha = (
            require_backend_sha256
            if require_backend_sha256 is not None
            else cfg.opensees.require_binary_sha256
        )
        probe = probe_opensees_executable(
            cfg.opensees.executable,
            extra_args=cfg.opensees.extra_args,
        )
        if probe.resolved is None:
            print(
                "[red]OpenSees executable not found:[/red] "
                f"{cfg.opensees.executable}"
            )
            raise typer.Exit(code=5)
        if not probe.available:
            print(
                "[red]OpenSees backend probe failed:[/red] "
                f"{probe.version}"
            )
            if probe.stderr.strip():
                print(f"[red]Probe stderr:[/red] {probe.stderr.strip()}")
            raise typer.Exit(code=5)
        requirement_errors = validate_backend_probe_requirements(
            probe,
            require_version_regex=effective_version_regex,
            require_binary_sha256=effective_sha,
        )
        if requirement_errors:
            print("[red]OpenSees backend requirement check failed:[/red]")
            for err in requirement_errors:
                print(f"- {err}")
            raise typer.Exit(code=5)
        print(f"[green]OpenSees executable[/green]: {probe.resolved}")
        if cfg.opensees.extra_args:
            print(f"[cyan]OpenSees extra args[/cyan]: {cfg.opensees.extra_args}")
        print(f"[cyan]OpenSees version probe[/cyan]: {probe.version}")
        print(f"[cyan]OpenSees binary sha256[/cyan]: {probe.binary_sha256}")
    print(f"[green]Valid config[/green]: {cfg.project_name}")


@app.command("run")
def run(
    config: Path = typer.Option(..., "--config"),
    motion: Path = typer.Option(..., "--motion"),
    out: Path = typer.Option(Path("out"), "--out"),
    backend: RunBackendMode = typer.Option("config", "--backend"),
    opensees_executable: str | None = typer.Option(None, "--opensees-executable"),
) -> None:
    cfg = load_project_config(config)
    cfg, backend_note = _apply_runtime_backend(
        cfg,
        backend=backend,
        opensees_executable=opensees_executable,
    )
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
    template: str = typer.Option("effective-stress-strict-plus", "--template"),
    backend: RunBackendMode = typer.Option("auto", "--backend"),
    opensees_executable: str | None = typer.Option(None, "--opensees-executable"),
) -> None:
    template_to_config = {
        "effective-stress": "effective_stress.yml",
        "effective-stress-strict-plus": "effective_stress_strict_plus.yml",
        "mkz-gqh-mock": "mkz_gqh_mock.yml",
        "mkz-gqh-eql": "mkz_gqh_eql.yml",
        "mkz-gqh-nonlinear": "mkz_gqh_nonlinear.yml",
    }
    config_name = template_to_config.get(template)
    if config_name is None:
        raise typer.BadParameter(
            f"Unknown template: {template}. "
            f"Allowed: {sorted(template_to_config)}"
        )

    repo_root = _repo_root()
    src_config = repo_root / "examples" / "configs" / config_name
    src_motion = repo_root / "examples" / "motions" / "sample_motion.csv"
    if not src_config.exists():
        raise typer.BadParameter(f"Sample config not found: {src_config}")
    if not src_motion.exists():
        raise typer.BadParameter(f"Sample motion not found: {src_motion}")

    out.mkdir(parents=True, exist_ok=True)
    config_out = out / "config.yml"
    motion_out = out / "motion.csv"
    shutil.copy2(src_config, config_out)
    shutil.copy2(src_motion, motion_out)

    cfg = load_project_config(config_out)
    cfg, backend_note = _apply_runtime_backend(
        cfg,
        backend=backend,
        opensees_executable=opensees_executable,
    )
    print(f"[cyan]Quickstart backend:[/cyan] {backend_note}")
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    mot = load_motion(motion_out, dt=dt, unit=cfg.motion.units)
    res = run_analysis(cfg, mot, output_dir=out / "runs")
    verify = verify_run(res.output_dir)

    summary = {
        "template": template,
        "backend": str(cfg.analysis.solver_backend),
        "backend_note": backend_note,
        "run_id": res.run_id,
        "run_status": res.status,
        "run_message": res.message,
        "run_dir": str(res.output_dir),
        "verify_ok": verify.ok,
    }
    summary_path = out / "quickstart_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[green]Quickstart summary:[/green] {summary_path}")
    print(f"[green]Run directory:[/green] {res.output_dir}")

    if res.status != "ok":
        raise typer.Exit(code=2)
    if not verify.ok:
        print("[red]Quickstart verify failed[/red]")
        raise typer.Exit(code=9)


@app.command("render-tcl")
def render_tcl_cmd(
    config: Path = typer.Option(..., "--config"),
    motion: Path = typer.Option(..., "--motion"),
    out: Path = typer.Option(Path("out/tcl"), "--out"),
) -> None:
    cfg = load_project_config(config)
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    mot = load_motion(motion, dt=dt, unit=cfg.motion.units)
    processed = preprocess_motion(mot, cfg.motion)

    out.mkdir(parents=True, exist_ok=True)
    motion_out = out / "motion_processed.csv"
    np.savetxt(motion_out, processed.acc, delimiter=",")

    script = render_tcl(cfg, motion_file=motion_out, output_dir=out)
    validate_tcl_script(script)
    tcl_out = out / "model.tcl"
    tcl_out.write_text(script, encoding="utf-8")

    print(f"[green]Tcl script written:[/green] {tcl_out}")
    print(f"[green]Processed motion written:[/green] {motion_out}")


@app.command("batch")
def batch(
    config: Path = typer.Option(..., "--config"),
    motions_dir: Path = typer.Option(..., "--motions-dir"),
    n_jobs: int = typer.Option(1, "--n-jobs"),
    out: Path = typer.Option(Path("out"), "--out"),
    backend: RunBackendMode = typer.Option("config", "--backend"),
    opensees_executable: str | None = typer.Option(None, "--opensees-executable"),
) -> None:
    cfg = load_project_config(config)
    cfg, backend_note = _apply_runtime_backend(
        cfg,
        backend=backend,
        opensees_executable=opensees_executable,
    )
    print(f"[cyan]Batch backend:[/cyan] {backend_note}")
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
    require_opensees: bool = typer.Option(False, "--require-opensees"),
    min_execution_coverage: float = typer.Option(0.0, "--min-execution-coverage"),
    require_explicit_checks: bool = typer.Option(False, "--require-explicit-checks"),
    opensees_executable: str | None = typer.Option(None, "--opensees-executable"),
    require_backend_version_regex: str | None = typer.Option(
        None,
        "--require-backend-version-regex",
    ),
    require_backend_sha256: str | None = typer.Option(
        None,
        "--require-backend-sha256",
    ),
) -> None:
    if not (0.0 <= min_execution_coverage <= 1.0):
        raise typer.BadParameter("--min-execution-coverage must be within [0, 1].")
    report = _run_benchmark_with_optional_override(
        suite,
        out,
        opensees_executable,
        require_backend_version_regex,
        require_backend_sha256,
    )
    _annotate_benchmark_policy(
        report,
        fail_on_skip=fail_on_skip,
        require_runs=require_runs,
        require_opensees=require_opensees,
        min_execution_coverage=min_execution_coverage,
        require_explicit_checks=require_explicit_checks,
        require_backend_version_regex=require_backend_version_regex,
        require_backend_sha256=require_backend_sha256,
    )
    report_path = out / f"benchmark_{suite}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[green]Benchmark report:[/green] {report_path}")
    _print_benchmark_coverage(report)
    if not bool(report.get("all_passed", False)):
        raise typer.Exit(code=3)
    _enforce_benchmark_strict_policy(
        report,
        fail_on_skip=fail_on_skip,
        require_runs=require_runs,
    )
    _enforce_backend_ready_policy(
        report,
        suite=suite,
        require_opensees=require_opensees,
    )
    _enforce_execution_coverage_policy(
        report,
        min_execution_coverage=min_execution_coverage,
    )
    _enforce_explicit_checks_policy(
        report,
        require_explicit_checks=require_explicit_checks,
    )


@app.command("campaign")
def campaign(
    suite: str = typer.Option("opensees-parity", "--suite"),
    out: Path = typer.Option(Path("out/campaign"), "--out"),
    fail_on_skip: bool = typer.Option(False, "--fail-on-skip"),
    require_runs: int = typer.Option(0, "--require-runs"),
    require_opensees: bool = typer.Option(False, "--require-opensees"),
    min_execution_coverage: float = typer.Option(0.0, "--min-execution-coverage"),
    require_explicit_checks: bool = typer.Option(False, "--require-explicit-checks"),
    verify_require_runs: int = typer.Option(1, "--verify-require-runs"),
    tolerance: float = typer.Option(1.0e-8, "--tolerance"),
    require_checksums: bool = typer.Option(True, "--require-checksums/--allow-missing-checksums"),
    opensees_executable: str | None = typer.Option(None, "--opensees-executable"),
    require_backend_version_regex: str | None = typer.Option(
        None,
        "--require-backend-version-regex",
    ),
    require_backend_sha256: str | None = typer.Option(
        None,
        "--require-backend-sha256",
    ),
) -> None:
    if not (0.0 <= min_execution_coverage <= 1.0):
        raise typer.BadParameter("--min-execution-coverage must be within [0, 1].")
    out.mkdir(parents=True, exist_ok=True)
    report = _run_benchmark_with_optional_override(
        suite,
        out,
        opensees_executable,
        require_backend_version_regex,
        require_backend_sha256,
    )
    _annotate_benchmark_policy(
        report,
        fail_on_skip=fail_on_skip,
        require_runs=require_runs,
        require_opensees=require_opensees,
        min_execution_coverage=min_execution_coverage,
        require_explicit_checks=require_explicit_checks,
        require_backend_version_regex=require_backend_version_regex,
        require_backend_sha256=require_backend_sha256,
    )
    benchmark_path = out / f"benchmark_{suite}.json"
    benchmark_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[green]Benchmark report:[/green] {benchmark_path}")
    _print_benchmark_coverage(report)

    if not bool(report.get("all_passed", False)):
        raise typer.Exit(code=3)
    _enforce_benchmark_strict_policy(
        report,
        fail_on_skip=fail_on_skip,
        require_runs=require_runs,
    )
    _enforce_backend_ready_policy(
        report,
        suite=suite,
        require_opensees=require_opensees,
    )
    _enforce_execution_coverage_policy(
        report,
        min_execution_coverage=min_execution_coverage,
    )
    _enforce_explicit_checks_policy(
        report,
        require_explicit_checks=require_explicit_checks,
    )

    verify = verify_batch(
        out,
        tolerance=tolerance,
        require_checksums=require_checksums,
        require_runs=verify_require_runs,
    )
    verify_dict = verify.as_dict()
    _annotate_verify_policy(verify_dict, require_runs=verify_require_runs)
    verify_path = out / "verify_batch_report.json"
    verify_path.write_text(json.dumps(verify_dict, indent=2), encoding="utf-8")
    print(f"[green]Verify batch report:[/green] {verify_path}")

    summary = summarize_campaign(report, verify_dict)
    summary_json = out / "campaign_summary.json"
    summary_md = out / "campaign_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(render_summary_markdown(summary), encoding="utf-8")
    print(f"[green]Campaign summary JSON:[/green] {summary_json}")
    print(f"[green]Campaign summary Markdown:[/green] {summary_md}")

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


@app.command("lock-golden")
def lock_golden(
    benchmark_report: Path = typer.Option(..., "--benchmark-report"),
    suite: str | None = typer.Option(None, "--suite"),
    golden_out: Path | None = typer.Option(None, "--golden-out"),
    metrics: str = typer.Option(
        "pga,ru_max,delta_u_max,sigma_v_eff_min",
        "--metrics",
    ),
    rel_tol: float = typer.Option(0.05, "--rel-tol"),
    abs_tol_min: float = typer.Option(1.0e-6, "--abs-tol-min"),
    require_all_passed: bool = typer.Option(True, "--require-all-passed/--allow-failed"),
    require_no_skip: bool = typer.Option(False, "--require-no-skip"),
) -> None:
    if rel_tol < 0.0:
        raise typer.BadParameter("--rel-tol must be >= 0.")
    if abs_tol_min < 0.0:
        raise typer.BadParameter("--abs-tol-min must be >= 0.")
    report = _load_json_mapping(benchmark_report)
    report_suite_raw = report.get("suite")
    report_suite = str(report_suite_raw) if isinstance(report_suite_raw, str) else ""
    selected_suite = suite or report_suite
    if not selected_suite:
        raise typer.BadParameter("Suite could not be determined. Provide --suite.")

    if require_all_passed and not bool(report.get("all_passed", False)):
        raise typer.BadParameter("Benchmark report is not all_passed; cannot lock golden.")
    skipped_raw = report.get("skipped", 0)
    skipped = int(skipped_raw) if isinstance(skipped_raw, (int, float, str)) else 0
    if require_no_skip and skipped > 0:
        raise typer.BadParameter(
            f"Benchmark report has skipped={skipped}; use --allow-failed or rerun without skips."
        )

    metric_names = _parse_metric_names(metrics)
    golden = _build_locked_golden(
        report,
        metrics=metric_names,
        rel_tol=rel_tol,
        abs_tol_min=abs_tol_min,
    )
    out_path = golden_out or _default_golden_path_from_suite(selected_suite)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(golden, indent=2), encoding="utf-8")
    print(f"[green]Golden metrics written:[/green] {out_path}")
    print(f"[cyan]Locked cases:[/cyan] {len(golden)}")


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
    backend: RunBackendMode = typer.Option("config", "--backend"),
    opensees_executable: str | None = typer.Option(None, "--opensees-executable"),
) -> None:
    cfg = load_project_config(config)
    cfg, backend_note = _apply_runtime_backend(
        cfg,
        backend=backend,
        opensees_executable=opensees_executable,
    )
    print(f"[cyan]dt-check backend:[/cyan] {backend_note}")
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

    if (
        rs_base.spectra_psa.shape != rs_half.spectra_psa.shape
        or rs_base.spectra_periods.shape != rs_half.spectra_periods.shape
    ):
        print("[red]dt-check failed:[/red] spectra shape mismatch")
        raise typer.Exit(code=8)
    if not np.allclose(
        rs_base.spectra_periods,
        rs_half.spectra_periods,
        rtol=1.0e-10,
        atol=1.0e-12,
    ):
        print("[red]dt-check failed:[/red] period grid mismatch")
        raise typer.Exit(code=8)

    min_period = 10.0 * dt_base
    mask = rs_base.spectra_periods >= min_period
    if not np.any(mask):
        mask = np.ones_like(rs_base.spectra_periods, dtype=bool)

    base_sel = rs_base.spectra_psa[mask]
    half_sel = rs_half.spectra_psa[mask]
    denom = np.maximum(np.abs(half_sel), 1.0e-10)
    rel = np.abs(base_sel - half_sel) / denom
    max_rel = float(np.max(rel))
    mean_rel = float(np.mean(rel))

    summary = {
        "dt_base": dt_base,
        "dt_half": cfg_half.analysis.dt,
        "max_relative_psa_diff": max_rel,
        "mean_relative_psa_diff": mean_rel,
        "min_period_used_s": float(np.min(rs_base.spectra_periods[mask])),
        "points_used": int(base_sel.size),
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
