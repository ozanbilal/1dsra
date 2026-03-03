
import React, { useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);

const WIZARD_STEPS = [
  { id: "analysis_step", title: "1) Analysis Type" },
  { id: "profile_step", title: "2) Soil Profile" },
  { id: "motion_step", title: "3) Input Motion" },
  { id: "damping_step", title: "4) Damping" },
  { id: "control_step", title: "5) Analysis Control" },
];

const RESULT_TABS = [
  "Time Histories",
  "Stress-Strain",
  "Spectral",
  "Profile",
  "Mobilized Strength",
  "Convergence",
];

const PROFILE_PRESETS = {
  "five-main-layers": [
    { name: "Layer-1", thickness_m: 2.0, unit_weight_kN_m3: 17.5, vs_m_s: 140.0, material: "pm4sand" },
    { name: "Layer-2", thickness_m: 3.0, unit_weight_kN_m3: 18.0, vs_m_s: 180.0, material: "pm4sand" },
    { name: "Layer-3", thickness_m: 5.0, unit_weight_kN_m3: 18.5, vs_m_s: 240.0, material: "pm4silt" },
    { name: "Layer-4", thickness_m: 8.0, unit_weight_kN_m3: 19.0, vs_m_s: 320.0, material: "pm4sand" },
    { name: "Layer-5", thickness_m: 12.0, unit_weight_kN_m3: 19.5, vs_m_s: 520.0, material: "elastic" },
  ],
  "soft-over-stiff": [
    { name: "Soft-Cap", thickness_m: 4.0, unit_weight_kN_m3: 17.2, vs_m_s: 120.0, material: "pm4silt" },
    { name: "Transition", thickness_m: 6.0, unit_weight_kN_m3: 18.0, vs_m_s: 180.0, material: "pm4sand" },
    { name: "Dense-Sand", thickness_m: 10.0, unit_weight_kN_m3: 19.0, vs_m_s: 330.0, material: "pm4sand" },
    { name: "Very-Dense", thickness_m: 12.0, unit_weight_kN_m3: 19.5, vs_m_s: 520.0, material: "elastic" },
  ],
};

const MATERIAL_PARAM_PRESETS = {
  pm4sand: { Dr: 0.45, G0: 600.0, hpo: 0.53 },
  pm4silt: { Su: 35.0, Su_Rat: 0.25, G_o: 500.0, h_po: 0.6 },
  mkz: { gmax: 70000.0, gamma_ref: 0.0012, damping_min: 0.01, damping_max: 0.1, reload_factor: 2.0 },
  gqh: {
    gmax: 110000.0,
    gamma_ref: 0.001,
    a1: 1.0,
    a2: 0.45,
    m: 2.0,
    damping_min: 0.01,
    damping_max: 0.12,
    reload_factor: 1.6,
  },
  elastic: { nu: 0.3 },
};

function materialParamDefaults(material) {
  const key = String(material || "pm4sand").toLowerCase();
  const base = MATERIAL_PARAM_PRESETS[key] || {};
  return { ...base };
}

function materialParamRows(material, rawParams) {
  const defaults = materialParamDefaults(material);
  const params = rawParams && typeof rawParams === "object" ? rawParams : {};
  const defaultKeys = Object.keys(defaults);
  const extraKeys = Object.keys(params).filter((k) => !defaultKeys.includes(k));
  const keys = [...defaultKeys, ...extraKeys];
  return keys.map((key) => {
    const raw = params[key];
    const value = Number.isFinite(Number(raw)) ? Number(raw) : defaults[key];
    return { key, value: Number.isFinite(Number(value)) ? Number(value) : 0.0 };
  });
}

function parseOptionalArgs(rawText) {
  const text = String(rawText || "").trim();
  if (!text) return [];
  return text
    .split(/[,\s]+/)
    .map((token) => Number(token))
    .filter((value) => Number.isFinite(value));
}

function csvEscape(value) {
  const raw = String(value ?? "");
  const escaped = raw.replace(/"/g, '""');
  if (/[",\n]/.test(raw)) return `"${escaped}"`;
  return escaped;
}

function parseCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(current);
      current = "";
      continue;
    }
    current += ch;
  }
  out.push(current);
  return out;
}

function toNum(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function fmt(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Number(value).toFixed(digits);
}

function mini(text) {
  if (!text) return "";
  const asText = String(text);
  if (asText.length <= 52) return asText;
  return `${asText.slice(0, 52)}...`;
}

async function requestJSON(url, options = undefined) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${errText}`);
  }
  return resp.json();
}

function linePoints(xs, ys) {
  if (!Array.isArray(xs) || !Array.isArray(ys)) return "";
  const n = Math.min(xs.length, ys.length);
  if (n < 2) return "";
  const x = xs.slice(0, n);
  const y = ys.slice(0, n);
  let xMin = Math.min(...x);
  let xMax = Math.max(...x);
  let yMin = Math.min(...y);
  let yMax = Math.max(...y);
  if (Math.abs(xMax - xMin) < 1e-12) xMax = xMin + 1.0;
  if (Math.abs(yMax - yMin) < 1e-12) yMax = yMin + 1.0;
  const width = 1000;
  const height = 280;
  const pad = 24;
  const pts = [];
  for (let i = 0; i < n; i += 1) {
    const px = pad + ((x[i] - xMin) / (xMax - xMin)) * (width - 2 * pad);
    const py = height - pad - ((y[i] - yMin) / (yMax - yMin)) * (height - 2 * pad);
    pts.push(`${px.toFixed(2)},${py.toFixed(2)}`);
  }
  return pts.join(" ");
}

function ChartCard({ title, subtitle, x, y, color = "var(--copper)" }) {
  const points = useMemo(() => linePoints(x, y), [x, y]);
  return html`
    <section className="chart-card">
      <div className="chart-head">
        <h4>${title}</h4>
        ${subtitle ? html`<span className="muted">${subtitle}</span>` : null}
      </div>
      ${points
        ? html`
            <svg viewBox="0 0 1000 280" role="img" aria-label=${title}>
              <polyline
                fill="none"
                stroke=${color}
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
                points=${points}
              ></polyline>
            </svg>
          `
        : html`<div className="muted">No data</div>`}
    </section>
  `;
}

function metricFromSignal(signal, key, reducer = "max_abs") {
  if (!signal || !Array.isArray(signal[key]) || signal[key].length === 0) return null;
  const arr = signal[key];
  if (reducer === "max") return arr.reduce((a, b) => (b > a ? b : a), arr[0]);
  if (reducer === "min") return arr.reduce((a, b) => (b < a ? b : a), arr[0]);
  return arr.reduce((a, b) => {
    const av = Math.abs(b);
    return av > a ? av : a;
  }, Math.abs(arr[0]));
}

function App() {
  const [status, setStatus] = useState("Loading wizard schema...");
  const [statusKind, setStatusKind] = useState("info");
  const [schema, setSchema] = useState(null);
  const [wizard, setWizard] = useState(null);
  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [generatedConfigPath, setGeneratedConfigPath] = useState("");
  const [generatedConfigYaml, setGeneratedConfigYaml] = useState("");
  const [configWarnings, setConfigWarnings] = useState([]);

  const [outputRoot, setOutputRoot] = useState("");
  const [runs, setRuns] = useState([]);
  const [runsTree, setRunsTree] = useState({});
  const [selectedRunId, setSelectedRunId] = useState("");
  const [runSignal, setRunSignal] = useState(null);
  const [runSummary, setRunSummary] = useState(null);
  const [runHysteresis, setRunHysteresis] = useState(null);
  const [selectedLayerIndex, setSelectedLayerIndex] = useState("");
  const [activeResultTab, setActiveResultTab] = useState("Time Histories");
  const [runsPanelOpen, setRunsPanelOpen] = useState(false);

  const [at2Path, setAt2Path] = useState("");
  const [motionPreview, setMotionPreview] = useState(null);
  const [processedMotionPath, setProcessedMotionPath] = useState("");
  const [processedMetricsPath, setProcessedMetricsPath] = useState("");
  const layerImportRef = useRef(null);
  const [profileEditorMode, setProfileEditorMode] = useState("table");
  const [profilePresetKey, setProfilePresetKey] = useState("five-main-layers");
  const [autoProfile, setAutoProfile] = useState({
    useControlFmax: true,
    fMax: 25,
    pointsPerWavelength: 10,
    minSliceThickness: 0.4,
    maxSubLayersPerMain: 24,
  });

  const runQuery = outputRoot ? `?output_root=${encodeURIComponent(outputRoot)}` : "";

  function updateWizard(stepKey, patch) {
    setWizard((prev) => {
      if (!prev) return prev;
      return { ...prev, [stepKey]: { ...prev[stepKey], ...patch } };
    });
  }

  function updateLayer(index, patch) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      layers[index] = { ...layers[index], ...patch };
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function setLayerMaterial(index, material) {
    const mat = String(material || "pm4sand").toLowerCase();
    updateLayer(index, {
      material: mat,
      material_params: materialParamDefaults(mat),
      material_optional_args: [],
    });
  }

  function setLayerMaterialParam(index, key, value) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      const layer = { ...(layers[index] || {}) };
      const params = { ...(layer.material_params || {}) };
      params[key] = Number.isFinite(value) ? value : 0.0;
      layer.material_params = params;
      layers[index] = layer;
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function setLayerOptionalArgs(index, rawText) {
    const values = parseOptionalArgs(rawText);
    updateLayer(index, { material_optional_args: values });
  }

  function addLayer() {
    setWizard((prev) => {
      if (!prev) return prev;
      const material = "pm4sand";
      const layer = {
        name: `Layer-${(prev.profile_step.layers || []).length + 1}`,
        thickness_m: 5.0,
        unit_weight_kN_m3: 18.0,
        vs_m_s: 200.0,
        material,
        material_params: materialParamDefaults(material),
        material_optional_args: [],
      };
      const layers = [...(prev.profile_step.layers || []), layer];
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function clonePresetLayers(presetKey) {
    const preset = PROFILE_PRESETS[presetKey] || PROFILE_PRESETS["five-main-layers"] || [];
    return preset.map((layer, idx) => {
      const material = String(layer.material || "pm4sand").toLowerCase();
      return {
        name: layer.name || `Layer-${idx + 1}`,
        thickness_m: Number(layer.thickness_m || 1.0),
        unit_weight_kN_m3: Number(layer.unit_weight_kN_m3 || 18.0),
        vs_m_s: Number(layer.vs_m_s || 150.0),
        material,
        material_params: materialParamDefaults(material),
        material_optional_args: [],
      };
    });
  }

  function applyProfilePreset() {
    const rows = clonePresetLayers(profilePresetKey);
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: rows },
      };
    });
    setStatusKind("ok");
    setStatus(`Profile preset applied: ${profilePresetKey} (${rows.length} main layers).`);
  }

  function seedFiveMainLayers() {
    setProfilePresetKey("five-main-layers");
    const rows = clonePresetLayers("five-main-layers");
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: rows },
      };
    });
    setStatusKind("ok");
    setStatus("5-layer starter profile loaded. You can edit values in Table mode then build sublayers.");
  }

  function removeLayer(idx) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      layers.splice(idx, 1);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function updateAutoProfile(patch) {
    setAutoProfile((prev) => ({ ...prev, ...patch }));
  }

  function computeAutoSliceCount(thickness, vs, cfg) {
    const H = Math.max(Number(thickness) || 0, 1.0e-4);
    const v = Math.max(Number(vs) || 0, 1.0e-3);
    const f = Math.max(Number(cfg.fMax) || 0, 0.1);
    const ppw = Math.max(Math.round(Number(cfg.pointsPerWavelength) || 0), 4);
    const minDz = Math.max(Number(cfg.minSliceThickness) || 0, 0.0);
    const maxSub = Math.max(Math.round(Number(cfg.maxSubLayersPerMain) || 0), 1);

    const dzByWave = v / (ppw * f);
    let nSub = Math.max(1, Math.ceil(H / Math.max(dzByWave, 1.0e-6)));
    nSub = Math.min(nSub, maxSub);
    if (minDz > 0.0) {
      const byMin = Math.max(1, Math.floor(H / minDz));
      nSub = Math.min(nSub, byMin);
    }
    return Math.max(1, nSub);
  }

  function buildAutoProfileLayers(mainLayers, cfg) {
    const out = [];
    mainLayers.forEach((layer, layerIdx) => {
      const nSub = computeAutoSliceCount(layer.thickness_m, layer.vs_m_s, cfg);
      const dz = Number(layer.thickness_m) / nSub;
      for (let i = 0; i < nSub; i += 1) {
        const sName =
          nSub === 1 ? layer.name : `${layer.name || `Layer-${layerIdx + 1}`}_s${i + 1}`;
        out.push({
          ...layer,
          name: sName,
          thickness_m: Number(dz.toFixed(5)),
          material_params: { ...(layer.material_params || {}) },
          material_optional_args: [...(layer.material_optional_args || [])],
        });
      }
    });
    return out;
  }

  function applyAutoProfile() {
    const mainLayers = wizard?.profile_step?.layers || [];
    if (!mainLayers.length) {
      setStatusKind("warn");
      setStatus("Auto Profile: no main layers to slice.");
      return;
    }
    const fMaxFromControl = Number(controlStep?.f_max || 25);
    const cfg = {
      ...autoProfile,
      fMax: autoProfile.useControlFmax ? fMaxFromControl : autoProfile.fMax,
    };
    const sliced = buildAutoProfileLayers(mainLayers, cfg);
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: sliced },
      };
    });
    setStatusKind("ok");
    setStatus(
      `Auto Profile generated: ${mainLayers.length} main -> ${sliced.length} sublayers (f_max=${Number(
        cfg.fMax
      ).toFixed(2)} Hz).`
    );
  }

  function duplicateLayer(idx) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      const src = layers[idx];
      if (!src) return prev;
      const copy = {
        ...src,
        name: `${src.name || `Layer-${idx + 1}`}-copy`,
        material_params: { ...(src.material_params || {}) },
        material_optional_args: [...(src.material_optional_args || [])],
      };
      layers.splice(idx + 1, 0, copy);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function moveLayer(idx, offset) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      const target = idx + offset;
      if (target < 0 || target >= layers.length) return prev;
      const [picked] = layers.splice(idx, 1);
      layers.splice(target, 0, picked);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function exportLayersCsv() {
    const allLayers = wizard?.profile_step?.layers || [];
    if (!allLayers.length) {
      setStatusKind("warn");
      setStatus("No layers to export.");
      return;
    }
    const header = [
      "name",
      "thickness_m",
      "unit_weight_kN_m3",
      "vs_m_s",
      "material",
      "material_params_json",
      "material_optional_args_csv",
    ];
    const rows = allLayers.map((layer) => [
      layer.name || "",
      Number(layer.thickness_m || 0),
      Number(layer.unit_weight_kN_m3 || 0),
      Number(layer.vs_m_s || 0),
      layer.material || "pm4sand",
      JSON.stringify(layer.material_params || {}),
      (layer.material_optional_args || []).join(" "),
    ]);
    const lines = [header, ...rows].map((row) => row.map(csvEscape).join(","));
    const csv = `${lines.join("\n")}\n`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "layers.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setStatusKind("ok");
    setStatus(`Layer CSV exported (${allLayers.length} rows).`);
  }

  function importLayersFromCsvText(text) {
    const lines = String(text || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    if (lines.length < 2) {
      throw new Error("CSV must contain a header and at least one data row.");
    }
    const header = parseCsvLine(lines[0]).map((h) => String(h || "").trim());
    const col = (name) => header.indexOf(name);
    const idxName = col("name");
    const idxThickness = col("thickness_m");
    const idxUw = col("unit_weight_kN_m3");
    const idxVs = col("vs_m_s");
    const idxMaterial = col("material");
    const idxParams = col("material_params_json");
    const idxOptional = col("material_optional_args_csv");
    if (
      idxName < 0 ||
      idxThickness < 0 ||
      idxUw < 0 ||
      idxVs < 0 ||
      idxMaterial < 0 ||
      idxParams < 0
    ) {
      throw new Error(
        "CSV header missing required columns: name, thickness_m, unit_weight_kN_m3, vs_m_s, material, material_params_json."
      );
    }

    const importedLayers = [];
    for (let i = 1; i < lines.length; i += 1) {
      const cols = parseCsvLine(lines[i]);
      const rawMaterial = String(cols[idxMaterial] || "pm4sand").trim().toLowerCase();
      const material = MATERIAL_PARAM_PRESETS[rawMaterial] ? rawMaterial : "pm4sand";
      const paramsRaw = String(cols[idxParams] || "{}").trim();
      let params = {};
      if (paramsRaw) {
        const parsed = JSON.parse(paramsRaw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          params = parsed;
        }
      }
      const typedParams = {};
      Object.entries(params).forEach(([key, value]) => {
        const numeric = Number(value);
        if (Number.isFinite(numeric)) {
          typedParams[key] = numeric;
        }
      });
      const optionalText = idxOptional >= 0 ? String(cols[idxOptional] || "") : "";
      importedLayers.push({
        name: String(cols[idxName] || `Layer-${i}`),
        thickness_m: toNum(cols[idxThickness], 1.0),
        unit_weight_kN_m3: toNum(cols[idxUw], 18.0),
        vs_m_s: toNum(cols[idxVs], 150.0),
        material,
        material_params: Object.keys(typedParams).length
          ? typedParams
          : materialParamDefaults(material),
        material_optional_args: parseOptionalArgs(optionalText),
      });
    }
    if (!importedLayers.length) {
      throw new Error("No valid layer rows found in CSV.");
    }
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: importedLayers },
      };
    });
    setStatusKind("ok");
    setStatus(`Layer CSV imported (${importedLayers.length} rows).`);
  }

  async function onImportLayersFile(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      importLayersFromCsvText(text);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Layer CSV import failed: ${String(err)}`);
    } finally {
      if (event?.target) {
        event.target.value = "";
      }
    }
  }

  async function loadWizardSchema() {
    try {
      const payload = await requestJSON("/api/wizard/schema");
      setSchema(payload);
      setWizard(payload.defaults);
      setStatusKind("ok");
      setStatus("Wizard schema loaded.");
    } catch (err) {
      setStatusKind("err");
      setStatus(`Schema load failed: ${String(err)}`);
    }
  }

  async function loadRuns() {
    try {
      const payload = await requestJSON(`/api/runs${runQuery}`);
      setRuns(payload);
      if (!selectedRunId && payload.length > 0) {
        setSelectedRunId(payload[0].run_id);
      }
    } catch (err) {
      setStatusKind("err");
      setStatus(`Run list failed: ${String(err)}`);
    }
  }

  async function loadRunsTree() {
    try {
      const payload = await requestJSON(`/api/runs/tree${runQuery}`);
      setRunsTree(payload.tree || {});
    } catch (err) {
      setStatusKind("err");
      setStatus(`Run tree failed: ${String(err)}`);
    }
  }

  async function loadRunDetail(runId) {
    if (!runId) return;
    try {
      const [signals, summary, hysteresis] = await Promise.all([
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/signals${runQuery}`),
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/results/summary${runQuery}`),
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/results/hysteresis${runQuery}`),
      ]);
      setRunSignal(signals);
      setRunSummary(summary);
      setRunHysteresis(hysteresis);
      const firstLayer = hysteresis?.layers?.[0];
      setSelectedLayerIndex(firstLayer ? String(firstLayer.layer_index) : "");
    } catch (err) {
      setRunHysteresis(null);
      setStatusKind("err");
      setStatus(`Run detail failed: ${String(err)}`);
    }
  }

  async function generateConfig() {
    if (!wizard) return;
    setStatusKind("info");
    setStatus("Generating config from wizard...");
    try {
      const payload = await requestJSON("/api/config/from-wizard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(wizard),
      });
      setGeneratedConfigPath(payload.config_path || "");
      setGeneratedConfigYaml(payload.config_yaml || "");
      setConfigWarnings(payload.warnings || []);
      setStatusKind("ok");
      setStatus(`Config generated: ${payload.config_path}`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Config generation failed: ${String(err)}`);
    }
  }

  async function runNow() {
    if (!wizard) return;
    const motionPath = wizard.motion_step?.motion_path || "";
    if (!generatedConfigPath) {
      setStatusKind("warn");
      setStatus("Generate config first.");
      return;
    }
    if (!motionPath) {
      setStatusKind("warn");
      setStatus("Motion path is required.");
      return;
    }
    setStatusKind("info");
    setStatus("Running analysis...");
    try {
      const payload = await requestJSON("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          config_path: generatedConfigPath,
          motion_path: motionPath,
          output_root: wizard.control_step?.output_dir || "out/ui",
          backend: wizard.analysis_step?.solver_backend || "config",
          opensees_executable: wizard.control_step?.opensees_executable || null,
        }),
      });
      await loadRuns();
      await loadRunsTree();
      setSelectedRunId(payload.run_id);
      setStatusKind(payload.status === "ok" ? "ok" : "warn");
      setStatus(`Run done: ${payload.run_id} | ${payload.message}`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Run failed: ${String(err)}`);
    }
  }

  async function importAT2() {
    if (!at2Path) {
      setStatusKind("warn");
      setStatus("AT2 path is empty.");
      return;
    }
    const step = wizard?.motion_step || {};
    try {
      const payload = await requestJSON("/api/motion/import/peer-at2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: at2Path,
          units_hint: step.units || "g",
          output_dir: wizard?.control_step?.output_dir || "out/ui/motions",
        }),
      });
      updateWizard("motion_step", {
        motion_path: payload.converted_csv_path,
        units: "m/s2",
        dt_override: payload.dt_s,
      });
      setStatusKind("ok");
      setStatus(`AT2 imported: ${payload.converted_csv_path} (dt=${Number(payload.dt_s).toFixed(6)} s)`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`AT2 import failed: ${String(err)}`);
    }
  }

  async function processMotion() {
    const step = wizard?.motion_step;
    const control = wizard?.control_step || {};
    if (!step?.motion_path) {
      setStatusKind("warn");
      setStatus("Motion path is empty.");
      return;
    }
    setStatusKind("info");
    setStatus("Processing motion...");
    try {
      const fmax = Math.max(toNum(control.f_max, 25), 0.1);
      const fallbackDt = control.dt && Number(control.dt) > 0 ? Number(control.dt) : 1.0 / (20.0 * fmax);
      const payload = await requestJSON("/api/motion/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          motion_path: step.motion_path,
          units_hint: step.units,
          dt_override:
            step.dt_override !== null && step.dt_override !== undefined && Number(step.dt_override) > 0
              ? Number(step.dt_override)
              : null,
          fallback_dt: fallbackDt,
          baseline_mode: step.baseline,
          scale_mode: step.scale_mode,
          scale_factor: step.scale_factor,
          target_pga: step.target_pga,
          output_dir: wizard?.control_step?.output_dir || "out/ui/motions",
        }),
      });
      setProcessedMotionPath(payload.processed_motion_path || "");
      setProcessedMetricsPath(payload.metrics_path || "");
      setMotionPreview(payload.spectra_preview || null);
      updateWizard("motion_step", {
        motion_path: payload.processed_motion_path,
        units: "m/s2",
      });
      setStatusKind("ok");
      setStatus(`Motion processed: ${payload.processed_motion_path} (dt=${Number(payload.metrics?.dt_s || 0).toFixed(6)} s)`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Motion process failed: ${String(err)}`);
    }
  }

  useEffect(() => {
    loadWizardSchema().catch(() => {});
    loadRuns().catch(() => {});
    loadRunsTree().catch(() => {});
  }, []);

  useEffect(() => {
    loadRuns().catch(() => {});
    loadRunsTree().catch(() => {});
  }, [outputRoot]);

  useEffect(() => {
    loadRunDetail(selectedRunId).catch(() => {});
  }, [selectedRunId, outputRoot]);

  const selectedRun = useMemo(
    () => runs.find((r) => r.run_id === selectedRunId) || null,
    [runs, selectedRunId]
  );

  const metrics = useMemo(() => {
    const pga = metricFromSignal(runSignal, "surface_acc_m_s2", "max_abs") ?? selectedRun?.pga;
    const ruMax = metricFromSignal(runSignal, "ru", "max") ?? selectedRun?.ru_max;
    const duMax = metricFromSignal(runSignal, "delta_u", "max") ?? selectedRun?.delta_u_max;
    const sigmaMin =
      metricFromSignal(runSignal, "sigma_v_eff", "min") ?? selectedRun?.sigma_v_eff_min;
    return {
      pga,
      ruMax,
      duMax,
      sigmaMin,
      dt: runSignal?.dt_s ?? null,
      sigmaRef: runSignal?.sigma_v_ref ?? null,
    };
  }, [runSignal, selectedRun]);

  const hysteresisView = useMemo(() => {
    const layers = Array.isArray(runHysteresis?.layers) ? runHysteresis.layers : [];
    if (layers.length === 0) {
      return {
        layers: [],
        selected: null,
        ratioX: [],
        ratioY: [],
        energyX: [],
        energyY: [],
      };
    }
    const selected =
      layers.find((layer) => String(layer.layer_index) === String(selectedLayerIndex)) || layers[0];
    const ratioX = layers.map((layer) => Number(layer.layer_index));
    const ratioY = layers.map((layer) => Number(layer.mobilized_strength_ratio));
    const energyX = layers.map((layer) => Number(layer.layer_index));
    const energyY = layers.map((layer) => Number(layer.loop_energy));
    return { layers, selected, ratioX, ratioY, energyX, energyY };
  }, [runHysteresis, selectedLayerIndex]);

  const artifactLinks = useMemo(() => {
    if (!selectedRunId) {
      return {
        surface: "",
        pwp: "",
        h5: "",
        sqlite: "",
        meta: "",
      };
    }
    const id = encodeURIComponent(selectedRunId);
    const suffix = runQuery || "";
    const withQuery = (path) => (suffix ? `${path}${suffix}` : path);
    return {
      surface: withQuery(`/api/runs/${id}/surface-acc.csv`),
      pwp: withQuery(`/api/runs/${id}/pwp-effective.csv`),
      h5: withQuery(`/api/runs/${id}/download/results.h5`),
      sqlite: withQuery(`/api/runs/${id}/download/results.sqlite`),
      meta: withQuery(`/api/runs/${id}/download/run_meta.json`),
    };
  }, [selectedRunId, runQuery]);

  const enums = schema?.enum_options || {};
  const layers = wizard?.profile_step?.layers || [];
  const motionStep = wizard?.motion_step || {};
  const dampingStep = wizard?.damping_step || {};
  const controlStep = wizard?.control_step || {};
  const analysisStep = wizard?.analysis_step || {};
  const autoProfilePreview = useMemo(() => {
    const controlFmax = Math.max(Number(controlStep?.f_max || 25), 0.1);
    const cfg = {
      ...autoProfile,
      fMax: autoProfile.useControlFmax ? controlFmax : Math.max(Number(autoProfile.fMax || 25), 0.1),
    };
    let predicted = 0;
    for (const layer of layers) {
      predicted += computeAutoSliceCount(layer.thickness_m, layer.vs_m_s, cfg);
    }
    return {
      mainCount: layers.length,
      predictedCount: predicted,
      fMaxUsed: cfg.fMax,
    };
  }, [autoProfile, controlStep?.f_max, layers]);

  if (!schema || !wizard) {
    return html`<div className="shell"><div className="panel">Loading...</div></div>`;
  }

  return html`
    <div className="shell">
      <header className="hero">
        <h1>StrataWave Wave-1 Studio</h1>
        <p>
          DEEPSOIL-style 5-step workflow: model build, motion processing, run orchestration and
          results review without manual YAML editing.
        </p>
      </header>

      <section
        className=${`layout ${
          runsPanelOpen ? "layout-workspace-open" : "layout-workspace-collapsed"
        }`}
      >
        <aside className="panel side-panel">
          <h2>Wizard</h2>
          <div className="tab-row">
            ${WIZARD_STEPS.map(
              (step, idx) => html`
                <button
                  className=${`tab-btn ${idx === activeStepIdx ? "active" : ""}`}
                  onClick=${() => setActiveStepIdx(idx)}
                >
                  ${step.title}
                </button>
              `
            )}
          </div>

          ${activeStepIdx === 0 &&
          html`
            <div className="step-body">
              <div className="field">
                <label>Project Name</label>
                <input
                  value=${analysisStep.project_name || ""}
                  onInput=${(e) => updateWizard("analysis_step", { project_name: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Boundary Condition</label>
                <select
                  value=${analysisStep.boundary_condition || "elastic_halfspace"}
                  onInput=${(e) =>
                    updateWizard("analysis_step", { boundary_condition: e.target.value })}
                >
                  ${(enums.boundary_condition || []).map(
                    (v) => html`<option value=${v}>${v}</option>`
                  )}
                </select>
              </div>
              <div className="field">
                <label>Solver Backend</label>
                <select
                  value=${analysisStep.solver_backend || "opensees"}
                  onInput=${(e) => updateWizard("analysis_step", { solver_backend: e.target.value })}
                >
                  ${(enums.solver_backend || []).map((v) => html`<option value=${v}>${v}</option>`)}
                </select>
              </div>
              <div className="field">
                <label>PM4 Validation Profile</label>
                <select
                  value=${analysisStep.pm4_validation_profile || "basic"}
                  onInput=${(e) =>
                    updateWizard("analysis_step", { pm4_validation_profile: e.target.value })}
                >
                  ${(enums.pm4_validation_profile || []).map(
                    (v) => html`<option value=${v}>${v}</option>`
                  )}
                </select>
              </div>
            </div>
          `}

          ${activeStepIdx === 1 &&
          html`
            <div className="step-body">
              <div className="row between">
                <strong>Layers (${layers.length})</strong>
                <div className="layer-actions">
                  <button className="btn-sub" onClick=${addLayer}>+ Add Layer</button>
                  <button className="btn-min" onClick=${seedFiveMainLayers}>5-Layer Starter</button>
                  <button
                    className="btn-min"
                    onClick=${() => {
                      if (layerImportRef.current) layerImportRef.current.click();
                    }}
                  >
                    Import CSV
                  </button>
                  <button className="btn-min" onClick=${exportLayersCsv}>Export CSV</button>
                </div>
              </div>
              <input
                ref=${layerImportRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden-input"
                onChange=${onImportLayersFile}
              />

              <div className="row">
                <div className="field">
                  <label>Profile Preset</label>
                  <select
                    value=${profilePresetKey}
                    onInput=${(e) => setProfilePresetKey(e.target.value)}
                  >
                    <option value="five-main-layers">five-main-layers</option>
                    <option value="soft-over-stiff">soft-over-stiff</option>
                  </select>
                </div>
                <div className="field align-end">
                  <button className="btn-min" onClick=${applyProfilePreset}>Load Preset</button>
                </div>
              </div>

              <div className="profile-mode-row">
                <div className="mode-switch">
                  <button
                    className=${`btn-min ${profileEditorMode === "table" ? "active-mode" : ""}`}
                    onClick=${() => setProfileEditorMode("table")}
                  >
                    Table
                  </button>
                  <button
                    className=${`btn-min ${profileEditorMode === "cards" ? "active-mode" : ""}`}
                    onClick=${() => setProfileEditorMode("cards")}
                  >
                    Cards
                  </button>
                </div>
              </div>

              <div className="auto-profile-box">
                <div className="row between">
                  <strong>Automatic Profile Builder</strong>
                  <span className="muted">
                    ${autoProfilePreview.mainCount} main -> ${autoProfilePreview.predictedCount}
                    sublayers
                  </span>
                </div>

                <div className="field-inline">
                  <label>
                    <input
                      type="checkbox"
                      checked=${autoProfile.useControlFmax}
                      onChange=${(e) => updateAutoProfile({ useControlFmax: e.target.checked })}
                    />
                    Use Analysis Control f_max (${Number(controlStep.f_max || 25).toFixed(2)} Hz)
                  </label>
                </div>

                <div className="auto-profile-grid">
                  <div className="field">
                    <label>f_max (Hz)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      disabled=${autoProfile.useControlFmax}
                      value=${autoProfile.fMax}
                      onInput=${(e) => updateAutoProfile({ fMax: Math.max(toNum(e.target.value, 25), 0.1) })}
                    />
                  </div>
                  <div className="field">
                    <label>Points / Wavelength</label>
                    <input
                      type="number"
                      step="1"
                      min="4"
                      value=${autoProfile.pointsPerWavelength}
                      onInput=${(e) =>
                        updateAutoProfile({
                          pointsPerWavelength: Math.max(Math.round(toNum(e.target.value, 10)), 4),
                        })}
                    />
                  </div>
                  <div className="field">
                    <label>Min Slice Thickness (m)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value=${autoProfile.minSliceThickness}
                      onInput=${(e) =>
                        updateAutoProfile({
                          minSliceThickness: Math.max(toNum(e.target.value, 0.4), 0),
                        })}
                    />
                  </div>
                  <div className="field">
                    <label>Max Sublayers / Main Layer</label>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      value=${autoProfile.maxSubLayersPerMain}
                      onInput=${(e) =>
                        updateAutoProfile({
                          maxSubLayersPerMain: Math.max(Math.round(toNum(e.target.value, 24)), 1),
                        })}
                    />
                  </div>
                  <div className="field align-end">
                    <button className="btn-sub" onClick=${applyAutoProfile}>
                      Build Sub-Layers
                    </button>
                  </div>
                </div>
                <div className="muted">Effective f_max: ${autoProfilePreview.fMaxUsed.toFixed(2)} Hz</div>
              </div>

              ${layers.length === 0
                ? html`<div className="muted">No layer defined yet. Add at least one layer.</div>`
                : null}

              ${layers.length > 0 && profileEditorMode === "table"
                ? html`
                    <div className="layer-table-wrap">
                      <table className="layer-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Name</th>
                            <th>Thickness (m)</th>
                            <th>Unit W. (kN/m^3)</th>
                            <th>Vs (m/s)</th>
                            <th>Material</th>
                            <th>Material Params</th>
                            <th>Optional Args</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          ${layers.map((layer, idx) => {
                            const rows = materialParamRows(layer.material, layer.material_params);
                            return html`
                              <tr key=${`layer-row-${idx}`}>
                                <td>${idx + 1}</td>
                                <td>
                                  <input
                                    value=${layer.name || ""}
                                    onInput=${(e) => updateLayer(idx, { name: e.target.value })}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    min="0.001"
                                    value=${layer.thickness_m ?? ""}
                                    onInput=${(e) =>
                                      updateLayer(idx, {
                                        thickness_m: Math.max(toNum(e.target.value, 1.0), 0.001),
                                      })}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    min="0.001"
                                    value=${layer.unit_weight_kN_m3 ?? ""}
                                    onInput=${(e) =>
                                      updateLayer(idx, {
                                        unit_weight_kN_m3: Math.max(toNum(e.target.value, 18.0), 0.001),
                                      })}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="1"
                                    min="1"
                                    value=${layer.vs_m_s ?? ""}
                                    onInput=${(e) =>
                                      updateLayer(idx, { vs_m_s: Math.max(toNum(e.target.value, 150.0), 1.0) })}
                                  />
                                </td>
                                <td>
                                  <select
                                    value=${layer.material || "pm4sand"}
                                    onInput=${(e) => setLayerMaterial(idx, e.target.value)}
                                  >
                                    ${(enums.material || []).map((v) => html`<option value=${v}>${v}</option>`)}
                                  </select>
                                </td>
                                <td>
                                  <div className="param-inline-grid">
                                    ${rows.map(
                                      (row) => html`
                                        <div className="param-mini">
                                          <span>${row.key}</span>
                                          <input
                                            type="number"
                                            step="0.0001"
                                            value=${row.value}
                                            onInput=${(e) =>
                                              setLayerMaterialParam(idx, row.key, toNum(e.target.value, row.value))}
                                          />
                                        </div>
                                      `
                                    )}
                                  </div>
                                </td>
                                <td>
                                  <input
                                    placeholder="space-separated values"
                                    value=${(layer.material_optional_args || []).join(" ")}
                                    onInput=${(e) => setLayerOptionalArgs(idx, e.target.value)}
                                  />
                                </td>
                                <td>
                                  <div className="layer-actions compact">
                                    <button className="btn-min" onClick=${() => moveLayer(idx, -1)}>Up</button>
                                    <button className="btn-min" onClick=${() => moveLayer(idx, 1)}>Down</button>
                                    <button className="btn-min" onClick=${() => duplicateLayer(idx)}>Dup</button>
                                    <button className="btn-min" onClick=${() => removeLayer(idx)}>Del</button>
                                  </div>
                                </td>
                              </tr>
                            `;
                          })}
                        </tbody>
                      </table>
                    </div>
                  `
                : null}

              ${layers.length > 0 && profileEditorMode === "cards"
                ? html`
                    <div className="layer-list">
                      ${layers.map((layer, idx) => {
                        const rows = materialParamRows(layer.material, layer.material_params);
                        return html`
                          <details className="layer-card" open>
                            <summary>
                              <span className="layer-title">${layer.name || `Layer-${idx + 1}`}</span>
                            </summary>
                            <div className="row">
                              <div className="field">
                                <label>Name</label>
                                <input
                                  value=${layer.name || ""}
                                  onInput=${(e) => updateLayer(idx, { name: e.target.value })}
                                />
                              </div>
                              <div className="field">
                                <label>Material</label>
                                <select
                                  value=${layer.material || "pm4sand"}
                                  onInput=${(e) => setLayerMaterial(idx, e.target.value)}
                                >
                                  ${(enums.material || []).map((v) => html`<option value=${v}>${v}</option>`)}
                                </select>
                              </div>
                            </div>

                            <div className="row">
                              <div className="field">
                                <label>Thickness (m)</label>
                                <input
                                  type="number"
                                  step="0.01"
                                  value=${layer.thickness_m ?? ""}
                                  onInput=${(e) =>
                                    updateLayer(idx, {
                                      thickness_m: Math.max(toNum(e.target.value, 1.0), 0.001),
                                    })}
                                />
                              </div>
                              <div className="field">
                                <label>Unit Weight (kN/m^3)</label>
                                <input
                                  type="number"
                                  step="0.01"
                                  value=${layer.unit_weight_kN_m3 ?? ""}
                                  onInput=${(e) =>
                                    updateLayer(idx, {
                                      unit_weight_kN_m3: Math.max(toNum(e.target.value, 18.0), 0.001),
                                    })}
                                />
                              </div>
                              <div className="field">
                                <label>Vs (m/s)</label>
                                <input
                                  type="number"
                                  step="1"
                                  value=${layer.vs_m_s ?? ""}
                                  onInput=${(e) =>
                                    updateLayer(idx, { vs_m_s: Math.max(toNum(e.target.value, 150.0), 1.0) })}
                                />
                              </div>
                            </div>

                            <div className="param-grid">
                              ${rows.map(
                                (row) => html`
                                  <div className="field param-field">
                                    <label>${row.key}</label>
                                    <input
                                      type="number"
                                      step="0.0001"
                                      value=${row.value}
                                      onInput=${(e) =>
                                        setLayerMaterialParam(idx, row.key, toNum(e.target.value, row.value))}
                                    />
                                  </div>
                                `
                              )}
                            </div>

                            <div className="field">
                              <label>Optional Args</label>
                              <input
                                placeholder="space-separated values"
                                value=${(layer.material_optional_args || []).join(" ")}
                                onInput=${(e) => setLayerOptionalArgs(idx, e.target.value)}
                              />
                            </div>

                            <div className="layer-actions compact">
                              <button className="btn-min" onClick=${() => moveLayer(idx, -1)}>Up</button>
                              <button className="btn-min" onClick=${() => moveLayer(idx, 1)}>Down</button>
                              <button className="btn-min" onClick=${() => duplicateLayer(idx)}>Duplicate</button>
                              <button className="btn-min" onClick=${() => removeLayer(idx)}>Delete</button>
                            </div>
                          </details>
                        `;
                      })}
                    </div>
                  `
                : null}
            </div>
          `}

          ${activeStepIdx === 2 &&
          html`
            <div className="step-body">
              <div className="field">
                <label>Motion Path (CSV)</label>
                <input
                  value=${motionStep.motion_path || ""}
                  onInput=${(e) => updateWizard("motion_step", { motion_path: e.target.value })}
                  placeholder="examples/motions/sample_motion.csv"
                />
              </div>
              <div className="field">
                <label>PEER AT2 Path</label>
                <div className="row">
                  <input
                    value=${at2Path}
                    onInput=${(e) => setAt2Path(e.target.value)}
                    placeholder=".../record.at2"
                  />
                  <button className="btn-sub" onClick=${importAT2}>Import AT2</button>
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Units</label>
                  <input
                    value=${motionStep.units || "m/s2"}
                    onInput=${(e) => updateWizard("motion_step", { units: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Baseline</label>
                  <select
                    value=${motionStep.baseline || "remove_mean"}
                    onInput=${(e) => updateWizard("motion_step", { baseline: e.target.value })}
                  >
                    ${(enums.baseline || []).map((v) => html`<option value=${v}>${v}</option>`)}
                  </select>
                </div>
                <div className="field">
                  <label>dt Override (s)</label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    value=${motionStep.dt_override ?? ""}
                    placeholder="auto from time axis / control"
                    onInput=${(e) =>
                      updateWizard("motion_step", {
                        dt_override: (() => {
                          if (e.target.value === "") return null;
                          const val = Number(e.target.value);
                          if (!Number.isFinite(val) || val <= 0) return null;
                          return val;
                        })(),
                      })}
                  />
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Scale Mode</label>
                  <select
                    value=${motionStep.scale_mode || "none"}
                    onInput=${(e) => updateWizard("motion_step", { scale_mode: e.target.value })}
                  >
                    ${(enums.scale_mode || []).map((v) => html`<option value=${v}>${v}</option>`)}
                  </select>
                </div>
                <div className="field">
                  <label>Scale Factor</label>
                  <input
                    type="number"
                    step="0.01"
                    value=${motionStep.scale_factor ?? ""}
                    onInput=${(e) =>
                      updateWizard("motion_step", { scale_factor: toNum(e.target.value, 1.0) })}
                  />
                </div>
                <div className="field">
                  <label>Target PGA</label>
                  <input
                    type="number"
                    step="0.01"
                    value=${motionStep.target_pga ?? ""}
                    onInput=${(e) =>
                      updateWizard("motion_step", { target_pga: toNum(e.target.value, 0.3) })}
                  />
                </div>
              </div>
              <div className="row">
                <button className="btn-main" onClick=${processMotion}>Process Motion</button>
              </div>
              ${processedMotionPath
                ? html`
                    <div className="muted">
                      Processed CSV: ${processedMotionPath}<br />
                      Metrics JSON: ${processedMetricsPath}
                    </div>
                  `
                : null}
              ${motionPreview
                ? html`
                    <div className="charts-grid compact">
                      <${ChartCard}
                        title="Processed Acc"
                        x=${motionPreview.time_s || []}
                        y=${motionPreview.acc_m_s2 || []}
                        color="var(--copper)"
                      />
                      <${ChartCard}
                        title="PSA (preview)"
                        x=${motionPreview.period_s || []}
                        y=${motionPreview.psa_m_s2 || []}
                        color="var(--teal)"
                      />
                      <${ChartCard}
                        title="FAS Ratio"
                        x=${motionPreview.freq_hz || []}
                        y=${motionPreview.fas_ratio || []}
                        color="var(--indigo)"
                      />
                    </div>
                  `
                : null}
            </div>
          `}

          ${activeStepIdx === 3 &&
          html`
            <div className="step-body">
              <div className="field">
                <label>Damping Mode</label>
                <select
                  value=${dampingStep.mode || "frequency_independent"}
                  onInput=${(e) => updateWizard("damping_step", { mode: e.target.value })}
                >
                  <option value="frequency_independent">frequency_independent</option>
                  <option value="rayleigh">rayleigh</option>
                </select>
              </div>
              <div className="row">
                <div className="field">
                  <label>Mode-1 Hz</label>
                  <input
                    type="number"
                    step="0.1"
                    value=${dampingStep.mode_1 ?? ""}
                    onInput=${(e) => updateWizard("damping_step", { mode_1: toNum(e.target.value, 1) })}
                  />
                </div>
                <div className="field">
                  <label>Mode-2 Hz</label>
                  <input
                    type="number"
                    step="0.1"
                    value=${dampingStep.mode_2 ?? ""}
                    onInput=${(e) => updateWizard("damping_step", { mode_2: toNum(e.target.value, 5) })}
                  />
                </div>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(dampingStep.update_matrix)}
                  onChange=${(e) =>
                    updateWizard("damping_step", { update_matrix: e.target.checked })}
                />
                <label>Update damping matrix during run</label>
              </div>
            </div>
          `}

          ${activeStepIdx === 4 &&
          html`
            <div className="step-body">
              <div className="row">
                <div className="field">
                  <label>dt (s)</label>
                  <input
                    type="number"
                    step="0.0005"
                    value=${controlStep.dt ?? ""}
                    onInput=${(e) => updateWizard("control_step", { dt: toNum(e.target.value, 0.005) })}
                  />
                </div>
                <div className="field">
                  <label>f_max (Hz)</label>
                  <input
                    type="number"
                    step="1"
                    value=${controlStep.f_max ?? 25}
                    onInput=${(e) => updateWizard("control_step", { f_max: toNum(e.target.value, 25) })}
                  />
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Timeout (s)</label>
                  <input
                    type="number"
                    step="1"
                    value=${controlStep.timeout_s ?? 180}
                    onInput=${(e) =>
                      updateWizard("control_step", { timeout_s: Math.round(toNum(e.target.value, 180)) })}
                  />
                </div>
                <div className="field">
                  <label>Retries</label>
                  <input
                    type="number"
                    step="1"
                    value=${controlStep.retries ?? 1}
                    onInput=${(e) =>
                      updateWizard("control_step", { retries: Math.round(toNum(e.target.value, 1)) })}
                  />
                </div>
              </div>
              <div className="field">
                <label>OpenSees Executable</label>
                <input
                  value=${controlStep.opensees_executable || "OpenSees"}
                  onInput=${(e) =>
                    updateWizard("control_step", { opensees_executable: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Output Dir</label>
                <input
                  value=${controlStep.output_dir || "out/ui"}
                  onInput=${(e) => updateWizard("control_step", { output_dir: e.target.value })}
                />
              </div>
              <div className="row">
                <div className="field">
                  <label>Config Output Dir</label>
                  <input
                    value=${controlStep.config_output_dir || ""}
                    onInput=${(e) =>
                      updateWizard("control_step", { config_output_dir: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Config File Name</label>
                  <input
                    value=${controlStep.config_file_name || "wizard_generated.yml"}
                    onInput=${(e) =>
                      updateWizard("control_step", { config_file_name: e.target.value })}
                  />
                </div>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(controlStep.write_hdf5)}
                  onChange=${(e) => updateWizard("control_step", { write_hdf5: e.target.checked })}
                />
                <label>Write HDF5</label>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(controlStep.write_sqlite)}
                  onChange=${(e) => updateWizard("control_step", { write_sqlite: e.target.checked })}
                />
                <label>Write SQLite</label>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(controlStep.parquet_export)}
                  onChange=${(e) =>
                    updateWizard("control_step", { parquet_export: e.target.checked })}
                />
                <label>Parquet export</label>
              </div>

              <div className="row">
                <button className="btn-main" onClick=${generateConfig}>Generate Config</button>
                <button className="btn-sub" onClick=${runNow}>Run Now</button>
              </div>
            </div>
          `}

          ${generatedConfigPath
            ? html`
                <div className="generated-box">
                  <div><strong>Config:</strong> ${generatedConfigPath}</div>
                  ${configWarnings.length
                    ? html`<div className="warn-box">${configWarnings.join(" | ")}</div>`
                    : null}
                  <details>
                    <summary>Show YAML</summary>
                    <pre>${generatedConfigYaml}</pre>
                  </details>
                </div>
              `
            : null}

          <div className=${`status status-${statusKind}`}>${status}</div>
        </aside>

        <main className=${`panel workspace-panel ${runsPanelOpen ? "workspace-open" : "workspace-collapsed"}`}>
          <section className="panel-block">
            <div className="row between">
              <h2 className="runs-heading">Runs</h2>
              <div className="accordion-actions">
                <button
                  className="btn-sub runs-refresh-btn"
                  onClick=${() => {
                    loadRuns().catch(() => {});
                    loadRunsTree().catch(() => {});
                  }}
                >
                  Refresh
                </button>
                <button
                  className="btn-min panel-toggle"
                  title=${runsPanelOpen ? "Runs panelini kapat" : "Runs panelini ac"}
                  aria-expanded=${runsPanelOpen}
                  onClick=${() => setRunsPanelOpen((prev) => !prev)}
                >
                  <span className=${`panel-caret ${runsPanelOpen ? "open" : ""}`}>
                    ${runsPanelOpen ? "▾" : "◂"}
                  </span>
                </button>
              </div>
            </div>
            ${runsPanelOpen
              ? html`
                  <div className="runs-panel-content">
                    <div className="field">
                      <label>Output Root</label>
                      <input
                        value=${outputRoot}
                        onInput=${(e) => setOutputRoot(e.target.value)}
                        placeholder="H:\\...\\StrataWave\\out\\ui"
                      />
                    </div>
                    <div className="tree-box">
                      ${Object.keys(runsTree).length === 0
                        ? html`<div className="muted">No run tree.</div>`
                        : Object.entries(runsTree).map(
                            ([project, motions]) => html`
                              <details open>
                                <summary><strong>${project}</strong></summary>
                                <div className="tree-nodes">
                                  ${Object.entries(motions).map(
                                    ([motionName, motionRuns]) => html`
                                      <details>
                                        <summary>${motionName}</summary>
                                        <div className="tree-nodes">
                                          ${motionRuns.map(
                                            (run) => html`
                                              <button
                                                className=${`run-link ${
                                                  selectedRunId === run.run_id ? "active" : ""
                                                }`}
                                                onClick=${() => setSelectedRunId(run.run_id)}
                                              >
                                                ${run.run_id} (${run.status})
                                              </button>
                                            `
                                          )}
                                        </div>
                                      </details>
                                    `
                                  )}
                                </div>
                              </details>
                            `
                          )}
                    </div>

                    <h3>Latest Runs</h3>
                    <div className="cards">
                      ${runs.map(
                        (run) => html`
                          <button
                            className=${`run-card ${selectedRunId === run.run_id ? "active" : ""}`}
                            onClick=${() => setSelectedRunId(run.run_id)}
                          >
                            <div className="run-id">${run.run_id}</div>
                            <div className="muted">${mini(run.project_name || "")}</div>
                            <div className="muted">${mini(run.motion_name || run.input_motion || "")}</div>
                            <div className="chips">
                              <span className=${`chip ${run.status === "ok" ? "chip-ok" : "chip-bad"}`}
                                >${run.status}</span
                              >
                              <span className="chip chip-ok">${run.solver_backend}</span>
                            </div>
                            <div className="muted">PGA: ${fmt(run.pga)}</div>
                          </button>
                        `
                      )}
                    </div>
                  </div>
                `
              : html`
                  <div className="muted">
                    Runs panel collapsed. Sag ustteki ucgen ile tekrar acabilirsiniz.
                  </div>
                `}
          </section>

          <section className="panel-block">
            <div className="row between">
              <h3>Results</h3>
              ${selectedRunId
                ? html`
                    <div className="download-row">
                      <a className="btn-min" href=${artifactLinks.surface}>surface_acc.csv</a>
                      <a className="btn-min" href=${artifactLinks.pwp}>pwp_effective.csv</a>
                      <a className="btn-min" href=${artifactLinks.h5}>results.h5</a>
                      <a className="btn-min" href=${artifactLinks.sqlite}>results.sqlite</a>
                      <a className="btn-min" href=${artifactLinks.meta}>run_meta.json</a>
                    </div>
                  `
                : null}
            </div>

            <div className="tab-row results-tab-row">
              ${RESULT_TABS.map(
                (tab) => html`
                  <button
                    className=${`tab-btn ${activeResultTab === tab ? "active" : ""}`}
                    onClick=${() => setActiveResultTab(tab)}
                  >
                    ${tab}
                  </button>
                `
              )}
            </div>

            ${!selectedRunId
              ? html`<div className="muted">Select a run to view results.</div>`
              : null}

            ${selectedRunId && activeResultTab === "Time Histories" && runSignal
              ? html`
                  <div className="metric-grid">
                    <div className="metric-card"><span>PGA</span><b>${fmt(metrics.pga)}</b></div>
                    <div className="metric-card"><span>ru_max</span><b>${fmt(metrics.ruMax)}</b></div>
                    <div className="metric-card">
                      <span>delta_u_max</span><b>${fmt(metrics.duMax)}</b>
                    </div>
                    <div className="metric-card">
                      <span>sigma_v_eff_min</span><b>${fmt(metrics.sigmaMin)}</b>
                    </div>
                    <div className="metric-card"><span>dt_s</span><b>${fmt(metrics.dt, 6)}</b></div>
                  </div>
                  <div className="charts-grid">
                    <${ChartCard}
                      title="Surface Acceleration"
                      x=${runSignal.time_s || []}
                      y=${runSignal.surface_acc_m_s2 || []}
                      color="var(--copper)"
                    />
                    <${ChartCard}
                      title="Pore Pressure Ratio (ru)"
                      x=${runSignal.ru_time_s || runSignal.ru_t || []}
                      y=${runSignal.ru || []}
                      color="var(--stone)"
                    />
                    <${ChartCard}
                      title="delta_u"
                      x=${runSignal.delta_u_time_s || runSignal.delta_u_t || []}
                      y=${runSignal.delta_u || []}
                      color="#7f5f2d"
                    />
                    <${ChartCard}
                      title="sigma_v_eff"
                      x=${runSignal.sigma_v_eff_time_s || runSignal.sigma_v_eff_t || []}
                      y=${runSignal.sigma_v_eff || []}
                      color="#1b7d87"
                      subtitle=${`sigma_v_ref=${fmt(metrics.sigmaRef)}`}
                    />
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Spectral" && runSignal
              ? html`
                  <div className="charts-grid">
                    <${ChartCard}
                      title="PSA (5%)"
                      x=${runSignal.period_s || []}
                      y=${runSignal.psa_m_s2 || []}
                      color="var(--teal)"
                      subtitle=${runSignal.spectra_source || "recomputed"}
                    />
                    <${ChartCard}
                      title="Transfer |H(f)|"
                      x=${runSignal.freq_hz || []}
                      y=${runSignal.transfer_abs || []}
                      color="var(--indigo)"
                    />
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Profile" && runSummary
              ? html`
                  <div className="profile-grid">
                    <div className="metric-card">
                      <span>Project</span><b>${runSummary.project_name || "n/a"}</b>
                    </div>
                    <div className="metric-card">
                      <span>Backend</span><b>${runSummary.solver_backend || "n/a"}</b>
                    </div>
                    <div className="metric-card">
                      <span>Status</span><b>${runSummary.status || "n/a"}</b>
                    </div>
                    <div className="metric-card">
                      <span>Layers</span><b>${(runSummary.output_layers || []).join(", ") || "n/a"}</b>
                    </div>
                  </div>
                  <div className="muted">
                    Solver notes: ${runSummary.solver_notes || "n/a"}<br />
                    Motion: ${runSummary.input_motion || "n/a"}
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Convergence" && runSummary
              ? html`
                  <pre className="json-box">
${JSON.stringify(runSummary.convergence || { available: false }, null, 2)}
                  </pre>
                `
              : null}

            ${selectedRunId && activeResultTab === "Stress-Strain"
              ? html`
                  ${hysteresisView.layers.length === 0
                    ? html`
                        <div className="muted">
                          ${(runHysteresis && runHysteresis.note) || "No stress-strain data."}
                        </div>
                      `
                    : html`
                        <div className="row">
                          <div className="field">
                            <label>Layer</label>
                            <select
                              value=${String(hysteresisView.selected?.layer_index ?? "")}
                              onInput=${(e) => setSelectedLayerIndex(String(e.target.value))}
                            >
                              ${hysteresisView.layers.map(
                                (layer) => html`
                                  <option value=${String(layer.layer_index)}>
                                    ${layer.layer_index}: ${layer.layer_name} (${layer.model})
                                  </option>
                                `
                              )}
                            </select>
                          </div>
                        </div>
                        <div className="metric-grid">
                          <div className="metric-card">
                            <span>Material</span>
                            <b>${hysteresisView.selected?.material || "n/a"}</b>
                          </div>
                          <div className="metric-card">
                            <span>Model</span>
                            <b>${hysteresisView.selected?.model || "n/a"}</b>
                          </div>
                          <div className="metric-card">
                            <span>strain_amplitude</span>
                            <b>${fmt(hysteresisView.selected?.strain_amplitude, 6)}</b>
                          </div>
                          <div className="metric-card">
                            <span>loop_energy</span>
                            <b>${fmt(hysteresisView.selected?.loop_energy, 6)}</b>
                          </div>
                          <div className="metric-card">
                            <span>G/Gmax</span>
                            <b>${fmt(hysteresisView.selected?.g_over_gmax, 6)}</b>
                          </div>
                          <div className="metric-card">
                            <span>damping_proxy</span>
                            <b>${fmt(hysteresisView.selected?.damping_proxy, 6)}</b>
                          </div>
                        </div>
                        <div className="charts-grid">
                          <${ChartCard}
                            title="Stress-Strain Loop"
                            subtitle=${hysteresisView.selected?.is_proxy
                              ? "proxy curve"
                              : "from stored layer model"}
                            x=${hysteresisView.selected?.strain || []}
                            y=${hysteresisView.selected?.stress || []}
                            color="var(--stone)"
                          />
                        </div>
                        ${runHysteresis?.note
                          ? html`<div className="muted">${runHysteresis.note}</div>`
                          : null}
                      `}
                `
              : null}

            ${selectedRunId && activeResultTab === "Mobilized Strength"
              ? html`
                  ${hysteresisView.layers.length === 0
                    ? html`
                        <div className="muted">
                          ${(runHysteresis && runHysteresis.note) || "No mobilized-strength data."}
                        </div>
                      `
                    : html`
                        <div className="metric-grid">
                          <div className="metric-card">
                            <span>Layer count</span><b>${hysteresisView.layers.length}</b>
                          </div>
                          <div className="metric-card">
                            <span>Source</span><b>${runHysteresis?.source || "n/a"}</b>
                          </div>
                          <div className="metric-card">
                            <span>Max mobilized ratio</span>
                            <b>${fmt(Math.max(...hysteresisView.ratioY), 4)}</b>
                          </div>
                          <div className="metric-card">
                            <span>Mean mobilized ratio</span>
                            <b>
                              ${fmt(
                                hysteresisView.ratioY.reduce((a, b) => a + b, 0) /
                                  Math.max(hysteresisView.ratioY.length, 1),
                                4
                              )}
                            </b>
                          </div>
                        </div>
                        <div className="charts-grid">
                          <${ChartCard}
                            title="Mobilized Strength Ratio by Layer"
                            x=${hysteresisView.ratioX}
                            y=${hysteresisView.ratioY}
                            color="var(--copper)"
                          />
                          <${ChartCard}
                            title="Loop Energy by Layer"
                            x=${hysteresisView.energyX}
                            y=${hysteresisView.energyY}
                            color="var(--teal)"
                          />
                        </div>
                        ${runHysteresis?.note
                          ? html`<div className="muted">${runHysteresis.note}</div>`
                          : null}
                      `}
                `
              : null}
          </section>
        </main>
      </section>
    </div>
  `;
}

const root = createRoot(document.getElementById("app"));
root.render(html`<${App} />`);

