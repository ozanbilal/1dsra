/**
 * GeoWave v2 — SVG Chart Components
 *
 * ChartCard          — single series line chart
 * MultiSeriesChart   — multi-series overlay with log axes support
 * DepthProfileChart  — horizontal depth-oriented profile
 */
import { html, useState, useCallback, useRef } from "./setup.js";
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
    const base = Math.pow(10, e);
    for (const mult of [1, 2, 5]) {
      const t = base * mult;
      if (t >= min * 0.99 && t <= max * 1.01) ticks.push(t);
    }
  }
  return ticks;
}

function isMajorLogTick(t) {
  const log = Math.log10(t);
  return Math.abs(log - Math.round(log)) < 0.001;
}

function buildGeometry(x, y, w, h, pad, opts = {}) {
  const logX = opts.logX || false;
  const logY = opts.logY || false;
  const xArr = Array.isArray(x) ? x : [];
  const yArr = Array.isArray(y) ? y : [];
  if (xArr.length < 2 || yArr.length < 2) return null;

  const filteredX = logX ? xArr.filter(v => Number.isFinite(v) && v > 0) : xArr.filter(Number.isFinite);
  const filteredY = logY ? yArr.filter(v => Number.isFinite(v) && v > 0) : yArr.filter(Number.isFinite);
  if (filteredX.length < 2 || filteredY.length < 2) return null;

  const xMin = opts.xMin != null ? opts.xMin : Math.min(...filteredX);
  const xMax = opts.xMax != null ? opts.xMax : Math.max(...filteredX);
  const yMin = opts.yMin != null ? opts.yMin : Math.min(...filteredY);
  const yMax = opts.yMax != null ? opts.yMax : Math.max(...filteredY);

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

  function invertX(px) {
    const frac = (px - pad.left) / (plotW || 1);
    const clamped = Math.min(1, Math.max(0, frac));
    if (logX) {
      const lMin = Math.log10(Math.max(xMin, 1e-10));
      const lMax = Math.log10(Math.max(xMax, 1e-9));
      return Math.pow(10, lMin + clamped * (lMax - lMin));
    }
    return xMin + clamped * (xMax - xMin);
  }

  function scaleY(v) {
    if (logY) {
      const lMin = Math.log10(Math.max(yMin, 1e-12));
      const lMax = Math.log10(Math.max(yMax, 1e-11));
      const lv = Math.log10(Math.max(v, 1e-12));
      return pad.top + plotH - ((lv - lMin) / (lMax - lMin || 1)) * plotH;
    }
    return pad.top + plotH - ((v - yMin) / (yMax - yMin || 1)) * plotH;
  }

  const points = xArr
    .map((xi, i) => ({ x: xi, y: yArr[i] }))
    .filter(({ x, y }) => Number.isFinite(x) && Number.isFinite(y) && (!logX || x > 0) && (!logY || y > 0))
    .map(({ x, y }) => `${scaleX(x)},${scaleY(y)}`)
    .join(" ");

  const xTicks = logX ? logTicks(xMin, xMax) : linearTicks(xMin, xMax, 5);
  const yTicks = logY ? logTicks(yMin, yMax) : linearTicks(yMin, yMax, 5);

  return { points, scaleX, scaleY, invertX, xTicks, yTicks, xMin, xMax, yMin, yMax, plotW, plotH, pad };
}

// ── Axis renderer ────────────────────────────────────────

function Axes({ geo, w, h, xLabel, yLabel, logX, logY }) {
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
        const isMajor = logX ? isMajorLogTick(t) : true;
        return html`
          <g key=${"xt" + t}>
            <line x1=${tx} y1=${pad.top + plotH} x2=${tx} y2=${pad.top + plotH + (isMajor ? 4 : 2)}
              stroke="var(--ink-40)" stroke-width="1" />
            <line x1=${tx} y1=${pad.top} x2=${tx} y2=${pad.top + plotH}
              stroke="var(--ink-10)" stroke-width="0.5" stroke-dasharray="2,3" />
            ${isMajor ? html`
              <text x=${tx} y=${h - 4} text-anchor="middle" fill="var(--ink-60)" font-size="9">
                ${logX ? t.toExponential(0) : fmt(t, 2)}
              </text>
            ` : null}
          </g>
        `;
      })}

      <!-- Y ticks -->
      ${yTicks.map(t => {
        const ty = scaleY(t);
        if (ty < pad.top || ty > pad.top + plotH) return null;
        const isMajor = logY ? isMajorLogTick(t) : true;
        return html`
          <g key=${"yt" + t}>
            <line x1=${pad.left - 4} y1=${ty} x2=${pad.left} y2=${ty}
              stroke="var(--ink-40)" stroke-width="1" />
            <line x1=${pad.left} y1=${ty} x2=${w - pad.right} y2=${ty}
              stroke="var(--ink-10)" stroke-width="0.5" stroke-dasharray="2,3" />
            ${isMajor ? html`
              <text x=${pad.left - 6} y=${ty + 3} text-anchor="end" fill="var(--ink-60)" font-size="9">
                ${logY ? t.toExponential(0) : fmt(t, 3)}
              </text>
            ` : null}
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

// ── Hover Crosshair ─────────────────────────────────────

function nearestIndex(arr, target) {
  let lo = 0, hi = arr.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid] < target) lo = mid + 1; else hi = mid;
  }
  if (lo > 0 && Math.abs(arr[lo - 1] - target) < Math.abs(arr[lo] - target)) lo--;
  return lo;
}

function svgMouseX(e) {
  const svgEl = e.currentTarget?.ownerSVGElement || e.currentTarget;
  if (!svgEl || typeof svgEl.createSVGPoint !== "function") return null;
  const ctm = svgEl.getScreenCTM();
  if (!ctm) return null;
  const pt = svgEl.createSVGPoint();
  pt.x = e.clientX;
  pt.y = e.clientY;
  return pt.matrixTransform(ctm.inverse()).x;
}

function formatHoverNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  const abs = Math.abs(numeric);
  if ((abs > 0 && abs < 1e-3) || abs >= 1e4) return numeric.toExponential(3);
  return fmt(numeric, abs >= 100 ? 2 : 4);
}

function HoverOverlay({ pad, plotW, plotH, w, h, seriesData, scaleX, scaleY, invertX, xLabel }) {
  const [hover, setHover] = useState(null);

  const onMove = useCallback((e) => {
    const mx = svgMouseX(e);
    if (mx == null) { setHover(null); return; }
    if (mx < pad.left || mx > pad.left + plotW) { setHover(null); return; }
    const xValue = typeof invertX === "function" ? invertX(mx) : null;
    setHover({ mx, xValue });
  }, [invertX, pad, plotW]);

  const onLeave = useCallback(() => setHover(null), []);

  if (!hover) return html`
    <rect x=${pad.left} y=${pad.top} width=${plotW} height=${plotH}
      fill="transparent" onMouseMove=${onMove} onMouseLeave=${onLeave} />
  `;

  // Find nearest values for each series
  const items = seriesData.map(s => {
    const xVals = Array.isArray(s.x) ? s.x : [];
    const yVals = Array.isArray(s.y) ? s.y : [];
    if (!xVals.length || !yVals.length || hover.xValue == null) return null;
    const idx = nearestIndex(xVals, hover.xValue);
    return { label: s.label, color: s.color, x: xVals[idx], y: yVals[idx], sx: scaleX(xVals[idx]), sy: scaleY(yVals[idx]) };
  }).filter(it => it && isFinite(it.x) && isFinite(it.y));

  const cx = items.length > 0 ? items[0].sx : hover.mx;
  const hoverXValue = items.length > 0 ? items[0].x : hover.xValue;
  const xLine = `${xLabel || "X"}: ${formatHoverNumber(hoverXValue)}`;
  const tooltipWidth = 132;
  const tooltipX = cx + 8 > w - tooltipWidth - 6 ? cx - tooltipWidth - 8 : cx + 8;
  const tooltipHeight = 16 + items.length * 12;

  return html`
    <g>
      <rect x=${pad.left} y=${pad.top} width=${plotW} height=${plotH}
        fill="transparent" onMouseMove=${onMove} onMouseLeave=${onLeave} />
      <line x1=${cx} y1=${pad.top} x2=${cx} y2=${pad.top + plotH}
        stroke="var(--ink-40)" stroke-width="0.5" stroke-dasharray="3,2" />
      ${items.map((it, i) => html`
        <circle key=${i} cx=${it.sx} cy=${it.sy} r="3" fill=${it.color} stroke="white" stroke-width="1" />
      `)}
      <g transform="translate(${tooltipX}, ${pad.top + 4})">
        <rect x="0" y="0" width=${tooltipWidth} height=${tooltipHeight} rx="3"
          fill="var(--card, #fff)" stroke="var(--ink-10)" stroke-width="0.5" opacity="0.95" />
        <text x="4" y="11" fill="var(--ink-70)" font-size="8" font-weight="600">
          ${xLine}
        </text>
        ${items.map((it, i) => html`
          <text key=${i} x="4" y=${23 + i * 12} fill=${it.color} font-size="8" font-weight="600">
            ${it.label ? it.label.slice(0, 10) + ": " : ""}${formatHoverNumber(it.y)}
          </text>
        `)}
      </g>
    </g>
  `;
}

// ── SVG Export ──────────────────────────────────────────

function downloadSvg(svgEl, filename) {
  if (!svgEl) return;
  const serializer = new XMLSerializer();
  const svgStr = serializer.serializeToString(svgEl);
  const blob = new Blob([svgStr], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename || "chart.svg";
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function ExportButton({ svgRef, title }) {
  return html`
    <button type="button" className="chart-export-btn" title="Download SVG"
      aria-label=${`Download ${title || "chart"} as SVG`}
      onClick=${() => downloadSvg(svgRef.current, (title || "chart").replace(/\s+/g, "_") + ".svg")}
      style=${{ position: "absolute", top: "4px", right: "4px", background: "var(--surface, #fff)", border: "1px solid var(--ink-10)", borderRadius: "3px", padding: "1px 5px", fontSize: "9px", cursor: "pointer", opacity: 0.5, color: "var(--ink-60)" }}>
      SVG
    </button>
  `;
}

// ── Chart Card ───────────────────────────────────────────

const COLORS = [
  "var(--accent, #D35400)", "#2980B9", "#27AE60", "#8E44AD",
  "#E74C3C", "#16A085", "#F39C12", "#2C3E50",
];

const PAD = { top: 20, right: 20, bottom: 36, left: 52 };

function VerticalLines({ lines, scaleX, pad, plotH }) {
  if (!lines || !lines.length) return null;
  return lines.map((vl, i) => {
    const vx = scaleX(vl.x);
    if (vx < pad.left || vx > pad.left + (plotH * 3)) return null;
    return html`
      <g key=${"vl" + i}>
        <line x1=${vx} y1=${pad.top} x2=${vx} y2=${pad.top + plotH}
          stroke=${vl.color || "#E74C3C"} stroke-width="1" stroke-dasharray="4,3" />
        ${vl.label ? html`
          <text x=${vx + 3} y=${pad.top + 10} fill=${vl.color || "#E74C3C"} font-size="8" font-weight="600">${vl.label}</text>
        ` : null}
      </g>
    `;
  });
}

export function ChartCard({ title, subtitle, x, y, color, xLabel, yLabel, logX, logY, xMin, xMax, yMin, yMax, w = 840, h = 240, vLines }) {
  const geo = buildGeometry(x, y, w, h, PAD, { logX, logY, xMin, xMax, yMin, yMax });
  const svgRef = useRef(null);
  if (!geo) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  const seriesData = [{ x, y, label: title, color: color || COLORS[0] }];

  return html`
    <div className="chart-card" style=${{ position: "relative" }}>
      <h4>${title}${subtitle ? html` <small className="muted">${subtitle}</small>` : null}</h4>
      <${ExportButton} svgRef=${svgRef} title=${title} />
      <svg ref=${svgRef} viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet">
        <${Axes} geo=${geo} w=${w} h=${h} xLabel=${xLabel} yLabel=${yLabel} logX=${logX} logY=${logY} />
        <polyline points=${geo.points} fill="none" stroke=${color || COLORS[0]} stroke-width="1.5" />
        <${VerticalLines} lines=${vLines} scaleX=${geo.scaleX} pad=${PAD} plotH=${geo.plotH} />
        <${HoverOverlay} pad=${PAD} plotW=${geo.plotW} plotH=${geo.plotH}
          w=${w} h=${h} seriesData=${seriesData}
          scaleX=${geo.scaleX} scaleY=${geo.scaleY} invertX=${geo.invertX} xLabel=${xLabel} />
      </svg>
    </div>
  `;
}

export function MultiSeriesChart({ title, subtitle, series, xLabel, yLabel, logX, logY, xMin, xMax, yMin, yMax, w = 960, h = 260, vLines }) {
  const svgRef = useRef(null);
  if (!series || !series.length) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  // Compute global bounds
  let gxMin = Infinity, gxMax = -Infinity, gyMin = Infinity, gyMax = -Infinity;
  for (const s of series) {
    if (!s.x || !s.y || s.x.length < 2) continue;
    for (const v of s.x) {
      if (!Number.isFinite(v) || (logX && v <= 0)) continue;
      if (v < gxMin) gxMin = v;
      if (v > gxMax) gxMax = v;
    }
    for (const v of s.y) {
      if (!Number.isFinite(v) || (logY && v <= 0)) continue;
      if (v < gyMin) gyMin = v;
      if (v > gyMax) gyMax = v;
    }
  }
  if (!isFinite(gxMin)) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  const padLegend = { ...PAD, bottom: PAD.bottom + series.length * 14 };
  const totalH = h + series.length * 14;

  const geos = series.map(s => buildGeometry(s.x, s.y, w, totalH, padLegend, {
    logX,
    logY,
    xMin: xMin != null ? xMin : gxMin,
    xMax: xMax != null ? xMax : gxMax,
    yMin: yMin != null ? yMin : gyMin,
    yMax: yMax != null ? yMax : gyMax,
  }));

  const seriesData = series.map((s, i) => ({
    x: s.x, y: s.y, label: s.label || `Series ${i + 1}`,
    color: s.color || COLORS[i % COLORS.length],
  }));

  return html`
    <div className="chart-card" style=${{ position: "relative" }}>
      <h4>${title}${subtitle ? html` <small className="muted">${subtitle}</small>` : null}</h4>
      <${ExportButton} svgRef=${svgRef} title=${title} />
      <svg ref=${svgRef} viewBox="0 0 ${w} ${totalH}" width="100%" preserveAspectRatio="xMidYMid meet">
        <${Axes} geo=${geos[0]} w=${w} h=${totalH} xLabel=${xLabel} yLabel=${yLabel} logX=${logX} logY=${logY} />
        ${geos.map((geo, i) => geo ? html`
          <polyline key=${i} points=${geo.points} fill="none"
            stroke=${series[i].color || COLORS[i % COLORS.length]} stroke-width="1.5" />
        ` : null)}
        <${VerticalLines} lines=${vLines} scaleX=${geos[0]?.scaleX} pad=${padLegend} plotH=${geos[0]?.plotH || 0} />
        <${HoverOverlay} pad=${padLegend} plotW=${geos[0]?.plotW || 0} plotH=${geos[0]?.plotH || 0}
          w=${w} h=${totalH} seriesData=${seriesData}
          scaleX=${geos[0]?.scaleX} scaleY=${geos[0]?.scaleY} invertX=${geos[0]?.invertX} xLabel=${xLabel} />
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
export function SoilProfilePlot({ layers, diagnostics = null, w = 1320, h = 440 }) {
  if (!layers || !layers.length) {
    return html`<div className="chart-card"><h4>Soil Profile</h4><p className="muted">No layers</p></div>`;
  }

  const pad = { top: 22, right: 18, bottom: 44, left: 54 };
  const sourceRows = (diagnostics && diagnostics.length ? diagnostics : layers) || [];
  const stepData = [];
  let depth = 0;

  for (let i = 0; i < sourceRows.length; i++) {
    const row = sourceRows[i] || {};
    const layer = layers[i] || {};
    const t = row.thickness_m || row.thickness || layer.thickness_m || layer.thickness || 0;
    const vs = row.vs_m_s || row.vs || layer.vs_m_s || layer.vs || 0;
    const maxFreq = row.max_frequency_hz ?? (vs > 0 && t > 0 ? vs / (4 * t) : 0);
    const dSmallPct = row.small_strain_damping_ratio != null
      ? row.small_strain_damping_ratio * 100
      : ((layer.material_params?.damping_min || 0) * 100);
    const impliedStrength = row.implied_strength_kpa ?? 0;
    const normalizedStrength = row.normalized_implied_strength ?? 0;
    const impliedPhi = row.implied_friction_angle_deg ?? 0;
    stepData.push({
      d0: depth,
      d1: depth + t,
      name: row.name || layer.name || "",
      vs,
      max_frequency_hz: maxFreq,
      small_strain_damping_pct: dSmallPct,
      implied_strength_kpa: impliedStrength,
      normalized_implied_strength: normalizedStrength,
      implied_friction_angle_deg: impliedPhi,
    });
    depth += t;
  }

  const totalDepth = depth;
  if (totalDepth <= 0) return null;
  const plotH = h - pad.top - pad.bottom;
  const sy = (d) => pad.top + (d / totalDepth) * plotH;

  const columns = [
    { key: "vs", label: "Vs (m/s)" },
    { key: "max_frequency_hz", label: "Max Freq (Hz)" },
    { key: "small_strain_damping_pct", label: "Small-Strain Damping (%)" },
    { key: "implied_strength_kpa", label: "Implied Strength (kPa)" },
    { key: "normalized_implied_strength", label: "Normalized Strength" },
    { key: "implied_friction_angle_deg", label: "Implied Friction Angle (deg)" },
  ];

  const stratW = 170;
  const colGap = 22;
  const usableWidth = w - pad.left - pad.right - stratW - colGap * columns.length;
  const colW = usableWidth / columns.length;

  function StepColumn({ colIdx, dataKey, label }) {
    const vals = stepData.map((s) => Number(s[dataKey]) || 0);
    const maxVal = Math.max(...vals, 0.001);
    const x0 = pad.left + stratW + colGap + colIdx * (colW + colGap);
    const innerLeft = x0 + 10;
    const innerWidth = Math.max(colW - 20, 8);

    return html`
      <g>
        <text x=${x0 + colW / 2} y=${pad.top - 8} text-anchor="middle" fill="var(--ink-60)" font-size="8.5" font-weight="600">${label}</text>
        <rect x=${x0} y=${pad.top} width=${colW} height=${plotH}
          fill="rgba(41,128,185,0.025)" stroke="rgba(41,128,185,0.12)" stroke-width="0.6" rx="8" />
        <line x1=${innerLeft} y1=${pad.top + 2} x2=${innerLeft} y2=${pad.top + plotH - 2} stroke="var(--ink-10)" />
        ${stepData.map((s, i) => {
          const value = Number(s[dataKey]) || 0;
          const barW = (value / maxVal) * innerWidth;
          const x1 = innerLeft + Math.max(barW, 0);
          const textX = Math.min(x0 + colW - 8, x1 + 8);
          return html`
            <g key=${`${dataKey}-${i}`}>
              <rect x=${innerLeft} y=${sy(s.d0)} width=${Math.max(barW, 0)} height=${sy(s.d1) - sy(s.d0)}
                fill="#2980B9" fill-opacity="0.15" stroke="#2980B9" stroke-width="0.5" />
              <line x1=${innerLeft} y1=${sy(s.d0)} x2=${x1} y2=${sy(s.d0)}
                stroke="#2980B9" stroke-width="1.4" />
              <line x1=${innerLeft} y1=${sy(s.d1)} x2=${x1} y2=${sy(s.d1)}
                stroke="#2980B9" stroke-width="1.4" />
              <line x1=${x1} y1=${sy(s.d0)} x2=${x1} y2=${sy(s.d1)}
                stroke="#2980B9" stroke-width="1.4" />
              <text x=${textX} y=${(sy(s.d0) + sy(s.d1)) / 2 + 3}
                fill="var(--ink-60)" font-size="8" text-anchor=${textX >= x0 + colW - 8 ? "end" : "start"}>${fmt(value, 1)}</text>
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
        <text x=${14} y=${pad.top + plotH / 2} text-anchor="middle" fill="var(--ink-70)" font-size="10" font-weight="600"
          transform="rotate(-90, 14, ${pad.top + plotH / 2})">Depth (m)</text>
        ${[0, 0.25, 0.5, 0.75, 1.0].map((frac) => {
          const d = frac * totalDepth;
          const yp = sy(d);
          return html`
            <g key=${`dtick-${frac}`}>
              <line x1=${pad.left - 4} y1=${yp} x2=${pad.left} y2=${yp} stroke="var(--ink-40)" />
              <text x=${pad.left - 6} y=${yp + 3} text-anchor="end" fill="var(--ink-60)" font-size="8">${fmt(d, 1)}</text>
            </g>
          `;
        })}

        <text x=${pad.left + stratW / 2} y=${pad.top - 8} text-anchor="middle" fill="var(--ink-60)" font-size="8.5" font-weight="600">Layers</text>
        ${stepData.map((s, i) => html`
          <g key=${`strat-${i}`}>
            <rect x=${pad.left} y=${sy(s.d0)} width=${stratW - 14} height=${sy(s.d1) - sy(s.d0)}
              fill=${LAYER_COLORS[i % LAYER_COLORS.length]} stroke="white" stroke-width="1" rx="2" />
            <text x=${pad.left + (stratW - 14) / 2} y=${(sy(s.d0) + sy(s.d1)) / 2 + 4}
              text-anchor="middle" fill="white" font-size="9" font-weight="600">
              ${s.name || `Layer ${i + 1}`}
            </text>
          </g>
        `)}

        ${columns.map((col, ci) => html`
          <${StepColumn} key=${col.key} colIdx=${ci} dataKey=${col.key} label=${col.label} />
        `)}
      </svg>
    </div>
  `;
}

export function DepthProfileChart({
  title,
  subtitle,
  depths,
  values,
  xLabel,
  yLabel,
  color,
  w = 300,
  h = 300,
  xMin = null,
  xMax = null,
}) {
  if (!depths || !values || depths.length < 2) return html`<div className="chart-card"><h4>${title}</h4><p className="muted">No data</p></div>`;

  const pad = { top: 24, right: 12, bottom: 32, left: 52 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const dMin = Math.min(...depths);
  const dMax = Math.max(...depths);
  const rawVMin = Math.min(...values);
  const rawVMax = Math.max(...values);
  const autoVMin = rawVMin > 0 ? 0 : rawVMin;
  const autoVMax = rawVMax === autoVMin ? autoVMin + 1 : rawVMax;
  const vMin = Number.isFinite(xMin) ? xMin : autoVMin;
  const vMaxBase = Number.isFinite(xMax) ? xMax : autoVMax;
  const vMax = vMaxBase === vMin ? vMin + 1 : vMaxBase;

  function sx(v) { return pad.left + ((v - vMin) / (vMax - vMin)) * plotW; }
  function sy(d) { return pad.top + ((d - dMin) / (dMax - dMin || 1)) * plotH; }

  const points = depths.map((d, i) => `${sx(values[i])},${sy(d)}`).join(" ");
  const xTicks = linearTicks(vMin, vMax, 4);
  const yTicks = linearTicks(dMin, dMax, 5);

  return html`
    <div className="chart-card">
      <h4>${title}${subtitle ? html` <small className="muted">${subtitle}</small>` : null}</h4>
      <svg viewBox="0 0 ${w} ${h}" width="100%" preserveAspectRatio="xMidYMid meet">
        <!-- Axes -->
        <line x1=${pad.left} y1=${pad.top} x2=${pad.left} y2=${pad.top + plotH} stroke="var(--ink-40)" />
        <line x1=${pad.left} y1=${pad.top + plotH} x2=${w - pad.right} y2=${pad.top + plotH} stroke="var(--ink-40)" />
        <!-- X ticks (top) -->
        ${xTicks.map(t => {
          const tx = sx(t);
          if (tx < pad.left - 1 || tx > w - pad.right + 1) return null;
          return html`
            <g key=${"xt" + t}>
              <line x1=${tx} y1=${pad.top} x2=${tx} y2=${pad.top + plotH} stroke="var(--ink-10)" stroke-width="0.5" stroke-dasharray="2,3" />
              <line x1=${tx} y1=${pad.top - 3} x2=${tx} y2=${pad.top} stroke="var(--ink-40)" />
              <text x=${tx} y=${pad.top - 5} text-anchor="middle" fill="var(--ink-60)" font-size="8">${fmt(t, t < 1 ? 3 : 1)}</text>
            </g>
          `;
        })}
        <!-- Y ticks (depth) -->
        ${yTicks.map(t => {
          const ty = sy(t);
          if (ty < pad.top - 1 || ty > pad.top + plotH + 1) return null;
          return html`
            <g key=${"yt" + t}>
              <line x1=${pad.left} y1=${ty} x2=${w - pad.right} y2=${ty} stroke="var(--ink-10)" stroke-width="0.5" stroke-dasharray="2,3" />
              <line x1=${pad.left - 3} y1=${ty} x2=${pad.left} y2=${ty} stroke="var(--ink-40)" />
              <text x=${pad.left - 5} y=${ty + 3} text-anchor="end" fill="var(--ink-60)" font-size="8">${fmt(t, 1)}</text>
            </g>
          `;
        })}
        <!-- Data line -->
        <polyline points=${points} fill="none" stroke=${color || COLORS[0]} stroke-width="1.5" />
        <!-- Labels -->
        ${xLabel ? html`<text x=${pad.left + plotW / 2} y=${h - 2} text-anchor="middle" fill="var(--ink-70)" font-size="9">${xLabel}</text>` : null}
        ${yLabel ? html`<text x=${12} y=${pad.top + plotH / 2} text-anchor="middle" fill="var(--ink-70)" font-size="9" transform="rotate(-90, 12, ${pad.top + plotH / 2})">${yLabel}</text>` : null}
      </svg>
    </div>
  `;
}
