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

    class FitLimits(BaseModel):
        model_config = ConfigDict(extra="forbid")

        mr_min_strain: PositiveFloat | None = None
        mr_max_strain: PositiveFloat | None = None
        damping_min_strain: PositiveFloat | None = None
        damping_max_strain: PositiveFloat | None = None
        min_strength_pct: float | None = Field(default=None, gt=0.0, le=100.0)
        fix_theta3: PositiveFloat | None = None

        @model_validator(mode="after")
        def validate_ranges(self) -> DarendeliCalibration.FitLimits:
            if (
                self.mr_min_strain is not None
                and self.mr_max_strain is not None
                and self.mr_max_strain <= self.mr_min_strain
            ):
                raise ValueError("fit_limits requires mr_max_strain > mr_min_strain.")
            if (
                self.damping_min_strain is not None
                and self.damping_max_strain is not None
                and self.damping_max_strain <= self.damping_min_strain
            ):
                raise ValueError(
                    "fit_limits requires damping_max_strain > damping_min_strain."
                )
            return self

    source: Literal["darendeli"] = "darendeli"
    plasticity_index: float = Field(default=0.0, ge=0.0)
    ocr: PositiveFloat = 1.0
    mean_effective_stress_kpa: PositiveFloat | None = None
    k0: float | None = Field(default=None, ge=0.0)
    frequency_hz: PositiveFloat = 1.0
    num_cycles: PositiveFloat = 10.0
    atmospheric_pressure_kpa: PositiveFloat = DEFAULT_ATMOSPHERIC_PRESSURE_KPA
    strain_min: PositiveFloat = 1.0e-6
    strain_max: PositiveFloat = 1.0e-1
    fit_strain_min: PositiveFloat = 1.0e-6
    fit_strain_max: PositiveFloat = 5.0e-4
    target_strength_kpa: PositiveFloat | None = None
    target_strength_ratio: PositiveFloat = 0.95
    target_strength_strain: PositiveFloat = 1.0e-1
    n_points: int = Field(default=60, ge=12, le=400)
    reload_factor: PositiveFloat | None = None
    fit_procedure: Literal["MR", "MRD", "DC"] = "MR"
    fit_limits: FitLimits | None = None
    auto_refit_on_reference_change: bool = True

    @model_validator(mode="after")
    def validate_strain_range(self) -> DarendeliCalibration:
        if self.strain_max <= self.strain_min:
            raise ValueError("Darendeli calibration requires strain_max > strain_min.")
        if self.fit_strain_max <= self.fit_strain_min:
            raise ValueError("Darendeli calibration requires fit_strain_max > fit_strain_min.")
        if self.target_strength_ratio > 1.0:
            raise ValueError("Darendeli calibration requires target_strength_ratio <= 1.0.")
        if self.mean_effective_stress_kpa is None and self.k0 is None:
            raise ValueError(
                "Darendeli calibration requires mean_effective_stress_kpa or k0."
            )
        return self


class MotionProcessingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processing_order: Literal["filter_first", "baseline_first"] = "filter_first"
    baseline_on: bool = False
    baseline_method: str = "poly4"
    baseline_degree: int = Field(default=4, ge=0, le=10)
    filter_on: bool = False
    filter_domain: Literal["time", "frequency"] = "time"
    filter_config: str = "bandpass"
    filter_type: Literal["butter", "cheby", "bessel"] = "butter"
    f_low: float = Field(default=0.1, ge=0.0)
    f_high: float = Field(default=25.0, ge=0.0)
    filter_order: int = Field(default=4, ge=1, le=16)
    acausal: bool = True
    window_on: bool = False
    window_type: str = "hanning"
    window_param: float = Field(default=0.1, ge=0.0)
    window_duration: PositiveFloat | None = None
    window_apply_to: Literal["start", "end", "both"] = "both"
    trim_start: float = Field(default=0.0, ge=0.0)
    trim_end: float = Field(default=0.0, ge=0.0)
    trim_taper: bool = False
    pad_front: float = Field(default=0.0, ge=0.0)
    pad_end: float = Field(default=0.0, ge=0.0)
    pad_method: str = "zeros"
    pad_method_front: str | None = None
    pad_method_end: str | None = None
    pad_smooth: bool = False
    residual_fix: bool = False
    spectrum_damping_ratio: float = Field(default=0.05, gt=0.0, lt=1.0)
    show_uncorrected_preview: bool = True

    @model_validator(mode="after")
    def validate_processing(self) -> MotionProcessingConfig:
        filter_config = str(self.filter_config or "bandpass").strip().lower()
        if filter_config not in {"bandpass", "band", "lowpass", "low", "highpass", "high", "bandstop", "stop"}:
            raise ValueError("motion.processing.filter_config must be one of bandpass/lowpass/highpass/bandstop.")
        if self.filter_on and filter_config in {"bandpass", "band", "bandstop", "stop"} and self.f_high <= self.f_low:
            raise ValueError("motion.processing requires f_high > f_low for band filters.")
        if self.window_on and self.window_duration is None:
            raise ValueError("motion.processing.window_duration is required when window_on=true.")
        return self


class MotionConfig(BaseModel):
    units: str = "m/s2"
    input_type: Literal["within", "outcrop"] = "outcrop"
    baseline: BaselineMode = BaselineMode.REMOVE_MEAN
    scale_mode: ScaleMode = ScaleMode.NONE
    scale_factor: float | None = None
    target_pga: float | None = None
    processing: MotionProcessingConfig | None = None

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
    solver_backend: Literal["linear", "eql", "nonlinear"] = "nonlinear"
    nonlinear_substeps: int = Field(default=4, ge=1, le=128)
    integration_scheme: Literal["newmark", "verlet", "euler"] = "newmark"
    damping_mode: Literal["frequency_independent", "rayleigh"] = "frequency_independent"
    damping_correction: Literal["auto", "floor_only", "mrdf_only", "combined"] = "auto"
    viscous_damping_update: bool = False
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
        if self.material in {MaterialType.PM4SAND, MaterialType.PM4SILT}:
            raise ValueError(
                "PM4Sand/PM4Silt configs are no longer supported in GeoWave core mode. "
                "Migrate this layer to MKZ/GQH/Elastic and use linear, eql, or nonlinear."
            )
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
            sigma_mean = self.calibration.mean_effective_stress_kpa
            if sigma_mean is None and self.calibration.k0 is None:
                raise ValueError(
                    "Darendeli calibration requires mean_effective_stress_kpa or k0."
                )
            if sigma_mean is not None:
                if self.material == MaterialType.MKZ:
                    calibrated = calibrate_mkz_from_darendeli(
                        gmax=gmax_seed,
                        plasticity_index=self.calibration.plasticity_index,
                        ocr=self.calibration.ocr,
                        mean_effective_stress_kpa=sigma_mean,
                        frequency_hz=self.calibration.frequency_hz,
                        num_cycles=self.calibration.num_cycles,
                        atmospheric_pressure_kpa=self.calibration.atmospheric_pressure_kpa,
                        strain_min=self.calibration.strain_min,
                        strain_max=self.calibration.strain_max,
                        n_points=self.calibration.n_points,
                        reload_factor=float(reload_factor_seed),
                    )
                else:
                    tau_target = self.calibration.target_strength_kpa
                    if tau_target is None:
                        tau_target = effective_params.get("tau_max")
                    calibrated = calibrate_gqh_from_darendeli(
                        gmax=gmax_seed,
                        plasticity_index=self.calibration.plasticity_index,
                        ocr=self.calibration.ocr,
                        mean_effective_stress_kpa=sigma_mean,
                        frequency_hz=self.calibration.frequency_hz,
                        num_cycles=self.calibration.num_cycles,
                        atmospheric_pressure_kpa=self.calibration.atmospheric_pressure_kpa,
                        strain_min=self.calibration.strain_min,
                        strain_max=self.calibration.strain_max,
                        n_points=self.calibration.n_points,
                        tau_target_kpa=tau_target,
                        fit_strain_min=self.calibration.fit_strain_min,
                        fit_strain_max=self.calibration.fit_strain_max,
                        target_strength_ratio=self.calibration.target_strength_ratio,
                        target_strength_strain=self.calibration.target_strength_strain,
                        reload_factor=float(reload_factor_seed),
                        fit_procedure=self.calibration.fit_procedure,
                        fit_limits=(
                            self.calibration.fit_limits.model_dump(exclude_none=True)
                            if self.calibration.fit_limits is not None
                            else None
                        ),
                    )
                effective_params = {**calibrated.material_params, **effective_params}
                self.material_params = effective_params
            else:
                effective_params.setdefault("gmax", gmax_seed)
                self.material_params = effective_params

        if self.material == MaterialType.MKZ:
            allowed = {
                "gmax",
                "gamma_ref",
                "tau_max",
                "damping_min",
                "damping_max",
                "reload_factor",
                "g_reduction_min",
                "mrdf_p1",
                "mrdf_p2",
                "mrdf_p3",
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
            g_red_min = effective_params.get("g_reduction_min")
            if g_red_min is not None and not (0.0 <= g_red_min < 1.0):
                raise ValueError("MKZ parameter 'g_reduction_min' must be in [0, 1).")
        elif self.material == MaterialType.GQH:
            allowed = {
                "gmax",
                "gamma_ref",
                "a1",
                "a2",
                "m",
                "tau_max",
                "theta1",
                "theta2",
                "theta3",
                "theta4",
                "theta5",
                "damping_min",
                "damping_max",
                "reload_factor",
                "g_reduction_min",
                "mrdf_p1",
                "mrdf_p2",
                "mrdf_p3",
            }
            gmax = effective_params.get("gmax")
            gamma_ref = effective_params.get("gamma_ref")
            if gmax is None or gmax <= 0.0:
                raise ValueError("GQH parameter 'gmax' is required and must be > 0.")

            tau_max = effective_params.get("tau_max")
            if tau_max is not None and tau_max <= 0.0:
                raise ValueError("GQH parameter 'tau_max' must be > 0 when provided.")
            theta_keys = ("theta1", "theta2", "theta3", "theta4", "theta5")
            has_any_theta = any(key in effective_params for key in theta_keys)
            has_all_theta = all(key in effective_params for key in theta_keys)
            has_strength_family = has_all_theta and (tau_max is not None)
            if has_any_theta and not has_strength_family:
                raise ValueError(
                    "GQH strength-controlled parameters require tau_max and theta1..theta5."
                )
            if not has_strength_family:
                if gamma_ref is None or gamma_ref <= 0.0:
                    raise ValueError(
                        "GQH legacy parameters require gamma_ref > 0 when theta1..theta5 are not provided."
                    )
                a1 = effective_params.get("a1")
                a2 = effective_params.get("a2")
                exponent = effective_params.get("m")
                if a1 is None or a1 <= 0.0:
                    raise ValueError("GQH legacy parameter 'a1' must be > 0.")
                if a2 is None or a2 < 0.0:
                    raise ValueError("GQH legacy parameter 'a2' must be >= 0.")
                if exponent is None or exponent <= 0.0:
                    raise ValueError("GQH legacy parameter 'm' must be > 0.")
            else:
                if gamma_ref is not None and gamma_ref <= 0.0:
                    raise ValueError("GQH parameter 'gamma_ref' must be > 0 when provided.")
                if effective_params["theta3"] <= 0.0:
                    raise ValueError("GQH parameter 'theta3' must be > 0.")
                if effective_params["theta4"] <= 0.0:
                    raise ValueError("GQH parameter 'theta4' must be > 0.")
                if effective_params["theta5"] <= 0.0:
                    raise ValueError("GQH parameter 'theta5' must be > 0.")
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
            g_red_min = effective_params.get("g_reduction_min")
            if g_red_min is not None and not (0.0 <= g_red_min < 1.0):
                raise ValueError("GQH parameter 'g_reduction_min' must be in [0, 1).")
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


class BedrockProperties(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = "Bedrock"
    vs_m_s: float = Field(gt=0.0)
    unit_weight_kn_m3: float = Field(gt=0.0, alias="unit_weight_kN_m3")


class SoilProfile(BaseModel):
    water_table_depth_m: float | None = Field(default=None, ge=0.0)
    bedrock: BedrockProperties | None = None
    layers: list[Layer] = Field(min_length=1)


class ProjectConfig(BaseModel):
    project_name: str = "GeoWave-project"
    seed: int = 42
    profile: SoilProfile
    boundary_condition: BoundaryCondition = BoundaryCondition.RIGID
    analysis: AnalysisControl = Field(default_factory=AnalysisControl)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

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

    def effective_bedrock(self) -> BedrockProperties:
        if self.profile.bedrock is not None:
            return self.profile.bedrock
        last_layer = self.profile.layers[-1]
        return BedrockProperties(
            name=f"{last_layer.name} halfspace",
            vs_m_s=float(last_layer.vs_m_s),
            unit_weight_kn_m3=float(last_layer.unit_weight_kn_m3),
        )

    @model_validator(mode="after")
    def apply_k0_based_calibration(self) -> ProjectConfig:
        from dsra1d.profile_diagnostics import (
            compute_layer_stress_states,
            mean_effective_stress_from_k0,
        )

        stress_states = compute_layer_stress_states(
            self.profile.layers,
            water_table_depth_m=self.profile.water_table_depth_m,
        )
        for layer, state in zip(self.profile.layers, stress_states, strict=False):
            calibration = layer.calibration
            if calibration is None:
                continue
            if calibration.mean_effective_stress_kpa is not None:
                continue
            if calibration.k0 is None:
                continue
            if layer.material not in {MaterialType.MKZ, MaterialType.GQH}:
                continue

            sigma_mean = mean_effective_stress_from_k0(
                state.sigma_v_eff_mid_kpa,
                calibration.k0,
            )
            default_gmax = (
                (float(layer.unit_weight_kn_m3) / 9.81)
                * float(layer.vs_m_s)
                * float(layer.vs_m_s)
            )
            effective_params = dict(layer.material_params)
            gmax_seed = float(effective_params.get("gmax", default_gmax))
            reload_factor_seed = (
                effective_params.get("reload_factor")
                or calibration.reload_factor
                or (2.0 if layer.material == MaterialType.MKZ else 1.6)
            )
            if layer.material == MaterialType.MKZ:
                calibrated = calibrate_mkz_from_darendeli(
                    gmax=gmax_seed,
                    plasticity_index=calibration.plasticity_index,
                    ocr=calibration.ocr,
                    mean_effective_stress_kpa=sigma_mean,
                    frequency_hz=calibration.frequency_hz,
                    num_cycles=calibration.num_cycles,
                    atmospheric_pressure_kpa=calibration.atmospheric_pressure_kpa,
                    strain_min=calibration.strain_min,
                    strain_max=calibration.strain_max,
                    n_points=calibration.n_points,
                    reload_factor=float(reload_factor_seed),
                )
            else:
                tau_target = calibration.target_strength_kpa
                if tau_target is None:
                    tau_target = effective_params.get("tau_max")
                calibrated = calibrate_gqh_from_darendeli(
                    gmax=gmax_seed,
                    plasticity_index=calibration.plasticity_index,
                    ocr=calibration.ocr,
                    mean_effective_stress_kpa=sigma_mean,
                    sigma_v_eff_mid_kpa=state.sigma_v_eff_mid_kpa,
                    k0=calibration.k0,
                    frequency_hz=calibration.frequency_hz,
                    num_cycles=calibration.num_cycles,
                    atmospheric_pressure_kpa=calibration.atmospheric_pressure_kpa,
                    strain_min=calibration.strain_min,
                    strain_max=calibration.strain_max,
                    n_points=calibration.n_points,
                    tau_target_kpa=tau_target,
                    fit_strain_min=calibration.fit_strain_min,
                    fit_strain_max=calibration.fit_strain_max,
                    target_strength_ratio=calibration.target_strength_ratio,
                    target_strength_strain=calibration.target_strength_strain,
                    reload_factor=float(reload_factor_seed),
                    fit_procedure=calibration.fit_procedure,
                    fit_limits=(
                        calibration.fit_limits.model_dump(exclude_none=True)
                        if calibration.fit_limits is not None
                        else None
                    ),
                )
            layer.material_params = {**calibrated.material_params, **effective_params}
            layer.calibration = calibration.model_copy(
                update={"mean_effective_stress_kpa": sigma_mean}
            )
        return self
