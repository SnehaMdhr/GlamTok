import { AD } from "../../data/analytics";
import { ENG_MAX } from "../../theme";
import Section from "../../components/ui/Section";
import Callout from "../../components/ui/Callout";
import EngagementScatter from "../../components/charts/EngagementScatter";

const pct1 = v => `${((v / ENG_MAX) * 100).toFixed(1)}%`;
const pct0 = v => `${((v / ENG_MAX) * 100).toFixed(0)}%`;

export default function DiagnosticTab() {
  const D = AD;
  const cap = D.diagnostic.cap_hashtag;

  const festDelta = ((D.festival.festival - D.festival.regular) / D.festival.regular) * 100;

  // best caption bucket (by engagement)
  const bestCapIdx = cap.eng.indexOf(Math.max(...cap.eng));

  return (
    <>
      <Section icon="search" title="Why does engagement vary between businesses?"
        subtitle="followers vs engagement - the 'why' behind the patterns">
        <EngagementScatter points={D.diagnostic.biz_bubble} />

        <div className="kpi-row" style={{ marginTop: 18, marginBottom: 0, gridTemplateColumns: "repeat(3, 1fr)" }}>
          <div className="stat-card accent-primary" style={{ padding: "16px 18px" }}>
            <div className="stat-label">Correlation</div>
            <div className="stat-value" style={{ fontSize: 26 }}>{D.diagnostic.follower_corr}</div>
            <div className="stat-sub">followers vs engagement score</div>
          </div>
          <div className="stat-card accent-primary" style={{ padding: "16px 18px" }}>
            <div className="stat-label">Highest engagement</div>
            <div className="stat-value" style={{ fontSize: 26 }}>{pct0(Math.max(...D.diagnostic.biz_bubble.map(b => b.eng)))}</div>
            <div className="stat-sub">largest account in sample</div>
          </div>
          <div className="stat-card accent-neutral" style={{ padding: "16px 18px" }}>
            <div className="stat-label">Posting volume corr</div>
            <div className="stat-value" style={{ fontSize: 26 }}>{D.diagnostic.volume_corr}</div>
            <div className="stat-sub">posting more ≠ higher engagement</div>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <Callout icon="bulb" tone="warning">
            <b>Account size is the dominant predictor.</b> The RQ1 finding shows followers (55.2% of model
            importance) matter far more than posting time - engagement differences between businesses mostly
            reflect audience size, not posting strategy.
          </Callout>
        </div>
      </Section>

      <div className="card-grid">
        <Section icon="message-2" title="Captions or hashtags?"
          subtitle="what's really driving the 'caption effect'">
          <div className="compare-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
            {cap.labels.map((l, i) => {
              const isBest = i === bestCapIdx;
              return (
                <div key={l} className={isBest ? "compare-card lever-opt-highlight" : "compare-card"}
                  style={{ padding: "12px 12px" }}>
                  <div className="compare-label">{l}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
                    avg tags: <b style={{ color: "var(--text)", fontFamily: "monospace" }}>{cap.hashtags[i]}</b>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                    score: <b style={{ color: isBest ? "var(--accent-strong)" : "var(--text)", fontFamily: "monospace" }}>{pct0(cap.eng[i])}</b>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="chart-note">
            <i className="ti ti-hash" aria-hidden="true" />
            Medium captions (50-150 chars) average {cap.hashtags[bestCapIdx]} hashtags vs {cap.hashtags[0]} for short ones
          </div>
        </Section>

        <Section icon="calendar-event" title="Festival season effect"
          subtitle="per-post engagement, regular vs festival months">
          <div className="compare-grid">
            <div className="compare-card">
              <div className="compare-label">Regular months</div>
              <div className="compare-value">{pct1(D.festival.regular)}</div>
            </div>
            <div className="compare-card">
              <div className="compare-label" style={{ color: "var(--warning-strong)" }}>Festival months</div>
              <div className="compare-value" style={{ color: "var(--warning)" }}>{pct1(D.festival.festival)}</div>
            </div>
          </div>
          <div className="diff-line diff-warn" style={{ marginTop: 0 }}>
            <i className="ti ti-arrow-down-right" aria-hidden="true" />
            Difference: {festDelta.toFixed(1)}%
          </div>
          <div style={{ marginTop: 14 }}>
            <Callout icon="alert-triangle" tone="danger">
              Businesses post <b>more</b> during festivals, but per-post engagement drops - volume increases, quality doesn't scale with it.
            </Callout>
          </div>
        </Section>
      </div>
    </>
  );
}
