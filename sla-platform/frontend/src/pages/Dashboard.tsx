import { useState } from "react";
import { Row, Col, Card, Statistic, Typography, Spin, DatePicker, Select, Space, Tag } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  CarOutlined,
} from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import { useQuery } from "@tanstack/react-query";
import { dashboardsApi } from "../api/dashboards";
import dayjs from "dayjs";

const { RangePicker } = DatePicker;

export default function Dashboard() {
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
      const resp = await dashboardsApi.slaTrend();
      return resp.data.trend;
    },
    refetchInterval: 60_000,
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;

  const kpis = overview || {};

  const kpiCards = [
    { title: "Total Tickets", value: kpis.total_tickets ?? 0, icon: <CarOutlined />, color: "#1677ff" },
    { title: "Open Tickets", value: kpis.open_tickets ?? 0, icon: <ClockCircleOutlined />, color: "#faad14" },
    { title: "Closed Tickets", value: kpis.closed_tickets ?? 0, icon: <CheckCircleOutlined />, color: "#52c41a" },
    { title: "SLA Breach %", value: `${kpis.sla_breach_pct ?? 0}%`, icon: <CloseCircleOutlined />, color: kpis.sla_breach_pct > 15 ? "#ff4d4f" : "#52c41a" },
    { title: "Avg Response", value: formatDuration(kpis.avg_response_time_seconds), icon: <ClockCircleOutlined />, color: "#1677ff" },
    { title: "Avg Resolution", value: formatDuration(kpis.avg_resolution_time_seconds), icon: <CheckCircleOutlined />, color: "#1677ff" },
    { title: "Imports Processed", value: kpis.imports_processed ?? 0, icon: <CarOutlined />, color: "#722ed1" },
    { title: "SLA Breached", value: kpis.sla_breached ?? 0, icon: <CloseCircleOutlined />, color: "#ff4d4f" },
  ];

  const trendChartOption = {
    tooltip: { trigger: "axis" },
    legend: { data: ["Created", "Closed", "Breaches"] },
    xAxis: { type: "category", data: (timeSeriesData?.created || []).map((d: any) => d.period?.slice(0, 10) || "") },
    yAxis: { type: "value", min: 0 },
    series: [
      { name: "Created", type: "line", data: (timeSeriesData?.created || []).map((d: any) => d.count), smooth: true },
      { name: "Closed", type: "line", data: (timeSeriesData?.closed || []).map((d: any) => d.count), smooth: true },
      { name: "Breaches", type: "line", data: (timeSeriesData?.breaches || []).map((d: any) => d.count), smooth: true, lineStyle: { type: "dashed" } },
    ],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  };

  const slaTrendOption = {
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: (slaTrend || []).map((d: any) => d.date?.slice(5) || "") },
    yAxis: { type: "value", min: 0 },
    series: [
      { name: "Total", type: "bar", data: (slaTrend || []).map((d: any) => d.total), itemStyle: { color: "#1677ff" } },
      { name: "Breached", type: "bar", data: (slaTrend || []).map((d: any) => d.breached), itemStyle: { color: "#ff4d4f" } },
    ],
    grid: { left: 50, right: 20, bottom: 30, top: 20 },
  };

  const responseTrendOption = {
    tooltip: { trigger: "axis" },
    title: { text: "Response Time Trend (avg seconds)", left: "center", textStyle: { fontSize: 14 } },
    xAxis: { type: "category", data: (timeSeriesData?.responseTime || []).map((d: any) => d.period?.slice(5, 10) || "") },
    yAxis: { type: "value", min: 0 },
    series: [{ type: "line", data: (timeSeriesData?.responseTime || []).map((d: any) => d.avg_seconds), smooth: true, lineStyle: { color: "#722ed1" }, areaStyle: { color: "rgba(114,46,209,0.1)" } }],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  };

  const resolutionTrendOption = {
    tooltip: { trigger: "axis" },
    title: { text: "Resolution Time Trend (avg seconds)", left: "center", textStyle: { fontSize: 14 } },
    xAxis: { type: "category", data: (timeSeriesData?.resolutionTime || []).map((d: any) => d.period?.slice(5, 10) || "") },
    yAxis: { type: "value", min: 0 },
    series: [{ type: "line", data: (timeSeriesData?.resolutionTime || []).map((d: any) => d.avg_seconds), smooth: true, lineStyle: { color: "#13c2c2" }, areaStyle: { color: "rgba(19,194,194,0.1)" } }],
    grid: { left: 50, right: 20, bottom: 30, top: 40 },
  };

  const queueData = kpis.tickets_by_queue ? Object.entries(kpis.tickets_by_queue).slice(0, 10) : [];
  const queueOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    title: { text: "Tickets by Queue", left: "center", textStyle: { fontSize: 14 } },
    xAxis: { type: "value", min: 0 },
    yAxis: { type: "category", data: queueData.map(([q]) => q).reverse() },
    series: [{ type: "bar", data: queueData.map(([, c]) => c).reverse(), itemStyle: { color: "#1677ff" } }],
    grid: { left: 120, right: 20, bottom: 20, top: 40 },
  };

  const stateData = kpis.tickets_by_state ? Object.entries(kpis.tickets_by_state) : [];
  const stateOption = {
    tooltip: { trigger: "item" },
    title: { text: "Tickets by State", left: "center", textStyle: { fontSize: 14 } },
    series: [{
      type: "pie", radius: ["40%", "70%"], center: ["50%", "55%"],
      data: stateData.map(([s, c]) => ({ name: s, value: c })),
      label: { show: true, formatter: "{b}: {c}" },
    }],
  };

  const priorityData = kpis.tickets_by_priority ? Object.entries(kpis.tickets_by_priority) : [];
  const priorityOption = {
    tooltip: { trigger: "item" },
    title: { text: "Tickets by Priority", left: "center", textStyle: { fontSize: 14 } },
    series: [{
      type: "pie", radius: ["40%", "70%"], center: ["50%", "55%"],
      data: priorityData.map(([p, c]) => ({ name: p || "none", value: c })),
      label: { show: true, formatter: "{b}: {c}" },
    }],
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Dashboard</Typography.Title>
        <Space>
          <Typography.Text type="secondary">Period:</Typography.Text>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={7}>Last 7 days</Select.Option>
            <Select.Option value={30}>Last 30 days</Select.Option>
            <Select.Option value={90}>Last 90 days</Select.Option>
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
          <Card title="Ticket and Breach Trends" size="small">
            <ReactECharts option={trendChartOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="SLA Breach Trend" size="small">
            <ReactECharts option={slaTrendOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={8}>
          <Card title="SLA Response Time" size="small">
            <ReactECharts option={responseTrendOption} style={{ height: 220 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="SLA Resolution Time" size="small">
            <ReactECharts option={resolutionTrendOption} style={{ height: 220 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Tickets by State" size="small">
            <ReactECharts option={stateOption} style={{ height: 220 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={12}>
          <Card title="Tickets by Queue" size="small">
            <ReactECharts option={queueOption} style={{ height: 250 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Tickets by Priority" size="small">
            <ReactECharts option={priorityOption} style={{ height: 250 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds === 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}
