/**
 * KPI stat card - big tabular number, small uppercase label, optional sub.
 * accent: "primary" | "secondary" | "green" | "orange" | "neutral"
 * highlight: render the value in the strong accent color (important KPI).
 */
export default function StatCard({ label, value, sub, icon, accent = "primary", highlight = false }) {
  return (
    <div className={`stat-card accent-${accent}`}>
      <div className="stat-label">
        {label}
        {icon && <i className={`ti ti-${icon}`} aria-hidden="true" />}
      </div>
      <div className={highlight ? "stat-value hl" : "stat-value"}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
