from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np


@dataclass(slots=True)
class ResultStore:
    run_id: str
    hdf5_path: Path
    sqlite_path: Path
    acc_surface: np.ndarray
    spectra_periods: np.ndarray
    spectra_psa: np.ndarray


def load_result(output_dir: str | Path) -> ResultStore:
    root = Path(output_dir)
    hdf5_path = root / "results.h5"
    sqlite_path = root / "results.sqlite"

    with h5py.File(hdf5_path, "r") as h5:
        acc = np.array(h5["/signals/surface_acc"], dtype=np.float64)
        periods = np.array(h5["/spectra/periods"], dtype=np.float64)
        psa = np.array(h5["/spectra/psa"], dtype=np.float64)

    return ResultStore(
        run_id=root.name,
        hdf5_path=hdf5_path,
        sqlite_path=sqlite_path,
        acc_surface=acc,
        spectra_periods=periods,
        spectra_psa=psa,
    )
