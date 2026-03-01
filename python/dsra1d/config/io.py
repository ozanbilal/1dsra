from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from dsra1d.config.models import ProjectConfig


def load_project_config(path: str | Path) -> ProjectConfig:
    path_obj = Path(path)
    raw: dict[str, Any]
    if path_obj.suffix.lower() in {".yml", ".yaml"}:
        raw = yaml.safe_load(path_obj.read_text(encoding="utf-8"))
    elif path_obj.suffix.lower() == ".json":
        raw = json.loads(path_obj.read_text(encoding="utf-8"))
    else:
        raise ValueError("Config must be .yaml/.yml or .json")
    return ProjectConfig.model_validate(raw)


def _effective_stress_template() -> dict[str, Any]:
    return {
        "project_name": "effective-stress-template",
        "seed": 42,
        "profile": {
            "layers": [
                {
                    "name": "Layer-1",
                    "thickness_m": 5.0,
                    "unit_weight_kN_m3": 18.0,
                    "vs_m_s": 180.0,
                    "material": "pm4sand",
                    "material_params": {
                        "Dr": 0.45,
                        "G0": 600.0,
                        "hpo": 0.53,
                    },
                    "material_optional_args": [],
                },
                {
                    "name": "Layer-2",
                    "thickness_m": 10.0,
                    "unit_weight_kN_m3": 19.0,
                    "vs_m_s": 300.0,
                    "material": "pm4silt",
                    "material_params": {
                        "Su": 35.0,
                        "Su_Rat": 0.25,
                        "G_o": 500.0,
                        "h_po": 0.6,
                    },
                    "material_optional_args": [],
                },
            ]
        },
        "boundary_condition": "elastic_halfspace",
        "analysis": {
            "dt": 0.002,
            "f_max": 25.0,
            "solver_backend": "opensees",
            "pm4_validation_profile": "basic",
            "timeout_s": 180,
            "retries": 1,
        },
        "motion": {
            "units": "m/s2",
            "baseline": "remove_mean",
            "scale_mode": "none",
        },
        "output": {
            "write_hdf5": True,
            "write_sqlite": True,
            "parquet_export": False,
        },
        "opensees": {
            "executable": "OpenSees",
            "extra_args": [],
            "column_width_m": 1.0,
            "thickness_m": 1.0,
            "fluid_bulk_modulus": 2.2e6,
            "fluid_mass_density": 1.0,
            "h_perm": 1.0e-5,
            "v_perm": 1.0e-5,
            "gravity_steps": 20,
        },
    }


def _effective_stress_strict_plus_template() -> dict[str, Any]:
    return {
        "project_name": "effective-stress-strict-plus-template",
        "seed": 42,
        "profile": {
            "layers": [
                {
                    "name": "Layer-1",
                    "thickness_m": 6.0,
                    "unit_weight_kN_m3": 18.5,
                    "vs_m_s": 180.0,
                    "material": "pm4sand",
                    "material_params": {
                        "Dr": 0.45,
                        "G0": 600.0,
                        "hpo": 0.53,
                    },
                    "material_optional_args": [],
                },
                {
                    "name": "Layer-2",
                    "thickness_m": 8.0,
                    "unit_weight_kN_m3": 19.0,
                    "vs_m_s": 240.0,
                    "material": "pm4silt",
                    "material_params": {
                        "Su": 35.0,
                        "Su_Rat": 0.25,
                        "G_o": 500.0,
                        "h_po": 0.6,
                    },
                    "material_optional_args": [],
                },
            ]
        },
        "boundary_condition": "elastic_halfspace",
        "analysis": {
            "dt": 0.002,
            "f_max": 25.0,
            "solver_backend": "opensees",
            "pm4_validation_profile": "strict_plus",
            "timeout_s": 180,
            "retries": 1,
        },
        "motion": {
            "units": "m/s2",
            "baseline": "remove_mean",
            "scale_mode": "none",
        },
        "output": {
            "write_hdf5": True,
            "write_sqlite": True,
            "parquet_export": False,
        },
        "opensees": {
            "executable": "OpenSees",
            "extra_args": [],
            "column_width_m": 1.0,
            "thickness_m": 1.0,
            "fluid_bulk_modulus": 2.2e6,
            "fluid_mass_density": 1.0,
            "h_perm": 1.0e-5,
            "v_perm": 1.0e-5,
            "gravity_steps": 20,
        },
    }


def _mkz_gqh_mock_template() -> dict[str, Any]:
    return {
        "project_name": "mkz-gqh-mock-template",
        "seed": 42,
        "profile": {
            "layers": [
                {
                    "name": "MKZ-Top",
                    "thickness_m": 6.0,
                    "unit_weight_kN_m3": 18.5,
                    "vs_m_s": 210.0,
                    "material": "mkz",
                    "material_params": {
                        "gmax": 70000.0,
                        "gamma_ref": 0.0012,
                        "damping_min": 0.01,
                        "damping_max": 0.10,
                    },
                },
                {
                    "name": "GQH-Bottom",
                    "thickness_m": 12.0,
                    "unit_weight_kN_m3": 19.5,
                    "vs_m_s": 320.0,
                    "material": "gqh",
                    "material_params": {
                        "gmax": 110000.0,
                        "gamma_ref": 0.0010,
                        "a1": 1.0,
                        "a2": 0.45,
                        "m": 2.0,
                        "damping_min": 0.01,
                        "damping_max": 0.12,
                    },
                },
            ]
        },
        "boundary_condition": "elastic_halfspace",
        "analysis": {
            "f_max": 25.0,
            "solver_backend": "mock",
            "timeout_s": 180,
            "retries": 1,
        },
        "motion": {
            "units": "m/s2",
            "baseline": "remove_mean",
            "scale_mode": "none",
        },
        "output": {
            "write_hdf5": True,
            "write_sqlite": True,
            "parquet_export": False,
        },
        "opensees": {
            "executable": "OpenSees",
            "extra_args": [],
            "column_width_m": 1.0,
            "thickness_m": 1.0,
            "fluid_bulk_modulus": 2.2e6,
            "fluid_mass_density": 1.0,
            "h_perm": 1.0e-5,
            "v_perm": 1.0e-5,
            "gravity_steps": 20,
        },
    }


def write_config_template(
    path: str | Path,
    template: str = "effective-stress",
) -> Path:
    templates: dict[str, dict[str, Any]] = {
        "effective-stress": _effective_stress_template(),
        "effective-stress-strict-plus": _effective_stress_strict_plus_template(),
        "mkz-gqh-mock": _mkz_gqh_mock_template(),
    }
    if template not in templates:
        valid = ", ".join(sorted(templates))
        raise ValueError(f"Unknown template '{template}'. Valid templates: {valid}")
    content = templates[template]

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    return out
