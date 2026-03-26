/**
 * StrataWave v2 — Motion Upload & Preview Panel
 */
import { html, useState, useRef } from "./setup.js";
import { ChartCard } from "./charts.js";
import { fmt } from "./utils.js";
import * as api from "./api.js";

export function MotionPanel({ wizard, update }) {
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const csvRef = useRef(null);
  const at2Ref = useRef(null);

  async function handleCSVUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadMotionCSV(file);
      update("motion_path", result.path || result.file_path);
      update("motion_units", "m/s2");
      if (result.time && result.acc) {
        setPreview({ time: result.time, acc: result.acc, dt: result.dt, pga: result.pga });
      }
    } catch (ex) {
      setError(ex.message);
    }
    setUploading(false);
  }

  async function handleAT2Upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadMotionAT2(file);
      update("motion_path", result.path || result.file_path);
      update("motion_units", "m/s2");
      if (result.time && result.acc) {
        setPreview({ time: result.time, acc: result.acc, dt: result.dt, pga: result.pga });
      }
    } catch (ex) {
      setError(ex.message);
    }
    setUploading(false);
  }

  return html`
    <div className="step-body">
      <input ref=${csvRef} type="file" accept=".csv,.txt" className="hidden-input" onChange=${handleCSVUpload} />
      <input ref=${at2Ref} type="file" accept=".at2,.AT2" className="hidden-input" onChange=${handleAT2Upload} />

      <div className="motion-upload-row">
        <button className="btn" onClick=${() => csvRef.current?.click()} disabled=${uploading}>
          Upload CSV
        </button>
        <button className="btn" onClick=${() => at2Ref.current?.click()} disabled=${uploading}>
          Upload PEER AT2
        </button>
        ${uploading ? html`<span className="muted">Uploading...</span>` : null}
      </div>

      ${wizard.motion_path ? html`
        <div className="field" style=${{ marginTop: "0.5rem" }}>
          <label>Motion File</label>
          <input type="text" value=${wizard.motion_path} readOnly className="muted" />
        </div>
      ` : null}

      ${error ? html`<p className="error-text">${error}</p>` : null}

      <!-- Scaling -->
      <div className="row" style=${{ marginTop: "0.75rem" }}>
        <div className="field">
          <label>Scale Mode</label>
          <select value=${wizard.scale_mode || "none"}
            onChange=${e => update("scale_mode", e.target.value)}>
            <option value="none">No Scaling</option>
            <option value="scale_factor">Scale Factor</option>
            <option value="scale_to_pga">Scale to PGA</option>
          </select>
        </div>
        ${wizard.scale_mode === "scale_factor" ? html`
          <div className="field">
            <label>Factor</label>
            <input type="number" step="0.1" min="0.01"
              value=${wizard.scale_factor || 1.0}
              onInput=${e => update("scale_factor", parseFloat(e.target.value))} />
          </div>
        ` : null}
        ${wizard.scale_mode === "scale_to_pga" ? html`
          <div className="field">
            <label>Target PGA (g)</label>
            <input type="number" step="0.01" min="0.001"
              value=${wizard.target_pga_g || 0.3}
              onInput=${e => update("target_pga_g", parseFloat(e.target.value))} />
          </div>
        ` : null}
      </div>

      <!-- Preview -->
      ${preview ? html`
        <div style=${{ marginTop: "0.75rem" }}>
          <div className="metric-row">
            <div className="metric-card"><span>PGA (m/s2)</span><b>${fmt(preview.pga, 4)}</b></div>
            <div className="metric-card"><span>PGA (g)</span><b>${fmt((preview.pga || 0) / 9.81, 4)}</b></div>
            <div className="metric-card"><span>dt (s)</span><b>${fmt(preview.dt, 5)}</b></div>
            <div className="metric-card"><span>Duration (s)</span><b>${fmt(preview.time?.[preview.time.length - 1], 2)}</b></div>
          </div>
          <${ChartCard}
            title="Input Motion Preview"
            x=${preview.time} y=${preview.acc}
            xLabel="Time (s)" yLabel="Acceleration (m/s2)"
            color="#2980B9"
          />
        </div>
      ` : null}
    </div>
  `;
}
