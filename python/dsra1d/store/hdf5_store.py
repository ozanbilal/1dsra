from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

from dsra1d.post.spectra import Spectra


def write_hdf5(
    path: Path,
    time: np.ndarray,
    acc_surface: np.ndarray,
    ru_time: np.ndarray,
    ru: np.ndarray,
    spectra: Spectra,
    mesh_layer_idx: np.ndarray,
    mesh_z_top: np.ndarray,
    mesh_z_bot: np.ndarray,
    mesh_dz: np.ndarray,
    mesh_n_sub: np.ndarray,
) -> Path:
    with h5py.File(path, "w") as h5:
        h5.create_dataset("/time", data=time)
        depth = np.array([0.0], dtype=np.float64)
        h5.create_dataset("/depth", data=depth)

        signals = h5.create_group("/signals")
        signals.create_dataset("surface_acc", data=acc_surface)

        pwp = h5.create_group("/pwp")
        pwp.create_dataset("time", data=ru_time)
        pwp.create_dataset("ru", data=ru)

        spec = h5.create_group("/spectra")
        spec.create_dataset("periods", data=spectra.periods)
        spec.create_dataset("psa", data=spectra.psa)

        mesh = h5.create_group("/mesh")
        mesh.create_dataset("layer_idx", data=mesh_layer_idx)
        mesh.create_dataset("z_top", data=mesh_z_top)
        mesh.create_dataset("z_bot", data=mesh_z_bot)
        mesh.create_dataset("dz", data=mesh_dz)
        mesh.create_dataset("n_sub", data=mesh_n_sub)

    return path
