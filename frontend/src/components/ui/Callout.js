export default function Callout({ icon, tone = "cyan", children }) {
  return (
    <div className={`callout callout-${tone}`}>
      {icon && <i className={`ti ti-${icon}`} aria-hidden="true" />}
      <div>{children}</div>
    </div>
  );
}
