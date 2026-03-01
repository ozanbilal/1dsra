from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt


@dataclass(slots=True)
class Motion:
    dt: float
    acc: npt.NDArray[np.float64]
    unit: str = "m/s2"
    source: Path | None = None


@dataclass(slots=True)
class RunResult:
    run_id: str
    output_dir: Path
    hdf5_path: Path
    sqlite_path: Path
    status: str
    message: str


@dataclass(slots=True)
class BatchResult:
    output_dir: Path
    results: list[RunResult]
