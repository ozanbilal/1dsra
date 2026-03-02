from __future__ import annotations

import numpy as np
from scipy import signal

from dsra1d.config.models import BaselineMode, MotionConfig, ScaleMode
from dsra1d.types import Motion
from dsra1d.units import accel_value_to_si


def _truncate_to_zero_crossings(acc: np.ndarray) -> np.ndarray:
    if acc.size < 3:
        return np.asarray(acc, dtype=np.float64)
    signs = np.signbit(acc)
    crossings = np.where(np.diff(signs))[0]
    if crossings.size < 2:
        return np.asarray(acc, dtype=np.float64)
    start = int(crossings[0] + 1)
    end = int(crossings[-1] + 1)
    if end <= start + 1:
        return np.asarray(acc, dtype=np.float64)
    return np.asarray(acc[start:end], dtype=np.float64)


def _deepsoil_bap_like(acc: np.ndarray, dt: float, cutoff_hz: float = 0.1) -> np.ndarray:
    series = _truncate_to_zero_crossings(np.asarray(acc, dtype=np.float64))
    if series.size < 8 or dt <= 0.0:
        return np.asarray(series, dtype=np.float64)

    # DEEPSOIL manual-inspired sequence: zero-padding + 2nd-order Butterworth high-pass + trim.
    pad_n = max(8, int(0.1 * series.size))
    padded = np.pad(series, (pad_n, pad_n), mode="constant", constant_values=0.0)

    nyquist = 0.5 / dt
    if not np.isfinite(nyquist) or nyquist <= 0.0:
        return np.asarray(series, dtype=np.float64)
    wn = cutoff_hz / nyquist
    if wn <= 0.0 or wn >= 1.0:
        return np.asarray(series, dtype=np.float64)
    b, a = signal.butter(2, wn, btype="highpass")
    filtered = signal.filtfilt(b, a, padded, method="pad")
    trimmed = filtered[pad_n:-pad_n] if filtered.size > 2 * pad_n else filtered
    return _truncate_to_zero_crossings(np.asarray(trimmed, dtype=np.float64))


def apply_baseline_correction(
    acc: np.ndarray,
    mode: BaselineMode,
    dt: float | None = None,
) -> np.ndarray:
    if mode == BaselineMode.NONE:
        return np.asarray(acc.copy(), dtype=np.float64)
    if mode == BaselineMode.REMOVE_MEAN:
        return np.asarray(acc - np.mean(acc), dtype=np.float64)
    if mode == BaselineMode.DETREND_LINEAR:
        return np.asarray(signal.detrend(acc, type="linear"), dtype=np.float64)
    if mode == BaselineMode.DEEPSOIL_BAP_LIKE:
        # Fallback dt proxy for standalone preprocessing when dt is not supplied by caller.
        return _deepsoil_bap_like(acc, dt=float(dt) if dt is not None else 0.005)
    raise ValueError(f"Unknown baseline mode: {mode}")


def apply_scaling(acc: np.ndarray, cfg: MotionConfig) -> np.ndarray:
    if cfg.scale_mode == ScaleMode.NONE:
        return acc
    if cfg.scale_mode == ScaleMode.SCALE_BY:
        assert cfg.scale_factor is not None
        return acc * cfg.scale_factor
    if cfg.scale_mode == ScaleMode.SCALE_TO_PGA:
        assert cfg.target_pga is not None
        target_pga_si = accel_value_to_si(cfg.target_pga, cfg.units)
        current = float(np.max(np.abs(acc)))
        if current == 0:
            raise ValueError("Cannot scale to target PGA with zero input motion")
        return acc * (target_pga_si / current)
    raise ValueError(f"Unknown scale mode: {cfg.scale_mode}")


def preprocess_motion(motion: Motion, cfg: MotionConfig) -> Motion:
    corrected = apply_baseline_correction(motion.acc, cfg.baseline, dt=float(motion.dt))
    scaled = apply_scaling(corrected, cfg)
    return Motion(
        dt=motion.dt,
        acc=scaled.astype(np.float64),
        unit=motion.unit,
        source=motion.source,
    )


def pga(acc: np.ndarray) -> float:
    return float(np.max(np.abs(acc)))
