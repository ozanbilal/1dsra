/**
 * GeoWave v2 — Utility helpers
 */

/** Format a number with fixed decimals, return "—" for null/NaN. */
export function fmt(val, decimals = 3) {
  if (val == null || !isFinite(val)) return "—";
  return Number(val).toFixed(decimals);
}

/** Format number in engineering notation (e.g. 1.23e+04). */
export function fmtEng(val, decimals = 3) {
  if (val == null || !isFinite(val)) return "—";
  return Number(val).toExponential(decimals);
}

/** Clamp a value between min and max. */
export function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

/** Generate logarithmically spaced array. */
export function logspace(start, end, n) {
  const logStart = Math.log10(start);
  const logEnd = Math.log10(end);
  const step = (logEnd - logStart) / (n - 1);
  return Array.from({ length: n }, (_, i) => Math.pow(10, logStart + i * step));
}

/** Deep clone a plain object/array. */
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/** Compute Gmax from Vs and unit_weight. */
export function computeGmax(vs, unitWeight) {
  const rho = unitWeight / 9.81;
  return rho * vs * vs;
}

/** Standard engineering periods for PSA tables. */
export const STANDARD_PERIODS = [
  0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3,
  0.4, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0,
];

/** Material type options. */
export const MATERIAL_TYPES = [
  { value: "mkz", label: "MKZ (Modified Kondner-Zelasko)" },
  { value: "gqh", label: "GQH (Generalized Quadratic-Hyperbolic)" },
  { value: "elastic", label: "Elastic" },
];

export const MOTION_UNIT_OPTIONS = [
  { value: "m/s2", label: "m/s²" },
  { value: "g", label: "g" },
  { value: "cm/s2", label: "cm/s²" },
  { value: "gal", label: "gal" },
];

export const MOTION_FORMAT_OPTIONS = [
  { value: "auto", label: "Auto Detect" },
  { value: "time_acc", label: "Time + Acc Columns" },
  { value: "single", label: "Single Column" },
  { value: "numeric_stream", label: "Numeric Stream" },
];

export const MOTION_DELIMITER_OPTIONS = [
  { value: "auto", label: "Auto Detect" },
  { value: "comma", label: "Comma (,)" },
  { value: "semicolon", label: "Semicolon (;)" },
  { value: "tab", label: "Tab" },
  { value: "space", label: "Whitespace" },
];

export const MOTION_PROCESSING_ORDER_OPTIONS = [
  { value: "filter_first", label: "Filter Then Baseline" },
  { value: "baseline_first", label: "Baseline Then Filter" },
];

export const MOTION_BASELINE_METHOD_OPTIONS = [
  { value: "poly4", label: "Polynomial (deg 4)" },
  { value: "remove_mean", label: "Remove Mean" },
  { value: "linear", label: "Linear Detrend" },
  { value: "quadratic", label: "Quadratic Detrend" },
  { value: "cubic", label: "Cubic Detrend" },
  { value: "deepsoil_bap_like", label: "DEEPSOIL BAP-Like" },
];

export const MOTION_FILTER_DOMAIN_OPTIONS = [
  { value: "time", label: "Time Domain" },
  { value: "frequency", label: "Frequency Domain" },
];

export const MOTION_FILTER_CONFIG_OPTIONS = [
  { value: "bandpass", label: "Bandpass" },
  { value: "lowpass", label: "Lowpass" },
  { value: "highpass", label: "Highpass" },
  { value: "bandstop", label: "Bandstop" },
];

export const MOTION_FILTER_TYPE_OPTIONS = [
  { value: "butter", label: "Butterworth" },
  { value: "cheby", label: "Chebyshev" },
  { value: "bessel", label: "Bessel" },
];

export const MOTION_WINDOW_TYPE_OPTIONS = [
  { value: "hanning", label: "Hanning" },
  { value: "hamming", label: "Hamming" },
  { value: "cosine", label: "Cosine" },
  { value: "tukey", label: "Tukey" },
];

export const MOTION_WINDOW_APPLY_OPTIONS = [
  { value: "both", label: "Start + End" },
  { value: "start", label: "Start Only" },
  { value: "end", label: "End Only" },
];

export const MOTION_PADDING_METHOD_OPTIONS = [
  { value: "zeros", label: "Zeros" },
  { value: "linear", label: "Linear Decay" },
  { value: "exponential", label: "Exponential Decay" },
];

/** Reference curve options. */
export const REFERENCE_CURVES = [
  {
    value: "seed_idriss_upper",
    label: "Seed & Idriss Upper (1970)",
    group: "sand",
    needsPI: false,
  },
  {
    value: "seed_idriss_mean",
    label: "Seed & Idriss Mean (1970)",
    group: "sand",
    needsPI: false,
  },
  {
    value: "darendeli",
    label: "Darendeli (2001)",
    group: "clay",
    needsPI: true,
    needsOCR: true,
    needsStress: true,
  },
  {
    value: "vucetic_dobry",
    label: "Vucetic-Dobry (1991)",
    group: "clay",
    needsPI: true,
  },
];

/** Solver backend options. */
export const SOLVER_BACKENDS = [
  { value: "linear", label: "Linear", desc: "Elastic 1D SH response" },
  { value: "eql", label: "Equivalent-Linear", desc: "Iterative strain-compatible" },
  { value: "nonlinear", label: "Nonlinear", desc: "Time-domain implicit Newmark" },
];

export function getSolutionTypeLabel(solverBackend) {
  switch ((solverBackend || "").toLowerCase()) {
    case "nonlinear":
      return "Time-domain implicit Newmark";
    case "linear":
      return "Frequency-domain linear elastic";
    case "eql":
    default:
      return "Frequency-domain iterative equivalent-linear";
  }
}

export function supportsCurveFitting(materialType) {
  return materialType === "mkz" || materialType === "gqh";
}

export function supportsReductionFormulation(materialType) {
  return materialType === "mkz" || materialType === "gqh";
}

export function referenceCurveGroup(curveType) {
  return REFERENCE_CURVES.find(curve => curve.value === curveType)?.group || "sand";
}

export function referenceCurvesForGroup(group) {
  return REFERENCE_CURVES.filter(curve => curve.group === group);
}

function finiteOrDefault(value, fallback) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback;
}

function positiveOrDefault(value, fallback) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : fallback;
}

function inRangeOrDefault(value, fallback, lo, hi) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric >= lo && numeric <= hi ? numeric : fallback;
}

export function defaultMaterialParams(materialType, overrides = {}) {
  const gmax = positiveOrDefault(overrides.gmax, 1.0);
  const common = {
    damping_min: inRangeOrDefault(overrides.damping_min, 0.01, 0.0, 0.5),
    damping_max: inRangeOrDefault(overrides.damping_max, 0.15, 0.0, 0.5),
    reload_factor: positiveOrDefault(
      overrides.reload_factor,
      materialType === "gqh" ? 1.6 : 2.0,
    ),
  };

  if (materialType === "elastic") {
    return {
      nu: inRangeOrDefault(overrides.nu, 0.3, 0.01, 0.49),
    };
  }

  if (materialType === "gqh") {
    return {
      gmax,
      gamma_ref: positiveOrDefault(overrides.gamma_ref, 0.001),
      a1: positiveOrDefault(overrides.a1, 1.0),
      a2: inRangeOrDefault(overrides.a2, 0.0, 0.0, Number.POSITIVE_INFINITY),
      m: positiveOrDefault(overrides.m, 1.0),
      damping_min: common.damping_min,
      damping_max: Math.max(common.damping_min, inRangeOrDefault(overrides.damping_max, 0.18, 0.0, 0.5)),
      reload_factor: common.reload_factor,
      g_reduction_min: inRangeOrDefault(overrides.g_reduction_min, 0.0, 0.0, 0.99),
      mrdf_p1: finiteOrDefault(overrides.mrdf_p1, 0.82),
      mrdf_p2: finiteOrDefault(overrides.mrdf_p2, 0.55),
      mrdf_p3: finiteOrDefault(overrides.mrdf_p3, 20.0),
    };
  }

  return {
    gmax,
    gamma_ref: positiveOrDefault(overrides.gamma_ref, 0.035),
    damping_min: common.damping_min,
    damping_max: Math.max(common.damping_min, inRangeOrDefault(overrides.damping_max, 0.15, 0.0, 0.5)),
    reload_factor: common.reload_factor,
    g_reduction_min: inRangeOrDefault(overrides.g_reduction_min, 0.0, 0.0, 0.99),
    mrdf_p1: finiteOrDefault(overrides.mrdf_p1, 1.0),
    mrdf_p2: finiteOrDefault(overrides.mrdf_p2, 0.0),
    mrdf_p3: finiteOrDefault(overrides.mrdf_p3, 0.0),
    ...(positiveOrDefault(overrides.tau_max, 0) > 0 ? { tau_max: Number(overrides.tau_max) } : {}),
  };
}

export function normalizeMaterialParams(materialType, materialParams = {}, vs = 150, unitWeight = 18) {
  const source = materialParams || {};
  if (materialType === "elastic") {
    return {
      nu: inRangeOrDefault(source.nu, 0.3, 0.01, 0.49),
    };
  }

  const gmax = positiveOrDefault(source.gmax, computeGmax(vs, unitWeight));
  const base = defaultMaterialParams(materialType, { ...source, gmax });

  if (materialType === "mkz") {
    return {
      ...base,
      ...(positiveOrDefault(source.tau_max, 0) > 0 ? { tau_max: Number(source.tau_max) } : {}),
    };
  }

  const thetaKeys = ["theta1", "theta2", "theta3", "theta4", "theta5"];
  const hasStrengthFamily = positiveOrDefault(source.tau_max, 0) > 0
    && thetaKeys.every(key => Number.isFinite(Number(source[key])));

  if (hasStrengthFamily) {
    const cleaned = {
      gmax,
      tau_max: Number(source.tau_max),
      theta1: Number(source.theta1),
      theta2: Number(source.theta2),
      theta3: positiveOrDefault(source.theta3, 0.25),
      theta4: positiveOrDefault(source.theta4, 1.0),
      theta5: positiveOrDefault(source.theta5, 1.0),
      damping_min: inRangeOrDefault(source.damping_min, base.damping_min, 0.0, 0.5),
      damping_max: Math.max(
        inRangeOrDefault(source.damping_min, base.damping_min, 0.0, 0.5),
        inRangeOrDefault(source.damping_max, base.damping_max, 0.0, 0.5),
      ),
      reload_factor: positiveOrDefault(source.reload_factor, base.reload_factor),
      g_reduction_min: inRangeOrDefault(source.g_reduction_min, base.g_reduction_min, 0.0, 0.99),
      mrdf_p1: finiteOrDefault(source.mrdf_p1, base.mrdf_p1),
      mrdf_p2: finiteOrDefault(source.mrdf_p2, base.mrdf_p2),
      mrdf_p3: finiteOrDefault(source.mrdf_p3, base.mrdf_p3),
    };
    if (positiveOrDefault(source.gamma_ref, 0) > 0) cleaned.gamma_ref = Number(source.gamma_ref);
    return cleaned;
  }

  return {
    ...base,
    ...(positiveOrDefault(source.tau_max, 0) > 0 ? { tau_max: Number(source.tau_max) } : {}),
  };
}

/** Default layer template for new layers. */
export function defaultLayer(index = 0, materialType = "gqh") {
  const thickness = 5.0;
  const vs = 150 + index * 50;
  const unit_weight = 17.0 + index * 0.5;
  return {
    name: `Layer ${index + 1}`,
    thickness,
    vs,
    unit_weight,
    material: materialType,
    reference_curve: null,
    fit_stale: false,
    material_params: normalizeMaterialParams(materialType, {}, vs, unit_weight),
  };
}

export function defaultMotionProcessingState() {
  return {
    motion_proc_processing_order: "filter_first",
    motion_proc_baseline_on: false,
    motion_proc_baseline_method: "poly4",
    motion_proc_baseline_degree: 4,
    motion_proc_filter_on: false,
    motion_proc_filter_domain: "time",
    motion_proc_filter_config: "bandpass",
    motion_proc_filter_type: "butter",
    motion_proc_f_low: 0.1,
    motion_proc_f_high: 25.0,
    motion_proc_filter_order: 4,
    motion_proc_acausal: true,
    motion_proc_window_on: false,
    motion_proc_window_type: "hanning",
    motion_proc_window_param: 0.1,
    motion_proc_window_duration: null,
    motion_proc_window_apply_to: "both",
    motion_proc_trim_start: 0.0,
    motion_proc_trim_end: 0.0,
    motion_proc_trim_taper: false,
    motion_proc_pad_front: 0.0,
    motion_proc_pad_end: 0.0,
    motion_proc_pad_method: "zeros",
    motion_proc_pad_method_front: null,
    motion_proc_pad_method_end: null,
    motion_proc_pad_smooth: false,
    motion_proc_residual_fix: false,
    motion_proc_spectrum_damping_ratio: 0.05,
    motion_proc_show_uncorrected_preview: true,
  };
}

function finitePositiveOrNull(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null;
}

function finiteNonNegative(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : fallback;
}

export function motionValueFromG(valueInG, units = "m/s2") {
  const numeric = Number(valueInG);
  if (!Number.isFinite(numeric)) return null;
  const unit = String(units || "m/s2").trim().toLowerCase();
  if (unit === "g") return numeric;
  if (unit === "cm/s2" || unit === "cm/s^2" || unit === "gal") return numeric * 981.0;
  return numeric * 9.81;
}

function toApiScaleMode(scaleMode) {
  if (scaleMode === "scale_factor") return "scale_by";
  return scaleMode || "none";
}

export function buildMotionProcessingPayload(wizard = {}) {
  const defaults = defaultMotionProcessingState();
  const payload = {
    processing_order: wizard.motion_proc_processing_order || defaults.motion_proc_processing_order,
    baseline_on: wizard.motion_proc_baseline_on === true,
    baseline_method: wizard.motion_proc_baseline_method || defaults.motion_proc_baseline_method,
    baseline_degree: Math.max(0, Math.round(Number(wizard.motion_proc_baseline_degree ?? defaults.motion_proc_baseline_degree) || defaults.motion_proc_baseline_degree)),
    filter_on: wizard.motion_proc_filter_on === true,
    filter_domain: wizard.motion_proc_filter_domain || defaults.motion_proc_filter_domain,
    filter_config: wizard.motion_proc_filter_config || defaults.motion_proc_filter_config,
    filter_type: wizard.motion_proc_filter_type || defaults.motion_proc_filter_type,
    f_low: finiteNonNegative(wizard.motion_proc_f_low, defaults.motion_proc_f_low),
    f_high: finiteNonNegative(wizard.motion_proc_f_high, defaults.motion_proc_f_high),
    filter_order: Math.max(1, Math.round(Number(wizard.motion_proc_filter_order ?? defaults.motion_proc_filter_order) || defaults.motion_proc_filter_order)),
    acausal: wizard.motion_proc_acausal !== false,
    window_on: wizard.motion_proc_window_on === true,
    window_type: wizard.motion_proc_window_type || defaults.motion_proc_window_type,
    window_param: finiteNonNegative(wizard.motion_proc_window_param, defaults.motion_proc_window_param),
    window_duration: finitePositiveOrNull(wizard.motion_proc_window_duration),
    window_apply_to: wizard.motion_proc_window_apply_to || defaults.motion_proc_window_apply_to,
    trim_start: finiteNonNegative(wizard.motion_proc_trim_start, defaults.motion_proc_trim_start),
    trim_end: finiteNonNegative(wizard.motion_proc_trim_end, defaults.motion_proc_trim_end),
    trim_taper: wizard.motion_proc_trim_taper === true,
    pad_front: finiteNonNegative(wizard.motion_proc_pad_front, defaults.motion_proc_pad_front),
    pad_end: finiteNonNegative(wizard.motion_proc_pad_end, defaults.motion_proc_pad_end),
    pad_method: wizard.motion_proc_pad_method || defaults.motion_proc_pad_method,
    pad_method_front: wizard.motion_proc_pad_method_front || null,
    pad_method_end: wizard.motion_proc_pad_method_end || null,
    pad_smooth: wizard.motion_proc_pad_smooth === true,
    residual_fix: wizard.motion_proc_residual_fix === true,
    spectrum_damping_ratio: finitePositiveOrNull(wizard.motion_proc_spectrum_damping_ratio) ?? defaults.motion_proc_spectrum_damping_ratio,
    show_uncorrected_preview: wizard.motion_proc_show_uncorrected_preview !== false,
  };

  const differs = Object.entries(defaults).some(([key, defaultValue]) => {
    const payloadKey = key.replace(/^motion_proc_/, "");
    return payload[payloadKey] !== defaultValue;
  });
  return differs ? payload : null;
}

export function buildMotionStepPayload(wizard = {}) {
  return {
    units: wizard.motion_units || "m/s2",
    input_type: wizard.motion_input_type || "within",
    baseline: "none",
    scale_mode: toApiScaleMode(wizard.scale_mode),
    scale_factor: wizard.scale_mode === "scale_factor" ? finitePositiveOrNull(wizard.scale_factor) : null,
    target_pga: wizard.scale_mode === "scale_to_pga"
      ? motionValueFromG(wizard.target_pga_g, wizard.motion_units || "m/s2")
      : null,
    motion_path: wizard.motion_path || "",
    processing: buildMotionProcessingPayload(wizard),
  };
}

export function buildMotionParseSettings(wizard = {}) {
  const formatHint = String(wizard.motion_format_hint || "auto");
  const delimiter = String(wizard.motion_delimiter || "auto");
  const skipRows = Number(wizard.motion_skip_rows);
  const timeCol = Number(wizard.motion_time_col);
  const accCol = Number(wizard.motion_acc_col);
  const dtOverride = Number(wizard.motion_dt_override);
  const hasTime = wizard.motion_has_time !== false;
  return {
    units_hint: wizard.motion_units || "m/s2",
    format_hint: formatHint,
    delimiter,
    skip_rows: Number.isFinite(skipRows) && skipRows >= 0 ? Math.round(skipRows) : 0,
    time_col: Number.isFinite(timeCol) && timeCol >= 0 ? Math.round(timeCol) : 0,
    acc_col: Number.isFinite(accCol) && accCol >= 0 ? Math.round(accCol) : 1,
    has_time: hasTime,
    dt_override: Number.isFinite(dtOverride) && dtOverride > 0 ? dtOverride : null,
    scale_mode: toApiScaleMode(wizard.scale_mode),
    scale_factor: wizard.scale_mode === "scale_factor" ? finitePositiveOrNull(wizard.scale_factor) : null,
    target_pga: wizard.scale_mode === "scale_to_pga"
      ? motionValueFromG(wizard.target_pga_g, wizard.motion_units || "m/s2")
      : null,
    ...(buildMotionProcessingPayload(wizard) || defaultMotionProcessingStateToApi()),
  };
}

function defaultMotionProcessingStateToApi() {
  const defaults = defaultMotionProcessingState();
  return Object.fromEntries(
    Object.entries(defaults).map(([key, value]) => [key.replace(/^motion_proc_/, ""), value]),
  );
}

/** Validate the wizard state before running analysis.
 * Returns { valid: boolean, errors: string[], warnings: string[] }
 */
export function validateWizard(w) {
  const errors = [];
  const warnings = [];

  // Layers
  if (!w.layers || w.layers.length === 0) {
    errors.push("At least one soil layer is required.");
  } else {
    w.layers.forEach((l, i) => {
      const label = l.name || `Layer ${i + 1}`;
      const thick = l.thickness_m || l.thickness || 0;
      const vs = l.vs_m_s || l.vs || 0;
      const uw = l.unit_weight_kN_m3 || l.unit_weight || 0;
      if (thick <= 0) errors.push(`${label}: thickness must be > 0`);
      if (vs <= 0) errors.push(`${label}: Vs must be > 0`);
      else if (vs < 10) warnings.push(`${label}: Vs = ${vs} m/s is very low`);
      else if (vs > 5000) warnings.push(`${label}: Vs = ${vs} m/s is unusually high`);
      if (uw <= 0) errors.push(`${label}: unit weight must be > 0`);
    });
  }
  if (w.water_table_depth_m != null) {
    const wt = Number(w.water_table_depth_m);
    if (!Number.isFinite(wt) || wt < 0) {
      errors.push("Water table depth must be >= 0.");
    }
  }
  if (w.bedrock != null) {
    const bedrockVs = Number(w.bedrock.vs_m_s);
    const bedrockUw = Number(w.bedrock.unit_weight_kN_m3);
    if (!Number.isFinite(bedrockVs) || bedrockVs <= 0) {
      errors.push("Bedrock Vs must be > 0 when explicit halfspace properties are set.");
    }
    if (!Number.isFinite(bedrockUw) || bedrockUw <= 0) {
      errors.push("Bedrock unit weight must be > 0 when explicit halfspace properties are set.");
    }
  }

  // Motion
  if (!w.motion_path) {
    errors.push("No input motion selected.");
  }

  // Analysis control
  const dt = w.dt || 0.005;
  const fmax = w.f_max || 25;
  if (dt <= 0) errors.push("Time step dt must be > 0");
  if (fmax <= 0) errors.push("Max frequency must be > 0");
  if (dt > 1.0 / (20 * fmax)) {
    warnings.push(`dt = ${dt}s may be too large for f_max = ${fmax} Hz (Nyquist: dt < ${(1.0 / (20 * fmax)).toFixed(4)}s)`);
  }

  // Scale factor
  if (w.scale_mode === "scale_factor" && (w.scale_factor == null || w.scale_factor <= 0)) {
    errors.push("Scale factor must be > 0");
  }
  if (w.scale_mode === "scale_to_pga" && (!w.target_pga_g || w.target_pga_g <= 0)) {
    errors.push("Target PGA must be > 0");
  }

  if (w.batch_motions && w.batch_motions.length > 1) {
    const workers = Number(w.parallel_workers || 1);
    if (!Number.isFinite(workers) || workers < 1) {
      errors.push("Parallel workers must be at least 1 for batch analysis.");
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}

/** Parameter help descriptions for tooltip display. */
export const PARAM_HELP = {
  solver_backend: "Linear: elastic frequency-domain. EQL: iterative strain-compatible. Nonlinear: time-domain Newmark-beta with MKZ/GQH backbone.",
  boundary_condition: "Rigid: fixed base (no radiation damping). Elastic Halfspace: allows energy radiation into underlying rock.",
  bedrock_vs: "Explicit halfspace Vs used only for Elastic Halfspace runs. Leave unset to reuse the last soil layer as the halfspace seed.",
  bedrock_unit_weight: "Explicit halfspace unit weight used only for Elastic Halfspace runs. Leave unset to reuse the last soil layer values.",
  motion_units: "Declared acceleration unit for the selected raw motion files. Preview, import tools and run-ready normalization use this assumption.",
  motion_library_dirs: "One folder per line. GeoWave scans only these folders, and only the motion files directly inside each folder.",
  motion_format_hint: "Auto Detect uses lightweight heuristics. Use Time + Acc Columns, Single Column or Numeric Stream when the file structure is known.",
  motion_delimiter: "Column separator for generic text motions. Auto Detect checks comma, semicolon, tab and whitespace.",
  motion_skip_rows: "Header rows to skip before parsing numeric motion data.",
  motion_time_col: "Zero-based time column index used when the file stores time and acceleration together.",
  motion_acc_col: "Zero-based acceleration column index used for generic text files.",
  motion_dt_override: "Optional manual dt used for single-column or numeric-stream files when no time axis exists.",
  motion_proc_processing_order: "Choose whether GeoWave filters before baseline correction or reverses the order for APP_GMPS-style preprocessing.",
  motion_proc_baseline_method: "Baseline correction method applied when Advanced Processing baseline correction is enabled.",
  motion_proc_filter_config: "Bandpass/lowpass/highpass/bandstop definition for the advanced motion filter.",
  motion_proc_window_duration: "Window duration in seconds. Start/end/both is controlled separately in the advanced panel.",
  motion_proc_trim_start: "Trim the record start in seconds before filtering and integration.",
  motion_proc_trim_end: "Trim the record end in seconds before filtering and integration.",
  motion_proc_pad_front: "Pad zeros or decayed tails in front of the record after processing.",
  motion_proc_pad_end: "Pad zeros or decayed tails at the end of the record after processing.",
  motion_proc_spectrum_damping_ratio: "Damping ratio used when building SA/SV/SD preview spectra.",
  dt: "Analysis time step. Should satisfy dt < 1/(20·f_max) for numerical stability.",
  f_max: "Maximum frequency resolved in the analysis. Controls sublayer thickness and dt requirements.",
  thickness: "Layer thickness in meters. Auto-sublayering can split thick layers for better accuracy.",
  vs: "Shear wave velocity (m/s). Determines layer stiffness: G_max = ρ·Vs².",
  unit_weight: "Unit weight (kN/m³). Used to compute mass density ρ = γ/g and overburden stress.",
  material: "MKZ: Modified Kondner-Zelasko. GQH: Generalized Quadratic Hyperbolic. Elastic: no nonlinearity.",
  gamma_ref: "Reference strain at which G/Gmax = 0.5 (for MKZ) or the transition strain (for GQH).",
  damping_min: "Small-strain damping ratio. Applied as baseline viscous damping.",
  strain_ratio: "Effective/max strain ratio for EQL (typically 0.65 per Idriss & Sun 1992).",
  convergence_tol: "EQL convergence tolerance. Iterations stop when max Vs change < this value.",
  max_iterations: "Maximum EQL iterations before declaring non-convergence.",
  scale_mode: "None: use as-is. Scale Factor: multiply all accelerations. Scale to PGA: adjust to target peak.",
  damping_mode: "Frequency-independent: constant damping. Rayleigh: frequency-dependent (2 target frequencies).",
};

/** Boundary condition options. */
export const BOUNDARY_CONDITIONS = [
  { value: "rigid", label: "Rigid Base" },
  { value: "elastic_halfspace", label: "Elastic Halfspace" },
];

/** Result tab definitions. */
export const RESULT_TABS = [
  { id: "time", label: "Time Histories" },
  { id: "stress_strain", label: "Stress-Strain" },
  { id: "spectral", label: "Spectral" },
  { id: "spectra_summary", label: "Spectra Summary" },
  { id: "displacement_animation", label: "Displacement Animation" },
  { id: "profile", label: "Profile" },
  { id: "mobilized", label: "Mobilized Strength" },
  { id: "convergence", label: "Convergence" },
];
