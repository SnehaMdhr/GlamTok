import { useEffect, useState } from "react";
import { API } from "../api";
import { DAYS, DAYS_FULL, ENG_MAX } from "../theme";
import { AD } from "../data/analytics";
import Section from "../components/ui/Section";
import StatCard from "../components/ui/StatCard";
import Heatmap from "../components/predict/Heatmap";
import CellDetail from "../components/predict/CellDetail";
import RecommendationCard from "../components/predict/RecommendationCard";
import BusinessComparison from "../components/predict/BusinessComparison";

// Rank-normalize the raw heatmap matrix (0..1 for color) while keeping the
// real score for tooltips and KPI derivation.
function normalizeMatrix(matrix) {
  const flat = matrix.flat();
  const sorted = [...flat].sort((a, b) => a - b);
  const n = sorted.length;
  return matrix.map(row => row.map(v => {
    const rank = sorted.findIndex(s => s >= v);
    return { norm: rank / (n - 1), raw: v };
  }));
}

function bestCell(norm) {
  let best = null;
  norm.forEach((row, d) => row.forEach((cell, h) => {
    if (!best || cell.raw > best.raw) best = { d, h, raw: cell.raw, norm: cell.norm };
  }));
  return best;
}

export default function PredictPage({ selectedCell, onCellClick }) {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true); setError(null);
    fetch(`${API}/heatmap?platform=tiktok`)
      .then(r => r.json())
      .then(d => {
        if (!d.matrix) throw new Error("No heatmap data");
        setMatrix(normalizeMatrix(d.matrix));
        setLoading(false);
      })
      .catch(() => { setError("Could not reach the Express API on port 5000."); setLoading(false); });
  }, []);

  const best = matrix ? bestCell(matrix) : null;

  return (
    <>
      <div className="kpi-row">
        <StatCard label="Relative engagement" icon="chart-line"
          value={best ? `${((best.raw / ENG_MAX) * 100).toFixed(1)}%` : "-"}
          sub={best ? "at the best posting window · % of reference max (0.086)" : "loading heatmap…"} accent="primary" highlight />
        <StatCard label="Best posting window" icon="clock"
          value={best ? `${DAYS[best.d]} · ${String(best.h).padStart(2, "0")}:00 NPT` : "-"}
          sub="predicted across day × hour" accent="primary" />
        <StatCard label="Best day" icon="calendar-week"
          value={best ? DAYS_FULL[best.d] : "-"}
          sub="highest average engagement" accent="secondary" />
        <StatCard label="Dataset" icon="database"
          value={AD.meta.real_posts.toLocaleString()} sub={`posts · ${AD.meta.businesses} businesses · TikTok`} accent="neutral" />
      </div>
      <div style={{ padding: "0 0 12px", color: "var(--text-muted)", fontSize: 12 }}>
        Percentages on this page are relative to the reference maximum engagement (0.086) — they are not an accuracy or confidence score.
      </div>

      <Section icon="chart-grid-dots" title="Engagement heatmap"
        subtitle="predicted engagement by day and hour - hover for details, click any cell to inspect">
        {loading
          ? <div style={{ padding: "16px 0", color: "var(--text-muted)", fontSize: 13 }}>Loading heatmap…</div>
          : error
            ? <div style={{ padding: "12px 0", color: "var(--danger)", fontSize: 13 }}>{error}</div>
            : <Heatmap matrix={matrix} onCellClick={onCellClick} selectedCell={selectedCell} />}
        <CellDetail cell={selectedCell} />
      </Section>

      <Section icon="clock" title="Best time to post"
        subtitle="top 3 windows for your follower count and target month">
        <RecommendationCard />
      </Section>

      <Section icon="building-store" title="Business comparison"
        subtitle="engagement score per TikTok account, in relative terms">
        <BusinessComparison />
      </Section>
    </>
  );
}
