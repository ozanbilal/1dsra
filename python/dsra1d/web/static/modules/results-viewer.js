/**
 * StrataWave v2 — Results Viewer (6 tabs matching DEEPSOIL)
 */
import { html, useState, useEffect } from "./setup.js";
import { ChartCard, MultiSeriesChart, DepthProfileChart } from "./charts.js";
import { fmt, RESULT_TABS, STANDARD_PERIODS } from "./utils.js";
import { excelExportUrl, downloadUrl, fetchSignals } from "./api.js";

export function ResultsViewer({ runId, signals, summary, hysteresis, profile, outputRoot, runs }) {
  const [activeTab, setActiveTab] = useState("time");
  const [selectedLayer, setSelectedLayer] = useState(0);
  const [compareRunId, setCompareRunId] = useState(null);
  const [compareSignals, setCompareSignals] = useState(null);

  // Fetch compare run signals when compareRunId changes
  useEffect(() => {
    if (!compareRunId) { setCompareSignals(null); return; }
    fetchSignals(compareRunId, outputRoot).then(setCompareSignals).catch(() => setCompareSignals(null));
  }, [compareRunId]);

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
  const fasFreq = signals?.fas_freq_hz;
  const fasAmp = signals?.fas_amplitude;

  const hasSignals = time && surfAcc;
  const hasPSA = psaPeriods && psaValues;
  const hasHyst = hysteresis && hysteresis.layers && hysteresis.layers.length > 0;
  const hasProfile = profile && profile.layers && profile.layers.length > 0;

  return html`
    <div className="results-viewer">
      <div className="results-header">
        <h3>Results — ${runId}</h3>
        <div className="results-actions">
          ${runs && runs.length > 1 ? html`
            <select style=${{ fontSize: "0.7rem", padding: "0.15rem 0.3rem", borderRadius: "4px", border: "1px solid var(--border)" }}
              value=${compareRunId || ""}
              onChange=${e => setCompareRunId(e.target.value || null)}>
              <option value="">Compare with...</option>
              ${runs.filter(r => r.run_id !== runId).map(r => {
                const ts = r.timestamp_utc || r.timestamp || "";
                const label = ts ? "run_" + new Date(ts).toLocaleString("tr-TR", { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" }) : r.run_id;
                return html`<option key=${r.run_id} value=${r.run_id}>${label} (${r.solver_backend || ""})</option>`;
              })}
            </select>
          ` : null}
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
          pga=${signals?.pga} pgaInput=${signals?.pga_input}
          compareSignals=${compareSignals} compareRunId=${compareRunId} />`}
        ${activeTab === "stress_strain" && html`<${StressStrainTab}
          hysteresis=${hysteresis} selectedLayer=${selectedLayer}
          onLayerChange=${setSelectedLayer} />`}
        ${activeTab === "spectral" && html`<${SpectralTab}
          psaPeriods=${psaPeriods} psaValues=${psaValues}
          inputPsaPeriods=${inputPsaPeriods} inputPsaValues=${inputPsaValues}
          transferFreq=${transferFreq} transferAbs=${transferAbs}
          fasFreq=${fasFreq} fasAmp=${fasAmp}
          compareSignals=${compareSignals} compareRunId=${compareRunId} />`}
        ${activeTab === "profile" && html`<${ProfileTab} profile=${profile} />`}
        ${activeTab === "mobilized" && html`<${MobilizedTab} hysteresis=${hysteresis} profile=${profile} />`}
        ${activeTab === "convergence" && html`<${ConvergenceTab} summary=${summary} />`}
      </div>
    </div>
  `;
}

// ── Tab Components ───────────────────────────────────────

function TimeHistoryTab({ time, surfAcc, inputAcc, pga: pgaFromApi, pgaInput, compareSignals, compareRunId }) {
  if (!time || !surfAcc) return html`<p className="muted">No time history data.</p>`;

  const pga = pgaFromApi || Math.max(...surfAcc.map(Math.abs));
  const hasInput = inputAcc && inputAcc.length > 1;
  const hasCompare = compareSignals && compareSignals.time_s && compareSignals.surface_acc_m_s2;

  // Build input time axis (same dt, same length as input)
  const inputTime = hasInput
    ? inputAcc.map((_, i) => i * (time[time.length - 1] / (inputAcc.length - 1)))
    : null;

  const series = [
    { x: time, y: surfAcc, label: "Surface", color: "var(--accent)" },
    ...(hasInput ? [{ x: inputTime, y: inputAcc, label: "Input (Base)", color: "#2980B9" }] : []),
    ...(hasCompare ? [{ x: compareSignals.time_s, y: compareSignals.surface_acc_m_s2, label: `Compare (${(compareRunId || "").slice(4, 12)})`, color: "#8E44AD" }] : []),
  ];

  // CAV = ∫|a(t)|dt
  const dt = time.length > 1 ? time[1] - time[0] : 0.01;
  let cavTotal = 0;
  for (let i = 0; i < surfAcc.length; i++) cavTotal += Math.abs(surfAcc[i]) * dt;

  // Velocity (trapezoidal integration of acc) and Displacement (integration of vel)
  const vel = new Array(surfAcc.length);
  const disp = new Array(surfAcc.length);
  vel[0] = 0; disp[0] = 0;
  for (let i = 1; i < surfAcc.length; i++) {
    vel[i] = vel[i - 1] + 0.5 * (surfAcc[i - 1] + surfAcc[i]) * dt;
    disp[i] = disp[i - 1] + 0.5 * (vel[i - 1] + vel[i]) * dt;
  }
  const pgv = Math.max(...vel.map(Math.abs));
  const pgd = Math.max(...disp.map(Math.abs));

  // Arias Intensity: Ia = (π / 2g) × ∫ a²(t) dt — cumulative
  const ariasTime = [], ariasNorm = [];
  let cumIa = 0;
  for (let i = 0; i < surfAcc.length; i++) {
    cumIa += surfAcc[i] * surfAcc[i] * dt;
    ariasTime.push(time[i]);
    ariasNorm.push(cumIa);
  }
  const iaTotal = cumIa * Math.PI / (2 * 9.81);
  // Normalize to 0-1 for Husid plot
  const iaNormalized = ariasNorm.map(v => cumIa > 0 ? v / cumIa : 0);
  // Significant duration D5-95
  let t5 = 0, t95 = 0;
  for (let i = 0; i < iaNormalized.length; i++) {
    if (iaNormalized[i] >= 0.05 && t5 === 0) t5 = ariasTime[i];
    if (iaNormalized[i] >= 0.95 && t95 === 0) { t95 = ariasTime[i]; break; }
  }
  const d595 = t95 - t5;

  return html`
    <div className="tab-content">
      <div className="metric-row">
        <div className="metric-card"><span>Surface PGA (m/s²)</span><b>${fmt(pga, 4)}</b></div>
        <div className="metric-card"><span>Surface PGA (g)</span><b>${fmt(pga / 9.81, 4)}</b></div>
        ${hasInput ? html`
          <div className="metric-card"><span>Input PGA (m/s²)</span><b>${fmt(pgaInput || Math.max(...inputAcc.map(Math.abs)), 4)}</b></div>
          <div className="metric-card"><span>Amp. Ratio</span><b>${fmt(pga / ((pgaInput || Math.max(...inputAcc.map(Math.abs))) || 1), 3)}</b></div>
        ` : null}
        <div className="metric-card"><span>PGV (cm/s)</span><b>${fmt(pgv * 100, 2)}</b></div>
        <div className="metric-card"><span>PGD (cm)</span><b>${fmt(pgd * 100, 3)}</b></div>
        <div className="metric-card"><span>Arias (m/s)</span><b>${fmt(iaTotal, 4)}</b></div>
        <div className="metric-card"><span>CAV (m/s)</span><b>${fmt(cavTotal, 3)}</b></div>
        <div className="metric-card"><span>D5-95 (s)</span><b>${fmt(d595, 2)}</b></div>
        <div className="metric-card"><span>Duration (s)</span><b>${fmt(time[time.length - 1], 2)}</b></div>
      </div>
      <${MultiSeriesChart}
        title="Acceleration Time History"
        series=${series}
        xLabel="Time (s)" yLabel="Acceleration (m/s²)"
      />
      <${ChartCard}
        title="Velocity Time History"
        subtitle="PGV = ${fmt(pgv * 100, 2)} cm/s"
        x=${time} y=${vel.map(v => v * 100)}
        xLabel="Time (s)" yLabel="Velocity (cm/s)"
        color="#2980B9"
      />
      <${ChartCard}
        title="Displacement Time History"
        subtitle="PGD = ${fmt(pgd * 100, 3)} cm"
        x=${time} y=${disp.map(v => v * 100)}
        xLabel="Time (s)" yLabel="Displacement (cm)"
        color="#8E44AD"
      />
      <${ChartCard}
        title="Husid Plot (Normalized Arias Intensity)"
        subtitle="D5-95 = ${fmt(d595, 2)}s"
        x=${ariasTime} y=${iaNormalized}
        xLabel="Time (s)" yLabel="Normalized Ia"
        color="#27AE60"
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
      <div className="row" style=${{ gap: "0.5rem", marginBottom: "0.5rem", alignItems: "center" }}>
        <label>Layer:
          <select value=${selectedLayer} onChange=${e => onLayerChange(Number(e.target.value))}>
            ${hysteresis.layers.map((l, i) => html`
              <option key=${i} value=${i}>${l.layer_name || `Layer ${i + 1}`} (${l.material || "—"})</option>
            `)}
          </select>
        </label>
      </div>
      <div className="metric-row" style=${{ marginBottom: "0.5rem" }}>
        <div className="metric-card"><span>Max Strain</span><b>${fmt(layer.strain_amplitude, 5)}</b></div>
        <div className="metric-card"><span>G/Gmax</span><b>${fmt(layer.g_over_gmax, 4)}</b></div>
        <div className="metric-card"><span>Damping</span><b>${fmt((layer.damping_proxy || 0) * 100, 2)}%</b></div>
        <div className="metric-card"><span>Loop Energy</span><b>${fmt(layer.loop_energy, 2)}</b></div>
        <div className="metric-card"><span>Mob. Ratio</span><b>${fmt(layer.mobilized_strength_ratio, 4)}</b></div>
      </div>
      <${ChartCard}
        title="Stress-Strain Loop"
        subtitle=${layer.layer_name || `Layer ${selectedLayer + 1}`}
        x=${layer.strain || []} y=${(layer.stress || []).map(s => s / 1000)}
        xLabel="Shear Strain" yLabel="Shear Stress (kPa)"
        color="#D35400"
      />
    </div>
  `;
}

function interpolateAtPeriods(periods, values, targetPeriods) {
  // Linear interpolation in log-space for spectral data
  return targetPeriods.map(tp => {
    if (!periods || periods.length < 2) return null;
    let lo = 0;
    for (let i = 1; i < periods.length; i++) {
      if (periods[i] >= tp) { lo = i - 1; break; }
      lo = i;
    }
    if (lo >= periods.length - 1) return values[periods.length - 1];
    if (lo < 0) return values[0];
    const hi = lo + 1;
    const frac = (tp - periods[lo]) / (periods[hi] - periods[lo] || 1);
    return values[lo] + frac * (values[hi] - values[lo]);
  });
}

function SpectralTab({ psaPeriods, psaValues, inputPsaPeriods, inputPsaValues, transferFreq, transferAbs, fasFreq, fasAmp, compareSignals, compareRunId }) {
  if (!psaPeriods || !psaValues) {
    return html`<p className="muted">No spectral data available.</p>`;
  }

  const hasInputPsa = inputPsaPeriods && inputPsaValues && inputPsaPeriods.length > 1;
  const hasCompare = compareSignals && compareSignals.period_s && compareSignals.psa_m_s2;
  const series = [
    { x: psaPeriods, y: psaValues, label: "Surface PSA", color: "#D35400" },
    ...(hasInputPsa ? [{ x: inputPsaPeriods, y: inputPsaValues, label: "Input PSA", color: "#2980B9" }] : []),
    ...(hasCompare ? [{ x: compareSignals.period_s, y: compareSignals.psa_m_s2, label: `Compare (${(compareRunId || "").slice(4, 12)})`, color: "#8E44AD" }] : []),
  ];

  const hasTF = transferFreq && transferAbs;

  // Spectral Amplification Ratio (surface / input)
  const hasAmpRatio = hasInputPsa && psaPeriods.length > 2;
  let ampRatioPeriods = null, ampRatioValues = null;
  if (hasAmpRatio) {
    const inputInterp = interpolateAtPeriods(inputPsaPeriods, inputPsaValues, psaPeriods);
    ampRatioPeriods = [];
    ampRatioValues = [];
    for (let i = 0; i < psaPeriods.length; i++) {
      const inp = inputInterp[i];
      if (inp != null && inp > 0.001) {
        ampRatioPeriods.push(psaPeriods[i]);
        ampRatioValues.push(psaValues[i] / inp);
      }
    }
  }

  // PSA Summary Table at standard periods
  const surfAtStd = interpolateAtPeriods(psaPeriods, psaValues, STANDARD_PERIODS);
  const inputAtStd = hasInputPsa ? interpolateAtPeriods(inputPsaPeriods, inputPsaValues, STANDARD_PERIODS) : null;

  return html`
    <div className="tab-content">
      <${MultiSeriesChart}
        title="Response Spectra (5% damping)"
        series=${series}
        xLabel="Period (s)" yLabel="PSA (m/s²)"
        logX=${true}
      />
      ${hasAmpRatio && ampRatioPeriods.length > 2 ? html`
        <${ChartCard}
          title="Spectral Amplification Ratio (Surface / Input)"
          x=${ampRatioPeriods} y=${ampRatioValues}
          xLabel="Period (s)" yLabel="Amplification"
          color="#E74C3C" logX=${true}
        />
      ` : null}
      ${hasTF ? html`
        <${ChartCard}
          title="Transfer Function |H(f)|"
          x=${transferFreq} y=${transferAbs}
          xLabel="Frequency (Hz)" yLabel="|H(f)|"
          color="#2980B9" logX=${true}
        />
      ` : null}
      ${fasFreq && fasAmp && fasFreq.length > 2 ? html`
        <${ChartCard}
          title="Fourier Amplitude Spectrum"
          x=${fasFreq} y=${fasAmp}
          xLabel="Frequency (Hz)" yLabel="Fourier Amplitude (m/s)"
          color="#16A085" logX=${true}
        />
      ` : null}
      <div style=${{ marginTop: "0.75rem" }}>
        <h4 style=${{ fontSize: "0.85rem", marginBottom: "0.4rem" }}>PSA Summary at Standard Periods</h4>
        <div style=${{ maxHeight: "300px", overflowY: "auto" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Period (s)</th><th>Freq (Hz)</th>
                <th>Surface PSA (m/s²)</th><th>Surface PSA (g)</th>
                ${hasInputPsa ? html`<th>Input PSA (m/s²)</th><th>Amp. Ratio</th>` : null}
              </tr>
            </thead>
            <tbody>
              ${STANDARD_PERIODS.map((T, i) => {
                const sv = surfAtStd[i];
                const iv = inputAtStd ? inputAtStd[i] : null;
                const ratio = iv != null && iv > 0.001 ? sv / iv : null;
                return html`
                  <tr key=${T}>
                    <td>${fmt(T, 3)}</td>
                    <td>${fmt(1 / T, 2)}</td>
                    <td>${sv != null ? fmt(sv, 4) : "—"}</td>
                    <td>${sv != null ? fmt(sv / 9.81, 4) : "—"}</td>
                    ${hasInputPsa ? html`
                      <td>${iv != null ? fmt(iv, 4) : "—"}</td>
                      <td>${ratio != null ? fmt(ratio, 3) : "—"}</td>
                    ` : null}
                  </tr>
                `;
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function ProfileTab({ profile }) {
  if (!profile || !profile.layers || !profile.layers.length) {
    return html`<p className="muted">No profile data.</p>`;
  }

  // Build step-profile arrays for depth charts
  const depths = [], vs = [], gammaMax = [], dampRatio = [], tauPeak = [], sigmaV0 = [], ruMax = [];
  let d = 0;
  for (const l of profile.layers) {
    const thick = l.thickness_m || l.thickness || 0;
    const vsVal = l.vs_m_s || l.vs || 0;
    const gm = l.gamma_max || 0;
    const dr = l.damping_ratio || 0;
    const tp = l.tau_peak_kpa || l.tau_peak || 0;
    const sv = l.sigma_v0_mid_kpa || 0;
    const ru = l.ru_max || 0;
    depths.push(d); vs.push(vsVal); gammaMax.push(gm); dampRatio.push(dr); tauPeak.push(tp); sigmaV0.push(sv); ruMax.push(ru);
    d += thick;
    depths.push(d); vs.push(vsVal); gammaMax.push(gm); dampRatio.push(dr); tauPeak.push(tp); sigmaV0.push(sv); ruMax.push(ru);
  }

  const hasResponse = gammaMax.some(v => v > 0) || tauPeak.some(v => v > 0);
  const hasRu = ruMax.some(v => v > 0);

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
            title="Damping" depths=${depths} values=${dampRatio.map(v => v * 100)}
            xLabel="Damping (%)" yLabel="Depth (m)" color="#27AE60"
          />
        ` : null}
        <${DepthProfileChart}
          title="Overburden Stress" depths=${depths} values=${sigmaV0}
          xLabel="σ'v0 (kPa)" yLabel="Depth (m)" color="#2C3E50"
        />
        ${hasRu ? html`
          <${DepthProfileChart}
            title="Max Pore Pressure Ratio" depths=${depths} values=${ruMax}
            xLabel="ru_max" yLabel="Depth (m)" color="#E74C3C"
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
            const depthTop = profile.layers.slice(0, i).reduce((s, x) => s + (x.thickness_m || x.thickness || 0), 0);
            return html`
              <tr key=${i}>
                <td>${i + 1}</td>
                <td>${fmt(depthTop, 1)}</td>
                <td>${fmt(l.thickness_m || l.thickness, 1)}</td>
                <td>${fmt(l.vs_m_s || l.vs, 0)}</td>
                <td>${fmt(l.unit_weight_kN_m3 || l.unit_weight_kn_m3 || l.unit_weight, 1)}</td>
                <td>${l.material || "—"}</td>
                <td>${l.gamma_max != null ? fmt(l.gamma_max * 100, 3) : "—"}</td>
                <td>${l.tau_peak_kpa != null ? fmt(l.tau_peak_kpa, 1) : "—"}</td>
              </tr>
            `;
          })}
        </tbody>
      </table>
    </div>
  `;
}

function MobilizedTab({ hysteresis, profile }) {
  if (!hysteresis || !hysteresis.layers || !hysteresis.layers.length) {
    return html`<p className="muted">No mobilized strength data. Run a nonlinear or EQL analysis.</p>`;
  }

  const layers = hysteresis.layers;

  // Build depth arrays for mobilized strength ratio chart
  const depths = [], mobRatios = [], gOverGmax = [], dampingVals = [];
  let d = 0;
  const profileLayers = profile?.layers || [];
  for (let i = 0; i < layers.length; i++) {
    const pl = profileLayers[i];
    const thick = pl ? (pl.thickness_m || pl.thickness || 1) : 1;
    const mob = layers[i].mobilized_strength_ratio || 0;
    const gg = layers[i].g_over_gmax || 0;
    const dp = layers[i].damping_proxy || 0;
    depths.push(d); mobRatios.push(mob); gOverGmax.push(gg); dampingVals.push(dp);
    d += thick;
    depths.push(d); mobRatios.push(mob); gOverGmax.push(gg); dampingVals.push(dp);
  }

  return html`
    <div className="tab-content">
      <div className="metric-row">
        ${layers.map((l, i) => html`
          <div className="metric-card" key=${i}>
            <span>${l.layer_name || `Layer ${i + 1}`}</span>
            <b>Mob: ${fmt(l.mobilized_strength_ratio, 3)}</b>
          </div>
        `)}
      </div>
      <div className="profile-charts-grid">
        <${DepthProfileChart}
          title="Mobilized Strength Ratio"
          depths=${depths} values=${mobRatios}
          xLabel="τ_mob / σ'v₀" yLabel="Depth (m)" color="#E74C3C"
        />
        <${DepthProfileChart}
          title="G/Gmax"
          depths=${depths} values=${gOverGmax}
          xLabel="G/Gmax" yLabel="Depth (m)" color="#2980B9"
        />
        <${DepthProfileChart}
          title="Damping Ratio"
          depths=${depths} values=${dampingVals.map(v => v * 100)}
          xLabel="Damping (%)" yLabel="Depth (m)" color="#27AE60"
        />
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>#</th><th>Layer</th><th>Material</th>
            <th>γ_amp</th><th>G/Gmax</th><th>Mob. Ratio</th>
            <th>Damping</th><th>Loop Energy</th>
          </tr>
        </thead>
        <tbody>
          ${layers.map((l, i) => html`
            <tr key=${i}>
              <td>${i + 1}</td>
              <td>${l.layer_name || "—"}</td>
              <td>${l.material || "—"}</td>
              <td>${fmt(l.strain_amplitude, 5)}</td>
              <td>${fmt(l.g_over_gmax, 4)}</td>
              <td>${fmt(l.mobilized_strength_ratio, 4)}</td>
              <td>${fmt(l.damping_proxy * 100, 2)}%</td>
              <td>${fmt(l.loop_energy, 2)}</td>
            </tr>
          `)}
        </tbody>
      </table>
    </div>
  `;
}

function ConvergenceTab({ summary }) {
  if (!summary) return html`<p className="muted">No convergence data.</p>`;

  const conv = summary.convergence || {};
  const eql = summary.eql_summary;

  // EQL convergence
  if (eql) {
    return html`
      <div className="tab-content">
        <div className="metric-row">
          <div className="metric-card"><span>Iterations</span><b>${eql.iterations}</b></div>
          <div className="metric-card"><span>Converged</span><b style=${{ color: eql.converged ? "#27AE60" : "#E74C3C" }}>${eql.converged ? "Yes" : "No"}</b></div>
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

  // Nonlinear convergence diagnostics
  const severity = conv.convergence_severity || "unknown";
  const sevColor = severity === "ok" ? "#27AE60" : severity === "warning" ? "#F39C12" : severity === "error" ? "#E74C3C" : "var(--ink-60)";
  const warnCount = conv.solver_warning_count;
  const failCount = conv.solver_failed_converge_count;
  const analyzeFailCount = conv.solver_analyze_failed_count;
  const divZeroCount = conv.solver_divide_by_zero_count;
  const fallbackCount = conv.solver_dynamic_fallback_failed_count;

  return html`
    <div className="tab-content">
      <div className="metric-row">
        <div className="metric-card"><span>Solver</span><b>${summary.solver_backend || "nonlinear"}</b></div>
        <div className="metric-card"><span>Status</span><b>${summary.status || "ok"}</b></div>
        <div className="metric-card">
          <span>Severity</span>
          <b style=${{ color: sevColor, textTransform: "uppercase" }}>${severity}</b>
        </div>
      </div>
      ${(warnCount != null || failCount != null) ? html`
        <div className="metric-row" style=${{ marginTop: "0.5rem" }}>
          ${warnCount != null ? html`<div className="metric-card"><span>Warnings</span><b style=${{ color: warnCount > 0 ? "#F39C12" : "inherit" }}>${warnCount}</b></div>` : null}
          ${failCount != null ? html`<div className="metric-card"><span>Failed Converge</span><b style=${{ color: failCount > 0 ? "#E74C3C" : "inherit" }}>${failCount}</b></div>` : null}
          ${analyzeFailCount != null ? html`<div className="metric-card"><span>Analyze Failed</span><b style=${{ color: analyzeFailCount > 0 ? "#E74C3C" : "inherit" }}>${analyzeFailCount}</b></div>` : null}
          ${divZeroCount != null ? html`<div className="metric-card"><span>Div by Zero</span><b style=${{ color: divZeroCount > 0 ? "#E74C3C" : "inherit" }}>${divZeroCount}</b></div>` : null}
          ${fallbackCount != null ? html`<div className="metric-card"><span>Fallback Failed</span><b style=${{ color: fallbackCount > 0 ? "#E74C3C" : "inherit" }}>${fallbackCount}</b></div>` : null}
        </div>
      ` : null}
      ${summary.solver_notes ? html`
        <div style=${{ marginTop: "0.5rem", padding: "0.5rem", background: "rgba(0,0,0,0.03)", borderRadius: "6px", fontSize: "0.8rem", color: "var(--ink-60)" }}>
          ${summary.solver_notes}
        </div>
      ` : null}
    </div>
  `;
}
