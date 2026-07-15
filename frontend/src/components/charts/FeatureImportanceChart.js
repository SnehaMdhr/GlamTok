import {
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import { chartColors, ChartTooltip } from "./ChartKit";

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

// Blend two hex colors; t=0 → a, t=1 → b
function blend(a, b, t) {
  const pa = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16));
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * t));
  return `#${c.map(x => x.toString(16).padStart(2, "0")).join("")}`;
}

/**
 * Horizontal feature-importance bars - violet gradient from light (low
 * importance) to deep violet (top feature). ML identity for the predictive page.
 * features: [{ label, importance }] - already ranked (highest first).
 */
export default function FeatureImportanceChart({ features }) {
  const data = [...features].reverse(); // highest on top
  const n = Math.max(data.length - 1, 1);
  const C = chartColors();
  const LIGHT = cssVar("--fi-light", "#F5E1E6");
  const DEEP = cssVar("--purple", "#B33E5D");

  return (
    <>
      <div className="chart-wrap" style={{ height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }}
            barCategoryGap="28%">
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} horizontal={false} />
            <XAxis type="number" domain={[0, (data[0]?.importance || 0.2) * 1.15]}
              tickFormatter={v => `${(v * 100).toFixed(0)}%`}
              tick={{ fill: C.axis, fontSize: C.tickFont }}
              axisLine={{ stroke: C.axisLine }} tickLine={false} />
            <YAxis type="category" dataKey="label" width={170}
              tick={{ fill: C.muted, fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip fmt={(v, p) => `${(v * 100).toFixed(1)}%`} />}
              cursor={{ fill: "rgba(92,75,67,0.04)" }} />
            <Bar dataKey="importance" radius={[0, 6, 6, 0]} barSize={18} isAnimationActive={true}>
              {data.map((f, i) => {
                const isTop = i === data.length - 1; // data reversed → top = last
                const t = i / n; // 0 (bottom) → 1 (top)
                return (
                  <Cell key={i}
                    fill={blend(LIGHT, DEEP, t)}
                    fillOpacity={isTop ? 1 : 0.9}
                    stroke={isTop ? "rgba(179,62,93,0.5)" : "none"}
                    style={isTop ? { filter: "drop-shadow(0 0 5px rgba(179,62,93,0.35))" } : undefined} />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-note">
        <i className="ti ti-gradient" aria-hidden="true" />
        Deeper purple = stronger contribution to the model
      </div>
    </>
  );
}
