/**
 * StrataWave v2 — SVG Chart Components
 *
 * ChartCard          — single series line chart
 * MultiSeriesChart   — multi-series overlay with log-x support
 * DepthProfileChart  — horizontal depth-oriented profile
 */
import { html } from "./setup.js";
import { fmt } from "./utils.js";

// ── Geometry helpers ─────────────────────────────────────

function linearTicks(min, max, count = 5) {
  if (!isFinite(min) || !isFinite(max) || max <= min) return [];
  const step = (max - min) / count;
  const ticks = [];
  for (let i = 0; i <= count; i++) ticks.push(min + i * step);
  return ticks;
}

function logTicks(min, max) {
  if (min <= 0) min = 1e-6;
  if (max <= min) max = min * 10;
  const logMin = Math.floor(Math.log10(min));
  const logMax = Math.ceil(Math.log10(max));
  const ticks = [];
  for (let e = logMin; e <= logMax; e++) {
    ticks.push(Math.pow(10, e));
  }
  return ticks;
}

function buildGeometry(x, y, w, h, pad, opts = {}) {
  const logX = opts.logX || false;
  const xArr = Array.isArray(x) ? x : [];
  const yArr = Array.isArray(y) ? y : [];
  if (xArr.length < 2 || yArr.length < 2) return null;

  const xMin = opts.xMin != null ? opts.xMin : Math.min(...xArr);
  const xMax = opts.xMax != null ? opts.xMax : Math.max(...xArr);
  const yMin = opts.yMin != null ? opts.yMin : Math.min(...yArr);
  const yMax = opts.yMax != null ? opts.yMax : Math.max(...yArr);

  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  function scaleX(v) {
    if (logX) {
      const lMin = Math.log10(Math.max(xMin, 1e-10));
      const lMax = Math.log10(Math.max(xMax, 1e-9));
      const lv = Math.log10(Math.max(v, 1e-10));
      return pad.left + ((lv - lMin) / (lMax - lMin)) * plotW;
    }
    return pad.left + ((v - xMin) / (xMax - xMin || 1)) * plotW;
  }

  function scaleY(v) {
    return pad.top + plotH - ((v - yMin) / (yMax - yMin || 1)) * plotH;
  }

  const points = xArr.map((xi, i) => `${scaleX(xi)},${scaleY(yArr[i])}`).join(" ");

  const xTicks = logX ? logTicks(xMin, xMax) : linearTicks(xMin, xMax, 5);
  const yTicks = linearTicks(yMin, yMax, 5);

  return { points, scaleX, scaleY, xTicks, yTicks, xMin, xMax, yMin, yMax, plotW, plotH, pad };
}

// ── Axis renderer ────────────────────────────────────────

function Axes({ geo, w, h, xLabel, yLabel, logX }) {
  if (!geo) return null;
  const { scaleX, scaleY, xTicks, yTicks, pad, plotH } = geo;

  return html`
    <g className="axes">
      <!-- X axis line -->
      <line x1=${pad.left} y1=${pad.top + plotH} x2=${w - pad.right} y2=${pad.top + plotH}
        stroke="var(--ink-40)" stroke-width="1" />
      <!-- Y axis line -->
      <line x1=${pad.left} y1=${pad.top} x2=${pad.left} y2=${pad.top + plotH}
        stroke="var(--ink-40)" stroke-width="1" />

      <!-- X ticks -->
      ${xTicks.map(t => {
        const tx = scaleX(t);
        if (tx < pad.left || tx > w - pad.right) return null;
        return html`
          <g key=${"xt" + t}>
            <line x1=${tx} y1=${pad.top + plotH} x2=${tx} y2=${pad.top + plotH + 4}
              stroke="var(--ink-40)" stroke-width="1" />
            <line x1=${tx} y1=${pad.top} x2=${tx} y2=${pad.top + plotH}
              stroke="var(--ink-10)" stroke-width="0.5" stroke-dasharray="2,3" />
            <text x=${tx} y=${h - 4} text-anchor="middle" fill="var(--ink-60)" font-size="9">
              ${logX ? t.toExponential(0) : fmt(t, 2)}
            </text>
          </g>
        `;
      })}

      <!-- Y ticks -->
      ${yTicks.map(t => {
        const ty = scaleY(t);
        if (ty < pad.top || ty > pad.top + plotH) return null;
        return html`
          <g key=${"yt" + t}>
            <line x1=${pad.left - 4} y1=${ty} x2=${pad.left} y2=${ty}
              stroke="var(--ink-40)" stroke-width="1" />
            <line x1=${pad.left} y1=${ty} x2=${w - pad.right} y2=${ty}
              stroke="var(--ink-10)" stroke-width="0.5" stroke-dasharray="2,3" />
            <text x=${pad.left - 6} y=${ty + 3} text-anchor="end" fill="var(--ink-60)" font-size="9">
              ${fmt(t, 3)}
            </text>
          </g>
        `;
      })}

      <!-- Labels -->
      ${xLabel ? html`
        <text x=${pad.left + geo.plotW / 2} y=${h - 1} text-anchor="middle"
          fill="var(--ink-70)" font-size="10" font-weight="600">${xLabel}</text>
      ` : null}
      ${yLabel ? html`
        <text x=${12} y=${pad.top + plotH / 2} text-anchor="middle"
          fill="var(--ink-70)" font-size="10" font-weight="600"
          transform="rotate(-90, 12, ${pad.top + plotH / 2})">${yLabel}</text>
      ` : null}
    </g>
  `;
}

// ── Chart Card ───────────────────────────────────────────

const COLORS = [
  "var(--accent, #D35400)", "#2980B9", "#27AE60", "#8E44AD",
  "#E74C3C", "#16A085", "#F39C12", "#2C3E50",
];

const PAD = { top: 20, right: 20, bottom: 36, left: 52 };

export function ChartCard({ title, subtitle, x, y, color, xLabel, yLabel, logX, w = 480, h = 240 }) {
  const geo = buildGeometry(x, y, w, h, PAD, { logX });
  if (!geo) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  return html`
    <div className="chart-card">
      <h4>${title}${subtitle ? html` <small className="muted">${subtitle}</small>` : null}</h4>
      <svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet">
        <${Axes} geo=${geo} w=${w} h=${h} xLabel=${xLabel} yLabel=${yLabel} logX=${logX} />
        <polyline points=${geo.points} fill="none" stroke=${color || COLORS[0]} stroke-width="1.5" />
      </svg>
    </div>
  `;
}

export function MultiSeriesChart({ title, subtitle, series, xLabel, yLabel, logX, w = 480, h = 260 }) {
  if (!series || !series.length) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  // Compute global bounds
  let gxMin = Infinity, gxMax = -Infinity, gyMin = Infinity, gyMax = -Infinity;
  for (const s of series) {
    if (!s.x || !s.y || s.x.length < 2) continue;
    for (const v of s.x) { if (v < gxMin) gxMin = v; if (v > gxMax) gxMax = v; }
    for (const v of s.y) { if (v < gyMin) gyMin = v; if (v > gyMax) gyMax = v; }
  }
  if (!isFinite(gxMin)) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  const padLegend = { ...PAD, bottom: PAD.bottom + series.length * 14 };
  const totalH = h + series.length * 14;

  const geos = series.map(s => buildGeometry(s.x, s.y, w, totalH, padLegend, { logX, xMin: gxMin, xMax: gxMax, yMin: gyMin, yMax: gyMax }));

  return html`
    <div className="chart-card">
      <h4>${title}${subtitle ? html` <small className="muted">${subtitle}</small>` : null}</h4>
      <svg viewBox="0 0 ${w} ${totalH}" width="100%" preserveAspectRatio="xMidYMid meet">
        <${Axes} geo=${geos[0]} w=${w} h=${totalH} xLabel=${xLabel} yLabel=${yLabel} logX=${logX} />
        ${geos.map((geo, i) => geo ? html`
          <polyline key=${i} points=${geo.points} fill="none"
            stroke=${series[i].color || COLORS[i % COLORS.length]} stroke-width="1.5" />
        ` : null)}
        <!-- Legend -->
        ${series.map((s, i) => html`
          <g key=${"leg" + i} transform="translate(${PAD.left + 10}, ${totalH - series.length * 14 + i * 14})">
            <circle cx="4" cy="-3" r="4" fill=${s.color || COLORS[i % COLORS.length]} />
            <text x="12" y="0" fill="var(--ink-70)" font-size="9">${s.label || `Series ${i + 1}`}</text>
          </g>
        `)}
      </svg>
    </div>
  `;
}

// ── Layer Colors ─────────────────────────────────────

const LAYER_COLORS = ["#E74C3C","#2980B9","#27AE60","#F1C40F","#E67E22","#9B59B6","#1ABC9C","#E91E63"];

/**
 * DEEPSOIL-style Soil Profile Plot — stratigraphy ribbon + multiple depth columns
 */
export function SoilProfilePlot({ layers, w = 900, h = 400 }) {
  if (!layers || !layers.length) return html`<div className="chart-card"><h4>Soil Profile</h4><p className="muted">No layers</p></div>`;

  const pad = { top: 20, right: 10, bottom: 40, left: 50 };
  const totalDepth = layers.reduce((s, l) => s + (l.thickness_m || l.thickness || 0), 0);
  if (totalDepth <= 0) return null;

  const plotH = h - pad.top - pad.bottom;
  const sy = (d) => pad.top + (d / totalDepth) * plotH;

  // Build step data for each column
  const stepData = [];
  let depth = 0;
  for (const l of layers) {
    const t = l.thickness_m || l.thickness || 0;
    const mp = l.material_params || {};
    const vs = l.vs_m_s || l.vs || 0;
    const gmax = mp.gmax || 0;
    const fmax = vs > 0 && t > 0 ? vs / (4 * t) : 0;
    const dmin = (mp.damping_min || 0) * 100;
    const tau = gmax * (mp.gamma_ref || 0.01); // implied shear strength approx

    stepData.push({ d0: depth, d1: depth + t, vs, fmax, dmin, tau, name: l.name || "", material: l.material || "mkz" });
    depth += t;
  }

  // Columns config
  const columns = [
    { key: "vs", label: "Vs (m/s)", unit: "" },
    { key: "fmax", label: "Max Freq (Hz)", unit: "" },
    { key: "dmin", label: "Damping (%)", unit: "" },
    { key: "tau", label: "Imp. Strength (kPa)", unit: "" },
  ];

  const stratW = 100;
  const colW = (w - pad.left - pad.right - stratW) / columns.length;

  function StepColumn({ colIdx, dataKey, label }) {
    const vals = stepData.map(s => s[dataKey]);
    const maxVal = Math.max(...vals, 0.001);
    const x0 = pad.left + stratW + colIdx * colW;

    return html`
      <g>
        <!-- Column header -->
        <text x=${x0 + colW / 2} y=${pad.top - 6} text-anchor="middle" fill="var(--ink-60)" font-size="8" font-weight="600">${label}</text>
        <!-- Axis line -->
        <line x1=${x0 + 4} y1=${pad.top} x2=${x0 + 4} y2=${pad.top + plotH} stroke="var(--ink-10)" />
        <!-- Step profile -->
        ${stepData.map((s, i) => {
          const barW = (s[dataKey] / maxVal) * (colW - 12);
          return html`
            <g key=${i}>
              <rect x=${x0 + 6} y=${sy(s.d0)} width=${Math.max(barW, 0)} height=${sy(s.d1) - sy(s.d0)}
                fill="#2980B9" fill-opacity="0.15" stroke="#2980B9" stroke-width="0.5" />
              <line x1=${x0 + 6} y1=${sy(s.d0)} x2=${x0 + 6 + Math.max(barW, 0)} y2=${sy(s.d0)}
                stroke="#2980B9" stroke-width="1.5" />
              <line x1=${x0 + 6} y1=${sy(s.d1)} x2=${x0 + 6 + Math.max(barW, 0)} y2=${sy(s.d1)}
                stroke="#2980B9" stroke-width="1.5" />
              <line x1=${x0 + 6 + Math.max(barW, 0)} y1=${sy(s.d0)} x2=${x0 + 6 + Math.max(barW, 0)} y2=${sy(s.d1)}
                stroke="#2980B9" stroke-width="1.5" />
              <text x=${x0 + 10 + Math.max(barW, 0)} y=${(sy(s.d0) + sy(s.d1)) / 2 + 3}
                fill="var(--ink-60)" font-size="8">${fmt(s[dataKey], 1)}</text>
            </g>
          `;
        })}
      </g>
    `;
  }

  return html`
    <div className="chart-card">
      <h4>Soil Profile Definition</h4>
      <svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet">
        <!-- Depth axis -->
        <text x=${14} y=${pad.top + plotH / 2} text-anchor="middle" fill="var(--ink-70)" font-size="10" font-weight="600"
          transform="rotate(-90, 14, ${pad.top + plotH / 2})">Depth (m)</text>
        ${[0, 0.25, 0.5, 0.75, 1.0].map(frac => {
          const d = frac * totalDepth;
          const yp = sy(d);
          return html`
            <g key=${"dtick" + frac}>
              <line x1=${pad.left - 4} y1=${yp} x2=${pad.left} y2=${yp} stroke="var(--ink-40)" />
              <text x=${pad.left - 6} y=${yp + 3} text-anchor="end" fill="var(--ink-60)" font-size="8">${fmt(d, 1)}</text>
            </g>
          `;
        })}

        <!-- Stratigraphy column -->
        <text x=${pad.left + stratW / 2} y=${pad.top - 6} text-anchor="middle" fill="var(--ink-60)" font-size="8" font-weight="600">Layers</text>
        ${stepData.map((s, i) => html`
          <g key=${"strat" + i}>
            <rect x=${pad.left} y=${sy(s.d0)} width=${stratW - 10} height=${sy(s.d1) - sy(s.d0)}
              fill=${LAYER_COLORS[i % LAYER_COLORS.length]} stroke="white" stroke-width="1" rx="2" />
            <text x=${pad.left + (stratW - 10) / 2} y=${(sy(s.d0) + sy(s.d1)) / 2 + 4}
              text-anchor="middle" fill="white" font-size="9" font-weight="600">
              ${s.name || `Layer ${i + 1}`}
            </text>
          </g>
        `)}

        <!-- Value columns -->
        ${columns.map((col, ci) => html`
          <${StepColumn} key=${col.key} colIdx=${ci} dataKey=${col.key} label=${col.label} />
        `)}
      </svg>
    </div>
  `;
}

export function DepthProfileChart({ title, subtitle, depths, values, xLabel, yLabel, color, w = 300, h = 300 }) {
  if (!depths || !values || depths.length < 2) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  const pad = { top: 20, right: 20, bottom: 32, left: 52 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const dMin = Math.min(...depths);
  const dMax = Math.max(...depths);
  const vMin = Math.min(...values);
  const vMax = Math.max(...values);

  function sx(v) { return pad.left + ((v - vMin) / (vMax - vMin || 1)) * plotW; }
  function sy(d) { return pad.top + ((d - dMin) / (dMax - dMin || 1)) * plotH; }

  const points = depths.map((d, i) => `${sx(values[i])},${sy(d)}`).join(" ");

  return html`
    <div className="chart-card">
      <h4>${title}${subtitle ? html` <small className="muted">${subtitle}</small>` : null}</h4>
      <svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet">
        <line x1=${pad.left} y1=${pad.top} x2=${pad.left} y2=${pad.top + plotH} stroke="var(--ink-40)" />
        <line x1=${pad.left} y1=${pad.top + plotH} x2=${w - pad.right} y2=${pad.top + plotH} stroke="var(--ink-40)" />
        <polyline points=${points} fill="none" stroke=${color || COLORS[0]} stroke-width="1.5" />
        ${xLabel ? html`<text x=${pad.left + plotW / 2} y=${h - 2} text-anchor="middle" fill="var(--ink-70)" font-size="10">${xLabel}</text>` : null}
        ${yLabel ? html`<text x=${12} y=${pad.top + plotH / 2} text-anchor="middle" fill="var(--ink-70)" font-size="10" transform="rotate(-90, 12, ${pad.top + plotH / 2})">${yLabel}</text>` : null}
      </svg>
    </div>
  `;
}
