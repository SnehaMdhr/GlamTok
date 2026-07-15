export default function Card({ title, subtitle, icon, children, className = "" }) {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="section-head">
          {icon && (
            <div className="section-icon">
              <i className={`ti ti-${icon}`} aria-hidden="true" />
            </div>
          )}
          <div style={{ minWidth: 0 }}>
            <div className="section-title">{title}</div>
            {subtitle && <div className="section-sub">{subtitle}</div>}
          </div>
        </div>
      )}
      {children}
    </div>
  );
}
