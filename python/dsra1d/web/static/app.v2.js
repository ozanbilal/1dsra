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

  // Run analysis
  const handleRun = useCallback(async () => {
    setStatus("running");
    setProgress(0);
    setError(null);
    try {
      // Step 1: Generate config (10%)
      setProgress(10);
      const configResp = await api.generateConfig(wizard);
      const configPath = configResp.config_path || configResp.path;

      // Step 2: Submit run (30%)
      setProgress(30);
      const runResp = await api.executeRun({
        config_path: configPath,
        motion_path: wizard.motion_path || "",
        output_root: outputRoot,
        backend: wizard.solver_backend,
      });

      // Step 3: Run completed (90%)
      setProgress(90);
      const newRunId = runResp.run_id;
      setSelectedRunId(newRunId);
      setViewMode("results");

      // Step 4: Refresh list (100%)
      const runsData = await api.fetchRuns(outputRoot);
      const refreshedRuns = Array.isArray(runsData) ? runsData : (runsData.runs || []);
      setRuns(refreshedRuns);
      setProgress(100);
      setStatus("done");
    } catch (ex) {
      setError(ex.message);
      setStatus("error");
      setProgress(0);
    }
  }, [wizard]);

  const [activeStep, setActiveStep] = useState(0);
  const [viewMode, setViewMode] = useState("wizard"); // "wizard" or "results"

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
        </div>
      </header>

      <div className="main-layout-3col">
        <!-- Col 1: Navigation -->
        <nav className="nav-rail">
          <div className="nav-section">
            <div className="nav-label">WIZARD</div>
            ${["Analysis Type", "Soil Profile", "Input Motion", "Damping", "Analysis Control"].map((label, i) => html`
              <button key=${i}
                className=${"nav-btn" + (viewMode === "wizard" && activeStep === i ? " active" : "")}
                onClick=${() => { setViewMode("wizard"); setActiveStep(i); }}>
                <span className="nav-num">${i + 1}</span>
                <span className="nav-text">${label}</span>
              </button>
            `)}
          </div>

          <div className="nav-divider" />

          <div className="nav-section">
            <div className="nav-label">RUNS</div>
            ${runs.slice(0, 15).map(r => {
              const ts = r.timestamp_utc || r.timestamp || "";
              const dateLabel = ts ? new Date(ts).toLocaleString("tr-TR", { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" }) : r.run_id.slice(4, 12);
              const runLabel = "run_" + dateLabel;
              return html`
                <button key=${r.run_id}
                  className=${"nav-btn nav-run" + (r.run_id === selectedRunId ? " active" : "")}
                  onClick=${() => { setSelectedRunId(r.run_id); setViewMode("results"); }}>
                  <span className="nav-text run-text">${runLabel}</span>
                  <span className="nav-badge">${r.solver_backend || r.backend || ""}</span>
                </button>
              `;
            })}
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
