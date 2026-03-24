from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, field_validator, model_validator

from dsra1d.calibration import (
    DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
    calibrate_gqh_from_darendeli,
    calibrate_mkz_from_darendeli,
)
from dsra1d.units import normalize_accel_unit


class MaterialType(StrEnum):
    PM4SAND = "pm4sand"
    PM4SILT = "pm4silt"
    MKZ = "mkz"
    GQH = "gqh"
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
    DEEPSOIL_BAP_LIKE = "deepsoil_bap_like"


class OutputConfig(BaseModel):
    write_hdf5: bool = True
    write_sqlite: bool = True
    parquet_export: bool = False


class DarendeliCalibration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["darendeli"] = "darendeli"
    plasticity_index: float = Field(default=0.0, ge=0.0)
    ocr: PositiveFloat = 1.0
    mean_effective_stress_kpa: PositiveFloat
    frequency_hz: PositiveFloat = 1.0
    num_cycles: PositiveFloat = 10.0
    atmospheric_pressure_kpa: PositiveFloat = DEFAULT_ATMOSPHERIC_PRESSURE_KPA
    strain_min: PositiveFloat = 1.0e-6
    strain_max: PositiveFloat = 1.0e-1
    n_points: int = Field(default=60, ge=12, le=400)
    reload_factor: PositiveFloat | None = None

    @model_validator(mode="after")
    def validate_strain_range(self) -> DarendeliCalibration:
        if self.strain_max <= self.strain_min:
            raise ValueError("Darendeli calibration requires strain_max > strain_min.")
        return self


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
    solver_backend: Literal["opensees", "mock", "linear", "eql", "nonlinear"] = "opensees"
    nonlinear_substeps: int = Field(default=4, ge=1, le=128)
    pm4_validation_profile: Literal["basic", "strict", "strict_plus"] = "basic"
    damping_mode: Literal["frequency_independent", "rayleigh"] = "frequency_independent"
    rayleigh_mode_1_hz: PositiveFloat = 1.0
    rayleigh_mode_2_hz: PositiveFloat = 5.0
    rayleigh_update_matrix: bool = False
    timeout_s: int = 180
    retries: int = 1

    @model_validator(mode="after")
    def validate_rayleigh_modes(self) -> AnalysisControl:
        if self.rayleigh_mode_2_hz <= self.rayleigh_mode_1_hz:
            raise ValueError(
                "analysis.rayleigh_mode_2_hz must be greater than analysis.rayleigh_mode_1_hz."
            )
        return self


class Layer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    thickness_m: PositiveFloat
    unit_weight_kn_m3: PositiveFloat = Field(alias="unit_weight_kN_m3")
    vs_m_s: PositiveFloat
    material: MaterialType
    material_params: dict[str, float] = Field(default_factory=dict)
    material_optional_args: list[float] = Field(default_factory=list)
    calibration: DarendeliCalibration | None = None

    @model_validator(mode="after")
    def validate_material_params(self) -> Layer:
        allowed: set[str]
        effective_params = dict(self.material_params)
        if self.calibration is not None:
            if self.material not in {MaterialType.MKZ, MaterialType.GQH}:
                raise ValueError(
                    "Layer calibration is currently supported only for MKZ/GQH materials."
                )
            default_gmax = (
                (float(self.unit_weight_kn_m3) / 9.81)
                * float(self.vs_m_s)
                * float(self.vs_m_s)
            )
            gmax_seed = float(
                effective_params.get(
                    "gmax",
                    default_gmax,
                )
            )
            reload_factor_seed = (
                effective_params.get("reload_factor")
                or self.calibration.reload_factor
                or (2.0 if self.material == MaterialType.MKZ else 1.6)
            )
            if self.material == MaterialType.MKZ:
                calibrated = calibrate_mkz_from_darendeli(
                    gmax=gmax_seed,
                    plasticity_index=self.calibration.plasticity_index,
                    ocr=self.calibration.ocr,
                    mean_effective_stress_kpa=self.calibration.mean_effective_stress_kpa,
                    frequency_hz=self.calibration.frequency_hz,
                    num_cycles=self.calibration.num_cycles,
                    atmospheric_pressure_kpa=self.calibration.atmospheric_pressure_kpa,
                    strain_min=self.calibration.strain_min,
                    strain_max=self.calibration.strain_max,
                    n_points=self.calibration.n_points,
                    reload_factor=float(reload_factor_seed),
                )
            else:
                calibrated = calibrate_gqh_from_darendeli(
                    gmax=gmax_seed,
                    plasticity_index=self.calibration.plasticity_index,
                    ocr=self.calibration.ocr,
                    mean_effective_stress_kpa=self.calibration.mean_effective_stress_kpa,
                    frequency_hz=self.calibration.frequency_hz,
                    num_cycles=self.calibration.num_cycles,
                    atmospheric_pressure_kpa=self.calibration.atmospheric_pressure_kpa,
                    strain_min=self.calibration.strain_min,
                    strain_max=self.calibration.strain_max,
                    n_points=self.calibration.n_points,
                    reload_factor=float(reload_factor_seed),
                )
            effective_params = {**calibrated.material_params, **effective_params}
            self.material_params = effective_params

        if self.material == MaterialType.PM4SAND:
            allowed = {"Dr", "G0", "hpo"}
            dr = effective_params.get("Dr")
            if dr is not None and not (0.0 < dr <= 1.0):
                raise ValueError("PM4Sand parameter 'Dr' must be in (0, 1].")
            for key in ("G0", "hpo"):
                val = effective_params.get(key)
                if val is not None and val <= 0.0:
                    raise ValueError(f"PM4Sand parameter '{key}' must be > 0.")
        elif self.material == MaterialType.PM4SILT:
            allowed = {"Su", "Su_Rat", "G_o", "h_po"}
            su_rat = effective_params.get("Su_Rat")
            if su_rat is not None and not (0.0 < su_rat <= 1.0):
                raise ValueError("PM4Silt parameter 'Su_Rat' must be in (0, 1].")
            for key in ("Su", "G_o", "h_po"):
                val = effective_params.get(key)
                if val is not None and val <= 0.0:
                    raise ValueError(f"PM4Silt parameter '{key}' must be > 0.")
        elif self.material == MaterialType.MKZ:
            allowed = {
                "gmax",
                "gamma_ref",
                "tau_max",
                "damping_min",
                "damping_max",
                "reload_factor",
            }
            gmax = effective_params.get("gmax")
            gamma_ref = effective_params.get("gamma_ref")
            if gmax is None or gmax <= 0.0:
                raise ValueError("MKZ parameter 'gmax' is required and must be > 0.")
            if gamma_ref is None or gamma_ref <= 0.0:
                raise ValueError("MKZ parameter 'gamma_ref' is required and must be > 0.")
            tau_max = effective_params.get("tau_max")
            if tau_max is not None and tau_max <= 0.0:
                raise ValueError("MKZ parameter 'tau_max' must be > 0 when provided.")
            d_min = effective_params.get("damping_min")
            d_max = effective_params.get("damping_max")
            if d_min is not None and not (0.0 <= d_min <= 0.5):
                raise ValueError("MKZ parameter 'damping_min' must be in [0, 0.5].")
            if d_max is not None and not (0.0 <= d_max <= 0.5):
                raise ValueError("MKZ parameter 'damping_max' must be in [0, 0.5].")
            if d_min is not None and d_max is not None and d_min > d_max:
                raise ValueError("MKZ requires damping_min <= damping_max.")
            reload_factor_value = effective_params.get("reload_factor")
            if reload_factor_value is not None and reload_factor_value <= 0.0:
                raise ValueError("MKZ parameter 'reload_factor' must be > 0 when provided.")
        elif self.material == MaterialType.GQH:
            allowed = {
                "gmax",
                "gamma_ref",
                "a1",
                "a2",
                "m",
                "tau_max",
                "damping_min",
                "damping_max",
                "reload_factor",
            }
            gmax = effective_params.get("gmax")
            gamma_ref = effective_params.get("gamma_ref")
            if gmax is None or gmax <= 0.0:
                raise ValueError("GQH parameter 'gmax' is required and must be > 0.")
            if gamma_ref is None or gamma_ref <= 0.0:
                raise ValueError("GQH parameter 'gamma_ref' is required and must be > 0.")
            for key in ("a1", "a2", "m"):
                val = effective_params.get(key)
                if val is not None and val <= 0.0:
                    raise ValueError(f"GQH parameter '{key}' must be > 0 when provided.")
            tau_max = effective_params.get("tau_max")
            if tau_max is not None and tau_max <= 0.0:
                raise ValueError("GQH parameter 'tau_max' must be > 0 when provided.")
            d_min = effective_params.get("damping_min")
            d_max = effective_params.get("damping_max")
            if d_min is not None and not (0.0 <= d_min <= 0.5):
                raise ValueError("GQH parameter 'damping_min' must be in [0, 0.5].")
            if d_max is not None and not (0.0 <= d_max <= 0.5):
                raise ValueError("GQH parameter 'damping_max' must be in [0, 0.5].")
            if d_min is not None and d_max is not None and d_min > d_max:
                raise ValueError("GQH requires damping_min <= damping_max.")
            reload_factor_value = effective_params.get("reload_factor")
            if reload_factor_value is not None and reload_factor_value <= 0.0:
                raise ValueError("GQH parameter 'reload_factor' must be > 0 when provided.")
        else:
            allowed = {"nu"}
            nu = effective_params.get("nu")
            if nu is not None and not (0.0 < nu < 0.5):
                raise ValueError("Elastic parameter 'nu' must be in (0, 0.5).")

        unknown = set(effective_params) - allowed
        if unknown:
            raise ValueError(
                f"Unknown material_params for {self.material.value}: {sorted(unknown)}"
            )
        for key, value in effective_params.items():
            if not math.isfinite(value):
                raise ValueError(f"Material parameter '{key}' must be finite.")
        for idx, value in enumerate(self.material_optional_args):
            if not math.isfinite(value):
                raise ValueError(
                    f"material_optional_args[{idx}] for layer '{self.name}' must be finite."
                )
        return self


class SoilProfile(BaseModel):
    layers: list[Layer] = Field(min_length=1)


class OpenseesConfig(BaseModel):
    executable: str = "OpenSees"
    extra_args: list[str] = Field(default_factory=list)
    require_version_regex: str | None = None
    require_binary_sha256: str | None = None
    column_width_m: PositiveFloat = 1.0
    thickness_m: PositiveFloat = 1.0
    fluid_bulk_modulus: PositiveFloat = 2.2e6
    fluid_mass_density: PositiveFloat = 1.0
    h_perm: PositiveFloat = 1.0e-5
    v_perm: PositiveFloat = 1.0e-5
    gravity_steps: int = Field(default=20, ge=1)

    @model_validator(mode="after")
    def validate_fingerprint_requirements(self) -> OpenseesConfig:
        required_sha = (self.require_binary_sha256 or "").strip()
        if required_sha:
            if len(required_sha) != 64:
                raise ValueError("opensees.require_binary_sha256 must be 64 hex chars.")
            if any(ch not in "0123456789abcdefABCDEF" for ch in required_sha):
                raise ValueError("opensees.require_binary_sha256 must be hex encoded.")
            self.require_binary_sha256 = required_sha.lower()
        regex = (self.require_version_regex or "").strip()
        self.require_version_regex = regex or None
        return self


class ProjectConfig(BaseModel):
    project_name: str = "StrataWave-project"
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

        unsupported_materials = {MaterialType.MKZ, MaterialType.GQH}
        unsupported_layers = [
            layer.name
            for layer in self.profile.layers
            if layer.material in unsupported_materials
        ]
        if unsupported_layers:
            raise ValueError(
                "OpenSees backend currently supports pm4sand/pm4silt/elastic in this v1 pipeline. "
                f"Unsupported layers for opensees: {unsupported_layers}"
            )

        required_by_material: dict[MaterialType, set[str]] = {
            MaterialType.PM4SAND: {"Dr", "G0", "hpo"},
            MaterialType.PM4SILT: {"Su", "Su_Rat", "G_o", "h_po"},
        }
        strict_ranges: dict[MaterialType, dict[str, tuple[float, float]]] = {
            MaterialType.PM4SAND: {
                "Dr": (0.0, 1.0),
                "G0": (50.0, 3000.0),
                "hpo": (0.01, 5.0),
            },
            MaterialType.PM4SILT: {
                "Su": (1.0e-6, 1000.0),
                "Su_Rat": (0.0, 1.0),
                "G_o": (50.0, 3000.0),
                "h_po": (0.01, 5.0),
            },
        }
        is_strict = self.analysis.pm4_validation_profile in {"strict", "strict_plus"}
        is_strict_plus = self.analysis.pm4_validation_profile == "strict_plus"

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
            if is_strict:
                bounds = strict_ranges[layer.material]
                for key, (lo, hi) in bounds.items():
                    val = layer.material_params[key]
                    if not (lo < val <= hi):
                        raise ValueError(
                            f"Layer '{layer.name}' "
                            f"({layer.material.value}) strict validation failed: "
                            f"{key}={val} is outside ({lo}, {hi}]."
                        )

        if is_strict_plus:
            pm4_materials = {MaterialType.PM4SAND, MaterialType.PM4SILT}
            non_pm4_layers = [
                layer.name
                for layer in self.profile.layers
                if layer.material not in pm4_materials
            ]
            if non_pm4_layers:
                raise ValueError(
                    "strict_plus currently supports PM4-only layer stacks "
                    f"(pm4sand/pm4silt). Non-PM4 layers: {non_pm4_layers}"
                )
            if self.boundary_condition != BoundaryCondition.ELASTIC_HALFSPACE:
                raise ValueError(
                    "strict_plus requires boundary_condition=elastic_halfspace "
                    "for PM4 effective-stress workflows."
                )

            total_depth = sum(layer.thickness_m for layer in self.profile.layers)
            if not (5.0 <= total_depth <= 200.0):
                raise ValueError(
                    "strict_plus profile depth check failed: "
                    f"total depth {total_depth} m is outside [5, 200]."
                )

            if not (0.2 <= self.opensees.column_width_m <= 10.0):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    f"column_width_m={self.opensees.column_width_m} outside [0.2, 10]."
                )
            if not (0.2 <= self.opensees.thickness_m <= 10.0):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    f"thickness_m={self.opensees.thickness_m} outside [0.2, 10]."
                )
            if not (1.0e5 <= self.opensees.fluid_bulk_modulus <= 1.0e8):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    "fluid_bulk_modulus outside [1e5, 1e8]."
                )
            if not (0.5 <= self.opensees.fluid_mass_density <= 2.0):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    "fluid_mass_density outside [0.5, 2.0]."
                )
            if not (1.0e-8 <= self.opensees.h_perm <= 1.0e-2):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    "h_perm outside [1e-8, 1e-2]."
                )
            if not (1.0e-8 <= self.opensees.v_perm <= 1.0e-2):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    "v_perm outside [1e-8, 1e-2]."
                )
            perm_ratio = self.opensees.h_perm / self.opensees.v_perm
            if not (1.0e-2 <= perm_ratio <= 1.0e2):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    f"h_perm/v_perm={perm_ratio} outside [1e-2, 1e2]."
                )
            if not (10 <= self.opensees.gravity_steps <= 2000):
                raise ValueError(
                    "strict_plus OpenSees check failed: "
                    "gravity_steps outside [10, 2000]."
                )

            for layer in self.profile.layers:
                if layer.material not in {MaterialType.PM4SAND, MaterialType.PM4SILT}:
                    continue
                if not (10.0 <= layer.unit_weight_kn_m3 <= 25.0):
                    raise ValueError(
                        f"strict_plus layer check failed for '{layer.name}': "
                        f"unit_weight_kN_m3={layer.unit_weight_kn_m3} outside [10, 25]."
                    )
                if not (30.0 <= layer.vs_m_s <= 800.0):
                    raise ValueError(
                        f"strict_plus layer check failed for '{layer.name}': "
                        f"vs_m_s={layer.vs_m_s} outside [30, 800]."
                    )
                if len(layer.material_optional_args) > 30:
                    raise ValueError(
                        f"strict_plus layer check failed for '{layer.name}': "
                        "material_optional_args length exceeds 30."
                    )
        return self

