import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceDot,
} from "recharts";
import { chartColors, ChartTooltip, fmtK } from "./ChartKit";

/**
 * Monthly posting volume area chart (cyan gradient).
 * peakIndex - the highlighted month (e.g. Jun 2026 · 792 posts).
 */
export default function MonthlyVolumeChart({ labels, values, peakIndex, height = 260 }) {
  const C = chartColors();
  const data = labels.map((label, i) => ({ label, posts: values[i] }));
  const peak = data[peakIndex ?? Math.max(0, data.length - 1)];

  return (
    <div className="chart-wrap" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
          <defs>
            <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={C.primary} stopOpacity={0.28} />
              <stop offset="100%" stopColor={C.primary} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
          <XAxis dataKey="label" interval={5}
            tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={{ stroke: C.axisLine }} tickLine={false} dy={4} />
          <YAxis tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={false} tickLine={false} width={40} tickFormatter={fmtK} />
          <Tooltip content={<ChartTooltip fmt={v => `${v.toLocaleString()} posts`} />}
            cursor={{ stroke: C.primary, strokeOpacity: 0.25, strokeDasharray: "4 4" }} />
          <Area type="monotone" dataKey="posts" stroke={C.primary} strokeWidth={2.5}
            fill="url(#volGrad)" dot={false} activeDot={{ r: 4.5, fill: C.primary, stroke: C.surface, strokeWidth: 2 }} />
          {peak && (
            <ReferenceDot x={peak.label} y={peak.posts} r={5} fill={C.primary}
              stroke={C.surface} strokeWidth={2} />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
