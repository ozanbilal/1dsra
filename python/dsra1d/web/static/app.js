
import React, { useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);

const WIZARD_STEPS = [
  { id: "analysis_step", title: "1) Analysis Type" },
  { id: "profile_step", title: "2) Soil Profile" },
  { id: "motion_step", title: "3) Input Motion" },
  { id: "damping_step", title: "4) Damping" },
  { id: "control_step", title: "5) Analysis Control" },
];

const RESULT_TABS = [
  "Time Histories",
  "Stress-Strain",
  "Spectral",
  "Profile",
  "Mobilized Strength",
  "Convergence",
];

const PROFILE_PRESETS = {
  "five-main-layers": [
    { name: "Layer-1", thickness_m: 2.0, unit_weight_kN_m3: 17.5, vs_m_s: 140.0, material: "pm4sand" },
    { name: "Layer-2", thickness_m: 3.0, unit_weight_kN_m3: 18.0, vs_m_s: 180.0, material: "pm4sand" },
    { name: "Layer-3", thickness_m: 5.0, unit_weight_kN_m3: 18.5, vs_m_s: 240.0, material: "pm4silt" },
    { name: "Layer-4", thickness_m: 8.0, unit_weight_kN_m3: 19.0, vs_m_s: 320.0, material: "pm4sand" },
    { name: "Layer-5", thickness_m: 12.0, unit_weight_kN_m3: 19.5, vs_m_s: 520.0, material: "elastic" },
  ],
  "soft-over-stiff": [
    { name: "Soft-Cap", thickness_m: 4.0, unit_weight_kN_m3: 17.2, vs_m_s: 120.0, material: "pm4silt" },
    { name: "Transition", thickness_m: 6.0, unit_weight_kN_m3: 18.0, vs_m_s: 180.0, material: "pm4sand" },
    { name: "Dense-Sand", thickness_m: 10.0, unit_weight_kN_m3: 19.0, vs_m_s: 330.0, material: "pm4sand" },
    { name: "Very-Dense", thickness_m: 12.0, unit_weight_kN_m3: 19.5, vs_m_s: 520.0, material: "elastic" },
  ],
};

const TEMPLATE_DESCRIPTIONS = {
  "effective-stress":
    "General effective-stress starter with mixed PM4Sand/PM4Silt layers and elastic half-space boundary.",
  "effective-stress-strict-plus":
    "Effective-stress starter with strict_plus PM4 validation and conservative default u-p setup.",
  "pm4sand-calibration":
    "Calibration-oriented PM4Sand stack for layer-by-layer Dr/G0/hpo tuning workflows.",
  "pm4silt-calibration":
    "Calibration-oriented PM4Silt stack for Su/Su_Rat/G_o/h_po sensitivity studies.",
  "mkz-gqh-mock":
    "Native MKZ/GQH mock baseline for constitutive curve setup without OpenSees dependency.",
  "mkz-gqh-eql":
    "Native equivalent-linear (EQL) MKZ/GQH template for strain-compatible iteration runs.",
  "mkz-gqh-nonlinear":
    "Native nonlinear time-domain MKZ/GQH template with stateful hysteretic branch updates.",
};

const MATERIAL_PARAM_PRESETS = {
  pm4sand: { Dr: 0.45, G0: 600.0, hpo: 0.53 },
  pm4silt: { Su: 35.0, Su_Rat: 0.25, G_o: 500.0, h_po: 0.6 },
  mkz: { gmax: 70000.0, gamma_ref: 0.0012, damping_min: 0.01, damping_max: 0.1, reload_factor: 2.0 },
  gqh: {
    gmax: 110000.0,
    gamma_ref: 0.001,
    a1: 1.0,
    a2: 0.45,
    m: 2.0,
    damping_min: 0.01,
    damping_max: 0.12,
    reload_factor: 1.6,
  },
  elastic: { nu: 0.3 },
};

function materialParamDefaults(material) {
  const key = String(material || "pm4sand").toLowerCase();
  const base = MATERIAL_PARAM_PRESETS[key] || {};
  return { ...base };
}

function materialParamRows(material, rawParams) {
  const defaults = materialParamDefaults(material);
  const params = rawParams && typeof rawParams === "object" ? rawParams : {};
  const defaultKeys = Object.keys(defaults);
  const extraKeys = Object.keys(params).filter((k) => !defaultKeys.includes(k));
  const keys = [...defaultKeys, ...extraKeys];
  return keys.map((key) => {
    const raw = params[key];
    const value = Number.isFinite(Number(raw)) ? Number(raw) : defaults[key];
    return { key, value: Number.isFinite(Number(value)) ? Number(value) : 0.0 };
  });
}

function parseOptionalArgs(rawText) {
  const text = String(rawText || "").trim();
  if (!text) return [];
  return text
    .split(/[,\s]+/)
    .map((token) => Number(token))
    .filter((value) => Number.isFinite(value));
}

function csvEscape(value) {
  const raw = String(value ?? "");
  const escaped = raw.replace(/"/g, '""');
  if (/[",\n]/.test(raw)) return `"${escaped}"`;
  return escaped;
}

function parseCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(current);
      current = "";
      continue;
    }
    current += ch;
  }
  out.push(current);
  return out;
}

function toNum(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function hasText(value) {
  return String(value || "").trim().length > 0;
}

function isPositive(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0;
}

function buildWizardValidation(wizard) {
  const analysis = wizard?.analysis_step || {};
  const profile = wizard?.profile_step || {};
  const motion = wizard?.motion_step || {};
  const damping = wizard?.damping_step || {};
  const control = wizard?.control_step || {};
  const layers = Array.isArray(profile.layers) ? profile.layers : [];
  const issues = {
    analysis_step: [],
    profile_step: [],
    motion_step: [],
    damping_step: [],
    control_step: [],
  };

  if (!hasText(analysis.project_name)) {
    issues.analysis_step.push("Project Name is required.");
  }
  if (!hasText(analysis.boundary_condition)) {
    issues.analysis_step.push("Boundary Condition is required.");
  }
  if (!hasText(analysis.solver_backend)) {
    issues.analysis_step.push("Solver Backend is required.");
  }

  if (layers.length === 0) {
    issues.profile_step.push("At least one layer is required.");
  }
  layers.forEach((layer, idx) => {
    const label = layer?.name || `Layer-${idx + 1}`;
    if (!isPositive(layer?.thickness_m)) {
      issues.profile_step.push(`${label}: thickness must be > 0.`);
    }
    if (!isPositive(layer?.unit_weight_kN_m3)) {
      issues.profile_step.push(`${label}: unit weight must be > 0.`);
    }
    if (!isPositive(layer?.vs_m_s)) {
      issues.profile_step.push(`${label}: Vs must be > 0.`);
    }
  });

  if (!hasText(motion.motion_path)) {
    issues.motion_step.push("Motion Path is required to run analysis.");
  }
  if (!hasText(motion.units)) {
    issues.motion_step.push("Motion units are required.");
  }

  if (!hasText(damping.mode)) {
    issues.damping_step.push("Damping mode is required.");
  }

  if (!isPositive(control.f_max)) {
    issues.control_step.push("f_max must be > 0.");
  }
  if (control.dt !== null && control.dt !== undefined && !isPositive(control.dt)) {
    issues.control_step.push("dt must be > 0 when specified.");
  }
  if (!hasText(control.output_dir)) {
    issues.control_step.push("Output Dir is required.");
  }

  return {
    analysis_step: { valid: issues.analysis_step.length === 0, issues: issues.analysis_step },
    profile_step: { valid: issues.profile_step.length === 0, issues: issues.profile_step },
    motion_step: { valid: issues.motion_step.length === 0, issues: issues.motion_step },
    damping_step: { valid: issues.damping_step.length === 0, issues: issues.damping_step },
    control_step: { valid: issues.control_step.length === 0, issues: issues.control_step },
  };
}

function alignedRatioSeries(xRef, yRef, xTar, yTar) {
  const n = Math.min(
    Array.isArray(xRef) ? xRef.length : 0,
    Array.isArray(yRef) ? yRef.length : 0,
    Array.isArray(xTar) ? xTar.length : 0,
    Array.isArray(yTar) ? yTar.length : 0
  );
  const x = [];
  const y = [];
  for (let i = 0; i < n; i += 1) {
    const xv = Number(xTar[i]);
    const a = Number(yTar[i]);
    const b = Number(yRef[i]);
    if (!Number.isFinite(xv) || !Number.isFinite(a) || !Number.isFinite(b)) continue;
    if (Math.abs(b) < 1e-12) continue;
    x.push(xv);
    y.push(a / b);
  }
  return { x, y };
}

function alignedDeltaSeries(xRef, yRef, xTar, yTar) {
  const n = Math.min(
    Array.isArray(xRef) ? xRef.length : 0,
    Array.isArray(yRef) ? yRef.length : 0,
    Array.isArray(xTar) ? xTar.length : 0,
    Array.isArray(yTar) ? yTar.length : 0
  );
  const x = [];
  const y = [];
  for (let i = 0; i < n; i += 1) {
    const xv = Number(xTar[i]);
    const a = Number(yTar[i]);
    const b = Number(yRef[i]);
    if (!Number.isFinite(xv) || !Number.isFinite(a) || !Number.isFinite(b)) continue;
    x.push(xv);
    y.push(a - b);
  }
  return { x, y };
}

function fmt(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Number(value).toFixed(digits);
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function convergenceSeverityClass(severity) {
  const key = String(severity || "").toLowerCase();
  if (key === "critical") return "diag-critical";
  if (key === "warning" || key === "warn") return "diag-warning";
  if (key === "ok" || key === "pass") return "diag-ok";
  return "diag-neutral";
}

function runSeverityKey(severity) {
  const key = String(severity || "").toLowerCase();
  if (key === "ok" || key === "pass") return "ok";
  if (key === "warning" || key === "warn") return "warning";
  if (key === "critical" || key === "error" || key === "bad") return "critical";
  return "neutral";
}

function runSeverityChipClass(severity) {
  const key = runSeverityKey(severity);
  if (key === "ok") return "chip-ok";
  if (key === "warning") return "chip-warn";
  if (key === "critical") return "chip-bad";
  return "chip-neutral";
}

function runSeverityLabel(run) {
  const mode = String(run?.convergence_mode || "none");
  const key = runSeverityKey(run?.convergence_severity);
  if (mode === "none") return "health:n/a";
  return `health:${key}`;
}

function runWarningHint(run) {
  if (!run || typeof run !== "object") return "";
  const divideByZero = Number(run.solver_divide_by_zero_count);
  if (Number.isFinite(divideByZero) && divideByZero > 0) {
    return `divide_by_zero:${Math.round(divideByZero)}`;
  }
  const fallbackFailed = Number(run.solver_dynamic_fallback_failed_count);
  if (Number.isFinite(fallbackFailed) && fallbackFailed > 0) {
    return `fallback_failed:${Math.round(fallbackFailed)}`;
  }
  const failedConverge = Number(run.solver_failed_converge_count);
  if (Number.isFinite(failedConverge) && failedConverge > 0) {
    return `failed_converge:${Math.round(failedConverge)}`;
  }
  const warnings = Number(run.solver_warning_count);
  if (Number.isFinite(warnings) && warnings > 0) return `warnings:${Math.round(warnings)}`;
  if (run.convergence_mode === "eql" && run.converged === false) return "eql:not-converged";
  return "";
}

function buildConvergenceView(summary) {
  const raw = summary?.convergence;
  if (!raw || raw.available === false) {
    return {
      mode: "none",
      available: false,
      severity: "neutral",
      title: "No convergence diagnostics",
      subtitle: "No EQL or solver diagnostics available for this run.",
      cards: [],
      raw: raw || { available: false },
    };
  }

  if (raw.iterations !== undefined || raw.max_change_last !== undefined) {
    const converged = Boolean(raw.converged);
    return {
      mode: "eql",
      available: true,
      severity: converged ? "ok" : "warning",
      title: converged ? "EQL converged" : "EQL not converged",
      subtitle: "Equivalent-linear iteration diagnostics",
      cards: [
        { label: "Mode", value: "EQL" },
        { label: "Converged", value: converged ? "yes" : "no" },
        { label: "Iterations", value: String(raw.iterations ?? "n/a") },
        { label: "max_change_last", value: fmt(raw.max_change_last, 6) },
        { label: "max_change_max", value: fmt(raw.max_change_max, 6) },
      ],
      raw,
    };
  }

  const warningCount = toFiniteNumber(raw.warning_count);
  const failedConverge = toFiniteNumber(raw.failed_converge_count);
  const analyzeFailed = toFiniteNumber(raw.analyze_failed_count);
  const divideByZero = toFiniteNumber(raw.divide_by_zero_count);
  const initCount = toFiniteNumber(raw.pm4_initialize_count);
  const fallbackFailed = toFiniteNumber(raw.dynamic_fallback_failed);
  const timeoutConfigured = toFiniteNumber(raw.timeout_s_configured);
  const timeoutEffective = toFiniteNumber(raw.timeout_s_effective);
  const timeoutRecovered = Boolean(raw.timeout_recovered);
  const timeoutRecoveredCoverage = toFiniteNumber(raw.timeout_recovered_coverage);
  const severity = String(raw.severity || "unknown").toLowerCase();
  const source = String(raw.source || "opensees_logs");
  const isTimeoutMetaOnly =
    source === "opensees_timeout_recovered" || source === "opensees_meta";

  return {
    mode: "solver",
    available: true,
    severity,
    title:
      timeoutRecovered
        ? "Solver timeout recovered outputs"
        : severity === "ok"
        ? "Solver diagnostics clean"
        : severity === "critical"
          ? "Solver diagnostics critical"
          : "Solver diagnostics warning",
    subtitle: isTimeoutMetaOnly
      ? "OpenSees runtime timeout/metadata diagnostics"
      : "OpenSees log-derived quality diagnostics",
    cards: [
      { label: "Source", value: source },
      { label: "Severity", value: severity || "unknown" },
      { label: "warning_count", value: fmt(warningCount ?? NaN, 0) },
      { label: "failed_converge_count", value: fmt(failedConverge ?? NaN, 0) },
      { label: "analyze_failed_count", value: fmt(analyzeFailed ?? NaN, 0) },
      { label: "divide_by_zero_count", value: fmt(divideByZero ?? NaN, 0) },
      { label: "pm4_initialize_count", value: fmt(initCount ?? NaN, 0) },
      { label: "dynamic_fallback_failed", value: fmt(fallbackFailed ?? NaN, 0) },
      { label: "timeout_s_configured", value: fmt(timeoutConfigured ?? NaN, 0) },
      { label: "timeout_s_effective", value: fmt(timeoutEffective ?? NaN, 0) },
      { label: "timeout_recovered", value: timeoutRecovered ? "yes" : "no" },
      { label: "timeout_recovered_coverage", value: fmt(timeoutRecoveredCoverage ?? NaN, 3) },
    ],
    raw,
  };
}

function buildProfileHealthCards(view) {
  if (!view || !view.available) return [];
  if (view.mode === "eql") {
    const pick = new Set(["Converged", "Iterations", "max_change_last", "max_change_max"]);
    return (view.cards || []).filter((c) => pick.has(c.label));
  }
  if (view.mode === "solver") {
    const pick = new Set([
      "warning_count",
      "failed_converge_count",
      "analyze_failed_count",
      "divide_by_zero_count",
      "dynamic_fallback_failed",
      "timeout_s_configured",
      "timeout_s_effective",
      "timeout_recovered",
      "timeout_recovered_coverage",
    ]);
    return (view.cards || []).filter((c) => pick.has(c.label));
  }
  return [];
}

function normalizeFingerprint(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return "";
  if (text.startsWith("sha256:")) return text.slice(7).trim();
  return text;
}

function isSha256(value) {
  return /^[0-9a-f]{64}$/.test(String(value || "").trim().toLowerCase());
}

function buildReleaseHealth({
  parityLatest,
  parityPrimary,
  releaseSignoff,
  scienceConfidence,
  runSummary,
  selectedRun,
}) {
  const blockers = [];
  const warnings = [];
  const checks = [];

  if (!parityLatest || !parityLatest.found || !parityPrimary) {
    blockers.push("Parity report is missing.");
    checks.push({ label: "parity_report", ok: false, value: "missing" });
  } else {
    const parityOk =
      parityPrimary.all_passed &&
      parityPrimary.backend_ready &&
      parityPrimary.backend_fingerprint_ok &&
      Number(parityPrimary.skipped || 0) === 0;
    checks.push({
      label: "parity_gate",
      ok: parityOk,
      value: `${parityPrimary.ran}/${parityPrimary.total_cases} cov=${fmt(
        Number(parityPrimary.execution_coverage || 0),
        3
      )}`,
    });
    if (!parityOk) {
      const reasons = Array.isArray(parityPrimary.block_reasons)
        ? parityPrimary.block_reasons.filter((v) => String(v || "").trim().length > 0)
        : [];
      blockers.push(`Parity gate failed${reasons.length ? `: ${reasons.join(", ")}` : ""}.`);
    }
  }

  if (!releaseSignoff || !releaseSignoff.found) {
    warnings.push("Release signoff summary not found under current output root.");
    checks.push({ label: "release_signoff_summary", ok: false, value: "missing" });
  } else {
    checks.push({
      label: "release_signoff_summary",
      ok: true,
      value: mini(releaseSignoff.summary_path || ""),
    });
    const strict = Boolean(releaseSignoff.strict_signoff);
    const passed = Boolean(releaseSignoff.signoff_passed);
    const releaseReady = Boolean(releaseSignoff.release_ready);
    const coverage = Number(releaseSignoff.benchmark_execution_coverage || 0);
    checks.push({ label: "strict_signoff", ok: strict, value: strict ? "enabled" : "disabled" });
    checks.push({ label: "signoff_passed", ok: passed, value: passed ? "true" : "false" });
    checks.push({
      label: "release_ready",
      ok: releaseReady,
      value: releaseReady ? "true" : "false",
    });
    checks.push({
      label: "signoff_severity",
      ok: releaseReady || Number(releaseSignoff.severity_score || 0) < 40,
      value: `${releaseSignoff.severity_label || "unknown"} (${fmt(
        Number(releaseSignoff.severity_score || 0),
        0
      )})`,
    });
    checks.push({
      label: "signoff_coverage",
      ok: coverage >= 1.0,
      value: `${releaseSignoff.benchmark_ran || 0}/${releaseSignoff.benchmark_total_cases || 0} cov=${fmt(
        coverage,
        3
      )}`,
    });
    if (!strict) blockers.push("Release signoff summary is not strict-signoff.");
    if (!passed) {
      const failed = Array.isArray(releaseSignoff.condition_failures)
        ? releaseSignoff.condition_failures
        : [];
      blockers.push(
        `Release signoff not passed${failed.length ? `: ${failed.join(", ")}` : ""}.`
      );
    }
    const categories = Array.isArray(releaseSignoff.blocker_categories)
      ? releaseSignoff.blocker_categories.filter((v) => String(v || "").trim().length > 0)
      : [];
    if (categories.length) {
      warnings.push(`Signoff categories: ${categories.join(", ")}`);
    }
  }

  const confidenceRows = Array.isArray(scienceConfidence) ? scienceConfidence : [];
  const parityRow =
    confidenceRows.find((r) => String(r?.suite || "").toLowerCase().includes("opensees-parity")) ||
    null;
  if (!parityRow) {
    blockers.push("Scientific confidence row for opensees-parity is missing.");
    checks.push({ label: "science_row", ok: false, value: "missing" });
  } else {
    checks.push({
      label: "science_row",
      ok: true,
      value: `${parityRow.confidence_tier || "n/a"} | ${parityRow.last_verified_utc || "n/a"}`,
    });
    const matrixFp = normalizeFingerprint(parityRow.binary_fingerprint || "");
    const reportFp = normalizeFingerprint(
      releaseSignoff?.observed_backend_sha256 || parityPrimary?.binary_fingerprint || ""
    );
    const matrixFpOk = isSha256(matrixFp);
    checks.push({ label: "matrix_fingerprint", ok: matrixFpOk, value: mini(matrixFp || "n/a") });
    if (!matrixFpOk) blockers.push("Scientific matrix fingerprint is not a valid sha256.");
    if (matrixFpOk && reportFp && matrixFp !== reportFp) {
      blockers.push("Scientific matrix fingerprint does not match parity report fingerprint.");
      checks.push({
        label: "fingerprint_match",
        ok: false,
        value: `${mini(matrixFp)} != ${mini(reportFp)}`,
      });
    } else if (matrixFpOk && reportFp) {
      checks.push({ label: "fingerprint_match", ok: true, value: "match" });
    }
  }

  if (!selectedRun || !runSummary) {
    warnings.push("No selected run for runtime diagnostics.");
    checks.push({ label: "runtime_diag", ok: true, value: "not evaluated" });
  } else {
    const runOk = String(runSummary.status || "").toLowerCase() === "ok";
    checks.push({
      label: "selected_run",
      ok: runOk,
      value: `${selectedRun.run_id} (${runSummary.status || "unknown"})`,
    });
    if (!runOk) blockers.push("Selected run status is not ok.");

    const conv = runSummary.convergence || {};
    const failedConverge = Number(conv.failed_converge_count || 0);
    const analyzeFailed = Number(conv.analyze_failed_count || 0);
    const divideByZero = Number(conv.divide_by_zero_count || 0);
    const fallbackFailed = Number(conv.dynamic_fallback_failed || 0);
    const warningCount = Number(conv.warning_count || 0);

    if (Number.isFinite(divideByZero) && divideByZero > 0) {
      blockers.push(`Selected run has divide_by_zero_count=${Math.round(divideByZero)}.`);
    }
    if (Number.isFinite(fallbackFailed) && fallbackFailed > 0) {
      blockers.push(
        `Selected run has dynamic_fallback_failed=${Math.round(fallbackFailed)}.`
      );
    }
    if (Number.isFinite(analyzeFailed) && analyzeFailed > 0) {
      blockers.push(`Selected run has analyze_failed_count=${Math.round(analyzeFailed)}.`);
    }
    if (Number.isFinite(failedConverge) && failedConverge > 0) {
      blockers.push(`Selected run has failed_converge_count=${Math.round(failedConverge)}.`);
    }
    if (Number.isFinite(warningCount) && warningCount > 0) {
      warnings.push(`Selected run warning_count=${Math.round(warningCount)}.`);
    }
  }

  return {
    ready: blockers.length === 0,
    blockers,
    warnings,
    checks,
  };
}

function mini(text) {
  if (!text) return "";
  const asText = String(text);
  if (asText.length <= 52) return asText;
  return `${asText.slice(0, 52)}...`;
}

function parentPath(pathValue) {
  const raw = String(pathValue || "").trim();
  if (!raw) return "";
  const normalized = raw.replace(/[\\/]+$/, "");
  const idx = Math.max(normalized.lastIndexOf("/"), normalized.lastIndexOf("\\"));
  if (idx <= 0) return "";
  return normalized.slice(0, idx);
}

async function requestJSON(url, options = undefined) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    let detail = "";
    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        const body = await resp.json();
        if (body && typeof body.detail === "string" && body.detail.trim()) {
          detail = body.detail;
        } else {
          detail = JSON.stringify(body);
        }
      } catch {
        detail = await resp.text();
      }
    } else {
      detail = await resp.text();
    }
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`);
  }
  return resp.json();
}

function bytesToBase64(bytes) {
  const chunk = 0x8000;
  let binary = "";
  for (let i = 0; i < bytes.length; i += chunk) {
    const slice = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode(...slice);
  }
  return btoa(binary);
}

async function fileToBase64(file) {
  const buffer = await file.arrayBuffer();
  return bytesToBase64(new Uint8Array(buffer));
}

const CHART_FRAME = {
  width: 1000,
  height: 280,
  padLeft: 58,
  padRight: 18,
  padTop: 14,
  padBottom: 36,
};

function formatAxisTick(value) {
  if (!Number.isFinite(value)) return "";
  const av = Math.abs(value);
  if (av >= 1e4 || (av > 0 && av < 1e-3)) return value.toExponential(2);
  return Number(value.toFixed(4)).toString();
}

function finitePoints(xValues, yValues) {
  if (!Array.isArray(xValues) || !Array.isArray(yValues)) return [];
  const n = Math.min(xValues.length, yValues.length);
  const out = [];
  for (let i = 0; i < n; i += 1) {
    const x = Number(xValues[i]);
    const y = Number(yValues[i]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    out.push({ x, y });
  }
  return out;
}

function niceStep(range, targetTicks = 5) {
  if (!Number.isFinite(range) || range <= 0) return 1;
  const rough = range / Math.max(targetTicks, 2);
  const power = Math.pow(10, Math.floor(Math.log10(rough)));
  const ratio = rough / power;
  if (ratio <= 1.5) return 1 * power;
  if (ratio <= 3) return 2 * power;
  if (ratio <= 7) return 5 * power;
  return 10 * power;
}

function buildTicks(minVal, maxVal, targetTicks = 5) {
  const lo = Number(minVal);
  const hi = Number(maxVal);
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [];
  if (Math.abs(hi - lo) < 1e-12) return [lo];
  const step = niceStep(hi - lo, targetTicks);
  const start = Math.floor(lo / step) * step;
  const end = Math.ceil(hi / step) * step;
  const ticks = [];
  for (let v = start; v <= end + step * 0.5; v += step) {
    if (v < lo - step * 0.5 || v > hi + step * 0.5) continue;
    ticks.push(Number(v.toPrecision(12)));
  }
  if (ticks.length === 0) return [lo, hi];
  if (ticks.length === 1 && Math.abs(hi - lo) > 1e-12) return [lo, hi];
  return ticks;
}

function buildChartGeometry(series) {
  const normalized = (Array.isArray(series) ? series : [])
    .map((s, idx) => ({
      key: s?.key || `series-${idx}`,
      name: s?.name || `Series ${idx + 1}`,
      color: s?.color || pickOverlayColor(idx),
      points: finitePoints(s?.x || [], s?.y || []),
    }))
    .filter((s) => s.points.length >= 2);
  if (normalized.length === 0) return null;

  let xMin = Infinity;
  let xMax = -Infinity;
  let yMin = Infinity;
  let yMax = -Infinity;
  normalized.forEach((s) => {
    s.points.forEach((p) => {
      if (p.x < xMin) xMin = p.x;
      if (p.x > xMax) xMax = p.x;
      if (p.y < yMin) yMin = p.y;
      if (p.y > yMax) yMax = p.y;
    });
  });
  if (!Number.isFinite(xMin) || !Number.isFinite(xMax) || !Number.isFinite(yMin) || !Number.isFinite(yMax)) {
    return null;
  }
  if (Math.abs(xMax - xMin) < 1e-12) xMax = xMin + 1.0;
  if (Math.abs(yMax - yMin) < 1e-12) yMax = yMin + 1.0;

  const yPad = 0.06 * (yMax - yMin);
  yMin -= yPad;
  yMax += yPad;

  const { width, height, padLeft, padRight, padTop, padBottom } = CHART_FRAME;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;
  const xToPx = (x) => padLeft + ((x - xMin) / (xMax - xMin)) * innerW;
  const yToPx = (y) => height - padBottom - ((y - yMin) / (yMax - yMin)) * innerH;

  const paths = normalized.map((s) => {
    const pts = s.points.map((p) => `${xToPx(p.x).toFixed(2)},${yToPx(p.y).toFixed(2)}`).join(" ");
    return { key: s.key, name: s.name, color: s.color, points: pts };
  });

  const xTicks = buildTicks(xMin, xMax, 6).map((v) => ({
    value: v,
    px: xToPx(v),
    label: formatAxisTick(v),
  }));
  const yTicks = buildTicks(yMin, yMax, 5).map((v) => ({
    value: v,
    py: yToPx(v),
    label: formatAxisTick(v),
  }));

  return {
    width,
    height,
    padLeft,
    padRight,
    padTop,
    padBottom,
    paths,
    xTicks,
    yTicks,
  };
}

function ChartCard({ title, subtitle, x, y, color = "var(--copper)" }) {
  const geometry = useMemo(
    () =>
      buildChartGeometry([
        {
          key: "single",
          name: title || "Series",
          color,
          x,
          y,
        },
      ]),
    [title, x, y, color]
  );
  return html`
    <section className="chart-card">
      <div className="chart-head">
        <h4>${title}</h4>
        ${subtitle ? html`<span className="muted">${subtitle}</span>` : null}
      </div>
      ${geometry
        ? html`
            <svg viewBox=${`0 0 ${geometry.width} ${geometry.height}`} role="img" aria-label=${title}>
              ${geometry.yTicks.map(
                (tick) => html`
                  <line
                    x1=${geometry.padLeft}
                    y1=${tick.py}
                    x2=${geometry.width - geometry.padRight}
                    y2=${tick.py}
                    className="chart-grid-line"
                  ></line>
                `
              )}
              <line
                x1=${geometry.padLeft}
                y1=${geometry.height - geometry.padBottom}
                x2=${geometry.width - geometry.padRight}
                y2=${geometry.height - geometry.padBottom}
                className="chart-axis-line"
              ></line>
              <line
                x1=${geometry.padLeft}
                y1=${geometry.padTop}
                x2=${geometry.padLeft}
                y2=${geometry.height - geometry.padBottom}
                className="chart-axis-line"
              ></line>
              ${geometry.xTicks.map(
                (tick) => html`
                  <line
                    x1=${tick.px}
                    y1=${geometry.height - geometry.padBottom}
                    x2=${tick.px}
                    y2=${geometry.height - geometry.padBottom + 4}
                    className="chart-axis-tick"
                  ></line>
                  <text
                    x=${tick.px}
                    y=${geometry.height - geometry.padBottom + 16}
                    textAnchor="middle"
                    className="chart-axis-text"
                  >
                    ${tick.label}
                  </text>
                `
              )}
              ${geometry.yTicks.map(
                (tick) => html`
                  <line
                    x1=${geometry.padLeft - 4}
                    y1=${tick.py}
                    x2=${geometry.padLeft}
                    y2=${tick.py}
                    className="chart-axis-tick"
                  ></line>
                  <text
                    x=${geometry.padLeft - 8}
                    y=${tick.py + 3}
                    textAnchor="end"
                    className="chart-axis-text"
                  >
                    ${tick.label}
                  </text>
                `
              )}
              <polyline
                fill="none"
                stroke=${color}
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
                points=${geometry.paths[0].points}
              ></polyline>
            </svg>
          `
        : html`<div className="muted">No data</div>`}
    </section>
  `;
}

const OVERLAY_COLORS = [
  "var(--copper)",
  "var(--teal)",
  "var(--indigo)",
  "#7d4a22",
  "#2b5e80",
  "#5a8456",
  "#7a3f7f",
  "#607084",
];

function pickOverlayColor(index) {
  return OVERLAY_COLORS[index % OVERLAY_COLORS.length];
}

function MultiSeriesChartCard({ title, subtitle, series }) {
  const normalized = Array.isArray(series) ? series : [];
  const geometry = useMemo(() => buildChartGeometry(normalized), [normalized]);

  return html`
    <section className="chart-card">
      <div className="chart-head">
        <h4>${title}</h4>
        ${subtitle ? html`<span className="muted">${subtitle}</span>` : null}
      </div>
      ${geometry
        ? html`
            <svg viewBox=${`0 0 ${geometry.width} ${geometry.height}`} role="img" aria-label=${title}>
              ${geometry.yTicks.map(
                (tick) => html`
                  <line
                    x1=${geometry.padLeft}
                    y1=${tick.py}
                    x2=${geometry.width - geometry.padRight}
                    y2=${tick.py}
                    className="chart-grid-line"
                  ></line>
                `
              )}
              <line
                x1=${geometry.padLeft}
                y1=${geometry.height - geometry.padBottom}
                x2=${geometry.width - geometry.padRight}
                y2=${geometry.height - geometry.padBottom}
                className="chart-axis-line"
              ></line>
              <line
                x1=${geometry.padLeft}
                y1=${geometry.padTop}
                x2=${geometry.padLeft}
                y2=${geometry.height - geometry.padBottom}
                className="chart-axis-line"
              ></line>
              ${geometry.xTicks.map(
                (tick) => html`
                  <line
                    x1=${tick.px}
                    y1=${geometry.height - geometry.padBottom}
                    x2=${tick.px}
                    y2=${geometry.height - geometry.padBottom + 4}
                    className="chart-axis-tick"
                  ></line>
                  <text
                    x=${tick.px}
                    y=${geometry.height - geometry.padBottom + 16}
                    textAnchor="middle"
                    className="chart-axis-text"
                  >
                    ${tick.label}
                  </text>
                `
              )}
              ${geometry.yTicks.map(
                (tick) => html`
                  <line
                    x1=${geometry.padLeft - 4}
                    y1=${tick.py}
                    x2=${geometry.padLeft}
                    y2=${tick.py}
                    className="chart-axis-tick"
                  ></line>
                  <text
                    x=${geometry.padLeft - 8}
                    y=${tick.py + 3}
                    textAnchor="end"
                    className="chart-axis-text"
                  >
                    ${tick.label}
                  </text>
                `
              )}
              ${geometry.paths.map(
                (line) => html`
                  <polyline
                    key=${line.key}
                    fill="none"
                    stroke=${line.color}
                    strokeWidth="2"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    points=${line.points}
                  ></polyline>
                `
              )}
            </svg>
            <div className="legend-row">
              ${geometry.paths.map(
                (line) => html`
                  <span key=${`${line.key}-legend`} className="legend-item">
                    <span className="legend-swatch" style=${{ background: line.color }}></span>
                    ${line.name}
                  </span>
                `
              )}
            </div>
          `
        : html`<div className="muted">No data</div>`}
    </section>
  `;
}

function metricFromSignal(signal, key, reducer = "max_abs") {
  if (!signal || !Array.isArray(signal[key]) || signal[key].length === 0) return null;
  const arr = signal[key];
  if (reducer === "max") return arr.reduce((a, b) => (b > a ? b : a), arr[0]);
  if (reducer === "min") return arr.reduce((a, b) => (b < a ? b : a), arr[0]);
  return arr.reduce((a, b) => {
    const av = Math.abs(b);
    return av > a ? av : a;
  }, Math.abs(arr[0]));
}

function App() {
  const [status, setStatus] = useState("Loading wizard schema...");
  const [statusKind, setStatusKind] = useState("info");
  const [schema, setSchema] = useState(null);
  const [wizard, setWizard] = useState(null);
  const [activeStepIdx, setActiveStepIdx] = useState(0);
  const [generatedConfigPath, setGeneratedConfigPath] = useState("");
  const [generatedConfigYaml, setGeneratedConfigYaml] = useState("");
  const [configWarnings, setConfigWarnings] = useState([]);

  const [outputRoot, setOutputRoot] = useState("out/web");
  const [runs, setRuns] = useState([]);
  const [runsTree, setRunsTree] = useState({});
  const [selectedRunId, setSelectedRunId] = useState("");
  const [runSignal, setRunSignal] = useState(null);
  const [runSummary, setRunSummary] = useState(null);
  const [runHysteresis, setRunHysteresis] = useState(null);
  const [runProfileSummary, setRunProfileSummary] = useState(null);
  const [selectedLayerIndex, setSelectedLayerIndex] = useState("");
  const [activeResultTab, setActiveResultTab] = useState("Time Histories");
  const [runsPanelOpen, setRunsPanelOpen] = useState(false);
  const [resultsFrameMode, setResultsFrameMode] = useState("integrated");
  const [backendProbe, setBackendProbe] = useState(null);
  const [backendProbeLoading, setBackendProbeLoading] = useState(false);
  const [compareRunIds, setCompareRunIds] = useState([]);
  const [compareReferenceId, setCompareReferenceId] = useState("");
  const [compareSignals, setCompareSignals] = useState({});
  const [compareLoading, setCompareLoading] = useState(false);
  const [parityLatest, setParityLatest] = useState(null);
  const [releaseSignoff, setReleaseSignoff] = useState(null);
  const [scienceConfidence, setScienceConfidence] = useState([]);
  const [scienceMatrixMeta, setScienceMatrixMeta] = useState({ source_path: "", last_updated: "" });

  const [at2Path, setAt2Path] = useState("");
  const [motionPreview, setMotionPreview] = useState(null);
  const [processedMotionPath, setProcessedMotionPath] = useState("");
  const [processedMetricsPath, setProcessedMetricsPath] = useState("");
  const [sanityReport, setSanityReport] = useState(null);
  const [sanityLoading, setSanityLoading] = useState(false);
  const layerImportRef = useRef(null);
  const motionCsvUploadRef = useRef(null);
  const motionAt2UploadRef = useRef(null);
  const [profileEditorMode, setProfileEditorMode] = useState("table");
  const [profilePresetKey, setProfilePresetKey] = useState("five-main-layers");
  const [configTemplateKey, setConfigTemplateKey] = useState("effective-stress");
  const [autoProfile, setAutoProfile] = useState({
    useControlFmax: true,
    fMax: 25,
    pointsPerWavelength: 10,
    minSliceThickness: 0.4,
    maxSubLayersPerMain: 24,
  });

  function makeRunQuery(rootOverride = outputRoot) {
    const root = String(rootOverride || "").trim();
    return root ? `?output_root=${encodeURIComponent(root)}` : "";
  }

  function runRootForId(runId, fallbackRoot = outputRoot) {
    const row = runs.find((run) => run.run_id === runId);
    const fromRow = parentPath(row?.output_dir);
    return fromRow || fallbackRoot;
  }

  function updateWizard(stepKey, patch) {
    setWizard((prev) => {
      if (!prev) return prev;
      return { ...prev, [stepKey]: { ...prev[stepKey], ...patch } };
    });
  }

  function updateLayer(index, patch) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      layers[index] = { ...layers[index], ...patch };
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function setLayerMaterial(index, material) {
    const mat = String(material || "pm4sand").toLowerCase();
    updateLayer(index, {
      material: mat,
      material_params: materialParamDefaults(mat),
      material_optional_args: [],
    });
  }

  function setLayerMaterialParam(index, key, value) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      const layer = { ...(layers[index] || {}) };
      const params = { ...(layer.material_params || {}) };
      params[key] = Number.isFinite(value) ? value : 0.0;
      layer.material_params = params;
      layers[index] = layer;
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function setLayerOptionalArgs(index, rawText) {
    const values = parseOptionalArgs(rawText);
    updateLayer(index, { material_optional_args: values });
  }

  function addLayer() {
    setWizard((prev) => {
      if (!prev) return prev;
      const material = "pm4sand";
      const layer = {
        name: `Layer-${(prev.profile_step.layers || []).length + 1}`,
        thickness_m: 5.0,
        unit_weight_kN_m3: 18.0,
        vs_m_s: 200.0,
        material,
        material_params: materialParamDefaults(material),
        material_optional_args: [],
      };
      const layers = [...(prev.profile_step.layers || []), layer];
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function clonePresetLayers(presetKey) {
    const preset = PROFILE_PRESETS[presetKey] || PROFILE_PRESETS["five-main-layers"] || [];
    return preset.map((layer, idx) => {
      const material = String(layer.material || "pm4sand").toLowerCase();
      return {
        name: layer.name || `Layer-${idx + 1}`,
        thickness_m: Number(layer.thickness_m || 1.0),
        unit_weight_kN_m3: Number(layer.unit_weight_kN_m3 || 18.0),
        vs_m_s: Number(layer.vs_m_s || 150.0),
        material,
        material_params: materialParamDefaults(material),
        material_optional_args: [],
      };
    });
  }

  function applyProfilePreset() {
    const rows = clonePresetLayers(profilePresetKey);
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: rows },
      };
    });
    setStatusKind("ok");
    setStatus(`Profile preset applied: ${profilePresetKey} (${rows.length} main layers).`);
  }

  function seedFiveMainLayers() {
    setProfilePresetKey("five-main-layers");
    const rows = clonePresetLayers("five-main-layers");
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: rows },
      };
    });
    setStatusKind("ok");
    setStatus("5-layer starter profile loaded. You can edit values in Table mode then build sublayers.");
  }

  function removeLayer(idx) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      layers.splice(idx, 1);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function updateAutoProfile(patch) {
    setAutoProfile((prev) => ({ ...prev, ...patch }));
  }

  function computeAutoSliceCount(thickness, vs, cfg) {
    const H = Math.max(Number(thickness) || 0, 1.0e-4);
    const v = Math.max(Number(vs) || 0, 1.0e-3);
    const f = Math.max(Number(cfg.fMax) || 0, 0.1);
    const ppw = Math.max(Math.round(Number(cfg.pointsPerWavelength) || 0), 4);
    const minDz = Math.max(Number(cfg.minSliceThickness) || 0, 0.0);
    const maxSub = Math.max(Math.round(Number(cfg.maxSubLayersPerMain) || 0), 1);

    const dzByWave = v / (ppw * f);
    let nSub = Math.max(1, Math.ceil(H / Math.max(dzByWave, 1.0e-6)));
    nSub = Math.min(nSub, maxSub);
    if (minDz > 0.0) {
      const byMin = Math.max(1, Math.floor(H / minDz));
      nSub = Math.min(nSub, byMin);
    }
    return Math.max(1, nSub);
  }

  function buildAutoProfileLayers(mainLayers, cfg) {
    const out = [];
    mainLayers.forEach((layer, layerIdx) => {
      const nSub = computeAutoSliceCount(layer.thickness_m, layer.vs_m_s, cfg);
      const dz = Number(layer.thickness_m) / nSub;
      for (let i = 0; i < nSub; i += 1) {
        const sName =
          nSub === 1 ? layer.name : `${layer.name || `Layer-${layerIdx + 1}`}_s${i + 1}`;
        out.push({
          ...layer,
          name: sName,
          thickness_m: Number(dz.toFixed(5)),
          material_params: { ...(layer.material_params || {}) },
          material_optional_args: [...(layer.material_optional_args || [])],
        });
      }
    });
    return out;
  }

  function applyAutoProfile() {
    const mainLayers = wizard?.profile_step?.layers || [];
    if (!mainLayers.length) {
      setStatusKind("warn");
      setStatus("Auto Profile: no main layers to slice.");
      return;
    }
    const fMaxFromControl = Number(controlStep?.f_max || 25);
    const cfg = {
      ...autoProfile,
      fMax: autoProfile.useControlFmax ? fMaxFromControl : autoProfile.fMax,
    };
    const sliced = buildAutoProfileLayers(mainLayers, cfg);
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: sliced },
      };
    });
    setStatusKind("ok");
    setStatus(
      `Auto Profile generated: ${mainLayers.length} main -> ${sliced.length} sublayers (f_max=${Number(
        cfg.fMax
      ).toFixed(2)} Hz).`
    );
  }

  function duplicateLayer(idx) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      const src = layers[idx];
      if (!src) return prev;
      const copy = {
        ...src,
        name: `${src.name || `Layer-${idx + 1}`}-copy`,
        material_params: { ...(src.material_params || {}) },
        material_optional_args: [...(src.material_optional_args || [])],
      };
      layers.splice(idx + 1, 0, copy);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function moveLayer(idx, offset) {
    setWizard((prev) => {
      if (!prev) return prev;
      const layers = [...(prev.profile_step.layers || [])];
      const target = idx + offset;
      if (target < 0 || target >= layers.length) return prev;
      const [picked] = layers.splice(idx, 1);
      layers.splice(target, 0, picked);
      return { ...prev, profile_step: { ...prev.profile_step, layers } };
    });
  }

  function exportLayersCsv() {
    const allLayers = wizard?.profile_step?.layers || [];
    if (!allLayers.length) {
      setStatusKind("warn");
      setStatus("No layers to export.");
      return;
    }
    const header = [
      "name",
      "thickness_m",
      "unit_weight_kN_m3",
      "vs_m_s",
      "material",
      "material_params_json",
      "material_optional_args_csv",
    ];
    const rows = allLayers.map((layer) => [
      layer.name || "",
      Number(layer.thickness_m || 0),
      Number(layer.unit_weight_kN_m3 || 0),
      Number(layer.vs_m_s || 0),
      layer.material || "pm4sand",
      JSON.stringify(layer.material_params || {}),
      (layer.material_optional_args || []).join(" "),
    ]);
    const lines = [header, ...rows].map((row) => row.map(csvEscape).join(","));
    const csv = `${lines.join("\n")}\n`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "layers.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setStatusKind("ok");
    setStatus(`Layer CSV exported (${allLayers.length} rows).`);
  }

  function importLayersFromCsvText(text) {
    const lines = String(text || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    if (lines.length < 2) {
      throw new Error("CSV must contain a header and at least one data row.");
    }
    const header = parseCsvLine(lines[0]).map((h) => String(h || "").trim());
    const col = (name) => header.indexOf(name);
    const idxName = col("name");
    const idxThickness = col("thickness_m");
    const idxUw = col("unit_weight_kN_m3");
    const idxVs = col("vs_m_s");
    const idxMaterial = col("material");
    const idxParams = col("material_params_json");
    const idxOptional = col("material_optional_args_csv");
    if (
      idxName < 0 ||
      idxThickness < 0 ||
      idxUw < 0 ||
      idxVs < 0 ||
      idxMaterial < 0 ||
      idxParams < 0
    ) {
      throw new Error(
        "CSV header missing required columns: name, thickness_m, unit_weight_kN_m3, vs_m_s, material, material_params_json."
      );
    }

    const importedLayers = [];
    for (let i = 1; i < lines.length; i += 1) {
      const cols = parseCsvLine(lines[i]);
      const rawMaterial = String(cols[idxMaterial] || "pm4sand").trim().toLowerCase();
      const material = MATERIAL_PARAM_PRESETS[rawMaterial] ? rawMaterial : "pm4sand";
      const paramsRaw = String(cols[idxParams] || "{}").trim();
      let params = {};
      if (paramsRaw) {
        const parsed = JSON.parse(paramsRaw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          params = parsed;
        }
      }
      const typedParams = {};
      Object.entries(params).forEach(([key, value]) => {
        const numeric = Number(value);
        if (Number.isFinite(numeric)) {
          typedParams[key] = numeric;
        }
      });
      const optionalText = idxOptional >= 0 ? String(cols[idxOptional] || "") : "";
      importedLayers.push({
        name: String(cols[idxName] || `Layer-${i}`),
        thickness_m: toNum(cols[idxThickness], 1.0),
        unit_weight_kN_m3: toNum(cols[idxUw], 18.0),
        vs_m_s: toNum(cols[idxVs], 150.0),
        material,
        material_params: Object.keys(typedParams).length
          ? typedParams
          : materialParamDefaults(material),
        material_optional_args: parseOptionalArgs(optionalText),
      });
    }
    if (!importedLayers.length) {
      throw new Error("No valid layer rows found in CSV.");
    }
    setWizard((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        profile_step: { ...prev.profile_step, layers: importedLayers },
      };
    });
    setStatusKind("ok");
    setStatus(`Layer CSV imported (${importedLayers.length} rows).`);
  }

  async function onImportLayersFile(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      importLayersFromCsvText(text);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Layer CSV import failed: ${String(err)}`);
    } finally {
      if (event?.target) {
        event.target.value = "";
      }
    }
  }

  async function loadWizardSchema() {
    try {
      const payload = await requestJSON("/api/wizard/schema");
      setSchema(payload);
      setWizard(payload.defaults);
      const defaultTemplate =
        payload.default_template ||
        (Array.isArray(payload.config_templates) && payload.config_templates.length
          ? payload.config_templates[0]
          : "effective-stress");
      setConfigTemplateKey(defaultTemplate);
      setStatusKind("ok");
      setStatus("Wizard schema loaded.");
    } catch (err) {
      setStatusKind("err");
      setStatus(`Schema load failed: ${String(err)}`);
    }
  }

  async function refreshBackendProbe(executableOverride = null) {
    const executable =
      executableOverride ||
      wizard?.control_step?.opensees_executable ||
      "OpenSees";
    setBackendProbeLoading(true);
    try {
      const payload = await requestJSON(
        `/api/backend/opensees/probe?executable=${encodeURIComponent(executable)}`
      );
      setBackendProbe(payload);
    } catch (err) {
      setBackendProbe({
        requested: executable,
        available: false,
        assumed_available: false,
        version: "",
        error: String(err),
      });
    } finally {
      setBackendProbeLoading(false);
    }
  }

  async function loadRuns(rootOverride = outputRoot) {
    const query = makeRunQuery(rootOverride);
    try {
      const payload = await requestJSON(`/api/runs${query}`);
      setRuns(payload);
      if (payload.length === 0) {
        setSelectedRunId("");
        setRunSignal(null);
        setRunSummary(null);
        setRunHysteresis(null);
        setRunProfileSummary(null);
        return payload;
      }
      const selectedExists = payload.some((run) => run.run_id === selectedRunId);
      if (!selectedExists) {
        setSelectedRunId(payload[0].run_id);
      }
      return payload;
    } catch (err) {
      setStatusKind("err");
      setStatus(`Run list failed: ${String(err)}`);
      return [];
    }
  }

  async function loadRunsTree(rootOverride = outputRoot) {
    const query = makeRunQuery(rootOverride);
    try {
      const payload = await requestJSON(`/api/runs/tree${query}`);
      setRunsTree(payload.tree || {});
      return payload.tree || {};
    } catch (err) {
      setStatusKind("err");
      setStatus(`Run tree failed: ${String(err)}`);
      return {};
    }
  }

  async function loadParityLatest(rootOverride = outputRoot) {
    const query = makeRunQuery(rootOverride);
    try {
      const payload = await requestJSON(`/api/parity/latest${query}`);
      setParityLatest(payload);
      return payload;
    } catch {
      setParityLatest(null);
      return null;
    }
  }

  async function loadReleaseSignoff(rootOverride = outputRoot) {
    const query = makeRunQuery(rootOverride);
    try {
      const payload = await requestJSON(`/api/release/signoff/latest${query}`);
      setReleaseSignoff(payload);
      return payload;
    } catch {
      setReleaseSignoff(null);
      return null;
    }
  }

  async function loadScienceConfidence() {
    try {
      const payload = await requestJSON("/api/science/confidence");
      setScienceConfidence(Array.isArray(payload.rows) ? payload.rows : []);
      setScienceMatrixMeta({
        source_path: payload.source_path || "",
        last_updated: payload.last_updated || "",
      });
      return payload;
    } catch {
      setScienceConfidence([]);
      setScienceMatrixMeta({ source_path: "", last_updated: "" });
      return null;
    }
  }

  async function loadRunDetail(runId, rootOverride = outputRoot) {
    if (!runId) return;
    const fetchWithRoot = async (rootCandidate) => {
      const query = makeRunQuery(rootCandidate);
      const [signals, summary, hysteresis, profileSummary] = await Promise.all([
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/signals${query}`),
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/results/summary${query}`),
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/results/hysteresis${query}`),
        requestJSON(`/api/runs/${encodeURIComponent(runId)}/results/profile-summary${query}`),
      ]);
      return { signals, summary, hysteresis, profileSummary, rootCandidate };
    };

    try {
      const first = await fetchWithRoot(rootOverride);
      setRunSignal(first.signals);
      setRunSummary(first.summary);
      setRunHysteresis(first.hysteresis);
      setRunProfileSummary(first.profileSummary);
      const firstLayer = first.hysteresis?.layers?.[0];
      setSelectedLayerIndex(firstLayer ? String(firstLayer.layer_index) : "");
    } catch (err) {
      const fallbackRoot = runRootForId(runId, rootOverride);
      if (fallbackRoot && fallbackRoot !== rootOverride) {
        try {
          const second = await fetchWithRoot(fallbackRoot);
          setRunSignal(second.signals);
          setRunSummary(second.summary);
          setRunHysteresis(second.hysteresis);
          setRunProfileSummary(second.profileSummary);
          const firstLayer = second.hysteresis?.layers?.[0];
          setSelectedLayerIndex(firstLayer ? String(firstLayer.layer_index) : "");
          return;
        } catch {
          // keep original error below
        }
      }
      setRunSignal(null);
      setRunSummary(null);
      setRunHysteresis(null);
      setRunProfileSummary(null);
      setStatusKind("err");
      setStatus(`Run detail failed: ${String(err)}`);
    }
  }

  async function generateConfig() {
    if (!wizard) return;
    setStatusKind("info");
    setStatus("Generating config from wizard...");
    try {
      const payload = await requestJSON("/api/config/from-wizard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(wizard),
      });
      setGeneratedConfigPath(payload.config_path || "");
      setGeneratedConfigYaml(payload.config_yaml || "");
      setConfigWarnings(payload.warnings || []);
      setStatusKind("ok");
      setStatus(`Config generated: ${payload.config_path}`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Config generation failed: ${String(err)}`);
    }
  }

  async function runSanityCheck() {
    if (!wizard) return;
    setSanityLoading(true);
    setStatusKind("info");
    setStatus("Running wizard sanity checks...");
    try {
      const payload = await requestJSON("/api/wizard/sanity-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(wizard),
      });
      setSanityReport(payload);
      if (payload.ok) {
        const warnCount = Array.isArray(payload.warnings) ? payload.warnings.length : 0;
        setStatusKind(warnCount > 0 ? "warn" : "ok");
        setStatus(
          warnCount > 0
            ? `Sanity check passed with ${warnCount} warning(s).`
            : "Sanity check passed."
        );
      } else {
        const blockerCount = Array.isArray(payload.blockers) ? payload.blockers.length : 0;
        setStatusKind("err");
        setStatus(`Sanity check found ${blockerCount} blocker(s).`);
      }
    } catch (err) {
      setStatusKind("err");
      setStatus(`Sanity check failed: ${String(err)}`);
    } finally {
      setSanityLoading(false);
    }
  }

  async function runNow() {
    if (!wizard) return;
    const motionPath = wizard.motion_step?.motion_path || "";
    if (!motionPath) {
      setStatusKind("warn");
      setStatus("Motion path is required.");
      return;
    }
    setStatusKind("info");
    setStatus("Running analysis...");
    try {
      const sanity = await requestJSON("/api/wizard/sanity-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(wizard),
      });
      setSanityReport(sanity);
      if (!sanity.ok) {
        const blockers = Array.isArray(sanity.blockers) ? sanity.blockers : [];
        setStatusKind("err");
        setStatus(`Run blocked by sanity check: ${blockers.join(" | ") || "unknown blocker"}`);
        return;
      }

      let configPath = generatedConfigPath;
      if (!configPath) {
        setStatusKind("info");
        setStatus("Generating config from wizard before run...");
        const gen = await requestJSON("/api/config/from-wizard", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(wizard),
        });
        configPath = gen.config_path || "";
        setGeneratedConfigPath(configPath);
        setGeneratedConfigYaml(gen.config_yaml || "");
        setConfigWarnings(gen.warnings || []);
      }
      if (!configPath) {
        setStatusKind("err");
        setStatus("Run aborted: config path could not be generated.");
        return;
      }

      const targetOutputRoot = wizard.control_step?.output_dir || outputRoot || "out/web";
      if (targetOutputRoot !== outputRoot) {
        setOutputRoot(targetOutputRoot);
      }
      const payload = await requestJSON("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          config_path: configPath,
          motion_path: motionPath,
          output_root: targetOutputRoot,
          backend: wizard.analysis_step?.solver_backend || "config",
          opensees_executable: wizard.control_step?.opensees_executable || null,
        }),
      });
      await loadRuns(targetOutputRoot);
      await loadRunsTree(targetOutputRoot);
      setSelectedRunId(payload.run_id);
      await loadRunDetail(payload.run_id, targetOutputRoot);
      setStatusKind(payload.status === "ok" ? "ok" : "warn");
      setStatus(`Run done: ${payload.run_id} | ${payload.message}`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Run failed: ${String(err)}`);
    }
  }

  async function importAT2() {
    if (!at2Path) {
      setStatusKind("warn");
      setStatus("AT2 path is empty.");
      return;
    }
    const step = wizard?.motion_step || {};
    try {
      const payload = await requestJSON("/api/motion/import/peer-at2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: at2Path,
          units_hint: step.units || "g",
          output_dir: wizard?.control_step?.output_dir || "out/ui/motions",
        }),
      });
      updateWizard("motion_step", {
        motion_path: payload.converted_csv_path,
        units: "m/s2",
        dt_override: payload.dt_s,
      });
      setStatusKind("ok");
      setStatus(`AT2 imported: ${payload.converted_csv_path} (dt=${Number(payload.dt_s).toFixed(6)} s)`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`AT2 import failed: ${String(err)}`);
    }
  }

  async function onUploadMotionCsvFile(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    try {
      setStatusKind("info");
      setStatus(`Uploading CSV: ${file.name}`);
      const payload = await requestJSON("/api/motion/upload/csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_name: file.name,
          content_base64: await fileToBase64(file),
          output_dir: wizard?.control_step?.output_dir || "out/ui/motions",
          output_name: file.name,
        }),
      });
      updateWizard("motion_step", {
        motion_path: payload.uploaded_path,
      });
      setStatusKind("ok");
      setStatus(`CSV uploaded: ${payload.uploaded_path}`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`CSV upload failed: ${String(err)}`);
    } finally {
      if (event?.target) event.target.value = "";
    }
  }

  async function onUploadAT2File(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    try {
      setStatusKind("info");
      setStatus(`Uploading and converting AT2: ${file.name}`);
      const payload = await requestJSON("/api/motion/upload/peer-at2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_name: file.name,
          content_base64: await fileToBase64(file),
          units_hint: motionStep.units || "g",
          output_dir: wizard?.control_step?.output_dir || "out/ui/motions",
          output_name: file.name,
          dt_override:
            motionStep.dt_override && Number(motionStep.dt_override) > 0
              ? Number(motionStep.dt_override)
              : null,
        }),
      });
      updateWizard("motion_step", {
        motion_path: payload.converted_csv_path,
        units: "m/s2",
        dt_override: payload.dt_s,
      });
      setStatusKind("ok");
      setStatus(`AT2 uploaded + converted: ${payload.converted_csv_path} (dt=${Number(payload.dt_s).toFixed(6)} s)`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`AT2 upload failed: ${String(err)}`);
    } finally {
      if (event?.target) event.target.value = "";
    }
  }

  async function processMotion() {
    const step = wizard?.motion_step;
    const control = wizard?.control_step || {};
    if (!step?.motion_path) {
      setStatusKind("warn");
      setStatus("Motion path is empty.");
      return;
    }
    setStatusKind("info");
    setStatus("Processing motion...");
    try {
      const fmax = Math.max(toNum(control.f_max, 25), 0.1);
      const fallbackDt = control.dt && Number(control.dt) > 0 ? Number(control.dt) : 1.0 / (20.0 * fmax);
      const payload = await requestJSON("/api/motion/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          motion_path: step.motion_path,
          units_hint: step.units,
          dt_override:
            step.dt_override !== null && step.dt_override !== undefined && Number(step.dt_override) > 0
              ? Number(step.dt_override)
              : null,
          fallback_dt: fallbackDt,
          baseline_mode: step.baseline,
          scale_mode: step.scale_mode,
          scale_factor: step.scale_factor,
          target_pga: step.target_pga,
          output_dir: wizard?.control_step?.output_dir || "out/ui/motions",
        }),
      });
      setProcessedMotionPath(payload.processed_motion_path || "");
      setProcessedMetricsPath(payload.metrics_path || "");
      setMotionPreview(payload.spectra_preview || null);
      updateWizard("motion_step", {
        motion_path: payload.processed_motion_path,
        units: "m/s2",
      });
      setStatusKind("ok");
      setStatus(`Motion processed: ${payload.processed_motion_path} (dt=${Number(payload.metrics?.dt_s || 0).toFixed(6)} s)`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Motion process failed: ${String(err)}`);
    }
  }

  function toggleCompareRun(runId) {
    setCompareRunIds((prev) => {
      if (prev.includes(runId)) {
        return prev.filter((id) => id !== runId);
      }
      const next = [...prev, runId];
      return next.slice(-6);
    });
  }

  async function loadCompareSignals() {
    if (compareRunIds.length === 0) {
      setStatusKind("warn");
      setStatus("Select at least one run for comparison.");
      return;
    }
    setCompareLoading(true);
    setStatusKind("info");
    setStatus(`Loading compare signals for ${compareRunIds.length} run(s)...`);
    try {
      const query = makeRunQuery();
      const entries = await Promise.all(
        compareRunIds.map(async (runId) => {
          const signals = await requestJSON(`/api/runs/${encodeURIComponent(runId)}/signals${query}`);
          const runMeta = runs.find((r) => r.run_id === runId);
          return [
            runId,
            {
              ...signals,
              run_id: runId,
              label: runMeta?.motion_name || runMeta?.project_name || runId,
            },
          ];
        })
      );
      setCompareSignals(Object.fromEntries(entries));
      setStatusKind("ok");
      setStatus(`Compare signals loaded for ${compareRunIds.length} run(s).`);
    } catch (err) {
      setStatusKind("err");
      setStatus(`Compare load failed: ${String(err)}`);
    } finally {
      setCompareLoading(false);
    }
  }

  function clearCompareSignals() {
    setCompareSignals({});
    setStatusKind("ok");
    setStatus("Compare overlays cleared.");
  }

  function applyWizardTemplate() {
    const templateDefaults = schema?.template_defaults || {};
    const selected = templateDefaults[configTemplateKey];
    if (!selected) {
      setStatusKind("warn");
      setStatus(`Template not found in wizard schema: ${configTemplateKey}`);
      return;
    }
    const currentMotionPath = wizard?.motion_step?.motion_path || "";
    const currentDtOverride =
      wizard?.motion_step?.dt_override !== undefined ? wizard.motion_step.dt_override : null;
    const next = cloneJson(selected);
    if (currentMotionPath) {
      next.motion_step = next.motion_step || {};
      next.motion_step.motion_path = currentMotionPath;
    }
    if (currentDtOverride !== null && currentDtOverride !== undefined) {
      next.motion_step = next.motion_step || {};
      next.motion_step.dt_override = currentDtOverride;
    }
    setWizard(next);
    setGeneratedConfigPath("");
    setGeneratedConfigYaml("");
    setConfigWarnings([]);
    setStatusKind("ok");
    setStatus(`Wizard template applied: ${configTemplateKey}`);
  }

  useEffect(() => {
    loadWizardSchema().catch(() => {});
    loadRuns().catch(() => {});
    loadRunsTree().catch(() => {});
    loadParityLatest().catch(() => {});
    loadReleaseSignoff().catch(() => {});
    loadScienceConfidence().catch(() => {});
  }, []);

  useEffect(() => {
    if (!wizard) return;
    refreshBackendProbe(wizard?.control_step?.opensees_executable || "OpenSees").catch(() => {});
  }, [wizard?.control_step?.opensees_executable]);

  useEffect(() => {
    loadRuns().catch(() => {});
    loadRunsTree().catch(() => {});
    loadParityLatest().catch(() => {});
    loadReleaseSignoff().catch(() => {});
  }, [outputRoot]);

  useEffect(() => {
    loadRunDetail(selectedRunId).catch(() => {});
  }, [selectedRunId, outputRoot]);

  useEffect(() => {
    setCompareRunIds((prev) => {
      const validPrev = prev.filter((id) => runs.some((run) => run.run_id === id));
      if (validPrev.length > 0) return validPrev;
      if (selectedRunId && runs.some((run) => run.run_id === selectedRunId)) {
        return [selectedRunId];
      }
      return [];
    });
  }, [runs, selectedRunId]);

  useEffect(() => {
    setCompareSignals({});
  }, [outputRoot]);

  useEffect(() => {
    if (!compareRunIds.length) {
      setCompareReferenceId("");
      return;
    }
    if (compareReferenceId && compareRunIds.includes(compareReferenceId)) return;
    setCompareReferenceId(compareRunIds[0]);
  }, [compareRunIds, compareReferenceId]);

  const selectedRun = useMemo(
    () => runs.find((r) => r.run_id === selectedRunId) || null,
    [runs, selectedRunId]
  );
  const selectedRunRoot = useMemo(
    () => parentPath(selectedRun?.output_dir) || outputRoot,
    [selectedRun, outputRoot]
  );

  const metrics = useMemo(() => {
    const pga = metricFromSignal(runSignal, "surface_acc_m_s2", "max_abs") ?? selectedRun?.pga;
    const ruMax = metricFromSignal(runSignal, "ru", "max") ?? selectedRun?.ru_max;
    const duMax = metricFromSignal(runSignal, "delta_u", "max") ?? selectedRun?.delta_u_max;
    const sigmaMin =
      metricFromSignal(runSignal, "sigma_v_eff", "min") ?? selectedRun?.sigma_v_eff_min;
    return {
      pga,
      ruMax,
      duMax,
      sigmaMin,
      dt: runSignal?.dt_s ?? null,
      sigmaRef: runSignal?.sigma_v_ref ?? null,
    };
  }, [runSignal, selectedRun]);

  const convergenceView = useMemo(() => buildConvergenceView(runSummary), [runSummary]);
  const profileHealthCards = useMemo(
    () => buildProfileHealthCards(convergenceView),
    [convergenceView]
  );

  const hysteresisView = useMemo(() => {
    const layers = Array.isArray(runHysteresis?.layers) ? runHysteresis.layers : [];
    if (layers.length === 0) {
      return {
        layers: [],
        selected: null,
        ratioX: [],
        ratioY: [],
        energyX: [],
        energyY: [],
      };
    }
    const selected =
      layers.find((layer) => String(layer.layer_index) === String(selectedLayerIndex)) || layers[0];
    const ratioX = layers.map((layer) => Number(layer.layer_index));
    const ratioY = layers.map((layer) => Number(layer.mobilized_strength_ratio));
    const energyX = layers.map((layer) => Number(layer.layer_index));
    const energyY = layers.map((layer) => Number(layer.loop_energy));
    return { layers, selected, ratioX, ratioY, energyX, energyY };
  }, [runHysteresis, selectedLayerIndex]);

  const artifactLinks = useMemo(() => {
    if (!selectedRunId) {
      return {
        surface: "",
        pwp: "",
        h5: "",
        sqlite: "",
        meta: "",
      };
    }
    const id = encodeURIComponent(selectedRunId);
    const suffix = makeRunQuery(selectedRunRoot) || "";
    const withQuery = (path) => (suffix ? `${path}${suffix}` : path);
    return {
      surface: withQuery(`/api/runs/${id}/surface-acc.csv`),
      pwp: withQuery(`/api/runs/${id}/pwp-effective.csv`),
      h5: withQuery(`/api/runs/${id}/download/results.h5`),
      sqlite: withQuery(`/api/runs/${id}/download/results.sqlite`),
      meta: withQuery(`/api/runs/${id}/download/run_meta.json`),
    };
  }, [selectedRunId, selectedRunRoot]);

  const compareSeries = useMemo(() => {
    const loaded = compareRunIds
      .map((id, idx) => {
        const sig = compareSignals[id];
        if (!sig) return null;
        const label = `${id} | ${mini(sig.label || id)}`;
        return {
          key: id,
          label,
          color: pickOverlayColor(idx),
          timeX: sig.time_s || [],
          timeY: sig.surface_acc_m_s2 || [],
          psaX: sig.period_s || [],
          psaY: sig.psa_m_s2 || [],
          tfX: sig.freq_hz || [],
          tfY: sig.transfer_abs || [],
          pga: metricFromSignal(sig, "surface_acc_m_s2", "max_abs"),
        };
      })
      .filter(Boolean);
    return {
      count: loaded.length,
      time: loaded.map((s) => ({ key: `${s.key}-time`, name: s.label, color: s.color, x: s.timeX, y: s.timeY })),
      psa: loaded.map((s) => ({ key: `${s.key}-psa`, name: s.label, color: s.color, x: s.psaX, y: s.psaY })),
      transfer: loaded.map((s) => ({ key: `${s.key}-tf`, name: s.label, color: s.color, x: s.tfX, y: s.tfY })),
      metrics: loaded.map((s) => ({ runId: s.key, label: s.label, pga: s.pga })),
    };
  }, [compareRunIds, compareSignals]);

  const compareReferenceDerived = useMemo(() => {
    if (!compareReferenceId) {
      return {
        referenceId: "",
        ratioPsa: [],
        deltaTransfer: [],
        deltaTime: [],
        metrics: [],
      };
    }
    const ref = compareSignals[compareReferenceId];
    if (!ref) {
      return {
        referenceId: "",
        ratioPsa: [],
        deltaTransfer: [],
        deltaTime: [],
        metrics: [],
      };
    }
    const refPga = metricFromSignal(ref, "surface_acc_m_s2", "max_abs");
    const ratioPsa = [];
    const deltaTransfer = [];
    const deltaTime = [];
    const metrics = [];
    compareRunIds.forEach((runId, idx) => {
      if (runId === compareReferenceId) return;
      const sig = compareSignals[runId];
      if (!sig) return;
      const label = `${runId} | ${mini(sig.label || runId)}`;
      const color = pickOverlayColor(idx);
      const psaRatio = alignedRatioSeries(
        ref.period_s || [],
        ref.psa_m_s2 || [],
        sig.period_s || [],
        sig.psa_m_s2 || []
      );
      const tfDelta = alignedDeltaSeries(
        ref.freq_hz || [],
        ref.transfer_abs || [],
        sig.freq_hz || [],
        sig.transfer_abs || []
      );
      const timeDelta = alignedDeltaSeries(
        ref.time_s || [],
        ref.surface_acc_m_s2 || [],
        sig.time_s || [],
        sig.surface_acc_m_s2 || []
      );
      ratioPsa.push({
        key: `${runId}-ratio-psa`,
        name: label,
        color,
        x: psaRatio.x,
        y: psaRatio.y,
      });
      deltaTransfer.push({
        key: `${runId}-delta-tf`,
        name: label,
        color,
        x: tfDelta.x,
        y: tfDelta.y,
      });
      deltaTime.push({
        key: `${runId}-delta-time`,
        name: label,
        color,
        x: timeDelta.x,
        y: timeDelta.y,
      });
      const pga = metricFromSignal(sig, "surface_acc_m_s2", "max_abs");
      const deltaPga = Number.isFinite(pga) && Number.isFinite(refPga) ? pga - refPga : null;
      const ratioPga =
        Number.isFinite(pga) && Number.isFinite(refPga) && Math.abs(refPga) > 1e-12
          ? pga / refPga
          : null;
      metrics.push({
        runId,
        label,
        pga,
        deltaPga,
        ratioPga,
      });
    });
    return {
      referenceId: compareReferenceId,
      ratioPsa,
      deltaTransfer,
      deltaTime,
      metrics,
    };
  }, [compareReferenceId, compareRunIds, compareSignals]);

  const enums = schema?.enum_options || {};
  const configTemplates = Array.isArray(schema?.config_templates)
    ? schema.config_templates
    : ["effective-stress"];
  const layers = wizard?.profile_step?.layers || [];
  const motionStep = wizard?.motion_step || {};
  const dampingStep = wizard?.damping_step || {};
  const controlStep = wizard?.control_step || {};
  const analysisStep = wizard?.analysis_step || {};
  const wizardValidation = useMemo(() => buildWizardValidation(wizard), [wizard]);
  const activeStepId = WIZARD_STEPS[activeStepIdx]?.id || "analysis_step";
  const activeStepIssues = wizardValidation?.[activeStepId]?.issues || [];
  const canGenerateConfig =
    wizardValidation.analysis_step.valid &&
    wizardValidation.profile_step.valid &&
    wizardValidation.control_step.valid;
  const isOpenSeesMode = (analysisStep?.solver_backend || "config") === "opensees";
  const backendBlockingIssue =
    isOpenSeesMode && backendProbe && backendProbe.available === false
      ? `OpenSees executable not available (${backendProbe.requested || "OpenSees"}). Use backend=auto/mock or set valid executable path.`
      : "";
  const backendProbeAssumedIssue =
    isOpenSeesMode &&
    backendProbe &&
    backendProbe.available === true &&
    backendProbe.assumed_available === true
      ? "OpenSees probe timed out; availability is assumed and final validation will occur at runtime."
      : "";
  const runBlockingIssues = [];
  if (!canGenerateConfig) runBlockingIssues.push("Fix wizard validation issues first.");
  if (!wizardValidation.motion_step.valid) runBlockingIssues.push("Motion step is incomplete.");
  if (backendBlockingIssue) runBlockingIssues.push(backendBlockingIssue);
  const canRunNow = runBlockingIssues.length === 0;
  const isResultsFrameMode = resultsFrameMode === "results_only";
  const layoutModeClass = isResultsFrameMode
    ? "layout-results-focus"
    : runsPanelOpen
      ? "layout-workspace-open"
      : "layout-workspace-collapsed";
  const configTemplateDescription =
    TEMPLATE_DESCRIPTIONS[configTemplateKey] ||
    "Template description is not available for this preset.";

  const autoProfilePreview = useMemo(() => {
    const controlFmax = Math.max(Number(controlStep?.f_max || 25), 0.1);
    const cfg = {
      ...autoProfile,
      fMax: autoProfile.useControlFmax ? controlFmax : Math.max(Number(autoProfile.fMax || 25), 0.1),
    };
    let predicted = 0;
    for (const layer of layers) {
      predicted += computeAutoSliceCount(layer.thickness_m, layer.vs_m_s, cfg);
    }
    return {
      mainCount: layers.length,
      predictedCount: predicted,
      fMaxUsed: cfg.fMax,
    };
  }, [autoProfile, controlStep?.f_max, layers]);

  const paritySuites = useMemo(
    () => (Array.isArray(parityLatest?.suites) ? parityLatest.suites : []),
    [parityLatest]
  );
  const parityPrimary = useMemo(() => {
    if (!paritySuites.length) return null;
    return (
      paritySuites.find((row) => String(row.suite || "").toLowerCase() === "opensees-parity") ||
      paritySuites[0]
    );
  }, [paritySuites]);
  const parityBlockText = useMemo(() => {
    if (!parityPrimary || !Array.isArray(parityPrimary.block_reasons)) return "";
    const nonEmpty = parityPrimary.block_reasons.filter((v) => String(v || "").trim().length > 0);
    return nonEmpty.join(" | ");
  }, [parityPrimary]);
  const releaseHealth = useMemo(
    () =>
      buildReleaseHealth({
        parityLatest,
        parityPrimary,
        releaseSignoff,
        scienceConfidence,
        runSummary,
        selectedRun,
      }),
    [parityLatest, parityPrimary, releaseSignoff, scienceConfidence, runSummary, selectedRun]
  );

  if (!schema || !wizard) {
    return html`<div className="shell"><div className="panel">Loading...</div></div>`;
  }

  return html`
    <div className="shell">
      <header className="hero">
        <h1>StrataWave Wave-1 Studio</h1>
        <p>
          DEEPSOIL-style 5-step workflow: model build, motion processing, run orchestration and
          results review without manual YAML editing.
        </p>
      </header>

      <section
        className=${`layout ${layoutModeClass}`}
      >
        <aside className=${`panel side-panel ${isResultsFrameMode ? "side-panel-hidden" : ""}`}>
          <h2>Wizard</h2>
          <div className="tab-row">
            ${WIZARD_STEPS.map(
              (step, idx) => {
                const stepState = wizardValidation?.[step.id] || { valid: true, issues: [] };
                const badge = stepState.valid ? "✓" : "!";
                return html`
                <button
                  className=${`tab-btn ${idx === activeStepIdx ? "active" : ""} ${
                    stepState.valid ? "step-valid" : "step-invalid"
                  }`}
                  onClick=${() => setActiveStepIdx(idx)}
                  title=${stepState.valid
                    ? `${step.title}: ready`
                    : `${step.title}: ${stepState.issues.length} issue(s)`}
                >
                  ${step.title}
                  <span className=${`step-badge ${stepState.valid ? "ok" : "bad"}`}>${badge}</span>
                </button>
              `;
              }
            )}
          </div>

          ${activeStepIdx === 0 &&
          html`
            <div className="step-body">
              <div className="row">
                <div className="field">
                  <label>Wizard Template</label>
                  <select
                    value=${configTemplateKey}
                    onInput=${(e) => setConfigTemplateKey(e.target.value)}
                  >
                    ${configTemplates.map((v) => html`<option value=${v}>${v}</option>`)}
                  </select>
                </div>
                <div className="field align-end">
                  <button className="btn-min" onClick=${applyWizardTemplate}>Apply Template</button>
                </div>
              </div>
              <div className="hint-box">
                <strong>${configTemplateKey}</strong><br />
                ${configTemplateDescription}
              </div>

              <div className="field">
                <label>Project Name</label>
                <input
                  value=${analysisStep.project_name || ""}
                  onInput=${(e) => updateWizard("analysis_step", { project_name: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Boundary Condition</label>
                <select
                  value=${analysisStep.boundary_condition || "elastic_halfspace"}
                  onInput=${(e) =>
                    updateWizard("analysis_step", { boundary_condition: e.target.value })}
                >
                  ${(enums.boundary_condition || []).map(
                    (v) => html`<option value=${v}>${v}</option>`
                  )}
                </select>
              </div>
              <div className="field">
                <label>Solver Backend</label>
                <select
                  value=${analysisStep.solver_backend || "opensees"}
                  onInput=${(e) => updateWizard("analysis_step", { solver_backend: e.target.value })}
                >
                  ${(enums.solver_backend || []).map((v) => html`<option value=${v}>${v}</option>`)}
                </select>
              </div>
              <div className="field">
                <label>PM4 Validation Profile</label>
                <select
                  value=${analysisStep.pm4_validation_profile || "basic"}
                  onInput=${(e) =>
                    updateWizard("analysis_step", { pm4_validation_profile: e.target.value })}
                >
                  ${(enums.pm4_validation_profile || []).map(
                    (v) => html`<option value=${v}>${v}</option>`
                  )}
                </select>
              </div>
              <div className="backend-probe-box">
                <div className="row between">
                  <strong>Backend Readiness</strong>
                  <button
                    className="btn-min"
                    onClick=${() => refreshBackendProbe().catch(() => {})}
                    disabled=${backendProbeLoading}
                  >
                    ${backendProbeLoading ? "Checking..." : "Check"}
                  </button>
                </div>
                <div className="muted">
                  Solver backend: ${analysisStep.solver_backend || "config"}<br />
                  OpenSees exe: ${controlStep.opensees_executable || "OpenSees"}
                </div>
                ${backendProbe
                  ? html`
                      <div
                        className=${`probe-chip ${
                          backendProbe.available
                            ? backendProbe.assumed_available
                              ? "warn"
                              : "ok"
                            : "bad"
                        }`}
                      >
                        ${backendProbe.available
                          ? backendProbe.assumed_available
                            ? "OpenSees assumed available"
                            : "OpenSees available"
                          : "OpenSees not available"}
                      </div>
                      <div className="muted">
                        ${backendProbe.resolved ? `Resolved: ${backendProbe.resolved}` : ""}
                        ${backendProbe.version ? html`<br />Version: ${backendProbe.version}` : null}
                        ${backendProbe.error ? html`<br />Error: ${backendProbe.error}` : null}
                      </div>
                    `
                  : html`<div className="muted">No backend probe yet.</div>`}
                ${backendBlockingIssue
                  ? html`<div className="warn-box"><strong>Run Blocker:</strong> ${backendBlockingIssue}</div>`
                  : null}
                ${backendProbeAssumedIssue
                  ? html`<div className="warn-box"><strong>Backend Warning:</strong> ${backendProbeAssumedIssue}</div>`
                  : null}
              </div>
            </div>
          `}

          ${activeStepIdx === 1 &&
          html`
            <div className="step-body">
              <div className="row between">
                <strong>Layers (${layers.length})</strong>
                <div className="layer-actions">
                  <button className="btn-sub" onClick=${addLayer}>+ Add Layer</button>
                  <button className="btn-min" onClick=${seedFiveMainLayers}>5-Layer Starter</button>
                  <button
                    className="btn-min"
                    onClick=${() => {
                      if (layerImportRef.current) layerImportRef.current.click();
                    }}
                  >
                    Import CSV
                  </button>
                  <button className="btn-min" onClick=${exportLayersCsv}>Export CSV</button>
                </div>
              </div>
              <input
                ref=${layerImportRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden-input"
                onChange=${onImportLayersFile}
              />

              <div className="row">
                <div className="field">
                  <label>Profile Preset</label>
                  <select
                    value=${profilePresetKey}
                    onInput=${(e) => setProfilePresetKey(e.target.value)}
                  >
                    <option value="five-main-layers">five-main-layers</option>
                    <option value="soft-over-stiff">soft-over-stiff</option>
                  </select>
                </div>
                <div className="field align-end">
                  <button className="btn-min" onClick=${applyProfilePreset}>Load Preset</button>
                </div>
              </div>

              <div className="profile-mode-row">
                <div className="mode-switch">
                  <button
                    className=${`btn-min ${profileEditorMode === "table" ? "active-mode" : ""}`}
                    onClick=${() => setProfileEditorMode("table")}
                  >
                    Table
                  </button>
                  <button
                    className=${`btn-min ${profileEditorMode === "cards" ? "active-mode" : ""}`}
                    onClick=${() => setProfileEditorMode("cards")}
                  >
                    Cards
                  </button>
                </div>
              </div>

              <div className="auto-profile-box">
                <div className="row between">
                  <strong>Automatic Profile Builder</strong>
                  <span className="muted">
                    ${autoProfilePreview.mainCount} main -> ${autoProfilePreview.predictedCount}
                    sublayers
                  </span>
                </div>

                <div className="field-inline">
                  <label>
                    <input
                      type="checkbox"
                      checked=${autoProfile.useControlFmax}
                      onChange=${(e) => updateAutoProfile({ useControlFmax: e.target.checked })}
                    />
                    Use Analysis Control f_max (${Number(controlStep.f_max || 25).toFixed(2)} Hz)
                  </label>
                </div>

                <div className="auto-profile-grid">
                  <div className="field">
                    <label>f_max (Hz)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      disabled=${autoProfile.useControlFmax}
                      value=${autoProfile.fMax}
                      onInput=${(e) => updateAutoProfile({ fMax: Math.max(toNum(e.target.value, 25), 0.1) })}
                    />
                  </div>
                  <div className="field">
                    <label>Points / Wavelength</label>
                    <input
                      type="number"
                      step="1"
                      min="4"
                      value=${autoProfile.pointsPerWavelength}
                      onInput=${(e) =>
                        updateAutoProfile({
                          pointsPerWavelength: Math.max(Math.round(toNum(e.target.value, 10)), 4),
                        })}
                    />
                  </div>
                  <div className="field">
                    <label>Min Slice Thickness (m)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      value=${autoProfile.minSliceThickness}
                      onInput=${(e) =>
                        updateAutoProfile({
                          minSliceThickness: Math.max(toNum(e.target.value, 0.4), 0),
                        })}
                    />
                  </div>
                  <div className="field">
                    <label>Max Sublayers / Main Layer</label>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      value=${autoProfile.maxSubLayersPerMain}
                      onInput=${(e) =>
                        updateAutoProfile({
                          maxSubLayersPerMain: Math.max(Math.round(toNum(e.target.value, 24)), 1),
                        })}
                    />
                  </div>
                  <div className="field align-end">
                    <button className="btn-sub" onClick=${applyAutoProfile}>
                      Build Sub-Layers
                    </button>
                  </div>
                </div>
                <div className="muted">Effective f_max: ${autoProfilePreview.fMaxUsed.toFixed(2)} Hz</div>
              </div>

              ${layers.length === 0
                ? html`<div className="muted">No layer defined yet. Add at least one layer.</div>`
                : null}

              ${layers.length > 0 && profileEditorMode === "table"
                ? html`
                    <div className="layer-table-wrap">
                      <table className="layer-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Name</th>
                            <th>Thickness (m)</th>
                            <th>Unit W. (kN/m^3)</th>
                            <th>Vs (m/s)</th>
                            <th>Material</th>
                            <th>Material Params</th>
                            <th>Optional Args</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          ${layers.map((layer, idx) => {
                            const rows = materialParamRows(layer.material, layer.material_params);
                            return html`
                              <tr key=${`layer-row-${idx}`}>
                                <td>${idx + 1}</td>
                                <td>
                                  <input
                                    value=${layer.name || ""}
                                    onInput=${(e) => updateLayer(idx, { name: e.target.value })}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    min="0.001"
                                    value=${layer.thickness_m ?? ""}
                                    onInput=${(e) =>
                                      updateLayer(idx, {
                                        thickness_m: Math.max(toNum(e.target.value, 1.0), 0.001),
                                      })}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="0.01"
                                    min="0.001"
                                    value=${layer.unit_weight_kN_m3 ?? ""}
                                    onInput=${(e) =>
                                      updateLayer(idx, {
                                        unit_weight_kN_m3: Math.max(toNum(e.target.value, 18.0), 0.001),
                                      })}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    step="1"
                                    min="1"
                                    value=${layer.vs_m_s ?? ""}
                                    onInput=${(e) =>
                                      updateLayer(idx, { vs_m_s: Math.max(toNum(e.target.value, 150.0), 1.0) })}
                                  />
                                </td>
                                <td>
                                  <select
                                    value=${layer.material || "pm4sand"}
                                    onInput=${(e) => setLayerMaterial(idx, e.target.value)}
                                  >
                                    ${(enums.material || []).map((v) => html`<option value=${v}>${v}</option>`)}
                                  </select>
                                </td>
                                <td>
                                  <div className="param-inline-grid">
                                    ${rows.map(
                                      (row) => html`
                                        <div className="param-mini">
                                          <span>${row.key}</span>
                                          <input
                                            type="number"
                                            step="0.0001"
                                            value=${row.value}
                                            onInput=${(e) =>
                                              setLayerMaterialParam(idx, row.key, toNum(e.target.value, row.value))}
                                          />
                                        </div>
                                      `
                                    )}
                                  </div>
                                </td>
                                <td>
                                  <input
                                    placeholder="space-separated values"
                                    value=${(layer.material_optional_args || []).join(" ")}
                                    onInput=${(e) => setLayerOptionalArgs(idx, e.target.value)}
                                  />
                                </td>
                                <td>
                                  <div className="layer-actions compact">
                                    <button className="btn-min" onClick=${() => moveLayer(idx, -1)}>Up</button>
                                    <button className="btn-min" onClick=${() => moveLayer(idx, 1)}>Down</button>
                                    <button className="btn-min" onClick=${() => duplicateLayer(idx)}>Dup</button>
                                    <button className="btn-min" onClick=${() => removeLayer(idx)}>Del</button>
                                  </div>
                                </td>
                              </tr>
                            `;
                          })}
                        </tbody>
                      </table>
                    </div>
                  `
                : null}

              ${layers.length > 0 && profileEditorMode === "cards"
                ? html`
                    <div className="layer-list">
                      ${layers.map((layer, idx) => {
                        const rows = materialParamRows(layer.material, layer.material_params);
                        return html`
                          <details className="layer-card" open>
                            <summary>
                              <span className="layer-title">${layer.name || `Layer-${idx + 1}`}</span>
                            </summary>
                            <div className="row">
                              <div className="field">
                                <label>Name</label>
                                <input
                                  value=${layer.name || ""}
                                  onInput=${(e) => updateLayer(idx, { name: e.target.value })}
                                />
                              </div>
                              <div className="field">
                                <label>Material</label>
                                <select
                                  value=${layer.material || "pm4sand"}
                                  onInput=${(e) => setLayerMaterial(idx, e.target.value)}
                                >
                                  ${(enums.material || []).map((v) => html`<option value=${v}>${v}</option>`)}
                                </select>
                              </div>
                            </div>

                            <div className="row">
                              <div className="field">
                                <label>Thickness (m)</label>
                                <input
                                  type="number"
                                  step="0.01"
                                  value=${layer.thickness_m ?? ""}
                                  onInput=${(e) =>
                                    updateLayer(idx, {
                                      thickness_m: Math.max(toNum(e.target.value, 1.0), 0.001),
                                    })}
                                />
                              </div>
                              <div className="field">
                                <label>Unit Weight (kN/m^3)</label>
                                <input
                                  type="number"
                                  step="0.01"
                                  value=${layer.unit_weight_kN_m3 ?? ""}
                                  onInput=${(e) =>
                                    updateLayer(idx, {
                                      unit_weight_kN_m3: Math.max(toNum(e.target.value, 18.0), 0.001),
                                    })}
                                />
                              </div>
                              <div className="field">
                                <label>Vs (m/s)</label>
                                <input
                                  type="number"
                                  step="1"
                                  value=${layer.vs_m_s ?? ""}
                                  onInput=${(e) =>
                                    updateLayer(idx, { vs_m_s: Math.max(toNum(e.target.value, 150.0), 1.0) })}
                                />
                              </div>
                            </div>

                            <div className="param-grid">
                              ${rows.map(
                                (row) => html`
                                  <div className="field param-field">
                                    <label>${row.key}</label>
                                    <input
                                      type="number"
                                      step="0.0001"
                                      value=${row.value}
                                      onInput=${(e) =>
                                        setLayerMaterialParam(idx, row.key, toNum(e.target.value, row.value))}
                                    />
                                  </div>
                                `
                              )}
                            </div>

                            <div className="field">
                              <label>Optional Args</label>
                              <input
                                placeholder="space-separated values"
                                value=${(layer.material_optional_args || []).join(" ")}
                                onInput=${(e) => setLayerOptionalArgs(idx, e.target.value)}
                              />
                            </div>

                            <div className="layer-actions compact">
                              <button className="btn-min" onClick=${() => moveLayer(idx, -1)}>Up</button>
                              <button className="btn-min" onClick=${() => moveLayer(idx, 1)}>Down</button>
                              <button className="btn-min" onClick=${() => duplicateLayer(idx)}>Duplicate</button>
                              <button className="btn-min" onClick=${() => removeLayer(idx)}>Delete</button>
                            </div>
                          </details>
                        `;
                      })}
                    </div>
                  `
                : null}
            </div>
          `}

          ${activeStepIdx === 2 &&
          html`
            <div className="step-body">
              <input
                ref=${motionCsvUploadRef}
                type="file"
                accept=".csv,text/csv,.txt,text/plain"
                className="hidden-input"
                onChange=${onUploadMotionCsvFile}
              />
              <input
                ref=${motionAt2UploadRef}
                type="file"
                accept=".at2,.accmt,.txt,text/plain"
                className="hidden-input"
                onChange=${onUploadAT2File}
              />
              <div className="row">
                <button
                  className="btn-min"
                  onClick=${() => {
                    if (motionCsvUploadRef.current) motionCsvUploadRef.current.click();
                  }}
                >
                  Upload CSV
                </button>
                <button
                  className="btn-min"
                  onClick=${() => {
                    if (motionAt2UploadRef.current) motionAt2UploadRef.current.click();
                  }}
                >
                  Upload AT2
                </button>
              </div>
              <div className="field">
                <label>Motion Path (CSV)</label>
                <input
                  value=${motionStep.motion_path || ""}
                  onInput=${(e) => updateWizard("motion_step", { motion_path: e.target.value })}
                  placeholder="examples/motions/sample_motion.csv"
                />
              </div>
              <div className="field">
                <label>PEER AT2 Path</label>
                <div className="row">
                  <input
                    value=${at2Path}
                    onInput=${(e) => setAt2Path(e.target.value)}
                    placeholder=".../record.at2"
                  />
                  <button className="btn-sub" onClick=${importAT2}>Import AT2</button>
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Units</label>
                  <input
                    value=${motionStep.units || "m/s2"}
                    onInput=${(e) => updateWizard("motion_step", { units: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Baseline</label>
                  <select
                    value=${motionStep.baseline || "remove_mean"}
                    onInput=${(e) => updateWizard("motion_step", { baseline: e.target.value })}
                  >
                    ${(enums.baseline || []).map((v) => html`<option value=${v}>${v}</option>`)}
                  </select>
                </div>
                <div className="field">
                  <label>dt Override (s)</label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    value=${motionStep.dt_override ?? ""}
                    placeholder="auto from time axis / control"
                    onInput=${(e) =>
                      updateWizard("motion_step", {
                        dt_override: (() => {
                          if (e.target.value === "") return null;
                          const val = Number(e.target.value);
                          if (!Number.isFinite(val) || val <= 0) return null;
                          return val;
                        })(),
                      })}
                  />
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Scale Mode</label>
                  <select
                    value=${motionStep.scale_mode || "none"}
                    onInput=${(e) => updateWizard("motion_step", { scale_mode: e.target.value })}
                  >
                    ${(enums.scale_mode || []).map((v) => html`<option value=${v}>${v}</option>`)}
                  </select>
                </div>
                <div className="field">
                  <label>Scale Factor</label>
                  <input
                    type="number"
                    step="0.01"
                    value=${motionStep.scale_factor ?? ""}
                    onInput=${(e) =>
                      updateWizard("motion_step", { scale_factor: toNum(e.target.value, 1.0) })}
                  />
                </div>
                <div className="field">
                  <label>Target PGA</label>
                  <input
                    type="number"
                    step="0.01"
                    value=${motionStep.target_pga ?? ""}
                    onInput=${(e) =>
                      updateWizard("motion_step", { target_pga: toNum(e.target.value, 0.3) })}
                  />
                </div>
              </div>
              <div className="row">
                <button className="btn-main" onClick=${processMotion}>Process Motion</button>
              </div>
              ${processedMotionPath
                ? html`
                    <div className="muted">
                      Processed CSV: ${processedMotionPath}<br />
                      Metrics JSON: ${processedMetricsPath}
                    </div>
                  `
                : null}
              ${motionPreview
                ? html`
                    <div className="charts-grid compact">
                      <${ChartCard}
                        title="Processed Acc"
                        x=${motionPreview.time_s || []}
                        y=${motionPreview.acc_m_s2 || []}
                        color="var(--copper)"
                      />
                      <${ChartCard}
                        title="PSA (preview)"
                        x=${motionPreview.period_s || []}
                        y=${motionPreview.psa_m_s2 || []}
                        color="var(--teal)"
                      />
                      <${ChartCard}
                        title="FAS Ratio"
                        x=${motionPreview.freq_hz || []}
                        y=${motionPreview.fas_ratio || []}
                        color="var(--indigo)"
                      />
                    </div>
                  `
                : null}
            </div>
          `}

          ${activeStepIdx === 3 &&
          html`
            <div className="step-body">
              <div className="field">
                <label>Damping Mode</label>
                <select
                  value=${dampingStep.mode || "frequency_independent"}
                  onInput=${(e) => updateWizard("damping_step", { mode: e.target.value })}
                >
                  <option value="frequency_independent">frequency_independent</option>
                  <option value="rayleigh">rayleigh</option>
                </select>
              </div>
              <div className="row">
                <div className="field">
                  <label>Mode-1 Hz</label>
                  <input
                    type="number"
                    step="0.1"
                    value=${dampingStep.mode_1 ?? ""}
                    onInput=${(e) => updateWizard("damping_step", { mode_1: toNum(e.target.value, 1) })}
                  />
                </div>
                <div className="field">
                  <label>Mode-2 Hz</label>
                  <input
                    type="number"
                    step="0.1"
                    value=${dampingStep.mode_2 ?? ""}
                    onInput=${(e) => updateWizard("damping_step", { mode_2: toNum(e.target.value, 5) })}
                  />
                </div>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(dampingStep.update_matrix)}
                  onChange=${(e) =>
                    updateWizard("damping_step", { update_matrix: e.target.checked })}
                />
                <label>Update damping matrix during run</label>
              </div>
            </div>
          `}

          ${activeStepIdx === 4 &&
          html`
            <div className="step-body">
              <div className="row">
                <div className="field">
                  <label>dt (s)</label>
                  <input
                    type="number"
                    step="0.0005"
                    value=${controlStep.dt ?? ""}
                    onInput=${(e) => updateWizard("control_step", { dt: toNum(e.target.value, 0.005) })}
                  />
                </div>
                <div className="field">
                  <label>f_max (Hz)</label>
                  <input
                    type="number"
                    step="1"
                    value=${controlStep.f_max ?? 25}
                    onInput=${(e) => updateWizard("control_step", { f_max: toNum(e.target.value, 25) })}
                  />
                </div>
              </div>
              <div className="row">
                <div className="field">
                  <label>Timeout (s)</label>
                  <input
                    type="number"
                    step="1"
                    value=${controlStep.timeout_s ?? 180}
                    onInput=${(e) =>
                      updateWizard("control_step", { timeout_s: Math.round(toNum(e.target.value, 180)) })}
                  />
                </div>
                <div className="field">
                  <label>Retries</label>
                  <input
                    type="number"
                    step="1"
                    value=${controlStep.retries ?? 1}
                    onInput=${(e) =>
                      updateWizard("control_step", { retries: Math.round(toNum(e.target.value, 1)) })}
                  />
                </div>
              </div>
              <div className="field">
                <label>OpenSees Executable</label>
                <input
                  value=${controlStep.opensees_executable || "OpenSees"}
                  onInput=${(e) =>
                    updateWizard("control_step", { opensees_executable: e.target.value })}
                />
              </div>
              ${backendProbe
                ? html`
                    <div
                      className=${`probe-chip ${
                        backendProbe.available
                          ? backendProbe.assumed_available
                            ? "warn"
                            : "ok"
                          : "bad"
                      }`}
                    >
                      ${backendProbe.available
                        ? backendProbe.assumed_available
                          ? `OpenSees assumed: ${backendProbe.requested}`
                          : `OpenSees ok: ${backendProbe.requested}`
                        : `OpenSees missing: ${backendProbe.requested}`}
                    </div>
                  `
                : null}
              <div className="field">
                <label>Output Dir</label>
                <input
                  value=${controlStep.output_dir || "out/ui"}
                  onInput=${(e) => updateWizard("control_step", { output_dir: e.target.value })}
                />
              </div>
              <div className="row">
                <div className="field">
                  <label>Config Output Dir</label>
                  <input
                    value=${controlStep.config_output_dir || ""}
                    onInput=${(e) =>
                      updateWizard("control_step", { config_output_dir: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label>Config File Name</label>
                  <input
                    value=${controlStep.config_file_name || "wizard_generated.yml"}
                    onInput=${(e) =>
                      updateWizard("control_step", { config_file_name: e.target.value })}
                  />
                </div>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(controlStep.write_hdf5)}
                  onChange=${(e) => updateWizard("control_step", { write_hdf5: e.target.checked })}
                />
                <label>Write HDF5</label>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(controlStep.write_sqlite)}
                  onChange=${(e) => updateWizard("control_step", { write_sqlite: e.target.checked })}
                />
                <label>Write SQLite</label>
              </div>
              <div className="checkline">
                <input
                  type="checkbox"
                  checked=${Boolean(controlStep.parquet_export)}
                  onChange=${(e) =>
                    updateWizard("control_step", { parquet_export: e.target.checked })}
                />
                <label>Parquet export</label>
              </div>

              <div className="row">
                <button
                  className="btn-main"
                  onClick=${generateConfig}
                  disabled=${!canGenerateConfig}
                  title=${canGenerateConfig
                    ? "Generate config from wizard values"
                    : "Fix wizard issues in Analysis/Profile/Control steps first"}
                >
                  Generate Config
                </button>
                <button
                  className="btn-sub"
                  onClick=${runNow}
                  disabled=${!canRunNow}
                  title=${canRunNow
                    ? "Run analysis with generated config and motion"
                    : runBlockingIssues.join(" | ")}
                  >
                  Run Now
                </button>
                <button
                  className="btn-min"
                  onClick=${runSanityCheck}
                  disabled=${sanityLoading}
                  title="Check motion path, backend readiness, dt/f_max, and config validity."
                >
                  ${sanityLoading ? "Checking..." : "Run Sanity Check"}
                </button>
              </div>

              ${sanityReport
                ? html`
                    <div className=${`status status-${sanityReport.ok ? "ok" : "err"}`}>
                      <strong>Sanity Summary:</strong> ${sanityReport.ok ? "Ready" : "Blocked"}
                      <br />
                      blockers: ${(sanityReport.blockers || []).length} | warnings:
                      ${(sanityReport.warnings || []).length}
                    </div>
                    <details className="json-details">
                      <summary>Sanity checks</summary>
                      <div className="metric-grid">
                        ${(sanityReport.checks || []).map(
                          (item) => html`
                            <div className="metric-card" key=${`sanity-${item.name}`}>
                              <span>${item.name}</span>
                              <b>${String(item.status || "unknown").toUpperCase()}</b>
                              <div className="muted">${item.message}</div>
                            </div>
                          `
                        )}
                      </div>
                    </details>
                  `
                : null}
            </div>
          `}

          ${activeStepIssues.length
            ? html`
                <div className="warn-box">
                  <strong>Step Issues:</strong> ${activeStepIssues.join(" | ")}
                </div>
              `
            : null}
          ${activeStepIdx === 4 && runBlockingIssues.length
            ? html`
                <div className="warn-box">
                  <strong>Run Blockers:</strong> ${runBlockingIssues.join(" | ")}
                </div>
              `
            : null}

          ${generatedConfigPath
            ? html`
                <div className="generated-box">
                  <div><strong>Config:</strong> ${generatedConfigPath}</div>
                  ${configWarnings.length
                    ? html`<div className="warn-box">${configWarnings.join(" | ")}</div>`
                    : null}
                  <details>
                    <summary>Show YAML</summary>
                    <pre>${generatedConfigYaml}</pre>
                  </details>
                </div>
              `
            : null}

          <div className=${`status status-${statusKind}`}>${status}</div>
        </aside>

        <main
          className=${`panel workspace-panel ${
            runsPanelOpen ? "workspace-open" : "workspace-collapsed"
          } ${isResultsFrameMode ? "workspace-results-focus" : ""}`}
        >
          ${!isResultsFrameMode
            ? html`
                <section className="panel-block">
            <div className="row between">
              <h2 className="runs-heading">Runs</h2>
              <div className="accordion-actions">
                <button
                  className="btn-sub runs-refresh-btn"
                  onClick=${() => {
                    loadRuns().catch(() => {});
                    loadRunsTree().catch(() => {});
                  }}
                >
                  Refresh
                </button>
                <button
                  className="btn-min panel-toggle"
                  title=${runsPanelOpen ? "Runs panelini kapat" : "Runs panelini ac"}
                  aria-expanded=${runsPanelOpen}
                  onClick=${() => setRunsPanelOpen((prev) => !prev)}
                >
                  <span className=${`panel-caret ${runsPanelOpen ? "open" : ""}`}>
                    ${runsPanelOpen ? "▾" : "◂"}
                  </span>
                </button>
              </div>
            </div>
            ${runsPanelOpen
              ? html`
                  <div className="runs-panel-content">
                    <div className="field">
                      <label>Output Root</label>
                      <input
                        value=${outputRoot}
                        onInput=${(e) => setOutputRoot(e.target.value)}
                        placeholder="H:\\...\\StrataWave\\out\\ui"
                      />
                    </div>
                    <div className="tree-box">
                      ${Object.keys(runsTree).length === 0
                        ? html`<div className="muted">No run tree.</div>`
                        : Object.entries(runsTree).map(
                            ([project, motions]) => html`
                              <details open>
                                <summary><strong>${project}</strong></summary>
                                <div className="tree-nodes">
                                  ${Object.entries(motions).map(
                                    ([motionName, motionRuns]) => html`
                                      <details>
                                        <summary>${motionName}</summary>
                                        <div className="tree-nodes">
                                          ${motionRuns.map(
                                            (run) => html`
                                              <button
                                                className=${`run-link ${
                                                  selectedRunId === run.run_id ? "active" : ""
                                                }`}
                                                onClick=${() => setSelectedRunId(run.run_id)}
                                              >
                                                <span>${run.run_id} (${run.status})</span>
                                                <span
                                                  className=${`chip ${runSeverityChipClass(
                                                    run.convergence_severity
                                                  )}`}
                                                >
                                                  ${runSeverityLabel(run)}
                                                </span>
                                              </button>
                                            `
                                          )}
                                        </div>
                                      </details>
                                    `
                                  )}
                                </div>
                              </details>
                            `
                          )}
                    </div>

                    <h3>Latest Runs</h3>
                    <div className="cards">
                      ${runs.map(
                        (run) => html`
                          <button
                            className=${`run-card ${selectedRunId === run.run_id ? "active" : ""}`}
                            onClick=${() => setSelectedRunId(run.run_id)}
                          >
                            <div className="run-id">${run.run_id}</div>
                            <div className="muted">${mini(run.project_name || "")}</div>
                            <div className="muted">${mini(run.motion_name || run.input_motion || "")}</div>
                            <div className="chips">
                              <span className=${`chip ${run.status === "ok" ? "chip-ok" : "chip-bad"}`}
                                >${run.status}</span
                              >
                              <span className="chip chip-ok">${run.solver_backend}</span>
                              <span className=${`chip ${runSeverityChipClass(run.convergence_severity)}`}>
                                ${runSeverityLabel(run)}
                              </span>
                            </div>
                            <div className="muted">PGA: ${fmt(run.pga)}</div>
                            ${runWarningHint(run)
                              ? html`<div className="muted">${runWarningHint(run)}</div>`
                              : null}
                          </button>
                        `
                      )}
                    </div>
                  </div>
                `
              : html`
                  <div className="muted">
                    Runs panel collapsed. Sag ustteki ucgen ile tekrar acabilirsiniz.
                  </div>
                `}
                </section>
              `
            : null}

          <section className="panel-block">
            <div className="row between">
              <h3>${isResultsFrameMode ? "Results Frame" : "Results"}</h3>
              <div className="row">
                <button
                  className="btn-min"
                  onClick=${() =>
                    setResultsFrameMode((prev) =>
                      prev === "results_only" ? "integrated" : "results_only"
                    )}
                >
                  ${isResultsFrameMode ? "Back to Workspace" : "Open Results Frame"}
                </button>
                ${selectedRunId
                  ? html`
                      <div className="download-row">
                        <a className="btn-min" href=${artifactLinks.surface}>surface_acc.csv</a>
                        <a className="btn-min" href=${artifactLinks.pwp}>pwp_effective.csv</a>
                        <a className="btn-min" href=${artifactLinks.h5}>results.h5</a>
                        <a className="btn-min" href=${artifactLinks.sqlite}>results.sqlite</a>
                        <a className="btn-min" href=${artifactLinks.meta}>run_meta.json</a>
                      </div>
                    `
                  : null}
              </div>
            </div>

            ${isResultsFrameMode
              ? html`
                  <div className="row results-frame-controls">
                    <div className="field">
                      <label>Selected Run</label>
                      <select
                        value=${selectedRunId || ""}
                        onInput=${(e) => setSelectedRunId(e.target.value)}
                      >
                        <option value="">Select run</option>
                        ${runs.map(
                          (run) => html`
                            <option value=${run.run_id}>
                              ${run.run_id} | ${mini(run.motion_name || run.input_motion || "")}
                            </option>
                          `
                        )}
                      </select>
                    </div>
                    <div className="field align-end">
                      <button
                        className="btn-sub"
                        onClick=${() => {
                          loadRuns().catch(() => {});
                          loadRunsTree().catch(() => {});
                        }}
                      >
                        Refresh Runs
                      </button>
                    </div>
                  </div>
                `
              : null}

            <div className="tab-row results-tab-row">
              ${RESULT_TABS.map(
                (tab) => html`
                  <button
                    className=${`tab-btn ${activeResultTab === tab ? "active" : ""}`}
                    onClick=${() => setActiveResultTab(tab)}
                  >
                    ${tab}
                  </button>
                `
              )}
            </div>

            <div className="quality-grid">
              <section className="quality-card">
                <div className="row between">
                  <strong>Parity Health</strong>
                  <button
                    className="btn-min"
                    onClick=${() => loadParityLatest().catch(() => {})}
                  >
                    Refresh
                  </button>
                </div>
                ${!parityLatest || !parityLatest.found
                  ? html`<div className="muted">No parity report found under current output root.</div>`
                  : html`
                      <div className="muted">Report: ${mini(parityLatest.report_path || "")}</div>
                      <div className="muted">
                        Suite bundle: ${parityLatest.suite || "unknown"} | generated:
                        ${parityLatest.generated_utc || "n/a"}
                      </div>
                      ${parityPrimary
                        ? html`
                            <div className="metric-grid quality-metrics">
                              <div className="metric-card">
                                <span>Primary Suite</span><b>${parityPrimary.suite}</b>
                              </div>
                              <div className="metric-card">
                                <span>Coverage</span
                                ><b>${fmt(Number(parityPrimary.execution_coverage || 0), 3)}</b>
                              </div>
                              <div className="metric-card">
                                <span>Runs</span
                                ><b>${parityPrimary.ran}/${parityPrimary.total_cases}</b>
                              </div>
                              <div className="metric-card">
                                <span>Fingerprint</span><b>${mini(parityPrimary.binary_fingerprint || "n/a")}</b>
                              </div>
                            </div>
                            <div className=${`status ${
                              parityPrimary.all_passed &&
                              parityPrimary.backend_ready &&
                              parityPrimary.backend_fingerprint_ok &&
                              Number(parityPrimary.skipped || 0) === 0
                                ? "status-ok"
                                : "status-err"
                            }`}>
                              <strong>
                                ${parityPrimary.all_passed &&
                                parityPrimary.backend_ready &&
                                parityPrimary.backend_fingerprint_ok &&
                                Number(parityPrimary.skipped || 0) === 0
                                  ? "Parity gate healthy"
                                  : "Parity gate has blockers"}
                              </strong>
                              ${parityBlockText
                                ? html`<div className="muted">Blockers: ${parityBlockText}</div>`
                                : null}
                            </div>
                          `
                        : null}
                      ${paritySuites.length > 0
                        ? html`
                            <div className="quality-list">
                              ${paritySuites.map(
                                (row) => html`
                                  <div className="quality-list-row">
                                    <span><strong>${row.suite}</strong></span>
                                    <span className=${`chip ${row.all_passed ? "chip-ok" : "chip-bad"}`}
                                      >${row.all_passed ? "pass" : "fail"}</span
                                    >
                                    <span className="muted"
                                      >cov=${fmt(Number(row.execution_coverage || 0), 3)} |
                                      skipped=${row.skipped}</span
                                    >
                                  </div>
                                `
                              )}
                            </div>
                          `
                        : null}
                    `}
              </section>

              <section className="quality-card">
                <div className="row between">
                  <strong>Scientific Confidence</strong>
                  <button className="btn-min" onClick=${() => loadScienceConfidence().catch(() => {})}>
                    Refresh
                  </button>
                </div>
                <div className="muted">
                  last_updated=${scienceMatrixMeta.last_updated || "n/a"} |
                  source=${mini(scienceMatrixMeta.source_path || "")}
                </div>
                ${scienceConfidence.length === 0
                  ? html`<div className="muted">No confidence rows loaded.</div>`
                  : html`
                      <div className="quality-list">
                        ${scienceConfidence.map(
                          (row) => html`
                            <div className="quality-list-row">
                              <span><strong>${row.suite}</strong></span>
                              <span className="chip chip-neutral">${row.confidence_tier || "n/a"}</span>
                              <span className="muted">cases=${row.case_count} | verified=${row.last_verified_utc || "n/a"}</span>
                            </div>
                          `
                        )}
                      </div>
                    `}
              </section>

              <section className="quality-card">
                <div className="row between">
                  <strong>Release Blockers</strong>
                  <div className="row">
                    <button
                      className="btn-min"
                      onClick=${() => {
                        loadParityLatest().catch(() => {});
                        loadReleaseSignoff().catch(() => {});
                        loadScienceConfidence().catch(() => {});
                      }}
                    >
                      Refresh
                    </button>
                    <span className=${`chip ${releaseHealth.ready ? "chip-ok" : "chip-bad"}`}>
                      ${releaseHealth.ready ? "go" : "no-go"}
                    </span>
                  </div>
                </div>
                ${releaseSignoff && releaseSignoff.found
                  ? html`
                      <div className="muted">
                        signoff: ${mini(releaseSignoff.summary_path || "")} |
                        generated=${releaseSignoff.generated_utc || "n/a"} |
                        strict=${releaseSignoff.strict_signoff ? "yes" : "no"} |
                        passed=${releaseSignoff.signoff_passed ? "yes" : "no"} |
                        severity=${releaseSignoff.severity_label || "unknown"} (${fmt(
                          Number(releaseSignoff.severity_score || 0),
                          0
                        )})
                      </div>
                    `
                  : null}
                <div
                  className=${`status ${releaseHealth.ready ? "status-ok" : "status-err"}`}
                >
                  <strong>
                    ${releaseHealth.ready
                      ? "Release signoff conditions look healthy."
                      : "Release is blocked by one or more critical checks."}
                  </strong>
                </div>
                <div className="quality-list">
                  ${(releaseHealth.checks || []).map(
                    (row) => html`
                      <div className="quality-list-row">
                        <span><strong>${row.label}</strong></span>
                        <span className=${`chip ${row.ok ? "chip-ok" : "chip-bad"}`}
                          >${row.ok ? "ok" : "fail"}</span
                        >
                        <span className="muted">${row.value || "n/a"}</span>
                      </div>
                    `
                  )}
                </div>
                ${releaseHealth.blockers.length
                  ? html`
                      <div className="quality-subtitle">Critical blockers</div>
                      <div className="quality-list quality-list-compact">
                        ${releaseHealth.blockers.map(
                          (item) => html`<div className="quality-list-row quality-list-row-err">${item}</div>`
                        )}
                      </div>
                    `
                  : null}
                ${releaseHealth.warnings.length
                  ? html`
                      <div className="quality-subtitle">Warnings</div>
                      <div className="quality-list quality-list-compact">
                        ${releaseHealth.warnings.map(
                          (item) => html`<div className="quality-list-row quality-list-row-warn">${item}</div>`
                        )}
                      </div>
                    `
                  : null}
              </section>
            </div>

            <div className="compare-box">
              <div className="row between">
                <strong>Multi-Motion Compare</strong>
                <div className="row">
                  <button
                    className="btn-min"
                    onClick=${loadCompareSignals}
                    disabled=${compareLoading || compareRunIds.length === 0}
                  >
                    ${compareLoading ? "Loading..." : "Load Compare"}
                  </button>
                  <button
                    className="btn-min"
                    onClick=${clearCompareSignals}
                    disabled=${Object.keys(compareSignals || {}).length === 0}
                  >
                    Clear
                  </button>
                </div>
              </div>
              <div className="compare-selector-grid">
                ${runs.slice(0, 20).map(
                  (run) => html`
                    <label className="compare-pick">
                      <input
                        type="checkbox"
                        checked=${compareRunIds.includes(run.run_id)}
                        onChange=${() => toggleCompareRun(run.run_id)}
                      />
                      <span>${run.run_id}</span>
                      <small>${mini(run.motion_name || run.input_motion || "")}</small>
                    </label>
                  `
                )}
              </div>
              <div className="muted">
                Selected: ${compareRunIds.length} run(s) (max 6). Load Compare to overlay charts.
              </div>
              ${compareRunIds.length > 0
                ? html`
                    <div className="field">
                      <label>Reference Run (for ratio/Δ)</label>
                      <select
                        value=${compareReferenceId || ""}
                        onInput=${(e) => setCompareReferenceId(e.target.value)}
                      >
                        ${compareRunIds.map((id) => html`<option value=${id}>${id}</option>`)}
                      </select>
                    </div>
                  `
                : null}

              ${compareSeries.count > 0
                ? html`
                    <div className="metric-grid">
                      ${compareSeries.metrics.map(
                        (row) => html`
                          <div className="metric-card" key=${`cmp-${row.runId}`}>
                            <span>${row.label}</span>
                            <b>PGA: ${fmt(row.pga, 4)}</b>
                          </div>
                        `
                      )}
                    </div>
                    <div className="charts-grid">
                      <${MultiSeriesChartCard}
                        title="Compare Surface Acceleration"
                        subtitle="Overlay by selected runs"
                        series=${compareSeries.time}
                      />
                      <${MultiSeriesChartCard}
                        title="Compare PSA (5%)"
                        subtitle="Overlay by selected runs"
                        series=${compareSeries.psa}
                      />
                      <${MultiSeriesChartCard}
                        title="Compare Transfer |H(f)|"
                        subtitle="Overlay by selected runs"
                        series=${compareSeries.transfer}
                      />
                      <${MultiSeriesChartCard}
                        title="PSA Ratio to Reference"
                        subtitle=${compareReferenceDerived.referenceId
                          ? `ref=${compareReferenceDerived.referenceId}`
                          : "select a reference run"}
                        series=${compareReferenceDerived.ratioPsa}
                      />
                      <${MultiSeriesChartCard}
                        title="Transfer Δ to Reference"
                        subtitle=${compareReferenceDerived.referenceId
                          ? `ref=${compareReferenceDerived.referenceId}`
                          : "select a reference run"}
                        series=${compareReferenceDerived.deltaTransfer}
                      />
                      <${MultiSeriesChartCard}
                        title="Surface Acc Δ to Reference"
                        subtitle=${compareReferenceDerived.referenceId
                          ? `ref=${compareReferenceDerived.referenceId}`
                          : "select a reference run"}
                        series=${compareReferenceDerived.deltaTime}
                      />
                    </div>
                    ${compareReferenceDerived.metrics.length > 0
                      ? html`
                          <div className="metric-grid">
                            ${compareReferenceDerived.metrics.map(
                              (row) => html`
                                <div className="metric-card" key=${`cmp-delta-${row.runId}`}>
                                  <span>${row.label}</span>
                                  <b>ΔPGA: ${fmt(row.deltaPga, 4)}</b><br />
                                  <b>PGA Ratio: ${fmt(row.ratioPga, 4)}</b>
                                </div>
                              `
                            )}
                          </div>
                        `
                      : null}
                  `
                : null}
            </div>

            ${!selectedRunId
              ? html`<div className="muted">Select a run to view results.</div>`
              : null}

            ${selectedRunId && activeResultTab === "Time Histories" && runSignal
              ? html`
                  <div className="metric-grid">
                    <div className="metric-card"><span>PGA</span><b>${fmt(metrics.pga)}</b></div>
                    <div className="metric-card"><span>ru_max</span><b>${fmt(metrics.ruMax)}</b></div>
                    <div className="metric-card">
                      <span>delta_u_max</span><b>${fmt(metrics.duMax)}</b>
                    </div>
                    <div className="metric-card">
                      <span>sigma_v_eff_min</span><b>${fmt(metrics.sigmaMin)}</b>
                    </div>
                    <div className="metric-card"><span>dt_s</span><b>${fmt(metrics.dt, 6)}</b></div>
                  </div>
                  <div className="charts-grid">
                    <${ChartCard}
                      title="Surface Acceleration"
                      x=${runSignal.time_s || []}
                      y=${runSignal.surface_acc_m_s2 || []}
                      color="var(--copper)"
                    />
                    <${ChartCard}
                      title="Pore Pressure Ratio (ru)"
                      x=${runSignal.ru_time_s || runSignal.ru_t || []}
                      y=${runSignal.ru || []}
                      color="var(--stone)"
                    />
                    <${ChartCard}
                      title="delta_u"
                      x=${runSignal.delta_u_time_s || runSignal.delta_u_t || []}
                      y=${runSignal.delta_u || []}
                      color="#7f5f2d"
                    />
                    <${ChartCard}
                      title="sigma_v_eff"
                      x=${runSignal.sigma_v_eff_time_s || runSignal.sigma_v_eff_t || []}
                      y=${runSignal.sigma_v_eff || []}
                      color="#1b7d87"
                      subtitle=${`sigma_v_ref=${fmt(metrics.sigmaRef)}`}
                    />
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Spectral" && runSignal
              ? html`
                  <div className="charts-grid">
                    <${ChartCard}
                      title="PSA (5%)"
                      x=${runSignal.period_s || []}
                      y=${runSignal.psa_m_s2 || []}
                      color="var(--teal)"
                      subtitle=${runSignal.spectra_source || "recomputed"}
                    />
                    <${ChartCard}
                      title="Transfer |H(f)|"
                      x=${runSignal.freq_hz || []}
                      y=${runSignal.transfer_abs || []}
                      color="var(--indigo)"
                    />
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Profile" && runSummary
              ? html`
                  <div className="profile-grid">
                    <div className="metric-card">
                      <span>Project</span><b>${runSummary.project_name || "n/a"}</b>
                    </div>
                    <div className="metric-card">
                      <span>Backend</span><b>${runSummary.solver_backend || "n/a"}</b>
                    </div>
                    <div className="metric-card">
                      <span>Status</span><b>${runSummary.status || "n/a"}</b>
                    </div>
                    <div className="metric-card">
                      <span>Layers</span><b>${(runSummary.output_layers || []).join(", ") || "n/a"}</b>
                    </div>
                  </div>
                  <div className=${`status ${convergenceSeverityClass(convergenceView.severity)}`}>
                    <div className="row between">
                      <strong>Solver Health</strong>
                      <span className=${`diag-chip ${convergenceSeverityClass(convergenceView.severity)}`}>
                        ${String(convergenceView.severity || "neutral").toUpperCase()}
                      </span>
                    </div>
                    <div className="muted">${convergenceView.subtitle || "No diagnostics."}</div>
                  </div>
                  ${profileHealthCards.length > 0
                    ? html`
                        <div className="metric-grid profile-health-grid">
                          ${profileHealthCards.map(
                            (item) => html`
                              <div key=${`profile-health-${item.label}`} className="metric-card">
                                <span>${item.label}</span>
                                <b>${item.value}</b>
                              </div>
                            `
                          )}
                        </div>
                      `
                    : null}
                  ${runProfileSummary && Array.isArray(runProfileSummary.layers)
                    ? html`
                        <div className="metric-grid">
                          <div className="metric-card">
                            <span>Layer Count</span>
                            <b>${runProfileSummary.layer_count ?? runProfileSummary.layers.length}</b>
                          </div>
                          <div className="metric-card">
                            <span>Total Thickness (m)</span>
                            <b>${fmt(runProfileSummary.total_thickness_m, 3)}</b>
                          </div>
                          <div className="metric-card">
                            <span>ru_max</span>
                            <b>${fmt(runProfileSummary.ru_max, 4)}</b>
                          </div>
                          <div className="metric-card">
                            <span>delta_u_max</span>
                            <b>${fmt(runProfileSummary.delta_u_max, 4)}</b>
                          </div>
                          <div className="metric-card">
                            <span>sigma_v_eff_min</span>
                            <b>${fmt(runProfileSummary.sigma_v_eff_min, 4)}</b>
                          </div>
                        </div>
                        <div className="layer-table-wrap profile-summary-wrap">
                          <table className="layer-table profile-summary-table">
                            <thead>
                              <tr>
                                <th>Idx</th>
                                <th>Name</th>
                                <th>Material</th>
                                <th>z_top (m)</th>
                                <th>z_bottom (m)</th>
                                <th>Thickness (m)</th>
                                <th>Vs (m/s)</th>
                                <th>Unit W. (kN/m^3)</th>
                                <th>n_sub</th>
                                <th>gamma_max</th>
                              </tr>
                            </thead>
                            <tbody>
                              ${runProfileSummary.layers.map(
                                (layer) => html`
                                  <tr key=${`profile-layer-${layer.idx}-${layer.name}`}>
                                    <td>${layer.idx}</td>
                                    <td>${layer.name}</td>
                                    <td>${layer.material}</td>
                                    <td>${fmt(layer.z_top_m, 3)}</td>
                                    <td>${fmt(layer.z_bottom_m, 3)}</td>
                                    <td>${fmt(layer.thickness_m, 3)}</td>
                                    <td>${fmt(layer.vs_m_s, 2)}</td>
                                    <td>${fmt(layer.unit_weight_kN_m3 ?? layer.unit_weight_kn_m3, 2)}</td>
                                    <td>${layer.n_sub}</td>
                                    <td>${fmt(layer.gamma_max, 6)}</td>
                                  </tr>
                                `
                              )}
                            </tbody>
                          </table>
                        </div>
                      `
                    : null}
                  <div className="muted">
                    Solver notes: ${runSummary.solver_notes || "n/a"}<br />
                    Motion: ${runSummary.input_motion || "n/a"}
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Convergence" && runSummary
              ? html`
                  <div className="convergence-shell">
                    <div className=${`status ${convergenceSeverityClass(convergenceView.severity)}`}>
                      <div className="row between">
                        <strong>${convergenceView.title}</strong>
                        <span className=${`diag-chip ${convergenceSeverityClass(convergenceView.severity)}`}>
                          ${String(convergenceView.severity || "neutral").toUpperCase()}
                        </span>
                      </div>
                      <div className="muted">${convergenceView.subtitle}</div>
                    </div>
                    <div className="metric-grid">
                      ${(convergenceView.cards || []).map(
                        (item) => html`
                          <div key=${`conv-${item.label}`} className="metric-card">
                            <span>${item.label}</span>
                            <b>${item.value}</b>
                          </div>
                        `
                      )}
                    </div>
                    <details className="json-details">
                      <summary>Raw payload</summary>
                      <pre className="json-box">
${JSON.stringify(convergenceView.raw || { available: false }, null, 2)}
                      </pre>
                    </details>
                  </div>
                `
              : null}

            ${selectedRunId && activeResultTab === "Stress-Strain"
              ? html`
                  ${hysteresisView.layers.length === 0
                    ? html`
                        <div className="muted">
                          ${(runHysteresis && runHysteresis.note) || "No stress-strain data."}
                        </div>
                      `
                    : html`
                        <div className="row">
                          <div className="field">
                            <label>Layer</label>
                            <select
                              value=${String(hysteresisView.selected?.layer_index ?? "")}
                              onInput=${(e) => setSelectedLayerIndex(String(e.target.value))}
                            >
                              ${hysteresisView.layers.map(
                                (layer) => html`
                                  <option value=${String(layer.layer_index)}>
                                    ${layer.layer_index}: ${layer.layer_name} (${layer.model})
                                  </option>
                                `
                              )}
                            </select>
                          </div>
                        </div>
                        <div className="metric-grid">
                          <div className="metric-card">
                            <span>Material</span>
                            <b>${hysteresisView.selected?.material || "n/a"}</b>
                          </div>
                          <div className="metric-card">
                            <span>Model</span>
                            <b>${hysteresisView.selected?.model || "n/a"}</b>
                          </div>
                          <div className="metric-card">
                            <span>strain_amplitude</span>
                            <b>${fmt(hysteresisView.selected?.strain_amplitude, 6)}</b>
                          </div>
                          <div className="metric-card">
                            <span>loop_energy</span>
                            <b>${fmt(hysteresisView.selected?.loop_energy, 6)}</b>
                          </div>
                          <div className="metric-card">
                            <span>G/Gmax</span>
                            <b>${fmt(hysteresisView.selected?.g_over_gmax, 6)}</b>
                          </div>
                          <div className="metric-card">
                            <span>damping_proxy</span>
                            <b>${fmt(hysteresisView.selected?.damping_proxy, 6)}</b>
                          </div>
                        </div>
                        <div className="charts-grid">
                          <${ChartCard}
                            title="Stress-Strain Loop"
                            subtitle=${hysteresisView.selected?.is_proxy
                              ? "proxy curve"
                              : "from stored layer model"}
                            x=${hysteresisView.selected?.strain || []}
                            y=${hysteresisView.selected?.stress || []}
                            color="var(--stone)"
                          />
                        </div>
                        ${runHysteresis?.note
                          ? html`<div className="muted">${runHysteresis.note}</div>`
                          : null}
                      `}
                `
              : null}

            ${selectedRunId && activeResultTab === "Mobilized Strength"
              ? html`
                  ${hysteresisView.layers.length === 0
                    ? html`
                        <div className="muted">
                          ${(runHysteresis && runHysteresis.note) || "No mobilized-strength data."}
                        </div>
                      `
                    : html`
                        <div className="metric-grid">
                          <div className="metric-card">
                            <span>Layer count</span><b>${hysteresisView.layers.length}</b>
                          </div>
                          <div className="metric-card">
                            <span>Source</span><b>${runHysteresis?.source || "n/a"}</b>
                          </div>
                          <div className="metric-card">
                            <span>Max mobilized ratio</span>
                            <b>${fmt(Math.max(...hysteresisView.ratioY), 4)}</b>
                          </div>
                          <div className="metric-card">
                            <span>Mean mobilized ratio</span>
                            <b>
                              ${fmt(
                                hysteresisView.ratioY.reduce((a, b) => a + b, 0) /
                                  Math.max(hysteresisView.ratioY.length, 1),
                                4
                              )}
                            </b>
                          </div>
                        </div>
                        <div className="charts-grid">
                          <${ChartCard}
                            title="Mobilized Strength Ratio by Layer"
                            x=${hysteresisView.ratioX}
                            y=${hysteresisView.ratioY}
                            color="var(--copper)"
                          />
                          <${ChartCard}
                            title="Loop Energy by Layer"
                            x=${hysteresisView.energyX}
                            y=${hysteresisView.energyY}
                            color="var(--teal)"
                          />
                        </div>
                        ${runHysteresis?.note
                          ? html`<div className="muted">${runHysteresis.note}</div>`
                          : null}
                      `}
                `
              : null}
          </section>
        </main>
      </section>
    </div>
  `;
}

const root = createRoot(document.getElementById("app"));
root.render(html`<${App} />`);

