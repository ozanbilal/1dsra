/**
 * GeoWave v2 — Motion Upload & Preview Panel
 * Supports: file upload (CSV/AT2), motion library browser, scaling
 */
import { html, useState, useEffect, useRef } from "./setup.js";
import { ChartCard, MultiSeriesChart } from "./charts.js";
import {
  buildMotionParseSettings,
  fmt,
  MOTION_BASELINE_METHOD_OPTIONS,
  MOTION_DELIMITER_OPTIONS,
  MOTION_FILTER_CONFIG_OPTIONS,
  MOTION_FILTER_DOMAIN_OPTIONS,
  MOTION_FILTER_TYPE_OPTIONS,
  MOTION_FORMAT_OPTIONS,
  MOTION_PADDING_METHOD_OPTIONS,
  MOTION_PROCESSING_ORDER_OPTIONS,
  MOTION_UNIT_OPTIONS,
  MOTION_WINDOW_APPLY_OPTIONS,
  MOTION_WINDOW_TYPE_OPTIONS,
  PARAM_HELP,
} from "./utils.js";
import * as api from "./api.js";
import { canUseFeature } from "./plans.js";

function HelpTip({ id }) {
  const tip = PARAM_HELP[id];
  if (!tip) return null;
  return html`<span className="help-tip" data-tip=${tip}>?</span>`;
}

function parseDirectoryList(rawText) {
  return String(rawText || "")
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean);
}

function usesExplicitColumns(formatHint, hasTime) {
  return formatHint === "time_acc" || (formatHint === "auto" && hasTime !== false);
}

const MOTION_UNIT_LABELS = {
  "m/s2": "m/s²",
  "m/s^2": "m/s²",
  g: "g",
  "cm/s2": "cm/s²",
  "cm/s^2": "cm/s²",
  gal: "gal",
};

function motionUnitLabel(unit) {
  return MOTION_UNIT_LABELS[String(unit || "").trim().toLowerCase()] || String(unit || "m/s2");
}

export function MotionPanel({ wizard, update, plan }) {
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [library, setLibrary] = useState([]);
  const [batchMode, setBatchMode] = useState(Boolean(wizard.batch_motions && wizard.batch_motions.length > 0));
  const [filterText, setFilterText] = useState("");
  const [libLoading, setLibLoading] = useState(false);
  const [clearGeneratedBusy, setClearGeneratedBusy] = useState(false);
  const [toolError, setToolError] = useState(null);
  const [toolAuditTrail, setToolAuditTrail] = useState([]);
  const [reduceTargetDt, setReduceTargetDt] = useState("");
  const [reduceFactor, setReduceFactor] = useState(2);
  const [reduceBusy, setReduceBusy] = useState(false);
  const [reducePreview, setReducePreview] = useState(null);
  const [kappaMinHz, setKappaMinHz] = useState(10);
  const [kappaMaxHz, setKappaMaxHz] = useState(40);
  const [kappaBusy, setKappaBusy] = useState(false);
  const [kappaPreview, setKappaPreview] = useState(null);
  const [accelerationView, setAccelerationView] = useState("overlay");
  const csvRef = useRef(null);
  const at2Ref = useRef(null);
  const parseSettings = buildMotionParseSettings(wizard);
  const showTimeColumnFields = usesExplicitColumns(parseSettings.format_hint, parseSettings.has_time);
  const directoryListValue = Array.isArray(wizard.motion_library_dirs)
    ? wizard.motion_library_dirs.join("\n")
    : "";
  const extraDirectoryCount = Array.isArray(wizard.motion_library_dirs) ? wizard.motion_library_dirs.length : 0;
  const parseSummary = [
    `skip ${parseSettings.skip_rows}`,
    parseSettings.delimiter === "auto" ? "delim auto" : `delim ${parseSettings.delimiter}`,
    parseSettings.has_time ? `cols t${parseSettings.time_col}/a${parseSettings.acc_col}` : `acc col ${parseSettings.acc_col}`,
    wizard.motion_dt_override ? `dt ${fmt(wizard.motion_dt_override, 4)} s` : "dt auto",
    extraDirectoryCount > 0 ? `${extraDirectoryCount} folder${extraDirectoryCount > 1 ? "s" : ""}` : "no folders",
  ];

  function appendAuditStep(action, details) {
    const stamp = new Date().toLocaleTimeString();
    setToolAuditTrail(prev => [{ stamp, action, details }, ...prev].slice(0, 12));
  }

  function refreshLibrary() {
    const dirs = wizard.motion_library_dirs || [];
    if (!dirs.length) {
      setLibrary([]);
      setLibLoading(false);
      return;
    }
    setLibLoading(true);
    api.fetchMotionLibrary(dirs)
      .then(data => setLibrary(Array.isArray(data) ? data : []))
      .catch(() => setLibrary([]))
      .finally(() => setLibLoading(false));
  }

  function clearLibraryFolders() {
    update("motion_library_dirs", []);
    setFilterText("");
    setLibrary([]);
  }

  async function clearGeneratedMotions() {
    setClearGeneratedBusy(true);
    setError(null);
    try {
      const result = await api.clearGeneratedMotions();
      appendAuditStep(
        "Generated motions cleared",
        `${result.removed_files || 0} file(s) removed from ${result.directory || "out/ui/motions"}`,
      );
      const currentPath = String(wizard.motion_path || "").replaceAll("/", "\\");
      if (currentPath.includes("out\\ui\\motions")) {
        update("motion_path", "");
        setPreview(null);
      }
    } catch (ex) {
      const message = ex.message || "";
      if (message.includes("404")) {
        setError("Clear Generated endpoint is not active in the running server yet. Restart the web server and try again.");
      } else {
        setError(message || "Generated motions could not be cleared.");
      }
    } finally {
      setClearGeneratedBusy(false);
    }
  }

  // Load motion library on mount
  useEffect(() => {
    refreshLibrary();
  }, [JSON.stringify(wizard.motion_library_dirs || [])]);

  useEffect(() => {
    setBatchMode(Boolean(wizard.batch_motions && wizard.batch_motions.length > 0));
  }, [wizard.batch_motions]);

  // Fetch motion preview whenever motion_path changes
  useEffect(() => {
    if (!wizard.motion_path) { setPreview(null); return; }
    api.fetchMotionPreview(wizard.motion_path, parseSettings)
      .then(data => {
        setPreview({
          rawTime: data.raw_time_s || [],
          rawAccInput: data.raw_acc_input_units || [],
          rawAcc: data.raw_acc_m_s2 || [],
          time: data.time_s || [],
          accInput: data.acc_input_units || [],
          acc: data.acc_m_s2 || [],
          vel: data.vel_m_s || [],
          disp: data.disp_m || [],
          period: data.period_s || [],
          saInput: data.sa_input_units || [],
          sa: data.sa_m_s2 || [],
          sv: data.sv_m_s || [],
          sd: data.sd_m || [],
          dt: data.dt,
          rawDt: data.raw_dt,
          rawPga: data.raw_pga_m_s2,
          rawPgaInput: data.raw_pga_input_units,
          rawPgaG: data.raw_pga_g,
          pga: data.pga_m_s2,
          pgaInput: data.pga_input_units,
          pgaG: data.pga_g,
          pgv: data.pgv_m_s,
          pgd: data.pgd_m,
          saMax: data.sa_max_input_units,
          peakSa: data.peak_sa_m_s2,
          duration: data.duration,
          rawDuration: data.raw_duration,
          npts: data.npts,
          inputUnits: data.input_units,
          showUncorrectedPreview: data.show_uncorrected_preview !== false,
        });
      })
      .catch(() => {}); // silently fail — preview is optional
  }, [wizard.motion_path, JSON.stringify(parseSettings)]);

  useEffect(() => {
    setToolError(null);
    setReducePreview(null);
    setKappaPreview(null);
    if (!wizard.motion_path) setToolAuditTrail([]);
  }, [wizard.motion_path, JSON.stringify(parseSettings)]);

  async function handleCSVUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadMotionCSV(file);
      const motionPath = result.uploaded_path || result.path || "";
      update("motion_path", motionPath);
    } catch (ex) {
      setError(ex.message);
    }
    setUploading(false);
  }

  async function handleAT2Upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadMotionAT2(file, {
        units_hint: wizard.motion_units || "g",
        dt_override: parseSettings.dt_override,
      });
      const motionPath = result.converted_csv_path || result.csv_path || result.uploaded_path || "";
      update("motion_path", motionPath);
      update("motion_units", "m/s2");
      update("motion_format_hint", "auto");
      update("motion_delimiter", "auto");
      update("motion_skip_rows", 0);
      update("motion_has_time", true);
      update("motion_time_col", 0);
      update("motion_acc_col", 1);
      update("motion_dt_override", null);
      setPreview(null);
    } catch (ex) {
      setError(ex.message);
    }
    setUploading(false);
  }

  function selectFromLibrary(motion) {
    update("motion_path", motion.path);
    setError(null);
  }

  function downloadCsv(filename, header, rows) {
    const csv = [header.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function runTimeStepReduction() {
    if (!wizard.motion_path) return;
    setToolError(null);
    setReduceBusy(true);
    try {
      const targetDtValue = Number(reduceTargetDt);
      const payload = {
        motion_path: wizard.motion_path,
        ...parseSettings,
        reduction_factor: Math.max(2, Math.round(Number(reduceFactor) || 2)),
        target_dt: Number.isFinite(targetDtValue) && targetDtValue > 0 ? targetDtValue : null,
      };
      const result = await api.motionTimeStepReduction(payload);
      setReducePreview(result);
      appendAuditStep(
        "Time-step reduction preview",
        `dt ${fmt(result.dt_original, 5)}s -> ${fmt(result.dt_reduced, 5)}s (x${result.reduction_factor})`,
      );
    } catch (ex) {
      setToolError(ex.message || "Time-step reduction failed.");
      setReducePreview(null);
    } finally {
      setReduceBusy(false);
    }
  }

  async function runKappaEstimator() {
    if (!wizard.motion_path) return;
    setToolError(null);
    setKappaBusy(true);
    try {
      const payload = {
        motion_path: wizard.motion_path,
        ...parseSettings,
        freq_min_hz: Math.max(0.1, Number(kappaMinHz) || 10),
        freq_max_hz: Math.max(0.2, Number(kappaMaxHz) || 40),
      };
      const result = await api.motionEstimateKappa(payload);
      setKappaPreview(result);
      if (result.kappa != null) {
        appendAuditStep(
          "Kappa estimation",
          `κ=${fmt(result.kappa, 5)} (R²=${fmt(result.kappa_r2, 4)}) over ${fmt(payload.freq_min_hz, 1)}-${fmt(payload.freq_max_hz, 1)} Hz`,
        );
      } else {
        appendAuditStep(
          "Kappa estimation",
          result.note || "Estimator did not return a stable kappa fit.",
        );
      }
    } catch (ex) {
      setToolError(ex.message || "Kappa estimation failed.");
      setKappaPreview(null);
    } finally {
      setKappaBusy(false);
    }
  }

  const filterNeedle = filterText.trim().toLowerCase();
  const sourceGroupLabel = (motion) => motion.source_group_label || motion.source_label || motion.source;
  const filteredLibrary = filterNeedle
    ? library.filter(m =>
      `${m.name} ${m.file_name} ${sourceGroupLabel(m)}`.toLowerCase().includes(filterNeedle))
    : library;
  const totalSourceGroups = new Set(library.map(sourceGroupLabel)).size;
  const visibleSourceGroups = new Set(filteredLibrary.map(sourceGroupLabel)).size;

  return html`
    <div className="step-body motion-panel-shell">
      <input ref=${csvRef} type="file" accept=".csv,.txt" aria-label="Upload motion CSV file" className="hidden-input" onChange=${handleCSVUpload} />
      <input ref=${at2Ref} type="file" accept=".at2,.AT2" aria-label="Upload PEER AT2 motion file" className="hidden-input" onChange=${handleAT2Upload} />

      <section className="motion-section">
        <div className="section-head">
          <h4>Source & Parse</h4>
          <p>Keep only the essentials visible. Library folders and parse controls stay one click away.</p>
        </div>
        <div className="motion-toolbar">
          <button type="button" className="btn" onClick=${() => csvRef.current?.click()} disabled=${uploading}>
            Upload CSV / TXT
          </button>
          <button type="button" className="btn" onClick=${() => at2Ref.current?.click()} disabled=${uploading}>
            Upload PEER AT2
          </button>
          <button type="button" className="btn btn-sm" onClick=${refreshLibrary} disabled=${libLoading}>
            ${libLoading ? "Refreshing..." : "Refresh Library"}
          </button>
          <button type="button" className="btn btn-sm" onClick=${clearGeneratedMotions} disabled=${clearGeneratedBusy}>
            ${clearGeneratedBusy ? "Clearing..." : "Clear Generated"}
          </button>
          ${uploading ? html`<span className="muted">Uploading...</span>` : null}
        </div>
        <div className="motion-source-shell">
          <div className="motion-essentials-grid">
            <div className="field">
              <label htmlFor="motion-units">Input Units<${HelpTip} id="motion_units" /></label>
              <select id="motion-units" value=${wizard.motion_units || "m/s2"} onChange=${e => update("motion_units", e.target.value)}>
                ${MOTION_UNIT_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="motion-format-hint">Format Hint<${HelpTip} id="motion_format_hint" /></label>
              <select id="motion-format-hint" value=${parseSettings.format_hint} onChange=${e => update("motion_format_hint", e.target.value)}>
                ${MOTION_FORMAT_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
              </select>
            </div>
            <div className="motion-parse-summary" aria-label="Current parse settings">
              ${parseSummary.map(item => html`<span className="motion-pill">${item}</span>`)}
            </div>
          </div>
          <div className="motion-toolbar" style=${{ marginTop: "0.35rem" }}>
            <button type="button" className="btn btn-sm" onClick=${clearLibraryFolders} disabled=${extraDirectoryCount === 0}>
              Clear Folders
            </button>
          </div>
          <details className="motion-parse-details">
            <summary>Library folders & parse options</summary>
            <div className="motion-parse-details-grid">
              <div className="field motion-span-2">
                <label htmlFor="motion-library-dirs">Motion Library Folders<${HelpTip} id="motion_library_dirs" /></label>
                <textarea
                  id="motion-library-dirs"
                  rows="2"
                  value=${directoryListValue}
                  placeholder="One folder path per line"
                  onInput=${e => update("motion_library_dirs", parseDirectoryList(e.target.value))}
                />
                <p className="muted section-footnote">Only these folders are scanned, and only their direct motion files are listed.</p>
              </div>
              <div className="field">
                <label htmlFor="motion-delimiter">Delimiter<${HelpTip} id="motion_delimiter" /></label>
                <select id="motion-delimiter" value=${parseSettings.delimiter || "auto"} onChange=${e => update("motion_delimiter", e.target.value)}>
                  ${MOTION_DELIMITER_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="motion-skip-rows">Skip Rows<${HelpTip} id="motion_skip_rows" /></label>
                <input id="motion-skip-rows" type="number" min="0" step="1" value=${parseSettings.skip_rows} onInput=${e => update("motion_skip_rows", Math.max(0, parseInt(e.target.value || "0", 10) || 0))} />
              </div>
              <div className="field">
                <label htmlFor="motion-dt-override">dt Override (s)<${HelpTip} id="motion_dt_override" /></label>
                <input id="motion-dt-override" type="number" min="0" step="any" value=${wizard.motion_dt_override ?? ""} placeholder="optional" onInput=${e => {
                  const value = parseFloat(e.target.value);
                  update("motion_dt_override", Number.isFinite(value) && value > 0 ? value : null);
                }} />
              </div>
              <label className="inline-checkbox motion-inline-toggle" htmlFor="motion-has-time">
                <span>File includes time column</span>
                <input id="motion-has-time" type="checkbox" checked=${parseSettings.has_time} onChange=${e => update("motion_has_time", e.target.checked)} disabled=${parseSettings.format_hint === "single" || parseSettings.format_hint === "numeric_stream"} />
              </label>
              ${showTimeColumnFields ? html`
                <div className="field">
                  <label htmlFor="motion-time-col">Time Column<${HelpTip} id="motion_time_col" /></label>
                  <input id="motion-time-col" type="number" min="0" step="1" value=${parseSettings.time_col} onInput=${e => update("motion_time_col", Math.max(0, parseInt(e.target.value || "0", 10) || 0))} />
                </div>
              ` : null}
              <div className="field">
                <label htmlFor="motion-acc-col">Acceleration Column<${HelpTip} id="motion_acc_col" /></label>
                <input id="motion-acc-col" type="number" min="0" step="1" value=${parseSettings.acc_col} onInput=${e => update("motion_acc_col", Math.max(0, parseInt(e.target.value || "0", 10) || 0))} />
              </div>
            </div>
          </details>
        </div>
        <p className="muted section-footnote">Preview, motion tools and run-ready normalization all use the settings above.</p>
      </section>

      <section className="motion-section">
        <div className="section-head">
          <h4>Motion Library</h4>
          <p>Search across the folders you listed above. Subfolders are not scanned automatically.</p>
        </div>
        <div className="motion-field-grid">
          <div className="field motion-span-2">
            <label htmlFor="motion-library-filter">Search Library</label>
            <input
              id="motion-library-filter"
              type="text"
              value=${filterText}
              placeholder="Filter by earthquake name or source folder"
              onInput=${e => setFilterText(e.target.value)}
            />
          </div>
          <div className="field motion-span-2">
            <label htmlFor="motion-library-select">Motion Library</label>
            <select id="motion-library-select" value=${wizard.motion_path || ""}
              onChange=${e => {
                const sel = filteredLibrary.find(m => m.path === e.target.value) || library.find(m => m.path === e.target.value);
                if (sel) selectFromLibrary(sel);
              }}>
              <option value="">— Select from library —</option>
              ${filteredLibrary.map(m => html`
                <option key=${m.path} value=${m.path}>
                  ${m.name} (${m.format.toUpperCase()}) — ${sourceGroupLabel(m)}
                </option>
              `)}
            </select>
          </div>
        </div>
        ${library.length > 0 ? html`
          <p className="muted section-footnote">
            ${filteredLibrary.length} / ${library.length} motion(s) visible • ${visibleSourceGroups} / ${totalSourceGroups} source group(s)
          </p>
        ` : libLoading ? html`<p className="muted section-footnote">Loading motion library...</p>` : null}
      </section>

      <!-- Batch mode toggle (Pro) -->
      ${canUseFeature(plan, "batch_analysis") && library.length > 1 ? html`
        <section className="motion-section">
          <div className="section-head">
            <h4>Batch Selection</h4>
            <p>Select multiple records when you want to launch the same model across several motions.</p>
          </div>
          <label style=${{ fontSize: "0.8rem", cursor: "pointer" }}>
            <input type="checkbox" checked=${batchMode}
              onChange=${e => {
                setBatchMode(e.target.checked);
                if (e.target.checked) {
                  // Initialize batch_motions with current selection if any
                  const initial = wizard.motion_path ? [wizard.motion_path] : [];
                  update("batch_motions", initial);
                } else {
                  update("batch_motions", null);
                }
              }} />
            ${" "}Batch mode — run with multiple motions
          </label>
        </section>
      ` : null}

      ${batchMode && filteredLibrary.length > 0 ? html`
        <div className="motion-batch-list">
          ${filteredLibrary.map(m => {
            const checked = (wizard.batch_motions || []).includes(m.path);
            return html`
              <label key=${m.path} className="motion-batch-item">
                <input type="checkbox" checked=${checked}
                  onChange=${e => {
                    const prev = wizard.batch_motions || [];
                    const next = e.target.checked ? [...prev, m.path] : prev.filter(p => p !== m.path);
                    update("batch_motions", next);
                    if (next.length > 0 && !wizard.motion_path) update("motion_path", next[0]);
                  }} />
                <span>${m.name} (${m.format.toUpperCase()})</span>
                <span className="motion-batch-meta">${sourceGroupLabel(m)}</span>
              </label>
            `;
          })}
          <div style=${{ fontSize: "0.7rem", color: "var(--ink-60)", marginTop: "0.2rem", padding: "0 0.25rem" }}>
            ${(wizard.batch_motions || []).length} motion(s) selected
          </div>
        </div>
      ` : null}

      <!-- Current selection -->
      ${wizard.motion_path ? html`
        <section className="motion-section">
          <div className="section-head">
            <h4>Selected Motion</h4>
            <p>Uploaded or converted motions are written under <code>out/ui/motions</code> so preview and reruns use the same file. That generated folder is no longer part of the motion library scan.</p>
          </div>
          <div className="field">
            <label htmlFor="selected-motion-path">Selected Motion</label>
            <div style=${{ display: "flex", gap: "0.25rem", alignItems: "center" }}>
              <input id="selected-motion-path" type="text" value=${wizard.motion_path} readOnly style=${{ color: "var(--ink-60)", fontSize: "0.75rem", flex: 1 }} />
              <button type="button" className="btn btn-sm" onClick=${() => { update("motion_path", ""); setPreview(null); }}
                style=${{ fontSize: "0.65rem", padding: "0.15rem 0.4rem" }}>Clear</button>
            </div>
          </div>
          <div className="metric-row compact">
            <div className="metric-card compact"><span>Declared Units</span><b>${wizard.motion_units || "m/s2"}</b></div>
            <div className="metric-card compact"><span>Format Hint</span><b>${parseSettings.format_hint}</b></div>
            <div className="metric-card compact"><span>Skip Rows</span><b>${parseSettings.skip_rows}</b></div>
            <div className="metric-card compact"><span>Acceleration Col</span><b>${parseSettings.acc_col}</b></div>
          </div>
        </section>
      ` : null}

      ${error ? html`<p className="error-text">${error}</p>` : null}

      <section className="motion-section">
        <div className="section-head">
          <h4>Processing & Scaling</h4>
          <p>Advanced preprocessing stays collapsed by default, but preview and run-ready export now share the same pipeline.</p>
        </div>
        <div className="row">
          <div className="field">
            <label htmlFor="motion-scale-mode">Scale Mode<${HelpTip} id="scale_mode" /></label>
            <select id="motion-scale-mode" value=${wizard.scale_mode || "none"}
              onChange=${e => update("scale_mode", e.target.value)}>
              <option value="none">No Scaling</option>
              <option value="scale_factor">Scale Factor</option>
              <option value="scale_to_pga">Scale to PGA</option>
            </select>
          </div>
          ${wizard.scale_mode === "scale_factor" ? html`
            <div className="field">
              <label htmlFor="motion-scale-factor">Factor</label>
              <input id="motion-scale-factor" type="number" step="0.1" min="0.01"
                value=${wizard.scale_factor || 1.0}
                onInput=${e => update("scale_factor", parseFloat(e.target.value))} />
            </div>
          ` : null}
          ${wizard.scale_mode === "scale_to_pga" ? html`
            <div className="field">
              <label htmlFor="motion-target-pga">Target PGA (g)</label>
              <input id="motion-target-pga" type="number" step="0.01" min="0.001"
                value=${wizard.target_pga_g || 0.3}
                onInput=${e => update("target_pga_g", parseFloat(e.target.value))} />
            </div>
          ` : null}
        </div>
        <details className="fit-limits-panel motion-advanced-panel">
          <summary>Advanced Processing</summary>
          <div className="profile-stage-grid profile-stage-grid-3">
            <div className="field">
              <label htmlFor="motion-proc-order">Processing Order<${HelpTip} id="motion_proc_processing_order" /></label>
              <select id="motion-proc-order" value=${wizard.motion_proc_processing_order || "filter_first"} onChange=${e => update("motion_proc_processing_order", e.target.value)}>
                ${MOTION_PROCESSING_ORDER_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
              </select>
            </div>
            <label className="field inline-checkbox" htmlFor="motion-proc-baseline-on">
              <span>Baseline Correction</span>
              <input id="motion-proc-baseline-on" type="checkbox" checked=${wizard.motion_proc_baseline_on === true} onChange=${e => update("motion_proc_baseline_on", e.target.checked)} />
            </label>
            <label className="field inline-checkbox" htmlFor="motion-proc-filter-on">
              <span>Filtering</span>
              <input id="motion-proc-filter-on" type="checkbox" checked=${wizard.motion_proc_filter_on === true} onChange=${e => update("motion_proc_filter_on", e.target.checked)} />
            </label>
            <label className="field inline-checkbox" htmlFor="motion-proc-window-on">
              <span>Windowing</span>
              <input id="motion-proc-window-on" type="checkbox" checked=${wizard.motion_proc_window_on === true} onChange=${e => update("motion_proc_window_on", e.target.checked)} />
            </label>
            <label className="field inline-checkbox" htmlFor="motion-proc-residual-fix">
              <span>Residual Fix</span>
              <input id="motion-proc-residual-fix" type="checkbox" checked=${wizard.motion_proc_residual_fix === true} onChange=${e => update("motion_proc_residual_fix", e.target.checked)} />
            </label>
            <label className="field inline-checkbox" htmlFor="motion-proc-show-raw">
              <span>Show Raw Preview</span>
              <input id="motion-proc-show-raw" type="checkbox" checked=${wizard.motion_proc_show_uncorrected_preview !== false} onChange=${e => update("motion_proc_show_uncorrected_preview", e.target.checked)} />
            </label>

            ${wizard.motion_proc_baseline_on === true ? html`
              <div className="field">
                <label htmlFor="motion-proc-baseline-method">Baseline Method<${HelpTip} id="motion_proc_baseline_method" /></label>
                <select id="motion-proc-baseline-method" value=${wizard.motion_proc_baseline_method || "poly4"} onChange=${e => update("motion_proc_baseline_method", e.target.value)}>
                  ${MOTION_BASELINE_METHOD_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="motion-proc-baseline-degree">Baseline Degree</label>
                <input id="motion-proc-baseline-degree" type="number" min="0" max="10" step="1" value=${wizard.motion_proc_baseline_degree ?? 4} onInput=${e => update("motion_proc_baseline_degree", Math.max(0, parseInt(e.target.value || "4", 10) || 4))} />
              </div>
            ` : null}

            ${wizard.motion_proc_filter_on === true ? html`
              <div className="field">
                <label htmlFor="motion-proc-filter-domain">Filter Domain</label>
                <select id="motion-proc-filter-domain" value=${wizard.motion_proc_filter_domain || "time"} onChange=${e => update("motion_proc_filter_domain", e.target.value)}>
                  ${MOTION_FILTER_DOMAIN_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="motion-proc-filter-config">Filter Config<${HelpTip} id="motion_proc_filter_config" /></label>
                <select id="motion-proc-filter-config" value=${wizard.motion_proc_filter_config || "bandpass"} onChange=${e => update("motion_proc_filter_config", e.target.value)}>
                  ${MOTION_FILTER_CONFIG_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="motion-proc-filter-type">Filter Type</label>
                <select id="motion-proc-filter-type" value=${wizard.motion_proc_filter_type || "butter"} onChange=${e => update("motion_proc_filter_type", e.target.value)}>
                  ${MOTION_FILTER_TYPE_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="motion-proc-f-low">f Low (Hz)</label>
                <input id="motion-proc-f-low" type="number" min="0" step="0.01" value=${wizard.motion_proc_f_low ?? 0.1} onInput=${e => update("motion_proc_f_low", parseFloat(e.target.value) || 0)} />
              </div>
              <div className="field">
                <label htmlFor="motion-proc-f-high">f High (Hz)</label>
                <input id="motion-proc-f-high" type="number" min="0" step="0.01" value=${wizard.motion_proc_f_high ?? 25} onInput=${e => update("motion_proc_f_high", parseFloat(e.target.value) || 0)} />
              </div>
              <div className="field">
                <label htmlFor="motion-proc-filter-order">Filter Order</label>
                <input id="motion-proc-filter-order" type="number" min="1" max="16" step="1" value=${wizard.motion_proc_filter_order ?? 4} onInput=${e => update("motion_proc_filter_order", Math.max(1, parseInt(e.target.value || "4", 10) || 4))} />
              </div>
              <label className="field inline-checkbox" htmlFor="motion-proc-acausal">
                <span>Acausal Filter</span>
                <input id="motion-proc-acausal" type="checkbox" checked=${wizard.motion_proc_acausal !== false} onChange=${e => update("motion_proc_acausal", e.target.checked)} />
              </label>
            ` : null}

            ${wizard.motion_proc_window_on === true ? html`
              <div className="field">
                <label htmlFor="motion-proc-window-type">Window Type</label>
                <select id="motion-proc-window-type" value=${wizard.motion_proc_window_type || "hanning"} onChange=${e => update("motion_proc_window_type", e.target.value)}>
                  ${MOTION_WINDOW_TYPE_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="motion-proc-window-param">Window Param</label>
                <input id="motion-proc-window-param" type="number" min="0" step="0.01" value=${wizard.motion_proc_window_param ?? 0.1} onInput=${e => update("motion_proc_window_param", parseFloat(e.target.value) || 0)} />
              </div>
              <div className="field">
                <label htmlFor="motion-proc-window-duration">Window Duration (s)<${HelpTip} id="motion_proc_window_duration" /></label>
                <input id="motion-proc-window-duration" type="number" min="0" step="0.01" value=${wizard.motion_proc_window_duration ?? ""} placeholder="optional" onInput=${e => {
                  const value = parseFloat(e.target.value);
                  update("motion_proc_window_duration", Number.isFinite(value) && value > 0 ? value : null);
                }} />
              </div>
              <div className="field">
                <label htmlFor="motion-proc-window-apply-to">Window Apply To</label>
                <select id="motion-proc-window-apply-to" value=${wizard.motion_proc_window_apply_to || "both"} onChange=${e => update("motion_proc_window_apply_to", e.target.value)}>
                  ${MOTION_WINDOW_APPLY_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
                </select>
              </div>
            ` : null}

            <div className="field">
              <label htmlFor="motion-proc-trim-start">Trim Start (s)<${HelpTip} id="motion_proc_trim_start" /></label>
              <input id="motion-proc-trim-start" type="number" min="0" step="0.01" value=${wizard.motion_proc_trim_start ?? 0} onInput=${e => update("motion_proc_trim_start", Math.max(0, parseFloat(e.target.value) || 0))} />
            </div>
            <div className="field">
              <label htmlFor="motion-proc-trim-end">Trim End (s)<${HelpTip} id="motion_proc_trim_end" /></label>
              <input id="motion-proc-trim-end" type="number" min="0" step="0.01" value=${wizard.motion_proc_trim_end ?? 0} onInput=${e => update("motion_proc_trim_end", Math.max(0, parseFloat(e.target.value) || 0))} />
            </div>
            <label className="field inline-checkbox" htmlFor="motion-proc-trim-taper">
              <span>Trim Taper</span>
              <input id="motion-proc-trim-taper" type="checkbox" checked=${wizard.motion_proc_trim_taper === true} onChange=${e => update("motion_proc_trim_taper", e.target.checked)} />
            </label>

            <div className="field">
              <label htmlFor="motion-proc-pad-front">Pad Front (s)<${HelpTip} id="motion_proc_pad_front" /></label>
              <input id="motion-proc-pad-front" type="number" min="0" step="0.01" value=${wizard.motion_proc_pad_front ?? 0} onInput=${e => update("motion_proc_pad_front", Math.max(0, parseFloat(e.target.value) || 0))} />
            </div>
            <div className="field">
              <label htmlFor="motion-proc-pad-end">Pad End (s)<${HelpTip} id="motion_proc_pad_end" /></label>
              <input id="motion-proc-pad-end" type="number" min="0" step="0.01" value=${wizard.motion_proc_pad_end ?? 0} onInput=${e => update("motion_proc_pad_end", Math.max(0, parseFloat(e.target.value) || 0))} />
            </div>
            <div className="field">
              <label htmlFor="motion-proc-pad-method">Pad Method</label>
              <select id="motion-proc-pad-method" value=${wizard.motion_proc_pad_method || "zeros"} onChange=${e => update("motion_proc_pad_method", e.target.value)}>
                ${MOTION_PADDING_METHOD_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="motion-proc-pad-method-front">Pad Method Front</label>
              <select id="motion-proc-pad-method-front" value=${wizard.motion_proc_pad_method_front || ""} onChange=${e => update("motion_proc_pad_method_front", e.target.value || null)}>
                <option value="">Use shared method</option>
                ${MOTION_PADDING_METHOD_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="motion-proc-pad-method-end">Pad Method End</label>
              <select id="motion-proc-pad-method-end" value=${wizard.motion_proc_pad_method_end || ""} onChange=${e => update("motion_proc_pad_method_end", e.target.value || null)}>
                <option value="">Use shared method</option>
                ${MOTION_PADDING_METHOD_OPTIONS.map(option => html`<option key=${option.value} value=${option.value}>${option.label}</option>`)}
              </select>
            </div>
            <label className="field inline-checkbox" htmlFor="motion-proc-pad-smooth">
              <span>Smooth Padding</span>
              <input id="motion-proc-pad-smooth" type="checkbox" checked=${wizard.motion_proc_pad_smooth === true} onChange=${e => update("motion_proc_pad_smooth", e.target.checked)} />
            </label>

            <div className="field">
              <label htmlFor="motion-proc-spectrum-damping">Spectrum Damping Ratio</label>
              <input id="motion-proc-spectrum-damping" type="number" min="0.001" max="0.2" step="0.005" value=${wizard.motion_proc_spectrum_damping_ratio ?? 0.05} onInput=${e => update("motion_proc_spectrum_damping_ratio", parseFloat(e.target.value) || 0.05)} />
            </div>
          </div>
        </details>
        ${wizard.motion_path ? html`
          <div className="motion-audit-shell">
            <div className="metric-row compact">
              <div className="metric-card compact"><span>Scale Mode</span><b>${wizard.scale_mode || "none"}</b></div>
              <div className="metric-card compact"><span>Processing Order</span><b>${wizard.motion_proc_processing_order || "filter_first"}</b></div>
              <div className="metric-card compact"><span>Baseline</span><b>${wizard.motion_proc_baseline_on ? (wizard.motion_proc_baseline_method || "poly4") : "Off"}</b></div>
              <div className="metric-card compact"><span>Filter</span><b>${wizard.motion_proc_filter_on ? (wizard.motion_proc_filter_config || "bandpass") : "Off"}</b></div>
              <div className="metric-card compact"><span>Window</span><b>${wizard.motion_proc_window_on ? (wizard.motion_proc_window_type || "hanning") : "Off"}</b></div>
            </div>
          </div>
        ` : null}
      </section>

      <!-- Motion Tools -->
      ${wizard.motion_path ? html`
        <section className="motion-section">
          <div className="section-head">
            <h4>Motion Tools</h4>
            <p>Preview preprocessing decisions before analysis: time-step reduction and frequency-domain kappa estimation.</p>
          </div>
          <div className="row">
            <div className="field">
              <label htmlFor="tool-reduce-target-dt">Target dt (s)</label>
              <input
                id="tool-reduce-target-dt"
                type="number"
                step="0.0005"
                min="0.0001"
                placeholder="optional"
                value=${reduceTargetDt}
                onInput=${e => setReduceTargetDt(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="tool-reduce-factor">Reduction Factor</label>
              <input
                id="tool-reduce-factor"
                type="number"
                min="2"
                max="20"
                step="1"
                value=${reduceFactor}
                onInput=${e => setReduceFactor(Math.max(2, Number(e.target.value) || 2))}
              />
            </div>
            <div className="field" style=${{ display: "flex", alignItems: "end" }}>
              <button type="button" className="btn btn-sm" onClick=${runTimeStepReduction} disabled=${reduceBusy}>
                ${reduceBusy ? "Running..." : "Preview Time-Step Reduction"}
              </button>
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label htmlFor="tool-kappa-min">κ Freq Min (Hz)</label>
              <input
                id="tool-kappa-min"
                type="number"
                min="0.1"
                step="0.5"
                value=${kappaMinHz}
                onInput=${e => setKappaMinHz(Number(e.target.value) || 10)}
              />
            </div>
            <div className="field">
              <label htmlFor="tool-kappa-max">κ Freq Max (Hz)</label>
              <input
                id="tool-kappa-max"
                type="number"
                min="0.2"
                step="0.5"
                value=${kappaMaxHz}
                onInput=${e => setKappaMaxHz(Number(e.target.value) || 40)}
              />
            </div>
            <div className="field" style=${{ display: "flex", alignItems: "end" }}>
              <button type="button" className="btn btn-sm" onClick=${runKappaEstimator} disabled=${kappaBusy}>
                ${kappaBusy ? "Running..." : "Estimate κ"}
              </button>
            </div>
          </div>
          ${toolError ? html`<p className="error-text" style=${{ marginTop: "0.2rem" }}>${toolError}</p>` : null}
          ${reducePreview ? html`
            <div style=${{ marginTop: "0.5rem" }}>
              <div className="metric-row">
                <div className="metric-card"><span>dt Original (s)</span><b>${fmt(reducePreview.dt_original, 5)}</b></div>
                <div className="metric-card"><span>dt Reduced (s)</span><b>${fmt(reducePreview.dt_reduced, 5)}</b></div>
                <div className="metric-card"><span>PGA Original (m/s²)</span><b>${fmt(reducePreview.pga_original_m_s2, 4)}</b></div>
                <div className="metric-card"><span>PGA Reduced (m/s²)</span><b>${fmt(reducePreview.pga_reduced_m_s2, 4)}</b></div>
              </div>
              <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.2rem" }}>
                <p className="muted" style=${{ margin: 0, fontSize: "0.72rem" }}>${reducePreview.note || ""}</p>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick=${() => {
                    const rows = reducePreview.time_s.map((t, i) => [
                      fmt(t, 6),
                      fmt(reducePreview.acc_original_m_s2[i], 8),
                      fmt(reducePreview.acc_reduced_m_s2[i], 8),
                    ]);
                    downloadCsv(
                      "motion_timestep_reduction.csv",
                      ["time_s", "acc_original_m_s2", "acc_reduced_m_s2"],
                      rows,
                    );
                  }}>
                  Export Reduction CSV
                </button>
              </div>
              <${MultiSeriesChart}
                title="Time-Step Reduction Preview"
                series=${[
                  { x: reducePreview.time_s, y: reducePreview.acc_original_m_s2, label: "Original", color: "#BDC3C7" },
                  { x: reducePreview.time_s, y: reducePreview.acc_reduced_m_s2, label: "Reduced", color: "#E74C3C" },
                ]}
                xLabel="Time (s)"
                yLabel="Acceleration (m/s²)"
              />
            </div>
          ` : null}
          ${kappaPreview ? html`
            <div style=${{ marginTop: "0.5rem" }}>
              <div className="metric-row">
                <div className="metric-card"><span>Kappa (κ)</span><b>${kappaPreview.kappa != null ? fmt(kappaPreview.kappa, 5) : "—"}</b></div>
                <div className="metric-card"><span>κ R²</span><b>${kappaPreview.kappa_r2 != null ? fmt(kappaPreview.kappa_r2, 4) : "—"}</b></div>
                <div className="metric-card"><span>Freq Min (Hz)</span><b>${fmt(kappaMinHz, 1)}</b></div>
                <div className="metric-card"><span>Freq Max (Hz)</span><b>${fmt(kappaMaxHz, 1)}</b></div>
              </div>
              <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.2rem" }}>
                <p className="muted" style=${{ margin: 0, fontSize: "0.72rem" }}>${kappaPreview.note || ""}</p>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick=${() => {
                    const nRows = Math.max(
                      kappaPreview.freq_hz?.length || 0,
                      kappaPreview.fit_freq_hz?.length || 0,
                    );
                    const rows = Array.from({ length: nRows }, (_, i) => [
                      fmt(kappaPreview.freq_hz?.[i], 6),
                      fmt(kappaPreview.fas_amplitude?.[i], 10),
                      fmt(kappaPreview.fit_freq_hz?.[i], 6),
                      fmt(kappaPreview.fit_amplitude?.[i], 10),
                    ]);
                    downloadCsv(
                      "motion_kappa_estimate.csv",
                      ["freq_hz", "fas_amplitude", "fit_freq_hz", "fit_amplitude"],
                      rows,
                    );
                  }}>
                  Export Kappa CSV
                </button>
              </div>
              ${(kappaPreview.freq_hz || []).length > 2 ? html`
                <${MultiSeriesChart}
                  title="Kappa Fit in Frequency Domain"
                  series=${[
                    { x: kappaPreview.freq_hz, y: kappaPreview.fas_amplitude, label: "FAS", color: "#16A085" },
                    { x: kappaPreview.fit_freq_hz || [], y: kappaPreview.fit_amplitude || [], label: "κ fit", color: "#E74C3C" },
                  ]}
                  xLabel="Frequency (Hz)"
                  yLabel="Fourier Amplitude (m/s)"
                  logX=${true}
                />
              ` : null}
            </div>
          ` : null}
        </section>
      ` : null}

      ${wizard.motion_path ? html`
        <section className="motion-section">
          <div className="section-head">
            <h4>Preprocessing Audit Trail</h4>
            <p>Keep a readable record of the transformations and previews applied before the motion enters the solver.</p>
          </div>
          <ul style=${{ margin: 0, paddingLeft: "1rem", fontSize: "0.74rem", color: "var(--ink-70)" }}>
            <li>Scale mode: ${wizard.scale_mode || "none"}${wizard.scale_mode === "scale_factor" ? ` (factor=${fmt(wizard.scale_factor || 1, 3)})` : ""}${wizard.scale_mode === "scale_to_pga" ? ` (target=${fmt((wizard.target_pga_g || 0), 3)} g)` : ""}</li>
            <li>Processing order: ${wizard.motion_proc_processing_order || "filter_first"}</li>
            <li>Baseline correction: ${wizard.motion_proc_baseline_on ? wizard.motion_proc_baseline_method || "poly4" : "off"}</li>
            <li>Filter: ${wizard.motion_proc_filter_on ? `${wizard.motion_proc_filter_config || "bandpass"} (${wizard.motion_proc_filter_domain || "time"})` : "off"}</li>
            ${(toolAuditTrail || []).map((step, idx) => html`
              <li key=${`audit-step-${idx}`}>${step.stamp} — ${step.action}: ${step.details}</li>
            `)}
          </ul>
        </section>
      ` : null}

      ${preview ? (() => {
        const inputUnitKey = String(preview.inputUnits || wizard.motion_units || "m/s2").trim().toLowerCase();
        const inputUnitLabel = motionUnitLabel(inputUnitKey);
        const showSiPga = inputUnitKey !== "m/s2" && inputUnitKey !== "m/s^2";
        const showGPga = inputUnitKey !== "g";
        const rawOverlayAvailable = preview.showUncorrectedPreview && (preview.rawTime?.length || 0) > 1;
        const accelerationSeries = rawOverlayAvailable && accelerationView === "overlay"
          ? [
            { x: preview.rawTime, y: preview.rawAccInput, label: "Raw", color: "#94A3B8" },
            { x: preview.time, y: preview.accInput, label: "Processed", color: "#D35400" },
          ]
          : accelerationView === "raw" && rawOverlayAvailable
            ? [{ x: preview.rawTime, y: preview.rawAccInput, label: "Raw", color: "#94A3B8" }]
            : [{ x: preview.time, y: preview.accInput, label: rawOverlayAvailable ? "Processed" : "Acceleration", color: "#D35400" }];
        return html`
          <section className="motion-section">
            <div className="section-head">
              <h4>Preview & Diagnostics</h4>
              <p>Inspect interpreted units, waveform, derived kinematics and response spectra before preprocessing commits a run-ready CSV.</p>
            </div>
            <div className="metric-row motion-preview-metrics">
              <div className="metric-card"><span>Input Units</span><b>${inputUnitLabel}</b></div>
              <div className="metric-card">
                <span>PGA (${inputUnitLabel})</span>
                <b>${fmt(preview.pgaInput, 4)}</b>
              </div>
              ${showSiPga ? html`
                <div className="metric-card"><span>PGA (m/s²)</span><b>${fmt(preview.pga, 4)}</b></div>
              ` : null}
              ${showGPga ? html`
                <div className="metric-card"><span>PGA (g)</span><b>${fmt(preview.pgaG ?? ((preview.pga || 0) / 9.81), 4)}</b></div>
              ` : null}
              ${rawOverlayAvailable ? html`
                <div className="metric-card"><span>Raw PGA (${inputUnitLabel})</span><b>${fmt(preview.rawPgaInput, 4)}</b></div>
              ` : null}
              <div className="metric-card"><span>Peak Velocity (m/s)</span><b>${fmt(preview.pgv, 4)}</b></div>
              <div className="metric-card"><span>Peak Displ. (m)</span><b>${fmt(preview.pgd, 4)}</b></div>
              <div className="metric-card"><span>Peak SA (${inputUnitLabel})</span><b>${fmt(preview.saMax, 4)}</b></div>
              <div className="metric-card"><span>dt (s)</span><b>${fmt(preview.dt, 5)}</b></div>
              <div className="metric-card"><span>Duration (s)</span><b>${fmt(preview.duration || preview.time?.[preview.time.length - 1], 2)}</b></div>
              ${preview.npts ? html`<div className="metric-card"><span>Points</span><b>${preview.npts}</b></div>` : null}
            </div>
            <div className="motion-preview-toolbar">
              ${rawOverlayAvailable ? html`
                <div className="motion-segmented">
                  <button type="button" className=${"btn btn-sm" + (accelerationView === "overlay" ? " btn-accent" : "")} onClick=${() => setAccelerationView("overlay")}>Overlay Raw + Processed</button>
                  <button type="button" className=${"btn btn-sm" + (accelerationView === "processed" ? " btn-accent" : "")} onClick=${() => setAccelerationView("processed")}>Processed Only</button>
                  <button type="button" className=${"btn btn-sm" + (accelerationView === "raw" ? " btn-accent" : "")} onClick=${() => setAccelerationView("raw")}>Raw Only</button>
                </div>
              ` : null}
              <div className="motion-export-row">
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick=${() => {
                    const rows = (preview.time || []).map((t, i) => [
                      fmt(t, 6),
                      fmt(preview.acc[i], 8),
                      fmt(preview.vel[i], 8),
                      fmt(preview.disp[i], 8),
                    ]);
                    downloadCsv("processed_motion_preview.csv", ["time_s", "acc_m_s2", "vel_m_s", "disp_m"], rows);
                  }}>
                  Export Processed History
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick=${() => {
                    const rows = (preview.period || []).map((period, i) => [
                      fmt(period, 6),
                      fmt(preview.saInput?.[i], 8),
                      fmt(preview.sv?.[i], 8),
                      fmt(preview.sd?.[i], 8),
                    ]);
                    downloadCsv("motion_spectra_preview.csv", ["period_s", "sa_input_units", "sv_m_s", "sd_m"], rows);
                  }}>
                  Export Spectra CSV
                </button>
                ${rawOverlayAvailable ? html`
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick=${() => {
                      const nRows = Math.max(preview.rawTime?.length || 0, preview.time?.length || 0);
                      const rows = Array.from({ length: nRows }, (_, i) => [
                        fmt(preview.rawTime?.[i], 6),
                        fmt(preview.rawAccInput?.[i], 8),
                        fmt(preview.time?.[i], 6),
                        fmt(preview.accInput?.[i], 8),
                      ]);
                      downloadCsv("raw_vs_processed_motion.csv", ["raw_time_s", "raw_acc_input_units", "processed_time_s", "processed_acc_input_units"], rows);
                    }}>
                    Export Raw vs Processed
                  </button>
                ` : null}
              </div>
            </div>
            <div className="motion-preview-grid">
              <${MultiSeriesChart}
                title="Acceleration"
                subtitle=${`displayed in ${inputUnitLabel}`}
                series=${accelerationSeries}
                xLabel="Time (s)" yLabel=${`Acceleration (${inputUnitLabel})`}
                w=${420} h=${220}
              />
              <${ChartCard}
                title="Velocity"
                subtitle="integrated from acceleration"
                x=${preview.time} y=${preview.vel}
                xLabel="Time (s)" yLabel="Velocity (m/s)"
                color="#2980B9" w=${420} h=${220}
              />
              <${ChartCard}
                title="Displacement"
                subtitle="double integrated"
                x=${preview.time} y=${preview.disp}
                xLabel="Time (s)" yLabel="Displacement (m)"
                color="#16A085" w=${420} h=${220}
              />
              <${ChartCard}
                title="SA Spectrum"
                subtitle=${`5% damping • ${inputUnitLabel}`}
                x=${preview.period} y=${preview.saInput}
                xLabel="Period (s)" yLabel=${`SA (${inputUnitLabel})`}
                color="#8E44AD" logX=${true} w=${420} h=${220}
              />
              <${ChartCard}
                title="SV Spectrum"
                subtitle="5% damping"
                x=${preview.period} y=${preview.sv}
                xLabel="Period (s)" yLabel="SV (m/s)"
                color="#C0392B" logX=${true} w=${420} h=${220}
              />
              <${ChartCard}
                title="SD Spectrum"
                subtitle="5% damping"
                x=${preview.period} y=${preview.sd}
                xLabel="Period (s)" yLabel="SD (m)"
                color="#2C3E50" logX=${true} w=${420} h=${220}
              />
            </div>
          </section>
        `;
      })() : null}
    </div>
  `;
}
