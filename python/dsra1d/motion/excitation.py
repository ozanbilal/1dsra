from __future__ import annotations

import numpy as np
import numpy.typing as npt

from dsra1d.config import BoundaryCondition, ProjectConfig

FloatArray = npt.NDArray[np.float64]


def effective_input_acceleration(
    config: ProjectConfig,
    acc_m_s2: npt.ArrayLike,
) -> FloatArray:
    """Return the excitation acceleration actually applied to the solver.

    Rigid-base analyses expect a within/base motion.  Real records are often
    specified as outcrop motions, which must be halved before being imposed at
    a rigid base.  Elastic half-space handling remains unchanged.
    """
    acc = np.asarray(acc_m_s2, dtype=np.float64)
    input_type = str(getattr(config.motion, "input_type", "within")).strip().lower()
    if (
        config.boundary_condition == BoundaryCondition.RIGID
        and input_type == "outcrop"
    ):
        return 0.5 * acc
    return acc.copy()
