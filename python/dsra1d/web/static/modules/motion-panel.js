/**
 * StrataWave v2 — Motion Upload & Preview Panel
 * Supports: file upload (CSV/AT2), motion library browser, scaling
 */
import { html, useState, useEffect, useRef } from "./setup.js";
import { ChartCard } from "./charts.js";
import { fmt, PARAM_HELP } from "./utils.js";
import * as api from "./api.js";
import { canUseFeature } from "./plans.js";

function HelpTip({ id }) {
  const tip = PARAM_HELP[id];
  if (!tip) return null;
  return html`<span className="help-tip" data-tip=${tip}>?</span>`;
}

export function MotionPanel({ wizard, update, plan }) {
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [library, setLibrary] = useState([]);
  const [batchMode, setBatchMode] = useState(false);
  const [libLoading, setLibLoading] = useState(false);
  const csvRef = useRef(null);
  const at2Ref = useRef(null);

  // Load motion library on mount
  useEffect(() => {
    setLibLoading(true);
    api.fetchMotionLibrary()
      .then(data => setLibrary(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLibLoading(false));
  }, []);

  // Fetch motion preview whenever motion_path changes
  useEffect(() => {
    if (!wizard.motion_path) { setPreview(null); return; }
    api.fetchMotionPreview(wizard.motion_path)
      .then(data => {
        setPreview({
          time: data.time_s,
          acc: data.acc_m_s2,
          dt: data.dt,
          pga: data.pga_m_s2,
          duration: data.duration,
          npts: data.npts,
        });
      })
      .catch(() => {}); // silently fail — preview is optional
  }, [wizard.motion_path]);

  async function handleCSVUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadMotionCSV(file);
      const motionPath = result.uploaded_path || result.path || "";
      update("motion_path", motionPath);
      update("motion_units", "m/s2");
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
      const motionPath = result.csv_path || result.uploaded_path || "";
      update("motion_path", motionPath);
      update("motion_units", "m/s2");
      if (result.time && result.acc) {
        setPreview({ time: result.time, acc: result.acc, dt: result.dt, pga: result.pga });
      }
    } catch (ex) {
      setError(ex.message);
    }
    setUploading(false);
  }

  function selectFromLibrary(motion) {
    update("motion_path", motion.path);
    update("motion_units", "m/s2");
    setError(null);
  }

  return html`
    <div className="step-body">
      <input ref=${csvRef} type="file" accept=".csv,.txt" className="hidden-input" onChange=${handleCSVUpload} />
      <input ref=${at2Ref} type="file" accept=".at2,.AT2" className="hidden-input" onChange=${handleAT2Upload} />

      <!-- Upload buttons -->
      <div className="motion-upload-row">
        <button className="btn" onClick=${() => csvRef.current?.click()} disabled=${uploading}>
          Upload CSV
        </button>
        <button className="btn" onClick=${() => at2Ref.current?.click()} disabled=${uploading}>
          Upload PEER AT2
        </button>
        ${uploading ? html`<span className="muted">Uploading...</span>` : null}
      </div>

      <!-- Motion Library -->
      ${library.length > 0 ? html`
        <div style=${{ marginTop: "0.75rem" }}>
          <div className="field">
            <label>Motion Library</label>
            <select value=${wizard.motion_path || ""}
              onChange=${e => {
                const sel = library.find(m => m.path === e.target.value);
                if (sel) selectFromLibrary(sel);
              }}>
              <option value="">— Select from library —</option>
              ${library.map(m => html`
                <option key=${m.path} value=${m.path}>
                  ${m.name} (${m.format.toUpperCase()}) — ${m.source}
                </option>
              `)}
            </select>
          </div>
        </div>
      ` : libLoading ? html`<p className="muted" style=${{ marginTop: "0.5rem" }}>Loading motion library...</p>` : null}

      <!-- Batch mode toggle (Pro) -->
      ${canUseFeature(plan, "batch_analysis") && library.length > 1 ? html`
        <div style=${{ marginTop: "0.5rem" }}>
          <label style=${{ fontSize: "0.8rem", cursor: "pointer" }}>
            <input type="checkbox" checked=${batchMode}
              onChange=${e => {
                setBatchMode(e.target.checked);
                if (e.target.checked) {
                  // Initialize batch_motions with current selection if any
                  const initial = wizard.motion_path ? [wizard.motion_path] : [];
                  update("batch_motions", initial);
                } else {
                  update("batch_motions", null);
                }
              }} />
            ${" "}Batch mode — run with multiple motions
          </label>
        </div>
      ` : null}

      ${batchMode && library.length > 0 ? html`
        <div style=${{ marginTop: "0.25rem", maxHeight: "180px", overflowY: "auto", border: "1px solid var(--border)", borderRadius: "4px", padding: "0.25rem" }}>
          ${library.map(m => {
            const checked = (wizard.batch_motions || []).includes(m.path);
            return html`
              <label key=${m.path} style=${{ display: "flex", alignItems: "center", gap: "0.3rem", padding: "0.15rem 0.25rem", fontSize: "0.75rem", cursor: "pointer" }}>
                <input type="checkbox" checked=${checked}
                  onChange=${e => {
                    const prev = wizard.batch_motions || [];
                    const next = e.target.checked ? [...prev, m.path] : prev.filter(p => p !== m.path);
                    update("batch_motions", next);
                    if (next.length > 0 && !wizard.motion_path) update("motion_path", next[0]);
                  }} />
                ${m.name} (${m.format.toUpperCase()})
              </label>
            `;
          })}
          <div style=${{ fontSize: "0.7rem", color: "var(--ink-60)", marginTop: "0.2rem", padding: "0 0.25rem" }}>
            ${(wizard.batch_motions || []).length} motion(s) selected
          </div>
        </div>
      ` : null}

      <!-- Current selection -->
      ${wizard.motion_path ? html`
        <div className="field" style=${{ marginTop: "0.5rem" }}>
          <label>Selected Motion</label>
          <div style=${{ display: "flex", gap: "0.25rem", alignItems: "center" }}>
            <input type="text" value=${wizard.motion_path} readOnly style=${{ color: "var(--ink-60)", fontSize: "0.75rem", flex: 1 }} />
            <button className="btn btn-sm" onClick=${() => { update("motion_path", ""); setPreview(null); }}
              style=${{ fontSize: "0.65rem", padding: "0.15rem 0.4rem" }}>Clear</button>
          </div>
        </div>
      ` : null}

      ${error ? html`<p className="error-text">${error}</p>` : null}

      <!-- Scaling -->
      <div className="row" style=${{ marginTop: "0.75rem" }}>
        <div className="field">
          <label>Scale Mode<${HelpTip} id="scale_mode" /></label>
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
      ${preview ? (() => {
        const rawPga = preview.pga || 0;
        const scaleMode = wizard.scale_mode || "none";
        let scaleFactor = 1.0;
        if (scaleMode === "scale_factor" && wizard.scale_factor > 0) scaleFactor = wizard.scale_factor;
        else if (scaleMode === "scale_to_pga" && wizard.target_pga_g > 0 && rawPga > 0) scaleFactor = (wizard.target_pga_g * 9.81) / rawPga;
        const effectivePga = rawPga * scaleFactor;
        const isScaled = Math.abs(scaleFactor - 1.0) > 0.001;
        return html`
          <div style=${{ marginTop: "0.75rem" }}>
            <div className="metric-row">
              <div className="metric-card"><span>${isScaled ? "Raw PGA" : "PGA"} (m/s²)</span><b>${fmt(rawPga, 4)}</b></div>
              ${isScaled ? html`
                <div className="metric-card"><span>Scaled PGA (m/s²)</span><b style=${{ color: "var(--accent)" }}>${fmt(effectivePga, 4)}</b></div>
                <div className="metric-card"><span>Scaled PGA (g)</span><b style=${{ color: "var(--accent)" }}>${fmt(effectivePga / 9.81, 4)}</b></div>
                <div className="metric-card"><span>Scale Factor</span><b>${fmt(scaleFactor, 3)}</b></div>
              ` : html`
                <div className="metric-card"><span>PGA (g)</span><b>${fmt(rawPga / 9.81, 4)}</b></div>
              `}
              <div className="metric-card"><span>dt (s)</span><b>${fmt(preview.dt, 5)}</b></div>
              <div className="metric-card"><span>Duration (s)</span><b>${fmt(preview.duration || preview.time?.[preview.time.length - 1], 2)}</b></div>
              ${preview.npts ? html`<div className="metric-card"><span>Points</span><b>${preview.npts}</b></div>` : null}
            </div>
            <${ChartCard}
              title="Input Motion Preview"
              x=${preview.time} y=${isScaled ? preview.acc.map(v => v * scaleFactor) : preview.acc}
              xLabel="Time (s)" yLabel="Acceleration (m/s²)"
              color="#2980B9"
            />
          </div>
        `;
      })() : null}
    </div>
  `;
}
