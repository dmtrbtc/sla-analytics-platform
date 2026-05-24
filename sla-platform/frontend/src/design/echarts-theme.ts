/**
 * ECharts theme `sla` for SLA Platform.
 *
 * Registered once in `main.tsx` via `echarts.registerTheme("sla", slaEChartsTheme)`.
 * Every `<ReactECharts theme="sla" ... />` in the app pulls these defaults.
 *
 * Palette order:
 *   1. Реакция     — orange  (--reaction)
 *   2. Решение     — violet  (--resolution)
 *   3. Brand       — indigo  (--brand)
 *   4. OK          — green   (--ok)
 *   5. High        — amber   (--high)
 *   6. Critical    — red     (--crit)
 *
 * The "Реакция = orange, Решение = violet" pair is canonical — never invert
 * the order, never substitute, even for visual variety.
 */

export const slaEChartsTheme = {
  color: ["#f59e0b", "#8b5cf6", "#4f46e5", "#10b981", "#f97316", "#ef4444"],
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: '"Inter", -apple-system, sans-serif',
    color: "#344054",
  },
  title: {
    textStyle: { color: "#101828", fontWeight: 600, fontSize: 14 },
    subtextStyle: { color: "#667085", fontSize: 12 },
  },
  line: {
    smooth: false,
    symbol: "circle",
    symbolSize: 5,
    lineStyle: { width: 2 },
    itemStyle: { borderWidth: 0 },
  },
  bar: { itemStyle: { borderRadius: [3, 3, 0, 0] } },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#e4e7ec" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: {
      color: "#98a2b3",
      fontFamily: "JetBrains Mono",
      fontSize: 10.5,
    },
  },
  valueAxis: {
    axisLine: { show: false },
    splitLine: { lineStyle: { color: "#eef0f3", type: "solid" } },
    axisLabel: {
      color: "#98a2b3",
      fontFamily: "JetBrains Mono",
      fontSize: 10.5,
    },
  },
  legend: {
    textStyle: { color: "#667085", fontSize: 12 },
    icon: "roundRect",
  },
  tooltip: {
    backgroundColor: "#101828",
    borderColor: "#101828",
    borderRadius: 8,
    textStyle: {
      color: "#ffffff",
      fontSize: 12,
      fontFamily: '"Inter", sans-serif',
    },
    padding: [10, 12],
    extraCssText:
      "box-shadow: 0 8px 16px rgba(16,24,40,0.18); font-feature-settings: 'tnum';",
  },
};

/**
 * Stable name we register with echarts. Use it as the `theme="sla"` prop
 * on every chart in the project.
 */
export const SLA_ECHARTS_THEME_NAME = "sla";
