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

  // Normalize signal field names (API uses _s/_m_s2 suffixes)
  const time = signals?.time || signals?.time_s;
  const surfAcc = signals?.surface_acc || signals?.surface_acc_m_s2;
  const inputAcc = signals?.input_acc_m_s2;
  const psaPeriods = signals?.psa_periods || signals?.period_s;
  const psaValues = signals?.psa_values || signals?.psa_m_s2;
  const inputPsaPeriods = signals?.input_period_s;
  const inputPsaValues = signals?.input_psa_m_s2;
  const transferFreq = signals?.transfer_freq || signals?.freq_hz;
  const transferAbs = signals?.transfer_abs;

  const hasSignals = time && surfAcc;
  const hasPSA = psaPeriods && psaValues;
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
        ${activeTab === "time" && html`<${TimeHistoryTab}
          time=${time} surfAcc=${surfAcc} inputAcc=${inputAcc}
          pga=${signals?.pga} pgaInput=${signals?.pga_input} />`}
        ${activeTab === "stress_strain" && html`<${StressStrainTab}
          hysteresis=${hysteresis} selectedLayer=${selectedLayer}
          onLayerChange=${setSelectedLayer} />`}
        ${activeTab === "spectral" && html`<${SpectralTab}
          psaPeriods=${psaPeriods} psaValues=${psaValues}
          inputPsaPeriods=${inputPsaPeriods} inputPsaValues=${inputPsaValues}
          transferFreq=${transferFreq} transferAbs=${transferAbs} />`}
        ${activeTab === "profile" && html`<${ProfileTab} profile=${profile} />`}
        ${activeTab === "mobilized" && html`<${MobilizedTab} hysteresis=${hysteresis} />`}
        ${activeTab === "convergence" && html`<${ConvergenceTab} summary=${summary} />`}
      </div>
    </div>
  `;
}

// ── Tab Components ───────────────────────────────────────

function TimeHistoryTab({ time, surfAcc, inputAcc, pga: pgaFromApi, pgaInput }) {
  if (!time || !surfAcc) return html`<p className="muted">No time history data.</p>`;

  const pga = pgaFromApi || Math.max(...surfAcc.map(Math.abs));
  const hasInput = inputAcc && inputAcc.length > 1;

  // Build input time axis (same dt, same length as input)
  const inputTime = hasInput
    ? inputAcc.map((_, i) => i * (time[time.length - 1] / (inputAcc.length - 1)))
    : null;

  const series = [
    { x: time, y: surfAcc, label: "Surface", color: "var(--accent)" },
    ...(hasInput ? [{ x: inputTime, y: inputAcc, label: "Input (Base)", color: "#2980B9" }] : []),
  ];

  return html`
    <div className="tab-content">
      <div className="metric-row">
        <div className="metric-card"><span>Surface PGA (m/s²)</span><b>${fmt(pga, 4)}</b></div>
        <div className="metric-card"><span>Surface PGA (g)</span><b>${fmt(pga / 9.81, 4)}</b></div>
        ${hasInput ? html`
          <div className="metric-card"><span>Input PGA (m/s²)</span><b>${fmt(pgaInput || Math.max(...inputAcc.map(Math.abs)), 4)}</b></div>
          <div className="metric-card"><span>Amp. Ratio</span><b>${fmt(pga / ((pgaInput || Math.max(...inputAcc.map(Math.abs))) || 1), 3)}</b></div>
        ` : null}
        <div className="metric-card"><span>Duration (s)</span><b>${fmt(time[time.length - 1], 2)}</b></div>
        <div className="metric-card"><span>Samples</span><b>${time.length}</b></div>
      </div>
      <${MultiSeriesChart}
        title="Acceleration Time History"
        series=${series}
        xLabel="Time (s)" yLabel="Acceleration (m/s²)"
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

function SpectralTab({ psaPeriods, psaValues, inputPsaPeriods, inputPsaValues, transferFreq, transferAbs }) {
  if (!psaPeriods || !psaValues) {
    return html`<p className="muted">No spectral data available.</p>`;
  }

  const hasInputPsa = inputPsaPeriods && inputPsaValues && inputPsaPeriods.length > 1;
  const series = [
    { x: psaPeriods, y: psaValues, label: "Surface PSA", color: "#D35400" },
    ...(hasInputPsa ? [{ x: inputPsaPeriods, y: inputPsaValues, label: "Input PSA", color: "#2980B9" }] : []),
  ];

  const hasTF = transferFreq && transferAbs;

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
          x=${transferFreq} y=${transferAbs}
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

  // Build step-profile arrays for depth charts
  const depths = [], vs = [], gammaMax = [], dmin = [], tauPeak = [], maxAcc = [];
  let d = 0;
  for (const l of profile.layers) {
    const thick = l.thickness || 0;
    const vsVal = l.vs || 0;
    const gm = l.gamma_max || 0;
    const dm = (l.damping_min || l.dmin || 0);
    const tp = l.tau_peak || 0;
    const acc = l.max_acc || 0;
    depths.push(d); vs.push(vsVal); gammaMax.push(gm); dmin.push(dm); tauPeak.push(tp); maxAcc.push(acc);
    d += thick;
    depths.push(d); vs.push(vsVal); gammaMax.push(gm); dmin.push(dm); tauPeak.push(tp); maxAcc.push(acc);
  }

  const hasResponse = gammaMax.some(v => v > 0) || tauPeak.some(v => v > 0);

  return html`
    <div className="tab-content">
      <div className="profile-charts-grid">
        <${DepthProfileChart}
          title="Vs Profile" depths=${depths} values=${vs}
          xLabel="Vs (m/s)" yLabel="Depth (m)" color="#2980B9"
        />
        ${hasResponse ? html`
          <${DepthProfileChart}
            title="Max Strain" depths=${depths} values=${gammaMax.map(v => v * 100)}
            xLabel="Strain (%)" yLabel="Depth (m)" color="#E74C3C"
          />
          <${DepthProfileChart}
            title="Peak Stress" depths=${depths} values=${tauPeak}
            xLabel="Stress (kPa)" yLabel="Depth (m)" color="#8E44AD"
          />
          <${DepthProfileChart}
            title="Damping" depths=${depths} values=${dmin.map(v => v * 100)}
            xLabel="Damping (%)" yLabel="Depth (m)" color="#27AE60"
          />
        ` : null}
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>#</th><th>Depth (m)</th><th>Thick (m)</th>
            <th>Vs (m/s)</th><th>γ_wt</th><th>Material</th>
            <th>γ_max (%)</th><th>τ_peak (kPa)</th>
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
                <td>${l.gamma_max ? fmt(l.gamma_max * 100, 3) : "—"}</td>
                <td>${l.tau_peak ? fmt(l.tau_peak, 1) : "—"}</td>
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
