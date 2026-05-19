import { palette } from "./colors";
import { typography } from "./typography";

export const chartTheme = {
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: typography.fontFamily,
    color: palette.text.secondary,
    fontSize: 11,
  },

  grid: {
    containLabel: true,
    top: 20,
    bottom: 24,
    left: 8,
    right: 8,
  },

  tooltip: {
    backgroundColor: "#ffffff",
    borderColor: palette.border,
    borderWidth: 1,
    borderRadius: 6,
    padding: [10, 14],
    textStyle: {
      fontFamily: typography.fontFamily,
      fontSize: 12,
      color: palette.text.primary,
      lineHeight: 1.5,
    },
    extraCssText: "box-shadow: 0 4px 12px rgba(26,29,38,0.08);",
  },

  legend: {
    bottom: 0,
    icon: "circle",
    itemWidth: 8,
    itemHeight: 8,
    textStyle: {
      fontFamily: typography.fontFamily,
      fontSize: 11,
      color: palette.text.secondary,
    },
  },

  xAxis: {
    axisLine: { lineStyle: { color: palette.border } },
    axisTick: { lineStyle: { color: palette.borderLight }, length: 4 },
    axisLabel: {
      fontFamily: typography.fontFamily,
      fontSize: 10,
      color: palette.text.tertiary,
    },
    splitLine: { show: false },
  },

  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      fontFamily: typography.fontFamily,
      fontSize: 10,
      color: palette.text.tertiary,
    },
    splitLine: {
      lineStyle: { color: palette.borderLight, type: "dashed" as const },
    },
  },

  series: {
    line: {
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 1 },
    },
    bar: {
      barMaxWidth: 32,
      itemStyle: { borderRadius: [2, 2, 0, 0] },
    },
    scatter: {
      symbolSize: 6,
    },
    heatmap: {
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(26,29,38,0.1)" } },
    },
  },
} as const;
