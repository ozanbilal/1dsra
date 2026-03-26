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

function initialWizard() {
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

// ── App Component ────────────────────────────────────────

function App() {
  const [wizard, setWizard] = useState(initialWizard);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [signals, setSignals] = useState(null);
  const [summary, setSummary] = useState(null);
  const [hysteresis, setHysteresis] = useState(null);
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const outputRoot = "out/web";

  // Load runs on mount
  useEffect(() => {
    api.fetchRuns(outputRoot).then(data => {
      setRuns(data.runs || []);
      if (data.runs && data.runs.length > 0) {
        const first = data.runs[0];
        setSelectedRunId(first.run_id);
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
    setError(null);
    try {
      // Generate config from wizard state
      const configResp = await api.generateConfig(wizard);
      const configPath = configResp.config_path || configResp.path;

      // Execute run
      const runResp = await api.executeRun({
        config_path: configPath,
        output_root: outputRoot,
        backend: wizard.solver_backend,
      });

      const newRunId = runResp.run_id;
      setSelectedRunId(newRunId);
      setStatus("done");

      // Refresh run list
      const runsData = await api.fetchRuns(outputRoot);
      setRuns(runsData.runs || []);
    } catch (ex) {
      setError(ex.message);
      setStatus("error");
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
            ${runs.slice(0, 15).map(r => html`
              <button key=${r.run_id}
                className=${"nav-btn nav-run" + (r.run_id === selectedRunId ? " active" : "")}
                onClick=${() => { setSelectedRunId(r.run_id); setViewMode("results"); }}>
                <span className="nav-text run-text">${r.run_id.slice(4, 16)}</span>
                <span className="nav-badge">${r.backend || ""}</span>
              </button>
            `)}
          </div>

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
