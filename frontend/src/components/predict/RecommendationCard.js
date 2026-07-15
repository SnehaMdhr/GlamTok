import { useState, useEffect } from "react";
import { API } from "../../api";
import { ENG_MAX, FOLLOWER_OPTIONS, MONTHS } from "../../theme";
import Dropdown from "../ui/Dropdown";
import Callout from "../ui/Callout";

const FESTIVAL_MONTHS = [3, 10, 11];
const FULL_DAY = { Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday", Fri: "Friday", Sat: "Saturday", Sun: "Sunday" };

export default function RecommendationCard() {
  const [followers, setFollowers] = useState(5000);
  const [month, setMonth]         = useState(new Date().getMonth() + 1);
  const [recs, setRecs]           = useState([]);
  const [loading, setLoading]     = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/recommendations?platform=tiktok&followers=${followers}&content=Video&month=${month}&top_n=3`)
      .then(r => r.json())
      .then(d => { setRecs(d.recommendations || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [followers, month]);

  const isFest = FESTIVAL_MONTHS.includes(month);
  const waitH  = recs[0] ? ((recs[0].hour - new Date().getHours() + 24) % 24) : null;

  const followerOpts = FOLLOWER_OPTIONS.map(v => ({
    value: v, label: v >= 1000 ? `${v / 1000}k followers` : `${v} followers`,
    icon: v >= 50000 ? "crown" : v >= 5000 ? "users" : "user",
  }));
  const monthOpts = MONTHS.map((m, i) => ({
    value: i + 1, label: m + (FESTIVAL_MONTHS.includes(i + 1) ? " - festival" : ""),
    icon: FESTIVAL_MONTHS.includes(i + 1) ? "sparkles" : "calendar",
  }));

  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 12, marginBottom: 16, position: "relative", maxWidth: 460 }}>
        <Dropdown label="followers" icon="users" value={followers}
          display={followers >= 1000 ? `${followers / 1000}k` : String(followers)}
          options={followerOpts} onChange={setFollowers} />
        <Dropdown label="month" icon="calendar" value={month}
          display={MONTHS[month - 1]} options={monthOpts} onChange={setMonth} />
      </div>

      {isFest && (
        <div style={{ marginBottom: 16 }}>
          <Callout icon="sparkles" tone="warning">
            Festival month - evening slots may be boosted (Dashain / Tihar / Holi).
          </Callout>
        </div>
      )}

      {loading ? (
        <div style={{ padding: "14px 0", color: "var(--text-muted)", fontSize: 13 }}>Loading recommendations…</div>
      ) : recs.length > 0 ? (
        <>
          <div className="hero-card">
            <div className="hero-eyebrow">Next best window</div>
            <div className="hero-title">
              {FULL_DAY[recs[0].day] || recs[0].day} · {recs[0].time_label || `${String(recs[0].hour).padStart(2, "0")}:00 NPT`}
            </div>
            <div className="hero-meta">
              <div>
                <div className="hm-label">Relative engagement</div>
                <div className="hm-value accent">{(recs[0].predicted_score / ENG_MAX * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div className="hm-label">Countdown</div>
                <div className="hm-value">
                  {waitH === 0 ? "Post now!" : waitH === 1 ? "In 1 hour" : `In ${waitH} hours`}
                </div>
              </div>
              <div>
                <div className="hm-label">Model</div>
                <div className="hm-value">XGBoost</div>
              </div>
            </div>
          </div>

          <div className="rec-row">
            {recs.map((r, i) => (
              <div key={i} className={i === 0 ? "rec-card rank1" : "rec-card"}>
                <div className="rec-top">
                  <span className="pill" style={{ color: i === 0 ? "var(--accent-strong)" : "var(--text-faint)", borderColor: i === 0 ? "rgba(255,126,165,0.4)" : undefined }}>
                    #{r.rank}
                  </span>
                  <span className="rec-score">
                    <strong>{(r.predicted_score / ENG_MAX * 100).toFixed(1)}%</strong>
                  </span>
                </div>
                <div className="rec-window">
                  {r.day} {String(r.hour).padStart(2, "0")}:00
                </div>
                <div className="rec-label">{r.label || `${r.day} ${r.time_label || ""}`}</div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div style={{ padding: "14px 0", fontSize: 13, color: "var(--text-muted)" }}>Could not load recommendations.</div>
      )}
    </>
  );
}
