/**
 * GeoWave v2 — Results Viewer
 */
import { html, useState, useEffect } from "./setup.js";
import { ChartCard, MultiSeriesChart, DepthProfileChart } from "./charts.js";
import { fmt, RESULT_TABS, STANDARD_PERIODS } from "./utils.js";
import {
  excelExportUrl,
  downloadUrl,
  fetchSignals,
  fetchDisplacementAnimation,
  fetchResponseSpectraSummary,
} from "./api.js";
import { canUseFeature, ProGuard, TierBadge } from "./plans.js";

const G_STANDARD = 9.81;

function accelerationUnitLabel(unit) {
  return unit === "g" ? "g" : "m/s²";
}

function convertAccelerationValue(value, unit) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return unit === "g" ? numeric / G_STANDARD : numeric;
}

function convertAccelerationSeries(values, unit) {
  return (Array.isArray(values) ? values : []).map(v => convertAccelerationValue(v, unit));
}

const runTimestampFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function ResultsViewer({ runId, signals, summary, hysteresis, profile, outputRoot, runs, plan }) {
  const [activeTab, setActiveTab] = useState("time");
  const [selectedLayer, setSelectedLayer] = useState(0);
  const [compareRunId, setCompareRunId] = useState(null);
  const [accelUnit, setAccelUnit] = useState("g");
  const [compareSignals, setCompareSignals] = useState(null);
  const [spectraSummary, setSpectraSummary] = useState(null);
  const [spectraSummaryLoading, setSpectraSummaryLoading] = useState(false);
  const [spectraSummaryError, setSpectraSummaryError] = useState(null);
  const [displacementAnimation, setDisplacementAnimation] = useState(null);
  const [displacementLoading, setDisplacementLoading] = useState(false);
  const [displacementError, setDisplacementError] = useState(null);

  // Fetch compare run signals when compareRunId changes
  useEffect(() => {
    if (!compareRunId) { setCompareSignals(null); return; }
    fetchSignals(compareRunId, outputRoot).then(setCompareSignals).catch(() => setCompareSignals(null));
  }, [compareRunId, outputRoot]);

  useEffect(() => {
    if (!runId) {
      setSpectraSummary(null);
      setDisplacementAnimation(null);
      setSpectraSummaryError(null);
      setDisplacementError(null);
      return;
    }
    setSpectraSummaryLoading(true);
    setSpectraSummaryError(null);
    fetchResponseSpectraSummary(runId, outputRoot)
      .then((payload) => setSpectraSummary(payload))
      .catch((err) => {
        setSpectraSummary(null);
        setSpectraSummaryError(err?.message || "Failed to load response spectra summary.");
      })
      .finally(() => setSpectraSummaryLoading(false));
  }, [runId, outputRoot]);

  useEffect(() => {
    if (!runId || activeTab !== "displacement_animation" || displacementAnimation) return;
    setDisplacementLoading(true);
    setDisplacementError(null);
    fetchDisplacementAnimation(runId, outputRoot)
      .then((payload) => setDisplacementAnimation(payload))
      .catch((err) => {
        setDisplacementAnimation(null);
        setDisplacementError(err?.message || "Failed to load displacement animation.");
      })
      .finally(() => setDisplacementLoading(false));
  }, [activeTab, displacementAnimation, outputRoot, runId]);

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
        <div className="results-heading">
          <h3 className="results-title">Results</h3>
          <div className="results-run-id">${runId}</div>
          ${summary ? html`
            <div className="results-meta">
              ${summary.solver_backend ? html`<span className="results-meta-item"><span>Solver</span><b>${summary.solver_backend}</b></span>` : null}
              ${summary.project_name ? html`<span className="results-meta-item"><span>Project</span><b>${summary.project_name}</b></span>` : null}
              ${summary.input_motion ? html`<span className="results-meta-item results-meta-item-wide"><span>Motion</span><b>${summary.input_motion.split(/[/\\]/).pop()}</b></span>` : null}
              ${summary.status ? html`<span className="results-meta-item"><span>Status</span><b style=${{ color: summary.status === "ok" ? "var(--green)" : "var(--red)" }}>${summary.status}</b></span>` : null}
              ${signals?.site_period_s != null ? html`<span className="results-meta-item"><span>T₀</span><b>${fmt(signals.site_period_s, 3)}s</b></span>` : null}
              ${signals?.kappa != null ? html`<span className="results-meta-item"><span>κ</span><b>${fmt(signals.kappa, 5)}</b></span>` : null}
            </div>
          ` : null}
        </div>
        <div className="results-actions">
          <div className="results-unit-toggle" role="group" aria-label="Acceleration result units">
            <button
              type="button"
              className=${`results-unit-btn${accelUnit === "g" ? " active" : ""}`}
              onClick=${() => setAccelUnit("g")}>
              g
            </button>
            <button
              type="button"
              className=${`results-unit-btn${accelUnit === "m/s2" ? " active" : ""}`}
              onClick=${() => setAccelUnit("m/s2")}>
              m/s²
            </button>
          </div>
          ${canUseFeature(plan, "run_comparison") && runs && runs.length > 1 ? html`
            <label style=${{ display: "inline-flex", gap: "0.35rem", alignItems: "center", fontSize: "0.7rem", color: "var(--ink-60)" }}>
              <span>Compare Run</span>
              <select
                aria-label="Compare this run with another run"
                style=${{ fontSize: "0.7rem", padding: "0.15rem 0.3rem", borderRadius: "4px", border: "1px solid var(--border)" }}
                value=${compareRunId || ""}
                onChange=${e => setCompareRunId(e.target.value || null)}>
                <option value="">Compare with...</option>
                ${runs.filter(r => r.run_id !== runId).map(r => {
                  const ts = r.timestamp_utc || r.timestamp || "";
                  const label = ts ? "run_" + runTimestampFormatter.format(new Date(ts)) : r.run_id;
                  return html`<option key=${r.run_id} value=${r.run_id}>${label} (${r.solver_backend || ""})</option>`;
                })}
              </select>
            </label>
          ` : null}
          <a href=${downloadUrl(runId, "surface_acc.csv", outputRoot)} className="btn btn-sm" download>CSV</a>
          ${canUseFeature(plan, "excel_export") ? html`
            <a href=${excelExportUrl(runId, outputRoot, plan)} className="btn btn-sm btn-accent" download>Excel</a>
          ` : html`
            <span className="btn btn-sm" style=${{ opacity: 0.5, cursor: "not-allowed" }}>Excel <${TierBadge} feature="excel_export" /></span>
          `}
        </div>
      </div>

      <div className="tab-row">
        ${RESULT_TABS.map(tab => html`
          <button key=${tab.id} type="button"
            className=${"tab-btn" + (activeTab === tab.id ? " active" : "")}
            onClick=${() => setActiveTab(tab.id)}>
            ${tab.label}
          </button>
        `)}
      </div>

      <div className="results-content">
        ${activeTab === "time" && html`<${TimeHistoryTab}
          time=${time} surfAcc=${surfAcc} inputTime=${signals?.input_time_s} inputAcc=${inputAcc}
          pga=${signals?.pga} pgaInput=${signals?.pga_input}
          compareSignals=${compareSignals} compareRunId=${compareRunId}
          accelUnit=${accelUnit} />`}
        ${activeTab === "stress_strain" && html`<${StressStrainTab}
          hysteresis=${hysteresis} selectedLayer=${selectedLayer}
          onLayerChange=${setSelectedLayer} />`}
        ${activeTab === "spectral" && html`<${SpectralTab}
          psaPeriods=${psaPeriods} psaValues=${psaValues}
          inputPsaPeriods=${inputPsaPeriods} inputPsaValues=${inputPsaValues}
          transferFreq=${transferFreq} transferAbs=${transferAbs}
          fasFreq=${fasFreq} fasAmp=${fasAmp}
          compareSignals=${compareSignals} compareRunId=${compareRunId}
          plan=${plan} signals=${signals} accelUnit=${accelUnit} />`}
        ${activeTab === "spectra_summary" && html`<${SpectraSummaryTab}
          data=${spectraSummary}
          loading=${spectraSummaryLoading}
          error=${spectraSummaryError}
          accelUnit=${accelUnit} />`}
        ${activeTab === "displacement_animation" && html`<${DisplacementAnimationTab}
          data=${displacementAnimation}
          loading=${displacementLoading}
          error=${displacementError} />`}
        ${activeTab === "profile" && html`<${ProfileTab} profile=${profile} />`}
        ${activeTab === "mobilized" && html`<${MobilizedTab} hysteresis=${hysteresis} profile=${profile} />`}
        ${activeTab === "convergence" && html`<${ConvergenceTab} summary=${summary} />`}
      </div>
    </div>
  `;
}

// ── Tab Components ───────────────────────────────────────

function TimeHistoryTab({ time, surfAcc, inputTime, inputAcc, pga: pgaFromApi, pgaInput, compareSignals, compareRunId, accelUnit }) {
  if (!time || !surfAcc) return html`<p className="muted">No time history data.</p>`;

  const pga = pgaFromApi || Math.max(...surfAcc.map(Math.abs));
  const hasInput = inputAcc && inputAcc.length > 1;
  const hasCompare = compareSignals && compareSignals.time_s && compareSignals.surface_acc_m_s2;
  const accelLabel = accelerationUnitLabel(accelUnit);
  const altAccelUnit = accelUnit === "g" ? "m/s2" : "g";
  const altAccelLabel = accelerationUnitLabel(altAccelUnit);
  const surfaceSeriesY = convertAccelerationSeries(surfAcc, accelUnit);
  const inputSeriesY = hasInput ? convertAccelerationSeries(inputAcc, accelUnit) : null;
  const compareSeriesY = hasCompare
    ? convertAccelerationSeries(compareSignals.surface_acc_m_s2, accelUnit)
    : null;

  const resolvedInputTime = hasInput
    ? (inputTime && inputTime.length === inputAcc.length
      ? inputTime
      : inputAcc.map((_, i) => i * (time[time.length - 1] / Math.max(inputAcc.length - 1, 1))))
    : null;

  const series = [
    { x: time, y: surfaceSeriesY, label: "Surface", color: "var(--accent)" },
    ...(hasInput ? [{ x: resolvedInputTime, y: inputSeriesY, label: "Input Motion", color: "#2980B9" }] : []),
    ...(hasCompare ? [{ x: compareSignals.time_s, y: compareSeriesY, label: `Compare (${(compareRunId || "").slice(4, 12)})`, color: "#8E44AD" }] : []),
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
        <div className="metric-card"><span>Surface PGA (${accelLabel})</span><b>${fmt(convertAccelerationValue(pga, accelUnit), 4)}</b></div>
        <div className="metric-card"><span>Surface PGA (${altAccelLabel})</span><b>${fmt(convertAccelerationValue(pga, altAccelUnit), 4)}</b></div>
        ${hasInput ? html`
          <div className="metric-card"><span>Input PGA (${accelLabel})</span><b>${fmt(convertAccelerationValue(pgaInput || Math.max(...inputAcc.map(Math.abs)), accelUnit), 4)}</b></div>
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
        xLabel="Time (s)" yLabel=${`Acceleration (${accelLabel})`}
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
        <label htmlFor="stress-strain-layer-select">Layer:</label>
        <select id="stress-strain-layer-select" value=${selectedLayer} onChange=${e => onLayerChange(Number(e.target.value))}>
            ${hysteresis.layers.map((l, i) => html`
              <option key=${i} value=${i}>${l.layer_name || `Layer ${i + 1}`} (${l.material || "—"})</option>
            `)}
        </select>
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

function SpectralTab({ psaPeriods, psaValues, inputPsaPeriods, inputPsaValues, transferFreq, transferAbs, fasFreq, fasAmp, compareSignals, compareRunId, plan, signals, accelUnit }) {
  const [xScale, setXScale] = useState("log");
  const [yScale, setYScale] = useState("linear");
  const [periodMinInput, setPeriodMinInput] = useState("");
  const [periodMaxInput, setPeriodMaxInput] = useState("");

  useEffect(() => {
    if (!psaPeriods?.length) return;
    const minPeriod = Math.min(...psaPeriods.filter(v => Number.isFinite(v) && v > 0));
    const maxPeriod = Math.max(...psaPeriods.filter(v => Number.isFinite(v)));
    if (periodMinInput === "") setPeriodMinInput(String(fmt(minPeriod, 4)));
    if (periodMaxInput === "") setPeriodMaxInput(String(fmt(maxPeriod, 4)));
  }, [periodMaxInput, periodMinInput, psaPeriods]);

  if (!psaPeriods || !psaValues) {
    return html`<p className="muted">No spectral data available.</p>`;
  }

  const rawPeriodMin = Number(periodMinInput);
  const rawPeriodMax = Number(periodMaxInput);
  const fallbackMin = Math.min(...psaPeriods.filter(v => Number.isFinite(v) && v > 0));
  const fallbackMax = Math.max(...psaPeriods.filter(v => Number.isFinite(v)));
  const periodMin = Number.isFinite(rawPeriodMin) && rawPeriodMin > 0 ? rawPeriodMin : fallbackMin;
  const periodMax = Number.isFinite(rawPeriodMax) && rawPeriodMax > periodMin ? rawPeriodMax : fallbackMax;

  const hasInputPsa = inputPsaPeriods && inputPsaValues && inputPsaPeriods.length > 1;
  const hasCompare = compareSignals && compareSignals.period_s && compareSignals.psa_m_s2;
  const accelLabel = accelerationUnitLabel(accelUnit);
  const altAccelUnit = accelUnit === "g" ? "m/s2" : "g";
  const altAccelLabel = accelerationUnitLabel(altAccelUnit);
  const surfacePsaDisplay = convertAccelerationSeries(psaValues, accelUnit);
  const inputPsaDisplay = hasInputPsa ? convertAccelerationSeries(inputPsaValues, accelUnit) : null;
  const comparePsaDisplay = hasCompare
    ? convertAccelerationSeries(compareSignals.psa_m_s2, accelUnit)
    : null;
  const series = [
    { x: psaPeriods, y: surfacePsaDisplay, label: "Surface PSA", color: "#D35400" },
    ...(hasInputPsa ? [{ x: inputPsaPeriods, y: inputPsaDisplay, label: "Input PSA", color: "#2980B9" }] : []),
    ...(hasCompare ? [{ x: compareSignals.period_s, y: comparePsaDisplay, label: `Compare (${(compareRunId || "").slice(4, 12)})`, color: "#8E44AD" }] : []),
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
  const hasAmpRatioSeries = hasAmpRatio && ampRatioPeriods.length > 2;

  // PSA Summary Table at standard periods
  const surfAtStd = interpolateAtPeriods(psaPeriods, psaValues, STANDARD_PERIODS);
  const inputAtStd = hasInputPsa ? interpolateAtPeriods(inputPsaPeriods, inputPsaValues, STANDARD_PERIODS) : null;

  // T₀ vertical line for spectral charts
  const T0 = signals?.site_period_s;
  const t0Lines = T0 ? [{ x: T0, label: `T₀=${fmt(T0, 3)}s`, color: "#E74C3C" }] : [];

  return html`
    <div className="tab-content">
      <div className="results-toolbar results-toolbar-tight">
        <div className="spectral-controls spectral-controls-inline">
          <div className="spectral-control">
            <span className="spectral-control-label">X Scale</span>
            <div className="results-segmented" role="group" aria-label="Spectral chart x-axis scale">
              <button
                type="button"
                className=${`results-segmented-btn${xScale === "linear" ? " active" : ""}`}
                onClick=${() => setXScale("linear")}>
                Arithmetic
              </button>
              <button
                type="button"
                className=${`results-segmented-btn${xScale === "log" ? " active" : ""}`}
                onClick=${() => setXScale("log")}>
                Log
              </button>
            </div>
          </div>
          <div className="spectral-control">
            <span className="spectral-control-label">Y Scale</span>
            <div className="results-segmented" role="group" aria-label="Spectral chart y-axis scale">
              <button
                type="button"
                className=${`results-segmented-btn${yScale === "linear" ? " active" : ""}`}
                onClick=${() => setYScale("linear")}>
                Arithmetic
              </button>
              <button
                type="button"
                className=${`results-segmented-btn${yScale === "log" ? " active" : ""}`}
                onClick=${() => setYScale("log")}>
                Log
              </button>
            </div>
          </div>
          <div className="field field-compact">
            <label>Period Min (s)</label>
            <input type="number" min="0.0001" step="0.0001" value=${periodMinInput} onInput=${e => setPeriodMinInput(e.target.value)} />
          </div>
          <div className="field field-compact">
            <label>Period Max (s)</label>
            <input type="number" min="0.001" step="0.001" value=${periodMaxInput} onInput=${e => setPeriodMaxInput(e.target.value)} />
          </div>
          <button
            type="button"
            className="btn btn-sm"
            onClick=${() => {
              setXScale("log");
              setYScale("linear");
              setPeriodMinInput(String(fmt(fallbackMin, 4)));
              setPeriodMaxInput(String(fmt(fallbackMax, 4)));
            }}>
            Reset View
          </button>
        </div>
      </div>
      <div className="results-chart-grid results-chart-grid-2">
        <${MultiSeriesChart}
          title="Response Spectra (5% damping)"
          series=${series}
          xLabel="Period (s)" yLabel=${`PSA (${accelLabel})`}
          logX=${xScale === "log"}
          logY=${yScale === "log"}
          xMin=${periodMin}
          xMax=${periodMax}
          yMin=${yScale === "log" ? undefined : 0}
          vLines=${t0Lines}
        />
        ${hasAmpRatioSeries ? html`
          <${ChartCard}
            title="Spectral Amplification Ratio (Surface / Input)"
            x=${ampRatioPeriods} y=${ampRatioValues}
            xLabel="Period (s)" yLabel="Amplification"
            color="#E74C3C" logX=${xScale === "log"}
            xMin=${periodMin}
            xMax=${periodMax}
            yMin=${0}
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
        ${fasFreq && fasAmp && fasFreq.length > 2 ? (() => {
          const kappaFitFreq = signals?.kappa_fit_freq;
          const kappaFitAmp = signals?.kappa_fit_amp;
          const hasKappaFit = kappaFitFreq && kappaFitAmp && kappaFitFreq.length === 2;
          const fasTitle = signals?.kappa != null ? `Fourier Amplitude Spectrum (κ = ${fmt(signals.kappa, 4)})` : "Fourier Amplitude Spectrum";
          if (hasKappaFit) {
            return html`
              <${MultiSeriesChart}
                title=${fasTitle}
                series=${[
                  { x: fasFreq, y: fasAmp, label: "FAS", color: "#16A085" },
                  { x: kappaFitFreq, y: kappaFitAmp, label: "κ fit (10-40 Hz)", color: "#E74C3C" },
                ]}
                xLabel="Frequency (Hz)" yLabel="Fourier Amplitude (m/s)"
                logX=${true}
              />
            `;
          }
          return html`
            <${ChartCard}
              title=${fasTitle}
              x=${fasFreq} y=${fasAmp}
              xLabel="Frequency (Hz)" yLabel="Fourier Amplitude (m/s)"
              color="#16A085" logX=${true}
            />
          `;
        })() : null}

        <!-- Pro Features -->
        ${(() => {
        const psv = signals?.psv_m_s;
        const psd = signals?.psd_m;
        const kappa = signals?.kappa;
        const kappaR2 = signals?.kappa_r2;
        const tfSmooth = signals?.transfer_abs_smooth;
        const T0 = signals?.site_period_s;
        const hasPro = psv || kappa != null || (tfSmooth && tfSmooth.length > 0);
        if (!hasPro) return null;

        return html`
          <${ProGuard} plan=${plan} feature="psv_psd">
            ${psv && psv.length > 2 ? html`
              <${ChartCard}
                title="Pseudo-Velocity Spectrum (PSV)"
                x=${psaPeriods} y=${psv}
                xLabel="Period (s)" yLabel="PSV (m/s)"
                color="#E67E22" logX=${true}
                xMin=${periodMin}
                xMax=${periodMax}
                vLines=${t0Lines}
              />
            ` : null}
            ${psd && psd.length > 2 ? html`
              <${ChartCard}
                title="Pseudo-Displacement Spectrum (PSD)"
                x=${psaPeriods} y=${psd}
                xLabel="Period (s)" yLabel="PSD (m)"
                color="#9B59B6" logX=${true}
                xMin=${periodMin}
                xMax=${periodMax}
                vLines=${t0Lines}
              />
            ` : null}
          <//>

          ${kappa != null ? html`
            <${ProGuard} plan=${plan} feature="kappa">
              <div className="metric-row" style=${{ marginTop: "0.5rem" }}>
                <div className="metric-card"><span>Kappa (κ)</span><b>${fmt(kappa, 5)}</b></div>
                <div className="metric-card"><span>κ R²</span><b>${fmt(kappaR2, 4)}</b></div>
                ${T0 != null ? html`<div className="metric-card"><span>Site Period T₀ (s)</span><b>${fmt(T0, 3)}</b></div>` : null}
                ${signals?.vs_avg_m_s != null ? html`<div className="metric-card"><span>Vs_avg (m/s)</span><b>${fmt(signals.vs_avg_m_s, 1)}</b></div>` : null}
              </div>
            <//>
          ` : null}

          ${tfSmooth && tfSmooth.length > 2 && transferFreq ? html`
            <${ProGuard} plan=${plan} feature="smoothed_tf">
              <${MultiSeriesChart}
                title="Transfer Function — Raw vs Smoothed"
                series=${[
                  { x: transferFreq, y: transferAbs, label: "Raw", color: "#BDC3C7" },
                  { x: transferFreq, y: tfSmooth, label: "Smoothed (KO b=40)", color: "#E74C3C" },
                ]}
                xLabel="Frequency (Hz)" yLabel="|H(f)|"
                logX=${true}
              />
            <//>
          ` : null}
        `;
        })()}
      </div>

      <div style=${{ marginTop: "0.75rem" }}>
        <h4 style=${{ fontSize: "0.85rem", marginBottom: "0.4rem" }}>PSA Summary at Standard Periods</h4>
        <div style=${{ maxHeight: "300px", overflowY: "auto" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th>Period (s)</th><th>Freq (Hz)</th>
                <th>${`Surface PSA (${accelLabel})`}</th><th>${`Surface PSA (${altAccelLabel})`}</th>
                ${hasInputPsa ? html`<th>${`Input PSA (${accelLabel})`}</th><th>Amp. Ratio</th>` : null}
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
                    <td>${sv != null ? fmt(convertAccelerationValue(sv, accelUnit), 4) : "—"}</td>
                    <td>${sv != null ? fmt(convertAccelerationValue(sv, altAccelUnit), 4) : "—"}</td>
                    ${hasInputPsa ? html`
                      <td>${iv != null ? fmt(convertAccelerationValue(iv, accelUnit), 4) : "—"}</td>
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

function SpectraSummaryTab({ data, loading, error, accelUnit }) {
  const rows = data?.rows || [];
  const [maxPeriodInput, setMaxPeriodInput] = useState("");
  const accelLabel = accelerationUnitLabel(accelUnit);
  const altAccelUnit = accelUnit === "g" ? "m/s2" : "g";
  const altAccelLabel = accelerationUnitLabel(altAccelUnit);

  useEffect(() => {
    if (!rows.length) {
      setMaxPeriodInput("");
      return;
    }
    const nextMax = Math.max(...rows.map(row => Number(row.period_s) || 0));
    setMaxPeriodInput(nextMax > 0 ? String(Number(nextMax.toFixed(4))) : "");
  }, [data]);

  if (loading) return html`<p className="muted">Loading response spectra summary...</p>`;
  if (error) return html`<p className="muted">${error}</p>`;
  if (!rows.length) return html`<p className="muted">No spectra summary data available.</p>`;

  const parsedMaxPeriod = Number(maxPeriodInput);
  const maxPeriod = Number.isFinite(parsedMaxPeriod) && parsedMaxPeriod > 0 ? parsedMaxPeriod : null;
  const visibleRows = maxPeriod != null
    ? rows.filter(row => (Number(row.period_s) || 0) <= maxPeriod)
    : rows;
  const summaryRows = visibleRows.filter(r => Number.isFinite(Number(r.period_s)) && r.surface_psa_m_s2 != null);
  const periods = summaryRows.map(r => Number(r.period_s));
  const ampSeries = visibleRows
    .filter(r => r.amplification_ratio != null)
    .map(r => ({ x: Number(r.period_s), y: Number(r.amplification_ratio) }));
  const ampPeriods = ampSeries.map(p => p.x);
  const ampValues = ampSeries.map(p => p.y);
  const visibleMaxSurfacePsa = visibleRows.length
    ? Math.max(...visibleRows.map(r => Number(r.surface_psa_m_s2) || 0))
    : null;
  const visibleMaxAmplification = visibleRows.length
    ? Math.max(...visibleRows.map(r => Number(r.amplification_ratio) || 0))
    : null;
  const summarySurfaceSeries = summaryRows.map(r =>
    convertAccelerationValue(Number(r.surface_psa_m_s2) || 0, accelUnit)
  );

  return html`
    <div className="tab-content">
      <div className="row" style=${{ alignItems: "end", marginBottom: "0.5rem" }}>
        <div className="field" style=${{ maxWidth: "240px" }}>
          <label htmlFor="spectra-summary-max-period">Spectrum Max Period (s)</label>
          <input
            id="spectra-summary-max-period"
            type="number"
            min="0.01"
            step="0.05"
            value=${maxPeriodInput}
            onInput=${e => setMaxPeriodInput(e.target.value)}
          />
        </div>
        <p className="muted" style=${{ margin: "0 0 0.35rem 0" }}>
          This limit only affects the Spectra Summary tab.
        </p>
      </div>
      <div className="metric-row">
        <div className="metric-card"><span>Visible Rows</span><b>${visibleRows.length}</b></div>
        <div className="metric-card"><span>Total Rows</span><b>${rows.length}</b></div>
        <div className="metric-card"><span>Damping</span><b>${fmt((data?.damping_ratio ?? 0.05) * 100, 2)}%</b></div>
        <div className="metric-card"><span>${`Max Surface PSA (${accelLabel})`}</span><b>${fmt(convertAccelerationValue(visibleMaxSurfacePsa ?? data?.max_surface_psa_m_s2, accelUnit), 4)}</b></div>
        <div className="metric-card"><span>Max Amplification</span><b>${fmt(visibleMaxAmplification ?? data?.max_amplification_ratio, 3)}</b></div>
      </div>
      <div className="results-chart-grid results-chart-grid-2">
        ${periods.length > 2 && summarySurfaceSeries.length > 2 ? html`
          <${ChartCard}
            title="Surface PSA Summary"
            x=${periods}
            y=${summarySurfaceSeries}
            xLabel="Period (s)"
            yLabel=${`Surface PSA (${accelLabel})`}
            color="#D35400"
            logX=${true}
            xMax=${maxPeriod ?? undefined}
            yMin=${0}
          />
        ` : null}
        ${ampPeriods.length > 2 ? html`
          <${ChartCard}
            title="Amplification Ratio Summary"
            x=${ampPeriods}
            y=${ampValues}
            xLabel="Period (s)"
            yLabel="Surface/Input"
            color="#8E44AD"
            logX=${true}
            xMax=${maxPeriod ?? undefined}
            yMin=${0}
          />
        ` : null}
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>Period (s)</th>
            <th>Freq (Hz)</th>
            <th>${`Surface PSA (${accelLabel})`}</th>
            <th>${`Surface PSA (${altAccelLabel})`}</th>
            <th>${`Input PSA (${accelLabel})`}</th>
            <th>Amp. Ratio</th>
          </tr>
        </thead>
        <tbody>
          ${visibleRows.map((row, idx) => html`
            <tr key=${`spectra-summary-${idx}`}>
              <td>${fmt(row.period_s, 3)}</td>
              <td>${fmt(row.frequency_hz, 3)}</td>
              <td>${row.surface_psa_m_s2 != null ? fmt(convertAccelerationValue(row.surface_psa_m_s2, accelUnit), 4) : "—"}</td>
              <td>${row.surface_psa_m_s2 != null ? fmt(convertAccelerationValue(row.surface_psa_m_s2, altAccelUnit), 4) : "—"}</td>
              <td>${row.input_psa_m_s2 != null ? fmt(convertAccelerationValue(row.input_psa_m_s2, accelUnit), 4) : "—"}</td>
              <td>${fmt(row.amplification_ratio, 3)}</td>
            </tr>
          `)}
        </tbody>
      </table>
    </div>
  `;
}

function DisplacementAnimationTab({ data, loading, error }) {
  const [frameIndex, setFrameIndex] = useState(0);
  const [displacementMode, setDisplacementMode] = useState("relative");

  useEffect(() => {
    const frameCount = data?.frame_time_s?.length || 0;
    setFrameIndex(frameCount > 0 ? frameCount - 1 : 0);
  }, [data?.frame_time_s?.length]);

  if (loading) return html`<p className="muted">Loading displacement animation...</p>`;
  if (error) return html`<p className="muted">${error}</p>`;

  const depth = data?.depth_m || [];
  const totalFrames = data?.displacement_cm || [];
  const relativeFrames = data?.relative_displacement_cm?.length
    ? data.relative_displacement_cm
    : totalFrames.map(frame => {
        const base = frame && frame.length ? Number(frame[frame.length - 1]) || 0 : 0;
        return (frame || []).map(v => (Number(v) || 0) - base);
      });
  const frameTimes = data?.frame_time_s || [];
  if (!depth.length || !totalFrames.length || !frameTimes.length) {
    return html`<p className="muted">No displacement animation data available.</p>`;
  }

  const clampedFrame = Math.max(0, Math.min(frameIndex, frameTimes.length - 1));
  const usingRelative = displacementMode === "relative";
  const frames = usingRelative ? relativeFrames : totalFrames;
  const profileDisp = frames[clampedFrame] || [];
  const surfaceSeries = frames.map(frame => frame && frame.length ? frame[0] : 0);
  const selectedFrameTime = frameTimes[clampedFrame] || 0;
  const flatDisp = frames.flat().map(v => Number(v) || 0);
  const peakAbsDisp = flatDisp.length
    ? Math.max(...flatDisp.map(v => Math.abs(v)), 1e-6)
    : 1;
  const profileXLimit = peakAbsDisp * 1.05;
  const peakSurfaceDispM = (
    Number(
      usingRelative
        ? data?.peak_surface_relative_displacement_cm
        : data?.peak_surface_displacement_cm
    ) || 0
  ) / 100;
  const peakProfileDispM = (
    Number(
      usingRelative
        ? data?.peak_profile_relative_displacement_cm
        : data?.peak_profile_displacement_cm
    ) || peakAbsDisp
  ) / 100;
  const profileDispM = profileDisp.map(v => (Number(v) || 0) / 100);
  const surfaceSeriesM = surfaceSeries.map(v => (Number(v) || 0) / 100);
  const modeLabel = usingRelative ? "Relative to Top of Rock" : "Total";
  const displacementLabel = usingRelative ? "Relative Displacement (m)" : "Displacement (m)";

  return html`
    <div className="tab-content">
      ${data?.note ? html`
        <div className=${`results-note-banner${data?.approximate ? " is-warn" : ""}`}>
          ${data.note}
        </div>
      ` : null}
      <div className="results-toolbar">
        <div className="results-segmented" role="group" aria-label="Displacement animation mode">
          <button
            type="button"
            className=${`results-segmented-btn${usingRelative ? " active" : ""}`}
            onClick=${() => setDisplacementMode("relative")}>
            Relative
          </button>
          <button
            type="button"
            className=${`results-segmented-btn${!usingRelative ? " active" : ""}`}
            onClick=${() => setDisplacementMode("total")}>
            Total
          </button>
        </div>
        <div className="results-toolbar-note">
          ${usingRelative
            ? "Relative mode subtracts total displacement at the top of rock, matching the manual's relative displacement convention."
            : "Total mode shows raw nodal displacement history from the solver output."}
        </div>
      </div>
      <div className="metric-row">
        <div className="metric-card"><span>Frames</span><b>${frameTimes.length}</b></div>
        <div className="metric-card"><span>Selected Time (s)</span><b>${fmt(selectedFrameTime, 3)}</b></div>
        <div className="metric-card"><span>${usingRelative ? "Peak Surface Relative Disp. (m)" : "Peak Surface Disp. (m)"}</span><b>${fmt(peakSurfaceDispM, 5)}</b></div>
        <div className="metric-card"><span>${usingRelative ? "Peak Profile Relative Disp. (m)" : "Peak Profile Disp. (m)"}</span><b>${fmt(peakProfileDispM, 5)}</b></div>
        <div className="metric-card"><span>Mode</span><b>${data?.approximate ? "Approximate" : "Recorded"}</b></div>
        <div className="metric-card"><span>Reference</span><b>${modeLabel}</b></div>
      </div>
      <div className="field" style=${{ maxWidth: "360px", marginBottom: "0.5rem" }}>
        <label htmlFor="disp-frame-slider">Animation Frame</label>
        <input
          id="disp-frame-slider"
          type="range"
          min="0"
          max=${Math.max(0, frameTimes.length - 1)}
          step="1"
          value=${clampedFrame}
          onInput=${e => setFrameIndex(Number(e.target.value))}
        />
      </div>
      <${DepthProfileChart}
        title="Displacement Profile at Selected Frame"
        subtitle=${`${modeLabel} · t = ${fmt(selectedFrameTime, 3)} s`}
        depths=${depth}
        values=${profileDispM}
        xLabel=${displacementLabel}
        yLabel="Depth (m)"
        color="#8E44AD"
        xMin=${-(profileXLimit / 100)}
        xMax=${profileXLimit / 100}
      />
      <${ChartCard}
        title="Surface Displacement Animation Track"
        subtitle=${data?.approximate
          ? `Integrated proxy response · ${modeLabel}`
          : `Recorded surface nodal displacement · ${modeLabel}`}
        x=${frameTimes}
        y=${surfaceSeriesM}
        xLabel="Time (s)"
        yLabel=${usingRelative ? "Surface Relative Displacement (m)" : "Surface Displacement (m)"}
        color="#D35400"
        vLines=${[{ x: selectedFrameTime, label: "Selected", color: "#2C3E50" }]}
      />
    </div>
  `;
}

function ProfileTab({ profile }) {
  if (!profile || !profile.layers || !profile.layers.length) {
    return html`<p className="muted">No profile data.</p>`;
  }

  // Build step-profile arrays for depth charts
  const depths = [];
  const vs = [];
  const gammaMax = [];
  const dampRatio = [];
  const tauPeak = [];
  const sigmaV0 = [];
  const ruMax = [];
  const impliedStrength = [];
  const normalizedStrength = [];
  const impliedFriction = [];
  let d = 0;
  for (const l of profile.layers) {
    const thick = l.thickness_m || l.thickness || 0;
    const vsVal = l.vs_m_s || l.vs || 0;
    const gm = l.gamma_max || 0;
    const dr = l.damping_ratio || 0;
    const tp = l.tau_peak_kpa || l.tau_peak || 0;
    const sv = l.sigma_v0_mid_kpa || 0;
    const ru = l.ru_max || 0;
    const imp = l.implied_strength_kpa || 0;
    const norm = l.normalized_implied_strength || 0;
    const phi = l.implied_friction_angle_deg || 0;
    depths.push(d); vs.push(vsVal); gammaMax.push(gm); dampRatio.push(dr); tauPeak.push(tp); sigmaV0.push(sv); ruMax.push(ru); impliedStrength.push(imp); normalizedStrength.push(norm); impliedFriction.push(phi);
    d += thick;
    depths.push(d); vs.push(vsVal); gammaMax.push(gm); dampRatio.push(dr); tauPeak.push(tp); sigmaV0.push(sv); ruMax.push(ru); impliedStrength.push(imp); normalizedStrength.push(norm); impliedFriction.push(phi);
  }

  const hasResponse = gammaMax.some(v => v > 0) || tauPeak.some(v => v > 0);
  const hasRu = ruMax.some(v => v > 0);
  const hasImplied =
    impliedStrength.some(v => v > 0) ||
    normalizedStrength.some(v => v > 0) ||
    impliedFriction.some(v => v > 0);

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
        ${hasImplied ? html`
          <${DepthProfileChart}
            title="Implied Strength" depths=${depths} values=${impliedStrength}
            xLabel="Implied Strength (kPa)" yLabel="Depth (m)" color="#D35400"
          />
          <${DepthProfileChart}
            title="Normalized Implied Strength" depths=${depths} values=${normalizedStrength}
            xLabel="τ/σ'v,mid" yLabel="Depth (m)" color="#8E44AD"
          />
          <${DepthProfileChart}
            title="Implied Friction Angle" depths=${depths} values=${impliedFriction}
            xLabel="φ (deg)" yLabel="Depth (m)" color="#27AE60"
          />
        ` : null}
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>#</th><th>Depth (m)</th><th>Thick (m)</th>
            <th>Vs (m/s)</th><th>γ_wt</th><th>Material</th>
            <th>γ_max (%)</th><th>τ_peak (kPa)</th>
            <th>Implied τ (kPa)</th><th>Norm. τ</th><th>Implied φ (deg)</th>
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
                <td>${l.implied_strength_kpa != null ? fmt(l.implied_strength_kpa, 1) : "—"}</td>
                <td>${l.normalized_implied_strength != null ? fmt(l.normalized_implied_strength, 3) : "—"}</td>
                <td>${l.implied_friction_angle_deg != null ? fmt(l.implied_friction_angle_deg, 2) : "—"}</td>
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
  const depths = [];
  const mobRatios = [];
  const gOverGmax = [];
  const dampingVals = [];
  const impliedStrength = [];
  const normalizedStrength = [];
  const impliedFriction = [];
  let d = 0;
  const profileLayers = profile?.layers || [];
  for (let i = 0; i < layers.length; i++) {
    const pl = profileLayers[i];
    const thick = pl ? (pl.thickness_m || pl.thickness || 1) : 1;
    const mob = layers[i].mobilized_strength_ratio || 0;
    const gg = layers[i].g_over_gmax || 0;
    const dp = layers[i].damping_proxy || 0;
    const imp = pl?.implied_strength_kpa || 0;
    const norm = pl?.normalized_implied_strength || 0;
    const phi = pl?.implied_friction_angle_deg || 0;
    depths.push(d); mobRatios.push(mob); gOverGmax.push(gg); dampingVals.push(dp); impliedStrength.push(imp); normalizedStrength.push(norm); impliedFriction.push(phi);
    d += thick;
    depths.push(d); mobRatios.push(mob); gOverGmax.push(gg); dampingVals.push(dp); impliedStrength.push(imp); normalizedStrength.push(norm); impliedFriction.push(phi);
  }
  const hasImplied =
    impliedStrength.some(v => v > 0) ||
    normalizedStrength.some(v => v > 0) ||
    impliedFriction.some(v => v > 0);

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
        ${hasImplied ? html`
          <${DepthProfileChart}
            title="Implied Strength Trend"
            depths=${depths} values=${impliedStrength}
            xLabel="Implied τ (kPa)" yLabel="Depth (m)" color="#D35400"
          />
          <${DepthProfileChart}
            title="Normalized Strength Trend"
            depths=${depths} values=${normalizedStrength}
            xLabel="τ/σ'v,mid" yLabel="Depth (m)" color="#8E44AD"
          />
          <${DepthProfileChart}
            title="Implied Friction Angle Trend"
            depths=${depths} values=${impliedFriction}
            xLabel="φ (deg)" yLabel="Depth (m)" color="#2C3E50"
          />
        ` : null}
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
  const eql = summary.eql_summary || (conv.iterations != null ? conv : null);

  // EQL convergence
  if (eql && eql.iterations != null) {
    const maxChangeLast = eql.max_change_last != null ? eql.max_change_last :
      (eql.max_change_history ? eql.max_change_history[eql.max_change_history.length - 1] : null);
    return html`
      <div className="tab-content">
        <div className="metric-row">
          <div className="metric-card"><span>Iterations</span><b>${eql.iterations}</b></div>
          <div className="metric-card"><span>Converged</span><b style=${{ color: eql.converged ? "#27AE60" : "#E74C3C" }}>${eql.converged ? "Yes" : "No"}</b></div>
          ${maxChangeLast != null ? html`
            <div className="metric-card"><span>Final Change</span><b>${fmt(maxChangeLast * 100, 2)}%</b></div>
          ` : null}
          ${eql.max_change_max != null ? html`
            <div className="metric-card"><span>Max Change</span><b>${fmt(eql.max_change_max * 100, 2)}%</b></div>
          ` : null}
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
