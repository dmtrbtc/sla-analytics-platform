/* Enterprise Design System V3 — neutral corporate palette, soft severity, AA+ accessible */
export const palette = {
  white: "#ffffff",
  page: "#f4f5f7",
  card: "#ffffff",
  border: "#e1e4e8",
  borderLight: "#ebedf0",
  divider: "#eff1f3",

  text: {
    primary: "#1b1f23",
    secondary: "#586069",
    tertiary: "#8b929a",
    disabled: "#c4c9ce",
    inverse: "#ffffff",
    link: "#0969da",
  },

  brand: {
    50: "#f0f6ff",
    100: "#dde9ff",
    200: "#b4d1ff",
    300: "#7fb4ff",
    400: "#4080ff",
    500: "#0969da",
    600: "#0550ae",
    700: "#033d8b",
    800: "#012b6b",
    900: "#001d4d",
  },

  accent: {
    teal: "#15803d",
    tealLight: "#e5f8ed",
    indigo: "#5046e5",
    indigoLight: "#eae8fd",
    rose: "#d92d4a",
    roseLight: "#fde8ec",
    amber: "#b65709",
    amberLight: "#fef2da",
    emerald: "#1a7f3b",
    emeraldLight: "#dff5e8",
    sky: "#1a7db9",
    skyLight: "#e0f0fa",
  },

  severity: {
    ok: "#1a7f3b",
    okBg: "#e8f8ee",
    warn: "#b65709",
    warnBg: "#fef4e0",
    high: "#c94c0d",
    highBg: "#fef0e4",
    crit: "#b42333",
    critBg: "#fde8ec",
  },

  chart: {
    line: ["#0969da", "#15803d", "#5046e5", "#b65709", "#d92d4a", "#1a7db9"],
    area: ["rgba(9,105,218,0.10)", "rgba(21,128,61,0.10)", "rgba(80,70,229,0.10)", "rgba(182,87,9,0.10)", "rgba(217,45,74,0.10)"],
    heatmap: ["#f0f2f5", "#dde9ff", "#7fb4ff", "#4080ff", "#0550ae"],
    bar: ["#0969da", "#15803d", "#5046e5", "#b65709", "#d92d4a", "#1a7db9"],
    gauge: ["#1a7f3b", "#b65709", "#b42333"],
  },
} as const;

export const darkPalette = {
  white: "#0d1117",
  page: "#010409",
  card: "#161b22",
  border: "#30363d",
  borderLight: "#252a32",
  divider: "#21262d",

  text: {
    primary: "#e6edf3",
    secondary: "#8b949e",
    tertiary: "#6e7681",
    disabled: "#484f58",
    inverse: "#0d1117",
    link: "#58a6ff",
  },

  brand: {
    50: "#0a1628",
    100: "#0f2440",
    200: "#1c3b66",
    300: "#285494",
    400: "#3570c4",
    500: "#58a6ff",
    600: "#79b8ff",
    700: "#a5d6ff",
    800: "#c8e1ff",
    900: "#e6edf3",
  },

  accent: {
    teal: "#3fb950",
    tealLight: "#0b2e13",
    indigo: "#7c7cf0",
    indigoLight: "#1a1a3e",
    rose: "#f47068",
    roseLight: "#3e1616",
    amber: "#d29922",
    amberLight: "#3e2d0b",
    emerald: "#3fb950",
    emeraldLight: "#0b2e13",
    sky: "#58a6ff",
    skyLight: "#0a2540",
  },

  severity: {
    ok: "#3fb950",
    okBg: "#0b2e13",
    warn: "#d29922",
    warnBg: "#3e2d0b",
    high: "#f47068",
    highBg: "#3e1616",
    crit: "#f85149",
    critBg: "#3d1214",
  },

  chart: {
    line: ["#58a6ff", "#3fb950", "#7c7cf0", "#d29922", "#f47068", "#79b8ff"],
    area: ["rgba(88,166,255,0.10)", "rgba(63,185,80,0.10)", "rgba(124,124,240,0.10)", "rgba(210,153,34,0.10)", "rgba(244,112,104,0.10)"],
    heatmap: ["#161b22", "#1c3b66", "#285494", "#3570c4", "#58a6ff"],
    bar: ["#58a6ff", "#3fb950", "#7c7cf0", "#d29922", "#f47068", "#79b8ff"],
    gauge: ["#3fb950", "#d29922", "#f85149"],
  },
} as const;
