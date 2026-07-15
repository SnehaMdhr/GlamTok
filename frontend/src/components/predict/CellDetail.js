import { DAYS } from "../../theme";
import Tag from "../ui/Tag";

export default function CellDetail({ cell }) {
  if (!cell) return null;

  const quality = cell.s > 0.75 ? "Excellent" : cell.s > 0.5 ? "Good" : cell.s > 0.25 ? "Average" : "Low";
  const qColor  = cell.s > 0.75 ? "var(--success)" : cell.s > 0.5 ? "var(--accent-strong)" : cell.s > 0.25 ? "var(--warning)" : "var(--danger)";

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginTop: 14,
      padding: "12px 14px", background: "var(--accent-surface)",
      border: "1px solid var(--accent-border)", borderRadius: 10,
    }}>
      <i className="ti ti-click" aria-hidden="true" style={{ fontSize: 15, color: "var(--accent-strong)" }} />
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, fontSize: 13.5, color: "var(--text)" }}>
        {DAYS[cell.d]} {String(cell.h).padStart(2, "0")}:00 NPT
      </div>
      <Tag color={qColor}>{quality}</Tag>
      <div style={{ marginLeft: "auto", fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: "var(--text-muted)" }}>
        score <b style={{ color: "var(--accent-strong)" }}>{(cell.s * 100).toFixed(1)}%</b>
      </div>
    </div>
  );
}
