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
