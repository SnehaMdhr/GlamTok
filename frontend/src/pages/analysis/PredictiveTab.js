import { AD } from "../../data/analytics";
import Section from "../../components/ui/Section";
import Card from "../../components/ui/Card";
import FeatureImportanceChart from "../../components/charts/FeatureImportanceChart";

const rf  = AD.model_metrics.RandomForest;
const xgb = AD.model_metrics.XGBoost;
const cls = AD.classification["XGBoost Classifier"];

const METRICS = [
  ["RMSE", "Lower is better", rf.rmse.toFixed(5), xgb.rmse.toFixed(5)],
  ["MAE", "Lower is better", rf.mae.toFixed(5), xgb.mae.toFixed(5)],
  ["R²", "Higher is better", rf.r2.toFixed(3), xgb.r2.toFixed(3)],
];

export default function PredictiveTab() {
  const D = AD;

  const features = D.features.labels.map((label, i) => ({
    label,
    importance: D.features.importance[i],
    category: D.features.categories[i] || "Content type",
  }));

  const top = features[0];

  return (
    <>
      <div className="card-grid">
        <Section icon="cpu" title="Model comparison"
          subtitle="Random Forest vs XGBoost on held-out test data">
          <table className="model-table">
            <thead>
              <tr>
                <th style={{ width: "34%" }}>Metric</th>
                <th>Random Forest</th>
                <th>XGBoost</th>
              </tr>
            </thead>
            <tbody>
              {METRICS.map(([m, hint, rfV, xgbV]) => (
                <tr key={m}>
                  <td className="metric-name">
                    {m}
                    <span className="metric-hint">{hint}</span>
                  </td>
                  <td>
                    <span className="model-name">Random Forest</span>
                    <div className="metric-value">{rfV}</div>
                  </td>
                  <td className="xgb-col">
                    <div className="xgb-box">
                      <span className="model-name xgb">XGBoost <i className="ti ti-check winner-check" aria-hidden="true" /></span>
                      <div className="metric-value xgb">{xgbV}</div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Card className="best-model" title={null}>
          <div className="best-eyebrow">Best model</div>
          <div className="best-name">XGBoost</div>
          <div className="best-r2">R² {xgb.r2.toFixed(3)}</div>
          <div className="best-sub">Wins on all 3 metrics - explains {xgb.r2.toFixed(3)} of the variance in engagement (classification: {(cls.accuracy * 100).toFixed(1)}% accuracy)</div>
        </Card>
      </div>

      <Section icon="chart-bar" title="Feature importance"
        subtitle="what actually drives the predictions - ranked by contribution">
        <FeatureImportanceChart features={features} />
        <div className="chart-note" style={{ marginTop: 14 }}>
          <i className="ti ti-trophy" aria-hidden="true" />
          Top feature: {top.label} ({(top.importance * 100).toFixed(1)}%) - account size dominates
        </div>
      </Section>

      <Section icon="bulb" title="Key thesis finding">
        <div className="hero-card violet" style={{ boxShadow: "0 1px 2px rgba(92,75,67,0.04)" }}>
          <div className="hero-eyebrow">Key thesis finding</div>
          <div className="hero-title" style={{ fontSize: 21 }}>
            Account size - not timing - drives engagement.
          </div>
          <div style={{ fontSize: 13.5, color: "var(--text-muted)", marginTop: 12, lineHeight: 1.6, maxWidth: 720 }}>
            Account size (<span style={{ fontFamily: "monospace", color: "var(--text)" }}>followers_log</span>) is by far the
            strongest predictor at {(top.importance * 100).toFixed(1)}% of importance. Posting time (hour / day-of-week)
            contributes only around 10% combined - the model explains just {xgb.r2.toFixed(3)} of the variance in
            engagement, so timing is a weak lever compared with audience size and content.
          </div>
        </div>
      </Section>
    </>
  );
}
