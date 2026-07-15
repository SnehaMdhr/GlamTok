import DescriptiveTab from "./analysis/DescriptiveTab";
import DiagnosticTab from "./analysis/DiagnosticTab";
import PredictiveTab from "./analysis/PredictiveTab";
import PrescriptiveTab from "./analysis/PrescriptiveTab";

/**
 * Analysis page - the `tab` prop selects which section renders; the sidebar
 * drives switching between Descriptive / Diagnostic / Predictive / Prescriptive.
 */
export default function AnalysisPage({ tab }) {
  const active = tab ?? "descriptive";

  return (
    <div className="analysis-page">
      {active === "descriptive" && <DescriptiveTab />}
      {active === "diagnostic" && <DiagnosticTab />}
      {active === "predictive" && <PredictiveTab />}
      {active === "prescriptive" && <PrescriptiveTab />}
    </div>
  );
}
