import {
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import { chartColors, ChartTooltip } from "./ChartKit";
import { ENG_MAX } from "../../theme";

/**
 * Compact bar chart for content levers (hashtags / captions / duration).
 * data: [{ label, value }] - value is a raw engagement score; highlighted index
 * gets the cyan treatment. Values are shown with the dashboard's standard
 * engagement-percentage convention (score / ENG_MAX).
 */
export default function LeverBars({ data, highlightIndex, height = 170 }) {
  const C = chartColors();
  const rows = data.map((d, i) => ({
    label: d.label,
    value: Number(((d.value / ENG_MAX) * 100).toFixed(1)),
    isBest: i === highlightIndex,
  }));
  const max = Math.max(...rows.map(r => r.value), 1);

  return (
    <div className="chart-wrap" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
          <XAxis dataKey="label" tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={{ stroke: C.axisLine }} tickLine={false} dy={4} />
          <YAxis hide domain={[0, Math.ceil(max / 10) * 10]} />
          <Tooltip content={<ChartTooltip fmt={(v, p) => `${p.payload.isBest ? "★ " : ""}${v.toFixed(1)}%`} />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="value" radius={[5, 5, 0, 0]} barSize={30}>
            {rows.map((r, i) => (
              <Cell key={i}
                fill={r.isBest ? C.primary : C.axisLine}
                fillOpacity={r.isBest ? 1 : 0.9}
                stroke={r.isBest ? "rgba(255,126,165,0.6)" : "none"}
                style={r.isBest ? { filter: "drop-shadow(0 0 4px rgba(255,126,165,0.4))" } : undefined} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
