import { useEffect, useState } from "react";
import { API } from "../api";
import { AD } from "../data/analytics";
import Section from "../components/ui/Section";
import StatCard from "../components/ui/StatCard";
import MonthlyVolumeChart from "../components/charts/MonthlyVolumeChart";
import BusinessBars from "../components/charts/BusinessBars";

export default function PostsPage() {
  const [biz, setBiz] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/businesses?platform=tiktok`)
      .then(r => r.json())
      .then(d => {
        const list = (d.businesses || []).slice().sort((a, b) => b.post_count - a.post_count);
        setBiz(list);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const peakMonthIdx = AD.monthly.values.indexOf(Math.max(...AD.monthly.values));
  const peakLabel = AD.monthly.labels[peakMonthIdx];
  const peakPosts = AD.monthly.values[peakMonthIdx];
  const totalPosts = AD.monthly.values.reduce((s, v) => s + v, 0);

  return (
    <>
      <div className="kpi-row">
        <StatCard label="Total posts" icon="database" value={totalPosts.toLocaleString()} sub="TikTok · Video only" accent="primary" />
        <StatCard label="Date range" icon="calendar-time" value={`${AD.meta.date_min.slice(0, 7)} – ${AD.meta.date_max.slice(0, 7)}`} sub="full dataset period" accent="secondary" />
        <StatCard label="Peak month" icon="chart-histogram" value={peakLabel} sub={`${peakPosts.toLocaleString()} posts in one month`} accent="primary" />
        <StatCard label="Posting accounts" icon="building-store" value={String(biz.length || AD.meta.businesses)} sub="Kathmandu fashion" accent="neutral" />
      </div>

      <Section icon="chart-histogram" title="Posting volume timeline"
        subtitle="monthly post counts across the full dataset">
        <div className="chart-note">
          <i className="ti ti-arrow-up-right" aria-hidden="true" />
          {peakLabel} · {peakPosts.toLocaleString()} posts - peak month
        </div>
        <MonthlyVolumeChart labels={AD.monthly.labels} values={AD.monthly.values} peakIndex={peakMonthIdx} />
      </Section>

      <Section icon="building-store" title="Posts per business"
        subtitle="posting volume ranked by account">
        {loading ? (
          <div style={{ padding: "14px 0", color: "var(--text-muted)", fontSize: 13 }}>Loading accounts…</div>
        ) : (
          <BusinessBars
            items={biz.map(b => ({ name: b.business, score: b.post_count }))}
            nameWidth={110}
            valueFmt={v => v.toLocaleString()}
          />
        )}
      </Section>
    </>
  );
}
