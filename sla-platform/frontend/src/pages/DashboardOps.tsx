import { useState } from "react";
import { Row, Col, Card, Statistic, Typography, Spin, Table, Tag, Space, Select } from "antd";
import {
  WarningOutlined,
  ClockCircleOutlined,
  SwapOutlined,
  QuestionCircleOutlined,
  UnorderedListOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import ReactECharts from "echarts-for-react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "../api/analytics";

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

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const kpis = overview || {};

  const kpiCards = [
    { title: t("analytics.ticketsAtRisk"), value: kpis.tickets_at_risk ?? 0, icon: <WarningOutlined />, color: "#ff4d4f" },
    { title: t("analytics.overloadedQueues"), value: kpis.overloaded_queues ?? 0, icon: <ApartmentOutlined />, color: "#faad14" },
    { title: t("analytics.avgWaitTime"), value: formatDuration(kpis.avg_wait_seconds ?? 0), icon: <ClockCircleOutlined />, color: "#1677ff" },
    { title: t("analytics.avgReassignments"), value: kpis.avg_reassignments ?? 0, icon: <SwapOutlined />, color: "#722ed1" },
    { title: t("analytics.mostProblematicQueue"), value: kpis.most_problematic_queue || "-", icon: <UnorderedListOutlined />, color: "#13c2c2" },
    { title: t("analytics.unownedTickets"), value: kpis.unowned_tickets ?? 0, icon: <QuestionCircleOutlined />, color: "#eb2f96" },
  ];

  const heatmapOption = buildHeatmapOption(heatmapData || []);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>{t("analytics.title")}</Typography.Title>
        <Space>
          <Typography.Text type="secondary">{t("common.period")}</Typography.Text>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={7}>{t("dashboard.last7days")}</Select.Option>
            <Select.Option value={30}>{t("dashboard.last30days")}</Select.Option>
            <Select.Option value={90}>{t("dashboard.last90days")}</Select.Option>
          </Select>
        </Space>
      </div>

      <Row gutter={[12, 12]}>
        {kpiCards.map((kpi) => (
          <Col xs={12} sm={8} md={6} lg={4} key={kpi.title}>
            <Card size="small" hoverable>
              <Statistic
                title={kpi.title}
                value={kpi.value}
                valueStyle={{ color: kpi.color, fontSize: 20 }}
                prefix={kpi.icon}
              />
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
                  { title: t("analytics.queue"), dataIndex: "queue_name", key: "queue_name", width: 120 },
                  { title: t("analytics.avgWaitMinutes"), dataIndex: "avg_wait_minutes", key: "avg_wait_minutes", width: 80, render: (v: number) => `${v} мин` },
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
        <Col xs={24}>
          <Card title={t("analytics.riskTitle")} size="small">
            {slaRisks.length > 0 ? (
              <Table
                dataSource={slaRisks}
                rowKey={(r: any) => `${r.ticket_id}-${r.metric_name}`}
                size="small"
                pagination={{ pageSize: 10, showSizeChanger: false }}
                columns={[
                  { title: t("analytics.ticket"), dataIndex: "ticket_id", key: "ticket_id", width: 80 },
                  { title: t("analytics.queue"), dataIndex: "queue_name", key: "queue_name", width: 150 },
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
      </Row>
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
  if (!data || data.length === 0) {
    return {};
  }

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
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" },
      },
    }],
  };
}
