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
