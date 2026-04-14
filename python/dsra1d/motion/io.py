from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dsra1d.types import Motion
from dsra1d.units import SI_ACCEL_UNIT, accel_factor_to_si


_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?")
_NUMERIC_ONLY_RE = re.compile(r"^[\s+\-0-9EeDd.,;]+$")
_DT_TEXT_RE = re.compile(r"\bDT\b\s*[:=]\s*([-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?)", re.IGNORECASE)
_NPTS_TEXT_RE = re.compile(r"\bNPTS\b\s*[:=]\s*(\d+)", re.IGNORECASE)
_COMPACT_NPTS_MIN = 16
_COMPACT_DT_MIN = 1e-6
_COMPACT_DT_MAX = 1.0


def _normalize_decimal_commas(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", ".", text)


def _iter_numbers(text: str):
    if not text:
        return
    normalized = _normalize_decimal_commas(text)
    for match in _NUM_RE.finditer(normalized):
        token = match.group(0).replace("D", "E").replace("d", "e")
        try:
            yield float(token)
        except ValueError:
            continue


def _as_int_like(value) -> int | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric):
        return None
    rounded = round(numeric)
    if abs(numeric - rounded) > 1.0e-9:
        return None
    return int(rounded)


def _is_valid_compact_dt(value) -> bool:
    try:
        dt = float(value)
    except (TypeError, ValueError):
        return False
    return np.isfinite(dt) and _COMPACT_DT_MIN < dt <= _COMPACT_DT_MAX


def _normalize_delimiter(delimiter: str | None) -> str | None:
    if delimiter is None:
        return None
    raw = str(delimiter).strip()
    if not raw or raw.lower() == "auto":
        return None
    lowered = raw.lower()
    if lowered in {"comma", ","}:
        return ","
    if lowered in {"semicolon", ";"}:
        return ";"
    if lowered in {"tab", "\\t"}:
        return "\t"
    if lowered in {"space", "whitespace"}:
        return None
    return raw


def detect_compact_header(
    lines: list[str],
    *,
    max_meaningful: int = 3,
    max_scan_lines: int = 16,
) -> dict[str, object]:
    result: dict[str, object] = {"dt": None, "npts": None, "data_start": 0, "mode": None}
    if not lines:
        return result

    meaningful: list[tuple[int, str]] = []
    scan_limit = min(len(lines), max_scan_lines)
    for idx in range(scan_limit):
        stripped = str(lines[idx] or "").strip()
        if not stripped or stripped.startswith("#"):
            continue
        meaningful.append((idx, stripped))
        if len(meaningful) >= max_meaningful:
            break

    if not meaningful:
        return result

    for idx, text in meaningful:
        dt_match = _DT_TEXT_RE.search(text)
        if not dt_match:
            continue
        token = dt_match.group(1).replace("D", "E").replace("d", "e")
        try:
            dt = float(token)
        except ValueError:
            continue
        if not _is_valid_compact_dt(dt):
            continue
        npts = None
        npts_match = _NPTS_TEXT_RE.search(text)
        if npts_match:
            npts = _as_int_like(npts_match.group(1))
        return {
            "dt": float(dt),
            "npts": npts if isinstance(npts, int) and npts >= _COMPACT_NPTS_MIN else None,
            "data_start": idx + 1,
            "mode": "dt_text",
        }

    for idx, text in meaningful:
        nums = list(_iter_numbers(text))
        if len(nums) != 2 or not _NUMERIC_ONLY_RE.match(text):
            continue
        npts = _as_int_like(nums[0])
        dt = nums[1]
        if isinstance(npts, int) and npts >= _COMPACT_NPTS_MIN and _is_valid_compact_dt(dt):
            return {
                "dt": float(dt),
                "npts": int(npts),
                "data_start": idx + 1,
                "mode": "compact_same_line",
            }

    if len(meaningful) >= 2:
        for i in range(len(meaningful) - 1):
            idx1, text1 = meaningful[i]
            idx2, text2 = meaningful[i + 1]
            nums1 = list(_iter_numbers(text1))
            nums2 = list(_iter_numbers(text2))
            if (
                len(nums1) == 1
                and len(nums2) == 1
                and _NUMERIC_ONLY_RE.match(text1)
                and _NUMERIC_ONLY_RE.match(text2)
            ):
                npts = _as_int_like(nums1[0])
                dt = nums2[0]
                if isinstance(npts, int) and npts >= _COMPACT_NPTS_MIN and _is_valid_compact_dt(dt):
                    return {
                        "dt": float(dt),
                        "npts": int(npts),
                        "data_start": idx2 + 1,
                        "mode": "compact_split_lines",
                    }

    return result


def _parse_numeric_stream_lines(
    lines: list[str],
    *,
    dt_override: float | None = None,
    fallback_dt: float = 1.0,
) -> tuple[np.ndarray, float]:
    header = detect_compact_header(lines)
    dt = float(header.get("dt")) if header.get("dt") is not None else float(fallback_dt)
    data_start = int(header.get("data_start") or 0)
    if dt_override is not None:
        dt = float(dt_override)

    values: list[float] = []
    for line in lines[data_start:]:
        for value in _iter_numbers(line):
            values.append(value)
    return np.asarray(values, dtype=np.float64), float(dt)


def _parse_single_value_per_line(
    lines: list[str],
    *,
    dt_override: float | None = None,
    fallback_dt: float = 1.0,
) -> tuple[np.ndarray, float]:
    header = detect_compact_header(lines)
    data_start = int(header.get("data_start") or 0)
    dt = float(header.get("dt")) if header.get("dt") is not None else float(fallback_dt)
    if dt_override is not None:
        dt = float(dt_override)

    values: list[float] = []
    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for value in _iter_numbers(stripped):
            values.append(value)
            break
    return np.asarray(values, dtype=np.float64), float(dt)


def _parse_generic_motion_columns(
    path_obj: Path,
    *,
    delimiter: str | None = None,
    skip_rows: int = 0,
    time_col: int = 0,
    acc_col: int = 1,
    has_time: bool = True,
    dt_override: float | None = None,
    fallback_dt: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    lines = path_obj.read_text(encoding="utf-8", errors="ignore").splitlines()
    try:
        skip_rows = int(float(skip_rows))
    except (TypeError, ValueError):
        skip_rows = 0
    skip_rows = max(skip_rows, 0)
    if skip_rows >= len(lines):
        skip_rows = 0
    lines = lines[skip_rows:]

    delimiter = _normalize_delimiter(delimiter)
    if delimiter is None:
        first_data = ""
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            first_data = stripped
            break
        if "," in first_data:
            delimiter = ","
        elif ";" in first_data:
            delimiter = ";"
        elif "\t" in first_data:
            delimiter = "\t"
        else:
            delimiter = None

    try:
        time_col = int(float(time_col))
    except (TypeError, ValueError):
        time_col = 0
    try:
        acc_col = int(float(acc_col))
    except (TypeError, ValueError):
        acc_col = 1
    time_col = max(time_col, 0)
    acc_col = max(acc_col, 0)

    time_vals: list[float] = []
    acc_vals: list[float] = []
    normalize_decimal = delimiter in {None, ";", "\t"}

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        normalized = _normalize_decimal_commas(stripped) if normalize_decimal else stripped
        parts = normalized.split(delimiter) if delimiter else normalized.split()
        try:
            if has_time and len(parts) > max(time_col, acc_col):
                time_vals.append(float(parts[time_col]))
                acc_vals.append(float(parts[acc_col]))
            elif not has_time and len(parts) > acc_col:
                acc_vals.append(float(parts[acc_col]))
        except (ValueError, IndexError):
            continue

    if not acc_vals:
        raise ValueError(f"No numeric motion samples found in {path_obj.name}.")

    acc = np.asarray(acc_vals, dtype=np.float64)
    if has_time and len(time_vals) > 1:
        time = np.asarray(time_vals, dtype=np.float64)
        return time, acc

    dt = float(dt_override) if dt_override is not None else float(fallback_dt)
    return np.arange(acc.size, dtype=np.float64) * dt, acc


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
    format_hint: str = "auto",
    delimiter: str | None = None,
    skip_rows: int = 0,
    time_col: int = 0,
    acc_col: int = 1,
    has_time: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    path_obj = Path(path)
    format_key = str(format_hint or "auto").strip().lower()
    dt_fallback = float(fallback_dt)
    if not np.isfinite(dt_fallback) or dt_fallback <= 0.0:
        dt_fallback = 1.0

    has_custom_parse = (
        format_key != "auto"
        or _normalize_delimiter(delimiter) is not None
        or int(skip_rows or 0) != 0
        or int(time_col or 0) != 0
        or int(acc_col or 1) != 1
        or bool(has_time) is False
    )

    if format_key == "single":
        lines = path_obj.read_text(encoding="utf-8", errors="ignore").splitlines()
        acc, dt = _parse_single_value_per_line(
            lines,
            dt_override=dt_override,
            fallback_dt=dt_fallback,
        )
        return np.arange(acc.size, dtype=np.float64) * dt, acc

    if format_key == "numeric_stream":
        lines = path_obj.read_text(encoding="utf-8", errors="ignore").splitlines()
        acc, dt = _parse_numeric_stream_lines(
            lines,
            dt_override=dt_override,
            fallback_dt=dt_fallback,
        )
        return np.arange(acc.size, dtype=np.float64) * dt, acc

    if format_key in {"time_acc", "generic"} or has_custom_parse:
        try:
            return _parse_generic_motion_columns(
                path_obj,
                delimiter=delimiter,
                skip_rows=skip_rows,
                time_col=time_col,
                acc_col=acc_col,
                has_time=has_time,
                dt_override=dt_override,
                fallback_dt=dt_fallback,
            )
        except ValueError:
            if format_key in {"time_acc", "generic"}:
                raise

    raw = _load_numeric_series(path_obj)
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
    time, acc = load_motion_series(path_obj, fallback_dt=float(dt))
    dt_inferred = float(dt)
    if time.size > 1:
        dt_candidate = float(np.median(np.diff(np.asarray(time, dtype=np.float64))))
        if np.isfinite(dt_candidate) and dt_candidate > 0.0:
            dt_inferred = dt_candidate
    acc_si = acc * accel_factor_to_si(unit)
    return Motion(
        dt=dt_inferred,
        acc=acc_si.astype(np.float64),
        unit=SI_ACCEL_UNIT,
        source=path_obj,
    )
