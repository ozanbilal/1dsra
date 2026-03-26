/**
 * StrataWave v2 — API client
 */

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
    material_params: l.material_params || {},
    calibration: l.calibration || undefined,
  }));

  const body = {
    analysis_step: {
      project_name: w.project_name || "wizard-project",
      boundary_condition: w.boundary_condition || "rigid",
      solver_backend: w.solver_backend || "eql",
    },
    profile_step: { layers },
    motion_step: {
      units: w.motion_units || "m/s2",
      baseline: "remove_mean",
      scale_mode: w.scale_mode || "none",
      scale_factor: w.scale_factor || null,
      target_pga: w.target_pga_g ? w.target_pga_g * 9.81 : null,
      motion_path: w.motion_path || "",
    },
    damping_step: {
      mode: w.damping_mode || "frequency_independent",
      update_matrix: false,
      mode_1: w.rayleigh_mode_1_hz || null,
      mode_2: w.rayleigh_mode_2_hz || null,
    },
    control_step: {
      dt: w.dt || 0.005,
      f_max: w.f_max || 25.0,
      output_dir: "out/web",
    },
  };
  return request("POST", "/api/config/from-wizard", body);
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

export async function uploadMotionAT2(file) {
  const content_base64 = await fileToBase64(file);
  return request("POST", "/api/motion/upload/peer-at2", {
    content_base64,
    file_name: file.name,
  });
}

export function processMotion(payload) {
  return request("POST", "/api/motion/process", payload);
}

// ── Calibration ──────────────────────────────────────────

export function fetchCalibrationPreview(layerData) {
  return request("POST", "/api/wizard/layer-calibration-preview", layerData);
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

export function fetchRuns(outputRoot = "out/web") {
  return request("GET", `/api/runs?output_root=${encodeURIComponent(outputRoot)}`);
}

export function fetchRunTree(outputRoot = "out/web") {
  return request("GET", `/api/runs/tree?output_root=${encodeURIComponent(outputRoot)}`);
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

// ── Downloads ────────────────────────────────────────────

export function downloadUrl(runId, artifact, outputRoot = "out/web") {
  return `${BASE}/api/runs/${runId}/download/${artifact}?output_root=${encodeURIComponent(outputRoot)}`;
}

export function excelExportUrl(runId, outputRoot = "out/web") {
  return `${BASE}/api/runs/${runId}/export/xlsx?output_root=${encodeURIComponent(outputRoot)}`;
}
