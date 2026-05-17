import { useState } from "react";
import { Typography, Table, Card, Tag, Spin, Select, Space } from "antd";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { dashboardsApi } from "../api/dashboards";
import { formatDuration } from "../utils/format";

export default function DashboardTeam() {
  const { t } = useTranslation();
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
    { title: t("teamDashboard.team"), dataIndex: "team_name", key: "team_name", sorter: (a: any, b: any) => a.team_name.localeCompare(b.team_name) },
    { title: t("teamDashboard.prefix"), dataIndex: "queue_prefix", key: "queue_prefix" },
    { title: t("teamDashboard.tickets"), dataIndex: "tickets_handled", key: "tickets_handled", sorter: (a: any, b: any) => a.tickets_handled - b.tickets_handled },
    {
      title: t("teamDashboard.slaBreachPercent"), dataIndex: "sla_breach_pct", key: "sla_breach_pct",
      render: (v: number) => <Tag color={v > 15 ? "red" : v > 5 ? "orange" : "green"}>{v}%</Tag>,
      sorter: (a: any, b: any) => a.sla_breach_pct - b.sla_breach_pct,
    },
    {
      title: t("teamDashboard.responseSlaPct"), dataIndex: "response_sla_pct", key: "response_sla_pct",
      render: (v: number) => <Tag color={v > 15 ? "red" : v > 5 ? "orange" : "green"}>{100 - v}% pass</Tag>,
    },
    {
      title: t("teamDashboard.resolutionSlaPct"), dataIndex: "resolution_sla_pct", key: "resolution_sla_pct",
      render: (v: number) => <Tag color={v > 15 ? "red" : v > 5 ? "orange" : "green"}>{100 - v}% pass</Tag>,
    },
    {
      title: t("teamDashboard.avgOwnership"), dataIndex: "avg_ownership_time_seconds", key: "avg_ownership_time_seconds",
      render: (v: number) => formatDuration(v),
    },
    {
      title: t("teamDashboard.avgQueueTime"), dataIndex: "avg_queue_time_seconds", key: "avg_queue_time_seconds",
      render: (v: number) => formatDuration(v),
    },
    { title: t("teamDashboard.reassignments"), dataIndex: "reassignments", key: "reassignments", sorter: (a: any, b: any) => a.reassignments - b.reassignments },
  ];

  const breachChartOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: teams.map((t: any) => t.team_name) },
    yAxis: { type: "value", name: "Breach %", max: 100 },
    series: [
      { name: t("teamDashboard.overall"), type: "bar", data: teams.map((t: any) => t.sla_breach_pct), itemStyle: { color: "#1677ff" } },
      { name: t("teamDashboard.response"), type: "bar", data: teams.map((t: any) => t.response_sla_pct), itemStyle: { color: "#faad14" } },
      { name: t("teamDashboard.resolution"), type: "bar", data: teams.map((t: any) => t.resolution_sla_pct), itemStyle: { color: "#ff4d4f" } },
    ],
    grid: { left: 60, right: 20, bottom: 30, top: 20 },
    legend: { data: [t("teamDashboard.overall"), t("teamDashboard.response"), t("teamDashboard.resolution")] },
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
        <Typography.Title level={4} style={{ margin: 0 }}>{t("teamDashboard.title")}</Typography.Title>
        <Space>
          <Typography.Text type="secondary">{t("teamDashboard.period")}</Typography.Text>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={30}>{t("teamDashboard.last30days")}</Select.Option>
            <Select.Option value={90}>{t("teamDashboard.last90days")}</Select.Option>
            <Select.Option value={365}>{t("teamDashboard.lastYear")}</Select.Option>
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
        <Card title={t("teamDashboard.slaBreachComparison")} size="small" style={{ flex: 1, minWidth: 400 }}>
          <ReactECharts option={breachChartOption} style={{ height: 300 }} />
        </Card>
        <Card title={t("teamDashboard.reassignmentCount")} size="small" style={{ flex: 1, minWidth: 400 }}>
          <ReactECharts option={reassignChartOption} style={{ height: 300 }} />
        </Card>
      </div>
    </div>
  );
}
