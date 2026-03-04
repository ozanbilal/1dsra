from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dsra1d.types import Motion
from dsra1d.units import SI_ACCEL_UNIT, accel_factor_to_si


def _load_numeric_series(path_obj: Path) -> np.ndarray:
    try:
        raw = np.loadtxt(path_obj, delimiter=",", ndmin=1)
    except ValueError:
        try:
            raw = np.loadtxt(path_obj, delimiter=None, ndmin=1)
        except ValueError:
            raw = _load_numeric_series_with_headers(path_obj)
    return np.asarray(raw, dtype=np.float64)


def _load_numeric_series_with_headers(path_obj: Path) -> np.ndarray:
    rows: list[list[float]] = []
    for line in path_obj.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        normalized = text.replace(";", ",")
        tokens = (
            [tok.strip() for tok in normalized.split(",")]
            if "," in normalized
            else text.split()
        )
        if not tokens:
            continue
        values: list[float] = []
        failed = False
        for token in tokens:
            if not token:
                continue
            try:
                values.append(float(token))
            except ValueError:
                failed = True
                break
        if failed or not values:
            continue
        rows.append(values)

    if not rows:
        raise ValueError(f"No numeric rows found in motion file: {path_obj}")

    widths = Counter(len(row) for row in rows)
    target_width = widths.most_common(1)[0][0]
    filtered = [row for row in rows if len(row) == target_width]
    if not filtered:
        raise ValueError(f"No consistent numeric rows found in motion file: {path_obj}")

    if target_width == 1:
        return np.asarray([row[0] for row in filtered], dtype=np.float64)
    return np.asarray(filtered, dtype=np.float64)


def _try_infer_dt_from_time(time_axis: np.ndarray) -> float | None:
    if time_axis.size < 2:
        return None
    diffs = np.diff(time_axis)
    diffs = diffs[np.isfinite(diffs)]
    if diffs.size == 0:
        return None
    dt = float(np.median(diffs))
    if not np.isfinite(dt) or dt <= 0.0:
        return None
    return dt


def load_motion_series(
    path: str | Path,
    *,
    dt_override: float | None = None,
    fallback_dt: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    path_obj = Path(path)
    raw = _load_numeric_series(path_obj)
    dt_fallback = float(fallback_dt)
    if not np.isfinite(dt_fallback) or dt_fallback <= 0.0:
        dt_fallback = 1.0
    if raw.ndim == 1:
        acc = np.asarray(raw, dtype=np.float64)
        dt = float(dt_override) if dt_override is not None else dt_fallback
        time = np.arange(acc.size, dtype=np.float64) * dt
        return time, acc

    arr = np.asarray(raw, dtype=np.float64)
    first_col = arr[:, 0]
    inferred = _try_infer_dt_from_time(first_col)
    if inferred is not None:
        time = first_col.astype(np.float64)
        acc = arr[:, -1].astype(np.float64)
        return time, acc

    acc = arr[:, -1].astype(np.float64)
    dt = float(dt_override) if dt_override is not None else dt_fallback
    time = np.arange(acc.size, dtype=np.float64) * dt
    return time, acc


@dataclass(slots=True)
class PeerAT2ImportResult:
    csv_path: Path
    npts: int
    dt_s: float
    pga_si: float


_NPTS_RE = re.compile(r"NPTS\s*=\s*(\d+)", re.IGNORECASE)
_DT_RE = re.compile(r"DT\s*=\s*([+\-]?\d*\.?\d+(?:[Ee][+\-]?\d+)?)", re.IGNORECASE)
_FLOAT_TOKEN_RE = re.compile(r"[+\-]?\d*\.?\d+(?:[Ee][+\-]?\d+)?")


def _read_peer_at2(path_obj: Path) -> tuple[np.ndarray, float | None]:
    text = path_obj.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    npts: int | None = None
    dt_s: float | None = None
    start_idx = 0
    for i, line in enumerate(lines):
        m_npts = _NPTS_RE.search(line)
        m_dt = _DT_RE.search(line)
        if m_npts is not None:
            npts = int(m_npts.group(1))
        if m_dt is not None:
            try:
                dt_s = float(m_dt.group(1))
            except ValueError:
                dt_s = None
        if m_npts is not None or m_dt is not None:
            start_idx = i + 1

    data_text = "\n".join(lines[start_idx:])
    tokens = _FLOAT_TOKEN_RE.findall(data_text)
    if not tokens:
        raise ValueError(f"No numeric acceleration samples found in AT2 file: {path_obj}")
    acc = np.asarray([float(tok) for tok in tokens], dtype=np.float64)
    if npts is not None and npts > 0 and acc.size >= npts:
        acc = acc[:npts]
    return acc, dt_s


def import_peer_at2_to_csv(
    source_path: str | Path,
    *,
    output_dir: str | Path,
    units_hint: str = "g",
    dt_override: float | None = None,
    output_name: str | None = None,
) -> PeerAT2ImportResult:
    src = Path(source_path)
    acc_raw, dt_hdr = _read_peer_at2(src)
    dt_s = float(dt_override) if dt_override is not None else (float(dt_hdr) if dt_hdr else 1.0)
    factor = accel_factor_to_si(units_hint)
    acc_si = np.asarray(acc_raw * factor, dtype=np.float64)
    time = np.arange(acc_si.size, dtype=np.float64) * dt_s

    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    file_name = output_name or f"{src.stem}_imported.csv"
    out_path = out_root / file_name
    np.savetxt(
        out_path,
        np.column_stack([time, acc_si]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )
    pga_si = float(np.max(np.abs(acc_si))) if acc_si.size > 0 else 0.0
    return PeerAT2ImportResult(
        csv_path=out_path,
        npts=int(acc_si.size),
        dt_s=float(dt_s),
        pga_si=pga_si,
    )


def load_motion(path: str | Path, dt: float, unit: str = "m/s2") -> Motion:
    path_obj = Path(path)
    raw = _load_numeric_series(path_obj)
    if raw.ndim > 1:
        acc = raw[:, -1]
    else:
        acc = raw
    acc_si = acc * accel_factor_to_si(unit)
    return Motion(dt=dt, acc=acc_si.astype(np.float64), unit=SI_ACCEL_UNIT, source=path_obj)
