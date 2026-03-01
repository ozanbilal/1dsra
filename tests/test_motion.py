from pathlib import Path

import numpy as np
from dsra1d.config.models import MotionConfig, ScaleMode
from dsra1d.motion import load_motion
from dsra1d.motion.processing import preprocess_motion
from dsra1d.types import Motion
from dsra1d.units import STD_GRAVITY_M_S2


def test_preprocess_scale_by() -> None:
    mot = Motion(dt=0.01, acc=np.array([1.0, -1.0, 0.0], dtype=np.float64))
    cfg = MotionConfig(scale_mode=ScaleMode.SCALE_BY, scale_factor=2.0)
    out = preprocess_motion(mot, cfg)
    assert np.max(np.abs(out.acc)) == 2.0


def test_preprocess_scale_to_pga() -> None:
    mot = Motion(dt=0.01, acc=np.array([0.5, -0.5, 0.0], dtype=np.float64))
    cfg = MotionConfig(scale_mode=ScaleMode.SCALE_TO_PGA, target_pga=1.0)
    out = preprocess_motion(mot, cfg)
    assert np.isclose(np.max(np.abs(out.acc)), 1.0)


def test_load_motion_unit_conversion_from_g(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_g.csv"
    motion_file.write_text("0.1\n-0.2\n0.0\n", encoding="utf-8")
    mot = load_motion(motion_file, dt=0.01, unit="g")
    assert mot.unit == "m/s2"
    assert np.isclose(mot.acc[0], 0.1 * STD_GRAVITY_M_S2)
    assert np.isclose(mot.acc[1], -0.2 * STD_GRAVITY_M_S2)


def test_scale_to_pga_respects_config_units(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_g.csv"
    motion_file.write_text("0.2\n-0.2\n0.0\n", encoding="utf-8")
    mot = load_motion(motion_file, dt=0.01, unit="g")
    cfg = MotionConfig(
        units="g",
        scale_mode=ScaleMode.SCALE_TO_PGA,
        target_pga=0.5,
    )
    out = preprocess_motion(mot, cfg)
    assert np.isclose(np.max(np.abs(out.acc)), 0.5 * STD_GRAVITY_M_S2)
