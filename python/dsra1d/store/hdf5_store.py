from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

from dsra1d.post.spectra import Spectra


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if np.isfinite(value):
            return int(value)
        return default
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _layer_map(
    eql_summary: dict[str, object],
    key: str,
) -> dict[int, float]:
    raw = eql_summary.get(key)
    if not isinstance(raw, dict):
        return {}
    mapped: dict[int, float] = {}
    for k, v in raw.items():
        try:
            idx = int(k)
            mapped[idx] = float(v)
        except (TypeError, ValueError):
            continue
    return mapped


def write_hdf5(
    path: Path,
    time: np.ndarray,
    dt_s: float,
    acc_surface: np.ndarray,
    ru_time: np.ndarray,
    ru: np.ndarray,
    delta_u: np.ndarray,
    sigma_v_ref: float,
    sigma_v_eff: np.ndarray,
    spectra: Spectra,
    transfer_freq_hz: np.ndarray,
    transfer_abs: np.ndarray,
    mesh_layer_idx: np.ndarray,
    mesh_z_top: np.ndarray,
    mesh_z_bot: np.ndarray,
    mesh_dz: np.ndarray,
    mesh_n_sub: np.ndarray,
    eql_summary: dict[str, object] | None = None,
    acc_input: np.ndarray | None = None,
    acc_applied_input: np.ndarray | None = None,
    input_dt_s: float | None = None,
    node_depth_m: np.ndarray | None = None,
    nodal_displacement_m: np.ndarray | None = None,
) -> Path:
    with h5py.File(path, "w") as h5:
        h5.create_dataset("/time", data=time)
        meta = h5.create_group("/meta")
        meta.create_dataset("delta_t_s", data=np.array([dt_s], dtype=np.float64))
        if input_dt_s is not None:
            meta.create_dataset("input_delta_t_s", data=np.array([input_dt_s], dtype=np.float64))
        depth = np.array([0.0], dtype=np.float64)
        h5.create_dataset("/depth", data=depth)

        signals = h5.create_group("/signals")
        signals.create_dataset("surface_acc", data=acc_surface)
        if acc_input is not None:
            signals.create_dataset("input_acc", data=acc_input)
        if acc_applied_input is not None:
            signals.create_dataset("applied_input_acc", data=acc_applied_input)
        if nodal_displacement_m is not None:
            signals.create_dataset("nodal_disp_m", data=nodal_displacement_m)

        pwp = h5.create_group("/pwp")
        pwp.create_dataset("time", data=ru_time)
        pwp.create_dataset("ru", data=ru)
        pwp.create_dataset("delta_u", data=delta_u)
        pwp.create_dataset("sigma_v_ref", data=np.array([sigma_v_ref], dtype=np.float64))
        pwp.create_dataset("sigma_v_eff", data=sigma_v_eff)

        spec = h5.create_group("/spectra")
        spec.create_dataset("periods", data=spectra.periods)
        spec.create_dataset("psa", data=spectra.psa)
        spec.create_dataset("freq_hz", data=transfer_freq_hz)
        spec.create_dataset("transfer_abs", data=transfer_abs)

        mesh = h5.create_group("/mesh")
        mesh.create_dataset("layer_idx", data=mesh_layer_idx)
        mesh.create_dataset("z_top", data=mesh_z_top)
        mesh.create_dataset("z_bot", data=mesh_z_bot)
        mesh.create_dataset("dz", data=mesh_dz)
        mesh.create_dataset("n_sub", data=mesh_n_sub)
        if node_depth_m is not None:
            mesh.create_dataset("node_depth_m", data=node_depth_m)

        if eql_summary is not None:
            eql = h5.create_group("/eql")
            iterations = _as_int(eql_summary.get("iterations", 0))
            converged = bool(eql_summary.get("converged", False))
            max_change_history_raw = eql_summary.get("max_change_history", [])
            if isinstance(max_change_history_raw, list):
                max_change_history = np.asarray(max_change_history_raw, dtype=np.float64)
            else:
                max_change_history = np.asarray([], dtype=np.float64)
            eql.create_dataset("iterations", data=np.array([iterations], dtype=np.int64))
            eql.create_dataset("converged", data=np.array([1 if converged else 0], dtype=np.int8))
            eql.create_dataset("max_change_history", data=max_change_history)

            layer_vs = _layer_map(eql_summary, "layer_vs_m_s")
            layer_damp = _layer_map(eql_summary, "layer_damping")
            layer_gamma = _layer_map(eql_summary, "layer_gamma_eff")
            layer_gamma_max = _layer_map(eql_summary, "layer_max_abs_strain")
            layer_idx_all = sorted(
                set(layer_vs) | set(layer_damp) | set(layer_gamma) | set(layer_gamma_max)
            )
            layer_idx = np.asarray(layer_idx_all, dtype=np.int64)
            eql.create_dataset("layer_idx", data=layer_idx)
            eql.create_dataset(
                "layer_vs_m_s",
                data=np.asarray([layer_vs.get(i, np.nan) for i in layer_idx_all], dtype=np.float64),
            )
            eql.create_dataset(
                "layer_damping",
                data=np.asarray(
                    [layer_damp.get(i, np.nan) for i in layer_idx_all],
                    dtype=np.float64,
                ),
            )
            eql.create_dataset(
                "layer_gamma_eff",
                data=np.asarray(
                    [layer_gamma.get(i, np.nan) for i in layer_idx_all],
                    dtype=np.float64,
                ),
            )
            eql.create_dataset(
                "layer_gamma_max",
                data=np.asarray(
                    [layer_gamma_max.get(i, np.nan) for i in layer_idx_all],
                    dtype=np.float64,
                ),
            )

    return path
