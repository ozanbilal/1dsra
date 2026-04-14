from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import signal

from dsra1d.config.models import BaselineMode, MotionConfig, MotionProcessingConfig, ScaleMode
from dsra1d.types import Motion
from dsra1d.units import accel_value_to_si


def _cumtrapz_np(values: np.ndarray, dt: float) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return np.asarray([], dtype=np.float64)
    out = np.zeros(arr.size, dtype=np.float64)
    if arr.size > 1:
        increments = 0.5 * (arr[1:] + arr[:-1]) * float(dt)
        out[1:] = np.cumsum(increments, dtype=np.float64)
    return out


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


def _tukey_window(length: int, alpha: float) -> np.ndarray:
    if length <= 0:
        return np.asarray([], dtype=np.float64)
    if alpha <= 0.0:
        return np.ones(length, dtype=np.float64)
    if alpha >= 1.0:
        return np.hanning(length)
    n = np.arange(length, dtype=np.float64)
    width = alpha * (length - 1) / 2.0
    window = np.ones(length, dtype=np.float64)
    left = n < width
    right = n > (length - 1 - width)
    window[left] = 0.5 * (
        1.0 + np.cos(np.pi * ((2.0 * n[left] / (alpha * (length - 1))) - 1.0))
    )
    window[right] = 0.5 * (
        1.0
        + np.cos(
            np.pi
            * ((2.0 * n[right] / (alpha * (length - 1))) - (2.0 / alpha) + 1.0)
        )
    )
    return window


def _detrend_poly(data: np.ndarray, degree: int = 4) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float64)
    if arr.size == 0:
        return arr
    if arr.size <= max(1, degree):
        return arr - np.mean(arr)
    x = np.arange(1, arr.size + 1, dtype=np.float64)
    x_mean = np.mean(x)
    x_std = np.std(x)
    if x_std == 0.0:
        return arr - np.mean(arr)
    x_norm = (x - x_mean) / x_std
    try:
        coeffs = np.polyfit(x_norm, arr, int(degree))
    except Exception:
        return arr - np.mean(arr)
    return arr - np.polyval(coeffs, x_norm)


def _apply_trim(
    data: np.ndarray,
    dt: float,
    start_s: float = 0.0,
    end_s: float = 0.0,
    taper: bool = False,
) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float64)
    if arr.size <= 1:
        return arr
    total_t = (arr.size - 1) * float(dt)
    t_start = max(0.0, float(start_s or 0.0))
    t_end = float(end_s or 0.0)
    if t_end <= 0.0 or t_end > total_t:
        t_end = total_t
    if t_end <= t_start:
        return arr
    time = np.arange(arr.size, dtype=np.float64) * float(dt)
    idx_start = int(np.searchsorted(time, t_start, side="left"))
    idx_end = int(np.searchsorted(time, t_end, side="left"))
    idx_start = max(0, min(idx_start, arr.size - 1))
    idx_end = max(idx_start, min(idx_end, arr.size - 1))
    out = np.asarray(arr[idx_start : idx_end + 1], dtype=np.float64)
    if not taper or out.size <= 4:
        return out
    taper_len = min(int(out.size * 0.05), int(0.5 / dt))
    if taper_len > 0 and out.size >= 2 * taper_len:
        win = np.hanning(2 * taper_len)
        out[:taper_len] = out[:taper_len] * win[:taper_len]
        out[-taper_len:] = out[-taper_len:] * win[taper_len:]
    return out


def _apply_window(
    data: np.ndarray,
    window_type: str,
    param: float,
    dt: float,
    duration: float | None,
    apply_to: str,
) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float64)
    if arr.size == 0 or duration is None or duration <= 0.0:
        return arr
    n_window = int(float(duration) / float(dt))
    if n_window <= 0:
        return arr
    n_window = min(n_window, max(1, arr.size // 2))
    total = 2 * n_window
    window_name = str(window_type or "hanning").strip().lower()
    if window_name == "hamming":
        window = np.hamming(total)
    elif window_name in {"hann", "hanning"}:
        window = np.hanning(total)
    elif window_name == "cosine":
        window = np.sin(np.linspace(0.0, np.pi, total))
    else:
        window = _tukey_window(total, max(0.0, min(float(param), 1.0)))

    out = arr.copy()
    apply_to = str(apply_to or "both").strip().lower()
    if apply_to in {"start", "both"}:
        out[:n_window] = out[:n_window] * window[:n_window]
    if apply_to in {"end", "both"}:
        out[-n_window:] = out[-n_window:] * window[n_window:]
    return out


def _apply_padding(
    data: np.ndarray,
    dt: float,
    front_s: float = 0.0,
    end_s: float = 0.0,
    method: str = "zeros",
    method_front: str | None = None,
    method_end: str | None = None,
    smooth: bool = False,
) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float64)
    if arr.size == 0:
        return arr
    pad_front = max(0.0, float(front_s or 0.0))
    pad_end = max(0.0, float(end_s or 0.0))
    n_front = int(pad_front / float(dt)) if pad_front > 0.0 else 0
    n_end = int(pad_end / float(dt)) if pad_end > 0.0 else 0
    if n_front == 0 and n_end == 0:
        return arr

    out = arr.copy()
    shared_method = str(method or "zeros").strip().lower()
    front_method = str(method_front or shared_method).strip().lower()
    end_method = str(method_end or shared_method).strip().lower()

    if smooth and out.size > 1:
        taper_len = min(int(out.size * 0.05), int(0.5 / dt))
        if taper_len > 0 and out.size >= 2 * taper_len:
            win = np.hanning(2 * taper_len)
            if n_front > 0:
                out[:taper_len] *= win[:taper_len]
            if n_end > 0:
                out[-taper_len:] *= win[taper_len:]

    def decay_pad(val: float, count: int, duration: float, method_name: str) -> np.ndarray:
        if count <= 0:
            return np.asarray([], dtype=np.float64)
        if method_name in {"linear", "linear_decay", "linear-decay"}:
            return np.linspace(val, 0.0, count)
        if method_name in {"exponential", "exp", "exponential_decay", "exponential-decay"}:
            duration_safe = max(duration, float(dt))
            k = -np.log(0.01) / duration_safe
            t_pad = np.linspace(0.0, duration_safe, count)
            return val * np.exp(-k * t_pad)
        return np.zeros(count, dtype=np.float64)

    if n_front > 0:
        front_val = float(out[0]) if front_method not in {"zeros", "zero"} else 0.0
        front_pad = decay_pad(front_val, n_front, pad_front, front_method)
        if front_method not in {"zeros", "zero"}:
            front_pad = front_pad[::-1]
        out = np.concatenate([front_pad, out])

    if n_end > 0:
        end_val = float(out[-1]) if end_method not in {"zeros", "zero"} else 0.0
        end_pad = decay_pad(end_val, n_end, pad_end, end_method)
        out = np.concatenate([out, end_pad])

    return out


def _apply_baseline_method(data: np.ndarray, method: str, degree: int = 4) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float64)
    if arr.size == 0:
        return arr
    mode = str(method or "none").strip().lower()
    if mode in {"none", "", "raw"}:
        return arr
    if mode in {"mean", "dc", "constant", "const", "remove_mean"}:
        return arr - np.mean(arr)
    if mode in {"linear", "lin", "detrend_linear"}:
        return _detrend_poly(arr, 1)
    if mode in {"quadratic", "quad"}:
        return _detrend_poly(arr, 2)
    if mode in {"cubic"}:
        return _detrend_poly(arr, 3)
    if mode == "deepsoil_bap_like":
        return _deepsoil_bap_like(arr, dt=0.005)
    if mode.startswith("poly"):
        digits = "".join(ch for ch in mode if ch.isdigit())
        deg = int(digits) if digits else int(degree)
        return _detrend_poly(arr, deg)
    return _detrend_poly(arr, int(degree))


def apply_baseline_correction(acc: np.ndarray, mode: BaselineMode, dt: float | None = None) -> np.ndarray:
    arr = np.asarray(acc, dtype=np.float64)
    if mode == BaselineMode.NONE:
        return np.asarray(arr.copy(), dtype=np.float64)
    if mode == BaselineMode.REMOVE_MEAN:
        return np.asarray(arr - np.mean(arr), dtype=np.float64)
    if mode == BaselineMode.DETREND_LINEAR:
        return np.asarray(signal.detrend(arr, type="linear"), dtype=np.float64)
    if mode == BaselineMode.DEEPSOIL_BAP_LIKE:
        return _deepsoil_bap_like(arr, dt=float(dt) if dt is not None else 0.005)
    raise ValueError(f"Unknown baseline mode: {mode}")


def _resolve_scale_multiplier(acc: np.ndarray, cfg: MotionConfig) -> float:
    if cfg.scale_mode == ScaleMode.NONE:
        return 1.0
    if cfg.scale_mode == ScaleMode.SCALE_BY:
        assert cfg.scale_factor is not None
        return float(cfg.scale_factor)
    if cfg.scale_mode == ScaleMode.SCALE_TO_PGA:
        assert cfg.target_pga is not None
        current = float(np.max(np.abs(acc))) if acc.size else 0.0
        if current == 0.0:
            raise ValueError("Cannot scale to target PGA with zero input motion")
        target_pga_si = accel_value_to_si(cfg.target_pga, cfg.units)
        return float(target_pga_si / current)
    raise ValueError(f"Unknown scale mode: {cfg.scale_mode}")


def apply_scaling(acc: np.ndarray, cfg: MotionConfig) -> np.ndarray:
    arr = np.asarray(acc, dtype=np.float64)
    return arr * _resolve_scale_multiplier(arr, cfg)


def _filter_cutoffs(proc: MotionProcessingConfig) -> tuple[float | None, float | None]:
    config = str(proc.filter_config or "bandpass").strip().lower()
    low = float(proc.f_low)
    high = float(proc.f_high)
    if config in {"lowpass", "low"}:
        return None, max(high if high > 0.0 else low, 0.0)
    if config in {"highpass", "high"}:
        return max(low if low > 0.0 else high, 0.0), None
    return max(low, 0.0), max(high, 0.0)


def _apply_filter(data: np.ndarray, dt: float, proc: MotionProcessingConfig) -> np.ndarray:
    arr = np.asarray(data, dtype=np.float64)
    if not proc.filter_on or arr.size <= 1:
        return arr
    filter_config = str(proc.filter_config or "bandpass").strip().lower()
    filter_domain = str(proc.filter_domain or "time").strip().lower()
    low_hz, high_hz = _filter_cutoffs(proc)

    if filter_domain in {"frequency", "freq", "fft"}:
        freq = np.fft.rfftfreq(arr.size, d=float(dt))
        spectrum = np.fft.rfft(arr)
        transfer = np.ones_like(freq, dtype=np.float64)
        if filter_config in {"lowpass", "low"} and high_hz is not None:
            transfer[freq > high_hz] = 0.0
        elif filter_config in {"highpass", "high"} and low_hz is not None:
            transfer[freq < low_hz] = 0.0
        elif filter_config in {"bandstop", "stop"} and low_hz is not None and high_hz is not None and high_hz > low_hz:
            transfer[(freq >= low_hz) & (freq <= high_hz)] = 0.0
        elif low_hz is not None and high_hz is not None and high_hz > low_hz:
            transfer[(freq < low_hz) | (freq > high_hz)] = 0.0
        return np.fft.irfft(spectrum * transfer, n=arr.size)

    nyquist = 1.0 / (2.0 * float(dt))
    if not np.isfinite(nyquist) or nyquist <= 0.0:
        return arr
    filter_type = str(proc.filter_type or "butter").strip().lower()

    def design_lowpass(cutoff: float) -> tuple[np.ndarray, np.ndarray]:
        wn = min(float(cutoff) / nyquist, 0.999)
        if filter_type == "cheby":
            return signal.cheby1(proc.filter_order, 0.5, wn, btype="low")
        if filter_type == "bessel":
            return signal.bessel(proc.filter_order, wn, btype="low", norm="phase")
        return signal.butter(proc.filter_order, wn, btype="low")

    def design_highpass(cutoff: float) -> tuple[np.ndarray, np.ndarray]:
        wn = min(max(float(cutoff) / nyquist, 1.0e-6), 0.999)
        if filter_type == "cheby":
            return signal.cheby1(proc.filter_order, 0.5, wn, btype="high")
        if filter_type == "bessel":
            return signal.bessel(proc.filter_order, wn, btype="high", norm="phase")
        return signal.butter(proc.filter_order, wn, btype="high")

    def design_band(low_cut: float, high_cut: float, *, stop: bool = False) -> tuple[np.ndarray, np.ndarray]:
        low = min(max(float(low_cut) / nyquist, 1.0e-6), 0.999)
        high = min(max(float(high_cut) / nyquist, low + 1.0e-6), 0.999)
        band_type = "bandstop" if stop else "bandpass"
        if filter_type == "cheby":
            return signal.cheby1(proc.filter_order, 0.5, [low, high], btype=band_type)
        if filter_type == "bessel":
            return signal.bessel(proc.filter_order, [low, high], btype=band_type, norm="phase")
        return signal.butter(proc.filter_order, [low, high], btype="bandstop" if stop else "band")

    b: np.ndarray | None = None
    a: np.ndarray | None = None
    try:
        if filter_config in {"lowpass", "low"} and high_hz:
            b, a = design_lowpass(high_hz)
        elif filter_config in {"highpass", "high"} and low_hz:
            b, a = design_highpass(low_hz)
        elif filter_config in {"bandstop", "stop"} and low_hz and high_hz and high_hz > low_hz:
            b, a = design_band(low_hz, high_hz, stop=True)
        elif low_hz and high_hz and high_hz > low_hz:
            b, a = design_band(low_hz, high_hz, stop=False)
    except ValueError:
        return arr

    if b is None or a is None:
        return arr
    if proc.acausal:
        padlen = 3 * (max(len(a), len(b)) - 1)
        if arr.size <= padlen:
            return signal.lfilter(b, a, arr)
        try:
            return signal.filtfilt(b, a, arr)
        except ValueError:
            return signal.lfilter(b, a, arr)
    return signal.lfilter(b, a, arr)


def _legacy_components(acc: np.ndarray, dt: float, cfg: MotionConfig) -> dict[str, np.ndarray]:
    corrected = apply_baseline_correction(acc, cfg.baseline, dt=float(dt))
    multiplier = _resolve_scale_multiplier(corrected, cfg)
    processed = corrected * multiplier
    vel = _cumtrapz_np(processed, float(dt))
    disp = _cumtrapz_np(vel, float(dt))
    return {
        "acc_raw": np.asarray(acc, dtype=np.float64),
        "acc_processed": np.asarray(processed, dtype=np.float64),
        "vel_processed": np.asarray(vel, dtype=np.float64),
        "disp_processed": np.asarray(disp, dtype=np.float64),
    }


def process_motion_components(motion: Motion, cfg: MotionConfig) -> dict[str, np.ndarray]:
    acc_raw = np.asarray(motion.acc, dtype=np.float64)
    dt = float(motion.dt)
    if cfg.processing is None:
        return _legacy_components(acc_raw, dt, cfg)

    proc = cfg.processing
    acc = _apply_trim(
        acc_raw,
        dt,
        start_s=float(proc.trim_start or 0.0),
        end_s=float(proc.trim_end or 0.0),
        taper=bool(proc.trim_taper),
    )
    if proc.window_on:
        acc = _apply_window(
            acc,
            proc.window_type,
            float(proc.window_param),
            dt,
            proc.window_duration,
            proc.window_apply_to,
        )

    def do_filter(signal_in: np.ndarray) -> np.ndarray:
        return _apply_filter(signal_in, dt, proc)

    def do_baseline(signal_in: np.ndarray) -> np.ndarray:
        if not proc.baseline_on or signal_in.size <= 1:
            return signal_in
        return _apply_baseline_method(
            signal_in,
            proc.baseline_method,
            degree=int(proc.baseline_degree),
        )

    if str(proc.processing_order or "filter_first").strip().lower() == "baseline_first":
        acc = do_baseline(acc)
        acc = do_filter(acc)
    else:
        acc = do_filter(acc)
        acc = do_baseline(acc)

    acc = _apply_padding(
        acc,
        dt,
        front_s=float(proc.pad_front or 0.0),
        end_s=float(proc.pad_end or 0.0),
        method=proc.pad_method,
        method_front=proc.pad_method_front,
        method_end=proc.pad_method_end,
        smooth=bool(proc.pad_smooth),
    )

    if proc.residual_fix:
        vel0 = _cumtrapz_np(acc, dt)
        disp0 = _cumtrapz_np(vel0, dt)
        if disp0.size >= 2:
            duration = float((disp0.size - 1) * dt)
            disp_final = float(disp0[-1])
            if duration > 0.0 and np.isfinite(disp_final) and abs(disp_final) > 0.0:
                acc = acc + (-2.0 * disp_final / (duration * duration))

    vel = _cumtrapz_np(acc, dt)
    disp = _cumtrapz_np(vel, dt)

    if proc.baseline_on and not proc.residual_fix:
        vel = vel - np.mean(vel)
        disp = _detrend_poly(disp, degree=1)

    multiplier = _resolve_scale_multiplier(acc, cfg)
    acc_scaled = acc * multiplier
    vel_scaled = vel * multiplier
    disp_scaled = disp * multiplier
    return {
        "acc_raw": np.asarray(acc_raw, dtype=np.float64),
        "acc_processed": np.asarray(acc_scaled, dtype=np.float64),
        "vel_processed": np.asarray(vel_scaled, dtype=np.float64),
        "disp_processed": np.asarray(disp_scaled, dtype=np.float64),
    }


def preprocess_motion(motion: Motion, cfg: MotionConfig) -> Motion:
    components = process_motion_components(motion, cfg)
    return Motion(
        dt=motion.dt,
        acc=np.asarray(components["acc_processed"], dtype=np.float64),
        unit=motion.unit,
        source=motion.source,
    )


def pga(acc: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(acc, dtype=np.float64))))
