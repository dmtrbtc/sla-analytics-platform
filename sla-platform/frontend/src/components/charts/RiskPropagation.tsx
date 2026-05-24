import { useMemo } from "react";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../../design/ThemeContext";

interface Node {
  id: string;
  name: string;
  risk: number;
  category: number;
}

interface Edge {
  source: string;
  target: string;
  weight: number;
}

interface Props {
  nodes: Node[];
  edges: Edge[];
  height?: number;
}

export default function RiskPropagation({ nodes, edges, height = 300 }: Props) {
  const { colors } = useTheme();

  const categories = useMemo(() => {
    const cats = [...new Set(nodes.map(n => n.category))];
    return cats.map(c => ({ name: `Category ${c}`, itemStyle: { color: colors.chart.line[c % colors.chart.line.length] } }));
  }, [nodes, colors]);

  const option = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: { formatter: (p: any) => p.dataType === "node" ? `<strong>${p.data.name}</strong><br/>Risk: ${(p.data.risk * 100).toFixed(0)}%` : `${p.data.source} → ${p.data.target}: ${p.data.weight}` },
    series: [{
      type: "graph",
      layout: "force",
      force: { repulsion: 300, edgeLength: [80, 200], friction: 0.1 },
      roam: true,
      draggable: true,
      data: nodes.map(n => ({ ...n, symbolSize: 10 + n.risk * 30, itemStyle: { color: n.risk > 0.7 ? colors.severity.crit : n.risk > 0.4 ? colors.severity.warn : colors.severity.ok } })),
      edges: edges.map(e => ({ ...e, lineStyle: { width: e.weight * 3, opacity: 0.5, curveness: 0.2 }, label: { show: false } })),
      categories,
      edgeSymbol: ["none", "arrow"],
      edgeSymbolSize: [0, 6],
      label: { show: true, position: "right", fontSize: 9, color: colors.text.secondary },
      lineStyle: { color: "source", curveness: 0.3 },
    }],
  }), [nodes, edges, categories, colors]);

  return <ReactEChartsCore theme="sla" option={option} style={{ height }} notMerge />;
}
