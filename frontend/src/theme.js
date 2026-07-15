// Design tokens - the single source of truth for the dashboard's look.
// Mirrors the CSS variables in index.css so inline styles stay in sync.
// Soft rose editorial theme: warm-cream background, white cards, warm-taupe
// text, rose primary (#FF7EA5), deep-rose accents (#B33E5D), light-rose soft
// fills (#FFDBE4), warm beige borders. Inter + JetBrains Mono, tight tracking,
// whisper-subtle shadows.

export const TT   = "#FF7EA5"; // primary accent - rose
export const PINK = "#FF7EA5"; // alias kept for compatibility
export const PURPLE = "#B33E5D"; // secondary accent - deep rose
export const GOOD = "#3AA876";
export const BAD  = "#E5484D";
export const WARN = "#D98A2B";

export const COLORS = {
  // surfaces
  bg:            "#FFF9F6",
  surface:       "#FFFFFF",   // cards
  surfaceAlt:    "#FAF3F0",   // muted fills / hover rows

  // borders
  border:        "#EBE0DA",
  borderStrong:  "#D8C7BF",

  // text (warm taupe scale)
  text:          "#5C4B43",
  textStrong:    "#45372E",   // KPI numbers / headings
  textMuted:     "#A18E84",
  textFaint:     "#B3A096",   // metadata

  // brand + semantics
  primary:       "#FF7EA5",
  primaryStrong: "#E5678F",
  primarySoft:   "#FFDBE4",
  pink:          "#FF7EA5",
  pinkSoft:      "#FFDBE4",
  purple:        "#B33E5D",
  purpleStrong:  "#96324E",
  purpleSoft:    "#FCE4EA",
  success:       "#3AA876",
  successStrong: "#237A55",
  successSoft:   "#E2F4EB",
  danger:        "#E5484D",
  dangerStrong:  "#C23B40",
  dangerSoft:    "#FDEAEA",
  warning:       "#D98A2B",
  warningStrong: "#A96A18",
  warningBg:     "#FBF1E0",
  warningBorder: "#F0DFC0",

  // shape (px)
  radiusSm: 6,
  radius:   10,
  radiusLg: 12,

  // elevation (very subtle)
  shadowSm: "0 2px 10px 0px rgb(0 0 0 / 0.03)",
  shadow:   "0 2px 10px 0px rgb(0 0 0 / 0.03), 0 1px 2px -1px rgb(0 0 0 / 0.03)",
  shadowLg: "0 2px 10px 0px rgb(0 0 0 / 0.03), 0 4px 6px -1px rgb(0 0 0 / 0.03)",

  // type
  font:     "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  fontMono: "'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, monospace",
};

// Backwards-compatible aliases so feature components can keep reading
// familiar names while we migrate to the tokens above.
COLORS.bgPrimary      = COLORS.surface;
COLORS.bgSecondary    = COLORS.surfaceAlt;
COLORS.borderTertiary = COLORS.border;
COLORS.textPrimary    = COLORS.text;
COLORS.textSecondary  = COLORS.textMuted;
COLORS.textTertiary   = COLORS.textFaint;
COLORS.textSuccess    = COLORS.successStrong;
COLORS.textDanger     = COLORS.dangerStrong;
COLORS.textWarning    = COLORS.warningStrong;
COLORS.bgWarning      = COLORS.warningBg;
COLORS.borderWarning  = COLORS.warningBorder;
COLORS.radiusMd       = COLORS.radiusSm;

// Chart palettes - rose family
// Heatmap: light rose → rose → deep rose
export const TT_SCALE = ["#FFDBE4", "#FFC4D3", "#FFABC2", "#FF93B2", "#FF7EA5", "#D95680", "#B33E5D"];

// Business bars - rose top, deep-rose 2nd, warm-mauve ramp after
export const BAR_COLORS = [
  "#FF7EA5", "#B33E5D", "#E8D5D0", "#E0CAC4", "#D8BEB8", "#D0B3AC",
  "#C8A7A0", "#C09B94", "#B88F88", "#B0837C", "#A87770", "#A06B64", "#985F58",
];

// Feature-importance category colors - deep-rose ML identity
export const CATEGORY_COLORS = {
  "Cyclical time":    "#B33E5D",
  "Nepal calendar":   "#F0C4CF",
  "Content type":     "#B79F97",
  "Engagement rates": "#96324E",
  "Account size":     "#FCE4EA",
};

// Dataset constants
export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const HOURS = Array.from({ length: 24 }, (_, i) => i);
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const FOLLOWER_OPTIONS = [500, 1000, 5000, 10000, 50000, 100000];

// Display convention used across the dashboard: engagement scores are
// shown as a percentage of the reference max (0.086) used in the thesis.
export const ENG_MAX = 0.086;
export const pct  = v => `${((v / ENG_MAX) * 100).toFixed(1)}%`;
export const pct0 = v => `${((v / ENG_MAX) * 100).toFixed(0)}%`;
