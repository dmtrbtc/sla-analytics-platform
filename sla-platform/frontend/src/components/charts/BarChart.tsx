import ReactECharts from "echarts-for-react";

interface BarChartProps {
  data: Array<{ name: string; value: number }>;
  title?: string;
}

export default function BarChart({ data, title }: BarChartProps) {
  const option = {
    title: { text: title, left: "center" },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: data.map((d) => d.name) },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: data.map((d) => d.value) }],
  };

  return <ReactECharts option={option} style={{ height: 300 }} />;
}
