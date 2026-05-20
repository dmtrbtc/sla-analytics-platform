import { useState, useMemo } from "react";
import {
  Row, Col, Card, Typography, Table, Tag, Spin, Progress, Input, Select, Tabs,
} from "antd";
import {
  SearchOutlined, WarningOutlined, CheckCircleOutlined,
  ClockCircleOutlined, ApartmentOutlined, NodeIndexOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../design/ThemeContext";
import { cardStyle } from "../design/tokens";
import { spacing } from "../design/spacing";
import { queueIntelligenceApi } from "../api/queueIntelligence";

const { Text, Title } = Typography;

export default function QueueForensics() {
  const { colors } = useTheme();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const forensicsQ = useQuery({
    queryKey: ["qi-forensics-full"],
    queryFn: () => queueIntelligenceApi.getQueueForensics(90),
    refetchInterval: 60000,
  });

  const queues = useMemo(() => {
    let qs = forensicsQ.data?.queues ?? [];
    if (search) qs = qs.filter((q: any) => q.queue.toLowerCase().includes(search.toLowerCase()));
    if (severityFilter !== "all") qs = qs.filter((q: any) => q.breach_severity === severityFilter);
    return qs;
  }, [forensicsQ.data, search, severityFilter]);

  const severityColor: Record<string, string> = {
    critical: "#b42333", high: "#b65709", medium: "#b98a1f", low: "#1a7f3b",
  };

  const breachChartOption = useMemo(() => ({
    backgroundColor: "transparent",
    grid: { left: 120, right: 40, top: 10, bottom: 30 },
    tooltip: { trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    xAxis: { type: "value" as const, axisLabel: { fontSize: 10, color: colors.text.tertiary, formatter: "{value}%" },
      splitLine: { lineStyle: { color: colors.divider, type: "dashed" as const } } },
    yAxis: { type: "category" as const, data: queues.slice(0, 15).map((q: any) => q.queue).reverse(),
      axisLabel: { fontSize: 10, color: colors.text.secondary } },
    series: [{
      type: "bar" as const, data: queues.slice(0, 15).map((q: any) => q.breach_pct).reverse(),
      itemStyle: {
        color: (p: any) => {
          const v = p.value;
          return v > 50 ? severityColor.critical : v > 20 ? severityColor.high : v > 10 ? severityColor.medium : severityColor.low;
        },
        borderRadius: [0, 3, 3, 0],
      },
      barMaxWidth: 18,
      label: { show: true, position: "right" as const, fontSize: 10, formatter: (p: any) => `${p.value}%` },
    }],
  }), [queues, colors]);

  const overloadOption = useMemo(() => ({
    backgroundColor: "transparent",
    grid: { left: 120, right: 40, top: 10, bottom: 30 },
    tooltip: { trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    xAxis: { type: "value" as const, axisLabel: { fontSize: 10, color: colors.text.tertiary },
      splitLine: { lineStyle: { color: colors.divider, type: "dashed" as const } } },
    yAxis: { type: "category" as const, data: queues.slice(0, 15).map((q: any) => q.queue).reverse(),
      axisLabel: { fontSize: 10, color: colors.text.secondary } },
    series: [
      {
        name: "Overload Score",
        type: "bar" as const, data: queues.slice(0, 15).map((q: any) => q.overload_score).reverse(),
        itemStyle: { color: "#b65709", borderRadius: [0, 3, 3, 0] }, barMaxWidth: 18,
      },
    ],
  }), [queues, colors]);

  const columns = [
    { title: "Queue", dataIndex: "queue", key: "queue", width: 180, fixed: "left" as const,
      render: (v: string, r: any) => (
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", display: "inline-block",
            background: severityColor[r.breach_severity] || severityColor.low }} />
          <Text style={{ fontSize: 12, color: colors.text.primary, fontWeight: r.systemically_degraded ? 600 : 400 }}>{v}</Text>
        </div>
      ),
    },
    { title: "Tickets", dataIndex: "total_tickets", key: "tickets", width: 60, sorter: (a: any, b: any) => a.total_tickets - b.total_tickets },
    { title: "Breaches", dataIndex: "breaches", key: "breaches", width: 60, sorter: (a: any, b: any) => a.breaches - b.breaches },
    { title: "Breach %", dataIndex: "breach_pct", key: "pct", width: 70, sorter: (a: any, b: any) => a.breach_pct - b.breach_pct,
      render: (v: number) => <Tag color={v > 50 ? "error" : v > 20 ? "warning" : "success"} style={{ fontSize: 10, borderRadius: 4, margin: 0 }}>{v}%</Tag> },
    { title: "Avg Resolution", dataIndex: "avg_resolution_min", key: "res", width: 80, sorter: (a: any, b: any) => a.avg_resolution_min - b.avg_resolution_min,
      render: (v: number) => <Text style={{ fontSize: 11 }}>{Math.round(v / 60)}h {v % 60}m</Text> },
    { title: "Avg Response", dataIndex: "avg_response_min", key: "resp", width: 70, render: (v: number) => `${v}m` },
    { title: "Avg Wait", dataIndex: "avg_wait_min", key: "wait", width: 60, render: (v: number) => `${v}m` },
    { title: "Avg Pause", dataIndex: "avg_pause_min", key: "pause", width: 60, render: (v: number) => `${Math.round(v / 60)}h` },
    { title: "Avg Active", dataIndex: "avg_active_work_min", key: "active", width: 60, render: (v: number) => `${Math.round(v / 60)}h` },
    { title: "Avg Reassign", dataIndex: "avg_reassignments", key: "reassign", width: 65 },
    { title: "High Reassign", dataIndex: "high_reassign_tickets", key: "high_reassign", width: 65 },
    { title: "Overload", dataIndex: "overload_score", key: "score", width: 65, sorter: (a: any, b: any) => a.overload_score - b.overload_score,
      render: (v: number) => (
        <Progress percent={Math.min(100, Math.round(v * 50))} size="small" style={{ margin: 0 }}
          strokeColor={v > 1.5 ? severityColor.critical : v > 0.8 ? severityColor.high : severityColor.low} showInfo={false} />
      ) },
    { title: "Stagnation", dataIndex: "stagnation_label", key: "stag", width: 70,
      render: (v: string) => <Tag color={v === "critical" ? "error" : v === "warning" ? "warning" : "success"} style={{ fontSize: 10, borderRadius: 4 }}>{v}</Tag> },
    { title: "Status", dataIndex: "breach_severity", key: "status", width: 80,
      render: (v: string, r: any) => r.systemically_degraded ? <Tag color="error" style={{ fontSize: 10, borderRadius: 4 }}>DEGRADED</Tag> :
        r.needs_separate_sla ? <Tag color="warning" style={{ fontSize: 10, borderRadius: 4 }}>SLA NEEDED</Tag> :
        <Tag color="success" style={{ fontSize: 10, borderRadius: 4 }}>OK</Tag> },
  ];

  if (forensicsQ.isLoading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: spacing[4], maxWidth: 1500, margin: "0 auto" }}>
      <Title level={3} style={{ margin: 0, marginBottom: 4, fontSize: 20, fontWeight: 600, color: colors.text.primary }}>
        Queue Forensics — Детальная аналитика очередей
      </Title>
      <Text style={{ fontSize: 12, color: colors.text.tertiary, display: "block", marginBottom: spacing[3] }}>
        {forensicsQ.data?.total_queues} queues • {forensicsQ.data?.queues_needing_sla_revision?.length ?? 0} need SLA revision • {forensicsQ.data?.systemically_degraded?.length ?? 0} systemically degraded
      </Text>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: spacing[3], alignItems: "center" }}>
        <Input prefix={<SearchOutlined />} placeholder="Поиск очереди..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: 250, borderRadius: 6, fontSize: 13 }} />
        <Select value={severityFilter} onChange={setSeverityFilter} style={{ width: 140 }}
          options={[
            { value: "all", label: "All Severities" },
            { value: "critical", label: "Critical" },
            { value: "high", label: "High" },
            { value: "medium", label: "Medium" },
            { value: "low", label: "Low" },
          ]} />
        <Text style={{ fontSize: 12, color: colors.text.tertiary }}>{queues.length} queues shown</Text>
      </div>

      {/* Charts */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[3] }}>
        <Col span={12}>
          <Card size="small" title="Breach % by Queue — Пробития SLA по очередям">
            <ReactEChartsCore option={breachChartOption} style={{ height: 400 }} notMerge />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="Overload Score by Queue — Перегрузка очередей">
            <ReactEChartsCore option={overloadOption} style={{ height: 400 }} notMerge />
          </Card>
        </Col>
      </Row>

      {/* Summary Cards */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[3] }}>
        {[
          { label: "Systemically Degraded", value: forensicsQ.data?.systemically_degraded?.length ?? 0, color: severityColor.critical, icon: <WarningOutlined /> },
          { label: "Need SLA Revision", value: forensicsQ.data?.queues_needing_sla_revision?.length ?? 0, color: severityColor.high, icon: <ClockCircleOutlined /> },
          { label: "Avg Breach %", value: `${forensicsQ.data?.avg_breach_pct ?? 0}%`, color: severityColor.medium, icon: <NodeIndexOutlined /> },
          { label: "Stable Queues", value: queues.filter((q: any) => !q.systemically_degraded && !q.needs_separate_sla).length, color: severityColor.low, icon: <CheckCircleOutlined /> },
        ].map((s, i) => (
          <Col span={6} key={i}>
            <div style={{ ...cardStyle, padding: spacing[3], display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 8, background: `${s.color}20`, display: "flex", alignItems: "center", justifyContent: "center", color: s.color, fontSize: 18 }}>{s.icon}</div>
              <div>
                <Text style={{ fontSize: 11, color: colors.text.tertiary, display: "block" }}>{s.label}</Text>
                <Text style={{ fontSize: 20, fontWeight: 600, color: colors.text.primary }}>{s.value}</Text>
              </div>
            </div>
          </Col>
        ))}
      </Row>

      {/* Data Table */}
      <Table
        dataSource={queues}
        columns={columns}
        rowKey="queue"
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t: number) => `${t} queues` }}
        size="small"
        scroll={{ x: 1300 }}
        locale={{ emptyText: "Нет данных" }}
      />
    </div>
  );
}
