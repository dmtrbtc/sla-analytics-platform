import { useMemo } from "react";
import { Row, Col, Card, Typography, Table, Tag, Spin, Progress } from "antd";
import {
  WarningOutlined, ApartmentOutlined, NodeIndexOutlined,
  ArrowUpOutlined, ArrowDownOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../design/ThemeContext";
import { cardStyle } from "../design/tokens";
import { spacing } from "../design/spacing";
import { queueIntelligenceApi } from "../api/queueIntelligence";

const { Text, Title } = Typography;

export default function ServiceDeskIntelligence() {
  const { colors } = useTheme();

  const sdQ = useQuery({
    queryKey: ["qi-servicedesk"],
    queryFn: () => queueIntelligenceApi.getServiceDeskIntelligence(90),
    refetchInterval: 60000,
  });
  const overviewQ = useQuery({
    queryKey: ["qi-overview-sd"],
    queryFn: () => queueIntelligenceApi.getOverview(90),
  });

  const sd = sdQ.data;
  const downstream = sd?.downstream ?? [];
  const intake = sd?.intake_trend ?? [];

  const totalIntake = sd?.total_sd_intake ?? 0;
  const totalQueues = sd?.total_downstream_queues ?? 0;
  const slowTransfers = downstream.reduce((s: number, q: any) => s + (q.slow_transfers ?? 0), 0);
  const totalTransfers = downstream.reduce((s: number, q: any) => s + (q.tickets_received ?? 0), 0);
  const slowPct = totalTransfers > 0 ? Math.round((slowTransfers / totalTransfers) * 100) : 0;

  const downstreamChartOption = useMemo(() => ({
    backgroundColor: "transparent",
    grid: { left: 100, right: 40, top: 10, bottom: 30 },
    tooltip: { trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    xAxis: { type: "value" as const, axisLabel: { fontSize: 10, color: colors.text.tertiary } },
    yAxis: { type: "category" as const, data: downstream.map((q: any) => q.target_queue).reverse(),
      axisLabel: { fontSize: 10, color: colors.text.secondary } },
    series: [
      { type: "bar" as const, data: downstream.map((q: any) => q.tickets_received).reverse(),
        itemStyle: { color: colors.chart.line[0], borderRadius: [0, 3, 3, 0] }, barMaxWidth: 16,
        label: { show: true, position: "right" as const, fontSize: 9 } },
    ],
  }), [downstream, colors]);

  const transferDelayOption = useMemo(() => ({
    backgroundColor: "transparent",
    grid: { left: 100, right: 40, top: 10, bottom: 30 },
    tooltip: { trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    xAxis: { type: "value" as const, axisLabel: { fontSize: 10, color: colors.text.tertiary, formatter: (v: number) => `${Math.round(v / 60)}h` } },
    yAxis: { type: "category" as const, data: downstream.slice(0, 15).map((q: any) => q.target_queue).reverse(),
      axisLabel: { fontSize: 10, color: colors.text.secondary } },
    series: [{
      type: "bar" as const, data: downstream.slice(0, 15).map((q: any) => Math.round(q.avg_transfer_delay_min / 60)).reverse(),
      itemStyle: { color: (p: any) => p.value > 4 ? colors.severity.crit : p.value > 2 ? colors.severity.warn : colors.severity.ok, borderRadius: [0, 3, 3, 0] },
      barMaxWidth: 16, label: { show: true, position: "right" as const, fontSize: 9, formatter: (p: any) => `${p.value}h` },
    }],
  }), [downstream, colors]);

  const columns = [
    { title: "Target Queue", dataIndex: "target_queue", key: "queue", width: 180 },
    { title: "Tickets", dataIndex: "tickets_received", key: "tickets", width: 60, sorter: (a: any, b: any) => a.tickets_received - b.tickets_received },
    { title: "Slow Transfers", dataIndex: "slow_transfers", key: "slow", width: 60 },
    { title: "Slow %", key: "slow_pct", width: 60, render: (_: any, r: any) => `${Math.round((r.slow_transfers / r.tickets_received) * 100)}%` },
    { title: "Avg Delay", dataIndex: "avg_transfer_delay_min", key: "delay", width: 80, render: (v: number) => `${Math.round(v / 60)}h ${Math.round(v % 60)}m` },
    { title: "Quality", dataIndex: "transfer_quality", key: "quality", width: 60,
      render: (v: string) => <Tag color={v === "poor" ? "error" : "success"} style={{ fontSize: 10, borderRadius: 4, margin: 0 }}>{v}</Tag> },
  ];

  if (sdQ.isLoading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: spacing[4], maxWidth: 1500, margin: "0 auto" }}>
      <Title level={3} style={{ margin: 0, marginBottom: 4, fontSize: 20, fontWeight: 600, color: colors.text.primary }}>
        ServiceDesk Intelligence — Аналитика ServiceDesk
      </Title>
      <Text style={{ fontSize: 12, color: colors.text.tertiary, display: "block", marginBottom: spacing[3] }}>
        40% всех пробитий SLA происходят после передачи из ServiceDesk • {totalQueues} downstream queues • {totalIntake} total tickets
      </Text>

      {/* KPI Cards */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[3] }}>
        {[
          { label: "Total Intake", value: totalIntake, icon: <ArrowUpOutlined />, color: colors.chart.line[0] },
          { label: "Downstream Queues", value: totalQueues, icon: <ApartmentOutlined />, color: colors.severity.warn },
          { label: "Slow Transfer %", value: `${slowPct}%`, icon: <WarningOutlined />, color: slowPct > 30 ? colors.severity.crit : colors.severity.warn },
          { label: "Avg Transfer Delay", value: downstream.length > 0 ? `${Math.round(downstream.reduce((s: number, q: any) => s + q.avg_transfer_delay_min, 0) / downstream.length / 60)}h` : "—", icon: <NodeIndexOutlined />, color: colors.severity.ok },
        ].map((k, i) => (
          <Col span={6} key={i}>
            <div style={{ ...cardStyle, padding: spacing[3], display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 8, background: `${k.color}20`, display: "flex", alignItems: "center", justifyContent: "center", color: k.color, fontSize: 18 }}>{k.icon}</div>
              <div>
                <Text style={{ fontSize: 11, color: colors.text.tertiary, display: "block" }}>{k.label}</Text>
                <Text style={{ fontSize: 20, fontWeight: 600, color: colors.text.primary }}>{k.value}</Text>
              </div>
            </div>
          </Col>
        ))}
      </Row>

      {/* Charts */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[3] }}>
        <Col span={12}>
          <Card size="small" title="Downstream Distribution — Распределение по очередям назначения">
            <ReactEChartsCore option={downstreamChartOption} style={{ height: 300 }} notMerge />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="Transfer Delay by Queue — Задержка передачи по очередям">
            <ReactEChartsCore option={transferDelayOption} style={{ height: 300 }} notMerge />
          </Card>
        </Col>
      </Row>

      {/* Transfer Quality Table */}
      <Card size="small" title="Transfer Quality — Качество передачи тикетов" style={{ marginBottom: 12 }}>
        <Table
          dataSource={downstream}
          columns={columns}
          rowKey="target_queue"
          pagination={{ pageSize: 10, size: "small" }}
          size="small"
          locale={{ emptyText: "Нет данных" }}
        />
      </Card>

      {/* Root Cause Section */}
      <Card size="small" title="Почему ServiceDesk — источник 40% пробитий?">
        <div style={{ padding: spacing[2] }}>
          <div style={{ display: "flex", gap: 16, marginBottom: spacing[2] }}>
            <div style={{ flex: 1, background: `${colors.severity.crit}10`, borderRadius: 8, padding: spacing[2] }}>
              <Text strong style={{ fontSize: 13, color: colors.severity.crit }}>Проблема 1: Долгая передача</Text>
              <Text style={{ fontSize: 12, color: colors.text.secondary, display: "block", marginTop: 4 }}>
                {slowPct}% передач из ServiceDesk занимают более 2 часов. Тикет застревает в очереди до назначения в L2/L3.
              </Text>
            </div>
            <div style={{ flex: 1, background: `${colors.severity.warn}10`, borderRadius: 8, padding: spacing[2] }}>
              <Text strong style={{ fontSize: 13, color: colors.severity.warn }}>Проблема 2: Неправильная маршрутизация</Text>
              <Text style={{ fontSize: 12, color: colors.text.secondary, display: "block", marginTop: 4 }}>
                Тикеты направляются не в ту очередь L2, вызывая повторные передачи (bounces) и потерю времени на перемаршрутизацию.
              </Text>
            </div>
            <div style={{ flex: 1, background: `${colors.severity.crit}10`, borderRadius: 8, padding: spacing[2] }}>
              <Text strong style={{ fontSize: 13, color: colors.severity.crit }}>Проблема 3: Перегрузка L2/L3</Text>
              <Text style={{ fontSize: 12, color: colors.text.secondary, display: "block", marginTop: 4 }}>
                Очереди L2/L3 систематически перегружены. SLA сгорает после передачи — не в ServiceDesk, а в очередях назначения.
              </Text>
            </div>
          </div>
          <Text style={{ fontSize: 12, color: colors.text.tertiary }}>
            Рекомендация: увеличить скорость назначения в L2/L3, внедрить автоматическую маршрутизацию по типу запроса, 
            установить отдельный SLA для очередей с нарушением &gt;50%
          </Text>
        </div>
      </Card>
    </div>
  );
}
