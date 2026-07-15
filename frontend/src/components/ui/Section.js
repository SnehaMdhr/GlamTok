import SectionHeader from "./SectionHeader";

/**
 * A titled card - the standard content block of the dashboard.
 * Renders a dark rounded surface with a section header on top.
 */
export default function Section({ icon, title, subtitle, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      <SectionHeader icon={icon} title={title} subtitle={subtitle} />
      {children}
    </section>
  );
}
