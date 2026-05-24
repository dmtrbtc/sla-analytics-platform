import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../../design/ThemeContext";

interface Props {
  data: { date: string; remaining: number; ideal: number }[];
  height?: number;
}

export default function SLABurnDown({ data, height = 200 }: Props) {
  const { colors } = useTheme();

  const option = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", formatter: (p: any) => `${p[0].axisValue}<br/>${p.map((s: any) => `${s.marker} ${s.seriesName}: ${Math.round(s.data)}`).join("<br/>")}` },
    grid: { left: 40, right: 16, top: 8, bottom: 24 },
    xAxis: { type: "category", data: data.map(d => d.date), axisLabel: { fontSize: 9, color: colors.text.tertiary }, axisLine: { lineStyle: { color: colors.border } } },
    yAxis: { type: "value", axisLabel: { fontSize: 10, color: colors.text.tertiary }, splitLine: { lineStyle: { color: colors.divider, type: "dashed" } } },
    series: [
      { name: "Ideal", type: "line", data: data.map(d => d.ideal), smooth: true, lineStyle: { width: 2, type: "dashed", color: colors.text.disabled }, symbol: "none" },
      { name: "Actual", type: "line", data: data.map(d => d.remaining), smooth: true, lineStyle: { width: 2, color: colors.severity.high }, areaStyle: { color: colors.chart.area[4] }, symbol: "circle", symbolSize: 4 },
    ],
  }), [data, colors]);

  return <ReactEChartsCore theme="sla" option={option} style={{ height }} notMerge />;
}
