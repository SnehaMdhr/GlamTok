/** Small colored legend chips - for categories / datasets. */
export default function Legend({ items }) {
  return (
    <div className="legend-row">
      {items.map(({ label, color }) => (
        <span key={label} className="legend-chip">
          <span className="legend-dot" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}
