import {
  ResponsiveContainer, ComposedChart, Scatter, XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { chartColors } from "./ChartKit";
import { ENG_MAX } from "../../theme";

/**
 * Scatter - followers (x) vs engagement rate (y, %), bubble size = posts.
 * Draws a least-squares regression line and a custom dark tooltip.
 * points: [{ name, followers, eng, posts }]
 */
export default function EngagementScatter({ points }) {
  const C = chartColors();
  // engagement on a % scale for readable axes
  const data = points.map(p => ({
    name: p.name,
    followers: p.followers,
    eng: (p.eng / ENG_MAX) * 100,
    posts: p.posts,
  }));

  // least-squares regression over followers -> eng%
  const n = data.length;
  const mx = data.reduce((s, p) => s + p.followers, 0) / n;
  const my = data.reduce((s, p) => s + p.eng, 0) / n;
  let num = 0, den = 0;
  data.forEach(p => {
    num += (p.followers - mx) * (p.eng - my);
    den += (p.followers - mx) ** 2;
  });
  const slope = den > 0 ? num / den : 0;
  const intercept = my - slope * mx;

  const xMax = Math.max(...data.map(p => p.followers), 1);
  const yMax = Math.max(...data.map(p => p.eng), 1);

  function ScatterTip({ active, payload }) {
    if (!active || !payload || !payload.length) return null;
    const p = payload[0]?.payload;
    if (!p || p.name === undefined) return null; // ignore regression line points
    return (
      <div className="chart-tooltip">
        <div className="ct-label" style={{ color: C.secondary }}>{p.name}</div>
        <div className="ct-row">
          <span className="ct-dot" style={{ background: C.reference }} />
          <span className="ct-name">Followers</span>
          <span className="ct-value">{p.followers.toLocaleString()}</span>
        </div>
        <div className="ct-row">
          <span className="ct-dot" style={{ background: C.primary }} />
          <span className="ct-name">Engagement rate</span>
          <span className="ct-value">{p.eng.toFixed(1)}%</span>
        </div>
        <div className="ct-row">
          <span className="ct-dot" style={{ background: C.reference }} />
          <span className="ct-name">Posts</span>
          <span className="ct-value">{p.posts.toLocaleString()}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-wrap" style={{ height: "auto" }}>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart margin={{ top: 10, right: 14, bottom: 0, left: -6 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={C.grid} vertical={false} />
          <XAxis type="number" dataKey="followers" name="Followers"
            domain={[0, Math.ceil(xMax / 25000) * 25000]}
            tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
            tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={{ stroke: C.axisLine }} tickLine={false} dy={4} />
          <YAxis type="number" dataKey="eng" name="Engagement rate" unit="%"
            domain={[0, Math.ceil(yMax / 10) * 10]}
            tick={{ fill: C.axis, fontSize: C.tickFont }}
            axisLine={false} tickLine={false} width={42} />
          <ZAxis type="number" dataKey="posts" range={[40, 220]} />
          <Tooltip content={<ScatterTip />} cursor={{ stroke: C.primary, strokeOpacity: 0.3 }} />
          <ReferenceLine segment={[
            { x: 0, y: intercept },
            { x: xMax, y: intercept + slope * xMax },
          ]} stroke={C.primary} strokeDasharray="5 4" strokeOpacity={0.55} />
          <Scatter name="Business" data={data} fill={C.primary} fillOpacity={0.8}
            stroke={C.primary} strokeWidth={1} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="scatter-legend">
        <span><span className="sl-dot" style={{ background: C.primary }} />Business · size = posts</span>
        <span><span className="sl-dot" style={{ background: C.primary }} />Rose regression trend</span>
      </div>
    </div>
  );
}
