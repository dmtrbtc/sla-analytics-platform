import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../../design/ThemeContext";

interface Props {
  data: { hour: number; day: string; value: number }[];
  height?: number;
}

export default function SLAHeatmap({ data, height = 280 }: Props) {
  const { colors, chartTheme } = useTheme();

  const option = useMemo(() => {
    const days = [...new Set(data.map(d => d.day))];
    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);

    const heatmapData = data.map(d => [d.day, d.hour, d.value]);

    return {
      backgroundColor: "transparent",
      tooltip: { position: "top", formatter: (p: any) => `${p.data[0]} ${p.data[1]}:00 — ${p.data[2]} tickets` },
      grid: { left: 56, right: 16, top: 8, bottom: 32 },
      xAxis: { type: "category", data: days, axisLabel: { fontSize: 10, color: colors.text.tertiary } },
      yAxis: { type: "category", data: hours, axisLabel: { fontSize: 9, color: colors.text.tertiary } },
      visualMap: {
        min: 0,
        max: Math.max(...heatmapData.map(d => Number(d[2])), 1),
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        inRange: { color: colors.chart.heatmap },
        textStyle: { color: colors.text.tertiary, fontSize: 10 },
      },
      series: [{
        type: "heatmap",
        data: heatmapData,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 4, shadowColor: "rgba(0,0,0,0.15)" } },
      }],
    };
  }, [data, colors]);

  return <ReactEChartsCore option={option} style={{ height }} notMerge />;
}
