from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Literal, cast

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dsra1d.config import load_project_config, write_config_template
from dsra1d.interop.opensees import resolve_opensees_executable
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.post import compute_spectra

RunBackendMode = Literal["config", "auto", "opensees", "mock", "linear", "eql", "nonlinear"]
ResolvedBackend = Literal["opensees", "mock", "linear", "eql", "nonlinear"]


class RunRequest(BaseModel):
    config_path: str
    motion_path: str
    output_root: str = "out/web"
    backend: RunBackendMode = "config"
    opensees_executable: str | None = None


class RunResponse(BaseModel):
    run_id: str
    output_dir: str
    status: str
    message: str
    backend: str


class RunSummary(BaseModel):
    run_id: str
    output_dir: str
    timestamp_utc: str = ""
    solver_backend: str = "unknown"
    status: str = "unknown"
    message: str = ""
    pga: float | None = None
    ru_max: float | None = None
    delta_u_max: float | None = None
    sigma_v_eff_min: float | None = None


class ConfigTemplateRequest(BaseModel):
    template: Literal[
        "effective-stress",
        "effective-stress-strict-plus",
        "mkz-gqh-mock",
        "mkz-gqh-eql",
        "mkz-gqh-nonlinear",
    ] = "effective-stress"
    output_dir: str = ""
    file_name: str = ""


class ConfigTemplateResponse(BaseModel):
    template: str
    config_path: str
    status: str
    message: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_output_root() -> Path:
    return _repo_root() / "out" / "ui"


def _default_config_root() -> Path:
    return _repo_root() / "out" / "ui" / "configs"


def _safe_real_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _collect_runs(output_root: Path) -> list[Path]:
    if not output_root.exists() or not output_root.is_dir():
        return []
    runs: list[Path] = []
    for p in sorted(output_root.iterdir()):
        if not p.is_dir():
            continue
        if (
            (p / "results.h5").exists()
            and (p / "results.sqlite").exists()
            and (p / "run_meta.json").exists()
        ):
            runs.append(p)
    return runs


def _read_metrics(sqlite_path: Path) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if not sqlite_path.exists():
        return metrics
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute("SELECT name, value FROM metrics").fetchall()
        for name, value in rows:
            try:
                metrics[str(name)] = float(value)
            except (TypeError, ValueError):
                continue
    finally:
        conn.close()
    return metrics


def _read_run_meta(run_dir: Path) -> dict[str, str]:
    meta_path = run_dir / "run_meta.json"
    if not meta_path.exists():
        return {}
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("timestamp_utc", "solver_backend", "status", "message"):
        value = raw.get(key)
        if isinstance(value, str):
            out[key] = value
    return out


def _downsample_pair(
    x: list[float],
    y: list[float],
    *,
    max_points: int,
) -> tuple[list[float], list[float]]:
    n = min(len(x), len(y))
    if n <= max_points:
        return x[:n], y[:n]
    step = max(1, n // max_points)
    return x[:n:step], y[:n:step]


def _estimate_dt(time_axis: np.ndarray) -> float:
    if time_axis.size > 1:
        dt = float(np.median(np.diff(time_axis)))
        if np.isfinite(dt) and dt > 0.0:
            return dt
    return 1.0


def _apply_runtime_backend(
    requested: RunBackendMode,
    *,
    config_backend: str,
    executable: str,
) -> tuple[ResolvedBackend, str]:
    def normalize(raw: str) -> ResolvedBackend:
        if raw not in {"opensees", "mock", "linear", "eql", "nonlinear"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported config solver backend: {raw}",
            )
        return cast(ResolvedBackend, raw)

    if requested == "config":
        normalized = normalize(config_backend)
        return normalized, normalized

    if requested == "auto":
        if config_backend == "opensees":
            resolved = resolve_opensees_executable(executable)
            if resolved is None:
                return "mock", "mock (auto-fallback: OpenSees missing)"
            return "opensees", f"opensees ({resolved})"
        normalized = normalize(config_backend)
        return normalized, normalized

    if requested == "opensees":
        resolved = resolve_opensees_executable(executable)
        if resolved is None:
            raise HTTPException(
                status_code=400,
                detail=f"OpenSees executable not found: {executable}",
            )
        return "opensees", f"opensees ({resolved})"

    if requested in {"mock", "linear", "eql", "nonlinear"}:
        return requested, f"{requested} (forced)"

    raise HTTPException(status_code=400, detail=f"Unsupported backend mode: {requested}")


def create_app() -> FastAPI:
    app = FastAPI(title="1DSRA Web API", version="0.1.0")
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/config/templates")
    def list_config_templates() -> dict[str, list[str]]:
        return {
            "templates": [
                "effective-stress",
                "effective-stress-strict-plus",
                "mkz-gqh-mock",
                "mkz-gqh-eql",
                "mkz-gqh-nonlinear",
            ]
        }

    @app.post("/api/config/template", response_model=ConfigTemplateResponse)
    def create_config_template(payload: ConfigTemplateRequest) -> ConfigTemplateResponse:
        out_root = (
            _safe_real_path(payload.output_dir)
            if payload.output_dir.strip()
            else _default_config_root()
        )
        out_root.mkdir(parents=True, exist_ok=True)
        file_name = payload.file_name.strip() or f"{payload.template}.yml"
        if not file_name.lower().endswith((".yml", ".yaml")):
            file_name = f"{file_name}.yml"
        out_path = out_root / file_name
        written = write_config_template(out_path, template=payload.template)
        return ConfigTemplateResponse(
            template=payload.template,
            config_path=str(written),
            status="ok",
            message="Config template created.",
        )

    @app.get("/api/runs", response_model=list[RunSummary])
    def list_runs(output_root: str = Query(default="")) -> list[RunSummary]:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        items: list[RunSummary] = []
        for run_dir in reversed(_collect_runs(root)):
            meta = _read_run_meta(run_dir)
            metrics = _read_metrics(run_dir / "results.sqlite")
            items.append(
                RunSummary(
                    run_id=run_dir.name,
                    output_dir=str(run_dir),
                    timestamp_utc=meta.get("timestamp_utc", ""),
                    solver_backend=meta.get("solver_backend", "unknown"),
                    status=meta.get("status", "unknown"),
                    message=meta.get("message", ""),
                    pga=metrics.get("pga"),
                    ru_max=metrics.get("ru_max"),
                    delta_u_max=metrics.get("delta_u_max"),
                    sigma_v_eff_min=metrics.get("sigma_v_eff_min"),
                )
            )
        return items

    @app.get("/api/runs/{run_id}/signals")
    def run_signals(
        run_id: str,
        output_root: str = Query(default=""),
        max_points: int = Query(default=4000, ge=200, le=40000),
        max_spectral_points: int = Query(default=2400, ge=100, le=40000),
    ) -> dict[str, object]:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        run_dir = root / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        rs = load_result(run_dir)
        time = rs.time
        acc = rs.acc_surface
        n = int(min(time.size, acc.size))
        if n <= 1:
            raise HTTPException(status_code=400, detail="Run has insufficient signal samples.")
        time_list = [float(v) for v in time[:n]]
        acc_list = [float(v) for v in acc[:n]]
        time_list, acc_list = _downsample_pair(time_list, acc_list, max_points=max_points)

        dt_s = _estimate_dt(rs.time)
        spectra_live = compute_spectra(
            np.asarray(rs.acc_surface, dtype=np.float64),
            dt=dt_s,
            damping=0.05,
        )
        period_list = [float(v) for v in spectra_live.periods]
        psa_list = [float(v) for v in spectra_live.psa]
        period_list, psa_list = _downsample_pair(
            period_list,
            psa_list,
            max_points=max_spectral_points,
        )

        freq_list = [float(v) for v in rs.transfer_freq_hz]
        tf_list = [float(v) for v in rs.transfer_abs]
        freq_list, tf_list = _downsample_pair(freq_list, tf_list, max_points=max_spectral_points)

        def make_time_axis(size: int) -> list[float]:
            if size <= 0:
                return []
            if rs.ru_time.size >= size:
                return [float(v) for v in rs.ru_time[:size]]
            if rs.time.size >= size:
                return [float(v) for v in rs.time[:size]]
            if rs.time.size > 1:
                dt_guess = float(rs.time[1] - rs.time[0])
                return [float(i) * dt_guess for i in range(size)]
            return [float(i) for i in range(size)]

        n_ru = int(rs.ru.size)
        ru_list = [float(v) for v in rs.ru[:n_ru]]
        ru_time_list = make_time_axis(n_ru)
        if n_ru > max_points:
            step = max(1, n_ru // max_points)
            ru_time_list = ru_time_list[::step]
            ru_list = ru_list[::step]

        n_du = int(rs.delta_u.size)
        delta_u_list = [float(v) for v in rs.delta_u[:n_du]]
        delta_u_time_list = make_time_axis(n_du)
        if n_du > max_points:
            step = max(1, n_du // max_points)
            delta_u_time_list = delta_u_time_list[::step]
            delta_u_list = delta_u_list[::step]

        n_sig = int(rs.sigma_v_eff.size)
        sigma_v_eff_list = [float(v) for v in rs.sigma_v_eff[:n_sig]]
        sigma_time_list = make_time_axis(n_sig)
        if n_sig > max_points:
            step = max(1, n_sig // max_points)
            sigma_time_list = sigma_time_list[::step]
            sigma_v_eff_list = sigma_v_eff_list[::step]

        pga = float(np.max(np.abs(acc))) if acc.size > 0 else 0.0
        ru_max = float(np.max(rs.ru)) if rs.ru.size > 0 else 0.0
        delta_u_max = float(np.max(rs.delta_u)) if rs.delta_u.size > 0 else 0.0
        sigma_v_eff_min = float(np.min(rs.sigma_v_eff)) if rs.sigma_v_eff.size > 0 else 0.0
        return {
            "run_id": run_id,
            "time_s": time_list,
            "surface_acc_m_s2": acc_list,
            "period_s": period_list,
            "psa_m_s2": psa_list,
            "spectra_source": "recomputed_from_surface_acc",
            "dt_s": float(dt_s),
            "delta_t": float(dt_s),
            "delta_t_s": float(dt_s),
            "freq_hz": freq_list,
            "transfer_abs": tf_list,
            "ru_time_s": ru_time_list,
            "ru_t": ru_time_list,
            "ru": ru_list,
            "delta_u_time_s": delta_u_time_list,
            "delta_u_t": delta_u_time_list,
            "delta_u": delta_u_list,
            "sigma_v_eff_time_s": sigma_time_list,
            "sigma_v_eff_t": sigma_time_list,
            "sigma_v_eff": sigma_v_eff_list,
            "sigma_v_ref": float(rs.sigma_v_ref),
            "pga": float(pga),
            "ru_max": float(ru_max),
            "delta_u_max": float(delta_u_max),
            "sigma_v_eff_min": float(sigma_v_eff_min),
        }

    @app.get("/api/runs/{run_id}/surface-acc.csv")
    def download_surface_csv(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> PlainTextResponse:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        run_dir = root / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        rs = load_result(run_dir)
        n = int(min(rs.time.size, rs.acc_surface.size))
        if n <= 1:
            raise HTTPException(status_code=400, detail="Run has insufficient signal samples.")
        dt_s = _estimate_dt(rs.time)
        lines = ["time_s,acc_m_s2,delta_t_s"]
        for t, a in zip(rs.time[:n], rs.acc_surface[:n], strict=False):
            lines.append(f"{float(t):.8f},{float(a):.10e},{dt_s:.8e}")
        payload = "\n".join(lines)
        headers = {"Content-Disposition": f'attachment; filename="{run_id}_surface_acc.csv"'}
        return PlainTextResponse(payload, media_type="text/csv", headers=headers)

    @app.get("/api/runs/{run_id}/pwp-effective.csv")
    def download_pwp_effective_csv(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> PlainTextResponse:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        run_dir = root / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        rs = load_result(run_dir)
        n = int(rs.ru.size)
        if n <= 0:
            raise HTTPException(status_code=400, detail="Run has no PWP/ru samples.")
        if rs.ru_time.size >= n:
            t_series = rs.ru_time[:n]
        elif rs.time.size >= n:
            t_series = rs.time[:n]
        else:
            t_series = np.arange(n, dtype=np.float64) * float(rs.dt_s)
        dt_s = _estimate_dt(t_series)
        lines = ["time_s,ru,delta_u,sigma_v_eff,delta_t_s"]
        for i in range(n):
            t = float(t_series[i])
            ru = float(rs.ru[i]) if i < rs.ru.size else float("nan")
            du = float(rs.delta_u[i]) if i < rs.delta_u.size else float("nan")
            sig = float(rs.sigma_v_eff[i]) if i < rs.sigma_v_eff.size else float("nan")
            lines.append(f"{t:.8f},{ru:.10e},{du:.10e},{sig:.10e},{dt_s:.8e}")
        payload = "\n".join(lines)
        headers = {"Content-Disposition": f'attachment; filename="{run_id}_pwp_effective.csv"'}
        return PlainTextResponse(payload, media_type="text/csv", headers=headers)

    @app.get("/api/runs/{run_id}/download/{artifact}")
    def download_artifact(
        run_id: str,
        artifact: str,
        output_root: str = Query(default=""),
    ) -> FileResponse:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        run_dir = root / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        allowed = {
            "results.h5": "results.h5",
            "results.sqlite": "results.sqlite",
            "surface_acc.out": "surface_acc.out",
            "run_meta.json": "run_meta.json",
        }
        if artifact not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported artifact: {artifact}")
        path = run_dir / allowed[artifact]
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact}")
        return FileResponse(path)

    @app.post("/api/run", response_model=RunResponse)
    def execute_run(payload: RunRequest) -> RunResponse:
        cfg = load_project_config(payload.config_path)
        if payload.opensees_executable:
            cfg.opensees.executable = payload.opensees_executable
        backend, backend_note = _apply_runtime_backend(
            payload.backend,
            config_backend=cfg.analysis.solver_backend,
            executable=cfg.opensees.executable,
        )
        cfg.analysis.solver_backend = backend
        if backend == "opensees":
            resolved = resolve_opensees_executable(cfg.opensees.executable)
            if resolved is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"OpenSees executable not found: {cfg.opensees.executable}",
                )
            cfg.opensees.executable = str(resolved)

        dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
        motion = load_motion(payload.motion_path, dt=dt, unit=cfg.motion.units)
        result = run_analysis(cfg, motion, output_dir=payload.output_root)
        return RunResponse(
            run_id=result.run_id,
            output_dir=str(result.output_dir),
            status=result.status,
            message=f"{backend_note} | {result.message}",
            backend=backend,
        )

    @app.get("/")
    def web_root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    return app


app = create_app()
