/**
 * GeoWave v3 — 3-Tier Plan & Feature Gating
 *
 * Free → Starter → Pro
 * Demo mode: plan toggled via localStorage.
 */
import { html } from "./setup.js";

// ── Plan Definitions ────────────────────────────────────

export const PLANS = {
  free: {
    id: "free",
    label: "Free",
    color: "#95a5a6",
    runsPerDay: 3,
    order: 0,
  },
  starter: {
    id: "starter",
    label: "Starter",
    color: "#2980B9",
    runsPerDay: 10,
    order: 1,
  },
  pro: {
    id: "pro",
    label: "Pro",
    color: "#D35400",
    runsPerDay: Infinity,
    order: 2,
  },
};

// Minimum plan required per feature
const FEATURE_MIN_PLAN = {
  // Starter features
  excel_export:    "starter",
  run_comparison:  "starter",
  dark_mode:       "starter",
  svg_export:      "starter",
  batch_analysis:  "starter",
  // Pro features
  psv_psd:         "pro",
  kappa:           "pro",
  site_period:     "pro",
  smoothed_tf:     "pro",
};

// Human-readable labels
export const FEATURE_LABELS = {
  excel_export:    "Excel Export (Multi-Sheet)",
  run_comparison:  "Run Comparison",
  dark_mode:       "Dark Mode",
  svg_export:      "SVG Chart Export",
  batch_analysis:  "Batch Analysis",
  psv_psd:         "PSV / PSD Spectral Charts",
  kappa:           "Kappa (κ) Estimator",
  site_period:     "Site Period (T₀)",
  smoothed_tf:     "Smoothed Transfer Function",
};

// ── Plan State ──────────────────────────────────────────

const PLAN_STORAGE_KEY = "stratawave_plan";
const PLAN_CYCLE = ["free", "starter", "pro"];

export function getStoredPlan() {
  try {
    const val = localStorage.getItem(PLAN_STORAGE_KEY);
    return PLAN_CYCLE.includes(val) ? val : "free";
  } catch { return "free"; }
}

export function setStoredPlan(planId) {
  try { localStorage.setItem(PLAN_STORAGE_KEY, planId); } catch {}
}

export function nextPlan(current) {
  const idx = PLAN_CYCLE.indexOf(current);
  return PLAN_CYCLE[(idx + 1) % PLAN_CYCLE.length];
}

// ── Helpers ─────────────────────────────────────────────

export function planOrder(planId) {
  return (PLANS[planId] || PLANS.free).order;
}

export function canUseFeature(currentPlan, featureKey) {
  const minPlan = FEATURE_MIN_PLAN[featureKey];
  if (!minPlan) return true; // not gated
  return planOrder(currentPlan) >= planOrder(minPlan);
}

export function requiredPlanFor(featureKey) {
  return FEATURE_MIN_PLAN[featureKey] || "free";
}

// ── UI Components ───────────────────────────────────────

/** Small tier badge (STARTER / PRO) next to feature names */
export function TierBadge({ feature }) {
  const minPlan = FEATURE_MIN_PLAN[feature];
  if (!minPlan) return null;
  const info = PLANS[minPlan];
  return html`
    <span className="tier-badge" style=${{ background: info.color }}>${info.label.toUpperCase()}</span>
  `;
}

/** Wraps content — shows lock overlay if plan too low */
export function ProGuard({ plan, feature, children }) {
  if (canUseFeature(plan, feature)) return children;

  const label = FEATURE_LABELS[feature] || feature;
  const required = PLANS[requiredPlanFor(feature)];
  return html`
    <div className="pro-guard">
      <div className="pro-guard-overlay">
        <div className="pro-guard-content">
          <span className="pro-guard-icon">🔒</span>
          <span className="pro-guard-label">${label}</span>
          <span className="pro-guard-hint">Requires <b style=${{ color: required.color }}>${required.label}</b> plan</span>
        </div>
      </div>
      <div className="pro-guard-blurred">
        ${children}
      </div>
    </div>
  `;
}

/** For backward compat — simple PRO badge */
export function ProBadge() {
  return html`<span className="tier-badge" style=${{ background: "#D35400" }}>PRO</span>`;
}

/** Plan toggle button in header — cycles Free → Starter → Pro */
export function PlanToggle({ plan, onToggle }) {
  const info = PLANS[plan] || PLANS.free;
  return html`
    <button type="button" className="plan-toggle" onClick=${onToggle}
      aria-label="Cycle demo subscription plan"
      style=${{ borderColor: info.color, color: info.color }}
      title="Click to cycle plan (demo): Free → Starter → Pro">
      ${info.label}
    </button>
  `;
}
