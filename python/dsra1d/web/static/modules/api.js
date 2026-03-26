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

export function generateConfig(wizardState) {
  return request("POST", "/api/config/from-wizard", wizardState);
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

export async function uploadMotionCSV(file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(BASE + "/api/motion/upload/csv", { method: "POST", body: form });
  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
  return resp.json();
}

export async function uploadMotionAT2(file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(BASE + "/api/motion/upload/peer-at2", { method: "POST", body: form });
  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
  return resp.json();
}

export function processMotion(payload) {
  return request("POST", "/api/motion/process", payload);
}

// ── Calibration ──────────────────────────────────────────

export function fetchCalibrationPreview(layerData) {
  return request("POST", "/api/wizard/calibration-preview", layerData);
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
