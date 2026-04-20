from pathlib import Path

import numpy as np

from dsra1d.config import BoundaryCondition, load_project_config
from dsra1d.motion import build_boundary_excitation


def test_boundary_excitation_within_motion_is_direct() -> None:
    cfg = load_project_config(Path("examples/native/linear_3layer_sand.yml"))
    cfg.motion.input_type = "within"
    acc = np.array([0.2, -0.1, 0.3], dtype=np.float64)

    excitation = build_boundary_excitation(cfg, acc)

    assert np.allclose(excitation.raw_acceleration_m_s2, acc)
    assert np.allclose(excitation.within_acceleration_m_s2, acc)
    assert np.allclose(excitation.incident_acceleration_m_s2, acc)
    assert np.allclose(
        excitation.applied_acceleration(BoundaryCondition.RIGID),
        acc,
    )
    assert np.allclose(
        excitation.applied_acceleration(BoundaryCondition.ELASTIC_HALFSPACE),
        acc,
    )


def test_boundary_excitation_outcrop_motion_converts_once_for_both_boundary_paths() -> None:
    cfg = load_project_config(Path("examples/native/linear_3layer_sand.yml"))
    cfg.motion.input_type = "outcrop"
    acc = np.array([0.2, -0.1, 0.3], dtype=np.float64)

    excitation = build_boundary_excitation(cfg, acc)
    expected = 0.5 * acc

    assert np.allclose(excitation.raw_acceleration_m_s2, acc)
    assert np.allclose(excitation.within_acceleration_m_s2, expected)
    assert np.allclose(excitation.incident_acceleration_m_s2, expected)
    assert np.allclose(
        excitation.applied_acceleration(BoundaryCondition.RIGID),
        expected,
    )
    assert np.allclose(
        excitation.applied_acceleration(BoundaryCondition.ELASTIC_HALFSPACE),
        expected,
    )
