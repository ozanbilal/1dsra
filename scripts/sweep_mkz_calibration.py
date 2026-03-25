"""Sweep MKZ/GQH calibration parameters and generate candidate configs for parity iteration.

Produces a grid of YAML configs varying reload_factor, gamma_ref scaling, and
damping bounds.  Each config targets the Example 5A rigid-base nonlinear case
so that StrataWave `run` + `compare-deepsoil` can be called per candidate.

Usage:
    python scripts/sweep_mkz_calibration.py [--out <dir>] [--base-config <yaml>]

Outputs per candidate:
    <out>/<sweep_id>/config.yml
    <out>/sweep_manifest.json   (batch summary for downstream tooling)
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from itertools import product
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from dsra1d.calibration import (  # noqa: E402
    calibrate_mkz_from_darendeli,
    generate_darendeli_curves,
)

# ---------------------------------------------------------------------------
# Default sweep grid
# ---------------------------------------------------------------------------
DEFAULT_RELOAD_FACTORS = [1.2, 1.3, 1.4, 1.45, 1.5, 1.6, 1.8, 2.0]
DEFAULT_GAMMA_REF_SCALES = [0.7, 0.85, 1.0, 1.15, 1.3]
DEFAULT_DAMPING_MAX_VALUES = [0.10, 0.12, 0.15]
DEFAULT_SUBSTEPS = [8, 16]

# Example 5A Darendeli soil properties (uniform 5-layer column)
EXAMPLE_5A_LAYERS = [
    {
        "name": "Layer1",
        "thickness_m": 4.0,
        "unit_weight_kN_m3": 20.0,
        "vs_m_s": 250.0,
        "gmax": 127420.0,
        "plasticity_index": 15.0,
        "ocr": 1.0,
        "mean_effective_stress_kpa": 40.0,
    },
    {
        "name": "Layer2",
        "thickness_m": 4.0,
        "unit_weight_kN_m3": 20.0,
        "vs_m_s": 250.0,
        "gmax": 127420.0,
        "plasticity_index": 15.0,
        "ocr": 1.0,
        "mean_effective_stress_kpa": 80.0,
    },
    {
        "name": "Layer3",
        "thickness_m": 4.0,
        "unit_weight_kN_m3": 20.0,
        "vs_m_s": 250.0,
        "gmax": 127420.0,
        "plasticity_index": 20.0,
        "ocr": 1.0,
        "mean_effective_stress_kpa": 120.0,
    },
    {
        "name": "Layer4",
        "thickness_m": 4.0,
        "unit_weight_kN_m3": 20.0,
        "vs_m_s": 250.0,
        "gmax": 127420.0,
        "plasticity_index": 20.0,
        "ocr": 1.0,
        "mean_effective_stress_kpa": 160.0,
    },
    {
        "name": "Layer5",
        "thickness_m": 4.0,
        "unit_weight_kN_m3": 20.0,
        "vs_m_s": 250.0,
        "gmax": 127420.0,
        "plasticity_index": 20.0,
        "ocr": 1.0,
        "mean_effective_stress_kpa": 200.0,
    },
]

# Base analysis config matching the Example 5A nonlinear rigid setup
BASE_ANALYSIS = {
    "dt": 0.0025,
    "f_max": 25.0,
    "solver_backend": "nonlinear",
    "nonlinear_substeps": 16,
    "pm4_validation_profile": "basic",
    "damping_mode": "frequency_independent",
    "rayleigh_mode_1_hz": 1.0,
    "rayleigh_mode_2_hz": 5.0,
    "rayleigh_update_matrix": False,
    "timeout_s": 180,
    "retries": 1,
}


def _calibrate_layer(
    layer: dict,
    reload_factor: float,
    gamma_ref_scale: float,
    damping_max: float,
) -> dict:
    """Calibrate MKZ params from Darendeli for a single layer."""
    result = calibrate_mkz_from_darendeli(
        gmax=layer["gmax"],
        plasticity_index=layer["plasticity_index"],
        ocr=layer["ocr"],
        mean_effective_stress_kpa=layer["mean_effective_stress_kpa"],
        reload_factor=reload_factor,
    )
    params = dict(result.material_params)
    # Apply gamma_ref scaling
    params["gamma_ref"] = params["gamma_ref"] * gamma_ref_scale
    # Override damping_max
    params["damping_max"] = damping_max
    return params


def _build_config(
    layers: list[dict],
    reload_factor: float,
    gamma_ref_scale: float,
    damping_max: float,
    substeps: int,
    sweep_id: str,
) -> dict:
    """Build a full StrataWave YAML config dict for a sweep candidate."""
    profile_layers = []
    for layer_def in layers:
        params = _calibrate_layer(layer_def, reload_factor, gamma_ref_scale, damping_max)
        profile_layers.append(
            {
                "name": layer_def["name"],
                "thickness_m": layer_def["thickness_m"],
                "unit_weight_kN_m3": layer_def["unit_weight_kN_m3"],
                "vs_m_s": layer_def["vs_m_s"],
                "material": "mkz",
                "material_params": params,
                "material_optional_args": [],
                "calibration": None,
            }
        )

    analysis = dict(BASE_ANALYSIS)
    analysis["nonlinear_substeps"] = substeps

    return {
        "project_name": f"sweep-{sweep_id}",
        "seed": 20260324,
        "profile": {"layers": profile_layers},
        "boundary_condition": "rigid",
        "analysis": analysis,
        "motion": {
            "units": "g",
            "baseline": "none",
            "scale_mode": "none",
            "scale_factor": None,
            "target_pga": None,
        },
        "output": {
            "write_hdf5": True,
            "write_sqlite": True,
            "parquet_export": False,
        },
        "opensees": {
            "executable": "OpenSees",
            "extra_args": [],
            "require_version_regex": None,
            "require_binary_sha256": None,
            "column_width_m": 1.0,
            "thickness_m": 1.0,
            "fluid_bulk_modulus": 2200000.0,
            "fluid_mass_density": 1.0,
            "h_perm": 1.0e-5,
            "v_perm": 1.0e-5,
            "gravity_steps": 20,
        },
    }


def _sweep_id(rf: float, grs: float, dmax: float, subs: int) -> str:
    return f"rf{rf:.2f}_grs{grs:.2f}_dmax{dmax:.2f}_sub{subs}"


def run_sweep(
    out_dir: Path,
    base_config_path: Path | None = None,
    reload_factors: list[float] | None = None,
    gamma_ref_scales: list[float] | None = None,
    damping_max_values: list[float] | None = None,
    substeps_values: list[int] | None = None,
) -> Path:
    """Generate sweep configs and manifest."""
    rf_values = reload_factors or DEFAULT_RELOAD_FACTORS
    grs_values = gamma_ref_scales or DEFAULT_GAMMA_REF_SCALES
    dmax_values = damping_max_values or DEFAULT_DAMPING_MAX_VALUES
    subs_values = substeps_values or DEFAULT_SUBSTEPS

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_cases: list[dict] = []

    total = len(rf_values) * len(grs_values) * len(dmax_values) * len(subs_values)
    print(f"Generating {total} sweep candidates ...")

    for rf, grs, dmax, subs in product(rf_values, grs_values, dmax_values, subs_values):
        sid = _sweep_id(rf, grs, dmax, subs)
        case_dir = out_dir / sid
        case_dir.mkdir(parents=True, exist_ok=True)

        config = _build_config(EXAMPLE_5A_LAYERS, rf, grs, dmax, subs, sid)
        config_path = case_dir / "config.yml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # Extract representative params for manifest
        layer0_params = config["profile"]["layers"][0]["material_params"]
        manifest_cases.append(
            {
                "sweep_id": sid,
                "config_path": str(config_path),
                "reload_factor": rf,
                "gamma_ref_scale": grs,
                "gamma_ref_layer0": layer0_params["gamma_ref"],
                "damping_max": dmax,
                "damping_min_layer0": layer0_params["damping_min"],
                "nonlinear_substeps": subs,
            }
        )

    manifest_path = out_dir / "sweep_manifest.json"
    manifest = {
        "sweep_type": "mkz_calibration",
        "total_candidates": total,
        "grid": {
            "reload_factors": rf_values,
            "gamma_ref_scales": grs_values,
            "damping_max_values": dmax_values,
            "substeps": subs_values,
        },
        "cases": manifest_cases,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote {total} configs + manifest to {out_dir}")
    print(f"Manifest: {manifest_path}")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweep MKZ calibration parameters for DEEPSOIL parity iteration."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "output" / "pdf" / "validation" / "deepsoil_examples" / "calibration_sweep",
        help="Output directory for sweep configs and manifest.",
    )
    parser.add_argument(
        "--base-config",
        type=Path,
        default=None,
        help="Optional base YAML config to use as template (not yet wired).",
    )
    parser.add_argument(
        "--reload-factors",
        type=str,
        default=None,
        help="Comma-separated reload factor values (e.g., '1.2,1.4,1.6').",
    )
    parser.add_argument(
        "--gamma-ref-scales",
        type=str,
        default=None,
        help="Comma-separated gamma_ref scale factors (e.g., '0.8,1.0,1.2').",
    )
    parser.add_argument(
        "--damping-max",
        type=str,
        default=None,
        help="Comma-separated damping_max values (e.g., '0.10,0.12,0.15').",
    )
    parser.add_argument(
        "--substeps",
        type=str,
        default=None,
        help="Comma-separated substep counts (e.g., '8,16').",
    )
    args = parser.parse_args()

    rf = [float(x) for x in args.reload_factors.split(",")] if args.reload_factors else None
    grs = [float(x) for x in args.gamma_ref_scales.split(",")] if args.gamma_ref_scales else None
    dmax = [float(x) for x in args.damping_max.split(",")] if args.damping_max else None
    subs = [int(x) for x in args.substeps.split(",")] if args.substeps else None

    run_sweep(
        out_dir=args.out,
        base_config_path=args.base_config,
        reload_factors=rf,
        gamma_ref_scales=grs,
        damping_max_values=dmax,
        substeps_values=subs,
    )


if __name__ == "__main__":
    main()
