from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dsra1d.config import ProjectConfig
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.nonlinear import simulate_hysteretic_stress_path


@dataclass(slots=True, frozen=True)
class LayerResponseHistory:
    layer_index_zero_based: int
    layer_tag: int
    layer_name: str
    z_mid_m: float
    strain: np.ndarray
    stress_kpa: np.ndarray
    gamma_max: float
    tau_peak_kpa: float
    secant_g_kpa: float | None
    secant_g_over_gmax: float | None


def derive_layer_response_histories(
    config: ProjectConfig,
    *,
    node_depth_m: np.ndarray,
    nodal_displacement_m: np.ndarray,
) -> list[LayerResponseHistory]:
    node_depth = np.asarray(node_depth_m, dtype=np.float64).reshape(-1)
    disp = np.asarray(nodal_displacement_m, dtype=np.float64)
    if node_depth.size < 2 or disp.ndim != 2 or disp.shape[0] < 2 or disp.shape[1] < 2:
        return []

    layer_slices = build_layer_slices(config)
    element_slices = build_element_slices(layer_slices)
    n_elem = len(element_slices)
    if n_elem == 0 or disp.shape[0] != (n_elem + 1):
        return []

    dz_elem = np.diff(node_depth)
    if dz_elem.size != n_elem or np.any(~np.isfinite(dz_elem)) or np.any(dz_elem <= 0.0):
        dz_elem = np.array([float(max(elem.dz_m, 1.0e-9)) for elem in element_slices], dtype=np.float64)

    layer_to_elem_indices: dict[int, list[int]] = defaultdict(list)
    elem_strain: list[np.ndarray] = []
    elem_stress: list[np.ndarray] = []

    for elem_idx, elem in enumerate(element_slices):
        cfg_layer = config.profile.layers[elem.layer_index - 1]
        dz = float(max(dz_elem[elem_idx], 1.0e-12))
        gamma = (disp[elem_idx, :] - disp[elem_idx + 1, :]) / dz
        rho = float(max(cfg_layer.unit_weight_kn_m3 / 9.81, 1.0e-6))
        # The solver uses kN-m-s units, so rho*Vs^2 is numerically in kPa.
        gmax_kpa = rho * float(cfg_layer.vs_m_s) * float(cfg_layer.vs_m_s)
        tau = simulate_hysteretic_stress_path(
            cfg_layer.material,
            cfg_layer.material_params,
            gamma,
            gmax_fallback=gmax_kpa,
        )
        elem_strain.append(np.asarray(gamma, dtype=np.float64))
        elem_stress.append(np.asarray(tau, dtype=np.float64))
        layer_to_elem_indices[elem.layer_index - 1].append(elem_idx)

    histories: list[LayerResponseHistory] = []
    for layer_idx_zero, cfg_layer in enumerate(config.profile.layers):
        elem_indices = layer_to_elem_indices.get(layer_idx_zero, [])
        if not elem_indices:
            continue
        weights = np.array([float(max(dz_elem[i], 1.0e-12)) for i in elem_indices], dtype=np.float64)
        strain_stack = np.vstack([elem_strain[i] for i in elem_indices])
        stress_stack = np.vstack([elem_stress[i] for i in elem_indices])
        layer_strain = np.average(strain_stack, axis=0, weights=weights).astype(np.float64)
        layer_stress = np.average(stress_stack, axis=0, weights=weights).astype(np.float64)
        gamma_max = float(np.max(np.abs(strain_stack))) if strain_stack.size > 0 else 0.0
        tau_peak_kpa = float(np.max(np.abs(layer_stress))) if layer_stress.size > 0 else 0.0

        idx_peak = int(np.argmax(np.abs(layer_strain))) if layer_strain.size > 0 else 0
        gamma_peak = float(abs(layer_strain[idx_peak])) if layer_strain.size > 0 else 0.0
        if gamma_peak > 1.0e-12:
            secant_g_kpa = float(abs(layer_stress[idx_peak] / layer_strain[idx_peak]))
        else:
            secant_g_kpa = None

        rho = float(max(cfg_layer.unit_weight_kn_m3 / 9.81, 1.0e-6))
        gmax_kpa = rho * float(cfg_layer.vs_m_s) * float(cfg_layer.vs_m_s)
        if secant_g_kpa is not None and gmax_kpa > 0.0:
            secant_ratio = float(secant_g_kpa / gmax_kpa)
        else:
            secant_ratio = None

        histories.append(
            LayerResponseHistory(
                layer_index_zero_based=layer_idx_zero,
                layer_tag=layer_idx_zero + 1,
                layer_name=cfg_layer.name,
                z_mid_m=float(sum(slice_.thickness_m for slice_ in layer_slices[:layer_idx_zero]) + (cfg_layer.thickness_m * 0.5)),
                strain=layer_strain,
                stress_kpa=layer_stress,
                gamma_max=gamma_max,
                tau_peak_kpa=tau_peak_kpa,
                secant_g_kpa=secant_g_kpa,
                secant_g_over_gmax=secant_ratio,
            )
        )
    return histories


def write_layer_response_outputs(
    run_dir: Path,
    *,
    time_s: np.ndarray,
    histories: list[LayerResponseHistory],
) -> tuple[list[tuple[str, Path]], Path | None]:
    if not histories:
        return [], None

    out_files: list[tuple[str, Path]] = []
    time_arr = np.asarray(time_s, dtype=np.float64).reshape(-1)
    for history in histories:
        n = int(min(time_arr.size, history.strain.size, history.stress_kpa.size))
        if n < 2:
            continue
        strain_path = run_dir / f"layer_{history.layer_tag}_strain.out"
        stress_path = run_dir / f"layer_{history.layer_tag}_stress.out"
        np.savetxt(
            strain_path,
            np.column_stack([time_arr[:n], history.strain[:n]]),
        )
        np.savetxt(
            stress_path,
            np.column_stack([time_arr[:n], history.stress_kpa[:n]]),
        )
        out_files.append((f"layer_{history.layer_tag}_strain", strain_path))
        out_files.append((f"layer_{history.layer_tag}_stress", stress_path))

    summary_path = run_dir / "layer_response_summary.csv"
    lines = [
        "layer_index,layer_tag,layer_name,z_mid_m,gamma_max,tau_peak_kpa,secant_g_pa,secant_g_over_gmax"
    ]
    for history in histories:
        secant_g_pa = "" if history.secant_g_kpa is None else f"{(history.secant_g_kpa * 1000.0):.10e}"
        secant_ratio = (
            ""
            if history.secant_g_over_gmax is None
            else f"{history.secant_g_over_gmax:.10e}"
        )
        layer_name = history.layer_name.replace('"', '""')
        lines.append(
            ",".join(
                [
                    str(history.layer_index_zero_based),
                    str(history.layer_tag),
                    f"\"{layer_name}\"",
                    f"{history.z_mid_m:.8f}",
                    f"{history.gamma_max:.10e}",
                    f"{history.tau_peak_kpa:.10e}",
                    secant_g_pa,
                    secant_ratio,
                ]
            )
        )
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return out_files, summary_path
