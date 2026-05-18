import { useState } from "react";
import { Row, Col, Card, Statistic, Typography, Spin, Table, Tag, Space, Select, Button, message, Progress } from "antd";
import {
  WarningOutlined,
  ClockCircleOutlined,
  SwapOutlined,
  QuestionCircleOutlined,
  UnorderedListOutlined,
  ApartmentOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  FireOutlined,
  TeamOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import ReactECharts from "echarts-for-react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../api/analytics";
import { dashboardsApi } from "../api/dashboards";

const WEEKDAYS_RU = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];

export default function DashboardOps() {
  const { t } = useTranslation();
  const [days, setDays] = useState(30);

  const { data: overview, isLoading } = useQuery({
    queryKey: ["analytics-overview", days],
    queryFn: async () => {
      const resp = await analyticsApi.overview({ days });
      return resp.data;
    },
    refetchInterval: 30_000,
  });

  const { data: dashOverview } = useQuery({
    queryKey: ["dash-overview"],
    queryFn: async () => {
      const resp = await dashboardsApi.overview();
      return resp.data;
    },
    refetchInterval: 60_000,
  });

  const { data: heatmapData } = useQuery({
    queryKey: ["analytics-heatmap", days],
    queryFn: async () => {
      const resp = await analyticsApi.queueHeatmap({ days });
      return resp.data.heatmap || [];
    },
    refetchInterval: 60_000,
  });

  const { data: bottlenecks } = useQuery({
    queryKey: ["analytics-bottlenecks"],
    queryFn: async () => {
      const resp = await analyticsApi.bottlenecks();
      return resp.data.bottlenecks || [];
    },
    refetchInterval: 60_000,
  });

  const { data: slaRisks } = useQuery({
    queryKey: ["analytics-sla-risks"],
    queryFn: async () => {
      const resp = await analyticsApi.slaRisks();
      return resp.data.risks || [];
    },
    refetchInterval: 30_000,
  });

  const { data: agentWorkload } = useQuery({
    queryKey: ["agent-workload"],
    queryFn: async () => {
      const resp = await dashboardsApi.agentWorkload();
      return resp.data.agents || [];
    },
    refetchInterval: 120_000,
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const kpis = overview || {};
  const dash = dashOverview || {};

  const kpiCards = [
    { title: t("analytics.ticketsAtRisk"), value: kpis.tickets_at_risk ?? 0, icon: <WarningOutlined />, color: "#ff4d4f" },
    { title: t("analytics.overloadedQueues"), value: kpis.overloaded_queues ?? 0, icon: <ApartmentOutlined />, color: "#faad14" },
    { title: t("analytics.avgWaitTime"), value: formatDuration(kpis.avg_wait_seconds ?? 0), icon: <ClockCircleOutlined />, color: "#1677ff" },
    { title: t("analytics.avgReassignments"), value: kpis.avg_reassignments ?? 0, icon: <SwapOutlined />, color: "#722ed1" },
    { title: t("analytics.mostProblematicQueue"), value: kpis.most_problematic_queue || "-", icon: <UnorderedListOutlined />, color: "#13c2c2" },
    { title: t("analytics.unownedTickets"), value: kpis.unowned_tickets ?? 0, icon: <QuestionCircleOutlined />, color: "#eb2f96" },
  ];

  const dashKpiCards = [
    { title: t("dashboard.openTickets"), value: dash.open_tickets ?? 0, icon: <DashboardOutlined />, color: "#1677ff" },
    { title: t("dashboard.slaBreachPercent"), value: `${dash.sla_breach_pct ?? 0}%`, icon: <FireOutlined />, color: "#ff4d4f" },
    { title: t("dashboard.avgResponse"), value: formatDuration(dash.avg_response_time_seconds ?? 0), icon: <ClockCircleOutlined />, color: "#52c41a" },
    { title: t("dashboard.avgResolution"), value: formatDuration(dash.avg_resolution_time_seconds ?? 0), icon: <CheckCircleOutlined />, color: "#722ed1" },
  ];

  const heatmapOption = buildHeatmapOption(heatmapData || []);

  const exportCSV = () => {
    try {
      const bottlenecksData = bottlenecks || [];
      const risksData = slaRisks || [];
      let csv = "\uFEFF";
      csv += `${t("analytics.bottleneckTitle")}\n`;
      csv += `${t("analytics.queue")},${t("analytics.avgWaitMinutes")},${t("analytics.slaPct")},${t("analytics.riskScore")}\n`;
      for (const b of bottlenecksData) {
        csv += `${b.queue_name},${b.avg_wait_minutes},${b.sla_pct},${b.risk_score}\n`;
      }
      csv += `\n${t("analytics.riskTitle")}\n`;
      csv += `${t("analytics.ticket")},${t("analytics.queue")},${t("analytics.slaUsage")},${t("analytics.riskLevel")}\n`;
      for (const r of risksData) {
        csv += `${r.ticket_id},${r.queue_name},${r.risk_score}%,${r.risk_level}\n`;
      }
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analitika_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(t("common.download"));
    } catch {
      message.error(t("reports.failedToDownload"));
    }
  };

  const topBottleneck = bottlenecks?.[0];
  const worstAgent = agentWorkload?.length ? [...agentWorkload].sort((a: any, b: any) => b.open_tickets - a.open_tickets)[0] : null;
  const topAgent = agentWorkload?.length ? [...agentWorkload].sort((a: any, b: any) => b.tickets_handled - a.tickets_handled)[0] : null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>{t("analytics.title")}</Typography.Title>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={exportCSV}>{t("common.download")}</Button>
          <Typography.Text type="secondary">{t("common.period")}</Typography.Text>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={7}>{t("dashboard.last7days")}</Select.Option>
            <Select.Option value={30}>{t("dashboard.last30days")}</Select.Option>
            <Select.Option value={90}>{t("dashboard.last90days")}</Select.Option>
          </Select>
        </Space>
      </div>

      <Row gutter={[12, 12]}>
        {dashKpiCards.map((kpi) => (
          <Col xs={12} sm={6} key={kpi.title}>
            <Card size="small" hoverable>
              <Statistic title={kpi.title} value={kpi.value} valueStyle={{ color: kpi.color, fontSize: 20 }} prefix={kpi.icon} />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        {kpiCards.map((kpi) => (
          <Col xs={12} sm={8} md={6} lg={4} key={kpi.title}>
            <Card size="small" hoverable>
              <Statistic title={kpi.title} value={kpi.value} valueStyle={{ color: kpi.color, fontSize: 20 }} prefix={kpi.icon} />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title={t("analytics.heatmapTitle")} size="small">
            {heatmapData.length > 0 ? (
              <ReactECharts option={heatmapOption} style={{ height: 320 }} />
            ) : (
              <Typography.Text type="secondary">{t("common.noData")}</Typography.Text>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t("analytics.bottleneckTitle")} size="small" style={{ maxHeight: 400, overflow: "auto" }}>
            {bottlenecks.length > 0 ? (
              <Table
                dataSource={bottlenecks.slice(0, 10)}
                rowKey="queue_name"
                size="small"
                pagination={false}
                columns={[
                  { title: t("analytics.queue"), dataIndex: "queue_name", key: "queue_name", width: 120, ellipsis: true },
                  { title: t("analytics.avgWaitMinutes"), dataIndex: "avg_wait_minutes", key: "avg_wait_minutes", width: 80, render: (v: number) => `${Math.round(v)} мин` },
                  { title: t("analytics.slaPct"), dataIndex: "sla_pct", key: "sla_pct", width: 70, render: (v: number) => `${v}%` },
                  { title: t("analytics.riskScore"), dataIndex: "risk_score", key: "risk_score", width: 70, render: (v: number) => <Tag color={v > 70 ? "red" : v > 40 ? "orange" : "green"}>{v}</Tag> },
                ]}
                scroll={{ y: 280 }}
              />
            ) : (
              <Typography.Text type="secondary">{t("common.noData")}</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={12}>
          <Card title={t("analytics.riskTitle")} size="small">
            {slaRisks.length > 0 ? (
              <Table
                dataSource={slaRisks}
                rowKey={(r: any) => `${r.ticket_id}-${r.metric_name}`}
                size="small"
                pagination={{ pageSize: 10, showSizeChanger: false }}
                columns={[
                  { title: t("analytics.ticket"), dataIndex: "ticket_id", key: "ticket_id", width: 80 },
                  { title: t("analytics.queue"), dataIndex: "queue_name", key: "queue_name", width: 150, ellipsis: true },
                  { title: t("analytics.slaUsage"), dataIndex: "risk_score", key: "risk_score", width: 120, render: (_: any, r: any) => `${r.risk_score}%` },
                  { title: t("analytics.remainingTime"), dataIndex: "elapsed_seconds", key: "remaining", width: 150, render: (v: number) => formatDuration(v) },
                  { title: t("analytics.riskLevel"), dataIndex: "risk_level", key: "risk_level", width: 120, render: (v: string) => {
                    const colors: Record<string, string> = { critical: "red", high: "orange", medium: "gold", low: "green" };
                    return <Tag color={colors[v] || "default"}>{t(`analytics.riskLevel_${v}`)}</Tag>;
                  }},
                ]}
              />
            ) : (
              <Typography.Text type="secondary">{t("analytics.noRisks")}</Typography.Text>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={<><TeamOutlined /> {t("dashboard.slaBreachPercent")} / {t("common.owner")}</>} size="small">
            {agentWorkload?.length > 0 ? (
              <Table
                dataSource={agentWorkload.slice(0, 10)}
                rowKey="owner"
                size="small"
                pagination={false}
                scroll={{ y: 250 }}
                columns={[
                  { title: t("common.owner"), dataIndex: "owner", key: "owner", width: 100 },
                  { title: t("dashboard.openTickets"), dataIndex: "open_tickets", key: "open", width: 70, sorter: (a: any, b: any) => a.open_tickets - b.open_tickets },
                  { title: t("common.total"), dataIndex: "tickets_handled", key: "handled", width: 70 },
                  { title: t("common.duration"), dataIndex: "avg_ownership_seconds", key: "avg_own", width: 120, render: (v: number) => formatDuration(v) },
                ]}
              />
            ) : (
              <Typography.Text type="secondary">{t("common.noData")}</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      {topBottleneck && (
        <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
          <Col xs={24} sm={8}>
            <Card size="small" hoverable>
              <Statistic
                title={`${t("analytics.mostProblematicQueue")} — ${topBottleneck.queue_name}`}
                value={`${topBottleneck.sla_pct}% SLA`}
                valueStyle={{ color: topBottleneck.sla_pct < 80 ? "#ff4d4f" : "#faad14", fontSize: 18 }}
                prefix={<FireOutlined />}
              />
              <Space style={{ marginTop: 8 }}>
                <Typography.Text type="secondary">{t("analytics.avgWaitMinutes")}: {Math.round(topBottleneck.avg_wait_minutes)} мин</Typography.Text>
                <Typography.Text type="secondary">| {t("analytics.riskScore")}: {topBottleneck.risk_score}</Typography.Text>
              </Space>
            </Card>
          </Col>
          {worstAgent && (
            <Col xs={24} sm={8}>
              <Card size="small" hoverable>
                <Statistic
                  title={`${t("dashboard.openTickets")} — ${worstAgent.owner}`}
                  value={worstAgent.open_tickets}
                  valueStyle={{ color: "#ff4d4f", fontSize: 18 }}
                  prefix={<TeamOutlined />}
                />
                <Space style={{ marginTop: 8 }}>
                  <Typography.Text type="secondary">{t("common.total")}: {worstAgent.tickets_handled}</Typography.Text>
                  <Typography.Text type="secondary">| {t("common.duration")}: {formatDuration(worstAgent.avg_ownership_seconds)}</Typography.Text>
                </Space>
              </Card>
            </Col>
          )}
          {topAgent && (
            <Col xs={24} sm={8}>
              <Card size="small" hoverable>
                <Statistic
                  title={`${t("common.total")} — ${topAgent.owner}`}
                  value={topAgent.tickets_handled}
                  valueStyle={{ color: "#52c41a", fontSize: 18 }}
                  prefix={<CheckCircleOutlined />}
                />
                <Space style={{ marginTop: 8 }}>
                  <Typography.Text type="secondary">{t("dashboard.openTickets")}: {topAgent.open_tickets}</Typography.Text>
                  <Typography.Text type="secondary">| {t("common.duration")}: {formatDuration(topAgent.avg_ownership_seconds)}</Typography.Text>
                </Space>
              </Card>
            </Col>
          )}
        </Row>
      )}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0 сек";
  if (seconds < 60) return `${Math.round(seconds)} сек`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} мин`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}

function buildHeatmapOption(data: any[]) {
  if (!data || data.length === 0) return {};

  const queues = [...new Set(data.map((d: any) => d.queue))].sort();
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const weekdays = [0, 1, 2, 3, 4, 5, 6];
  const maxBreach = Math.max(...data.map((d: any) => d.breach_count), 1);

  const values: [number, number, number][] = [];
  for (const d of data) {
    const qi = queues.indexOf(d.queue);
    if (qi === -1) continue;
    const hi = hours.indexOf(d.hour);
    const wi = weekdays.indexOf(d.weekday);
    if (hi === -1 || wi === -1) continue;
    values.push([hi, wi, d.breach_count]);
  }

  return {
    tooltip: {
      formatter: (p: any) => {
        const h = p.value[0];
        const w = p.value[1];
        const v = p.value[2];
        return `${WEEKDAYS_RU[w]} ${h}:00<br/>Нарушений: ${v}`;
      },
    },
    grid: { left: 60, right: 30, bottom: 40, top: 10 },
    xAxis: {
      type: "category",
      data: hours.map((h) => `${h}:00`),
      splitArea: { show: true },
      axisLabel: { interval: 3, fontSize: 10 },
    },
    yAxis: {
      type: "category",
      data: WEEKDAYS_RU,
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: maxBreach,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#f0f9ff", "#bae6fd", "#38bdf8", "#0284c7", "#0c4a6e"] },
    },
    series: [{
      type: "heatmap",
      data: values,
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
    }],
  };
}
