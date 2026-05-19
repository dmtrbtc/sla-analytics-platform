import { useState, useCallback, useMemo } from "react";
import {
  Row, Col, Card, Statistic, Typography, Spin, Table, Tag, Space, Select, Button, message,
  Segmented, Input, Drawer, Badge, Tooltip, Divider,
} from "antd";
import {
  AimOutlined, DownloadOutlined, ClockCircleOutlined, WarningOutlined, FireOutlined,
  CheckCircleOutlined, CloseOutlined, ReloadOutlined, SearchOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { slaApi, mapQueueMetrics, mapKPIs, mapBreachTickets } from "../api/sla";
import type { QueueMetric, BreachTicket, SLAKPI } from "../api/sla";
import { useWebSocket } from "../api/websocket";
import { KpiCard } from "../components/common/KpiCard";
import { palette } from "../design/colors";
import { typography } from "../design/typography";
import { cardStyle, sectionTitle } from "../design/tokens";

const feedRowIn = `@keyframes feedRowIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }`;

// ── Helpers ──

function fmtDuration(sec: number): string {
  if (!sec || sec <= 0) return "0 с";
  if (sec < 60) return `${Math.round(sec)} с`;
  if (sec < 3600) return `${Math.round(sec / 60)} мин`;
  const h = Math.floor(sec / 3600);
  const m = Math.round((sec % 3600) / 60);
  if (h < 24) return m === 0 ? `${h} ч` : `${h} ч ${m} мин`;
  const d = Math.floor(h / 24);
  const hr = h % 24;
  return hr === 0 ? `${d} д` : `${d} д ${hr} ч`;
}

function fmtNum(n: number): string {
  return n.toLocaleString("ru-RU");
}

function fmtPct(pct: number): string {
  return `${pct}%`;
}

function pctColor(pct: number): string {
  if (pct >= 95) return "#52c41a";
  if (pct >= 90) return "#faad14";
  if (pct >= 80) return "#ff4d4f";
  return "#a8071a";
}

function sevTagColor(sev: string): string {
  return sev === "crit" ? "red" : sev === "high" ? "orange" : "gold";
}

// ── Inline SVG Sparkline ──

function Sparkline({ data, color = "#fa8c16", height = 20, width = 56 }: { data: number[]; color?: string; height?: number; width?: number }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, 1);
  const stepX = width / (data.length - 1 || 1);
  const pts = data.map((d, i) => `${(i * stepX).toFixed(1)},${(height - (d / max) * (height - 2) - 1).toFixed(1)}`).join(" ");
  const area = `0,${height} ${pts} ${width},${height}`;
  const lx = (data.length - 1) * stepX;
  const ly = height - (data[data.length - 1] / max) * (height - 2) - 1;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: "block" }}>
      <polygon points={area} fill={color} fillOpacity={0.15} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="2" fill={color} />
    </svg>
  );
}

// ── Pct bar cell ──

function PctBar({ pct }: { pct: number }) {
  const color = pctColor(pct);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 100 }}>
      <span style={{ width: 40, textAlign: "right", fontWeight: 600, fontSize: 13 }}>{pct}%</span>
      <div style={{ flex: 1, height: 8, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${Math.max(2, pct)}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

// ── Count pill ──

function CountPill({ value, total }: { value: number; total: number }) {
  if (value === 0) return <span style={{ color: "#bbb" }}>0</span>;
  const ratio = value / Math.max(total, 1);
  const cls = ratio >= 0.2 ? "red" : ratio >= 0.1 ? "orange" : "gold";
  return <Tag color={cls}>{fmtNum(value)}</Tag>;
}

// ── Page ──

export default function SLAMonitor() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // State
  const [view, setView] = useState<string>("matrix");
  const [period, setPeriod] = useState<number>(30);
  const [search, setSearch] = useState("");
  const [groupBy, setGroupBy] = useState("all");
  const [kindFilter, setKindFilter] = useState("all");
  const [queueFilter, setQueueFilter] = useState("all");
  const [sevFilter, setSevFilter] = useState("all");
  const [sortKey, setSortKey] = useState("r_breached");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [sortKeyFeed, setSortKeyFeed] = useState("overdue");
  const [sortDirFeed, setSortDirFeed] = useState<"asc" | "desc">("desc");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerKind, setDrawerKind] = useState<"queue" | "ticket" | null>(null);
  const [drawerPayload, setDrawerPayload] = useState<any>(null);

  // WebSocket live
  const wsBase = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
  const handleWSEvent = useCallback((event: any) => {
    if (["sla_breach", "ticket_updated", "queue_overloaded", "risk_changed"].includes(event.type)) {
      queryClient.invalidateQueries({ queryKey: ["sla-queue-breaches"] });
      queryClient.invalidateQueries({ queryKey: ["sla-breaches"] });
      queryClient.invalidateQueries({ queryKey: ["sla-summary"] });
      queryClient.invalidateQueries({ queryKey: ["sla-queue-rules"] });
    }
  }, [queryClient]);

  const { isConnected } = useWebSocket({ url: `${wsBase}/ws/dashboard`, onEvent: handleWSEvent });

  // Queries
  const { data: rawBreaches, isLoading: breachesLoading } = useQuery({
    queryKey: ["sla-queue-breaches", period],
    queryFn: async () => (await slaApi.getQueueBreaches({ days: period })).data.queue_breaches || [],
    refetchInterval: 30_000,
  });

  const { data: rawRules } = useQuery({
    queryKey: ["sla-queue-rules"],
    queryFn: async () => (await slaApi.listQueueRules({ is_active: true })).data.queue_rules || [],
    refetchInterval: 60_000,
  });

  const { data: rawSummary } = useQuery({
    queryKey: ["sla-summary", period],
    queryFn: async () => (await slaApi.getSummary({ days: period })).data,
    refetchInterval: 30_000,
  });

  const { data: rawBreachList } = useQuery({
    queryKey: ["sla-breaches", period],
    queryFn: async () => (await slaApi.listBreaches({ days: period, limit: 200 })).data.breaches || [],
    refetchInterval: 30_000,
  });

  // Mapped data
  const queueMetrics: QueueMetric[] = useMemo(
    () => mapQueueMetrics(rawBreaches || [], rawRules || []),
    [rawBreaches, rawRules],
  );

  const kpis: SLAKPI = useMemo(
    () => mapKPIs(rawSummary || {}, queueMetrics),
    [rawSummary, queueMetrics],
  );

  const breachTickets: BreachTicket[] = useMemo(
    () => mapBreachTickets(rawBreachList || [], queueMetrics),
    [rawBreachList, queueMetrics],
  );

  const resetFilters = useCallback(() => {
    setSearch("");
    setGroupBy("all");
    setKindFilter("all");
    setQueueFilter("all");
    setSevFilter("all");
  }, []);

  // Drawer handlers
  const openQueueDrawer = useCallback((q: QueueMetric) => {
    setDrawerKind("queue");
    setDrawerPayload(q);
    setDrawerOpen(true);
  }, []);

  const openTicketDrawer = useCallback((t: BreachTicket) => {
    setDrawerKind("ticket");
    setDrawerPayload(t);
    setDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    setDrawerKind(null);
    setDrawerPayload(null);
  }, []);

  // CSV export (lazy — reads current state from refs to avoid hoisting issues)
  const exportCSV = useCallback(() => {
    try {
      let csv = "\uFEFF";
      if (view === "matrix") {
        csv += `${t("slaMonitor.queue")},${t("slaConfig.priority")},${t("slaMonitor.tickets")},${t("analytics.breachedResponse")},${t("analytics.breachedResolution")},% SLA ${t("slaConfig.responseTime")},% SLA ${t("slaConfig.resolutionTime")}\n`;
        for (const q of queueMetrics) {
          if (search && !q.name.toLowerCase().includes(search.toLowerCase())) continue;
          csv += `"${q.name}",${q.priority},${q.tickets},${q.reaction.breached},${q.resolution.breached},${q.reaction.pct_ok},${q.resolution.pct_ok}\n`;
        }
      } else if (view === "feed") {
        csv += `${t("tickets.columns.ticketNo")},${t("common.title")},${t("common.queue")},${t("common.owner")},${t("analytics.riskLevel")},${t("slaMonitor.overdue")}\n`;
        for (const b of breachTickets) {
          csv += `${b.ticket_number},"${b.title}","${b.queue}","${b.owner}","${b.severity}",${Math.max(b.over_reaction_min, b.over_resolution_min)}\n`;
        }
      }
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sla_monitor_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(t("common.download"));
    } catch {
      message.error(t("reports.failedToDownload"));
    }
  }, [view, search, queueMetrics, breachTickets, t]);

  // ── View data ──

  const matrixData = useMemo(() => {
    let arr = queueMetrics;
    if (search) {
      const s = search.toLowerCase();
      arr = arr.filter((q) => q.name.toLowerCase().includes(s));
    }
    if (groupBy === "support") arr = arr.filter((q) => q.name.startsWith("Support"));
    else if (groupBy === "infra") arr = arr.filter((q) => q.name.startsWith("Infrastructure"));
    else if (groupBy === "biz") arr = arr.filter((q) => ["Billing", "Finance", "HR", "Development", "Security"].includes(q.name));

    const dir = sortDir === "desc" ? -1 : 1;
    return [...arr].sort((a, b) => {
      let va: any, vb: any;
      switch (sortKey) {
        case "name": va = a.name; vb = b.name; break;
        case "priority": va = a.priority; vb = b.priority; break;
        case "tickets": va = a.tickets; vb = b.tickets; break;
        case "r_in": va = a.reaction.in_time; vb = b.reaction.in_time; break;
        case "r_breached": va = a.reaction.breached; vb = b.reaction.breached; break;
        case "r_pct": va = a.reaction.pct_ok; vb = b.reaction.pct_ok; break;
        case "r_avg": va = a.reaction.avg_sec; vb = b.reaction.avg_sec; break;
        case "q_in": va = a.resolution.in_time; vb = b.resolution.in_time; break;
        case "q_breached": va = a.resolution.breached; vb = b.resolution.breached; break;
        case "q_pct": va = a.resolution.pct_ok; vb = b.resolution.pct_ok; break;
        case "q_avg": va = a.resolution.avg_sec; vb = b.resolution.avg_sec; break;
        default: va = 0; vb = 0;
      }
      if (typeof va === "string") return va.localeCompare(vb) * dir;
      return (va - vb) * dir;
    });
  }, [queueMetrics, search, groupBy, sortKey, sortDir]);

  const splitReaction = useMemo(
    () => [...queueMetrics].filter((q) => !search || q.name.toLowerCase().includes(search.toLowerCase())).sort((a, b) => b.reaction.breached - a.reaction.breached),
    [queueMetrics, search],
  );

  const splitResolution = useMemo(
    () => [...queueMetrics].filter((q) => !search || q.name.toLowerCase().includes(search.toLowerCase())).sort((a, b) => b.resolution.breached - a.resolution.breached),
    [queueMetrics, search],
  );

  const feedData = useMemo(() => {
    let arr = breachTickets;
    if (kindFilter !== "all") {
      arr = arr.filter((t) => kindFilter === "both" ? t.kind === "both" : (t.kind === kindFilter || t.kind === "both"));
    }
    if (queueFilter !== "all") arr = arr.filter((t) => t.queue_id === queueFilter);
    if (sevFilter !== "all") arr = arr.filter((t) => t.severity === sevFilter);
    if (search) {
      const s = search.toLowerCase();
      arr = arr.filter((t) =>
        t.title.toLowerCase().includes(s) || t.queue.toLowerCase().includes(s) ||
        t.ticket_number.toLowerCase().includes(s) || (t.owner || "").toLowerCase().includes(s),
      );
    }
    const dir = sortDirFeed === "desc" ? -1 : 1;
    return [...arr].sort((a, b) => {
      let va: any, vb: any;
      switch (sortKeyFeed) {
        case "ticket": va = a.id; vb = b.id; break;
        case "queue": va = a.queue; vb = b.queue; break;
        case "owner": va = a.owner; vb = b.owner; break;
        case "overdue": va = Math.max(a.over_reaction_min, a.over_resolution_min); vb = Math.max(b.over_reaction_min, b.over_resolution_min); break;
        case "severity": va = a.severity === "crit" ? 3 : a.severity === "high" ? 2 : 1; vb = b.severity === "crit" ? 3 : b.severity === "high" ? 2 : 1; break;
        case "kind": va = a.kind; vb = b.kind; break;
        default: va = 0; vb = 0;
      }
      if (typeof va === "string") return va.localeCompare(vb) * dir;
      return (va - vb) * dir;
    });
  }, [breachTickets, search, kindFilter, queueFilter, sevFilter, sortKeyFeed, sortDirFeed]);

  const toggleSort = (key: string) => {
    setSortKey((prev) => {
      if (prev === key) setSortDir((d) => (d === "desc" ? "asc" : "desc"));
      else setSortDir("desc");
      return key;
    });
  };

  const toggleSortFeed = (key: string) => {
    setSortKeyFeed((prev) => {
      if (prev === key) setSortDirFeed((d) => (d === "desc" ? "asc" : "desc"));
      else setSortDirFeed("desc");
      return key;
    });
  };

  // Matrix totals
  const matrixTotals = useMemo(() => matrixData.reduce(
    (s, q) => ({
      tickets: s.tickets + q.tickets,
      r_in: s.r_in + q.reaction.in_time,
      r_breached: s.r_breached + q.reaction.breached,
      q_in: s.q_in + q.resolution.in_time,
      q_breached: s.q_breached + q.resolution.breached,
    }),
    { tickets: 0, r_in: 0, r_breached: 0, q_in: 0, q_breached: 0 },
  ), [matrixData]);

  const totalReactPct = +(((matrixTotals.r_in) / Math.max(matrixTotals.tickets, 1)) * 100).toFixed(1);
  const totalResolvePct = +(((matrixTotals.q_in) / Math.max(matrixTotals.tickets, 1)) * 100).toFixed(1);

  // ── Table columns for Matrix view ──

  const sortArrow = (key: string) => {
    if (sortKey !== key) return "";
    return sortDir === "desc" ? " ↓" : " ↑";
  };

  const matrixColumns: any[] = [
    {
      title: <>{t("slaMonitor.queue")}{sortArrow("name")}</>,
      dataIndex: "name",
      key: "name",
      width: 220,
      render: (_: string, r: QueueMetric) => (
        <div>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</div>
          <div style={{ fontSize: 11, color: "#888" }}>
            {t("slaConfig.responseTime")}: {fmtDuration(r.target_response)} / {t("slaConfig.resolutionTime")}: {fmtDuration(r.target_resolution)} · {r.calendar}
          </div>
        </div>
      ),
    },
    {
      title: <>{t("slaConfig.priority")}{sortArrow("priority")}</>,
      dataIndex: "priority",
      key: "priority",
      width: 80,
      render: (v: number) => (
        <Tag color={v >= 20 ? "red" : v >= 10 ? "orange" : v >= 5 ? "blue" : "default"}>{v}</Tag>
      ),
    },
    {
      title: <div style={{ textAlign: "right" }}>{t("slaMonitor.tickets")}{sortArrow("tickets")}</div>,
      dataIndex: "tickets",
      key: "tickets",
      width: 80,
      align: "right" as const,
      render: (v: number) => <strong>{fmtNum(v)}</strong>,
    },
    {
      title: <div style={{ color: "#fa8c16" }}>⏱ {t("slaConfig.responseTime")}</div>,
      children: [
        {
          title: <>{t("slaMonitor.inTime")}{sortArrow("r_in")}</>,
          dataIndex: ["reaction", "in_time"],
          key: "r_in",
          width: 70,
          align: "right" as const,
          render: (v: number) => <span style={{ color: "#888" }}>{fmtNum(v)}</span>,
        },
        {
          title: <>{t("slaMonitor.breached")}{sortArrow("r_breached")}</>,
          dataIndex: ["reaction", "breached"],
          key: "r_breached",
          width: 90,
          render: (v: number, r: QueueMetric) => <CountPill value={v} total={r.tickets} />,
        },
        {
          title: <>% SLA{sortArrow("r_pct")}</>,
          dataIndex: ["reaction", "pct_ok"],
          key: "r_pct",
          width: 120,
          render: (v: number) => <PctBar pct={v} />,
        },
        {
          title: <>{t("slaMonitor.avg")}{sortArrow("r_avg")}</>,
          dataIndex: ["reaction", "avg_sec"],
          key: "r_avg",
          width: 80,
          align: "right" as const,
          render: (v: number) => <span style={{ color: "#888" }}>{fmtDuration(v)}</span>,
        },
      ],
    },
    {
      title: <div style={{ color: "#722ed1" }}>✓ {t("slaConfig.resolutionTime")}</div>,
      children: [
        {
          title: <>{t("slaMonitor.inTime")}{sortArrow("q_in")}</>,
          dataIndex: ["resolution", "in_time"],
          key: "q_in",
          width: 70,
          align: "right" as const,
          render: (v: number) => <span style={{ color: "#888" }}>{fmtNum(v)}</span>,
        },
        {
          title: <>{t("slaMonitor.breached")}{sortArrow("q_breached")}</>,
          dataIndex: ["resolution", "breached"],
          key: "q_breached",
          width: 90,
          render: (v: number, r: QueueMetric) => <CountPill value={v} total={r.tickets} />,
        },
        {
          title: <>% SLA{sortArrow("q_pct")}</>,
          dataIndex: ["resolution", "pct_ok"],
          key: "q_pct",
          width: 120,
          render: (v: number) => <PctBar pct={v} />,
        },
        {
          title: <>{t("slaMonitor.avg")}{sortArrow("q_avg")}</>,
          dataIndex: ["resolution", "avg_sec"],
          key: "q_avg",
          width: 80,
          align: "right" as const,
          render: (v: number) => <span style={{ color: "#888" }}>{fmtDuration(v)}</span>,
        },
      ],
    },
    {
      title: t("slaMonitor.trend"),
      key: "trend",
      width: 130,
      render: (_: any, r: QueueMetric) => (
        <Space size={4}>
          <Sparkline data={r.reaction.trend} color="#fa8c16" />
          <Sparkline data={r.resolution.trend} color="#722ed1" />
        </Space>
      ),
    },
  ];

  const filterBySeverity = (t: any) => {
    if (sevFilter === "all") return true;
    return t.severity === sevFilter;
  };

  const sevLabel: Record<string, string> = { warn: "Предупр.", high: "Высокий", crit: "Критич." };
  const kindLabel: Record<string, string> = { reaction: "Реакция", resolution: "Решение", both: "Оба" };
  const kindColor: Record<string, string> = { reaction: "orange", resolution: "purple", both: "red" };

  if (breachesLoading && queueMetrics.length === 0) {
    return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div>
          <Space>
            <Typography.Title level={4} style={{ margin: 0 }}>{t("slaMonitor.title")}</Typography.Title>
            <Badge status={isConnected ? "success" : "error"} text={isConnected ? t("common.connected") : t("common.disconnected")} />
          </Space>
          <div style={{ color: "#888", fontSize: 13, marginTop: 2 }}>
            {t("slaMonitor.subtitle", { days: period })}
          </div>
        </div>
        <Space>
          <Select value={period} onChange={setPeriod} style={{ width: 150 }}>
            <Select.Option value={1}>{t("slaMonitor.today")}</Select.Option>
            <Select.Option value={7}>{t("dashboard.last7days")}</Select.Option>
            <Select.Option value={30}>{t("dashboard.last30days")}</Select.Option>
            <Select.Option value={90}>{t("dashboard.last90days")}</Select.Option>
          </Select>
          <Button icon={<DownloadOutlined />} onClick={exportCSV}>{t("common.download")}</Button>
          <Button type="primary" icon={<AimOutlined />} onClick={() => message.info(t("slaMonitor.goToConfig"))}>
            {t("slaConfig.title")}
          </Button>
        </Space>
      </div>

      <style>{feedRowIn}</style>
      <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <KpiCard title={t("slaMonitor.totalTickets")} value={fmtNum(kpis.total_tickets)} small />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <KpiCard title={t("slaMonitor.slaBy", { type: t("slaConfig.responseTime") })} value={fmtPct(kpis.overall_reaction_pct)} color={pctColor(kpis.overall_reaction_pct)} small />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <KpiCard title={t("slaMonitor.slaBy", { type: t("slaConfig.resolutionTime") })} value={fmtPct(kpis.overall_resolution_pct)} color={pctColor(kpis.overall_resolution_pct)} small />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <KpiCard title={t("slaMonitor.breachedBy", { type: t("slaConfig.responseTime") })} value={fmtNum(kpis.total_reaction_breach)} color={palette.accent.amber} small />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <KpiCard title={t("slaMonitor.breachedBy", { type: t("slaConfig.resolutionTime") })} value={fmtNum(kpis.total_resolution_breach)} color={palette.accent.indigo} small />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <KpiCard title={t("slaMonitor.queuesAtRisk")} value={kpis.queues_at_risk} color={kpis.queues_at_risk > 0 ? palette.accent.rose : palette.accent.emerald} small />
        </Col>
      </Row>

      {/* View switcher + filters */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <Segmented
          value={view}
          onChange={(v) => setView(v as string)}
          options={[
            { label: t("slaMonitor.viewMatrix"), value: "matrix" },
            { label: t("slaMonitor.viewSplit"), value: "split" },
            { label: "📋 " + t("slaMonitor.viewFeed"), value: "feed" },
          ]}
        />
        <Space wrap>
          <Input
            prefix={<SearchOutlined />}
            placeholder={t("slaMonitor.searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 240 }}
            allowClear
          />
          {view === "matrix" && (
            <Segmented
              value={groupBy}
              onChange={(v) => setGroupBy(v as string)}
              options={[
                { label: `${t("common.all")} (${queueMetrics.length})`, value: "all" },
                { label: "Support", value: "support" },
                { label: "Infra", value: "infra" },
                { label: t("slaMonitor.biz"), value: "biz" },
              ]}
              size="small"
            />
          )}
          {view === "feed" && (
            <>
              <Segmented
                value={kindFilter}
                onChange={(v) => setKindFilter(v as string)}
                size="small"
                options={[
                  { label: t("common.all"), value: "all" },
                  { label: <><span style={{ color: "#fa8c16" }}>●</span> {t("slaConfig.responseTime")}</>, value: "reaction" },
                  { label: <><span style={{ color: "#722ed1" }}>●</span> {t("slaConfig.resolutionTime")}</>, value: "resolution" },
                  { label: <><span style={{ color: "#ff4d4f" }}>●</span> {t("slaMonitor.both")}</>, value: "both" },
                ]}
              />
              <Select value={queueFilter} onChange={setQueueFilter} style={{ minWidth: 160 }} size="small">
                <Select.Option value="all">{t("slaMonitor.allQueues")}</Select.Option>
                {queueMetrics.map((q) => (
                  <Select.Option key={q.id} value={q.id}>{q.name}</Select.Option>
                ))}
              </Select>
              <Select value={sevFilter} onChange={setSevFilter} style={{ width: 120 }} size="small">
                <Select.Option value="all">{t("slaMonitor.anySeverity")}</Select.Option>
                <Select.Option value="warn">{t("slaMonitor.sevWarn")}</Select.Option>
                <Select.Option value="high">{t("slaMonitor.sevHigh")}</Select.Option>
                <Select.Option value="crit">{t("slaMonitor.sevCrit")}</Select.Option>
              </Select>
            </>
          )}
          <Button size="small" icon={<ReloadOutlined />} onClick={resetFilters}>
            {t("slaMonitor.reset")}
          </Button>
        </Space>
      </div>

      {/* ── Matrix View ── */}
      {view === "matrix" && (
        <div style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}` }}>
            <Space>
              <span style={sectionTitle}>{t("slaMonitor.matrixTitle")}</span>
              <Space size="small" style={{ fontSize: 11 }}>
                <Tag color="green">≥95%</Tag>
                <Tag color="gold">90–95%</Tag>
                <Tag color="red">80–90%</Tag>
                <Tag color="#a8071a">&lt;80%</Tag>
              </Space>
            </Space>
          </div>
          <Table
            dataSource={matrixData}
            rowKey="id"
            size="small"
            pagination={false}
            scroll={{ x: 1100 }}
            columns={matrixColumns}
            onRow={(record) => ({
              onClick: () => openQueueDrawer(record),
              style: { cursor: "pointer" },
            })}
            onChange={(_pagination, _filters, sorter: any) => {
              if (sorter.columnKey) {
                toggleSort(sorter.columnKey as string);
              }
            }}
            summary={() => (
              <Table.Summary>
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}>
                    <strong>{t("slaMonitor.total")} ({matrixData.length})</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1} />
                  <Table.Summary.Cell index={2} align="right">
                    <strong>{fmtNum(matrixTotals.tickets)}</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">
                    <span style={{ color: "#888" }}>{fmtNum(matrixTotals.r_in)}</span>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4}>
                    <CountPill value={matrixTotals.r_breached} total={matrixTotals.tickets} />
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5}>
                    <PctBar pct={totalReactPct} />
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} />
                  <Table.Summary.Cell index={7} align="right">
                    <span style={{ color: "#888" }}>{fmtNum(matrixTotals.q_in)}</span>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={8}>
                    <CountPill value={matrixTotals.q_breached} total={matrixTotals.tickets} />
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={9}>
                    <PctBar pct={totalResolvePct} />
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={10} />
                  <Table.Summary.Cell index={11} />
                </Table.Summary.Row>
              </Table.Summary>
            )}
          />
        </div>
      )}

      {/* ── Split View ── */}
      {view === "split" && (
        <Row gutter={12}>
          <Col span={12}>
            <div style={cardStyle}>
              <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ ...sectionTitle, color: palette.accent.amber }}>⏱ {t("slaMonitor.reactionBreaches")}</span>
                <span style={{ fontSize: 11, color: palette.text.tertiary }}>{t("slaMonitor.byBreachCount")}</span>
              </div>
              {splitReaction.map((q) => {
                const breach = q.reaction.breached;
                const pct = q.reaction.pct_ok;
                return (
                  <div
                    key={q.id}
                    onClick={() => openQueueDrawer(q)}
                    style={{ display: "flex", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f0f0f0", cursor: "pointer", gap: 8 }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{q.name}</div>
                      <div style={{ fontSize: 11, color: "#888" }}>{fmtNum(q.tickets)} {t("slaMonitor.tickets").toLowerCase()} · {t("slaMonitor.target")}: {fmtDuration(q.target_response)}</div>
                    </div>
                    <CountPill value={breach} total={q.tickets} />
                    <div style={{ width: 100, display: "flex", alignItems: "center", gap: 4 }}>
                      <div style={{ flex: 1, height: 8, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
                        <div style={{ width: `${(breach / Math.max(splitReaction[0]?.reaction.breached || 0, 1)) * 100}%`, height: "100%", background: "#fa8c16", borderRadius: 4 }} />
                      </div>
                    </div>
                    <span style={{ width: 50, textAlign: "right", fontWeight: 600, color: pctColor(pct) }}>{pct}%</span>
                  </div>
                );
              })}
              {splitReaction.length === 0 && <div style={{ padding: 20, textAlign: "center", color: "#888" }}>{t("slaMonitor.noBreaches")}</div>}
            </div>
          </Col>
          <Col span={12}>
            <div style={cardStyle}>
              <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ ...sectionTitle, color: palette.accent.indigo }}>✓ {t("slaMonitor.resolutionBreaches")}</span>
                <span style={{ fontSize: 11, color: palette.text.tertiary }}>{t("slaMonitor.byBreachCount")}</span>
              </div>
              {splitResolution.map((q) => {
                const breach = q.resolution.breached;
                const pct = q.resolution.pct_ok;
                return (
                  <div
                    key={q.id}
                    onClick={() => openQueueDrawer(q)}
                    style={{ display: "flex", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f0f0f0", cursor: "pointer", gap: 8 }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{q.name}</div>
                      <div style={{ fontSize: 11, color: "#888" }}>{fmtNum(q.tickets)} {t("slaMonitor.tickets").toLowerCase()} · {t("slaMonitor.target")}: {fmtDuration(q.target_resolution)}</div>
                    </div>
                    <CountPill value={breach} total={q.tickets} />
                    <div style={{ width: 100, display: "flex", alignItems: "center", gap: 4 }}>
                      <div style={{ flex: 1, height: 8, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
                        <div style={{ width: `${(breach / Math.max(splitResolution[0]?.resolution.breached || 0, 1)) * 100}%`, height: "100%", background: "#722ed1", borderRadius: 4 }} />
                      </div>
                    </div>
                    <span style={{ width: 50, textAlign: "right", fontWeight: 600, color: pctColor(pct) }}>{pct}%</span>
                  </div>
                );
              })}
              {splitResolution.length === 0 && <div style={{ padding: 20, textAlign: "center", color: "#888" }}>{t("slaMonitor.noBreaches")}</div>}
            </div>
          </Col>
        </Row>
      )}

      {/* ── Feed View ── */}
      {view === "feed" && (
        <div style={cardStyle}>
          <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Space>
              <span style={sectionTitle}>{t("slaMonitor.feedTitle")}</span>
              <span style={{ fontWeight: 400, fontSize: 12, color: palette.text.tertiary }}>{fmtNum(feedData.length)} {t("slaMonitor.tickets").toLowerCase()}</span>
            </Space>
            <Space size="small">
              <span style={{ fontSize: 11, color: palette.text.tertiary }}>{t("slaMonitor.sortBy")}:</span>
              <Select
                value={`${sortKeyFeed}-${sortDirFeed}`}
                onChange={(v) => { const [k, d] = v.split("-"); setSortKeyFeed(k); setSortDirFeed(d as "asc" | "desc"); }}
                size="small"
                style={{ width: 160 }}
              >
                <Select.Option value="overdue-desc">{t("slaMonitor.sortOverdue")}</Select.Option>
                <Select.Option value="severity-desc">{t("slaMonitor.sortSeverity")}</Select.Option>
                <Select.Option value="queue-asc">{t("slaMonitor.sortQueue")}</Select.Option>
                <Select.Option value="ticket-desc">{t("slaMonitor.sortTicket")}</Select.Option>
              </Select>
            </Space>
          </div>
          {feedData.length > 0 ? (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "100px 1fr 140px 90px 120px 80px", gap: 8, padding: "8px 12px", background: palette.page, fontWeight: 600, fontSize: 11, color: palette.text.tertiary, borderBottom: `1px solid ${palette.borderLight}`, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                <div>{t("slaMonitor.ticket")}</div>
                <div>{t("common.title")}</div>
                <div>{t("common.queue")}</div>
                <div>{t("slaMonitor.type")}</div>
                <div>{t("slaMonitor.overdue")}</div>
                <div style={{ textAlign: "right" }}>{t("analytics.riskLevel")}</div>
              </div>
              {feedData.slice(0, 60).map((bt, idx) => (
                <div
                  key={bt.id}
                  onClick={() => openTicketDrawer(bt)}
                  style={{ display: "grid", gridTemplateColumns: "100px 1fr 140px 90px 120px 80px", gap: 8, padding: "10px 12px", borderBottom: `1px solid ${palette.borderLight}`, cursor: "pointer", alignItems: "center", fontSize: 13, animation: `feedRowIn 0.3s ease-out ${idx * 0.02}s both` }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = palette.page)}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                >
                  <span style={{ fontFamily: typography.fontMono, fontSize: 12, color: palette.brand[500], fontWeight: 600 }}>{bt.ticket_number}</span>
                  <div>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: palette.text.primary }}>{bt.title}</div>
                    <div style={{ fontSize: 11, color: palette.text.tertiary, marginTop: 2 }}>{bt.created_at} · {bt.owner}</div>
                  </div>
                  <div><Tag style={{ fontSize: 11 }}>{bt.queue}</Tag></div>
                  <div><Tag color={kindColor[bt.kind]} style={{ fontSize: 11 }}>{kindLabel[bt.kind]}</Tag></div>
                  <div>
                    {(bt.kind === "reaction" || bt.kind === "both") && bt.over_reaction_min > 0 && (
                      <div style={{ fontSize: 12, color: bt.over_reaction_min > 180 ? palette.accent.rose : bt.over_reaction_min > 30 ? palette.accent.amber : "#d48806" }}>
                        {t("slaConfig.responseTime")}: +{fmtDuration(bt.over_reaction_min * 60)}
                      </div>
                    )}
                    {(bt.kind === "resolution" || bt.kind === "both") && bt.over_resolution_min > 0 && (
                      <div style={{ fontSize: 12, color: bt.over_resolution_min > 480 ? palette.accent.rose : bt.over_resolution_min > 120 ? palette.accent.amber : "#d48806" }}>
                        {t("slaConfig.resolutionTime")}: +{fmtDuration(bt.over_resolution_min * 60)}
                      </div>
                    )}
                    {!((bt.kind === "reaction" || bt.kind === "both") && bt.over_reaction_min > 0) && !((bt.kind === "resolution" || bt.kind === "both") && bt.over_resolution_min > 0) && (
                      <span style={{ color: palette.text.tertiary }}>—</span>
                    )}
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <Tag color={sevTagColor(bt.severity)} style={{ fontSize: 11 }}>{sevLabel[bt.severity]}</Tag>
                  </div>
                </div>
              ))}
              {feedData.length > 60 && (
                <div style={{ padding: 12, textAlign: "center", color: palette.text.disabled, fontSize: 12, borderTop: `1px solid ${palette.borderLight}` }}>
                  {t("slaMonitor.showingLimit", { shown: 60, total: feedData.length })}
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", color: palette.text.tertiary }}>{t("slaMonitor.noBreaches")}</div>
          )}
        </div>
      )}

      {/* Hint */}
      <div style={{ marginTop: 16, padding: "10px 16px", background: "#e6f4ff", borderLeft: "3px solid #1677ff", borderRadius: 6, fontSize: 13, color: "#666" }}>
        <strong style={{ color: "#333" }}>{t("slaMonitor.hint")}</strong> {t("slaMonitor.hintText")}
      </div>

      {/* ── Drawer ── */}
      <Drawer
        title={null}
        placement="right"
        closable={false}
        onClose={closeDrawer}
        open={drawerOpen}
        width={520}
        footer={null}
      >
        {drawerKind === "queue" && drawerPayload && (
          <QueueDrawerContent
            queue={drawerPayload as QueueMetric}
            breachTickets={breachTickets}
            onPickTicket={openTicketDrawer}
            onClose={closeDrawer}
            t={t}
          />
        )}
        {drawerKind === "ticket" && drawerPayload && (
          <TicketDrawerContent
            ticket={drawerPayload as BreachTicket}
            onClose={closeDrawer}
            t={t}
          />
        )}
      </Drawer>
    </div>
  );
}

// ── Queue Drawer Content ──

function QueueDrawerContent({
  queue, breachTickets, onPickTicket, onClose, t,
}: {
  queue: QueueMetric;
  breachTickets: BreachTicket[];
  onPickTicket: (t: BreachTicket) => void;
  onClose: () => void;
  t: any;
}) {
  const qBreached = breachTickets.filter((bt) => bt.queue === queue.name);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <Typography.Title level={5} style={{ margin: 0 }}>{queue.name}</Typography.Title>
          <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
            {t("slaMonitor.queue")} · {t("slaConfig.priority")} {queue.priority} · {queue.calendar}
          </div>
        </div>
        <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
      </div>

      {/* SLA bars */}
      <Card size="small" style={{ background: "#fafafa", marginBottom: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <strong style={{ fontSize: 13 }}>⏱ {t("slaConfig.responseTime")}</strong>
            <span style={{ color: "#888", fontSize: 12 }}>{t("slaMonitor.target")}: {fmtDuration(queue.target_response)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ width: 70, fontSize: 12, color: "#888" }}>{t("slaMonitor.inTime")}</span>
            <div style={{ flex: 1, height: 10, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${queue.reaction.pct_ok}%`, height: "100%", background: "#fa8c16", borderRadius: 4 }} />
            </div>
            <span style={{ width: 50, textAlign: "right", fontWeight: 600 }}>{queue.reaction.pct_ok}%</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 70, fontSize: 12, color: "#888" }}>{t("slaMonitor.breached")}</span>
            <div style={{ flex: 1, height: 10, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${100 - queue.reaction.pct_ok}%`, height: "100%", background: "#ff4d4f", borderRadius: 4 }} />
            </div>
            <span style={{ width: 50, textAlign: "right", color: "#ff4d4f" }}>{queue.reaction.breached}</span>
          </div>
        </div>

        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <strong style={{ fontSize: 13 }}>✓ {t("slaConfig.resolutionTime")}</strong>
            <span style={{ color: "#888", fontSize: 12 }}>{t("slaMonitor.target")}: {fmtDuration(queue.target_resolution)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ width: 70, fontSize: 12, color: "#888" }}>{t("slaMonitor.inTime")}</span>
            <div style={{ flex: 1, height: 10, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${queue.resolution.pct_ok}%`, height: "100%", background: "#722ed1", borderRadius: 4 }} />
            </div>
            <span style={{ width: 50, textAlign: "right", fontWeight: 600 }}>{queue.resolution.pct_ok}%</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 70, fontSize: 12, color: "#888" }}>{t("slaMonitor.breached")}</span>
            <div style={{ flex: 1, height: 10, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${100 - queue.resolution.pct_ok}%`, height: "100%", background: "#ff4d4f", borderRadius: 4 }} />
            </div>
            <span style={{ width: 50, textAlign: "right", color: "#ff4d4f" }}>{queue.resolution.breached}</span>
          </div>
        </div>
      </Card>

      {/* Trend */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <strong style={{ fontSize: 13 }}>{t("slaMonitor.trendTitle")}</strong>
          <Space size="small" style={{ fontSize: 12 }}>
            <span style={{ color: "#fa8c16" }}>● {t("slaConfig.responseTime")}</span>
            <span style={{ color: "#722ed1" }}>● {t("slaConfig.resolutionTime")}</span>
          </Space>
        </div>
        <DualTrend a={queue.reaction.trend} b={queue.resolution.trend} />
      </div>

      {/* Breached tickets */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <strong style={{ fontSize: 13 }}>{t("slaMonitor.breachedTickets")} ({qBreached.length})</strong>
        </div>
        {qBreached.length > 0 ? (
          <div style={{ border: "1px solid #f0f0f0", borderRadius: 6, overflow: "hidden" }}>
            {qBreached.slice(0, 10).map((t) => (
              <div
                key={t.id}
                onClick={() => onPickTicket(t)}
                style={{ padding: "10px 12px", borderBottom: "1px solid #f0f0f0", cursor: "pointer", display: "grid", gridTemplateColumns: "100px 1fr auto", gap: 10, alignItems: "center", fontSize: 13 }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#fafafa")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "")}
              >
                <span style={{ fontFamily: "SF Mono, Menlo, monospace", color: "#1677ff", fontWeight: 600 }}>{t.ticket_number}</span>
                <div>
                  <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.title}</div>
                  <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{t.owner} · {t.created_at}</div>
                </div>
                <Tag color={kindColorMap[t.kind]}>{kindLabelMap[t.kind]}</Tag>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: 20, textAlign: "center", color: "#aaa" }}>{t("slaMonitor.noQueueBreaches")}</div>
        )}
      </div>

      {/* Quick actions */}
      <Card size="small" style={{ background: "#fafafa" }}>
        <strong style={{ fontSize: 13 }}>{t("slaMonitor.quickActions")}</strong>
        <Space style={{ marginTop: 8, flexWrap: "wrap" }}>
          <Button size="small">{t("slaConfig.queueRules")}</Button>
          <Button size="small">{t("slaConfig.businessCalendars")}</Button>
          <Button size="small">{t("slaConfig.escalationRules")}</Button>
          <Button size="small"><DownloadOutlined /> CSV</Button>
        </Space>
      </Card>
    </div>
  );
}

// ── Ticket Drawer Content ──

function TicketDrawerContent({ ticket, onClose, t }: { ticket: BreachTicket; onClose: () => void; t: any }) {
  const events = [
    { when: ticket.created_at, what: t("slaMonitor.ticketCreated"), who: "system" },
    { when: ticket.created_at, what: t("slaMonitor.assignedQueue") + ` ${ticket.queue}`, who: "auto-routing" },
    { when: ticket.created_at, what: ticket.kind === "resolution" ? t("slaMonitor.firstResponded") : t("slaMonitor.responseBreached"), who: ticket.owner },
    ...(ticket.kind !== "reaction" ? [{ when: ticket.created_at, what: t("slaMonitor.resolutionBreached"), who: "sla-engine" }] : []),
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <Space>
            <span style={{ fontFamily: "SF Mono, Menlo, monospace", color: "#1677ff" }}>{ticket.ticket_number}</span>
            <Tag color={kindColorMap[ticket.kind]}>{kindLabelMap[ticket.kind]}</Tag>
          </Space>
          <Typography.Title level={5} style={{ margin: "4px 0 0" }}>{ticket.title}</Typography.Title>
        </div>
        <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <table style={{ width: "100%", fontSize: 13 }}>
          <tbody>
            {[
              [t("common.queue"), <Tag key="q">{ticket.queue}</Tag>],
              [t("common.owner"), ticket.owner],
              [t("slaConfig.priority"), <Tag key="p" color={sevTagColor(ticket.severity)}>{ticket.priority}</Tag>],
              [t("ticketDetail.fields.created"), ticket.created_at],
              [t("slaMonitor.opened"), ticket.opened_min_ago > 0 ? fmtDuration(ticket.opened_min_ago * 60) : "—"],
            ].map(([label, value], i) => (
              <tr key={i} style={{ borderBottom: "1px solid #f0f0f0" }}>
                <td style={{ padding: "6px 0", color: "#888", width: 120 }}>{label}</td>
                <td style={{ padding: "6px 0" }}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Divider />

      <strong style={{ fontSize: 13 }}>{t("slaMonitor.slaVsTarget")}</strong>
      <div style={{ marginTop: 8 }}>
        <div style={{ marginBottom: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ width: 100, fontSize: 12, color: "#888" }}>{t("slaConfig.responseTime")}</span>
            <div style={{ flex: 1, height: 10, background: "#f0f0f0", borderRadius: 4, overflow: "hidden", position: "relative" }}>
              <div style={{ width: `${Math.min(ticket.sla_response_used_pct, 100)}%`, height: "100%", background: ticket.sla_response_used_pct > 100 ? "#ff4d4f" : "#fa8c16", borderRadius: 4 }} />
            </div>
            <span style={{ width: 60, textAlign: "right", color: ticket.sla_response_used_pct > 100 ? "#ff4d4f" : "#333" }}>{ticket.sla_response_used_pct}%</span>
          </div>
          <div style={{ fontSize: 12, color: "#888", marginLeft: 108, marginBottom: 8 }}>
            {t("slaMonitor.target")}: {fmtDuration(ticket.target_response_sec)}
            {ticket.over_reaction_min > 0 && <span style={{ color: "#ff4d4f", marginLeft: 8 }}>· {t("slaMonitor.overdueBy")} {fmtDuration(ticket.over_reaction_min * 60)}</span>}
          </div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ width: 100, fontSize: 12, color: "#888" }}>{t("slaConfig.resolutionTime")}</span>
            <div style={{ flex: 1, height: 10, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${Math.min(ticket.sla_resolution_used_pct, 100)}%`, height: "100%", background: ticket.sla_resolution_used_pct > 100 ? "#ff4d4f" : "#722ed1", borderRadius: 4 }} />
            </div>
            <span style={{ width: 60, textAlign: "right", color: ticket.sla_resolution_used_pct > 100 ? "#ff4d4f" : "#333" }}>{ticket.sla_resolution_used_pct}%</span>
          </div>
          <div style={{ fontSize: 12, color: "#888", marginLeft: 108 }}>
            {t("slaMonitor.target")}: {fmtDuration(ticket.target_resolution_sec)}
            {ticket.over_resolution_min > 0 && <span style={{ color: "#ff4d4f", marginLeft: 8 }}>· {t("slaMonitor.overdueBy")} {fmtDuration(ticket.over_resolution_min * 60)}</span>}
          </div>
        </div>
      </div>

      <Divider />

      <strong style={{ fontSize: 13 }}>{t("slaMonitor.timeline")}</strong>
      <div style={{ marginTop: 8 }}>
        {events.map((e, i) => (
          <div key={i} style={{ display: "flex", gap: 12, padding: "6px 0", borderBottom: "1px solid #f0f0f0", fontSize: 13 }}>
            <span style={{ color: "#888", minWidth: 140, fontSize: 12 }}>{e.when}</span>
            <span>{e.what} <span style={{ color: "#888" }}>· {e.who}</span></span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        <Space>
          <Button type="primary">{t("slaMonitor.openInOtrs")}</Button>
          <Button>{t("slaMonitor.reassign")}</Button>
          <Button>{t("slaMonitor.escalate")}</Button>
        </Space>
      </div>
    </div>
  );
}

// ── Shared constants ──

const kindColorMap: Record<string, string> = { reaction: "orange", resolution: "purple", both: "red" };
const kindLabelMap: Record<string, string> = { reaction: "Реакция", resolution: "Решение", both: "Оба" };

// ── Dual Trend SVG ──

function DualTrend({ a, b }: { a: number[]; b: number[] }) {
  const w = 520; const h = 90; const pad = 8;
  const max = Math.max(...a, ...b, 1);
  const stepX = (w - pad * 2) / (a.length - 1 || 1);
  const toPts = (arr: number[]) => arr.map((v, i) => `${(pad + i * stepX).toFixed(1)},${(h - pad - (v / max) * (h - pad * 2)).toFixed(1)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ background: "#fafafa", borderRadius: 6, border: "1px solid #f0f0f0" }}>
      {[0.25, 0.5, 0.75].map((y) => (
        <line key={y} x1={pad} y1={h - pad - y * (h - pad * 2)} x2={w - pad} y2={h - pad - y * (h - pad * 2)} stroke="#eee" />
      ))}
      <polyline points={toPts(a)} fill="none" stroke="#fa8c16" strokeWidth="2" />
      <polyline points={toPts(b)} fill="none" stroke="#722ed1" strokeWidth="2" />
      {a.map((v, i) => (
        <circle key={"a" + i} cx={pad + i * stepX} cy={h - pad - (v / max) * (h - pad * 2)} r="2.5" fill="#fa8c16" />
      ))}
      {b.map((v, i) => (
        <circle key={"b" + i} cx={pad + i * stepX} cy={h - pad - (v / max) * (h - pad * 2)} r="2.5" fill="#722ed1" />
      ))}
    </svg>
  );
}
