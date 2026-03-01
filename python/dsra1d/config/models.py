from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, field_validator, model_validator

from dsra1d.units import normalize_accel_unit


class MaterialType(StrEnum):
    PM4SAND = "pm4sand"
    PM4SILT = "pm4silt"
    ELASTIC = "elastic"


class BoundaryCondition(StrEnum):
    RIGID = "rigid"
    ELASTIC_HALFSPACE = "elastic_halfspace"


class ScaleMode(StrEnum):
    NONE = "none"
    SCALE_BY = "scale_by"
    SCALE_TO_PGA = "scale_to_pga"


class BaselineMode(StrEnum):
    NONE = "none"
    REMOVE_MEAN = "remove_mean"
    DETREND_LINEAR = "detrend_linear"


class OutputConfig(BaseModel):
    write_hdf5: bool = True
    write_sqlite: bool = True
    parquet_export: bool = False


class MotionConfig(BaseModel):
    units: str = "m/s2"
    baseline: BaselineMode = BaselineMode.REMOVE_MEAN
    scale_mode: ScaleMode = ScaleMode.NONE
    scale_factor: float | None = None
    target_pga: float | None = None

    @field_validator("units")
    @classmethod
    def validate_units(cls, value: str) -> str:
        return normalize_accel_unit(value)

    @model_validator(mode="after")
    def validate_scaling(self) -> MotionConfig:
        if self.scale_mode == ScaleMode.SCALE_BY and self.scale_factor is None:
            raise ValueError("scale_factor is required when scale_mode=scale_by")
        if self.scale_mode == ScaleMode.SCALE_TO_PGA and self.target_pga is None:
            raise ValueError("target_pga is required when scale_mode=scale_to_pga")
        return self


class AnalysisControl(BaseModel):
    dt: PositiveFloat | None = None
    t_end: PositiveFloat | None = None
    f_max: PositiveFloat = 25.0
    solver_backend: Literal["opensees", "mock"] = "opensees"
    timeout_s: int = 180
    retries: int = 1


class Layer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    thickness_m: PositiveFloat
    unit_weight_kn_m3: PositiveFloat = Field(alias="unit_weight_kN_m3")
    vs_m_s: PositiveFloat
    material: MaterialType
    material_params: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_material_params(self) -> Layer:
        allowed: set[str]
        if self.material == MaterialType.PM4SAND:
            allowed = {"Dr", "G0", "hpo"}
            dr = self.material_params.get("Dr")
            if dr is not None and not (0.0 < dr <= 1.0):
                raise ValueError("PM4Sand parameter 'Dr' must be in (0, 1].")
            for key in ("G0", "hpo"):
                val = self.material_params.get(key)
                if val is not None and val <= 0.0:
                    raise ValueError(f"PM4Sand parameter '{key}' must be > 0.")
        elif self.material == MaterialType.PM4SILT:
            allowed = {"Su", "Su_Rat", "G_o", "h_po"}
            su_rat = self.material_params.get("Su_Rat")
            if su_rat is not None and not (0.0 < su_rat <= 1.0):
                raise ValueError("PM4Silt parameter 'Su_Rat' must be in (0, 1].")
            for key in ("Su", "G_o", "h_po"):
                val = self.material_params.get(key)
                if val is not None and val <= 0.0:
                    raise ValueError(f"PM4Silt parameter '{key}' must be > 0.")
        else:
            allowed = {"nu"}
            nu = self.material_params.get("nu")
            if nu is not None and not (0.0 < nu < 0.5):
                raise ValueError("Elastic parameter 'nu' must be in (0, 0.5).")

        unknown = set(self.material_params) - allowed
        if unknown:
            raise ValueError(
                f"Unknown material_params for {self.material.value}: {sorted(unknown)}"
            )
        for key, value in self.material_params.items():
            if not math.isfinite(value):
                raise ValueError(f"Material parameter '{key}' must be finite.")
        return self


class SoilProfile(BaseModel):
    layers: list[Layer] = Field(min_length=1)


class OpenseesConfig(BaseModel):
    executable: str = "OpenSees"
    extra_args: list[str] = Field(default_factory=list)


class ProjectConfig(BaseModel):
    project_name: str = "1dsra-project"
    seed: int = 42
    profile: SoilProfile
    boundary_condition: BoundaryCondition = BoundaryCondition.ELASTIC_HALFSPACE
    analysis: AnalysisControl = Field(default_factory=AnalysisControl)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    opensees: OpenseesConfig = Field(default_factory=OpenseesConfig)

    @field_validator("project_name")
    @classmethod
    def project_name_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project_name cannot be empty")
        return value

    @model_validator(mode="after")
    def fill_dt(self) -> ProjectConfig:
        if self.analysis.dt is None:
            self.analysis.dt = 1.0 / (20.0 * self.analysis.f_max)
        return self

    @model_validator(mode="after")
    def validate_pm4_for_backend(self) -> ProjectConfig:
        if self.analysis.solver_backend != "opensees":
            return self

        required_by_material: dict[MaterialType, set[str]] = {
            MaterialType.PM4SAND: {"Dr", "G0", "hpo"},
            MaterialType.PM4SILT: {"Su", "Su_Rat", "G_o", "h_po"},
        }
        for layer in self.profile.layers:
            required = required_by_material.get(layer.material)
            if required is None:
                continue
            missing = sorted(required - set(layer.material_params))
            if missing:
                raise ValueError(
                    f"Layer '{layer.name}' ({layer.material.value}) is missing required "
                    f"material_params for opensees backend: {missing}"
                )
        return self
