import { AD } from "../../data/analytics";
import Section from "../../components/ui/Section";
import LeverBars from "../../components/charts/LeverBars";

const LEVERS = [
  {
    key: "hashtags",
    icon: "hash",
    title: "Hashtag count",
    data: AD.hashtags.labels.map((label, i) => ({ label, value: AD.hashtags.scores[i] })),
    highlight: 1,           // 4–7 hashtags
    best: "4–7 hashtags",
    sub: "best engagement",
  },
  {
    key: "caption",
    icon: "message-2",
    title: "Caption length",
    data: AD.caption.labels.map((label, i) => ({ label, value: AD.caption.scores[i] })),
    highlight: 1,           // 50–150 chars
    best: "50–150 characters",
    sub: "medium captions win",
  },
  {
    key: "duration",
    icon: "clock",
    title: "Video duration",
    data: AD.duration.labels.map((label, i) => ({ label, value: AD.duration.scores[i] })),
    highlight: 1,           // 15–30 s
    best: "15–30 second videos",
    sub: "keep it short",
  },
];

const ACTIONS = [
  { text: <>Post around <b>00:00–03:00 NPT</b></> },
  { text: <>Prioritize <b>Saturday</b> for peak engagement</> },
  { text: <>Use <b>4–7 hashtags</b></> },
  { text: <>Use <b>50–150 character</b> captions</> },
  { text: <>Keep videos around <b>15–30 seconds</b></> },
  { text: <>Maintain <b>consistent posting</b></> },
  { text: <>Weekends perform <b>slightly better</b></> },
  { text: <>Festival months require focus on <b>content quality</b></> },
];

export default function PrescriptiveTab() {
  return (
    <>
      <Section icon="adjustments" title="Content levers"
        subtitle="how format choices move engagement - the best option is highlighted">
        <div className="lever-grid">
          {LEVERS.map(l => (
            <div key={l.key} className="lever-card">
              <div className="lever-title">
                <i className={`ti ti-${l.icon}`} aria-hidden="true" />
                {l.title}
              </div>
              <LeverBars data={l.data} highlightIndex={l.highlight} height={150} />
              <span className="lever-best">
                <i className="ti ti-star-filled" aria-hidden="true" />
                {l.best} - {l.sub}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section icon="list-check" title="Action plan"
        subtitle="what 13 Kathmandu fashion businesses should do on TikTok">
        <div className="action-card">
          <div className="action-grid">
            {ACTIONS.map((a, i) => (
              <div key={i} className="action-item">
                <span className="check">
                  <i className="ti ti-check" aria-hidden="true" />
                </span>
                {a.text}
              </div>
            ))}
          </div>
        </div>
      </Section>
    </>
  );
}
