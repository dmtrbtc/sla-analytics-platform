import ReactECharts from "echarts-for-react";

interface TimeSeriesChartProps {
  data: Array<{ date: string; value: number }>;
  title?: string;
}

export default function TimeSeriesChart({ data, title }: TimeSeriesChartProps) {
  const option = {
    title: { text: title, left: "center" },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: data.map((d) => d.date) },
    yAxis: { type: "value" },
    series: [
      {
        type: "line",
        data: data.map((d) => d.value),
        smooth: true,
        areaStyle: { opacity: 0.3 },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 300 }} />;
}
