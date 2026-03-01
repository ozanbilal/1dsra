from __future__ import annotations

import os
from pathlib import Path

import pytest
from dsra1d.config import load_project_config
from dsra1d.motion import load_motion
from dsra1d.pipeline import run_analysis

RUN_REAL = os.getenv("DSRA1D_RUN_OPENSEES_INTEGRATION", "0") == "1"


@pytest.mark.skipif(
    not RUN_REAL,
    reason="Set DSRA1D_RUN_OPENSEES_INTEGRATION=1 to enable real OpenSees integration test.",
)
def test_opensees_integration_real_binary(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "opensees"
    cfg.analysis.retries = 0
    cfg.opensees.executable = os.getenv("OPENSEES_EXE", "OpenSees")

    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    assert result.status == "ok"
    assert result.hdf5_path.exists()
    assert result.sqlite_path.exists()
