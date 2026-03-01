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


def write_config_template(path: str | Path) -> Path:
    template = {
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
        },
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    return out
