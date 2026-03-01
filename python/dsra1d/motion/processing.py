from __future__ import annotations

import numpy as np
from scipy import signal

from dsra1d.config.models import BaselineMode, MotionConfig, ScaleMode
from dsra1d.types import Motion


def apply_baseline_correction(acc: np.ndarray, mode: BaselineMode) -> np.ndarray:
    if mode == BaselineMode.NONE:
        return np.asarray(acc.copy(), dtype=np.float64)
    if mode == BaselineMode.REMOVE_MEAN:
        return np.asarray(acc - np.mean(acc), dtype=np.float64)
    if mode == BaselineMode.DETREND_LINEAR:
        return np.asarray(signal.detrend(acc, type="linear"), dtype=np.float64)
    raise ValueError(f"Unknown baseline mode: {mode}")


def apply_scaling(acc: np.ndarray, cfg: MotionConfig) -> np.ndarray:
    if cfg.scale_mode == ScaleMode.NONE:
        return acc
    if cfg.scale_mode == ScaleMode.SCALE_BY:
        assert cfg.scale_factor is not None
        return acc * cfg.scale_factor
    if cfg.scale_mode == ScaleMode.SCALE_TO_PGA:
        assert cfg.target_pga is not None
        current = float(np.max(np.abs(acc)))
        if current == 0:
            raise ValueError("Cannot scale to target PGA with zero input motion")
        return acc * (cfg.target_pga / current)
    raise ValueError(f"Unknown scale mode: {cfg.scale_mode}")


def preprocess_motion(motion: Motion, cfg: MotionConfig) -> Motion:
    corrected = apply_baseline_correction(motion.acc, cfg.baseline)
    scaled = apply_scaling(corrected, cfg)
    return Motion(dt=motion.dt, acc=scaled.astype(np.float64), unit=cfg.units, source=motion.source)


def pga(acc: np.ndarray) -> float:
    return float(np.max(np.abs(acc)))
