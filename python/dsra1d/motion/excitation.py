from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from dsra1d.config import BoundaryCondition, ProjectConfig

FloatArray = npt.NDArray[np.float64]


@dataclass(slots=True, frozen=True)
class BoundaryExcitation:
    raw_acceleration_m_s2: FloatArray
    within_acceleration_m_s2: FloatArray
    incident_acceleration_m_s2: FloatArray
    input_type: str

    def applied_acceleration(
        self,
        boundary_condition: BoundaryCondition,
    ) -> FloatArray:
        if boundary_condition == BoundaryCondition.ELASTIC_HALFSPACE:
            return np.asarray(self.incident_acceleration_m_s2, dtype=np.float64)
        return np.asarray(self.within_acceleration_m_s2, dtype=np.float64)


def build_boundary_excitation(
    config: ProjectConfig,
    acc_m_s2: npt.ArrayLike,
) -> BoundaryExcitation:
    """Build a boundary-input semantic view of a raw acceleration history.

    The raw motion can be declared either as:

    - ``within``: directly compatible with rigid-base prescription and with the
      upward-incident wave used by an elastic halfspace boundary.
    - ``outcrop``: free-surface motion that must be converted to an incident/
      within-compatible motion before boundary loading.
    """
    raw = np.asarray(acc_m_s2, dtype=np.float64)
    input_type = str(getattr(config.motion, "input_type", "within")).strip().lower()
    if input_type == "outcrop":
        converted = 0.5 * raw
    else:
        converted = raw.copy()
    return BoundaryExcitation(
        raw_acceleration_m_s2=raw.copy(),
        within_acceleration_m_s2=np.asarray(converted, dtype=np.float64),
        incident_acceleration_m_s2=np.asarray(converted, dtype=np.float64),
        input_type=input_type,
    )


def effective_input_acceleration(
    config: ProjectConfig,
    acc_m_s2: npt.ArrayLike,
) -> FloatArray:
    """Return the acceleration actually consumed by the current boundary path."""
    excitation = build_boundary_excitation(config, acc_m_s2)
    return excitation.applied_acceleration(config.boundary_condition)
