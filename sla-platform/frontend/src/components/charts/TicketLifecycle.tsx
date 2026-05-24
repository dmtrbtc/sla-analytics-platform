import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../../design/ThemeContext";

interface Phase {
  name: string;
  start: number;
  end: number;
  status: "ok" | "warn" | "crit";
}

interface Props {
  phases: Phase[];
  height?: number;
}

export default function TicketLifecycle({ phases, height = 60 }: Props) {
  const { colors } = useTheme();

  const statusColors = { ok: colors.severity.ok, warn: colors.severity.warn, crit: colors.severity.crit };

  const option = useMemo(() => ({
    backgroundColor: "transparent",
    grid: { left: 80, right: 16, top: 4, bottom: 4 },
    xAxis: { type: "value", show: false, min: 0, max: Math.max(...phases.map(p => p.end), 1) },
    yAxis: { type: "category", data: [""], show: false },
    series: phases.map((p, i) => ({
      type: "bar" as const,
      barGap: "-100%",
      data: [{ value: [p.start, p.end], itemStyle: { color: statusColors[p.status], borderRadius: [2, 2, 2, 2] } }],
      label: { show: i === 0, formatter: p.name, position: "left", fontSize: 9, color: colors.text.secondary },
    })),
  }), [phases, colors]);

  return <ReactEChartsCore theme="sla" option={option} style={{ height }} notMerge />;
}
