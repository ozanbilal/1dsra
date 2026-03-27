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
    dt_s: float
    time: np.ndarray
    acc_surface: np.ndarray
    acc_input: np.ndarray
    spectra_periods: np.ndarray
    spectra_psa: np.ndarray
    transfer_freq_hz: np.ndarray
    transfer_abs: np.ndarray
    ru_time: np.ndarray
    ru: np.ndarray
    delta_u: np.ndarray
    sigma_v_ref: float
    sigma_v_eff: np.ndarray
    eql_iterations: int | None
    eql_converged: bool | None
    eql_max_change_history: np.ndarray
    eql_layer_idx: np.ndarray
    eql_layer_vs_m_s: np.ndarray
    eql_layer_damping: np.ndarray
    eql_layer_gamma_eff: np.ndarray
    eql_layer_gamma_max: np.ndarray


def load_result(output_dir: str | Path) -> ResultStore:
    root = Path(output_dir)
    hdf5_path = root / "results.h5"
    sqlite_path = root / "results.sqlite"

    with h5py.File(hdf5_path, "r") as h5:
        dt_meta_arr = (
            np.array(h5["/meta/delta_t_s"], dtype=np.float64)
            if "/meta/delta_t_s" in h5
            else np.array([], dtype=np.float64)
        )
        time = np.array(h5["/time"], dtype=np.float64) if "/time" in h5 else np.array([])
        acc = np.array(h5["/signals/surface_acc"], dtype=np.float64)
        acc_input = (
            np.array(h5["/signals/input_acc"], dtype=np.float64)
            if "/signals/input_acc" in h5
            else np.array([], dtype=np.float64)
        )
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
        if "/eql" in h5:
            eql_iterations_arr = (
                np.array(h5["/eql/iterations"], dtype=np.int64)
                if "/eql/iterations" in h5
                else np.array([], dtype=np.int64)
            )
            eql_converged_arr = (
                np.array(h5["/eql/converged"], dtype=np.int8)
                if "/eql/converged" in h5
                else np.array([], dtype=np.int8)
            )
            eql_max_change_history = (
                np.array(h5["/eql/max_change_history"], dtype=np.float64)
                if "/eql/max_change_history" in h5
                else np.array([], dtype=np.float64)
            )
            eql_layer_idx = (
                np.array(h5["/eql/layer_idx"], dtype=np.int64)
                if "/eql/layer_idx" in h5
                else np.array([], dtype=np.int64)
            )
            eql_layer_vs = (
                np.array(h5["/eql/layer_vs_m_s"], dtype=np.float64)
                if "/eql/layer_vs_m_s" in h5
                else np.array([], dtype=np.float64)
            )
            eql_layer_damping = (
                np.array(h5["/eql/layer_damping"], dtype=np.float64)
                if "/eql/layer_damping" in h5
                else np.array([], dtype=np.float64)
            )
            eql_layer_gamma_eff = (
                np.array(h5["/eql/layer_gamma_eff"], dtype=np.float64)
                if "/eql/layer_gamma_eff" in h5
                else np.array([], dtype=np.float64)
            )
            eql_layer_gamma_max = (
                np.array(h5["/eql/layer_gamma_max"], dtype=np.float64)
                if "/eql/layer_gamma_max" in h5
                else np.array([], dtype=np.float64)
            )
        else:
            eql_iterations_arr = np.array([], dtype=np.int64)
            eql_converged_arr = np.array([], dtype=np.int8)
            eql_max_change_history = np.array([], dtype=np.float64)
            eql_layer_idx = np.array([], dtype=np.int64)
            eql_layer_vs = np.array([], dtype=np.float64)
            eql_layer_damping = np.array([], dtype=np.float64)
            eql_layer_gamma_eff = np.array([], dtype=np.float64)
            eql_layer_gamma_max = np.array([], dtype=np.float64)

    if time.size == 0 and acc.size > 0:
        dt = 1.0
        if ru_time.size > 1:
            dt = float(ru_time[1] - ru_time[0])
        time = np.arange(acc.size, dtype=np.float64) * dt

    if dt_meta_arr.size > 0 and np.isfinite(dt_meta_arr.reshape(-1)[0]):
        dt_s = float(dt_meta_arr.reshape(-1)[0])
    elif time.size > 1:
        dt_s = float(np.median(np.diff(time)))
    elif ru_time.size > 1:
        dt_s = float(np.median(np.diff(ru_time)))
    else:
        dt_s = 1.0

    sigma_v_ref = (
        float(sigma_v_ref_arr.reshape(-1)[0])
        if sigma_v_ref_arr.size > 0
        else float("nan")
    )
    eql_iterations = (
        int(eql_iterations_arr.reshape(-1)[0])
        if eql_iterations_arr.size > 0
        else None
    )
    eql_converged = (
        bool(int(eql_converged_arr.reshape(-1)[0]))
        if eql_converged_arr.size > 0
        else None
    )

    return ResultStore(
        run_id=root.name,
        hdf5_path=hdf5_path,
        sqlite_path=sqlite_path,
        dt_s=dt_s,
        time=time,
        acc_surface=acc,
        acc_input=acc_input,
        spectra_periods=periods,
        spectra_psa=psa,
        transfer_freq_hz=transfer_freq_hz,
        transfer_abs=transfer_abs,
        ru_time=ru_time,
        ru=ru,
        delta_u=delta_u,
        sigma_v_ref=sigma_v_ref,
        sigma_v_eff=sigma_v_eff,
        eql_iterations=eql_iterations,
        eql_converged=eql_converged,
        eql_max_change_history=eql_max_change_history,
        eql_layer_idx=eql_layer_idx,
        eql_layer_vs_m_s=eql_layer_vs,
        eql_layer_damping=eql_layer_damping,
        eql_layer_gamma_eff=eql_layer_gamma_eff,
        eql_layer_gamma_max=eql_layer_gamma_max,
    )
