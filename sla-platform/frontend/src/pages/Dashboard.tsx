import { useState } from "react";
import { Row, Col, Card, Statistic, Typography, Spin, Select, Space } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  CarOutlined,
} from "@ant-design/icons";
import { Table } from "antd";
import { useTranslation } from "react-i18next";
import ReactECharts from "echarts-for-react";
import { useQuery } from "@tanstack/react-query";
import { dashboardsApi } from "../api/dashboards";
import { slaApi } from "../api/sla";
import { formatDuration } from "../utils/format";

export default function Dashboard() {
  const { t } = useTranslation();
  const [days, setDays] = useState(30);

  const { data: overview, isLoading } = useQuery({
    queryKey: ["dashboard-overview", days],
    queryFn: async () => {
      const resp = await dashboardsApi.overview({ days });
      return resp.data;
    },
    refetchInterval: 30_000,
  });

  const { data: timeSeriesData } = useQuery({
    queryKey: ["time-series", days],
    queryFn: async () => {
      const [created, closed, breaches, respTime, resTime] = await Promise.all([
        dashboardsApi.timeSeries({ metric: "tickets_created", granularity: "daily", days }),
        dashboardsApi.timeSeries({ metric: "tickets_closed", granularity: "daily", days }),
        dashboardsApi.timeSeries({ metric: "sla_breaches", granularity: "daily", days }),
        dashboardsApi.timeSeries({ metric: "response_time", granularity: "daily", days }),
        dashboardsApi.timeSeries({ metric: "resolution_time", granularity: "daily", days }),
      ]);
      return { created: created.data.data, closed: closed.data.data, breaches: breaches.data.data, responseTime: respTime.data.data, resolutionTime: resTime.data.data };
    },
    refetchInterval: 60_000,
  });

  const { data: slaTrend } = useQuery({
    queryKey: ["sla-trend", days],
    queryFn: async () => {
      const resp = await dashboardsApi.slaTrend({ days });
      return resp.data.trend;
    },
    refetchInterval: 60_000,
  });

  const { data: queueBreaches } = useQuery({
    queryKey: ["queue-breaches"],
    queryFn: async () => {
      const resp = await slaApi.getQueueBreaches();
      return resp.data.queue_breaches || [];
    },
    refetchInterval: 60_000,
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const kpis = overview || {};

  const kpiCards = [
    { title: t("dashboard.totalTickets"), value: kpis.total_tickets ?? 0, icon: <CarOutlined />, color: "#1677ff" },
    { title: t("dashboard.openTickets"), value: kpis.open_tickets ?? 0, icon: <ClockCircleOutlined />, color: "#faad14" },
    { title: t("dashboard.closedTickets"), value: kpis.closed_tickets ?? 0, icon: <CheckCircleOutlined />, color: "#52c41a" },
    { title: t("dashboard.slaBreachPercent"), value: `${kpis.sla_breach_pct ?? 0}%`, icon: <CloseCircleOutlined />, color: kpis.sla_breach_pct > 15 ? "#ff4d4f" : "#52c41a" },
    { title: t("dashboard.avgResponse"), value: formatDuration(kpis.avg_response_time_seconds), icon: <ClockCircleOutlined />, color: "#1677ff" },
    { title: t("dashboard.avgResolution"), value: formatDuration(kpis.avg_resolution_time_seconds), icon: <CheckCircleOutlined />, color: "#1677ff" },
    { title: t("dashboard.importsProcessed"), value: kpis.imports_processed ?? 0, icon: <CarOutlined />, color: "#722ed1" },
    { title: t("dashboard.slaBreached"), value: kpis.sla_breached ?? 0, icon: <CloseCircleOutlined />, color: "#ff4d4f" },
  ];

  const trendChartOption = {
    tooltip: { trigger: "axis" },
    legend: { data: [t("dashboard.created"), t("dashboard.closed"), t("dashboard.breaches")] },
    xAxis: { type: "category", data: (timeSeriesData?.created || []).map((d: any) => d.period?.slice(0, 10) || "") },
    yAxis: { type: "value", min: 0 },
    series: [
      { name: t("dashboard.created"), type: "line", data: (timeSeriesData?.created || []).map((d: any) => d.count), smooth: true },
      { name: t("dashboard.closed"), type: "line", data: (timeSeriesData?.closed || []).map((d: any) => d.count), smooth: true },
      { name: t("dashboard.breaches"), type: "line", data: (timeSeriesData?.breaches || []).map((d: any) => d.count), smooth: true, lineStyle: { type: "dashed" } },
    ],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  };

  const slaTrendOption = {
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: (slaTrend || []).map((d: any) => d.date?.slice(5) || "") },
    yAxis: { type: "value", min: 0 },
    series: [
      { name: t("dashboard.total"), type: "bar", data: (slaTrend || []).map((d: any) => d.total), itemStyle: { color: "#1677ff" } },
      { name: t("dashboard.breached"), type: "bar", data: (slaTrend || []).map((d: any) => d.breached), itemStyle: { color: "#ff4d4f" } },
    ],
    grid: { left: 50, right: 20, bottom: 30, top: 20 },
  };

  const responseTrendOption = {
    tooltip: { trigger: "axis" },
    title: { text: t("dashboard.slaResponseTime"), left: "center", textStyle: { fontSize: 14 } },
    xAxis: { type: "category", data: (timeSeriesData?.responseTime || []).map((d: any) => d.period?.slice(5, 10) || "") },
    yAxis: { type: "value", min: 0 },
    series: [{ type: "line", data: (timeSeriesData?.responseTime || []).map((d: any) => d.avg_seconds), smooth: true, lineStyle: { color: "#722ed1" }, areaStyle: { color: "rgba(114,46,209,0.1)" } }],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  };

  const resolutionTrendOption = {
    tooltip: { trigger: "axis" },
    title: { text: t("dashboard.slaResolutionTime"), left: "center", textStyle: { fontSize: 14 } },
    xAxis: { type: "category", data: (timeSeriesData?.resolutionTime || []).map((d: any) => d.period?.slice(5, 10) || "") },
    yAxis: { type: "value", min: 0 },
    series: [{ type: "line", data: (timeSeriesData?.resolutionTime || []).map((d: any) => d.avg_seconds), smooth: true, lineStyle: { color: "#13c2c2" }, areaStyle: { color: "rgba(19,194,194,0.1)" } }],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  };

  const queueData = kpis.tickets_by_queue ? Object.entries(kpis.tickets_by_queue).slice(0, 10) : [];
  const queueOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    title: { text: t("dashboard.ticketsByQueue"), left: "center", textStyle: { fontSize: 14 } },
    xAxis: { type: "value", min: 0 },
    yAxis: { type: "category", data: queueData.map(([q]) => q).reverse() },
    series: [{ type: "bar", data: queueData.map(([, c]) => c).reverse(), itemStyle: { color: "#1677ff" } }],
    grid: { left: 120, right: 20, bottom: 20, top: 40 },
  };

  const stateData = kpis.tickets_by_state ? Object.entries(kpis.tickets_by_state) : [];
  const stateOption = {
    tooltip: { trigger: "item" },
    title: { text: t("dashboard.ticketsByState"), left: "center", textStyle: { fontSize: 14 } },
    series: [{
      type: "pie", radius: ["40%", "70%"], center: ["50%", "55%"],
      data: stateData.map(([s, c]) => ({ name: s, value: c })),
      label: { show: true, formatter: "{b}: {c}" },
    }],
  };

  const priorityData = kpis.tickets_by_priority ? Object.entries(kpis.tickets_by_priority) : [];
  const priorityOption = {
    tooltip: { trigger: "item" },
    title: { text: t("dashboard.ticketsByPriority"), left: "center", textStyle: { fontSize: 14 } },
    series: [{
      type: "pie", radius: ["40%", "70%"], center: ["50%", "55%"],
      data: priorityData.map(([p, c]) => ({ name: p || "none", value: c })),
      label: { show: true, formatter: "{b}: {c}" },
    }],
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>{t("dashboard.title")}</Typography.Title>
        <Space>
          <Typography.Text type="secondary">{t("dashboard.period")}</Typography.Text>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={7}>{t("dashboard.last7days")}</Select.Option>
            <Select.Option value={30}>{t("dashboard.last30days")}</Select.Option>
            <Select.Option value={90}>{t("dashboard.last90days")}</Select.Option>
          </Select>
        </Space>
      </div>

      <Row gutter={[12, 12]}>
        {kpiCards.map((kpi) => (
          <Col xs={12} sm={8} md={6} lg={3} key={kpi.title}>
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
          <Card title={t("dashboard.ticketTrends")} size="small">
            <ReactECharts option={trendChartOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t("dashboard.slaBreachTrend")} size="small">
            <ReactECharts option={slaTrendOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={8}>
          <Card title={t("dashboard.slaResponseTime")} size="small">
            <ReactECharts option={responseTrendOption} style={{ height: 220 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t("dashboard.slaResolutionTime")} size="small">
            <ReactECharts option={resolutionTrendOption} style={{ height: 220 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t("dashboard.ticketsByState")} size="small">
            <ReactECharts option={stateOption} style={{ height: 220 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={12}>
          <Card title={t("dashboard.ticketsByQueue")} size="small">
            <ReactECharts option={queueOption} style={{ height: 250 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t("dashboard.ticketsByPriority")} size="small">
            <ReactECharts option={priorityOption} style={{ height: 250 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24}>
          <Card title={t("slaQueue.title")} size="small">
            {queueBreaches && queueBreaches.length > 0 ? (
              <>
                <ReactECharts
                  option={{
                    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
                    legend: { data: [t("slaQueue.breachedResponse"), t("slaQueue.breachedResolution")] },
                    xAxis: { type: "value" },
                    yAxis: { type: "category", data: queueBreaches.map((q: any) => q.queue_name).reverse() },
                    series: [
                      {
                        name: t("slaQueue.breachedResponse"),
                        type: "bar",
                        data: queueBreaches.map((q: any) => q.breached_response).reverse(),
                        itemStyle: { color: "#faad14" },
                      },
                      {
                        name: t("slaQueue.breachedResolution"),
                        type: "bar",
                        data: queueBreaches.map((q: any) => q.breached_resolution).reverse(),
                        itemStyle: { color: "#ff4d4f" },
                      },
                    ],
                    grid: { left: 150, right: 30, bottom: 20, top: 40 },
                  }}
                  style={{ height: Math.max(150, queueBreaches.length * 32) }}
                />
                <Table
                  dataSource={queueBreaches}
                  rowKey="queue_name"
                  size="small"
                  pagination={false}
                  scroll={{ x: true }}
                  columns={[
                    { title: t("slaQueue.queue"), dataIndex: "queue_name", key: "queue_name", width: 180 },
                    { title: t("slaQueue.ticketsTotal"), dataIndex: "tickets_total", key: "tickets_total", width: 120 },
                    { title: t("slaQueue.breachedResponse"), dataIndex: "breached_response", key: "breached_response", width: 150 },
                    { title: t("slaQueue.breachedResolution"), dataIndex: "breached_resolution", key: "breached_resolution", width: 150 },
                    { title: t("slaQueue.avgResponseMin"), dataIndex: "avg_response_minutes", key: "avg_response_minutes", width: 200, render: (v: number) => `${v} мин` },
                    { title: t("slaQueue.avgResolutionHours"), dataIndex: "avg_resolution_hours", key: "avg_resolution_hours", width: 200, render: (v: number) => `${v} ч` },
                  ]}
                />
              </>
            ) : (
              <Typography.Text type="secondary">{t("slaQueue.noData")}</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
