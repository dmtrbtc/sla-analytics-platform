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
    "5xl": "28px",
    "6xl": "32px",
  },

  weight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: "1.25",
    normal: "1.5",
    relaxed: "1.625",
  },

  letterSpacing: {
    tight: "-0.01em",
    normal: "0",
    wide: "0.02em",
  },

  heading: {
    h1: { size: "24px", weight: 600, lineHeight: "1.3", letterSpacing: "-0.02em" },
    h2: { size: "20px", weight: 600, lineHeight: "1.3", letterSpacing: "-0.015em" },
    h3: { size: "16px", weight: 600, lineHeight: "1.4", letterSpacing: "-0.01em" },
    h4: { size: "14px", weight: 600, lineHeight: "1.4", letterSpacing: "0" },
    subtitle: { size: "13px", weight: 500, lineHeight: "1.5", letterSpacing: "0.01em" },
    label: { size: "11px", weight: 600, lineHeight: "1.5", letterSpacing: "0.04em" },
  },
} as const;
