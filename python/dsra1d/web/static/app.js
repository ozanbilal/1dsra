
import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
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
  const [activeResultTab, setActiveResultTab] = useState("Time Histories");

  const [at2Path, setAt2Path] = useState("");
  const [motionPreview, setMotionPreview] = useState(null);
  const [processedMotionPath, setProcessedMotionPath] = useState("");
  const [processedMetricsPath, setProcessedMetricsPath] = useState("");

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

  function addLayer() {
    setWizard((prev) => {
      if (!prev) return prev;
      const layer = {
        name: `Layer-${(prev.profile_step.layers || []).length + 1}`,
        thickness_m: 5.0,
        unit_weight_kN_m3: 18.0,
        vs_m_s: 200.0,
        material: "pm4sand",
        material_params: { Dr: 0.45, G0: 600.0, hpo: 0.53 },
        material_optional_args: [],
      };
      const layers = [...(prev.profile_step.layers || []), layer];
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function removeLayer(idx) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      layers.splice(idx, 1);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
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
      const [signals, summary] = await Promise.all([
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/signals${runQuery}`),
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/results/summary${runQuery}`),
      ]);
      setRunSignal(signals);
      setRunSummary(summary);
    } catch (err) {
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
      updateWizard("motion_step", { motion_path: payload.converted_csv_path });
      setStatusKind("ok");
      setStatus(`AT2 imported: ${payload.converted_csv_path}`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`AT2 import failed: ${String(err)}`);
    }
  }

  async function processMotion() {
    const step = wizard?.motion_step;
    if (!step?.motion_path) {
      setStatusKind("warn");
      setStatus("Motion path is empty.");
      return;
    }
    setStatusKind("info");
    setStatus("Processing motion...");
    try {
      const payload = await requestJSON("/api/motion/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          motion_path: step.motion_path,
          units_hint: step.units,
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
      updateWizard("motion_step", { motion_path: payload.processed_motion_path });
      setStatusKind("ok");
      setStatus(`Motion processed: ${payload.processed_motion_path}`);
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

  if (!schema || !wizard) {
    return html`<div className="shell"><div className="panel">Loading...</div></div>`;
  }

  const enums = schema.enum_options || {};
  const layers = wizard.profile_step?.layers || [];
  const motionStep = wizard.motion_step || {};
  const dampingStep = wizard.damping_step || {};
  const controlStep = wizard.control_step || {};
  const analysisStep = wizard.analysis_step || {};

  return html`
    <div className="shell">
      <header className="hero">
        <h1>1DSRA Wave-1 Studio</h1>
        <p>
          DEEPSOIL-style 5-step workflow: model build, motion processing, run orchestration and
          results review without manual YAML editing.
        </p>
      </header>

      <section className="layout">
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
                <strong>Layers</strong>
                <button className="btn-sub" onClick=${addLayer}>+ Add Layer</button>
              </div>
              <div className="layer-list">
                ${layers.map(
                  (layer, idx) => html`
                    <div className="layer-card">
                      <div className="row between">
                        <span className="layer-title">${layer.name || `Layer-${idx + 1}`}</span>
                        <button className="btn-min" onClick=${() => removeLayer(idx)}>Remove</button>
                      </div>
                      <div className="field">
                        <label>Name</label>
                        <input
                          value=${layer.name || ""}
                          onInput=${(e) => updateLayer(idx, { name: e.target.value })}
                        />
                      </div>
                      <div className="row">
                        <div className="field">
                          <label>Thickness (m)</label>
                          <input
                            type="number"
                            step="0.1"
                            value=${layer.thickness_m}
                            onInput=${(e) =>
                              updateLayer(idx, { thickness_m: toNum(e.target.value, 1.0) })}
                          />
                        </div>
                        <div className="field">
                          <label>Vs (m/s)</label>
                          <input
                            type="number"
                            step="1"
                            value=${layer.vs_m_s}
                            onInput=${(e) => updateLayer(idx, { vs_m_s: toNum(e.target.value, 150) })}
                          />
                        </div>
                      </div>
                      <div className="row">
                        <div className="field">
                          <label>Unit Weight (kN/m3)</label>
                          <input
                            type="number"
                            step="0.1"
                            value=${layer.unit_weight_kN_m3}
                            onInput=${(e) =>
                              updateLayer(idx, {
                                unit_weight_kN_m3: toNum(e.target.value, 18),
                              })}
                          />
                        </div>
                        <div className="field">
                          <label>Material</label>
                          <select
                            value=${layer.material || "pm4sand"}
                            onInput=${(e) => updateLayer(idx, { material: e.target.value })}
                          >
                            ${(enums.material || []).map((v) => html`<option value=${v}>${v}</option>`)}
                          </select>
                        </div>
                      </div>
                    </div>
                  `
                )}
              </div>
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

        <main className="panel">
          <section className="panel-block">
            <div className="row between">
              <h2>Runs</h2>
              <button
                className="btn-sub"
                onClick=${() => {
                  loadRuns().catch(() => {});
                  loadRunsTree().catch(() => {});
                }}
              >
                Refresh
              </button>
            </div>
            <div className="field">
              <label>Output Root</label>
              <input
                value=${outputRoot}
                onInput=${(e) => setOutputRoot(e.target.value)}
                placeholder="H:\\...\\1DSRA\\out\\ui"
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
          </section>

          <section className="panel-block">
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

            ${selectedRunId &&
            (activeResultTab === "Stress-Strain" || activeResultTab === "Mobilized Strength")
              ? html`
                  <div className="muted">
                    ${activeResultTab} view is wired for UI parity; detailed layer-wise tensors require
                    additional backend recorder channels in the next wave.
                  </div>
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
