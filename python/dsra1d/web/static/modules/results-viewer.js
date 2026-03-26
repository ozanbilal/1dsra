/**
 * StrataWave v2 — Results Viewer (6 tabs matching DEEPSOIL)
 */
import { html, useState } from "./setup.js";
import { ChartCard, MultiSeriesChart, DepthProfileChart } from "./charts.js";
import { fmt, RESULT_TABS } from "./utils.js";
import { excelExportUrl, downloadUrl } from "./api.js";

export function ResultsViewer({ runId, signals, summary, hysteresis, profile, outputRoot }) {
  const [activeTab, setActiveTab] = useState("time");
  const [selectedLayer, setSelectedLayer] = useState(0);

  if (!runId) {
    return html`<div className="results-empty">
      <p>Run an analysis to see results here.</p>
    </div>`;
  }

  const hasSignals = signals && signals.time && signals.surface_acc;
  const hasPSA = signals && signals.psa_periods && signals.psa_values;
  const hasHyst = hysteresis && hysteresis.layers && hysteresis.layers.length > 0;
  const hasProfile = profile && profile.layers && profile.layers.length > 0;

  return html`
    <div className="results-viewer">
      <div className="results-header">
        <h3>Results — ${runId}</h3>
        <div className="results-actions">
          <a href=${downloadUrl(runId, "surface_acc.csv", outputRoot)} className="btn btn-sm" download>CSV</a>
          <a href=${excelExportUrl(runId, outputRoot)} className="btn btn-sm btn-accent" download>Excel</a>
        </div>
      </div>

      <div className="tab-row">
        ${RESULT_TABS.map(tab => html`
          <button key=${tab.id}
            className=${"tab-btn" + (activeTab === tab.id ? " active" : "")}
            onClick=${() => setActiveTab(tab.id)}>
            ${tab.label}
          </button>
        `)}
      </div>

      <div className="results-content">
        ${activeTab === "time" && html`<${TimeHistoryTab} signals=${signals} />`}
        ${activeTab === "stress_strain" && html`<${StressStrainTab}
          hysteresis=${hysteresis} selectedLayer=${selectedLayer}
          onLayerChange=${setSelectedLayer} />`}
        ${activeTab === "spectral" && html`<${SpectralTab} signals=${signals} />`}
        ${activeTab === "profile" && html`<${ProfileTab} profile=${profile} />`}
        ${activeTab === "mobilized" && html`<${MobilizedTab} hysteresis=${hysteresis} />`}
        ${activeTab === "convergence" && html`<${ConvergenceTab} summary=${summary} />`}
      </div>
    </div>
  `;
}

// ── Tab Components ───────────────────────────────────────

function TimeHistoryTab({ signals }) {
  if (!signals || !signals.time) return html`<p className="muted">No time history data.</p>`;

  const pga = signals.surface_acc ? Math.max(...signals.surface_acc.map(Math.abs)) : 0;

  return html`
    <div className="tab-content">
      <div className="metric-row">
        <div className="metric-card"><span>PGA (m/s2)</span><b>${fmt(pga, 4)}</b></div>
        <div className="metric-card"><span>PGA (g)</span><b>${fmt(pga / 9.81, 4)}</b></div>
        <div className="metric-card"><span>Duration (s)</span><b>${fmt(signals.time[signals.time.length - 1], 2)}</b></div>
        <div className="metric-card"><span>Samples</span><b>${signals.time.length}</b></div>
      </div>
      <${ChartCard}
        title="Surface Acceleration"
        x=${signals.time} y=${signals.surface_acc}
        xLabel="Time (s)" yLabel="Acceleration (m/s2)"
        color="var(--accent)"
      />
    </div>
  `;
}

function StressStrainTab({ hysteresis, selectedLayer, onLayerChange }) {
  if (!hysteresis || !hysteresis.layers || !hysteresis.layers.length) {
    return html`<p className="muted">No stress-strain data. Run a nonlinear analysis.</p>`;
  }

  const layer = hysteresis.layers[selectedLayer] || hysteresis.layers[0];

  return html`
    <div className="tab-content">
      <div className="row" style=${{ gap: "0.5rem", marginBottom: "0.5rem" }}>
        <label>Layer:
          <select value=${selectedLayer} onChange=${e => onLayerChange(Number(e.target.value))}>
            ${hysteresis.layers.map((l, i) => html`
              <option key=${i} value=${i}>Layer ${i + 1} (${l.material || "—"})</option>
            `)}
          </select>
        </label>
      </div>
      <${ChartCard}
        title="Stress-Strain Loop"
        subtitle=${`Layer ${selectedLayer + 1}`}
        x=${layer.strain || []} y=${layer.stress || []}
        xLabel="Shear Strain" yLabel="Shear Stress (kPa)"
        color="#D35400"
      />
    </div>
  `;
}

function SpectralTab({ signals }) {
  if (!signals || !signals.psa_periods || !signals.psa_values) {
    return html`<p className="muted">No spectral data available.</p>`;
  }

  const series = [
    { x: signals.psa_periods, y: signals.psa_values, label: "Surface PSA", color: "#D35400" },
  ];
  if (signals.psa_input_values) {
    series.push({ x: signals.psa_periods, y: signals.psa_input_values, label: "Input PSA", color: "#2980B9" });
  }

  // Transfer function
  const hasTF = signals.transfer_freq && signals.transfer_abs;

  return html`
    <div className="tab-content">
      <${MultiSeriesChart}
        title="Response Spectra (5% damping)"
        series=${series}
        xLabel="Period (s)" yLabel="PSA (m/s2)"
        logX=${true}
      />
      ${hasTF ? html`
        <${ChartCard}
          title="Transfer Function |H(f)|"
          x=${signals.transfer_freq} y=${signals.transfer_abs}
          xLabel="Frequency (Hz)" yLabel="|H(f)|"
          color="#2980B9" logX=${true}
        />
      ` : null}
    </div>
  `;
}

function ProfileTab({ profile }) {
  if (!profile || !profile.layers || !profile.layers.length) {
    return html`<p className="muted">No profile data.</p>`;
  }

  const depths = [];
  const vs = [];
  let d = 0;
  for (const l of profile.layers) {
    depths.push(d);
    vs.push(l.vs || 0);
    d += l.thickness || 0;
    depths.push(d);
    vs.push(l.vs || 0);
  }

  return html`
    <div className="tab-content">
      <div className="profile-charts-grid">
        <${DepthProfileChart}
          title="Vs Profile" depths=${depths} values=${vs}
          xLabel="Vs (m/s)" yLabel="Depth (m)" color="#2980B9"
        />
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>#</th><th>Depth (m)</th><th>Thickness (m)</th>
            <th>Vs (m/s)</th><th>Unit Wt (kN/m3)</th><th>Material</th>
          </tr>
        </thead>
        <tbody>
          ${profile.layers.map((l, i) => {
            const depthTop = profile.layers.slice(0, i).reduce((s, x) => s + (x.thickness || 0), 0);
            return html`
              <tr key=${i}>
                <td>${i + 1}</td>
                <td>${fmt(depthTop, 1)}</td>
                <td>${fmt(l.thickness, 1)}</td>
                <td>${fmt(l.vs, 0)}</td>
                <td>${fmt(l.unit_weight, 1)}</td>
                <td>${l.material || "—"}</td>
              </tr>
            `;
          })}
        </tbody>
      </table>
    </div>
  `;
}

function MobilizedTab({ hysteresis }) {
  if (!hysteresis || !hysteresis.layers) {
    return html`<p className="muted">No mobilized strength data. Run a nonlinear analysis.</p>`;
  }

  return html`
    <div className="tab-content">
      <div className="metric-row">
        ${hysteresis.layers.map((l, i) => html`
          <div className="metric-card" key=${i}>
            <span>Layer ${i + 1}</span>
            <b>Energy: ${fmt(l.energy_dissipation, 4)}</b>
          </div>
        `)}
      </div>
    </div>
  `;
}

function ConvergenceTab({ summary }) {
  if (!summary) return html`<p className="muted">No convergence data.</p>`;

  const eql = summary.eql_summary;
  if (eql) {
    return html`
      <div className="tab-content">
        <div className="metric-row">
          <div className="metric-card"><span>Iterations</span><b>${eql.iterations}</b></div>
          <div className="metric-card"><span>Converged</span><b>${eql.converged ? "Yes" : "No"}</b></div>
          <div className="metric-card"><span>Final Change</span><b>${fmt((eql.max_change_history || []).slice(-1)[0] * 100, 2)}%</b></div>
        </div>
        ${eql.max_change_history ? html`
          <${ChartCard}
            title="EQL Convergence"
            x=${eql.max_change_history.map((_, i) => i + 1)}
            y=${eql.max_change_history.map(v => v * 100)}
            xLabel="Iteration" yLabel="Max Vs Change (%)"
            color="#27AE60"
          />
        ` : null}
      </div>
    `;
  }

  // Nonlinear diagnostics
  return html`
    <div className="tab-content">
      <div className="metric-row">
        <div className="metric-card"><span>Solver</span><b>${summary.backend || "nonlinear"}</b></div>
        <div className="metric-card"><span>Status</span><b>${summary.status || "ok"}</b></div>
      </div>
    </div>
  `;
}
