import { AD } from "../../data/analytics";
import Section from "../../components/ui/Section";
import StatCard from "../../components/ui/StatCard";
import BusinessBars from "../../components/charts/BusinessBars";
import MonthlyVolumeChart from "../../components/charts/MonthlyVolumeChart";
import HourlyEngagementChart from "../../components/charts/HourlyEngagementChart";
import { ENG_MAX } from "../../theme";

const pct1 = v => `${((v / ENG_MAX) * 100).toFixed(1)}%`;

export default function DescriptiveTab() {
  const D = AD;

  const weekDelta = ((D.weekend.weekend - D.weekend.weekday) / D.weekend.weekday) * 100;          // +5.1
  const festDelta = ((D.festival.festival - D.festival.regular) / D.festival.regular) * 100;      // −2.6

  const peakMonthIdx = D.monthly.values.indexOf(Math.max(...D.monthly.values));                   // Jun 26
  const peakHour = D.hourly_likes.indexOf(Math.max(...D.hourly_likes));                           // hour 0

  const bizItems = D.biz.labels.map((name, i) => ({ name, score: D.biz.scores[i] }));

  return (
    <>
      <div className="kpi-row">
        <StatCard label="Total posts" icon="database" value={D.meta.real_posts.toLocaleString()} sub={`all ${D.meta.businesses} businesses`} accent="primary" />
        <StatCard label="Businesses" icon="building-store" value={String(D.meta.businesses)} sub="Kathmandu fashion" accent="secondary" />
        <StatCard label="Data range" icon="calendar-time" value={`${D.meta.date_min.slice(0, 7)} – ${D.meta.date_max.slice(0, 7)}`} sub="full dataset period" accent="neutral" />
        <StatCard label="Content type" icon="video" value="Video" sub="100% of posts" accent="neutral" />
      </div>

      <Section icon="chart-histogram" title="Monthly posting volume"
        subtitle="posts per month across all businesses - the dataset is growing fast">
        <div className="chart-note">
          <i className="ti ti-arrow-up-right" aria-hidden="true" />
          {D.monthly.labels[peakMonthIdx]} · {D.monthly.values[peakMonthIdx].toLocaleString()} posts - peak month
        </div>
        <MonthlyVolumeChart labels={D.monthly.labels} values={D.monthly.values} peakIndex={peakMonthIdx} />
      </Section>

      <div className="card-grid card-grid-rows">
        <Section icon="clock" title="Engagement by hour"
          subtitle="average likes across the day (NPT) - midnight scroll culture">
          <HourlyEngagementChart values={D.hourly_likes} highlight={[0, 3]} height={240} />
          <div className="chart-note">
            <i className="ti ti-moon" aria-hidden="true" />
            00:00–03:00 NPT peak - {Math.round(D.hourly_likes[peakHour]).toLocaleString()} avg likes at {String(peakHour).padStart(2, "0")}h
          </div>
        </Section>

        <Section icon="building-store" title="Business engagement scores"
          subtitle="ranked, relative to the top account">
          <BusinessBars items={bizItems} nameWidth={104} valueFmt={v => pct1(v)} />
        </Section>

        <Section icon="calendar-week" title="Weekday vs weekend"
          subtitle="does the calendar day change engagement?">
          <div className="compare-grid">
            <div className="compare-card">
              <div className="compare-label">Weekday</div>
              <div className="compare-value">{pct1(D.weekend.weekday)}</div>
            </div>
            <div className="compare-card">
              <div className="compare-label" style={{ color: "var(--success-strong)" }}>Weekend</div>
              <div className="compare-value" style={{ color: "var(--success)" }}>{pct1(D.weekend.weekend)}</div>
            </div>
          </div>
          <div className="diff-line diff-pos">
            <i className="ti ti-arrow-up-right" aria-hidden="true" />
            +{weekDelta.toFixed(1)}% engagement on weekends
          </div>
        </Section>

        <Section icon="calendar-event" title="Festival months"
          subtitle="Mar, Oct & Nov - Dashain, Tihar, Holi">
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
          <div className="diff-line diff-warn">
            <i className="ti ti-arrow-down-right" aria-hidden="true" />
            {festDelta.toFixed(1)}% during festival months - volume rises, per-post quality doesn't
          </div>
        </Section>
      </div>
    </>
  );
}
