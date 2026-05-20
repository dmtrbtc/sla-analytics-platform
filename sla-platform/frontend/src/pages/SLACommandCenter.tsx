import { useMemo, useState } from "react";
import { Row, Col, Tag, Spin, Typography, Badge, Table, Progress } from "antd";
import { WarningOutlined, CheckCircleOutlined, ClockCircleOutlined, ArrowUpOutlined, ArrowDownOutlined, ThunderboltOutlined, TeamOutlined, DashboardOutlined, AlertOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react";
import { useTheme } from "../design/ThemeContext";
import { cardStyle, cardHeaderStyle, kpiCardStyle, statusStrip, kpiValueStyle, kpiLabelStyle } from "../design/tokens";
import { spacing } from "../design/spacing";
import { typography } from "../design/typography";
import client from "../api/client";

const { Text, Title } = Typography;

interface KpiData {
  label: string;
  value: string | number;
  trend?: number;
  status?: "ok" | "warn" | "crit";
  icon?: React.ReactNode;
  sparkline?: number[];
}

function KpiCard({ label, value, trend, status = "ok", icon, sparkline }: KpiData) {
  const { colors } = useTheme();
  const stripColor = status === "ok" ? colors.severity.ok : status === "warn" ? colors.severity.warn : colors.severity.crit;

  return (
    <div style={{ ...kpiCardStyle, cursor: "default" }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 4px 12px rgba(27,31,35,0.07)"; e.currentTarget.style.borderColor = colors.border; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 1px 3px rgba(27,31,35,0.03)"; e.currentTarget.style.borderColor = colors.border; }}>
      <div style={{ ...statusStrip, background: stripColor }} />
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

const statusColors: Record<string, string> = { ok: "#1a7f3b", warn: "#b65709", crit: "#b42333", healthy: "#1a7f3b", warning: "#b65709", critical: "#b42333" };

export default function SLACommandCenter() {
  const { colors, resolved } = useTheme();
  const [now] = useState(new Date());

  const { data: overview, isLoading } = useQuery({
    queryKey: ["command-center-overview"],
    queryFn: async () => {
      const [metrics, breaches, queueBreachesRes, approaching, health, anomalies, forecast] = await Promise.all([
        client.get("/sla/metrics", { params: { limit: 1 } }).then(r => r.data).catch(() => ({ total: 0 })),
        client.get("/sla/breaches", { params: { limit: 1 } }).then(r => r.data).catch(() => ({ total: 0 })),
        client.get("/sla/queue-breaches").then(r => r.data).catch(() => ({ queue_breaches: [] })),
        client.get("/dashboards/approaching-breach", { params: { limit: 20 } }).then(r => r.data).catch(() => ({ tickets: [] })),
        client.get("/system/health").then(r => r.data).catch(() => ({ status: "unknown" })),
        client.get("/ai/anomalies", { params: { days: 7 } }).then(r => r.data).catch(() => ({ anomalies: [] })),
        client.get("/dashboards/analytics/sla-forecast", { params: { days: 30 } }).then(r => r.data).catch(() => ({})),
      ]);
      return { metrics, breaches, queueBreaches: queueBreachesRes, approaching, health, anomalies, forecast };
    },
    refetchInterval: 30000,
  });

  const slaCompliance = useMemo(() => {
    const m = overview?.metrics?.total ?? 0;
    const b = overview?.breaches?.total ?? 0;
    return m > 0 ? Math.round(((m - b) / m) * 100) : 100;
  }, [overview]);

  const kpis: KpiData[] = useMemo(() => [
    { label: "SLA Compliance", value: `${slaCompliance}%`, status: slaCompliance >= 95 ? "ok" : slaCompliance >= 85 ? "warn" : "crit", icon: <CheckCircleOutlined />, trend: slaCompliance >= 95 ? 2 : -3 },
    { label: "Active Breaches", value: overview?.breaches?.total ?? 0, status: (overview?.breaches?.total ?? 0) > 50 ? "crit" : (overview?.breaches?.total ?? 0) > 10 ? "warn" : "ok", icon: <WarningOutlined />, trend: undefined },
    { label: "At Risk Tickets", value: overview?.approaching?.tickets?.length ?? 0, status: (overview?.approaching?.tickets?.length ?? 0) > 20 ? "warn" : "ok", icon: <ClockCircleOutlined /> },
    { label: "Active Incidents", value: overview?.anomalies?.total ?? 0, status: (overview?.anomalies?.total ?? 0) > 5 ? "crit" : "ok", icon: <ThunderboltOutlined /> },
    { label: "System Health", value: overview?.health?.status ?? "Unknown", status: overview?.health?.status === "healthy" ? "ok" : "warn", icon: <DashboardOutlined /> },
    { label: "Active Queues", value: overview?.queueBreaches?.queue_breaches?.length ?? 0, icon: <TeamOutlined /> },
  ], [slaCompliance, overview]);

  const slaTrendOption = useMemo(() => ({
    backgroundColor: "transparent",
    grid: { left: 36, right: 8, top: 20, bottom: 20 },
    tooltip: { trigger: "axis" as const },
    xAxis: { type: "category" as const, data: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"], axisLabel: { fontSize: 10, color: colors.text.tertiary }, axisLine: { lineStyle: { color: colors.border } } },
    yAxis: { type: "value" as const, min: 85, max: 100, axisLabel: { fontSize: 10, color: colors.text.tertiary, formatter: "{value}%" }, splitLine: { lineStyle: { color: colors.divider, type: "dashed" as const } } },
    series: [{
      data: [96, 94, 93, 91, 92, 95, slaCompliance], type: "line", smooth: true,
      lineStyle: { width: 2, color: slaCompliance >= 95 ? colors.severity.ok : slaCompliance >= 85 ? colors.severity.warn : colors.severity.crit },
      areaStyle: { color: { type: "linear" as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: slaCompliance >= 95 ? "rgba(26,127,59,0.15)" : "rgba(182,87,9,0.15)" }, { offset: 1, color: "rgba(0,0,0,0)" }] } },
      symbol: "circle", symbolSize: 6,
    }],
  }), [slaCompliance, colors]);

  const queueBreachOption = useMemo(() => {
    const qb = overview?.queueBreaches?.queue_breaches?.slice(0, 8) ?? [];
    return {
      backgroundColor: "transparent",
      grid: { left: 80, right: 24, top: 8, bottom: 8 },
      tooltip: { trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
      xAxis: { type: "value" as const, axisLabel: { fontSize: 9, color: colors.text.tertiary }, splitLine: { lineStyle: { color: colors.divider, type: "dashed" as const } } },
      yAxis: { type: "category" as const, data: qb.map((q: any) => q.queue_name || q.queue).reverse(), axisLabel: { fontSize: 10, color: colors.text.secondary } },
      series: [{ type: "bar" as const, data: qb.map((q: any) => q.tickets_total || 0).reverse(), itemStyle: { color: colors.chart.line[0], borderRadius: [0, 3, 3, 0] }, barMaxWidth: 16 }],
    };
  }, [overview, colors]);

  const approachingBreachColumns = [
    { title: "Ticket", dataIndex: "ticket_number", key: "ticket", width: 100, render: (v: string) => <Text style={{ fontFamily: typography.fontMono, fontSize: 12 }}>{v}</Text> },
    { title: "Queue", dataIndex: "queue", key: "queue", width: 100 },
    { title: "Metric", dataIndex: "metric_name", key: "metric", width: 120 },
    { title: "Elapsed", dataIndex: "elapsed_seconds", key: "elapsed", width: 90, render: (v: number) => `${Math.round(v / 60)}m` },
    { title: "Status", key: "status", width: 80, render: (_: any, r: any) => <Tag color={r.risk_level === "critical" ? "error" : r.risk_level === "high" ? "warning" : "default"} style={{ fontSize: 10, borderRadius: 4, margin: 0 }}>{r.risk_level || "low"}</Tag> },
  ];

  if (isLoading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: spacing[4], maxWidth: 1400, margin: "0 auto" }}>
      {/* Top Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing[4] }}>
        <div>
          <Title level={3} style={{ margin: 0, fontSize: 20, fontWeight: 600, color: colors.text.primary, letterSpacing: "-0.02em" }}>Центр управления SLA</Title>
          <Text style={{ fontSize: 12, color: colors.text.tertiary }}>Enterprise Operations Command Center • Обновлено: {now.toLocaleTimeString("ru-RU")}</Text>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge status={slaCompliance >= 95 ? "success" : "error"} />
          <Tag color={slaCompliance >= 95 ? "success" : slaCompliance >= 85 ? "warning" : "error"} style={{ fontSize: 11, borderRadius: 4, padding: "2px 8px" }}>
            {slaCompliance >= 95 ? "Все системы работают" : slaCompliance >= 85 ? "Требуется внимание" : "Критическое состояние"}
          </Tag>
        </div>
      </div>

      {/* KPI Row */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        {kpis.map(k => <Col span={4} key={k.label}><KpiCard {...k} /></Col>)}
      </Row>

      {/* Middle row: Left (Queue Health) + Center (SLA Trend + Breach Map) + Right (Incidents + AI) */}
      <Row gutter={[12, 12]} style={{ marginBottom: spacing[4] }}>
        {/* Left — Queue Health */}
        <Col span={6}>
          <div style={{ ...cardStyle, height: "100%" }}>
            <div style={cardHeaderStyle as React.CSSProperties}>
              <TeamOutlined style={{ marginRight: 6 }} /> Состояние очередей
            </div>
            <div style={{ padding: spacing[3] }}>
              {overview?.queueBreaches?.queue_breaches?.slice(0, 8).map((q: any) => {
                const pct = Math.min(100, Math.round(((q.tickets_total || 0) / Math.max((overview?.metrics?.total ?? 1), 1)) * 100));
                return (
                  <div key={q.queue_name || q.queue} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                      <Text style={{ fontSize: 12, color: colors.text.secondary }}>{q.queue_name || q.queue}</Text>
                      <Text style={{ fontSize: 11, color: colors.text.tertiary }}>{q.tickets_total || 0} tickets</Text>
                    </div>
                    <Progress percent={pct} size="small" strokeColor={pct > 20 ? colors.severity.crit : pct > 10 ? colors.severity.warn : colors.severity.ok} trailColor={colors.borderLight} showInfo={false} style={{ margin: 0 }} />
                  </div>
                );
              })}
            </div>
          </div>
        </Col>

        {/* Center — SLA Trend + Breach Risk */}
        <Col span={12}>
          <div style={{ ...cardStyle, marginBottom: 12 }}>
            <div style={cardHeaderStyle as React.CSSProperties}>
              <DashboardOutlined style={{ marginRight: 6 }} /> SLA Compliance Trend
            </div>
            <ReactEChartsCore option={slaTrendOption} style={{ height: 180 }} notMerge />
          </div>
          <Row gutter={12}>
            <Col span={12}>
              <div style={{ ...cardStyle }}>
                <div style={cardHeaderStyle as React.CSSProperties}>Breach Risk Map</div>
                <ReactEChartsCore option={queueBreachOption} style={{ height: 160 }} notMerge />
              </div>
            </Col>
            <Col span={12}>
              <div style={{ ...cardStyle }}>
                <div style={cardHeaderStyle as React.CSSProperties}>SLA Timeline</div>
                <div style={{ padding: spacing[3], display: "flex", flexDirection: "column", gap: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Badge status="success" text={<Text style={{ fontSize: 12, color: colors.text.secondary }}>Response Time</Text>} />
                    <Text style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>{overview?.metrics?.total ? `${Math.round((overview?.metrics?.total ?? 0) / 100)}s` : "—"}</Text>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Badge status="warning" text={<Text style={{ fontSize: 12, color: colors.text.secondary }}>Resolution Time</Text>} />
                    <Text style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>{overview?.breaches?.total ? `${Math.round((overview?.breaches?.total ?? 0) / 10)}m` : "—"}</Text>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Badge status="error" text={<Text style={{ fontSize: 12, color: colors.text.secondary }}>Breach Rate</Text>} />
                    <Text style={{ fontSize: 13, fontWeight: 600, color: colors.text.primary }}>{100 - slaCompliance}%</Text>
                  </div>
                </div>
              </div>
            </Col>
          </Row>
        </Col>

        {/* Right — Incidents + AI */}
        <Col span={6}>
          <div style={{ ...cardStyle, height: "100%" }}>
            <div style={cardHeaderStyle as React.CSSProperties}>
              <AlertOutlined style={{ marginRight: 6 }} /> AI Рекомендации
            </div>
            <div style={{ padding: spacing[3] }}>
              {(overview?.anomalies?.anomalies ?? []).length > 0 ? (
                overview?.anomalies?.anomalies?.slice(0, 5).map((a: any, i: number) => (
                  <div key={i} style={{ padding: "8px 0", borderBottom: i < 4 ? `1px solid ${colors.divider}` : "none" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                      <Tag color={a.severity === "high" ? "error" : "warning"} style={{ fontSize: 9, lineHeight: "14px", borderRadius: 3, padding: "0 4px", margin: 0 }}>{a.severity}</Tag>
                      <Text style={{ fontSize: 12, fontWeight: 600, color: colors.text.primary }}>{a.queue}</Text>
                    </div>
                    <Text style={{ fontSize: 11, color: colors.text.secondary }}>{a.description}</Text>
                  </div>
                ))
              ) : (
                <div style={{ textAlign: "center", padding: spacing[4], color: colors.text.tertiary }}>
                  <CheckCircleOutlined style={{ fontSize: 24, marginBottom: 8, color: colors.severity.ok }} />
                  <br />
                  <Text style={{ fontSize: 12, color: colors.text.tertiary }}>Аномалий не обнаружено</Text>
                </div>
              )}
            </div>
          </div>
        </Col>
      </Row>

      {/* Bottom — Tickets at Risk */}
      <div style={{ ...cardStyle }}>
        <div style={cardHeaderStyle as React.CSSProperties}>
          <WarningOutlined style={{ marginRight: 6 }} /> Тикеты с риском нарушения SLA
        </div>
        <Table
          dataSource={overview?.approaching?.tickets ?? []}
          columns={approachingBreachColumns}
          rowKey={(r: any) => r.ticket_number || r.id}
          pagination={{ pageSize: 5, size: "small" }}
          size="small"
          style={{ fontSize: 12 }}
          locale={{ emptyText: "Нет тикетов с риском нарушения" }}
        />
      </div>
    </div>
  );
}
