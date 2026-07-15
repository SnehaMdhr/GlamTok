// Fixed left navigation - GlamTok · Nepal Fashion Analytics

const NAV_GROUPS = [
  {
    label: "Prediction",
    items: [
      { key: "predict", label: "Predict", icon: "chart-dots" },
    ],
  },
  {
    label: "Analytics",
    items: [
      { key: "descriptive",  label: "Descriptive",   icon: "chart-histogram" },
      { key: "diagnostic",   label: "Diagnostic",    icon: "search" },
      { key: "predictive",   label: "Predictive",    icon: "cpu" },
      { key: "prescriptive", label: "Prescriptive",  icon: "bulb" },
    ],
  },
  {
    label: "Data",
    items: [
      { key: "posts",      label: "Posts",      icon: "database" },
      { key: "businesses", label: "Businesses", icon: "building-store" },
    ],
  },
  
];

export default function Sidebar({ active, onChange, dark, onToggleTheme }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-inner">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1"
              strokeLinecap="round" strokeLinejoin="round">
              {/* analytics pulse line */}
              <path d="M2.5 12.5 H7.5 L10 5.5 L13.5 19 L16 12.5 H21.5" />
              {/* glam sparkle */}
              <path d="M19.3 1.6 L20 4.7 L23.1 5.4 L20 6.1 L19.3 9.2 L18.6 6.1 L15.5 5.4 L18.6 4.7 Z"
                fill="currentColor" stroke="none" />
            </svg>
          </span>
          <span>
            <span className="brand-name">GlamTok</span>
          </span>
        </div>

        <nav className="sidenav" aria-label="Main navigation">
          {NAV_GROUPS.map(group => (
            <div className="nav-group" key={group.label}>
              <div className="nav-group-label">{group.label}</div>
              {group.items.map(({ key, label, icon }) => (
                <button key={key} type="button"
                  className={active === key ? "nav-item active" : "nav-item"}
                  onClick={() => onChange(key)}
                  aria-current={active === key ? "page" : undefined}>
                  <i className={`ti ti-${icon}`} aria-hidden="true" />
                  {label}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button type="button" className="theme-toggle" onClick={onToggleTheme}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}>
            <i className={dark ? "ti ti-sun" : "ti ti-moon"} aria-hidden="true" />
            <span>{dark ? "Light mode" : "Dark mode"}</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
