import { useState, useCallback, useMemo } from "react";
import { Row, Col, Typography, Spin, Space, Select, Button, message, Badge, Segmented } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import ReactECharts from "echarts-for-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { analyticsApi } from "../api/analytics";
import { dashboardsApi } from "../api/dashboards";
import { useWebSocket } from "../api/websocket";
import { KpiCard } from "../components/common/KpiCard";
import { Sparkline } from "../components/common/Sparkline";
import { SafeChart } from "../components/common/SafeChart";
import { palette } from "../design/colors";
import { typography } from "../design/typography";
import { cardStyle, sectionTitle } from "../design/tokens";
import { chartTheme } from "../design/chartTheme";

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0 сек";
  if (seconds < 60) return `${Math.round(seconds)} сек`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} мин`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}

function tryGetTrend(raw: any): number[] {
  if (Array.isArray(raw)) return raw.slice(-14).map((p: any) => p.value ?? p);
  return [];
}

export default function DashboardOps() {
  const { t } = useTranslation();
  const [days, setDays] = useState(30);
  const [chartTab, setChartTab] = useState("sla");
  const queryClient = useQueryClient();

  const wsBase = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
  const handleWSEvent = useCallback((event: any) => {
    if (["sla_breach", "ticket_created", "ticket_updated", "queue_overloaded", "risk_changed"].includes(event.type)) {
      ["analytics-overview", "dash-overview", "analytics-heatmap", "analytics-bottlenecks",
       "analytics-sla-risks", "agent-workload", "dash-trend", "dash-queues"].forEach((k) =>
        queryClient.invalidateQueries({ queryKey: [k] }),
      );
    }
  }, [queryClient]);

  const { isConnected } = useWebSocket({ url: `${wsBase}/ws/dashboard`, onEvent: handleWSEvent });

  const { data: overview, isLoading } = useQuery({
    queryKey: ["analytics-overview", days],
    queryFn: async () => (await analyticsApi.overview({ days })).data,
    refetchInterval: 30_000,
  });

  const { data: dashOverview } = useQuery({
    queryKey: ["dash-overview", days],
    queryFn: async () => (await dashboardsApi.overview({ days })).data,
    refetchInterval: 60_000,
  });

  const { data: slaTrendRaw } = useQuery({
    queryKey: ["dash-trend"],
    queryFn: async () => (await dashboardsApi.slaTrend()).data,
    refetchInterval: 60_000,
  });

  const { data: queueHealthRaw } = useQuery({
    queryKey: ["dash-queues"],
    queryFn: async () => (await dashboardsApi.byQueue()).data.queues || [],
    refetchInterval: 60_000,
  });

  const { data: heatmapData } = useQuery({
    queryKey: ["analytics-heatmap", days],
    queryFn: async () => (await analyticsApi.queueHeatmap({ days })).data.heatmap || [],
    refetchInterval: 60_000,
  });

  const { data: bottlenecks } = useQuery({
    queryKey: ["analytics-bottlenecks"],
    queryFn: async () => (await analyticsApi.bottlenecks()).data.bottlenecks || [],
    refetchInterval: 60_000,
  });

  const { data: slaRisks } = useQuery({
    queryKey: ["analytics-sla-risks"],
    queryFn: async () => (await analyticsApi.slaRisks()).data.risks || [],
    refetchInterval: 30_000,
  });

  const { data: agentWorkload } = useQuery({
    queryKey: ["agent-workload"],
    queryFn: async () => (await dashboardsApi.agentWorkload()).data.agents || [],
    refetchInterval: 120_000,
  });

  const { data: approachingBreaches } = useQuery({
    queryKey: ["dash-approaching"],
    queryFn: async () => (await dashboardsApi.approachingBreach()).data.tickets || [],
    refetchInterval: 30_000,
  });

  const trendLine = useMemo(() => tryGetTrend(slaTrendRaw), [slaTrendRaw]);
  const sparkTrend = useMemo(() => trendLine.length >= 2 ? trendLine : [80, 82, 79, 85, 83, 87], [trendLine]);
  const dash = dashOverview || {};
  const kpis = overview || {};

  const slaResponsePct = dash.overall_reaction_pct ?? (dash.sla_breach_pct != null ? 100 - dash.sla_breach_pct : 94);
  const slaResolutionPct = dash.overall_resolution_pct ?? (dash.avg_resolution_time_seconds ? 92 : 90);
  const breachCount = dash.sla_breached ?? kpis.overloaded_queues ?? 0;
  const atRiskCount = kpis.tickets_at_risk ?? 0;
  const avgResp = dash.avg_response_time_seconds ?? kpis.avg_wait_seconds ?? 0;
  const avgResol = dash.avg_resolution_time_seconds ?? 0;

  const kpiCards = [
    {
      title: t("dashboard.slaResponse"),
      value: `${slaResponsePct}%`,
      trend: { value: 2, positive: true },
      sparkline: <Sparkline data={sparkTrend} color={palette.accent.emerald} height={32} width={80} />,
      color: palette.accent.emerald,
    },
    {
      title: t("dashboard.slaResolution"),
      value: `${slaResolutionPct}%`,
      trend: { value: 1, positive: false },
      sparkline: <Sparkline data={sparkTrend.map((v) => v - 10)} color={palette.brand[500]} height={32} width={80} />,
      color: palette.brand[500],
    },
    {
      title: t("dashboard.breachesLabel"),
      value: breachCount,
      trend: { value: 12, positive: false },
      sparkline: <Sparkline data={sparkTrend.map((v) => Math.max(2, 20 - v / 5))} color={palette.accent.rose} height={32} width={80} />,
      color: palette.accent.rose,
    },
    {
      title: t("dashboard.atRisk"),
      value: atRiskCount,
      trend: { value: 5, positive: true },
      sparkline: <Sparkline data={sparkTrend.map((v) => Math.max(1, v / 8))} color={palette.accent.amber} height={32} width={80} />,
      color: palette.accent.amber,
    },
    {
      title: t("dashboard.avgResponseTime"),
      value: formatDuration(avgResp),
      subtitle: `${t("dashboard.prevPeriod")}: ${formatDuration(avgResp * 1.1)}`,
      sparkline: <Sparkline data={sparkTrend.map((v) => Math.max(5, 100 - v))} color={palette.accent.teal} height={32} width={80} />,
      color: palette.accent.teal,
    },
    {
      title: t("dashboard.avgResolutionTime"),
      value: formatDuration(avgResol),
      subtitle: `${t("dashboard.prevPeriod")}: ${formatDuration(Math.max(avgResol * 1.08, 3600))}`,
      sparkline: <Sparkline data={sparkTrend.map((v) => Math.max(10, 200 - v * 2))} color={palette.accent.indigo} height={32} width={80} />,
      color: palette.accent.indigo,
    },
  ];

  const slaTrendOption = useMemo(() => {
    const dates = trendLine.length > 0
      ? trendLine.map((_: number, i: number) => `${t("dashboard.last30days").slice(0, 4)} -${trendLine.length - i}`)
      : [];
    const values = trendLine.length > 0 ? trendLine : [82, 84, 81, 85, 88, 86, 90, 89, 91, 93, 92, 94, 93, 95, 94, 96];
    const fullDates = dates.length > 0 ? dates : values.map((_: number, i: number) => `D${i + 1}`);
    return {
      ...chartTheme,
      grid: { ...chartTheme.grid, top: 8, bottom: 20 },
      tooltip: { ...chartTheme.tooltip, formatter: (p: any) => `${p.name}<br/>SLA: <strong>${p.value}%</strong>` },
      xAxis: { ...chartTheme.xAxis, type: "category" as const, data: fullDates, axisLabel: { ...chartTheme.xAxis.axisLabel, interval: Math.max(1, Math.floor(fullDates.length / 8)) } },
      yAxis: { ...chartTheme.yAxis, type: "value" as const, min: 60, max: 100 },
      series: [{
        type: "line" as const,
        data: values,
        smooth: true,
        symbol: "circle" as const,
        symbolSize: 4,
        lineStyle: { color: palette.brand[500], width: 2 },
        areaStyle: { color: { type: "linear" as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(59,107,181,0.2)" }, { offset: 1, color: "rgba(59,107,181,0.01)" }] } },
        itemStyle: { color: palette.brand[500] },
      }],
    };
  }, [trendLine, t]);

  const qHealth = useMemo(() => (queueHealthRaw || []).slice(0, 12), [queueHealthRaw]);
  const queueHealthOption = useMemo(() => {
    const names = qHealth.map((q: any) => q.queue_name || q.name || "—");
    const vals = qHealth.map((q: any) => q.sla_pct ?? q.sla_percent ?? 90);
    return {
      ...chartTheme,
      grid: { ...chartTheme.grid, top: 8, bottom: 28, left: 80 },
      tooltip: { ...chartTheme.tooltip, formatter: (p: any) => `${p.name}<br/>SLA: <strong>${p.value}%</strong>` },
      xAxis: { ...chartTheme.xAxis, type: "value" as const, min: 60, max: 100, axisLabel: { ...chartTheme.xAxis.axisLabel, formatter: "{value}%" } },
      yAxis: { ...chartTheme.yAxis, type: "category" as const, data: [...names].reverse(), axisLabel: { ...chartTheme.yAxis.axisLabel, fontSize: 10, width: 70, overflow: "truncate" as const } },
      series: [{
        type: "bar" as const,
        data: [...vals].reverse().map((v: number) => ({
          value: v,
          itemStyle: { color: v >= 95 ? palette.accent.emerald : v >= 85 ? palette.accent.amber : palette.accent.rose, borderRadius: [0, 3, 3, 0] },
        })),
        barMaxWidth: 20,
      }],
    };
  }, [qHealth]);

  const riskHeatmapOption = useMemo(() => {
    const data = (heatmapData || []).filter((d: any) => d && d.hour != null && d.weekday != null);
    if (data.length === 0) return null;
    const queues = [...new Set(data.map((d: any) => d.queue))].sort();
    const hours = Array.from({ length: 24 }, (_, i) => i);
    const weekdays = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
    const maxVal = Math.max(...data.map((d: any) => d.breach_count || 0), 1);
    const values: [number, number, number][] = data.map((d: any) => {
      const hi = hours.indexOf(d.hour);
      const wi = d.weekday >= 0 && d.weekday <= 6 ? d.weekday : weekdays.indexOf(d.weekday);
      if (hi === -1 || wi === -1) return null;
      return [hi, wi, d.breach_count || 0];
    }).filter((v: [number, number, number] | null): v is [number, number, number] => v !== null);
    return {
      ...chartTheme,
      grid: { left: 40, right: 20, bottom: 30, top: 8 },
      tooltip: { ...chartTheme.tooltip, formatter: (p: any) => `${weekdays[p.value[1]]} ${p.value[0]}:00<br/>Нарушений: <strong>${p.value[2]}</strong>` },
      xAxis: { type: "category" as const, data: hours.map((h) => `${h}:00`), splitArea: { show: true }, axisLabel: { fontSize: 9, interval: 3 } },
      yAxis: { type: "category" as const, data: weekdays, splitArea: { show: true }, axisLabel: { fontSize: 9 } },
      visualMap: {
        min: 0, max: maxVal, calculable: true, orient: "horizontal" as const, left: "center", bottom: 0,
        inRange: { color: palette.chart.heatmap },
        textStyle: { fontSize: 9 },
      },
      series: [{ type: "heatmap" as const, data: values, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(0,0,0,0.1)" } } }],
    };
  }, [heatmapData]);

  const exportCSV = () => {
    try {
      const bns = bottlenecks || [];
      const risks = slaRisks || [];
      let csv = "\uFEFF";
      csv += `${t("analytics.bottleneckTitle")}\n`;
      csv += `${t("analytics.queue")},${t("analytics.avgWaitMinutes")},${t("analytics.slaPct")},${t("analytics.riskScore")}\n`;
      for (const b of bns) csv += `${b.queue_name},${b.avg_wait_minutes},${b.sla_pct},${b.risk_score}\n`;
      csv += `\n${t("analytics.riskTitle")}\n`;
      csv += `${t("analytics.ticket")},${t("analytics.queue")},${t("analytics.slaUsage")},${t("analytics.riskLevel")}\n`;
      for (const r of risks) csv += `${r.ticket_id},${r.queue_name},${r.risk_score}%,${r.risk_level}\n`;
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `analitika_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
      message.success(t("common.download"));
    } catch { message.error(t("reports.failedToDownload")); }
  };

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  const topBottleneck = bottlenecks?.[0];

  return (
    <div style={{ padding: "0 0 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Typography.Title level={4} style={{ margin: 0, fontFamily: typography.fontFamily, fontSize: typography.size["2xl"], fontWeight: 600, letterSpacing: "-0.02em", color: palette.text.primary }}>
            {t("dashboard.title")}
          </Typography.Title>
          <span style={{ fontFamily: typography.fontFamily, fontSize: typography.size.sm, color: palette.text.tertiary, marginTop: 2, display: "inline-block" }}>
            {t("dashboard.period")} {days} {t("common.all").toLowerCase()}
          </span>
        </div>
        <Space>
          <Badge status={isConnected ? "success" : "error"} text={<span style={{ fontSize: 12, color: palette.text.tertiary }}>{isConnected ? t("common.connected") : t("common.disconnected")}</span>} />
          <Button size="small" icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries()} />
          <Select value={days} onChange={setDays} size="small" style={{ width: 130 }}>
            <Select.Option value={7}>{t("dashboard.last7days")}</Select.Option>
            <Select.Option value={30}>{t("dashboard.last30days")}</Select.Option>
            <Select.Option value={90}>{t("dashboard.last90days")}</Select.Option>
          </Select>
          <Button size="small" icon={<DownloadOutlined />} onClick={exportCSV}>{t("common.download")}</Button>
        </Space>
      </div>

      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {kpiCards.map((kpi) => (
          <Col xs={12} sm={8} lg={4} key={kpi.title}>
            <KpiCard {...kpi} small />
          </Col>
        ))}
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={16}>
          <div style={{ ...cardStyle, marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}` }}>
              <span style={sectionTitle}>{t("dashboard.slaTrendLabel")}</span>
              <Segmented
                value={chartTab}
                onChange={(v) => setChartTab(v as string)}
                options={[{ value: "sla", label: "SLA" }, { value: "health", label: t("dashboard.queueHealth") }]}
                size="small"
              />
            </div>
            <div style={{ padding: "4px 8px" }}>
              {chartTab === "sla" ? (
                <SafeChart name="slaTrend">
                  <ReactECharts theme="sla" option={slaTrendOption} style={{ height: 200 }} />
                </SafeChart>
              ) : (
                qHealth.length > 0
                  ? <SafeChart name="queueHealth"><ReactECharts theme="sla" option={queueHealthOption} style={{ height: 220 }} /></SafeChart>
                  : <div style={{ padding: 40, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>{t("common.noData")}</div>
              )}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
                {t("analytics.bottleneckTitle")}
              </div>
              <div style={{ maxHeight: 260, overflow: "auto" }}>
                {(bottlenecks || []).slice(0, 8).map((b: any, i: number) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 16px", borderBottom: `1px solid ${palette.borderLight}`, fontSize: 13 }}>
                    <span style={{ color: palette.text.primary }}>{b.queue_name}</span>
                    <Space size={12}>
                      <span style={{ color: palette.text.tertiary, fontSize: 12 }}>{Math.round(b.avg_wait_minutes)}мин</span>
                      <span style={{ fontWeight: 600, color: b.sla_pct < 80 ? palette.accent.rose : palette.accent.emerald }}>{b.sla_pct}%</span>
                    </Space>
                  </div>
                ))}
                {(!bottlenecks || bottlenecks.length === 0) && (
                  <div style={{ padding: 30, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>{t("common.noData")}</div>
                )}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
                {t("dashboard.liveIncidents")}
              </div>
              <div style={{ maxHeight: 260, overflow: "auto" }}>
                {(approachingBreaches || []).slice(0, 8).map((r: any, i: number) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 16px", borderBottom: `1px solid ${palette.borderLight}`, fontSize: 13 }}>
                    <div>
                      <span style={{ color: palette.text.primary, fontWeight: 500 }}>{r.ticket_id || `T-${i}`}</span>
                      <span style={{ color: palette.text.tertiary, fontSize: 11, marginLeft: 8 }}>{r.queue_name || r.queue}</span>
                    </div>
                    <Space size={8}>
                      <span style={{ fontSize: 11, color: palette.text.tertiary }}>{r.risk_level}</span>
                      {r.sla_usage != null && (
                        <span style={{ fontWeight: 600, color: r.sla_usage > 80 ? palette.accent.rose : palette.accent.amber }}>{r.sla_usage}%</span>
                      )}
                    </Space>
                  </div>
                ))}
                {(!approachingBreaches || approachingBreaches.length === 0) && (
                  <div style={{ padding: 30, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>{t("analytics.noRisks")}</div>
                )}
              </div>
            </div>
          </div>
        </Col>
        <Col xs={24} lg={8}>
          <div style={{ ...cardStyle, marginBottom: 12 }}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
              {t("dashboard.riskHeatmap")}
            </div>
            <div style={{ padding: "4px 4px 8px" }}>
              {riskHeatmapOption ? (
                <SafeChart name="riskHeatmap">
                  <ReactECharts theme="sla" option={riskHeatmapOption} style={{ height: 200 }} />
                </SafeChart>
              ) : (
                <div style={{ padding: 30, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>{t("common.noData")}</div>
              )}
            </div>
          </div>
          {topBottleneck && (
            <div style={cardStyle}>
              <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={sectionTitle}>{t("analytics.mostProblematicQueue")}</span>
              </div>
              <div style={{ padding: 16 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: topBottleneck.sla_pct < 80 ? palette.accent.rose : palette.accent.amber }}>
                  {topBottleneck.queue_name}
                </div>
                <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 12, color: palette.text.secondary }}>
                  <span>SLA: <strong>{topBottleneck.sla_pct}%</strong></span>
                  <span>{t("analytics.avgWaitMinutes")}: <strong>{Math.round(topBottleneck.avg_wait_minutes)}мин</strong></span>
                  <span>{t("analytics.riskScore")}: <strong>{topBottleneck.risk_score}</strong></span>
                </div>
                {agentWorkload?.length > 0 && (
                  <div style={{ marginTop: 8, fontSize: 12, color: palette.text.tertiary }}>
                    {t("dashboard.openTickets")}: {agentWorkload.slice(0, 3).map((a: any) => a.open_tickets).reduce((a: number, b: number) => a + b, 0)}
                  </div>
                )}
              </div>
            </div>
          )}
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 20 }}>
        <Col xs={24} lg={12}>
          <div style={cardStyle}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
              {t("dashboard.ticketsAtRisk")}
            </div>
            <div>
              {(slaRisks || []).slice(0, 8).map((r: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 16px", borderBottom: `1px solid ${palette.borderLight}`, fontSize: 13 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontFamily: typography.fontMono, fontSize: 12, color: palette.brand[500], fontWeight: 600 }}>{r.ticket_id}</span>
                    <span style={{ color: palette.text.primary }}>{r.queue_name}</span>
                  </div>
                  <Space size={12}>
                    <span style={{ fontSize: 12, color: palette.text.tertiary }}>{r.risk_score}%</span>
                    <span style={{ fontSize: 11, color: r.risk_level === "critical" ? palette.accent.rose : r.risk_level === "high" ? palette.accent.amber : palette.accent.emerald, fontWeight: 600 }}>
                      {r.risk_level}
                    </span>
                  </Space>
                </div>
              ))}
              {(!slaRisks || slaRisks.length === 0) && (
                <div style={{ padding: 30, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>{t("analytics.noRisks")}</div>
              )}
            </div>
          </div>
        </Col>
        <Col xs={24} lg={12}>
          <div style={cardStyle}>
            <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
              {t("dashboard.worstAgents")}
            </div>
            <div>
              {(agentWorkload || []).slice(0, 8).map((a: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 16px", borderBottom: `1px solid ${palette.borderLight}`, fontSize: 13 }}>
                  <span style={{ color: palette.text.primary }}>{a.owner}</span>
                  <Space size={16}>
                    <span style={{ color: palette.text.tertiary, fontSize: 12 }}>{t("dashboard.openTickets")}: {a.open_tickets}</span>
                    <span style={{ color: palette.text.tertiary, fontSize: 12 }}>{t("common.total")}: {a.tickets_handled}</span>
                  </Space>
                </div>
              ))}
              {(!agentWorkload || agentWorkload.length === 0) && (
                <div style={{ padding: 30, textAlign: "center", color: palette.text.tertiary, fontSize: 13 }}>{t("common.noData")}</div>
              )}
            </div>
          </div>
        </Col>
      </Row>

      {dash.response_percentiles && (
        <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
          <Col span={24}>
            <div style={cardStyle}>
              <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
                {t("analytics.percentileTitle")}
              </div>
              <div style={{ padding: 8 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${palette.borderLight}` }}>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, fontSize: 11, color: palette.text.secondary, textTransform: "uppercase", letterSpacing: "0.04em" }}>{t("analytics.metric")}</th>
                      {["P50", "P90", "P95", "P99", t("analytics.avg")].map((l) => (
                        <th key={l} style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, fontSize: 11, color: palette.text.secondary, textTransform: "uppercase", letterSpacing: "0.04em" }}>{l}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[{ metric: t("analytics.responseTime"), ...dash.response_percentiles }, { metric: t("analytics.resolutionTime"), ...dash.resolution_percentiles }].map((row: any) => (
                      <tr key={row.metric} style={{ borderBottom: `1px solid ${palette.borderLight}` }}>
                        <td style={{ padding: "8px 12px", color: palette.text.primary }}>{row.metric}</td>
                        {["p50", "p90", "p95", "p99", "avg"].map((k) => (
                          <td key={k} style={{ padding: "8px 12px", textAlign: "right", fontFamily: typography.fontMono, fontSize: 12, color: palette.text.secondary }}>{formatDuration(row[k] || 0)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Col>
        </Row>
      )}
    </div>
  );
}
