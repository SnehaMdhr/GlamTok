export default function SectionHeader({ icon, title, subtitle }) {
  return (
    <div className="section-head">
      <div className="section-icon">
        <i className={`ti ti-${icon}`} aria-hidden="true" />
      </div>
      <div style={{ minWidth: 0 }}>
        <div className="section-title">{title}</div>
        {subtitle && <div className="section-sub">{subtitle}</div>}
      </div>
    </div>
  );
}
