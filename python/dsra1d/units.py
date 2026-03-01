from __future__ import annotations

from typing import Final

SI_ACCEL_UNIT: Final[str] = "m/s2"
STD_GRAVITY_M_S2: Final[float] = 9.80665

_UNIT_FACTORS_TO_SI: Final[dict[str, float]] = {
    "m/s2": 1.0,
    "m/s^2": 1.0,
    "mps2": 1.0,
    "g": STD_GRAVITY_M_S2,
    "gal": 0.01,
    "cm/s2": 0.01,
    "cm/s^2": 0.01,
}


def normalize_accel_unit(unit: str) -> str:
    key = unit.strip().lower().replace(" ", "")
    if key not in _UNIT_FACTORS_TO_SI:
        supported = sorted(_UNIT_FACTORS_TO_SI.keys())
        raise ValueError(f"Unsupported acceleration unit '{unit}'. Supported: {supported}")
    return key


def accel_factor_to_si(unit: str) -> float:
    key = normalize_accel_unit(unit)
    return _UNIT_FACTORS_TO_SI[key]


def accel_value_to_si(value: float, unit: str) -> float:
    return value * accel_factor_to_si(unit)
