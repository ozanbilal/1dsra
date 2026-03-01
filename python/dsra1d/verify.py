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

        checksum_rows = conn.execute(
            "SELECT artifact, sha256 FROM checksums WHERE run_id = ?",
            (sqlite_run_id,),
        ).fetchall()
        checksum_map_sqlite = {str(k): str(v) for k, v in checksum_rows}

    with h5py.File(h5_path, "r") as h5:
        acc = np.array(h5["/signals/surface_acc"], dtype=np.float64)
        ru = np.array(h5["/pwp/ru"], dtype=np.float64)

    pga_h5 = float(np.max(np.abs(acc)))
    ru_max_h5 = float(np.max(ru))
    pga_sql = metric_map.get("pga", float("nan"))
    ru_max_sql = metric_map.get("ru_max", float("nan"))
    details["pga_hdf5"] = pga_h5
    details["pga_sqlite"] = pga_sql
    details["ru_max_hdf5"] = ru_max_h5
    details["ru_max_sqlite"] = ru_max_sql

    checks["run_id_dir_vs_meta"] = meta_run_id == root.name
    checks["run_id_meta_vs_sqlite"] = meta_run_id == sqlite_run_id
    checks["metrics_pga_match"] = abs(pga_h5 - pga_sql) <= tolerance
    checks["metrics_ru_max_match"] = abs(ru_max_h5 - ru_max_sql) <= tolerance

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
