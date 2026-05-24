import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../../design/ThemeContext";

interface Link {
  source: string;
  target: string;
  value: number;
}

interface Props {
  links: Link[];
  height?: number;
}

export default function QueueSankey({ links, height = 300 }: Props) {
  const { colors } = useTheme();

  const nodes = useMemo(() => {
    const names = new Set<string>();
    links.forEach(l => { names.add(l.source); names.add(l.target); });
    return [...names].map(n => ({ name: n }));
  }, [links]);

  const option = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: { formatter: (p: any) => `${p.data.source} → ${p.data.target}: ${p.data.value} tickets` },
    series: [{
      type: "sankey",
      layout: "none",
      emphasis: { focus: "adjacency" },
      nodeAlign: "left" as const,
      nodeWidth: 16,
      nodeGap: 12,
      data: nodes,
      links,
      lineStyle: { color: "gradient", curveness: 0.5 },
      label: { fontSize: 10, color: colors.text.secondary },
    }],
  }), [nodes, links, colors]);

  return <ReactEChartsCore theme="sla" option={option} style={{ height }} notMerge />;
}
