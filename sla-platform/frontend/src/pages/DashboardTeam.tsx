import { useState } from "react";
import { Typography, Table, Card, Tag, Spin, Select, Space } from "antd";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { dashboardsApi } from "../api/dashboards";

export default function DashboardTeam() {
  const [days, setDays] = useState(90);

  const { data, isLoading } = useQuery({
    queryKey: ["team-analytics", days],
    queryFn: async () => {
      const resp = await dashboardsApi.teamsAnalytics({ days });
      return resp.data.teams;
    },
    refetchInterval: 60_000,
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const teams = data || [];

  const columns = [
    { title: "Team", dataIndex: "team_name", key: "team_name", sorter: (a: any, b: any) => a.team_name.localeCompare(b.team_name) },
    { title: "Prefix", dataIndex: "queue_prefix", key: "queue_prefix" },
    { title: "Tickets", dataIndex: "tickets_handled", key: "tickets_handled", sorter: (a: any, b: any) => a.tickets_handled - b.tickets_handled },
    {
      title: "SLA Breach %", dataIndex: "sla_breach_pct", key: "sla_breach_pct",
      render: (v: number) => <Tag color={v > 15 ? "red" : v > 5 ? "orange" : "green"}>{v}%</Tag>,
      sorter: (a: any, b: any) => a.sla_breach_pct - b.sla_breach_pct,
    },
    {
      title: "Response SLA %", dataIndex: "response_sla_pct", key: "response_sla_pct",
      render: (v: number) => <Tag color={v > 15 ? "red" : v > 5 ? "orange" : "green"}>{100 - v}% pass</Tag>,
    },
    {
      title: "Resolution SLA %", dataIndex: "resolution_sla_pct", key: "resolution_sla_pct",
      render: (v: number) => <Tag color={v > 15 ? "red" : v > 5 ? "orange" : "green"}>{100 - v}% pass</Tag>,
    },
    {
      title: "Avg Ownership", dataIndex: "avg_ownership_time_seconds", key: "avg_ownership_time_seconds",
      render: (v: number) => formatDuration(v),
    },
    {
      title: "Avg Queue Time", dataIndex: "avg_queue_time_seconds", key: "avg_queue_time_seconds",
      render: (v: number) => formatDuration(v),
    },
    { title: "Reassignments", dataIndex: "reassignments", key: "reassignments", sorter: (a: any, b: any) => a.reassignments - b.reassignments },
  ];

  const breachChartOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: teams.map((t: any) => t.team_name) },
    yAxis: { type: "value", name: "Breach %", max: 100 },
    series: [
      { name: "Overall", type: "bar", data: teams.map((t: any) => t.sla_breach_pct), itemStyle: { color: "#1677ff" } },
      { name: "Response", type: "bar", data: teams.map((t: any) => t.response_sla_pct), itemStyle: { color: "#faad14" } },
      { name: "Resolution", type: "bar", data: teams.map((t: any) => t.resolution_sla_pct), itemStyle: { color: "#ff4d4f" } },
    ],
    grid: { left: 60, right: 20, bottom: 30, top: 20 },
    legend: { data: ["Overall", "Response", "Resolution"] },
  };

  const reassignChartOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: teams.map((t: any) => t.team_name) },
    yAxis: { type: "value", name: "Reassignments", min: 0 },
    series: [{ type: "bar", data: teams.map((t: any) => t.reassignments), itemStyle: { color: "#722ed1" } }],
    grid: { left: 60, right: 20, bottom: 30, top: 20 },
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Team Performance Analytics</Typography.Title>
        <Space>
          <Typography.Text type="secondary">Period:</Typography.Text>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={30}>Last 30 days</Select.Option>
            <Select.Option value={90}>Last 90 days</Select.Option>
            <Select.Option value={365}>Last year</Select.Option>
          </Select>
        </Space>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Table
          dataSource={teams}
          columns={columns}
          rowKey="team_id"
          pagination={false}
          size="small"
        />
      </Card>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Card title="SLA Breach Comparison by Team" size="small" style={{ flex: 1, minWidth: 400 }}>
          <ReactECharts option={breachChartOption} style={{ height: 300 }} />
        </Card>
        <Card title="Reassignment Count by Team" size="small" style={{ flex: 1, minWidth: 400 }}>
          <ReactECharts option={reassignChartOption} style={{ height: 300 }} />
        </Card>
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds === 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}
