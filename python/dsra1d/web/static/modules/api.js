/**
 * GeoWave v2 — API client
 */
import { buildMotionStepPayload } from "./utils.js";

const BASE = "";

async function request(method, path, body = null) {
  const opts = { method, headers: {} };
  if (body != null) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(BASE + path, opts);
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`${resp.status}: ${text}`);
  }
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) return resp.json();
  return resp;
}

// ── Wizard & Config ──────────────────────────────────────

export function fetchWizardSchema() {
  return request("GET", "/api/wizard/schema");
}

export function generateConfig(w) {
  // Transform flat wizard state into step-based request the backend expects
  const layers = (w.layers || []).map(l => ({
    name: l.name || "Layer",
    thickness_m: l.thickness_m || l.thickness || 5.0,
    vs_m_s: l.vs_m_s || l.vs || 150.0,
    unit_weight_kN_m3: l.unit_weight_kN_m3 || l.unit_weight || 18.0,
    material: l.material || "mkz",
    reference_curve: l.reference_curve || null,
    fit_stale: !!l.fit_stale,
    material_params: l.material_params || {},
    calibration: l.calibration || undefined,
  }));

  const body = {
    analysis_step: {
      project_name: w.project_name || "wizard-project",
      boundary_condition: w.boundary_condition || "rigid",
      solver_backend: w.solver_backend || "nonlinear",
    },
    profile_step: {
      water_table_depth_m: w.water_table_depth_m ?? null,
      bedrock: w.bedrock || null,
      layers,
    },
    motion_step: buildMotionStepPayload(w),
    damping_step: {
      mode: w.damping_mode || "frequency_independent",
      update_matrix: false,
      mode_1: w.rayleigh_mode_1_hz || null,
      mode_2: w.rayleigh_mode_2_hz || null,
    },
    control_step: {
      dt: w.dt || 0.005,
      f_max: w.f_max || 25.0,
      timeout_s: w.timeout_s || 180,
      retries: w.retries ?? 1,
      output_dir: "out/web",
    },
  };
  return request("POST", "/api/config/from-wizard", body);
}

export function wizardSanityCheck(w) {
  // Same body structure as generateConfig but sent to sanity-check endpoint
  const layers = (w.layers || []).map(l => ({
    name: l.name || "Layer",
    thickness_m: l.thickness_m || l.thickness || 5.0,
    vs_m_s: l.vs_m_s || l.vs || 150.0,
    unit_weight_kN_m3: l.unit_weight_kN_m3 || l.unit_weight || 18.0,
    material: l.material || "mkz",
    reference_curve: l.reference_curve || null,
    fit_stale: !!l.fit_stale,
    material_params: l.material_params || {},
    calibration: l.calibration || undefined,
  }));
  const body = {
    analysis_step: {
      project_name: w.project_name || "wizard-project",
      boundary_condition: w.boundary_condition || "rigid",
      solver_backend: w.solver_backend || "nonlinear",
    },
    profile_step: {
      water_table_depth_m: w.water_table_depth_m ?? null,
      bedrock: w.bedrock || null,
      layers,
    },
    motion_step: buildMotionStepPayload(w),
    damping_step: {
      mode: w.damping_mode || "frequency_independent",
      update_matrix: false,
      mode_1: w.rayleigh_mode_1_hz || null,
      mode_2: w.rayleigh_mode_2_hz || null,
    },
    control_step: {
      dt: w.dt || 0.005,
      f_max: w.f_max || 25.0,
      timeout_s: w.timeout_s || 180,
      retries: w.retries ?? 1,
      output_dir: "out/web",
    },
  };
  return request("POST", "/api/wizard/sanity-check", body);
}

export function fetchConfigTemplates() {
  return request("GET", "/api/config/templates");
}

export function applyTemplate(templateId) {
  return request("POST", "/api/config/template", { template_id: templateId });
}

// ── Examples ─────────────────────────────────────────────

export function fetchExamples() {
  return request("GET", "/api/examples");
}

export function loadExample(exampleId) {
  return request("POST", `/api/examples/${exampleId}/load`);
}

// ── Motion ───────────────────────────────────────────────

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(",")[1]; // strip data:...;base64, prefix
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export async function uploadMotionCSV(file) {
  const content_base64 = await fileToBase64(file);
  return request("POST", "/api/motion/upload/csv", {
    content_base64,
    file_name: file.name,
  });
}

export async function uploadMotionAT2(file, options = {}) {
  const content_base64 = await fileToBase64(file);
  return request("POST", "/api/motion/upload/peer-at2", {
    content_base64,
    file_name: file.name,
    units_hint: options.units_hint,
    dt_override: options.dt_override,
  });
}

export function processMotion(payload) {
  return request("POST", "/api/motion/process", payload);
}

export function motionTimeStepReduction(payload) {
  return request("POST", "/api/motion/tools/timestep-reduction", payload);
}

export function motionEstimateKappa(payload) {
  return request("POST", "/api/motion/tools/kappa", payload);
}

export function fetchMotionLibrary(extraDirs = []) {
  const qs = new URLSearchParams();
  (Array.isArray(extraDirs) ? extraDirs : []).forEach(dir => {
    if (dir && String(dir).trim()) qs.append("extra_dir", String(dir).trim());
  });
  return request("GET", `/api/motions/library${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export function clearGeneratedMotions() {
  return request("POST", "/api/motions/generated/clear");
}

export function fetchMotionPreview(motionPath, options = {}) {
  const qs = new URLSearchParams({ path: motionPath });
  Object.entries(options || {}).forEach(([key, value]) => {
    if (value == null || value === "") return;
    qs.set(key, String(value));
  });
  return request("GET", `/api/motion/preview?${qs}`);
}

// ── Calibration ──────────────────────────────────────────

export function fetchCalibrationPreview(layerData) {
  return request("POST", "/api/wizard/layer-calibration-preview", layerData);
}

export function fetchProfileDiagnostics(profileStep) {
  return request("POST", "/api/profile-diagnostics", { profile_step: profileStep });
}

export function runSingleElementTest(params) {
  const qs = new URLSearchParams(params).toString();
  return request("POST", `/api/single-element-test?${qs}`);
}

export function fetchReferenceCurves(curveType, pi = 0) {
  const qs = new URLSearchParams({ curve_type: curveType, plasticity_index: pi }).toString();
  return request("GET", `/api/reference-curves?${qs}`);
}

// ── Runs ─────────────────────────────────────────────────

export function executeRun(payload) {
  return request("POST", "/api/run", payload);
}

export function executeRunBatch(payload) {
  return request("POST", "/api/run-batch", payload);
}

export function fetchRuns(outputRoot = "out/web") {
  return request("GET", `/api/runs?output_root=${encodeURIComponent(outputRoot)}`);
}

export function fetchRunTree(outputRoot = "out/web") {
  return request("GET", `/api/runs/tree?output_root=${encodeURIComponent(outputRoot)}`);
}

export function deleteRun(runId, outputRoot = "out/web") {
  return request("DELETE", `/api/runs/${runId}?output_root=${encodeURIComponent(outputRoot)}`);
}

// ── Results ──────────────────────────────────────────────

export function fetchSignals(runId, outputRoot = "out/web") {
  return request("GET", `/api/runs/${runId}/signals?output_root=${encodeURIComponent(outputRoot)}`);
}

export function fetchResultSummary(runId, outputRoot = "out/web") {
  return request("GET", `/api/runs/${runId}/results/summary?output_root=${encodeURIComponent(outputRoot)}`);
}

export function fetchHysteresis(runId, outputRoot = "out/web") {
  return request("GET", `/api/runs/${runId}/results/hysteresis?output_root=${encodeURIComponent(outputRoot)}`);
}

export function fetchProfileSummary(runId, outputRoot = "out/web") {
  return request("GET", `/api/runs/${runId}/results/profile-summary?output_root=${encodeURIComponent(outputRoot)}`);
}

export function fetchDisplacementAnimation(
  runId,
  outputRoot = "out/web",
  frameCount = 120,
  maxDepthPoints = 200,
) {
  return request("POST", "/api/results/displacement-animation", {
    run_id: runId,
    output_root: outputRoot,
    frame_count: frameCount,
    max_depth_points: maxDepthPoints,
  });
}

export function fetchResponseSpectraSummary(runId, outputRoot = "out/web") {
  const qs = new URLSearchParams({
    run_id: runId,
    output_root: outputRoot,
  }).toString();
  return request("GET", `/api/results/response-spectra-summary?${qs}`);
}

// ── Downloads ────────────────────────────────────────────

export function downloadUrl(runId, artifact, outputRoot = "out/web") {
  return `${BASE}/api/runs/${runId}/download/${artifact}?output_root=${encodeURIComponent(outputRoot)}`;
}

export function excelExportUrl(runId, outputRoot = "out/web", tier = "pro") {
  return `${BASE}/api/runs/${runId}/export/xlsx?output_root=${encodeURIComponent(outputRoot)}&tier=${tier}`;
}
