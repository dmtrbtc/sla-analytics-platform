/* Enterprise Design System V3 — ECharts themes (light + dark) */
import { palette, darkPalette } from "./colors";

export const chartTheme = {
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontSize: 11,
    color: palette.text.tertiary,
  },
  grid: { top: 24, bottom: 20, left: 40, right: 16, containLabel: true },
  tooltip: {
    backgroundColor: palette.white,
    borderColor: palette.border,
    borderWidth: 1,
    textStyle: { fontSize: 12, color: palette.text.primary },
    extraCssText: "box-shadow: 0 4px 12px rgba(27,31,35,0.08); border-radius: 6px;",
  },
  legend: {
    textStyle: { fontSize: 11, color: palette.text.secondary },
    pageTextStyle: { color: palette.text.tertiary },
  },
  xAxis: {
    axisLine: { lineStyle: { color: palette.border } },
    axisLabel: { color: palette.text.tertiary, fontSize: 10 },
    splitLine: { show: false },
  },
  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: palette.text.tertiary, fontSize: 10 },
    splitLine: { lineStyle: { color: palette.divider, type: "dashed" as const } },
  },
  series: {
    line: { smooth: true, lineStyle: { width: 2 }, symbol: "circle", symbolSize: 4 },
    bar: { barMaxWidth: 24, itemStyle: { borderRadius: [2, 2, 0, 0] } },
    scatter: { symbolSize: 6 },
    heatmap: { label: { show: false } },
  },
};

export const darkChartTheme = {
  ...chartTheme,
  textStyle: { ...chartTheme.textStyle, color: darkPalette.text.tertiary },
  tooltip: {
    ...chartTheme.tooltip,
    backgroundColor: darkPalette.card,
    borderColor: darkPalette.border,
    textStyle: { ...chartTheme.tooltip.textStyle, color: darkPalette.text.primary },
    extraCssText: "box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-radius: 6px;",
  },
  legend: { textStyle: { fontSize: 11, color: darkPalette.text.secondary } },
  xAxis: { axisLine: { lineStyle: { color: darkPalette.border } }, axisLabel: { color: darkPalette.text.tertiary, fontSize: 10 }, splitLine: { show: false } },
  yAxis: {
    axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: darkPalette.text.tertiary, fontSize: 10 },
    splitLine: { lineStyle: { color: darkPalette.divider, type: "dashed" as const } },
  },
  series: chartTheme.series,
};
