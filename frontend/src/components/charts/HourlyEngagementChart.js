import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceArea,
} from "recharts";
import { chartColors, ChartTooltip, fmtK } from "./ChartKit";

/**
 * 24-hour engagement area chart.
 * highlight - [startHour, endHour] range to tint with cyan (e.g. [0, 3]).
 */
export default function HourlyEngagementChart({ values, highlight = [0, 3], height = 260 }) {
  const C = chartColors();
  const data = values.map((v, h) => ({ hour: h, likes: v }));

  return (
    <div className="chart-wrap" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
          <defs>
            <linearGradient id="hourGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={C.primary} stopOpacity={0.26} />
              <stop offset="100%" stopColor={C.primary} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
          <XAxis dataKey="hour" type="number" domain={[0, 23]} ticks={[0, 3, 6, 9, 12, 15, 18, 21]}
            tickFormatter={h => `${String(h).padStart(2, "0")}h`}
            tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={{ stroke: C.axisLine }} tickLine={false} dy={4} />
          <YAxis tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={false} tickLine={false} width={44} tickFormatter={fmtK} />
          <Tooltip content={<ChartTooltip fmt={v => `${Math.round(v).toLocaleString()} likes`} />}
            cursor={{ stroke: C.primary, strokeOpacity: 0.25, strokeDasharray: "4 4" }} />
          <ReferenceArea x1={highlight[0]} x2={highlight[1]} fill={C.primary} fillOpacity={0.05}
            stroke={C.primary} strokeOpacity={0.25} strokeDasharray="3 3" />
          <Area type="monotone" dataKey="likes" stroke={C.primary} strokeWidth={2.5}
            fill="url(#hourGrad)" dot={false} activeDot={{ r: 4.5, fill: C.primary, stroke: C.surface, strokeWidth: 2 }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
