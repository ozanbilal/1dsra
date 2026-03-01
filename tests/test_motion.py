import numpy as np
from dsra1d.config.models import MotionConfig, ScaleMode
from dsra1d.motion.processing import preprocess_motion
from dsra1d.types import Motion


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
