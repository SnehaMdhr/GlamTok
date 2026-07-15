// Compact top header - page title and description, plus the
// mobile navigation trigger.
export default function Header({ meta, onOpenNav }) {
  return (
    <header className="topbar">
      <div className="page-head">
        <div className="page-eyebrow">{meta.eyebrow}</div>
        <h1 className="page-title">{meta.title}</h1>
        <p className="page-desc">{meta.desc}</p>
      </div>

      <div className="topbar-actions">
        <button type="button" className="btn-icon btn-hamburger" onClick={onOpenNav} aria-label="Open navigation">
          <i className="ti ti-menu-2" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
