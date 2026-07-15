export default function Tag({ children, color }) {
  return (
    <span style={{ fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 999,
      background: `color-mix(in srgb, ${color} 14%, transparent)`, color,
      border: `1px solid color-mix(in srgb, ${color} 40%, transparent)`, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}
