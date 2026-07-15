// Shared chart helpers (recharts).
// Colors are read from the CSS design tokens at render time so charts
// follow the active light/dark theme automatically.

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export const CHART = {
  primary: cssVar("--accent", "#FF7EA5"),        // rose accent
  secondary: cssVar("--accent-strong", "#B33E5D"), // deep rose
  green:   cssVar("--success", "#3AA876"),
  amber:   cssVar("--warning", "#D98A2B"),
  reference: cssVar("--chart-muted", "#A18E84"),
  muted:   cssVar("--chart-muted", "#A18E84"),
  grid:    cssVar("--chart-grid", "rgba(92, 75, 67, 0.08)"),
  axis:    cssVar("--chart-axis", "#B3A096"),
  axisLine: cssVar("--chart-axisline", "#EBE0DA"),
  surface: cssVar("--chart-surface", "#FFFFFF"),
  tickFont: 11,
};

// Re-read the tokens (call inside render so a theme flip is picked up).
export function chartColors() {
  return {
    primary: cssVar("--accent", "#FF7EA5"),
    secondary: cssVar("--accent-strong", "#B33E5D"),
    green:   cssVar("--success", "#3AA876"),
    amber:   cssVar("--warning", "#D98A2B"),
    reference: cssVar("--chart-muted", "#A18E84"),
    muted:   cssVar("--chart-muted", "#A18E84"),
    grid:    cssVar("--chart-grid", "rgba(92, 75, 67, 0.08)"),
    axis:    cssVar("--chart-axis", "#B3A096"),
    axisLine: cssVar("--chart-axisline", "#EBE0DA"),
    surface: cssVar("--chart-surface", "#FFFFFF"),
    tickFont: 11,
  };
}

// Shared tooltip content for recharts <Tooltip content={<ChartTooltip />} />
export function ChartTooltip({ active, payload, label, fmt }) {
  if (!active || !payload || !payload.length) return null;
  const rows = payload.filter(p => p.value !== undefined && p.value !== null);
  if (!rows.length) return null;
  const C = chartColors();
  return (
    <div className="chart-tooltip">
      {label !== undefined && label !== null && label !== "" && (
        <div className="ct-label">{label}</div>
      )}
      {rows.map((p, i) => (
        <div key={i} className="ct-row">
          <span className="ct-dot" style={{ background: p.color || p.payload?.fill || C.primary }} />
          <span className="ct-name">{p.name || p.dataKey}</span>
          <span className="ct-value">{fmt ? fmt(p.value, p) : p.value}</span>
        </div>
      ))}
    </div>
  );
}

export const fmtK = v => v >= 1000 ? `${(v / 1000).toFixed(1).replace(/\.0$/, "")}k` : String(v);
