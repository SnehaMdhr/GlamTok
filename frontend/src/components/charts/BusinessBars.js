import { ENG_MAX } from "../../theme";

/**
 * Ranked horizontal bars for business engagement.
 * items: [{ name, score }] in ranked order (highest first).
 * pctFmt - how to render the trailing value (default: score/ENG_MAX %).
 */
export default function BusinessBars({ items, nameWidth = 108, showRank = true, valueFmt }) {
  if (!items.length) return <div style={{ fontSize: 13, color: "var(--text-faint)" }}>No data.</div>;
  const max = Math.max(...items.map(b => b.score), 0.001);
  const fmt = valueFmt || (v => `${Math.min(100, (v / ENG_MAX) * 100).toFixed(0)}%`);

  return (
    <div>
      {items.map((b, i) => {
        const pctW = Math.max(2, (b.score / max) * 100);
        const cls = i === 0 ? "bar-row top" : i === 1 ? "bar-row second" : "bar-row";
        const fill = i === 0
          ? `linear-gradient(90deg, rgba(255,126,165,0.35), var(--accent))`
          : i === 1
            ? `linear-gradient(90deg, rgba(179,62,93,0.5), var(--accent-strong))`
            : `linear-gradient(90deg, var(--bar-muted-a), var(--bar-muted-b))`;
        return (
          <div key={b.name} className={cls}>
            {showRank && <span className="bar-rank">{i + 1}</span>}
            <span className="bar-name" style={{ width: nameWidth, textAlign: "left" }}>
              {i === 0 ? <strong>{b.name}</strong> : b.name}
            </span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${pctW}%`, background: fill }} />
            </div>
            <span className="bar-pct">
              {i === 0 ? <strong>{fmt(b.score)}</strong> : fmt(b.score)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
