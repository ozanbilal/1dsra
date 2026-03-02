import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);

function miniFormat(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Number(value).toFixed(4);
}

function safeMax(values) {
  if (!Array.isArray(values) || values.length === 0) return null;
  return values.reduce((acc, v) => (v > acc ? v : acc), values[0]);
}

function safeMin(values) {
  if (!Array.isArray(values) || values.length === 0) return null;
  return values.reduce((acc, v) => (v < acc ? v : acc), values[0]);
}

function maxAbs(values) {
  if (!Array.isArray(values) || values.length === 0) return null;
  return values.reduce((acc, v) => {
    const a = Math.abs(v);
    return a > acc ? a : acc;
  }, Math.abs(values[0]));
}

function buildPolyline(xs, ys) {
  if (!Array.isArray(xs) || !Array.isArray(ys)) return "";
  if (!xs.length || xs.length !== ys.length) return "";
  const pad = 16;
  const width = 1000;
  const height = 300;
  let xMin = Math.min(...xs);
  let xMax = Math.max(...xs);
  let yMin = Math.min(...ys);
  let yMax = Math.max(...ys);
  if (xMax - xMin < 1e-12) xMax = xMin + 1.0;
  if (yMax - yMin < 1e-12) yMax = yMin + 1.0;

  const points = xs.map((x, idx) => {
    const y = ys[idx];
    const px = pad + ((x - xMin) / (xMax - xMin)) * (width - 2 * pad);
    const py = height - pad - ((y - yMin) / (yMax - yMin)) * (height - 2 * pad);
    return `${px.toFixed(2)},${py.toFixed(2)}`;
  });
  return points.join(" ");
}

function PlotCard({ title, x, y, color, subtitle }) {
  const polyline = useMemo(() => buildPolyline(x, y), [x, y]);
  return html`
    <section className="chart-card">
      <h4>${title}</h4>
      ${subtitle && html`<div className="muted">${subtitle}</div>`}
      ${polyline
        ? html`
            <svg viewBox="0 0 1000 300" role="img" aria-label=${title}>
              <rect x="0" y="0" width="1000" height="300" fill="transparent"></rect>
              <polyline
                fill="none"
                stroke=${color || "rgb(164,83,35)"}
                stroke-width="2"
                points=${polyline}
              ></polyline>
            </svg>
          `
        : html`<div className="muted">No data</div>`}
    </section>
  `;
}

function App() {
  const [outputRoot, setOutputRoot] = useState("");
  const [configPath, setConfigPath] = useState("examples/configs/effective_stress_strict_plus.yml");
  const [motionPath, setMotionPath] = useState("examples/motions/sample_motion.csv");
  const [templates, setTemplates] = useState(["effective-stress"]);
  const [templateName, setTemplateName] = useState("effective-stress");
  const [templateOutDir, setTemplateOutDir] = useState("out/ui/configs");
  const [templateFileName, setTemplateFileName] = useState("effective_stress_ui.yml");
  const [createdConfigPath, setCreatedConfigPath] = useState("");
  const [backend, setBackend] = useState("config");
  const [openseesExe, setOpenseesExe] = useState("");
  const [runs, setRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [signal, setSignal] = useState(null);
  const [status, setStatus] = useState("");
  const [statusClass, setStatusClass] = useState("status");

  function querySuffix() {
    return outputRoot ? `?output_root=${encodeURIComponent(outputRoot)}` : "";
  }

  function defaultTemplateFileName(template) {
    return `${String(template).replace(/[^a-zA-Z0-9]+/g, "_")}_ui.yml`;
  }

  function withRoot(path) {
    const suffix = querySuffix();
    if (!suffix) return path;
    if (path.includes("?")) return `${path}&${suffix.slice(1)}`;
    return `${path}${suffix}`;
  }

  async function loadRuns() {
    setStatus("Loading runs...");
    setStatusClass("status");
    const res = await fetch(`/api/runs${querySuffix()}`);
    if (!res.ok) {
      setStatusClass("status err");
      setStatus(`Failed to list runs: HTTP ${res.status}`);
      return;
    }
    const data = await res.json();
    setRuns(data);
    if (data.length === 0) {
      setActiveRun(null);
      setSignal(null);
      setStatus("No runs found in selected output root.");
      return;
    }
    setActiveRun((prev) => {
      if (!prev) return data[0];
      const hit = data.find((item) => item.run_id === prev.run_id);
      return hit || data[0];
    });
    setStatus(`Loaded ${data.length} run(s).`);
  }

  async function loadSignals(runId) {
    const res = await fetch(withRoot(`/api/runs/${encodeURIComponent(runId)}/signals`));
    if (!res.ok) {
      setStatusClass("status err");
      setStatus(`Signal fetch failed for ${runId}: HTTP ${res.status}`);
      setSignal(null);
      return;
    }
    const data = await res.json();
    setSignal(data);
    setStatusClass("status");
    setStatus(`Loaded signal payload for ${runId} (${data.time_s.length} points).`);
  }

  async function runAnalysis() {
    if (!configPath || !motionPath) {
      setStatusClass("status warn");
      setStatus("config_path and motion_path are required.");
      return;
    }
    setStatusClass("status");
    setStatus("Running analysis...");
    const payload = {
      config_path: configPath,
      motion_path: motionPath,
      output_root: outputRoot || "out/web",
      backend,
      opensees_executable: openseesExe || null,
    };
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text();
      setStatusClass("status err");
      setStatus(`Run failed: HTTP ${res.status}\n${errText}`);
      return;
    }
    const run = await res.json();
    setStatusClass(run.status === "ok" ? "status" : "status warn");
    setStatus(`Run finished: ${run.run_id} | ${run.message}`);
    await loadRuns();
  }

  async function loadTemplates() {
    const res = await fetch("/api/config/templates");
    if (!res.ok) return;
    const payload = await res.json();
    if (!Array.isArray(payload.templates) || payload.templates.length === 0) return;
    setTemplates(payload.templates);
    setTemplateName((prev) => {
      if (payload.templates.includes(prev)) return prev;
      const first = payload.templates[0];
      setTemplateFileName(defaultTemplateFileName(first));
      return first;
    });
  }

  async function createTemplateConfig() {
    setStatusClass("status");
    setStatus("Creating model config template...");
    const res = await fetch("/api/config/template", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template: templateName,
        output_dir: templateOutDir,
        file_name: templateFileName,
      }),
    });
    if (!res.ok) {
      const errText = await res.text();
      setStatusClass("status err");
      setStatus(`Template create failed: HTTP ${res.status}\n${errText}`);
      return;
    }
    const data = await res.json();
    setCreatedConfigPath(data.config_path);
    setConfigPath(data.config_path);
    setStatusClass("status");
    setStatus(`Template created: ${data.config_path}`);
  }

  useEffect(() => {
    loadRuns().catch((err) => {
      setStatusClass("status err");
      setStatus(`Load error: ${String(err)}`);
    });
    loadTemplates().catch(() => {});
  }, []);

  useEffect(() => {
    if (!activeRun?.run_id) return;
    loadSignals(activeRun.run_id).catch((err) => {
      setStatusClass("status err");
      setStatus(`Signal error: ${String(err)}`);
    });
  }, [activeRun?.run_id, outputRoot]);

  const metrics = useMemo(() => {
    const pga = signal ? (maxAbs(signal.surface_acc_m_s2) ?? activeRun?.pga) : activeRun?.pga;
    const ruMax = signal ? (safeMax(signal.ru) ?? activeRun?.ru_max) : activeRun?.ru_max;
    const duMax = signal
      ? (safeMax(signal.delta_u) ?? activeRun?.delta_u_max)
      : activeRun?.delta_u_max;
    const sigmaMin = signal
      ? (safeMin(signal.sigma_v_eff) ?? activeRun?.sigma_v_eff_min)
      : activeRun?.sigma_v_eff_min;
    return {
      pga,
      ruMax,
      duMax,
      sigmaMin,
      dt: signal?.dt_s ?? null,
      sigmaRef: signal?.sigma_v_ref ?? null,
    };
  }, [signal, activeRun]);

  const links = useMemo(() => {
    if (!activeRun?.run_id) {
      return { surfaceCsv: "", h5: "", sqlite: "", out: "", meta: "" };
    }
    const id = encodeURIComponent(activeRun.run_id);
    return {
      surfaceCsv: withRoot(`/api/runs/${id}/surface-acc.csv`),
      pwpCsv: withRoot(`/api/runs/${id}/pwp-effective.csv`),
      h5: withRoot(`/api/runs/${id}/download/results.h5`),
      sqlite: withRoot(`/api/runs/${id}/download/results.sqlite`),
      out: withRoot(`/api/runs/${id}/download/surface_acc.out`),
      meta: withRoot(`/api/runs/${id}/download/run_meta.json`),
    };
  }, [activeRun?.run_id, outputRoot]);

  return html`
    <div className="shell">
      <header className="hero">
        <h1>1DSRA Web Studio</h1>
        <p>
          FastAPI + React dashboard. Select a run to inspect surface acceleration,
          PSA, transfer function, pore pressure ratio and effective stress proxies.
        </p>
      </header>

      <section className="layout">
        <aside className="panel">
          <h2>Control</h2>
          <div className="builder">
            <h3>Model Builder</h3>
            <div className="field">
              <label>Template</label>
              <select
                value=${templateName}
                onInput=${(e) => {
                  const value = e.target.value;
                  setTemplateName(value);
                  setTemplateFileName(defaultTemplateFileName(value));
                }}
              >
                ${templates.map((tpl) => html`<option value=${tpl}>${tpl}</option>`)}
              </select>
            </div>
            <div className="field">
              <label>Config Output Dir</label>
              <input
                value=${templateOutDir}
                onInput=${(e) => setTemplateOutDir(e.target.value)}
                placeholder="out/ui/configs"
              />
            </div>
            <div className="field">
              <label>Config File Name</label>
              <input
                value=${templateFileName}
                onInput=${(e) => setTemplateFileName(e.target.value)}
                placeholder="effective_stress_ui.yml"
              />
            </div>
            <div className="row">
              <button className="btn-main" onClick=${createTemplateConfig}>Create Model Config</button>
            </div>
            ${createdConfigPath
              ? html`<div className="muted" style=${{ marginTop: "6px" }}>Created: ${createdConfigPath}</div>`
              : null}
          </div>
          <div className="divider"></div>
          <div className="field">
            <label>Output Root (optional)</label>
            <input
              value=${outputRoot}
              onInput=${(e) => setOutputRoot(e.target.value)}
              placeholder="H:\\...\\1DSRA\\out\\ui"
            />
          </div>
          <div className="field">
            <label>Config Path</label>
            <input value=${configPath} onInput=${(e) => setConfigPath(e.target.value)} />
          </div>
          <div className="field">
            <label>Motion Path</label>
            <input value=${motionPath} onInput=${(e) => setMotionPath(e.target.value)} />
          </div>
          <div className="field">
            <label>Backend</label>
            <select value=${backend} onInput=${(e) => setBackend(e.target.value)}>
              <option value="config">config</option>
              <option value="auto">auto</option>
              <option value="opensees">opensees</option>
              <option value="mock">mock</option>
              <option value="linear">linear</option>
              <option value="eql">eql</option>
              <option value="nonlinear">nonlinear</option>
            </select>
          </div>
          <div className="field">
            <label>OpenSees Executable (optional)</label>
            <input
              value=${openseesExe}
              onInput=${(e) => setOpenseesExe(e.target.value)}
              placeholder="OpenSees"
            />
          </div>
          <div className="row">
            <button className="btn-main" onClick=${runAnalysis}>Run Analysis</button>
            <button className="btn-sub" onClick=${loadRuns}>Refresh</button>
          </div>
          <p className=${statusClass}>${status}</p>
          <p className="foot">
            Flow: first create model config from template, then set motion path and run.
          </p>
        </aside>

        <main className="panel">
          <h2>Runs</h2>
          <div className="cards">
            ${runs.map(
              (run) => html`
                <div
                  className=${`run-card ${activeRun?.run_id === run.run_id ? "active" : ""}`}
                  onClick=${() => setActiveRun(run)}
                >
                  <div className="run-id">${run.run_id}</div>
                  <div>
                    <span className=${`chip ${run.status === "ok" ? "chip-ok" : "chip-bad"}`}>
                      ${run.status}
                    </span>
                    <span className="chip chip-ok">${run.solver_backend}</span>
                  </div>
                  <div className="muted">PGA: ${miniFormat(run.pga)} m/s2</div>
                  <div className="muted">ru_max: ${miniFormat(run.ru_max)}</div>
                </div>
              `
            )}
          </div>

          ${activeRun
            ? html`
                <section className="detail-wrap">
                  <div className="metric-grid">
                    <div className="metric-card">
                      <div className="metric-label">PGA (m/s2)</div>
                      <div className="metric-value">${miniFormat(metrics.pga)}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">ru_max</div>
                      <div className="metric-value">${miniFormat(metrics.ruMax)}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">delta_u_max</div>
                      <div className="metric-value">${miniFormat(metrics.duMax)}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">sigma_v_eff_min</div>
                      <div className="metric-value">${miniFormat(metrics.sigmaMin)}</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-label">dt (s)</div>
                      <div className="metric-value">${miniFormat(metrics.dt)}</div>
                    </div>
                  </div>

                  <div className="download-row">
                    <a className="btn-min" href=${links.surfaceCsv}>surface_acc.csv</a>
                    <a className="btn-min" href=${links.pwpCsv}>pwp_effective.csv</a>
                    <a className="btn-min" href=${links.out}>surface_acc.out</a>
                    <a className="btn-min" href=${links.h5}>results.h5</a>
                    <a className="btn-min" href=${links.sqlite}>results.sqlite</a>
                    <a className="btn-min" href=${links.meta}>run_meta.json</a>
                  </div>

                  ${signal
                    ? html`
                        <section className="charts-grid">
                          <${PlotCard}
                            title=${`Surface Acc - ${activeRun.run_id}`}
                            x=${signal.time_s}
                            y=${signal.surface_acc_m_s2}
                            color="rgb(164,83,35)"
                            subtitle=${`backend=${activeRun.solver_backend} | status=${activeRun.status}`}
                          />
                          <${PlotCard}
                            title="PSA (5%)"
                            x=${signal.period_s}
                            y=${signal.psa_m_s2}
                            color="rgb(31,104,99)"
                            subtitle=${signal.spectra_source || "stored"}
                          />
                          <${PlotCard}
                            title="Transfer |H(f)|"
                            x=${signal.freq_hz}
                            y=${signal.transfer_abs}
                            color="rgb(71,68,125)"
                          />
                          <${PlotCard}
                            title="Pore Pressure Ratio (ru)"
                            x=${signal.ru_time_s}
                            y=${signal.ru}
                            color="rgb(47,58,66)"
                          />
                          <${PlotCard}
                            title="delta_u"
                            x=${signal.delta_u_time_s || signal.ru_time_s}
                            y=${signal.delta_u}
                            color="rgb(123,81,24)"
                          />
                          <${PlotCard}
                            title="sigma_v_eff"
                            x=${signal.sigma_v_eff_time_s || signal.ru_time_s}
                            y=${signal.sigma_v_eff}
                            color="rgb(24,110,120)"
                            subtitle=${`sigma_v_ref=${miniFormat(metrics.sigmaRef)}`}
                          />
                        </section>
                      `
                    : html`<div className="muted" style=${{ marginTop: "12px" }}>Signal not loaded.</div>`}
                </section>
              `
            : html`<div className="muted" style=${{ marginTop: "12px" }}>Select a run.</div>`}
        </main>
      </section>
    </div>
  `;
}

const root = createRoot(document.getElementById("app"));
root.render(html`<${App} />`);
