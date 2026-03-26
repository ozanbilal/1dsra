/**
 * StrataWave v2 — Soil Profile Editor
 * DEEPSOIL-style layer table with reference curve selector and calibration preview
 */
import { html, useState, useCallback, useEffect } from "./setup.js";
import { ChartCard, MultiSeriesChart, SoilProfilePlot } from "./charts.js";
import {
  fmt, defaultLayer, computeGmax,
  MATERIAL_TYPES, REFERENCE_CURVES, deepClone,
} from "./utils.js";
import * as api from "./api.js";

export function ProfileEditor({ wizard, setWizard }) {
  const layers = wizard.layers || [];
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [calibPreview, setCalibPreview] = useState(null);
  const [refCurveData, setRefCurveData] = useState(null);
  const [setResult, setSetResult] = useState(null);
  const [autoFmax, setAutoFmax] = useState(25);
  const [autoPPW, setAutoPPW] = useState(10);
  const [autoMinDz, setAutoMinDz] = useState(0.5);
  const [autoMaxSub, setAutoMaxSub] = useState(20);

  function updateLayers(newLayers) {
    setWizard(prev => ({ ...prev, layers: newLayers }));
  }

  function autoSublayer() {
    // DEEPSOIL-style: split each layer into sublayers based on wavelength criterion
    // target_dz = Vs / (points_per_wavelength * f_max), capped at min_dz and max_sublayers
    const newLayers = [];
    for (const l of layers) {
      const vs = l.vs_m_s || l.vs || 150;
      const thick = l.thickness_m || l.thickness || 5;
      const targetDz = Math.max(vs / (autoPPW * autoFmax), autoMinDz);
      const nSub = Math.min(Math.max(Math.ceil(thick / targetDz), 1), autoMaxSub);
      const subThick = thick / nSub;
      for (let j = 0; j < nSub; j++) {
        newLayers.push({
          ...deepClone(l),
          name: (l.name || "Layer") + (nSub > 1 ? `_${j + 1}` : ""),
          thickness: subThick,
          thickness_m: subThick,
        });
      }
    }
    updateLayers(newLayers);
    setSelectedIdx(0);
  }

  function addLayer() {
    const newLayers = [...layers, defaultLayer(layers.length)];
    // auto-compute gmax
    const l = newLayers[newLayers.length - 1];
    l.material_params.gmax = computeGmax(l.vs, l.unit_weight);
    updateLayers(newLayers);
    setSelectedIdx(newLayers.length - 1);
  }

  function removeLayer(idx) {
    if (layers.length <= 1) return;
    const newLayers = layers.filter((_, i) => i !== idx);
    updateLayers(newLayers);
    if (selectedIdx >= newLayers.length) setSelectedIdx(newLayers.length - 1);
  }

  function updateLayer(idx, field, value) {
    const newLayers = deepClone(layers);
    const keys = field.split(".");
    let obj = newLayers[idx];
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {};
      obj = obj[keys[i]];
    }
    obj[keys[keys.length - 1]] = value;
    // auto-compute gmax when vs or unit_weight change
    if (field === "vs" || field === "unit_weight") {
      const l = newLayers[idx];
      if (!l.material_params) l.material_params = {};
      l.material_params.gmax = computeGmax(l.vs, l.unit_weight);
    }
    updateLayers(newLayers);
  }

  const loadRefCurve = useCallback(async (curveType, pi = 0) => {
    try {
      const data = await api.fetchReferenceCurves(curveType, pi);
      setRefCurveData(data);
    } catch (e) { console.error(e); }
  }, []);

  const loadCalibPreview = useCallback(async (layer) => {
    try {
      const data = await api.fetchCalibrationPreview({
        layer: {
          name: layer.name || `Layer ${selectedIdx + 1}`,
          thickness_m: layer.thickness || layer.thickness_m || 5.0,
          vs_m_s: layer.vs || layer.vs_m_s || 150.0,
          unit_weight_kN_m3: layer.unit_weight || layer.unit_weight_kN_m3 || 18.0,
          material: layer.material || "mkz",
          material_params: layer.material_params || {},
          calibration: layer.calibration || undefined,
        },
      });
      setCalibPreview(data);
    } catch (e) { console.error("Calibration preview:", e); }
  }, [selectedIdx]);

  const runSET = useCallback(async (layer, strainAmp) => {
    try {
      const mp = layer.material_params || {};
      const params = {
        material: layer.material || "mkz",
        strain_amplitude: strainAmp,
        gmax: mp.gmax || 100000,
        gamma_ref: mp.gamma_ref || 0.001,
        damping_min: mp.damping_min || 0.01,
        damping_max: mp.damping_max || 0.15,
        reload_factor: mp.reload_factor || 2.0,
        g_reduction_min: mp.g_reduction_min || 0.0,
        a1: mp.a1 || 1.0, a2: mp.a2 || 0.0, m: mp.m || 1.0,
      };
      const data = await api.runSingleElementTest(params);
      setSetResult(data);
    } catch (e) { console.error(e); }
  }, []);

  const sel = layers[selectedIdx] || null;

  return html`
    <div className="profile-editor-full">
      <!-- Soil Profile Plot (DEEPSOIL-style) -->
      <${SoilProfilePlot} layers=${layers} />

      <div className="profile-editor">
      <!-- Layer Table -->
      <div className="layer-table-container">
        <div className="layer-table-header">
          <h4>Soil Layers (${layers.length})</h4>
          <div style=${{ display: "flex", gap: "0.35rem" }}>
            <button className="btn btn-sm" onClick=${addLayer}>+ Add</button>
          </div>
        </div>
        <details className="auto-profile-details">
          <summary>Auto Sublayering</summary>
          <div className="row" style=${{ gap: "0.4rem", marginTop: "0.4rem", fontSize: "0.75rem" }}>
            <div className="field">
              <label>f_max (Hz)</label>
              <input type="number" min="1" max="100" value=${autoFmax}
                onInput=${e => setAutoFmax(parseFloat(e.target.value) || 25)} />
            </div>
            <div className="field">
              <label>Pts/λ</label>
              <input type="number" min="3" max="30" value=${autoPPW}
                onInput=${e => setAutoPPW(parseInt(e.target.value) || 10)} />
            </div>
            <div className="field">
              <label>Min dz (m)</label>
              <input type="number" step="0.1" min="0.1" max="5" value=${autoMinDz}
                onInput=${e => setAutoMinDz(parseFloat(e.target.value) || 0.5)} />
            </div>
            <div className="field">
              <label>Max sub</label>
              <input type="number" min="1" max="50" value=${autoMaxSub}
                onInput=${e => setAutoMaxSub(parseInt(e.target.value) || 20)} />
            </div>
          </div>
          <button className="btn btn-sm btn-accent" style=${{ marginTop: "0.4rem" }}
            onClick=${autoSublayer}>Apply Auto Sublayering</button>
        </details>
        <table className="tbl layer-table">
          <thead>
            <tr>
              <th>#</th><th>Thickness (m)</th><th>Vs (m/s)</th>
              <th>Unit Wt</th><th>Material</th><th></th>
            </tr>
          </thead>
          <tbody>
            ${layers.map((l, i) => html`
              <tr key=${i} className=${i === selectedIdx ? "selected" : ""}
                onClick=${() => setSelectedIdx(i)}>
                <td>${i + 1}</td>
                <td><input type="number" step="0.5" value=${l.thickness}
                  onClick=${e => e.stopPropagation()}
                  onInput=${e => updateLayer(i, "thickness", parseFloat(e.target.value) || 1)} /></td>
                <td><input type="number" step="10" value=${l.vs}
                  onClick=${e => e.stopPropagation()}
                  onInput=${e => updateLayer(i, "vs", parseFloat(e.target.value) || 100)} /></td>
                <td><input type="number" step="0.5" value=${l.unit_weight}
                  onClick=${e => e.stopPropagation()}
                  onInput=${e => updateLayer(i, "unit_weight", parseFloat(e.target.value) || 16)} /></td>
                <td>
                  <select value=${l.material || "mkz"}
                    onClick=${e => e.stopPropagation()}
                    onChange=${e => updateLayer(i, "material", e.target.value)}>
                    ${MATERIAL_TYPES.map(m => html`<option key=${m.value} value=${m.value}>${m.value.toUpperCase()}</option>`)}
                  </select>
                </td>
                <td><button className="btn-icon" onClick=${e => { e.stopPropagation(); removeLayer(i); }}>✕</button></td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>

      <!-- Layer Properties Panel -->
      ${sel ? html`
        <div className="layer-properties">
          <h4>Layer ${selectedIdx + 1} Properties</h4>

          <!-- Reference Curve Selector -->
          <div className="field">
            <label>Reference Curve</label>
            <select value=${sel.reference_curve || ""}
              onChange=${e => {
                updateLayer(selectedIdx, "reference_curve", e.target.value);
                if (e.target.value) loadRefCurve(e.target.value, sel.plasticity_index || 0);
              }}>
              <option value="">— None —</option>
              ${REFERENCE_CURVES.map(rc => html`
                <option key=${rc.value} value=${rc.value}>${rc.label}</option>
              `)}
            </select>
          </div>

          ${sel.reference_curve && REFERENCE_CURVES.find(r => r.value === sel.reference_curve)?.needsPI ? html`
            <div className="field">
              <label>Plasticity Index (PI)</label>
              <input type="number" min="0" max="200" value=${sel.plasticity_index || 0}
                onInput=${e => {
                  updateLayer(selectedIdx, "plasticity_index", parseInt(e.target.value) || 0);
                  loadRefCurve(sel.reference_curve, parseInt(e.target.value) || 0);
                }} />
            </div>
          ` : null}

          <!-- Material Parameters -->
          <details open className="params-section">
            <summary>Material Parameters (${(sel.material || "mkz").toUpperCase()})</summary>
            <div className="param-grid">
              ${Object.entries(sel.material_params || {}).map(([key, val]) => html`
                <div className="field" key=${key}>
                  <label>${key}</label>
                  <input type="number" step="any" value=${val}
                    onInput=${e => updateLayer(selectedIdx, "material_params." + key, parseFloat(e.target.value))} />
                </div>
              `)}
            </div>
          </details>

          <!-- Calibration Preview -->
          <div className="calibration-actions">
            <button className="btn btn-sm" onClick=${() => loadCalibPreview(sel)}>Preview Curves</button>
            <button className="btn btn-sm" onClick=${() => runSET(sel, 0.01)}>Single Element Test</button>
          </div>

          ${calibPreview ? html`
            <div className="calib-charts">
              <${MultiSeriesChart}
                title="G/Gmax" logX=${true}
                xLabel="Strain" yLabel="G/Gmax"
                series=${[
                  calibPreview.target_available
                    ? { x: calibPreview.strain, y: calibPreview.target_modulus_reduction, label: "Target", color: "#2980B9" }
                    : null,
                  { x: calibPreview.strain, y: calibPreview.fitted_modulus_reduction, label: "Fitted", color: "#D35400" },
                  refCurveData ? { x: refCurveData.strain, y: refCurveData.g_gmax, label: "Reference", color: "#27AE60" } : null,
                ].filter(Boolean)}
              />
              <${MultiSeriesChart}
                title="Damping Ratio" logX=${true}
                xLabel="Strain" yLabel="Damping"
                series=${[
                  calibPreview.target_available
                    ? { x: calibPreview.strain, y: calibPreview.target_damping_ratio, label: "Target", color: "#2980B9" }
                    : null,
                  { x: calibPreview.strain, y: calibPreview.fitted_damping_ratio, label: "Fitted", color: "#8E44AD" },
                  refCurveData ? { x: refCurveData.strain, y: refCurveData.damping, label: "Reference", color: "#27AE60" } : null,
                ].filter(Boolean)}
              />
            </div>
          ` : null}

          ${setResult ? html`
            <div className="set-results">
              <h5>Single Element Test</h5>
              <div className="metric-row">
                <div className="metric-card"><span>G/Gmax</span><b>${fmt(setResult.g_reduction, 4)}</b></div>
                <div className="metric-card"><span>Masing D</span><b>${fmt(setResult.masing_damping_ratio, 4)}</b></div>
                <div className="metric-card"><span>G_sec (kPa)</span><b>${fmt(setResult.secant_modulus, 0)}</b></div>
              </div>
              <${ChartCard}
                title="Stress-Strain Loop"
                x=${setResult.loop_strain} y=${setResult.loop_stress}
                xLabel="Strain" yLabel="Stress (kPa)" color="#D35400"
              />
            </div>
          ` : null}
        </div>
      ` : html`<div className="layer-properties"><p className="muted">Select a layer to edit.</p></div>`}
    </div>
    </div>
  `;
}
