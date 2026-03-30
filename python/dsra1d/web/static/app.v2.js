/**
 * StrataWave v2 — App Shell
 *
 * Clean, modular architecture:
 *   app.v2.js          → App shell (this file, ~180 lines)
 *   modules/wizard.js  → 5-step wizard
 *   modules/profile-editor.js → Layer table + calibration
 *   modules/motion-panel.js   → Motion upload/preview
 *   modules/results-viewer.js → 6-tab results display
 *   modules/charts.js  → SVG chart components
 *   modules/api.js     → Fetch wrappers
 *   modules/utils.js   → Formatting, constants
 */
import { html, useState, useEffect, useCallback, createRoot } from "./modules/setup.js";

import { Wizard } from "./modules/wizard.js";
import { ResultsViewer } from "./modules/results-viewer.js";
import * as api from "./modules/api.js";
import { defaultLayer, computeGmax } from "./modules/utils.js";

// ── Initial State ────────────────────────────────────────

const WIZARD_STORAGE_KEY = "stratawave_wizard_v1";

function defaultWizardState() {
  const layer1 = defaultLayer(0);
  layer1.material_params.gmax = computeGmax(layer1.vs, layer1.unit_weight);
  return {
    project_name: "",
    solver_backend: "eql",
    boundary_condition: "rigid",
    damping_mode: "frequency_independent",
    dt: 0.005,
    f_max: 25,
    max_iterations: 15,
    convergence_tol: 0.03,
    strain_ratio: 0.65,
    nonlinear_substeps: 4,
    viscous_damping_update: true,
    motion_path: "",
    motion_units: "m/s2",
    scale_mode: "none",
    layers: [layer1],
  };
}

function initialWizard() {
  try {
    const saved = localStorage.getItem(WIZARD_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // Exclude motion_path — server-side path may be stale across sessions
      parsed.motion_path = "";
      if (parsed.layers && parsed.layers.length > 0) return parsed;
    }
  } catch { /* ignore parse errors */ }
  return defaultWizardState();
}

// ── App Component ────────────────────────────────────────

function App() {
  const [wizard, setWizard] = useState(initialWizard);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [signals, setSignals] = useState(null);
  const [summary, setSummary] = useState(null);
  const [hysteresis, setHysteresis] = useState(null);
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [progress, setProgress] = useState(0);  // 0-100
  const [error, setError] = useState(null);

  const outputRoot = "out/web";

  // Persist wizard state to localStorage (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      try { localStorage.setItem(WIZARD_STORAGE_KEY, JSON.stringify(wizard)); } catch { /* quota exceeded */ }
    }, 500);
    return () => clearTimeout(timer);
  }, [wizard]);

  const resetWizard = useCallback(() => {
    localStorage.removeItem(WIZARD_STORAGE_KEY);
    setWizard(defaultWizardState());
    setActiveStep(0);
  }, []);

  // Load runs on mount
  useEffect(() => {
    api.fetchRuns(outputRoot).then(data => {
      const runList = Array.isArray(data) ? data : (data.runs || []);
      setRuns(runList);
      if (runList.length > 0) {
        setSelectedRunId(runList[0].run_id);
      }
    }).catch(() => {});
  }, []);

  // Delete a run
  const handleDeleteRun = useCallback(async (runId) => {
    try {
      await api.deleteRun(runId, outputRoot);
      setRuns(prev => prev.filter(r => r.run_id !== runId));
      if (selectedRunId === runId) {
        setSelectedRunId(null);
        setSignals(null); setSummary(null); setHysteresis(null); setProfile(null);
      }
    } catch (ex) { setError("Delete failed: " + ex.message); }
  }, [selectedRunId]);

  // Load run data when selection changes
  useEffect(() => {
    if (!selectedRunId) return;
    Promise.all([
      api.fetchSignals(selectedRunId, outputRoot).catch(() => null),
      api.fetchResultSummary(selectedRunId, outputRoot).catch(() => null),
      api.fetchHysteresis(selectedRunId, outputRoot).catch(() => null),
      api.fetchProfileSummary(selectedRunId, outputRoot).catch(() => null),
    ]).then(([sig, sum, hyst, prof]) => {
      setSignals(sig);
      setSummary(sum);
      setHysteresis(hyst);
      setProfile(prof);
    });
  }, [selectedRunId]);

  // Run analysis (single or batch)
  const handleRun = useCallback(async () => {
    setStatus("running");
    setProgress(0);
    setError(null);

    const batchMotions = wizard.batch_motions && wizard.batch_motions.length > 1
      ? wizard.batch_motions
      : [wizard.motion_path || ""];
    const isBatch = batchMotions.length > 1;

    try {
      // Step 0: Sanity check (5%)
      setProgress(5);
      const sanity = await api.wizardSanityCheck(wizard);
      if (!sanity.ok) {
        throw new Error((sanity.blockers || []).join("; ") || "Server-side validation failed.");
      }

      // Step 1: Generate config (10%)
      setProgress(10);
      const configResp = await api.generateConfig(wizard);
      const configPath = configResp.config_path || configResp.path;

      let lastRunId = null;
      for (let i = 0; i < batchMotions.length; i++) {
        const motionPath = batchMotions[i];
        const pct = 15 + Math.round((i / batchMotions.length) * 75);
        setProgress(pct);
        if (isBatch) setError(`Running ${i + 1}/${batchMotions.length}...`);

        const runResp = await api.executeRun({
          config_path: configPath,
          motion_path: motionPath,
          output_root: outputRoot,
          backend: wizard.solver_backend,
        });
        lastRunId = runResp.run_id;
      }

      // Done
      setProgress(95);
      setSelectedRunId(lastRunId);
      setViewMode("results");
      const runsData = await api.fetchRuns(outputRoot);
      setRuns(Array.isArray(runsData) ? runsData : (runsData.runs || []));
      setProgress(100);
      setStatus("done");
      setError(isBatch ? `Batch complete: ${batchMotions.length} runs` : null);
    } catch (ex) {
      setError(ex.message);
      setStatus("error");
      setProgress(0);
    }
  }, [wizard]);

  const [activeStep, setActiveStep] = useState(0);
  const [viewMode, setViewMode] = useState("wizard"); // "wizard" or "results"
  const [runFilter, setRunFilter] = useState("");
  const [theme, setTheme] = useState(() => localStorage.getItem("stratawave_theme") || "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("stratawave_theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(t => t === "dark" ? "light" : "dark");
  }, []);

  return html`
    <div className="shell">
      <header className="header">
        <h1 className="logo">StrataWave</h1>
        <span className="tagline">1D Site Response Analysis</span>
        <div className="header-actions">
          <button className=${"header-tab" + (viewMode === "wizard" ? " active" : "")}
            onClick=${() => setViewMode("wizard")}>Model</button>
          <button className=${"header-tab" + (viewMode === "results" ? " active" : "")}
            onClick=${() => setViewMode("results")}>Results</button>
          <button className="theme-toggle" onClick=${toggleTheme}
            title=${theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            ${theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <div className="main-layout-3col">
        <!-- Col 1: Navigation -->
        <nav className="nav-rail">
          <div className="nav-section">
            <div className="nav-label">WIZARD</div>
            ${(() => {
              // Step completion status
              const hasLayers = wizard.layers && wizard.layers.length > 0;
              const hasMotion = !!wizard.motion_path;
              const stepStatus = [
                wizard.solver_backend ? "ok" : "pending",        // 1. Analysis Type
                hasLayers ? "ok" : "pending",                     // 2. Soil Profile
                hasMotion ? "ok" : "pending",                     // 3. Input Motion
                "ok",                                             // 4. Damping (always has defaults)
                hasLayers && hasMotion ? "ok" : "blocked",        // 5. Analysis Control
              ];
              return ["Analysis Type", "Soil Profile", "Input Motion", "Damping", "Analysis Control"].map((label, i) => html`
              <button key=${i}
                className=${"nav-btn" + (viewMode === "wizard" && activeStep === i ? " active" : "")}
                onClick=${() => { setViewMode("wizard"); setActiveStep(i); }}>
                <span className=${"nav-num" + (stepStatus[i] === "ok" ? " step-ok" : stepStatus[i] === "blocked" ? " step-blocked" : "")}>${stepStatus[i] === "ok" ? "\u2713" : i + 1}</span>
                <span className="nav-text">${label}</span>
              </button>
            `);
            })()}
          </div>

          <div className="nav-divider" />

          <div className="nav-section nav-runs-section">
            <div className="nav-label">RUNS (${runs.length})</div>
            ${runs.length > 5 ? html`
              <input type="text" className="nav-search" placeholder="Filter..."
                value=${runFilter} onInput=${e => setRunFilter(e.target.value)}
                style=${{ fontSize: "0.7rem", padding: "0.2rem 0.4rem", margin: "0 0.5rem 0.25rem", width: "calc(100% - 1rem)", border: "1px solid var(--ink-10)", borderRadius: "4px" }} />
            ` : null}
            ${(() => {
              const now = new Date();
              const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
              const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
              const weekAgo = new Date(today); weekAgo.setDate(today.getDate() - 7);
              const filterLc = runFilter.toLowerCase();
              const filtered = runs.filter(r => {
                if (!filterLc) return true;
                const backend = (r.solver_backend || r.backend || "").toLowerCase();
                const rid = r.run_id.toLowerCase();
                return backend.includes(filterLc) || rid.includes(filterLc);
              });
              const groups = { "Today": [], "Yesterday": [], "This Week": [], "Older": [] };
              for (const r of filtered) {
                const ts = r.timestamp_utc || r.timestamp || "";
                const d = ts ? new Date(ts) : null;
                if (d && d >= today) groups["Today"].push(r);
                else if (d && d >= yesterday) groups["Yesterday"].push(r);
                else if (d && d >= weekAgo) groups["This Week"].push(r);
                else groups["Older"].push(r);
              }
              return Object.entries(groups).filter(([, arr]) => arr.length > 0).map(([label, arr]) => html`
                <div key=${label}>
                  <div className="nav-group-label" style=${{ fontSize: "0.6rem", color: "var(--ink-40)", padding: "0.25rem 0.75rem 0.1rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>${label}</div>
                  ${arr.map(r => {
                    const ts = r.timestamp_utc || r.timestamp || "";
                    const dateLabel = ts ? new Date(ts).toLocaleString("tr-TR", { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" }) : r.run_id.slice(4, 12);
                    const runLabel = "run_" + dateLabel;
                    return html`
                      <div key=${r.run_id} className=${"nav-btn nav-run" + (r.run_id === selectedRunId ? " active" : "")}
                        style=${{ display: "flex", alignItems: "center", cursor: "pointer" }}>
                        <div style=${{ flex: 1 }} onClick=${() => { setSelectedRunId(r.run_id); setViewMode("results"); }}>
                          <span className="nav-text run-text">${runLabel}</span>
                          <span className="nav-badge">${r.solver_backend || r.backend || ""}</span>
                        </div>
                        <button className="btn-icon" title="Delete run"
                          style=${{ fontSize: "0.65rem", opacity: 0.4, padding: "0 0.2rem" }}
                          onClick=${(e) => { e.stopPropagation(); handleDeleteRun(r.run_id); }}>✕</button>
                      </div>
                    `;
                  })}
                </div>
              `);
            })()}
          </div>

          ${status === "running" ? html`
            <div className="nav-progress">
              <div className="progress-bar">
                <div className="progress-fill" style=${{ width: progress + "%" }} />
              </div>
              <span className="muted">${progress}% Running...</span>
            </div>
          ` : null}

          ${status === "done" ? html`
            <div className="nav-section" style=${{ padding: "0.5rem 0.75rem" }}>
              <span style=${{ color: "var(--green)", fontSize: "0.75rem" }}>Analysis complete</span>
            </div>
          ` : null}

          ${error ? html`<div className="nav-error">${error}</div>` : null}
        </nav>

        <!-- Col 2+3: Content -->
        <main className="content-area">
          ${viewMode === "wizard" ? html`
            <${Wizard}
              wizard=${wizard}
              setWizard=${setWizard}
              onRun=${handleRun}
              status=${status}
              activeStep=${activeStep}
              setActiveStep=${setActiveStep}
              onReset=${resetWizard}
            />
          ` : html`
            <${ResultsViewer}
              runId=${selectedRunId}
              signals=${signals}
              summary=${summary}
              hysteresis=${hysteresis}
              runs=${runs}
              profile=${profile}
              outputRoot=${outputRoot}
            />
          `}
        </main>
      </div>
    </div>
  `;
}

// ── Mount ────────────────────────────────────────────────

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(html`<${App} />`);
}
