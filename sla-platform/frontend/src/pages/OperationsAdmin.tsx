import { useState } from "react";
import { Card, Row, Col, Table, Tag, Typography, Spin, Tabs, Statistic, Descriptions, Badge, Progress, Space } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined, ApiOutlined, NodeIndexOutlined, BugOutlined, DashboardOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { useTheme } from "../design/ThemeContext";
import { cardStyle, cardHeaderStyle, sectionTitle } from "../design/tokens";
import { spacing } from "../design/spacing";
import { typography } from "../design/typography";
import ReactEChartsCore from "echarts-for-react";
import client from "../api/client";

const { Text, Title } = Typography;

export default function OperationsAdmin() {
  const { colors } = useTheme();

  const { data: diagnostics, isLoading: diagLoading } = useQuery({
    queryKey: ["tenant-diagnostics"],
    queryFn: async () => {
      const resp = await client.get("/operations/tenant-diagnostics");
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const { data: queueLag } = useQuery({
    queryKey: ["queue-lag"],
    queryFn: async () => {
      const resp = await client.get("/operations/queue-lag-monitor");
      return resp.data;
    },
    refetchInterval: 15000,
  });

  const { data: slaProfiler } = useQuery({
    queryKey: ["sla-profiler"],
    queryFn: async () => {
      const resp = await client.get("/operations/sla-profiler");
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: liveLogs } = useQuery({
    queryKey: ["live-logs"],
    queryFn: async () => {
      const resp = await client.get("/operations/live-logs", { params: { limit: 50 } });
      return resp.data;
    },
    refetchInterval: 10000,
  });

  if (diagLoading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spin size="large" /></div>;

  const queueLagColumns = [
    { title: "Queue", dataIndex: "queue", key: "queue", render: (v: string) => <Text style={{ fontWeight: 600, fontSize: 13 }}>{v}</Text> },
    { title: "Pending", dataIndex: "pending", key: "pending", render: (v: number) => <Tag>{v}</Tag> },
    { title: "Unprocessed", dataIndex: "unprocessed", key: "unprocessed", render: (v: number) => <Tag color={v > 100 ? "error" : v > 20 ? "warning" : "default"}>{v}</Tag> },
    { title: "Breaches", dataIndex: "breaches", key: "breaches", render: (v: number) => <Tag color={v > 10 ? "error" : "default"}>{v}</Tag> },
    { title: "Lag Score", dataIndex: "lag_score", key: "lag", render: (v: number) => <Progress percent={Math.min(100, v)} size="small" strokeColor={v > 50 ? colors.severity.crit : v > 20 ? colors.severity.warn : colors.severity.ok} showInfo={false} style={{ width: 80 }} /> },
  ];

  const slaProfileColumns = [
    { title: "Metric", dataIndex: "metric", key: "metric" },
    { title: "Count", dataIndex: "count", key: "count" },
    { title: "Avg (s)", dataIndex: "avg_seconds", key: "avg" },
    { title: "P95 (s)", dataIndex: "p95_seconds", key: "p95" },
    { title: "P99 (s)", dataIndex: "p99_seconds", key: "p99" },
  ];

  return (
    <div style={{ padding: spacing[4], maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ marginBottom: spacing[4] }}>
        <Title level={3} style={{ margin: 0, fontSize: 20, fontWeight: 600, color: colors.text.primary }}>Operations Admin Center</Title>
        <Text style={{ fontSize: 12, color: colors.text.tertiary }}>Управление инфраструктурой и мониторинг производительности</Text>
      </div>

      {/* System Health */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        <Col span={6}>
          <div style={cardStyle}>
            <Statistic title="Database" value={diagnostics?.db?.healthy ? "Healthy" : "Error"} valueStyle={{ color: diagnostics?.db?.healthy ? colors.severity.ok : colors.severity.crit, fontSize: 14 }} prefix={diagnostics?.db?.healthy ? <CheckCircleOutlined /> : <CloseCircleOutlined />} />
            <Text style={{ fontSize: 11, color: colors.text.tertiary }}>Size: {diagnostics?.db?.size_mb ?? "?"} MB</Text>
          </div>
        </Col>
        <Col span={6}>
          <div style={cardStyle}>
            <Statistic title="Redis Cache" value={diagnostics?.cache?.healthy ? "Healthy" : "Offline"} valueStyle={{ color: diagnostics?.cache?.healthy ? colors.severity.ok : colors.severity.crit, fontSize: 14 }} prefix={diagnostics?.cache?.healthy ? <CheckCircleOutlined /> : <CloseCircleOutlined />} />
            <Text style={{ fontSize: 11, color: colors.text.tertiary }}>Memory: {diagnostics?.cache?.used_memory_mb ?? "?"} MB</Text>
          </div>
        </Col>
        <Col span={6}>
          <div style={cardStyle}>
            <Statistic title="Active Workers" value={diagnostics?.workers?.active_queues?.length ?? 0} valueStyle={{ fontSize: 14 }} prefix={<NodeIndexOutlined />} />
            <Text style={{ fontSize: 11, color: colors.text.tertiary }}>Queues: {diagnostics?.workers?.active_queues?.join(", ") ?? "—"}</Text>
          </div>
        </Col>
        <Col span={6}>
          <div style={cardStyle}>
            <Statistic title="SLA Metrics (24h)" value={diagnostics?.sla_profiler?.total_metrics_24h ?? 0} valueStyle={{ fontSize: 14 }} prefix={<DatabaseOutlined />} />
            <Text style={{ fontSize: 11, color: colors.text.tertiary }}>Avg age: {diagnostics?.sla_profiler?.avg_age_seconds ?? 0}s</Text>
          </div>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        <Col span={16}>
          <div style={cardStyle}>
            <div style={cardHeaderStyle as React.CSSProperties}><ApiOutlined style={{ marginRight: 6 }} /> Queue Lag Monitor</div>
            <Table dataSource={queueLag?.queues ?? []} columns={queueLagColumns} rowKey="queue" pagination={false} size="small" locale={{ emptyText: "No queue data" }} />
          </div>
        </Col>
        <Col span={8}>
          <div style={cardStyle}>
            <div style={cardHeaderStyle as React.CSSProperties}><BugOutlined style={{ marginRight: 6 }} /> SLA Profiler</div>
            <Table dataSource={slaProfiler?.profiles ?? []} columns={slaProfileColumns} rowKey="metric" pagination={false} size="small" locale={{ emptyText: "No profile data" }} />
          </div>
        </Col>
      </Row>

      {/* Live Logs */}
      <div style={cardStyle}>
        <div style={cardHeaderStyle as React.CSSProperties}><DashboardOutlined style={{ marginRight: 6 }} /> Live Audit Log</div>
        <Table
          dataSource={liveLogs?.logs ?? []}
          columns={[
            { title: "Time", dataIndex: "created_at", key: "time", width: 160, render: (v: string) => <Text style={{ fontSize: 11, fontFamily: typography.fontMono }}>{v ? new Date(v).toLocaleTimeString() : "—"}</Text> },
            { title: "Action", dataIndex: "action", key: "action", width: 140 },
            { title: "Resource", dataIndex: "resource_type", key: "resource", width: 100 },
            { title: "User", dataIndex: "user_id", key: "user", width: 100, render: (v: string) => <Text style={{ fontSize: 11 }}>{v?.slice(0, 8)}</Text> },
            { title: "Details", dataIndex: "details", key: "details", ellipsis: true },
          ]}
          rowKey={(r: any) => r.id || r.created_at}
          pagination={{ pageSize: 10, size: "small" }}
          size="small"
          locale={{ emptyText: "No log entries" }}
        />
      </div>
    </div>
  );
}
