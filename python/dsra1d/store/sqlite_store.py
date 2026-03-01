from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from dsra1d.config.models import ProjectConfig
from dsra1d.interop.opensees.tcl import LayerSlice
from dsra1d.post.spectra import Spectra


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


def _as_float(value: object, default: float = float("nan")) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _layer_value(layer_map: dict[object, object], idx: int) -> float:
    val = layer_map.get(str(idx), layer_map.get(idx, float("nan")))
    return _as_float(val)


DDL = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  project_name TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS layers (
  run_id TEXT NOT NULL,
  idx INTEGER NOT NULL,
  name TEXT NOT NULL,
  thickness_m REAL NOT NULL,
  unit_weight_kN_m3 REAL NOT NULL,
  vs_m_s REAL NOT NULL,
  material TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS motions (
  run_id TEXT NOT NULL,
  npts INTEGER NOT NULL,
  dt REAL NOT NULL,
  pga REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
  run_id TEXT NOT NULL,
  name TEXT NOT NULL,
  value REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS spectra (
  run_id TEXT NOT NULL,
  period_s REAL NOT NULL,
  psa REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS transfer_function (
  run_id TEXT NOT NULL,
  freq_hz REAL NOT NULL,
  amplification REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pwp_stats (
  run_id TEXT NOT NULL,
  t REAL NOT NULL,
  ru REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pwp_effective_stats (
  run_id TEXT NOT NULL,
  t REAL NOT NULL,
  delta_u REAL NOT NULL,
  sigma_v_eff REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
  run_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mesh_slices (
  run_id TEXT NOT NULL,
  layer_idx INTEGER NOT NULL,
  layer_name TEXT NOT NULL,
  material TEXT NOT NULL,
  z_top REAL NOT NULL,
  z_bot REAL NOT NULL,
  dz REAL NOT NULL,
  n_sub INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS checksums (
  run_id TEXT NOT NULL,
  artifact TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  PRIMARY KEY (run_id, artifact)
);
CREATE TABLE IF NOT EXISTS eql_summary (
  run_id TEXT PRIMARY KEY,
  iterations INTEGER NOT NULL,
  converged INTEGER NOT NULL,
  max_change_last REAL NOT NULL,
  max_change_max REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS eql_layers (
  run_id TEXT NOT NULL,
  layer_idx INTEGER NOT NULL,
  vs_m_s REAL NOT NULL,
  damping REAL NOT NULL,
  gamma_eff REAL NOT NULL,
  gamma_max REAL NOT NULL
);
"""


def write_sqlite(
    path: Path,
    run_id: str,
    config: ProjectConfig,
    status: str,
    message: str,
    dt: float,
    acc_surface: np.ndarray,
    spectra_data: Spectra,
    transfer_freq_hz: np.ndarray,
    transfer_abs: np.ndarray,
    ru_time: np.ndarray,
    ru: np.ndarray,
    delta_u: np.ndarray,
    sigma_v_ref: float,
    sigma_v_eff: np.ndarray,
    mesh_slices: list[LayerSlice],
    eql_summary: dict[str, object] | None = None,
    artifacts: Iterable[tuple[str, str]] = (),
    checksums: Iterable[tuple[str, str]] = (),
) -> Path:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(DDL)
        # Keep per-run tables idempotent when a deterministic run-id is re-written.
        for table in (
            "layers",
            "motions",
            "metrics",
            "spectra",
            "transfer_function",
            "pwp_stats",
            "pwp_effective_stats",
            "artifacts",
            "mesh_slices",
            "checksums",
            "eql_summary",
            "eql_layers",
        ):
            conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        conn.execute(
            (
                "INSERT OR REPLACE INTO runs("
                "run_id, project_name, status, message"
                ") VALUES (?, ?, ?, ?)"
            ),
            (run_id, config.project_name, status, message),
        )

        for idx, layer in enumerate(config.profile.layers):
            conn.execute(
                """
                INSERT INTO layers(
                    run_id, idx, name, thickness_m, unit_weight_kN_m3, vs_m_s, material
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    idx,
                    layer.name,
                    layer.thickness_m,
                    layer.unit_weight_kn_m3,
                    layer.vs_m_s,
                    layer.material.value,
                ),
            )

        pga = float(np.max(np.abs(acc_surface)))
        conn.execute(
            "INSERT INTO motions(run_id, npts, dt, pga) VALUES (?, ?, ?, ?)",
            (run_id, int(acc_surface.size), dt, pga),
        )
        conn.execute(
            "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
            (run_id, "pga", pga),
        )
        conn.execute(
            "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
            (run_id, "ru_max", float(np.max(ru))),
        )
        conn.execute(
            "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
            (run_id, "delta_u_max", float(np.max(delta_u))),
        )
        conn.execute(
            "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
            (run_id, "sigma_v_ref", float(sigma_v_ref)),
        )
        conn.execute(
            "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
            (run_id, "sigma_v_eff_min", float(np.min(sigma_v_eff))),
        )

        conn.executemany(
            "INSERT INTO spectra(run_id, period_s, psa) VALUES (?, ?, ?)",
            [
                (run_id, float(t), float(s))
                for t, s in zip(spectra_data.periods, spectra_data.psa, strict=True)
            ],
        )
        conn.executemany(
            "INSERT INTO transfer_function(run_id, freq_hz, amplification) VALUES (?, ?, ?)",
            [
                (run_id, float(f), float(h))
                for f, h in zip(transfer_freq_hz, transfer_abs, strict=True)
            ],
        )
        conn.executemany(
            "INSERT INTO pwp_stats(run_id, t, ru) VALUES (?, ?, ?)",
            [(run_id, float(t), float(r)) for t, r in zip(ru_time, ru, strict=True)],
        )
        conn.executemany(
            "INSERT INTO pwp_effective_stats(run_id, t, delta_u, sigma_v_eff) VALUES (?, ?, ?, ?)",
            [
                (run_id, float(t), float(du), float(sve))
                for t, du, sve in zip(ru_time, delta_u, sigma_v_eff, strict=True)
            ],
        )
        conn.executemany(
            """
            INSERT INTO mesh_slices(
                run_id, layer_idx, layer_name, material, z_top, z_bot, dz, n_sub
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    s.index,
                    s.name,
                    s.material.value,
                    s.z_top_m,
                    s.z_bot_m,
                    s.dz_m,
                    s.n_sublayers,
                )
                for s in mesh_slices
            ],
        )
        conn.executemany(
            "INSERT INTO artifacts(run_id, kind, path) VALUES (?, ?, ?)",
            [(run_id, kind, path) for kind, path in artifacts],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO checksums(run_id, artifact, sha256) VALUES (?, ?, ?)",
            [(run_id, artifact, sha256) for artifact, sha256 in checksums],
        )
        if eql_summary is not None:
            iterations = _as_int(eql_summary.get("iterations", 0))
            converged = 1 if bool(eql_summary.get("converged", False)) else 0
            max_change_history_raw = eql_summary.get("max_change_history", [])
            max_change_history = (
                [float(v) for v in max_change_history_raw]
                if isinstance(max_change_history_raw, list)
                else []
            )
            max_change_last = (
                float(max_change_history[-1]) if max_change_history else 0.0
            )
            max_change_max = float(max(max_change_history)) if max_change_history else 0.0
            conn.execute(
                """
                INSERT INTO eql_summary(
                  run_id, iterations, converged, max_change_last, max_change_max
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, iterations, converged, max_change_last, max_change_max),
            )
            conn.execute(
                "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
                (run_id, "eql_iterations", float(iterations)),
            )
            conn.execute(
                "INSERT INTO metrics(run_id, name, value) VALUES (?, ?, ?)",
                (run_id, "eql_converged", float(converged)),
            )
            layer_vs_raw = eql_summary.get("layer_vs_m_s", {})
            layer_damping_raw = eql_summary.get("layer_damping", {})
            layer_gamma_eff_raw = eql_summary.get("layer_gamma_eff", {})
            layer_gamma_max_raw = eql_summary.get("layer_max_abs_strain", {})
            layer_vs = layer_vs_raw if isinstance(layer_vs_raw, dict) else {}
            layer_damping = layer_damping_raw if isinstance(layer_damping_raw, dict) else {}
            layer_gamma_eff = (
                layer_gamma_eff_raw if isinstance(layer_gamma_eff_raw, dict) else {}
            )
            layer_gamma_max = (
                layer_gamma_max_raw if isinstance(layer_gamma_max_raw, dict) else {}
            )
            layer_vs_map = {k: v for k, v in layer_vs.items()}
            layer_damping_map = {k: v for k, v in layer_damping.items()}
            layer_gamma_eff_map = {k: v for k, v in layer_gamma_eff.items()}
            layer_gamma_max_map = {k: v for k, v in layer_gamma_max.items()}
            layer_ids = sorted(
                {
                    _as_int(k, -1)
                    for k in (
                        set(layer_vs_map.keys())
                        | set(layer_damping_map.keys())
                        | set(layer_gamma_eff_map.keys())
                        | set(layer_gamma_max_map.keys())
                    )
                    if _as_int(k, -1) > 0
                }
            )
            conn.executemany(
                """
                INSERT INTO eql_layers(
                  run_id, layer_idx, vs_m_s, damping, gamma_eff, gamma_max
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        idx,
                        _layer_value(layer_vs_map, idx),
                        _layer_value(layer_damping_map, idx),
                        _layer_value(layer_gamma_eff_map, idx),
                        _layer_value(layer_gamma_max_map, idx),
                    )
                    for idx in layer_ids
                ],
            )
        conn.commit()
    finally:
        conn.close()

    return path


def write_checksums(
    path: Path,
    run_id: str,
    checksums: Iterable[tuple[str, str]],
) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(DDL)
        conn.executemany(
            "INSERT OR REPLACE INTO checksums(run_id, artifact, sha256) VALUES (?, ?, ?)",
            [(run_id, artifact, sha256) for artifact, sha256 in checksums],
        )
        conn.commit()
    finally:
        conn.close()
