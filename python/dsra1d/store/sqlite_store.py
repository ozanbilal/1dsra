from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from dsra1d.config.models import ProjectConfig
from dsra1d.interop.opensees.tcl import LayerSlice
from dsra1d.post.spectra import Spectra

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
    ru_time: np.ndarray,
    ru: np.ndarray,
    delta_u: np.ndarray,
    sigma_v_ref: float,
    sigma_v_eff: np.ndarray,
    mesh_slices: list[LayerSlice],
    artifacts: Iterable[tuple[str, str]] = (),
    checksums: Iterable[tuple[str, str]] = (),
) -> Path:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(DDL)
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
