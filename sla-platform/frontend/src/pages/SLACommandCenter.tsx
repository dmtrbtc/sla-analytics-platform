import { useMemo, useState } from "react";
import {
  Row, Col, Tag, Spin, Typography, Badge, Table, Progress, Card, Tabs, Tooltip,
} from "antd";
import {
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ArrowUpOutlined, ArrowDownOutlined, ThunderboltOutlined,
  TeamOutlined, DashboardOutlined, AlertOutlined, BranchesOutlined,
  ApartmentOutlined, HeatMapOutlined, NodeIndexOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../design/ThemeContext";
import { cardStyle, cardHeaderStyle, kpiCardStyle, kpiValueStyle, kpiLabelStyle } from "../design/tokens";
import { spacing } from "../design/spacing";
import { queueIntelligenceApi } from "../api/queueIntelligence";
import { useTimeScope } from "../contexts/TimeScopeContext";

const { Text, Title } = Typography;

interface KpiData {
  label: string; value: string | number; trend?: number;
  status?: "ok" | "warn" | "crit"; icon?: React.ReactNode;
}

function KpiCard({ label, value, trend, status = "ok", icon }: KpiData) {
  const { colors } = useTheme();
  const stripColor = status === "ok" ? colors.severity.ok : status === "warn" ? colors.severity.warn : colors.severity.crit;
  return (
    <div style={{ ...kpiCardStyle, cursor: "default" }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 4px 12px rgba(27,31,35,0.07)"; e.currentTarget.style.borderColor = colors.border; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 1px 3px rgba(27,31,35,0.03)"; e.currentTarget.style.borderColor = colors.border; }}>
      <div style={{ height: 3, background: stripColor, margin: "-13px -13px 8px -13px", borderRadius: "8px 8px 0 0" }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Text style={{ ...kpiLabelStyle, marginBottom: 2 }}>{label}</Text>
        {icon && <span style={{ color: colors.text.tertiary, fontSize: 14 }}>{icon}</span>}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ ...kpiValueStyle, fontSize: "22px" }}>{value}</span>
        {trend !== undefined && (
          <Tag color={trend >= 0 ? "success" : "error"} style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", borderRadius: 4, margin: 0 }}>
            {trend >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {Math.abs(trend)}%
          </Tag>
        )}
      </div>
    </div>
  );
}

const severityColor: Record<string, string> = {
  critical: "#b42333", high: "#b65709",
  medium: "#b98a1f", low: "#1a7f3b", normal: "#5b6873",
};

export default function SLACommandCenter() {
  const { colors } = useTheme();
  const [now] = useState(new Date());
  const { toParams } = useTimeScope();
  const scopeParams = toParams();
  // Cache-bust queries when scope changes; include scopeParams in queryKey.
  const scopeKey = JSON.stringify(scopeParams);

  const overviewQ = useQuery({
    queryKey: ["qi-overview", scopeKey],
    queryFn: () => queueIntelligenceApi.getOverview(30, scopeParams),
    refetchInterval: 30000,
  });
  const flowMapQ = useQuery({
    queryKey: ["qi-flowmap", scopeKey],
    queryFn: () => queueIntelligenceApi.getQueueFlowMap(30, scopeParams),
    refetchInterval: 60000,
  });
  const forensicsQ = useQuery({
    queryKey: ["qi-forensics", scopeKey],
    queryFn: () => queueIntelligenceApi.getQueueForensics(30, scopeParams),
    refetchInterval: 60000,
  });

  const data = overviewQ.data;
  const summary = data?.summary ?? {};

  const kpis: KpiData[] = useMemo(() => [
    { label: "SLA Compliance", value: `${100 - (summary.avg_breach_pct ?? 0)}%`, status: (summary.avg_breach_pct ?? 100) < 10 ? "ok" : (summary.avg_breach_pct ?? 100) < 30 ? "warn" : "crit", icon: <CheckCircleOutlined /> },
    { label: "Active Breaches", value: summary.total_breaches ?? 0, status: (summary.total_breaches ?? 0) > 100 ? "crit" : (summary.total_breaches ?? 0) > 20 ? "warn" : "ok", icon: <WarningOutlined /> },
    { label: "Queues in Danger", value: summary.degraded_queues ?? 0, status: (summary.degraded_queues ?? 0) > 5 ? "crit" : (summary.degraded_queues ?? 0) > 2 ? "warn" : "ok", icon: <TeamOutlined /> },
    { label: "Need SLA Revision", value: summary.queues_needing_sla_revision ?? 0, status: (summary.queues_needing_sla_revision ?? 0) > 10 ? "crit" : (summary.queues_needing_sla_revision ?? 0) > 3 ? "warn" : "ok", icon: <AlertOutlined /> },
    { label: "Degraded Flows", value: summary.degraded_flows ?? 0, status: (summary.degraded_flows ?? 0) > 10 ? "crit" : (summary.degraded_flows ?? 0) > 3 ? "warn" : "ok", icon: <BranchesOutlined /> },
    { label: "SD Downstream", value: summary.servicedesk_downstream_queues ?? 0, status: (summary.servicedesk_downstream_queues ?? 0) > 15 ? "crit" : "ok", icon: <ApartmentOutlined /> },
  ], [summary]);

  // Sankey-like Queue Flow Map
  const flowOption = useMemo(() => {
    const flows = flowMapQ.data?.flows ?? {};
    const nodes: any[] = [];
    const links: any[] = [];
    const seen = new Set<string>();
    Object.values(flows).forEach((f: any) => {
      if (!seen.has(f.queue) && f.queue) {
        seen.add(f.queue);
        const qf = forensicsQ.data?.queues?.find((q: any) => q.queue === f.queue);
        const isDegraded = qf?.systemically_degraded;
        nodes.push({
          name: f.queue,
          itemStyle: { color: isDegraded ? severityColor.critical : severityColor.normal },
        });
      }
      (f.outbound ?? []).forEach((o: any) => {
        if (!seen.has(o.target)) {
          seen.add(o.target);
          const qf2 = forensicsQ.data?.queues?.find((q: any) => q.queue === o.target);
          nodes.push({
            name: o.target,
            itemStyle: { color: qf2?.systemically_degraded ? severityColor.critical : severityColor.normal },
          });
        }
        links.push({
          source: f.queue, target: o.target,
          value: Math.max(1, o.count),
          lineStyle: { color: o.is_degraded ? severityColor.critical : severityColor.low, opacity: 0.6 },
        });
      });
    });
    return {
      backgroundColor: "transparent",
      tooltip: { trigger: "item" as const, formatter: (p: any) => `${p.source} → ${p.target}: ${p.value} tickets` },
      series: [{
        type: "sankey", layout: "none", emphasis: { focus: "adjacency" as const },
        nodeAlign: "left" as const, nodeWidth: 12, nodeGap: 6, layoutIterations: 32,
        data: nodes.slice(0, 40), links: links.slice(0, 80),
        label: { fontSize: 9, color: colors.text.secondary },
        lineStyle: { curveness: 0.5 },
      }],
    };
  }, [flowMapQ.data, forensicsQ.data, colors]);

  // Breach Heatmap
  const heatmapOption = useMemo(() => {
    const queues = forensicsQ.data?.queues ?? [];
    const top20 = queues.slice(0, 20);
    return {
      backgroundColor: "transparent",
      grid: { left: 120, right: 40, top: 10, bottom: 40 },
      tooltip: { trigger: "item" as const, formatter: (p: any) =>
        `${top20[p.data[1]]?.queue}: ${p.data[2]}% breaches, overload ${top20[p.data[1]]?.overload_score}` },
      xAxis: { type: "category" as const, data: ["Breach %", "Overload", "Avg Min"], axisLabel: { fontSize: 9, color: colors.text.tertiary } },
      yAxis: { type: "category" as const, data: top20.map((q: any) => q.queue).reverse(), axisLabel: { fontSize: 8, color: colors.text.secondary } },
      visualMap: { min: 0, max: 100, calculable: true, orient: "horizontal", left: "center", bottom: 0,
        inRange: { color: ["#1a7f3b", "#b98a1f", "#b65709", "#b42333"] } },
      series: [{
        type: "heatmap",
        data: top20.flatMap((q: any, i: number) => [
          [0, i, q.breach_pct],
          [1, i, Math.min(100, q.overload_score * 50)],
          [2, i, Math.min(100, q.avg_resolution_min / 100)],
        ]),
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
      }],
    };
  }, [forensicsQ.data, colors]);

  // Degraded Flows Table
  const degradedColumns = [
    { title: "From", dataIndex: "from", key: "from", width: 120 },
    { title: "To", dataIndex: "to", key: "to", width: 120 },
    { title: "Count", dataIndex: "count", key: "count", width: 60, sorter: (a: any, b: any) => a.count - b.count },
    { title: "Breach %", dataIndex: "breach_pct", key: "breach_pct", width: 70, render: (v: number) => <Tag color={v > 50 ? "error" : v > 20 ? "warning" : "success"} style={{ fontSize: 10, borderRadius: 4, margin: 0 }}>{v}%</Tag>, sorter: (a: any, b: any) => a.breach_pct - b.breach_pct },
  ];

  // ServiceDesk section
  const sdDownstream = data?.servicedesk?.downstream ?? [];
  const sdColumns = [
    { title: "Target Queue", dataIndex: "target_queue", key: "queue", width: 160 },
    { title: "Tickets", dataIndex: "tickets_received", key: "tickets", width: 60, sorter: (a: any, b: any) => a.tickets_received - b.tickets_received },
    { title: "Slow %", key: "slow", width: 60, render: (_: any, r: any) => `${Math.round((r.slow_transfers / r.tickets_received) * 100)}%` },
    { title: "Avg Delay", dataIndex: "avg_transfer_delay_min", key: "delay", width: 80, render: (v: number) => `${Math.round(v / 60)}h ${Math.round(v % 60)}m` },
    { title: "Quality", dataIndex: "transfer_quality", key: "quality", width: 70, render: (v: string) => <Tag color={v === "poor" ? "error" : "success"} style={{ fontSize: 10, borderRadius: 4 }}>{v}</Tag> },
  ];

  const isDegraded = (status: string) => status === "BREACHED";

  if (overviewQ.isLoading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: spacing[4], maxWidth: 1500, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing[4] }}>
        <div>
          <Title level={3} style={{ margin: 0, fontSize: 20, fontWeight: 600, color: colors.text.primary, letterSpacing: "-0.02em" }}>
            OTRS SLA Command Center
          </Title>
          <Text style={{ fontSize: 12, color: colors.text.tertiary }}>
            Queue Intelligence Platform • {summary.total_queues} queues • {summary.total_tickets} tickets • {summary.total_breaches} breaches • Обновлено: {now.toLocaleTimeString("ru-RU")}
          </Text>
        </div>
        <Badge status={(summary.avg_breach_pct ?? 100) < 10 ? "success" : (summary.avg_breach_pct ?? 100) < 30 ? "warning" : "error"}
          text={<Text style={{ fontSize: 12, color: colors.text.secondary }}>{(summary.avg_breach_pct ?? 100) < 10 ? "Стабильно" : (summary.avg_breach_pct ?? 100) < 30 ? "Внимание" : "Критично"}</Text>} />
      </div>

      {/* KPI Row */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        {kpis.map(k => <Col xs={12} sm={8} lg={4} key={k.label}><KpiCard {...k} /></Col>)}
      </Row>

      {/* Queue Flow Map */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        <Col span={24}>
          <Card size="small" title={<><ApartmentOutlined style={{ marginRight: 6 }} />Queue Flow Map — Поток тикетов между очередями</>}
            extra={<Text style={{ fontSize: 11, color: colors.text.tertiary }}>Красный = деградированный поток</Text>}>
            <ReactEChartsCore theme="sla" option={flowOption} style={{ height: 360 }} notMerge />
          </Card>
        </Col>
      </Row>

      {/* Middle: Breach Heatmap + Degraded Flows */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        <Col span={14}>
          <Card size="small" title={<><HeatMapOutlined style={{ marginRight: 6 }} />Breach Heatmap — Тепловая карта пробитий</>}>
            <ReactEChartsCore theme="sla" option={heatmapOption} style={{ height: 360 }} notMerge />
          </Card>
        </Col>
        <Col span={10}>
          <Card size="small" title={<><BranchesOutlined style={{ marginRight: 6 }} />Top Degraded Flows — Деградированные потоки</>}
            extra={<Text style={{ fontSize: 11, color: colors.text.tertiary }}>{data?.summary?.degraded_flows ?? 0} degraded</Text>}>
            <Table
              dataSource={flowMapQ.data?.degraded_flows ?? []}
              columns={degradedColumns}
              rowKey={(r: any) => `${r.from}-${r.to}`}
              pagination={false}
              size="small"
              locale={{ emptyText: "Нет деградированных потоков" }}
            />
          </Card>
        </Col>
      </Row>

      {/* Bottom Tabs */}
      <Card size="small">
        <Tabs
          items={[
            {
              key: "queue-forensics",
              label: <><DashboardOutlined /> Queue Forensics — Аналитика очередей</>,
              children: <QueueForensicsTable data={forensicsQ.data?.queues ?? []} colors={colors} />,
            },
            {
              key: "servicedesk",
              label: <><ApartmentOutlined /> ServiceDesk Intelligence — Аналитика ServiceDesk</>,
              children: (
                <div>
                  <div style={{ marginBottom: spacing[3] }}>
                    <Text strong>ServiceDesk Intake: {data?.servicedesk?.total_intake ?? 0} tickets</Text>
                    <Text style={{ marginLeft: 16, color: colors.text.tertiary }}>Downstream queues: {sdDownstream.length}</Text>
                  </div>
                  <Table
                    dataSource={sdDownstream}
                    columns={sdColumns}
                    rowKey="target_queue"
                    pagination={false}
                    size="small"
                    locale={{ emptyText: "Нет данных" }}
                  />
                </div>
              ),
            },
            {
              key: "transfer-analytics",
              label: <><NodeIndexOutlined /> Transfer Analytics — Аналитика переходов</>,
              children: <TransferAnalytics data={data} colors={colors} />,
            },
            {
              key: "ai-root-cause",
              label: <><ThunderboltOutlined /> AI Root Cause — Анализ причин</>,
              children: <RootCausePanel colors={colors} />,
            },
          ]}
        />
      </Card>
    </div>
  );
}

function QueueForensicsTable({ data, colors }: { data: any[]; colors: any }) {
  const cols = [
    { title: "Queue", dataIndex: "queue", key: "queue", width: 180, fixed: "left" as const,
      render: (v: string, r: any) => (
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{
            width: 8, height: 8, borderRadius: "50%", display: "inline-block",
            background: r.systemically_degraded ? severityColor.critical : r.needs_separate_sla ? severityColor.high : severityColor.low,
          }} />
          <Text style={{ fontSize: 12, color: r.systemically_degraded ? severityColor.critical : colors.text.primary }}>{v}</Text>
        </div>
      ),
    },
    { title: "Tickets", dataIndex: "total_tickets", key: "total", width: 60, sorter: (a: any, b: any) => a.total_tickets - b.total_tickets },
    { title: "Breach %", dataIndex: "breach_pct", key: "breach_pct", width: 70,
      render: (v: number) => <Tag color={v > 50 ? "error" : v > 20 ? "warning" : "success"} style={{ fontSize: 10, borderRadius: 4, margin: 0 }}>{v}%</Tag>,
      sorter: (a: any, b: any) => a.breach_pct - b.breach_pct },
    { title: "Avg Res (min)", dataIndex: "avg_resolution_min", key: "res", width: 70, render: (v: number) => `${Math.round(v / 60)}h ${v % 60}m`, sorter: (a: any, b: any) => a.avg_resolution_min - b.avg_resolution_min },
    { title: "Avg Resp (min)", dataIndex: "avg_response_min", key: "resp", width: 60, render: (v: number) => `${v}m` },
    { title: "Avg Wait (min)", dataIndex: "avg_wait_min", key: "wait", width: 60, render: (v: number) => `${v}m` },
    { title: "Avg Reassign", dataIndex: "avg_reassignments", key: "reassign", width: 60 },
    { title: "Overload Score", dataIndex: "overload_score", key: "score", width: 60, sorter: (a: any, b: any) => a.overload_score - b.overload_score,
      render: (v: number) => <Tag color={v > 1.5 ? "error" : v > 0.8 ? "warning" : "blue"} style={{ fontSize: 10, borderRadius: 4 }}>{v}</Tag> },
    { title: "Status", key: "status", width: 100,
      render: (_: any, r: any) => r.systemically_degraded ? <Tag color="error" style={{ fontSize: 10, borderRadius: 4 }}>Systemic</Tag> :
        r.needs_separate_sla ? <Tag color="warning" style={{ fontSize: 10, borderRadius: 4 }}>SLA Review</Tag> :
        <Tag color="success" style={{ fontSize: 10, borderRadius: 4 }}>Stable</Tag> },
  ];
  return (
    <Table
      dataSource={data}
      columns={cols}
      rowKey="queue"
      pagination={{ pageSize: 10, size: "small" }}
      size="small"
      scroll={{ x: 800 }}
      locale={{ emptyText: "Нет данных" }}
    />
  );
}

function TransferAnalytics({ data, colors }: { data: any; colors: any }) {
  const loops = data?.top_transfer_loops ?? [];
  const bounces = data?.top_bounce_queues ?? [];
  return (
    <Row gutter={16}>
      <Col span={12}>
        <Text strong style={{ display: "block", marginBottom: 8 }}>Transfer Loops — Циклические переходы</Text>
        {loops.map((l: any, i: number) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: `1px solid ${colors.divider}` }}>
            <Text style={{ fontSize: 12 }}>{l.queue}</Text>
            <Text style={{ fontSize: 12, color: colors.text.tertiary }}>{l.tickets_in_loop} tickets, avg {l.avg_visits} visits</Text>
          </div>
        ))}
        {loops.length === 0 && <Text style={{ color: colors.text.tertiary }}>Нет циклических переходов</Text>}
      </Col>
      <Col span={12}>
        <Text strong style={{ display: "block", marginBottom: 8 }}>Bounce Queues — Очереди с отскоками</Text>
        {bounces.map((b: any, i: number) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: `1px solid ${colors.divider}` }}>
            <Text style={{ fontSize: 12 }}>{b.queue}</Text>
            <Tag color="warning" style={{ fontSize: 10, borderRadius: 4 }}>{b.bounces} bounces</Tag>
          </div>
        ))}
        {bounces.length === 0 && <Text style={{ color: colors.text.tertiary }}>Нет отскоков</Text>}
      </Col>
    </Row>
  );
}

function RootCausePanel({ colors }: { colors: any }) {
  const [ticketId, setTicketId] = useState("");
  const [rootCause, setRootCause] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    if (!ticketId) return;
    setLoading(true);
    try {
      const res = await queueIntelligenceApi.getTicketRootCause(parseInt(ticketId));
      setRootCause(res.root_cause);
    } catch { setRootCause("Ошибка загрузки"); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: spacing[3], alignItems: "center" }}>
        <input
          placeholder="Введите Ticket ID"
          value={ticketId}
          onChange={e => setTicketId(e.target.value)}
          style={{
            padding: "4px 12px", borderRadius: 6, border: `1px solid ${colors.border}`,
            fontSize: 14, width: 200, background: colors.bg.secondary, color: colors.text.primary,
          }}
          onKeyDown={e => e.key === "Enter" && analyze()}
        />
        <button onClick={analyze} disabled={loading}
          style={{
            padding: "4px 16px", borderRadius: 6, border: "none",
            background: colors.chart.line[0], color: "#fff", cursor: "pointer", fontSize: 13,
          }}>
          {loading ? "..." : "Анализ"}
        </button>
      </div>
      {rootCause && (
        <div style={{
          background: colors.bg.secondary, borderRadius: 8, padding: spacing[3],
          whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 13, lineHeight: 1.6,
        }}>
          {rootCause}
        </div>
      )}
    </div>
  );
}
