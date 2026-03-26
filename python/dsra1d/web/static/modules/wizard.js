/**
 * StrataWave v2 — 5-Step Wizard (DEEPSOIL-equivalent flow)
 */
import { html, useState, useEffect } from "./setup.js";
import { ProfileEditor } from "./profile-editor.js";
import { MotionPanel } from "./motion-panel.js";
import {
  SOLVER_BACKENDS, BOUNDARY_CONDITIONS, MATERIAL_TYPES,
  defaultLayer, computeGmax,
} from "./utils.js";
import * as api from "./api.js";

const STEPS = [
  { id: "analysis", label: "1. Analysis Type" },
  { id: "profile", label: "2. Soil Profile" },
  { id: "motion", label: "3. Input Motion" },
  { id: "damping", label: "4. Damping" },
  { id: "control", label: "5. Analysis Control" },
];

export function Wizard({ wizard, setWizard, onRun, status, activeStep = 0, setActiveStep }) {
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
      if (data) setWizard(data);
    } catch (e) { console.error("Load example failed:", e); }
  }

  const canRun = wizard.layers && wizard.layers.length > 0 && wizard.motion_path;

  return html`
    <div className="wizard">
      <div className="wizard-body">
        ${activeStep === 0 && html`
          <${AnalysisStep}
            wizard=${wizard} update=${update}
            examples=${examples} onLoadExample=${loadExample}
          />
        `}
        ${activeStep === 1 && html`
          <${ProfileEditor} wizard=${wizard} setWizard=${setWizard} />
        `}
        ${activeStep === 2 && html`
          <${MotionPanel} wizard=${wizard} update=${update} />
        `}
        ${activeStep === 3 && html`<${DampingStep} wizard=${wizard} update=${update} />`}
        ${activeStep === 4 && html`
          <${ControlStep} wizard=${wizard} update=${update}
            canRun=${canRun} onRun=${onRun} status=${status} />
        `}
      </div>
    </div>
  `;
}

// ── Step 1: Analysis Type ────────────────────────────────

function AnalysisStep({ wizard, update, examples, onLoadExample }) {
  return html`
    <div className="step-body">
      <div className="field">
        <label>Project Name</label>
        <input type="text" value=${wizard.project_name || ""}
          onInput=${e => update("project_name", e.target.value)}
          placeholder="My Site Response Analysis" />
      </div>

      <div className="field">
        <label>Solver</label>
        <select value=${wizard.solver_backend || "eql"}
          onChange=${e => update("solver_backend", e.target.value)}>
          ${SOLVER_BACKENDS.map(s => html`
            <option key=${s.value} value=${s.value}>${s.label} — ${s.desc}</option>
          `)}
        </select>
      </div>

      <div className="field">
        <label>Boundary Condition</label>
        <select value=${wizard.boundary_condition || "rigid"}
          onChange=${e => update("boundary_condition", e.target.value)}>
          ${BOUNDARY_CONDITIONS.map(b => html`
            <option key=${b.value} value=${b.value}>${b.label}</option>
          `)}
        </select>
      </div>

      ${examples && examples.length > 0 ? html`
        <div className="field">
          <label>Load Example</label>
          <div className="example-grid">
            ${examples.map(ex => html`
              <button key=${ex.id} className="btn btn-sm"
                onClick=${() => onLoadExample(ex.id)}>
                ${ex.name}
              </button>
            `)}
          </div>
        </div>
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
        <label>Damping Mode</label>
        <select value=${mode}
          onChange=${e => update("damping_mode", e.target.value)}>
          <option value="frequency_independent">Frequency Independent</option>
          <option value="rayleigh">Rayleigh</option>
        </select>
      </div>

      ${mode === "rayleigh" ? html`
        <div className="row">
          <div className="field">
            <label>Mode 1 Freq (Hz)</label>
            <input type="number" step="0.1" value=${wizard.rayleigh_mode_1_hz || 1.0}
              onInput=${e => update("rayleigh_mode_1_hz", parseFloat(e.target.value))} />
          </div>
          <div className="field">
            <label>Mode 2 Freq (Hz)</label>
            <input type="number" step="0.1" value=${wizard.rayleigh_mode_2_hz || 5.0}
              onInput=${e => update("rayleigh_mode_2_hz", parseFloat(e.target.value))} />
          </div>
        </div>
      ` : null}

      <div className="field">
        <label>
          <input type="checkbox" checked=${wizard.viscous_damping_update !== false}
            onChange=${e => update("viscous_damping_update", e.target.checked)} />
          ${" "}Update viscous damping from secant stiffness (nonlinear only)
        </label>
      </div>
    </div>
  `;
}

// ── Step 5: Analysis Control ─────────────────────────────

function ControlStep({ wizard, update, canRun, onRun, status }) {
  const backend = wizard.solver_backend || "eql";

  return html`
    <div className="step-body">
      <div className="row">
        <div className="field">
          <label>Time Step dt (s)</label>
          <input type="number" step="0.001" min="0.0001" max="0.1"
            value=${wizard.dt || 0.005}
            onInput=${e => update("dt", parseFloat(e.target.value))} />
        </div>
        <div className="field">
          <label>Max Frequency (Hz)</label>
          <input type="number" step="1" min="1" max="100"
            value=${wizard.f_max || 25}
            onInput=${e => update("f_max", parseFloat(e.target.value))} />
        </div>
      </div>

      ${backend === "eql" ? html`
        <div className="row">
          <div className="field">
            <label>Max Iterations</label>
            <input type="number" min="1" max="50"
              value=${wizard.max_iterations || 15}
              onInput=${e => update("max_iterations", parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label>Convergence Tol (%)</label>
            <input type="number" step="0.1" min="0.1" max="10"
              value=${(wizard.convergence_tol || 0.03) * 100}
              onInput=${e => update("convergence_tol", parseFloat(e.target.value) / 100)} />
          </div>
          <div className="field">
            <label>Strain Ratio</label>
            <input type="number" step="0.05" min="0.1" max="1"
              value=${wizard.strain_ratio || 0.65}
              onInput=${e => update("strain_ratio", parseFloat(e.target.value))} />
          </div>
        </div>
      ` : null}

      ${backend === "nonlinear" ? html`
        <div className="row">
          <div className="field">
            <label>Substeps per dt</label>
            <input type="number" min="1" max="32"
              value=${wizard.nonlinear_substeps || 4}
              onInput=${e => update("nonlinear_substeps", parseInt(e.target.value))} />
          </div>
        </div>
      ` : null}

      <div style=${{ marginTop: "1rem" }}>
        <button className="btn btn-accent btn-lg"
          disabled=${!canRun || status === "running"}
          onClick=${onRun}>
          ${status === "running" ? "Running..." : "Run Analysis"}
        </button>
        ${!canRun ? html`<p className="muted" style=${{ marginTop: "0.25rem" }}>
          Add soil layers and select a motion file first.
        </p>` : null}
      </div>
    </div>
  `;
}
