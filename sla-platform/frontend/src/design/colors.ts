export const palette = {
  white: "#ffffff",
  page: "#f6f8fa",
  card: "#ffffff",
  border: "#e8ecf0",
  borderLight: "#f0f2f5",
  divider: "#eef1f5",

  text: {
    primary: "#1a1d26",
    secondary: "#5a6070",
    tertiary: "#9399a8",
    disabled: "#c0c6d0",
    inverse: "#ffffff",
  },

  brand: {
    50: "#eef2ff",
    100: "#dce4f5",
    200: "#b8c8eb",
    300: "#8fa8db",
    400: "#5a7fc4",
    500: "#3b6bb5",
    600: "#2a5699",
    700: "#1e4080",
    800: "#142b66",
    900: "#0c1a4d",
  },

  accent: {
    teal: "#0d9488",
    tealLight: "#ccfbf1",
    indigo: "#6366f1",
    indigoLight: "#e0e7ff",
    rose: "#f43f5e",
    roseLight: "#ffe4e6",
    amber: "#f59e0b",
    amberLight: "#fef3c7",
    emerald: "#22c55e",
    emeraldLight: "#d1fae5",
    sky: "#0ea5e9",
    skyLight: "#e0f2fe",
  },

  severity: {
    ok: "#22c55e",
    okBg: "#f0fdf4",
    warn: "#f59e0b",
    warnBg: "#fffbeb",
    high: "#f97316",
    highBg: "#fff7ed",
    crit: "#ef4444",
    critBg: "#fef2f2",
  },

  chart: {
    line: ["#3b6bb5", "#0d9488", "#6366f1", "#f59e0b", "#f43f5e"],
    area: ["rgba(59,107,181,0.12)", "rgba(13,148,136,0.12)", "rgba(99,102,241,0.12)", "rgba(245,158,11,0.12)", "rgba(244,63,94,0.12)"],
    heatmap: ["#f0f2f5", "#dce4f5", "#8fa8db", "#5a7fc4", "#2a5699"],
    bar: ["#3b6bb5", "#0d9488", "#6366f1", "#f59e0b", "#f43f5e", "#8b5cf6"],
    gauge: ["#22c55e", "#f59e0b", "#ef4444"],
  },
} as const;

export type PaletteToken = keyof typeof palette.text;
