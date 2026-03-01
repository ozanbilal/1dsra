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
    time: np.ndarray
    acc_surface: np.ndarray
    spectra_periods: np.ndarray
    spectra_psa: np.ndarray
    transfer_freq_hz: np.ndarray
    transfer_abs: np.ndarray
    ru_time: np.ndarray
    ru: np.ndarray
    delta_u: np.ndarray
    sigma_v_ref: float
    sigma_v_eff: np.ndarray


def load_result(output_dir: str | Path) -> ResultStore:
    root = Path(output_dir)
    hdf5_path = root / "results.h5"
    sqlite_path = root / "results.sqlite"

    with h5py.File(hdf5_path, "r") as h5:
        time = np.array(h5["/time"], dtype=np.float64) if "/time" in h5 else np.array([])
        acc = np.array(h5["/signals/surface_acc"], dtype=np.float64)
        periods = np.array(h5["/spectra/periods"], dtype=np.float64)
        psa = np.array(h5["/spectra/psa"], dtype=np.float64)
        transfer_freq_hz = (
            np.array(h5["/spectra/freq_hz"], dtype=np.float64)
            if "/spectra/freq_hz" in h5
            else np.array([], dtype=np.float64)
        )
        transfer_abs = (
            np.array(h5["/spectra/transfer_abs"], dtype=np.float64)
            if "/spectra/transfer_abs" in h5
            else np.array([], dtype=np.float64)
        )
        ru_time = np.array(h5["/pwp/time"], dtype=np.float64) if "/pwp/time" in h5 else np.array([])
        ru = np.array(h5["/pwp/ru"], dtype=np.float64) if "/pwp/ru" in h5 else np.array([])
        delta_u = (
            np.array(h5["/pwp/delta_u"], dtype=np.float64)
            if "/pwp/delta_u" in h5
            else np.array([])
        )
        sigma_v_ref_arr = (
            np.array(h5["/pwp/sigma_v_ref"], dtype=np.float64)
            if "/pwp/sigma_v_ref" in h5
            else np.array([])
        )
        sigma_v_eff = (
            np.array(h5["/pwp/sigma_v_eff"], dtype=np.float64)
            if "/pwp/sigma_v_eff" in h5
            else np.array([])
        )

    if time.size == 0 and acc.size > 0:
        dt = 1.0
        if ru_time.size > 1:
            dt = float(ru_time[1] - ru_time[0])
        time = np.arange(acc.size, dtype=np.float64) * dt

    sigma_v_ref = (
        float(sigma_v_ref_arr.reshape(-1)[0])
        if sigma_v_ref_arr.size > 0
        else float("nan")
    )

    return ResultStore(
        run_id=root.name,
        hdf5_path=hdf5_path,
        sqlite_path=sqlite_path,
        time=time,
        acc_surface=acc,
        spectra_periods=periods,
        spectra_psa=psa,
        transfer_freq_hz=transfer_freq_hz,
        transfer_abs=transfer_abs,
        ru_time=ru_time,
        ru=ru,
        delta_u=delta_u,
        sigma_v_ref=sigma_v_ref,
        sigma_v_eff=sigma_v_eff,
    )
