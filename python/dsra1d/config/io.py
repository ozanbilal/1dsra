from __future__ import annotations

import copy
import json
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from dsra1d.config.models import ProjectConfig

_CORE_BACKENDS = {"linear", "eql", "nonlinear"}
_CORE_MATERIALS = {"mkz", "gqh", "elastic"}
_LEGACY_PM4_MATERIALS = {"pm4sand", "pm4silt"}


def _normalize_legacy_project_payload(
    raw: dict[str, Any],
    *,
    path: Path | None = None,
) -> dict[str, Any]:
    payload = copy.deepcopy(raw)
    analysis = payload.get("analysis")
    if not isinstance(analysis, dict):
        analysis = {}
        payload["analysis"] = analysis

    profile = payload.get("profile")
    layers_raw = profile.get("layers", []) if isinstance(profile, dict) else []
    layer_materials = {
        str(layer.get("material", "")).strip().lower()
        for layer in layers_raw
        if isinstance(layer, dict)
    }
    backend = str(analysis.get("solver_backend", "")).strip().lower()
    source_label = str(path) if path is not None else "payload"

    unsupported_materials = sorted(layer_materials & _LEGACY_PM4_MATERIALS)
    if unsupported_materials:
        raise ValueError(
            "Legacy PM4/OpenSees config is no longer supported in GeoWave core mode. "
            f"Unsupported materials in {source_label}: {unsupported_materials}. "
            "Migrate to MKZ/GQH/Elastic and use linear, eql, or nonlinear."
        )

    if backend == "opensees":
        raise ValueError(
            "Legacy OpenSees config is no longer supported in GeoWave core mode. "
            f"Update {source_label} to use linear, eql, or nonlinear."
        )

    if backend == "mock":
        non_core_materials = sorted(layer_materials - _CORE_MATERIALS)
        if non_core_materials:
            raise ValueError(
                "Legacy mock config can only be migrated when all layers use MKZ/GQH/Elastic. "
                f"Found unsupported materials in {source_label}: {non_core_materials}."
            )
        analysis["solver_backend"] = "nonlinear"
        warnings.warn(
            f"{source_label} used deprecated solver_backend=mock; migrated to nonlinear.",
            stacklevel=2,
        )
    elif backend and backend not in _CORE_BACKENDS:
        raise ValueError(
            f"Unsupported solver_backend '{backend}' in {source_label}. "
            "Allowed values: linear, eql, nonlinear."
        )

    analysis.pop("pm4_validation_profile", None)
    payload.pop("opensees", None)
    return payload


def load_project_config(path: str | Path) -> ProjectConfig:
    path_obj = Path(path)
    raw: dict[str, Any]
    if path_obj.suffix.lower() in {".yml", ".yaml"}:
        raw = yaml.safe_load(path_obj.read_text(encoding="utf-8"))
    elif path_obj.suffix.lower() == ".json":
        raw = json.loads(path_obj.read_text(encoding="utf-8"))
    else:
        raise ValueError("Config must be .yaml/.yml or .json")
    normalized = _normalize_legacy_project_payload(raw, path=path_obj)
    return ProjectConfig.model_validate(normalized)


def _linear_3layer_sand_template() -> dict[str, Any]:
    return {
        "project_name": "linear-3layer-sand-template",
        "seed": 42,
        "profile": {
            "layers": [
                {
                    "name": "LooseSand",
                    "thickness_m": 5.0,
                    "unit_weight_kN_m3": 17.0,
                    "vs_m_s": 150.0,
                    "material": "elastic",
                    "material_params": {"nu": 0.30},
                },
                {
                    "name": "MediumSand",
                    "thickness_m": 10.0,
                    "unit_weight_kN_m3": 18.5,
                    "vs_m_s": 250.0,
                    "material": "elastic",
                    "material_params": {"nu": 0.30},
                },
                {
                    "name": "DenseSand",
                    "thickness_m": 15.0,
                    "unit_weight_kN_m3": 20.0,
                    "vs_m_s": 400.0,
                    "material": "elastic",
                    "material_params": {"nu": 0.28},
                },
            ]
        },
        "boundary_condition": "rigid",
        "analysis": {
            "dt": 0.005,
            "f_max": 25.0,
            "solver_backend": "linear",
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
    }


def _base_mkz_gqh_template() -> dict[str, Any]:
    return {
        "project_name": "mkz-gqh-core-template",
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
                        "reload_factor": 2.0,
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
                        "tau_max": 95.0,
                        "damping_min": 0.01,
                        "damping_max": 0.12,
                        "reload_factor": 1.6,
                        "mrdf_p1": 0.82,
                        "mrdf_p2": 0.55,
                        "mrdf_p3": 20.0,
                    },
                },
            ]
        },
        "boundary_condition": "rigid",
        "analysis": {
            "f_max": 25.0,
            "solver_backend": "nonlinear",
            "dt": 0.0025,
            "timeout_s": 180,
            "retries": 1,
        },
        "motion": {
            "units": "m/s2",
            "input_type": "outcrop",
            "baseline": "remove_mean",
            "scale_mode": "none",
        },
        "output": {
            "write_hdf5": True,
            "write_sqlite": True,
            "parquet_export": False,
        },
    }


def _mkz_gqh_eql_template() -> dict[str, Any]:
    template = _base_mkz_gqh_template()
    template["project_name"] = "mkz-gqh-eql-template"
    analysis = template["analysis"]
    if isinstance(analysis, dict):
        analysis["solver_backend"] = "eql"
        analysis["dt"] = 0.005
    return template


def _mkz_gqh_nonlinear_template() -> dict[str, Any]:
    template = _base_mkz_gqh_template()
    template["project_name"] = "mkz-gqh-nonlinear-template"
    analysis = template["analysis"]
    if isinstance(analysis, dict):
        analysis["solver_backend"] = "nonlinear"
        analysis["dt"] = 0.0025
    return template


def _mkz_gqh_darendeli_template() -> dict[str, Any]:
    return {
        "project_name": "mkz-gqh-darendeli-template",
        "seed": 42,
        "profile": {
            "layers": [
                {
                    "name": "Darendeli-MKZ",
                    "thickness_m": 6.0,
                    "unit_weight_kN_m3": 18.2,
                    "vs_m_s": 190.0,
                    "material": "mkz",
                    "material_params": {"tau_max": 80.0},
                    "calibration": {
                        "source": "darendeli",
                        "plasticity_index": 20.0,
                        "ocr": 1.5,
                        "mean_effective_stress_kpa": 80.0,
                        "frequency_hz": 1.0,
                        "num_cycles": 10.0,
                        "reload_factor": 2.0,
                    },
                },
                {
                    "name": "Darendeli-GQH",
                    "thickness_m": 10.0,
                    "unit_weight_kN_m3": 19.0,
                    "vs_m_s": 280.0,
                    "material": "gqh",
                    "calibration": {
                        "source": "darendeli",
                        "plasticity_index": 8.0,
                        "ocr": 1.0,
                        "mean_effective_stress_kpa": 150.0,
                        "frequency_hz": 1.0,
                        "num_cycles": 10.0,
                        "reload_factor": 1.6,
                    },
                },
            ]
        },
        "boundary_condition": "rigid",
        "analysis": {
            "dt": 0.0025,
            "f_max": 25.0,
            "solver_backend": "nonlinear",
            "timeout_s": 180,
            "retries": 1,
        },
        "motion": {
            "units": "m/s2",
            "input_type": "outcrop",
            "baseline": "remove_mean",
            "scale_mode": "none",
        },
        "output": {
            "write_hdf5": True,
            "write_sqlite": True,
            "parquet_export": False,
        },
    }


def _template_factories() -> dict[str, Callable[[], dict[str, Any]]]:
    return {
        "linear-3layer-sand": _linear_3layer_sand_template,
        "mkz-gqh-eql": _mkz_gqh_eql_template,
        "mkz-gqh-nonlinear": _mkz_gqh_nonlinear_template,
        "mkz-gqh-darendeli": _mkz_gqh_darendeli_template,
    }


def available_config_templates() -> tuple[str, ...]:
    return tuple(_template_factories().keys())


def get_config_template_payload(template: str = "mkz-gqh-nonlinear") -> dict[str, Any]:
    factories = _template_factories()
    if template not in factories:
        valid = ", ".join(sorted(factories))
        raise ValueError(f"Unknown template '{template}'. Valid templates: {valid}")
    content = factories[template]()
    return copy.deepcopy(content)


def write_config_template(
    path: str | Path,
    template: str = "mkz-gqh-nonlinear",
) -> Path:
    content = get_config_template_payload(template)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    return out
