/**
 * GeoWave v2 — 5-Step Wizard (DEEPSOIL-equivalent flow)
 */
import { html, useState, useEffect } from "./setup.js";
import { ProfileEditor } from "./profile-editor.js";
import { MotionPanel } from "./motion-panel.js";
import {
  SOLVER_BACKENDS, BOUNDARY_CONDITIONS, MATERIAL_TYPES,
  getSolutionTypeLabel, validateWizard, PARAM_HELP,
} from "./utils.js";

function HelpTip({ id }) {
  const tip = PARAM_HELP[id];
  if (!tip) return null;
  return html`<span className="help-tip" data-tip=${tip}>?</span>`;
}
import * as api from "./api.js";

const STEPS = [
  { id: "analysis", label: "1. Analysis Type" },
  { id: "profile", label: "2. Soil Profile" },
  { id: "motion", label: "3. Input Motion" },
  { id: "damping", label: "4. Damping" },
  { id: "control", label: "5. Analysis Control" },
];

export function Wizard({ wizard, setWizard, onRun, status, activeStep = 0, setActiveStep, onReset, plan }) {
  const [examples, setExamples] = useState([]);

  useEffect(() => {
    api.fetchExamples().then(setExamples).catch(() => {});
  }, []);

  function update(path, value) {
    setWizard(prev => {
      const next = JSON.parse(JSON.stringify(prev));
      const keys = path.split(".");
      let obj = next;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {};
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;
      return next;
    });
  }

  async function loadExample(id) {
    try {
      const data = await api.loadExample(id);
      if (data) {
        setWizard(prev => ({
          ...prev,
          ...data,
          motion_path: "",
          batch_motions: [],
        }));
      }
    } catch (e) { console.error("Load example failed:", e); }
  }

  const validation = validateWizard(wizard);
  const canRun = validation.valid;

  return html`
    <div className="wizard">
      <div className="wizard-body">
        ${activeStep === 0 && html`
          <${AnalysisStep}
            wizard=${wizard} update=${update}
            examples=${examples} onLoadExample=${loadExample}
            onReset=${onReset}
          />
        `}
        ${activeStep === 1 && html`
          <${ProfileEditor} wizard=${wizard} setWizard=${setWizard} />
        `}
        ${activeStep === 2 && html`
          <${MotionPanel} wizard=${wizard} update=${update} plan=${plan} />
        `}
        ${activeStep === 3 && html`<${DampingStep} wizard=${wizard} update=${update} />`}
        ${activeStep === 4 && html`
          <${ControlStep} wizard=${wizard} update=${update}
            canRun=${canRun} onRun=${onRun} status=${status}
            validation=${validation} />
        `}
      </div>
    </div>
  `;
}

// ── Step 1: Analysis Type ────────────────────────────────

function AnalysisStep({ wizard, update, examples, onLoadExample, onReset }) {
  const solverBackend = wizard.solver_backend || "nonlinear";
  const boundaryCondition = wizard.boundary_condition || "rigid";
  const solutionType = getSolutionTypeLabel(solverBackend);
  const selectedMaterial = MATERIAL_TYPES.find(
    option => option.value === (wizard.default_material_type || "gqh"),
  );
  const selectedBoundary = BOUNDARY_CONDITIONS.find(
    option => option.value === boundaryCondition,
  );

  return html`
    <div className="step-body analysis-step-grid">
      <section className="analysis-block analysis-block-project">
        <div className="section-head">
          <h4>Project</h4>
          <p>Run metadata and naming.</p>
        </div>
        <div className="field">
          <label htmlFor="analysis-project-name">Project Name</label>
          <input
            id="analysis-project-name"
            type="text"
            value=${wizard.project_name || ""}
            onInput=${e => update("project_name", e.target.value)}
            placeholder="GeoWave Site Response Case"
          />
        </div>
      </section>

      <section className="analysis-block analysis-block-method">
        <div className="section-head">
          <h4>Analysis Method</h4>
          <p>Select the backend capability GeoWave actually runs.</p>
        </div>
        <div className="field">
          <label htmlFor="analysis-solver-backend">Analysis Method<${HelpTip} id="solver_backend" /></label>
          <select
            id="analysis-solver-backend"
            value=${solverBackend}
            onChange=${e => update("solver_backend", e.target.value)}>
            ${SOLVER_BACKENDS.map(s => html`
              <option key=${s.value} value=${s.value}>${s.label} — ${s.desc}</option>
            `)}
          </select>
        </div>
      </section>

      <section className="analysis-block analysis-block-summary">
        <div className="section-head">
          <h4>Boundary / Solution Summary</h4>
          <p>Base condition plus derived solution family.</p>
        </div>
        <div className="row">
          <div className="field">
            <label htmlFor="analysis-boundary-condition">Boundary Condition<${HelpTip} id="boundary_condition" /></label>
            <select
              id="analysis-boundary-condition"
              value=${boundaryCondition}
              onChange=${e => update("boundary_condition", e.target.value)}>
              ${BOUNDARY_CONDITIONS.map(b => html`
                <option key=${b.value} value=${b.value}>${b.label}</option>
              `)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="analysis-solution-type">Solution Type</label>
            <input id="analysis-solution-type" type="text" value=${solutionType} disabled />
          </div>
        </div>
        <div className="metric-row compact">
          <div className="metric-card compact">
            <span>Backend</span>
            <b>${solverBackend}</b>
          </div>
          <div className="metric-card compact">
            <span>Boundary</span>
            <b>${selectedBoundary?.label || "Rigid Base"}</b>
          </div>
        </div>
      </section>

      <section className="analysis-block analysis-block-default">
        <div className="section-head">
          <h4>Default Soil Model</h4>
          <p>Applied only when new layers are added in Step 2.</p>
        </div>
        <div className="field">
          <label htmlFor="analysis-default-material">Default Soil Model</label>
          <select
            id="analysis-default-material"
            value=${wizard.default_material_type || "gqh"}
            onChange=${e => update("default_material_type", e.target.value)}>
            ${MATERIAL_TYPES.map(material => html`
              <option key=${material.value} value=${material.value}>${material.label}</option>
            `)}
          </select>
        </div>
        <p className="muted section-footnote">
          New layers will start as ${selectedMaterial?.label || "GQH"}.
        </p>
      </section>

      ${examples && examples.length > 0 ? html`
        <section className="analysis-block analysis-block-full">
          <div className="section-head">
            <h4>Load Example</h4>
            <p>Pre-populate the wizard from an existing GeoWave case.</p>
          </div>
          <div className="example-grid">
            ${examples.map(ex => html`
              <button key=${ex.id} type="button" className="btn btn-sm"
                onClick=${() => onLoadExample(ex.id)}>
                ${ex.name}
              </button>
            `)}
          </div>
        </section>
      ` : null}

      ${onReset ? html`
        <section className="analysis-block analysis-block-muted analysis-block-reset">
          <div className="section-head">
            <h4>Reset</h4>
            <p>Clear local wizard state and return to defaults.</p>
          </div>
          <button type="button" className="btn btn-sm" onClick=${onReset}>
            Reset Wizard
          </button>
        </section>
      ` : null}
    </div>
  `;
}

// ── Step 4: Damping ──────────────────────────────────────

function DampingStep({ wizard, update }) {
  const mode = wizard.damping_mode || "frequency_independent";

  return html`
    <div className="step-body">
      <div className="field">
        <label htmlFor="damping-mode">Damping Mode<${HelpTip} id="damping_mode" /></label>
        <select id="damping-mode" value=${mode}
          onChange=${e => update("damping_mode", e.target.value)}>
          <option value="frequency_independent">Frequency Independent</option>
          <option value="rayleigh">Rayleigh</option>
        </select>
      </div>

      ${mode === "rayleigh" ? html`
        <div className="row">
          <div className="field">
            <label htmlFor="damping-mode-1-freq">Mode 1 Freq (Hz)</label>
            <input id="damping-mode-1-freq" type="number" step="0.1" value=${wizard.rayleigh_mode_1_hz || 1.0}
              onInput=${e => update("rayleigh_mode_1_hz", parseFloat(e.target.value))} />
          </div>
          <div className="field">
            <label htmlFor="damping-mode-2-freq">Mode 2 Freq (Hz)</label>
            <input id="damping-mode-2-freq" type="number" step="0.1" value=${wizard.rayleigh_mode_2_hz || 5.0}
              onInput=${e => update("rayleigh_mode_2_hz", parseFloat(e.target.value))} />
          </div>
        </div>
      ` : null}

      <div className="field">
        <label>
          <input type="checkbox" checked=${wizard.viscous_damping_update === true}
            onChange=${e => update("viscous_damping_update", e.target.checked)} />
          ${" "}Update viscous damping from secant stiffness (nonlinear only)
        </label>
      </div>
    </div>
  `;
}

// ── Step 5: Analysis Control ─────────────────────────────

function ControlStep({ wizard, update, canRun, onRun, status, validation }) {
  const backend = wizard.solver_backend || "nonlinear";
  const { errors = [], warnings = [] } = validation || {};
  const batchCount = wizard.batch_motions?.length || 0;
  const isBatch = batchCount > 1;

  return html`
    <div className="step-body">
      <div className="row">
        <div className="field">
          <label htmlFor="control-dt">Time Step dt (s)<${HelpTip} id="dt" /></label>
          <input id="control-dt" type="number" step="0.001" min="0.0001" max="0.1"
            value=${wizard.dt || 0.005}
            onInput=${e => update("dt", parseFloat(e.target.value))} />
        </div>
        <div className="field">
          <label htmlFor="control-f-max">Max Frequency (Hz)<${HelpTip} id="f_max" /></label>
          <input id="control-f-max" type="number" step="1" min="1" max="100"
            value=${wizard.f_max || 25}
            onInput=${e => update("f_max", parseFloat(e.target.value))} />
        </div>
      </div>

      ${backend === "eql" ? html`
        <div className="row">
          <div className="field">
            <label htmlFor="control-max-iterations">Max Iterations<${HelpTip} id="max_iterations" /></label>
            <input id="control-max-iterations" type="number" min="1" max="50"
              value=${wizard.max_iterations || 15}
              onInput=${e => update("max_iterations", parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label htmlFor="control-convergence-tol">Convergence Tol (%)<${HelpTip} id="convergence_tol" /></label>
            <input id="control-convergence-tol" type="number" step="0.1" min="0.1" max="10"
              value=${(wizard.convergence_tol || 0.03) * 100}
              onInput=${e => update("convergence_tol", parseFloat(e.target.value) / 100)} />
          </div>
          <div className="field">
            <label htmlFor="control-strain-ratio">Strain Ratio<${HelpTip} id="strain_ratio" /></label>
            <input id="control-strain-ratio" type="number" step="0.05" min="0.1" max="1"
              value=${wizard.strain_ratio || 0.65}
              onInput=${e => update("strain_ratio", parseFloat(e.target.value))} />
          </div>
        </div>
      ` : null}

      ${backend === "nonlinear" ? html`
        <div className="row">
          <div className="field">
            <label htmlFor="control-nonlinear-substeps">Substeps per dt</label>
            <input id="control-nonlinear-substeps" type="number" min="1" max="32"
              value=${wizard.nonlinear_substeps || 4}
              onInput=${e => update("nonlinear_substeps", parseInt(e.target.value))} />
          </div>
        </div>
      ` : null}

      <div className="row">
        <div className="field">
          <label htmlFor="control-timeout-s">Solver Timeout (s)</label>
          <input id="control-timeout-s" type="number" min="30" max="7200"
            value=${wizard.timeout_s || 180}
            onInput=${e => update("timeout_s", parseInt(e.target.value, 10) || 180)} />
        </div>
        <div className="field">
          <label htmlFor="control-retries">Retries</label>
          <input id="control-retries" type="number" min="0" max="10"
            value=${wizard.retries ?? 1}
            onInput=${e => update("retries", parseInt(e.target.value, 10) || 0)} />
        </div>
      </div>

      ${isBatch ? html`
        <div className="row">
          <div className="field">
            <label htmlFor="control-parallel-workers">Parallel Workers</label>
            <input id="control-parallel-workers" type="number" min="1" max="64"
              value=${wizard.parallel_workers || 1}
              onInput=${e => update("parallel_workers", parseInt(e.target.value, 10) || 1)} />
          </div>
        </div>
        <p className="muted" style=${{ marginTop: "-0.2rem" }}>
          ${batchCount} motion selected. GeoWave will queue them and run up to ${wizard.parallel_workers || 1} analysis worker(s) in parallel.
        </p>
      ` : null}

      ${warnings.length > 0 ? html`
        <div className="validation-warnings" style=${{ marginTop: "0.5rem", padding: "0.5rem", background: "rgba(243,156,18,0.08)", borderRadius: "6px", border: "1px solid rgba(243,156,18,0.2)" }}>
          ${warnings.map((w, i) => html`<p key=${i} style=${{ margin: "0.15rem 0", fontSize: "0.8rem", color: "#F39C12" }}>${w}</p>`)}
        </div>
      ` : null}
      ${errors.length > 0 ? html`
        <div className="validation-errors" style=${{ marginTop: "0.5rem", padding: "0.5rem", background: "rgba(231,76,60,0.08)", borderRadius: "6px", border: "1px solid rgba(231,76,60,0.2)" }}>
          ${errors.map((e, i) => html`<p key=${i} style=${{ margin: "0.15rem 0", fontSize: "0.8rem", color: "#E74C3C" }}>${e}</p>`)}
        </div>
      ` : null}
      <div style=${{ marginTop: "1rem" }}>
        <button type="button" className="btn btn-accent btn-lg"
          disabled=${!canRun || status === "running"}
          onClick=${onRun}>
          ${status === "running" ? "Running..." : "Run Analysis"}
        </button>
      </div>
    </div>
  `;
}
