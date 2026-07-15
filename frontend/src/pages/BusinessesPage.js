import { useEffect, useState } from "react";
import { API } from "../api";
import { ENG_MAX } from "../theme";
import Section from "../components/ui/Section";
import StatCard from "../components/ui/StatCard";

const fmt = v => v.toLocaleString();
const pct0 = v => `${((v / ENG_MAX) * 100).toFixed(0)}%`;

export default function BusinessesPage() {
  const [biz, setBiz] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/businesses?platform=tiktok`)
      .then(r => r.json())
      .then(d => {
        if (!d.businesses) throw new Error("no data");
        setBiz(d.businesses.slice().sort((a, b) => (b.avg_engagement_score || 0) - (a.avg_engagement_score || 0)));
        setLoading(false);
      })
      .catch(() => { setError("Could not load business data."); setLoading(false); });
  }, []);

  if (loading) return <div style={{ padding: "24px 0", color: "var(--text-muted)", fontSize: 13 }}>Loading businesses…</div>;
  if (error) return <div style={{ padding: "24px 0", color: "var(--danger)", fontSize: 13 }}>{error}</div>;

  const maxScore = Math.max(...biz.map(b => b.avg_engagement_score || 0), 0.001);

  // modal peak posting hour across accounts (most businesses post in the same window)
  const hourCounts = {};
  biz.forEach(b => { const h = b.peak_hour_label || "-"; hourCounts[h] = (hourCounts[h] || 0) + 1; });
  const peakHour = Object.entries(hourCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "-";
  const peakHourCount = Object.entries(hourCounts).sort((a, b) => b[1] - a[1])[0]?.[1] || 0;

  return (
    <>
      <div className="kpi-row">
        <StatCard label="Accounts" icon="building-store" value={String(biz.length)} sub="TikTok fashion brands" accent="primary" />
        <StatCard label="Top account" icon="trophy" value={biz[0]?.business || "-"} sub={`${pct0(biz[0]?.avg_engagement_score)} engagement score`} accent="primary" />
        <StatCard label="Avg engagement" icon="chart-line" value={pct0(biz.reduce((s, b) => s + (b.avg_engagement_score || 0), 0) / (biz.length || 1))} sub="across all accounts" accent="secondary" />
        <StatCard label="Peak hour" icon="clock" value={peakHour} sub={`most common posting hour · ${peakHourCount} of ${biz.length} accounts`} accent="neutral" />
      </div>

      <Section icon="building-store" title="Business ranking"
        subtitle="engagement score, followers, posting volume and peak hour - live from the API">
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" style={{ minWidth: 720 }}>
            <thead>
              <tr>
                <th>#</th>
                <th>Business</th>
                <th style={{ width: "34%" }}>Engagement score</th>
                <th>Followers</th>
                <th>Posts</th>
                <th>Avg likes</th>
                <th>Peak hour</th>
              </tr>
            </thead>
            <tbody>
              {biz.map((b, i) => {
                const pctW = Math.max(2, ((b.avg_engagement_score || 0) / maxScore) * 100);
                const fill = i === 0
                  ? "linear-gradient(90deg, rgba(255,126,165,0.35), var(--accent))"
                  : i === 1
                    ? "linear-gradient(90deg, rgba(179,62,93,0.5), var(--accent-strong))"
                    : "linear-gradient(90deg, var(--bar-muted-a), var(--bar-muted-b))";
                return (
                  <tr key={b.business}>
                    <td className="num muted">{i + 1}</td>
                    <td style={{ fontWeight: 600, color: i === 0 ? "var(--accent-strong)" : "var(--text)" }}>{b.business}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div className="bar-track" style={{ height: 12, flex: 1 }}>
                          <div className="bar-fill" style={{ width: `${pctW}%`, background: fill }} />
                        </div>
                        <span className="num" style={{ width: 44, textAlign: "right" }}>{pct0(b.avg_engagement_score)}</span>
                      </div>
                    </td>
                    <td className="num">{fmt(b.followers)}</td>
                    <td className="num">{fmt(b.post_count)}</td>
                    <td className="num muted">{fmt(Math.round(b.avg_likes || 0))}</td>
                    <td className="num muted">{b.peak_hour_label || "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>
    </>
  );
}
