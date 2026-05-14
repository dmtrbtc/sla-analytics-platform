import ReactECharts from "echarts-for-react";

interface SLAHeatmapProps {
  data: Array<[string, string, number]>;
}

export default function SLAHeatmap({ data }: SLAHeatmapProps) {
  const queues = [...new Set(data.map((d) => d[0]))];
  const weeks = [...new Set(data.map((d) => d[1]))];

  const option = {
    tooltip: { position: "top" },
    xAxis: { type: "category", data: weeks },
    yAxis: { type: "category", data: queues },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      inRange: { color: ["#52c41a", "#faad14", "#ff4d4f"] },
    },
    series: [
      {
        type: "heatmap",
        data: data.map((d) => [d[1], d[0], d[2]]),
        label: { show: true },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
