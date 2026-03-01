from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np


@dataclass(slots=True)
class VerificationReport:
    ok: bool
    checks: dict[str, bool]
    details: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "checks": self.checks, "details": self.details}


@dataclass(slots=True)
class BatchVerificationReport:
    ok: bool
    total_runs: int
    passed_runs: int
    failed_runs: int
    reports: dict[str, dict[str, object]]

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "total_runs": self.total_runs,
            "passed_runs": self.passed_runs,
            "failed_runs": self.failed_runs,
            "reports": self.reports,
        }


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _safe_float(x: object, default: float = float("nan")) -> float:
    if isinstance(x, bool):
        return float(x)
    if isinstance(x, int | float):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return default
    return default


def verify_run(
    output_dir: str | Path,
    *,
    tolerance: float = 1.0e-8,
    require_checksums: bool = True,
) -> VerificationReport:
    root = Path(output_dir)
    h5_path = root / "results.h5"
    sqlite_path = root / "results.sqlite"
    meta_path = root / "run_meta.json"

    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    files_present = h5_path.exists() and sqlite_path.exists() and meta_path.exists()
    checks["files_present"] = files_present
    details["hdf5_path"] = str(h5_path)
    details["sqlite_path"] = str(sqlite_path)
    details["meta_path"] = str(meta_path)
    if not files_present:
        return VerificationReport(ok=False, checks=checks, details=details)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_run_id = str(meta.get("run_id", ""))
    meta_checksums_raw = meta.get("checksums", {})
    meta_checksums = meta_checksums_raw if isinstance(meta_checksums_raw, dict) else {}
    details["run_id_dir"] = root.name
    details["run_id_meta"] = meta_run_id
    pwp_effective_row: tuple[object, ...] | None = None
    pwp_effective_error = ""

    try:
        with sqlite3.connect(sqlite_path) as conn:
            run_row = conn.execute(
                "SELECT run_id FROM runs ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            sqlite_run_id = str(run_row[0]) if run_row else ""
            details["run_id_sqlite"] = sqlite_run_id

            metrics_rows = conn.execute(
                "SELECT name, value FROM metrics WHERE run_id = ?",
                (sqlite_run_id,),
            ).fetchall()
            metric_map = {str(name): _safe_float(value) for name, value in metrics_rows}

            try:
                checksum_rows = conn.execute(
                    "SELECT artifact, sha256 FROM checksums WHERE run_id = ?",
                    (sqlite_run_id,),
                ).fetchall()
            except sqlite3.OperationalError:
                checksum_rows = []
            checksum_map_sqlite = {str(k): str(v) for k, v in checksum_rows}

            try:
                pwp_effective_row = conn.execute(
                    """
                    SELECT
                      COUNT(*),
                      MIN(t),
                      MAX(t),
                      MAX(delta_u),
                      MIN(sigma_v_eff)
                    FROM pwp_effective_stats
                    WHERE run_id = ?
                    """,
                    (sqlite_run_id,),
                ).fetchone()
                pwp_effective_error = ""
            except sqlite3.OperationalError as exc:
                pwp_effective_row = None
                pwp_effective_error = str(exc)
    except sqlite3.Error as exc:
        checks["sqlite_readable"] = False
        details["sqlite_error"] = str(exc)
        return VerificationReport(ok=False, checks=checks, details=details)

    try:
        with h5py.File(h5_path, "r") as h5:
            acc = np.array(h5["/signals/surface_acc"], dtype=np.float64)
            ru_time = np.array(h5["/pwp/time"], dtype=np.float64)
            ru = np.array(h5["/pwp/ru"], dtype=np.float64)
            has_delta_u = "/pwp/delta_u" in h5
            has_sigma_v_ref = "/pwp/sigma_v_ref" in h5
            has_sigma_v_eff = "/pwp/sigma_v_eff" in h5
            delta_u = (
                np.array(h5["/pwp/delta_u"], dtype=np.float64)
                if has_delta_u
                else np.array([], dtype=np.float64)
            )
            sigma_v_ref_arr = (
                np.array(h5["/pwp/sigma_v_ref"], dtype=np.float64)
                if has_sigma_v_ref
                else np.array([], dtype=np.float64)
            )
            sigma_v_eff = (
                np.array(h5["/pwp/sigma_v_eff"], dtype=np.float64)
                if has_sigma_v_eff
                else np.array([], dtype=np.float64)
            )
    except OSError as exc:
        checks["hdf5_readable"] = False
        details["hdf5_error"] = str(exc)
        return VerificationReport(ok=False, checks=checks, details=details)

    pga_h5 = float(np.max(np.abs(acc)))
    ru_max_h5 = float(np.max(ru))
    delta_u_max_h5 = float(np.max(delta_u)) if delta_u.size > 0 else float("nan")
    sigma_v_ref_h5 = (
        float(sigma_v_ref_arr.reshape(-1)[0])
        if sigma_v_ref_arr.size > 0
        else float("nan")
    )
    sigma_v_eff_min_h5 = float(np.min(sigma_v_eff)) if sigma_v_eff.size > 0 else float("nan")
    pga_sql = metric_map.get("pga", float("nan"))
    ru_max_sql = metric_map.get("ru_max", float("nan"))
    delta_u_max_sql = metric_map.get("delta_u_max", float("nan"))
    sigma_v_ref_sql = metric_map.get("sigma_v_ref", float("nan"))
    sigma_v_eff_min_sql = metric_map.get("sigma_v_eff_min", float("nan"))
    details["pga_hdf5"] = pga_h5
    details["pga_sqlite"] = pga_sql
    details["ru_max_hdf5"] = ru_max_h5
    details["ru_max_sqlite"] = ru_max_sql
    details["delta_u_max_hdf5"] = delta_u_max_h5
    details["delta_u_max_sqlite"] = delta_u_max_sql
    details["sigma_v_ref_hdf5"] = sigma_v_ref_h5
    details["sigma_v_ref_sqlite"] = sigma_v_ref_sql
    details["sigma_v_eff_min_hdf5"] = sigma_v_eff_min_h5
    details["sigma_v_eff_min_sqlite"] = sigma_v_eff_min_sql

    checks["run_id_dir_vs_meta"] = meta_run_id == root.name
    checks["run_id_meta_vs_sqlite"] = meta_run_id == sqlite_run_id
    checks["metrics_pga_match"] = abs(pga_h5 - pga_sql) <= tolerance
    checks["metrics_ru_max_match"] = abs(ru_max_h5 - ru_max_sql) <= tolerance
    checks["metrics_delta_u_max_match"] = (
        abs(delta_u_max_h5 - delta_u_max_sql) <= tolerance
        if ("delta_u_max" in metric_map and delta_u.size > 0)
        else True
    )
    checks["metrics_sigma_v_ref_match"] = (
        abs(sigma_v_ref_h5 - sigma_v_ref_sql) <= tolerance
        if ("sigma_v_ref" in metric_map and sigma_v_ref_arr.size > 0)
        else True
    )
    checks["metrics_sigma_v_eff_min_match"] = (
        abs(sigma_v_eff_min_h5 - sigma_v_eff_min_sql) <= tolerance
        if ("sigma_v_eff_min" in metric_map and sigma_v_eff.size > 0)
        else True
    )
    checks["pwp_effective_table_readable"] = pwp_effective_row is not None
    has_effective_h5 = (
        (ru_time.size > 0)
        and (delta_u.size > 0)
        and (sigma_v_eff.size > 0)
    )

    checks["pwp_effective_rows_match"] = True
    checks["pwp_effective_time_start_match"] = True
    checks["pwp_effective_time_end_match"] = True
    checks["pwp_effective_delta_u_max_match"] = True
    checks["pwp_effective_sigma_v_eff_min_match"] = True

    if pwp_effective_row is None:
        details["pwp_effective_error"] = pwp_effective_error
        if has_effective_h5:
            checks["pwp_effective_rows_match"] = False
            checks["pwp_effective_time_start_match"] = False
            checks["pwp_effective_time_end_match"] = False
            checks["pwp_effective_delta_u_max_match"] = False
            checks["pwp_effective_sigma_v_eff_min_match"] = False
    else:
        row_count = int(_safe_float(pwp_effective_row[0], 0.0))
        t_min_sql = _safe_float(pwp_effective_row[1], float("nan"))
        t_max_sql = _safe_float(pwp_effective_row[2], float("nan"))
        delta_u_max_sql_table = _safe_float(pwp_effective_row[3], float("nan"))
        sigma_v_eff_min_sql_table = _safe_float(pwp_effective_row[4], float("nan"))
        details["pwp_effective_rows_sqlite"] = row_count
        details["pwp_effective_t_min_sqlite"] = t_min_sql
        details["pwp_effective_t_max_sqlite"] = t_max_sql
        details["pwp_effective_delta_u_max_sqlite"] = delta_u_max_sql_table
        details["pwp_effective_sigma_v_eff_min_sqlite"] = sigma_v_eff_min_sql_table

        if has_effective_h5:
            t_min_h5 = float(ru_time[0])
            t_max_h5 = float(ru_time[-1])
            delta_u_max_h5_table = float(np.max(delta_u))
            sigma_v_eff_min_h5_table = float(np.min(sigma_v_eff))
            details["pwp_effective_rows_hdf5"] = int(ru_time.size)
            details["pwp_effective_t_min_hdf5"] = t_min_h5
            details["pwp_effective_t_max_hdf5"] = t_max_h5
            details["pwp_effective_delta_u_max_hdf5"] = delta_u_max_h5_table
            details["pwp_effective_sigma_v_eff_min_hdf5"] = sigma_v_eff_min_h5_table

            checks["pwp_effective_rows_match"] = row_count == int(ru_time.size)
            checks["pwp_effective_time_start_match"] = abs(t_min_sql - t_min_h5) <= tolerance
            checks["pwp_effective_time_end_match"] = abs(t_max_sql - t_max_h5) <= tolerance
            checks["pwp_effective_delta_u_max_match"] = (
                abs(delta_u_max_sql_table - delta_u_max_h5_table) <= tolerance
            )
            checks["pwp_effective_sigma_v_eff_min_match"] = (
                abs(sigma_v_eff_min_sql_table - sigma_v_eff_min_h5_table) <= tolerance
            )

    h5_hash_actual = _sha256_file(h5_path)
    sqlite_hash_actual = _sha256_file(sqlite_path)
    details["sha256_results_h5_actual"] = h5_hash_actual
    details["sha256_results_sqlite_actual"] = sqlite_hash_actual

    h5_hash_meta = str(meta_checksums.get("results.h5", ""))
    sqlite_hash_meta = str(meta_checksums.get("results.sqlite", ""))
    h5_hash_sqlite = checksum_map_sqlite.get("results.h5", "")
    details["sha256_results_h5_meta"] = h5_hash_meta
    details["sha256_results_sqlite_meta"] = sqlite_hash_meta
    details["sha256_results_h5_sqlite"] = h5_hash_sqlite

    if require_checksums:
        checks["checksum_h5_meta_exists"] = bool(h5_hash_meta)
        checks["checksum_h5_sqlite_exists"] = bool(h5_hash_sqlite)
        checks["checksum_sqlite_meta_exists"] = bool(sqlite_hash_meta)
    else:
        checks["checksum_h5_meta_exists"] = True
        checks["checksum_h5_sqlite_exists"] = True
        checks["checksum_sqlite_meta_exists"] = True

    checks["checksum_h5_meta_match"] = (
        (h5_hash_meta == h5_hash_actual) if h5_hash_meta else (not require_checksums)
    )
    checks["checksum_h5_sqlite_match"] = (
        (h5_hash_sqlite == h5_hash_actual) if h5_hash_sqlite else (not require_checksums)
    )
    checks["checksum_sqlite_meta_match"] = (
        (sqlite_hash_meta == sqlite_hash_actual)
        if sqlite_hash_meta
        else (not require_checksums)
    )

    ok = all(checks.values())
    return VerificationReport(ok=ok, checks=checks, details=details)


def _is_run_dir(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "results.h5").exists()
        and (path / "results.sqlite").exists()
        and (path / "run_meta.json").exists()
    )


def verify_batch(
    output_root: str | Path,
    *,
    tolerance: float = 1.0e-8,
    require_checksums: bool = True,
    require_runs: int = 1,
) -> BatchVerificationReport:
    root = Path(output_root)
    if not root.exists():
        return BatchVerificationReport(
            ok=False,
            total_runs=0,
            passed_runs=0,
            failed_runs=0,
            reports={"_batch": {"ok": False, "reason": f"Path not found: {root}"}},
        )
    if not root.is_dir():
        return BatchVerificationReport(
            ok=False,
            total_runs=0,
            passed_runs=0,
            failed_runs=0,
            reports={"_batch": {"ok": False, "reason": f"Not a directory: {root}"}},
        )

    run_dirs = sorted([p for p in root.iterdir() if _is_run_dir(p)])

    reports: dict[str, dict[str, object]] = {}
    passed = 0
    failed = 0

    for run_dir in run_dirs:
        try:
            rep = verify_run(
                run_dir,
                tolerance=tolerance,
                require_checksums=require_checksums,
            )
        except Exception as exc:  # defensive guard to keep batch verification progressing
            rep = VerificationReport(
                ok=False,
                checks={"unexpected_error": False},
                details={"exception": str(exc)},
            )
        reports[run_dir.name] = rep.as_dict()
        if rep.ok:
            passed += 1
        else:
            failed += 1

    total = len(run_dirs)
    ok = (failed == 0) and (total >= require_runs)
    return BatchVerificationReport(
        ok=ok,
        total_runs=total,
        passed_runs=passed,
        failed_runs=failed,
        reports=reports,
    )
