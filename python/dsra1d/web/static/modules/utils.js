/**
 * StrataWave v2 — Utility helpers
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

/** Default layer template for new layers. */
export function defaultLayer(index = 0) {
  return {
    thickness: 5.0,
    vs: 150 + index * 50,
    unit_weight: 17.0 + index * 0.5,
    material: "mkz",
    material_params: {
      gmax: 0,  // will be computed from vs & unit_weight
      gamma_ref: 0.035,
      damping_min: 0.01,
      damping_max: 0.15,
      reload_factor: 2.0,
      g_reduction_min: 0.0,
    },
  };
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

/** Reference curve options. */
export const REFERENCE_CURVES = [
  { value: "darendeli", label: "Darendeli (2001)", needsPI: true, needsOCR: true, needsStress: true },
  { value: "seed_idriss_upper", label: "Seed & Idriss Upper (1970)", needsPI: false },
  { value: "seed_idriss_mean", label: "Seed & Idriss Mean (1970)", needsPI: false },
  { value: "vucetic_dobry", label: "Vucetic-Dobry (1991)", needsPI: true },
];

/** Solver backend options. */
export const SOLVER_BACKENDS = [
  { value: "linear", label: "Linear", desc: "Elastic 1D SH response" },
  { value: "eql", label: "Equivalent-Linear", desc: "Iterative strain-compatible" },
  { value: "nonlinear", label: "Nonlinear", desc: "Time-domain implicit Newmark" },
];

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
  if (w.scale_mode === "factor" && (w.scale_factor == null || w.scale_factor <= 0)) {
    errors.push("Scale factor must be > 0");
  }
  if (w.scale_mode === "target_pga" && (!w.target_pga_g || w.target_pga_g <= 0)) {
    errors.push("Target PGA must be > 0");
  }

  return { valid: errors.length === 0, errors, warnings };
}

/** Parameter help descriptions for tooltip display. */
export const PARAM_HELP = {
  solver_backend: "Linear: elastic frequency-domain. EQL: iterative strain-compatible. Nonlinear: time-domain Newmark-beta with MKZ/GQH backbone.",
  boundary_condition: "Rigid: fixed base (no radiation damping). Elastic Halfspace: allows energy radiation into underlying rock.",
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
  { id: "profile", label: "Profile" },
  { id: "mobilized", label: "Mobilized Strength" },
  { id: "convergence", label: "Convergence" },
];
