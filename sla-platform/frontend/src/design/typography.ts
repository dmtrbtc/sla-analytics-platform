/* Enterprise Design System V3 — Inter typography with clear hierarchy */
export const typography = {
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  fontMono: "'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",

  size: {
    xs: "11px",
    sm: "12px",
    base: "13px",
    md: "14px",
    lg: "15px",
    xl: "16px",
    "2xl": "18px",
    "3xl": "20px",
    "4xl": "24px",
    "5xl": "30px",
    "6xl": "36px",
    "7xl": "42px",
  },

  weight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: "1.2",
    normal: "1.4",
    relaxed: "1.6",
  },

  letterSpacing: {
    tight: "-0.02em",
    normal: "0",
    wide: "0.02em",
    wider: "0.04em",
  },

  heading: {
    h1: { size: "28px", weight: 600, lineHeight: "1.25", letterSpacing: "-0.025em" },
    h2: { size: "22px", weight: 600, lineHeight: "1.3", letterSpacing: "-0.02em" },
    h3: { size: "17px", weight: 600, lineHeight: "1.35", letterSpacing: "-0.01em" },
    h4: { size: "14px", weight: 600, lineHeight: "1.4", letterSpacing: "0" },
    subtitle: { size: "13px", weight: 500, lineHeight: "1.5", letterSpacing: "0.005em" },
    label: { size: "11px", weight: 600, lineHeight: "1.5", letterSpacing: "0.05em" },
    kpi: { size: "26px", weight: 700, lineHeight: "1.15", letterSpacing: "-0.02em" },
  },
} as const;
