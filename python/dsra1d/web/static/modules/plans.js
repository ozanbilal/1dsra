/**
 * StrataWave v3 — Plan & Feature Gating
 *
 * Defines Free vs Pro feature tiers.
 * In demo mode, plan can be toggled via localStorage.
 */
import { html, useState, useEffect } from "./setup.js";

// ── Plan Definitions ────────────────────────────────────

export const PLANS = {
  free: {
    id: "free",
    label: "Free",
    color: "#95a5a6",
    runsPerDay: 5,
  },
  pro: {
    id: "pro",
    label: "Pro",
    color: "#D35400",
    runsPerDay: Infinity,
  },
};

// Features that require Pro plan
export const PRO_FEATURES = {
  psv_psd: "PSV / PSD Spectral Charts",
  kappa: "Kappa (κ) Estimator",
  site_period: "Site Period (T₀)",
  smoothed_tf: "Smoothed Transfer Function",
  excel_export: "Excel Export (Multi-Sheet)",
  batch_analysis: "Batch Analysis",
  run_comparison: "Run Comparison",
  svg_export: "SVG Chart Export",
  dark_mode: "Dark Mode",
};

// ── Plan State ──────────────────────────────────────────

const PLAN_STORAGE_KEY = "stratawave_plan";

export function getStoredPlan() {
  try {
    return localStorage.getItem(PLAN_STORAGE_KEY) || "free";
  } catch { return "free"; }
}

export function setStoredPlan(planId) {
  try { localStorage.setItem(PLAN_STORAGE_KEY, planId); } catch {}
}

// ── Helpers ─────────────────────────────────────────────

export function isPro(currentPlan) {
  return currentPlan === "pro";
}

export function canUseFeature(currentPlan, featureKey) {
  if (currentPlan === "pro") return true;
  return !(featureKey in PRO_FEATURES);
}

// ── UI Components ───────────────────────────────────────

/**
 * ProBadge — small "PRO" label next to feature names
 */
export function ProBadge() {
  return html`
    <span className="pro-badge">PRO</span>
  `;
}

/**
 * ProGuard — wraps content, shows lock overlay if not Pro
 */
export function ProGuard({ plan, feature, children }) {
  if (isPro(plan)) return children;

  const label = PRO_FEATURES[feature] || feature;
  return html`
    <div className="pro-guard">
      <div className="pro-guard-overlay">
        <div className="pro-guard-content">
          <span className="pro-guard-icon">🔒</span>
          <span className="pro-guard-label">${label}</span>
          <span className="pro-guard-hint">Upgrade to Pro to unlock</span>
        </div>
      </div>
      <div className="pro-guard-blurred">
        ${children}
      </div>
    </div>
  `;
}

/**
 * PlanToggle — demo toggle in header for switching plans
 */
export function PlanToggle({ plan, onToggle }) {
  const planInfo = PLANS[plan] || PLANS.free;
  return html`
    <button className="plan-toggle" onClick=${onToggle}
      style=${{ borderColor: planInfo.color, color: planInfo.color }}
      title="Click to toggle plan (demo)">
      ${planInfo.label}
    </button>
  `;
}
