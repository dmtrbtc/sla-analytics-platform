import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../../design/ThemeContext";

interface Point {
  response: number;
  resolution: number;
  queue: string;
  breached: boolean;
}

interface Props {
  data: Point[];
  height?: number;
}

export default function SLAScatter({ data, height = 280 }: Props) {
  const { colors, chartTheme } = useTheme();

  const option = useMemo(() => {
    const queues = [...new Set(data.map(d => d.queue))];
    const series = queues.map((q, i) => ({
      name: q,
      type: "scatter" as const,
      data: data.filter(d => d.queue === q).map(d => [d.response, d.resolution]),
      symbolSize: (val: number[]) => (val[0] > 0 && val[1] > 0 ? 8 : 4),
      itemStyle: { color: colors.chart.line[i % colors.chart.line.length], opacity: 0.7 },
    }));

    return {
      backgroundColor: "transparent",
      tooltip: { formatter: (p: any) => `<strong>${p.seriesName}</strong><br/>Response: ${p.data[0]}h<br/>Resolution: ${p.data[1]}h` },
      grid: { left: 48, right: 16, top: 36, bottom: 28 },
      xAxis: { name: "Response Time (h)", nameTextStyle: { fontSize: 10, color: colors.text.tertiary }, axisLabel: { fontSize: 10, color: colors.text.tertiary }, splitLine: { lineStyle: { color: colors.divider, type: "dashed" } } },
      yAxis: { name: "Resolution Time (h)", nameTextStyle: { fontSize: 10, color: colors.text.tertiary }, axisLabel: { fontSize: 10, color: colors.text.tertiary }, splitLine: { lineStyle: { color: colors.divider, type: "dashed" } } },
      legend: { type: "scroll", bottom: 0, textStyle: { fontSize: 10, color: colors.text.secondary } },
      series,
    };
  }, [data, colors]);

  return <ReactEChartsCore theme="sla" option={option} style={{ height }} notMerge />;
}
