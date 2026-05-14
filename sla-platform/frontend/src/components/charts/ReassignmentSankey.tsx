import ReactECharts from "echarts-for-react";

interface SankeyNode {
  name: string;
}

interface SankeyEdge {
  source: string;
  target: string;
  value: number;
}

interface ReassignmentSankeyProps {
  nodes: SankeyNode[];
  edges: SankeyEdge[];
}

export default function ReassignmentSankey({ nodes, edges }: ReassignmentSankeyProps) {
  const option = {
    title: { text: "Reassignment Flow", left: "center" },
    tooltip: { trigger: "item", triggerOn: "mousemove" },
    series: [
      {
        type: "sankey",
        layout: "none",
        emphasis: { focus: "adjacency" },
        nodeAlign: "left",
        data: nodes,
        links: edges,
        lineStyle: { color: "gradient", curveness: 0.5 },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
