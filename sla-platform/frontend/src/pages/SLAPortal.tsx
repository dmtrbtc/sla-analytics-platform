import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Input, Select, Spin, Tabs, Tag, Button, Table, Empty } from "antd";
import {
  ClockCircleOutlined,
  AimOutlined,
  WarningOutlined,
  HourglassOutlined,
  DownloadOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  ApartmentOutlined,
  HeatMapOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import type { ColumnsType } from "antd/es/table";

import { slaApi, mapQueueMetrics } from "../api/sla";
import { analyticsApi } from "../api/analytics";
import { dashboardsApi } from "../api/dashboards";
import {
  KpiCard,
  HealthPip,
  MetricBar,
  Sparkline,
  ScopeChips,
  SortableHeader,
  DetailDrawer,
  LivePill,
  severityFor,
  SLA_ECHARTS_THEME_NAME,
  type SortDirection,
} from "../design";
import { onWsEvent } from "../hooks/useWebSocket";
import RuntimeErrorBoundary from "../components/safety/RuntimeErrorBoundary";

type ScopeKey = "all" | "support" | "infra" | "biz";
type CalendarKey = "all" | "24x7" | "bh";

// ──────────────────────────────────────────────────────────────────
// Formatters — all-local, no hardcoded text (numbers only).
// ──────────────────────────────────────────────────────────────────
const fmtNum = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("ru-RU");
const fmtMin = (m: number | null | undefined) => {
  if (m == null) return "—";
  const abs = Math.abs(m);
  if (abs === 0) return "0 мин";
  if (abs < 60) return `${Math.round(abs)} мин`;
  if (abs < 24 * 60) {
    const h = Math.floor(abs / 60);
    const mn = Math.round(abs % 60);
    return mn === 0 ? `${h} ч` : `${h} ч ${mn} мин`;
  }
  const d = Math.floor(abs / (24 * 60));
  const h = Math.round((abs % (24 * 60)) / 60);
  return h === 0 ? `${d} д` : `${d} д ${h} ч`;
};

// ──────────────────────────────────────────────────────────────────
// Types — UI shape (mapped from server response).
// ──────────────────────────────────────────────────────────────────
interface PortalQueue {
  id: string;
  name: string;
  priority: number;
  calendar: string;
  tickets: number;
  reaction_pct: number;
  resolution_pct: number;
  reaction_breach: number;
  resolution_breach: number;
  at_risk: number;
  avg_wait_min: number;
  health: number;
  reaction_trend: number[];
  resolution_trend: number[];
}

interface PortalRisk {
  id: string;
  ticket_number: string;
  title: string;
  queue: string;
  owner: string;
  r_used: number;
  s_used: number;
  r_over: boolean;
  s_over: boolean;
  breach_eta_min: number;
}

interface PortalAgent {
  name: string;
  initials: string;
  open: number;
  handled: number;
  sla_pct: number;
  avg_min: number;
  status: "top" | "over" | "norm";
}

interface DailyTrendPoint {
  date: string;
  total: number;
  reaction: number;
  resolution: number;
}

interface HeatmapRow {
  queue: string;
  hours: number[]; // 24 values
}

// ──────────────────────────────────────────────────────────────────
// Inner component — wrapped by RuntimeErrorBoundary at export.
// ──────────────────────────────────────────────────────────────────
function SLAPortalInner() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  // ── Global filters ─────────────────────────────────────────────
  const [period, setPeriod] = useState<number>(30);
  const [scope, setScope] = useState<ScopeKey>("all");
  const [calendar, setCalendar] = useState<CalendarKey>("all");
  const [search, setSearch] = useState("");

  // ── Tabs ───────────────────────────────────────────────────────
  const [tab, setTab] = useState<"queues" | "tickets" | "heat" | "team">(
    "queues",
  );

  // ── Sort state for the queues table ────────────────────────────
  const [sortKey, setSortKey] = useState<string>("health");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");

  // ── Drawer ─────────────────────────────────────────────────────
  const [drawer, setDrawer] = useState<{
    open: boolean;
    kind: "queue" | "ticket" | null;
    payload: PortalQueue | PortalRisk | null;
  }>({ open: false, kind: null, payload: null });

  // ── ESC closes drawer ──────────────────────────────────────────
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape")
        setDrawer((d) => ({ ...d, open: false }));
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, []);

  // ── Live WebSocket — refetch queries on relevant events ────────
  useEffect(() => {
    const types = [
      "sla_breach",
      "ticket_updated",
      "queue_overloaded",
      "ticket_created",
    ];
    const unsubs = types.map((type) =>
      onWsEvent(type, () => {
        qc.invalidateQueries({ queryKey: ["sla-portal"] });
      }),
    );
    return () => {
      unsubs.forEach((u) => u());
    };
  }, [qc]);

  // ──────────────────────────────────────────────────────────────
  // Data queries — every key includes filters so refetch is automatic.
  // ──────────────────────────────────────────────────────────────
  const filterKey = `${period}|${scope}|${calendar}`;

  const queuesQ = useQuery({
    queryKey: ["sla-portal", "queues", filterKey],
    queryFn: async (): Promise<PortalQueue[]> => {
      const [breachesResp, rulesResp] = await Promise.all([
        slaApi.getQueueBreaches({ days: period }),
        slaApi.listQueueRules(),
      ]);
      const breaches = (breachesResp.data as { queues?: unknown[] }).queues || [];
      const rules =
        (rulesResp.data as { items?: unknown[]; rules?: unknown[] }).items ||
        (rulesResp.data as { rules?: unknown[] }).rules ||
        [];
      const mapped = mapQueueMetrics(breaches as never[], rules as never[]);
      return mapped.map<PortalQueue>((q, idx) => ({
        id: q.id || `q-${idx}`,
        name: q.name,
        priority: q.priority,
        calendar: q.calendar,
        tickets: q.tickets,
        reaction_pct: q.reaction.pct_ok,
        resolution_pct: q.resolution.pct_ok,
        reaction_breach: q.reaction.breached,
        resolution_breach: q.resolution.breached,
        at_risk: q.at_risk,
        avg_wait_min: q.avg_wait_min,
        health: q.health,
        reaction_trend: q.reaction.trend,
        resolution_trend: q.resolution.trend,
      }));
    },
    refetchInterval: 30_000,
  });

  const trendQ = useQuery({
    queryKey: ["sla-portal", "trend", filterKey],
    queryFn: async (): Promise<DailyTrendPoint[]> => {
      const { data } = await analyticsApi.dailyTrend({
        days: period,
        scope,
        calendar,
      });
      return ((data as { daily?: DailyTrendPoint[] }).daily || []).map(
        (d) => ({ ...d, date: d.date }),
      );
    },
    refetchInterval: 60_000,
  });

  // Server-side summary is kept warm so the WS-invalidate cascade picks
  // up KPI changes even though the displayed numbers come from `scopedKpi`
  // (computed locally from the queue list). Result is intentionally unused.
  useQuery({
    queryKey: ["sla-portal", "summary", filterKey],
    queryFn: async () => {
      const { data } = await slaApi.getSummary({ days: period });
      return data as Record<string, number>;
    },
    refetchInterval: 60_000,
  });

  const heatmapQ = useQuery({
    queryKey: ["sla-portal", "heatmap", filterKey],
    queryFn: async (): Promise<HeatmapRow[]> => {
      const { data } = await analyticsApi.queueHeatmap({ days: period });
      const raw =
        (data as { heatmap?: Array<{ queue: string; hour: number; breach_count: number }> })
          .heatmap || [];
      // Pivot {queue, hour, breach_count} → {queue, hours: number[24]}
      const byQueue = new Map<string, number[]>();
      for (const row of raw) {
        if (!byQueue.has(row.queue)) byQueue.set(row.queue, Array(24).fill(0));
        const arr = byQueue.get(row.queue)!;
        arr[row.hour] = (arr[row.hour] || 0) + row.breach_count;
      }
      return [...byQueue.entries()]
        .map(([queue, hours]) => ({ queue, hours }))
        .sort(
          (a, b) =>
            b.hours.reduce((s, n) => s + n, 0) -
            a.hours.reduce((s, n) => s + n, 0),
        )
        .slice(0, 20);
    },
    refetchInterval: 120_000,
  });

  const risksQ = useQuery({
    queryKey: ["sla-portal", "risks", filterKey],
    queryFn: async (): Promise<PortalRisk[]> => {
      const { data } = await analyticsApi.slaRisks({ limit: 100 });
      const list =
        (data as { risks?: Array<Record<string, unknown>> }).risks || [];
      return list.map((r, idx) => {
        const used = Number(r.sla_risk_score) || 0;
        const isResp = String(r.metric_name || "").includes("response");
        const isResol = String(r.metric_name || "").includes("resolution");
        const breached = Boolean(r.sla_breached);
        const remainSec = Number(r.time_remaining_seconds) || 0;
        return {
          id: String(r.ticket_id ?? idx),
          ticket_number: `T-${r.ticket_id ?? idx}`,
          title:
            (r.risk_reason as string) ||
            `${String(r.metric_name || "SLA")} в зоне риска`,
          queue: (r.queue_name as string) || "—",
          owner: (r.owner as string) || "—",
          r_used: isResp ? used : 0,
          s_used: isResol ? used : 0,
          r_over: isResp && breached,
          s_over: isResol && breached,
          breach_eta_min: Math.round(remainSec / 60),
        };
      });
    },
    refetchInterval: 30_000,
  });

  const agentsQ = useQuery({
    queryKey: ["sla-portal", "agents", filterKey],
    queryFn: async (): Promise<PortalAgent[]> => {
      const { data } = await dashboardsApi.agentWorkload({ days: period });
      const list =
        (data as { agents?: Array<Record<string, unknown>> }).agents ||
        (data as { workload?: Array<Record<string, unknown>> }).workload ||
        [];
      return list.map((a) => {
        const name = String(a.owner || a.agent || a.name || "—");
        const initials = name
          .split(/\s|\./)
          .filter(Boolean)
          .slice(0, 2)
          .map((w) => w[0]?.toUpperCase() ?? "")
          .join("");
        const open = Number(a.open_tickets ?? a.open ?? 0);
        const handled = Number(a.tickets_handled ?? a.handled ?? 0);
        const slaPct = Number(a.sla_compliance_pct ?? a.sla_pct ?? 100);
        const avgMin = Math.round(
          Number(a.avg_handle_seconds ?? a.avg_seconds ?? 0) / 60,
        );
        const status: PortalAgent["status"] =
          open > 20 ? "over" : slaPct >= 95 ? "top" : "norm";
        return {
          name,
          initials: initials || "—",
          open,
          handled,
          sla_pct: Math.round(slaPct),
          avg_min: avgMin,
          status,
        };
      });
    },
    refetchInterval: 60_000,
  });

  // ──────────────────────────────────────────────────────────────
  // Derived state (filtered/sorted).
  // ──────────────────────────────────────────────────────────────
  const filteredQueues = useMemo(() => {
    const list = queuesQ.data || [];
    return list.filter((q) => {
      if (scope === "support" && !/^support/i.test(q.name)) return false;
      if (scope === "infra" && !/^infra/i.test(q.name)) return false;
      if (
        scope === "biz" &&
        (/^support/i.test(q.name) || /^infra/i.test(q.name))
      )
        return false;
      if (calendar === "24x7" && q.calendar !== "24×7") return false;
      if (calendar === "bh" && q.calendar === "24×7") return false;
      if (
        search &&
        !q.name.toLowerCase().includes(search.toLowerCase())
      )
        return false;
      return true;
    });
  }, [queuesQ.data, scope, calendar, search]);

  const sortedQueues = useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1;
    const get = (q: PortalQueue) => {
      switch (sortKey) {
        case "name":
          return q.name;
        case "priority":
          return q.priority;
        case "tickets":
          return q.tickets;
        case "reaction":
          return q.reaction_pct;
        case "resolution":
          return q.resolution_pct;
        case "rbreach":
          return q.reaction_breach;
        case "sbreach":
          return q.resolution_breach;
        case "at_risk":
          return q.at_risk;
        case "wait":
          return q.avg_wait_min;
        case "health":
        default:
          return q.health;
      }
    };
    return [...filteredQueues].sort((a, b) => {
      const va = get(a) as number | string;
      const vb = get(b) as number | string;
      if (typeof va === "string")
        return (va as string).localeCompare(vb as string) * dir;
      return ((va as number) - (vb as number)) * dir;
    });
  }, [filteredQueues, sortKey, sortDir]);

  const filteredQueueNames = useMemo(
    () => new Set(filteredQueues.map((q) => q.name)),
    [filteredQueues],
  );

  const filteredRisks = useMemo(
    () =>
      (risksQ.data || []).filter((r) => filteredQueueNames.has(r.queue)),
    [risksQ.data, filteredQueueNames],
  );

  const filteredHeatmap = useMemo(
    () =>
      (heatmapQ.data || []).filter((r) => filteredQueueNames.has(r.queue)),
    [heatmapQ.data, filteredQueueNames],
  );

  // ── Scoped KPIs (mirror prototype's `scopedKpi`) ────────────────
  const scopedKpi = useMemo(() => {
    const total =
      filteredQueues.reduce((s, q) => s + q.tickets, 0) || 0;
    const rB = filteredQueues.reduce((s, q) => s + q.reaction_breach, 0);
    const sB = filteredQueues.reduce((s, q) => s + q.resolution_breach, 0);
    const atRisk = filteredQueues.reduce((s, q) => s + q.at_risk, 0);
    const rPct =
      total > 0 ? +(((total - rB) / total) * 100).toFixed(1) : 100;
    const sPct =
      total > 0 ? +(((total - sB) / total) * 100).toFixed(1) : 100;
    const avgWait = filteredQueues.length
      ? Math.round(
          filteredQueues.reduce((s, q) => s + q.avg_wait_min, 0) /
            filteredQueues.length,
        )
      : 0;
    return {
      rPct,
      sPct,
      rB,
      sB,
      atRisk,
      total,
      avgWait,
      qCount: filteredQueues.length,
    };
  }, [filteredQueues]);

  // ── Top queues by total breaches (for horizontal bar chart) ─────
  const topByBreaches = useMemo(
    () =>
      [...filteredQueues]
        .sort(
          (a, b) =>
            b.reaction_breach +
            b.resolution_breach -
            (a.reaction_breach + a.resolution_breach),
        )
        .slice(0, 8),
    [filteredQueues],
  );

  // ── ECharts options — stacked area + horizontal bars + heatmap ──
  const trendOption = useMemo(
    () => buildTrendOption(trendQ.data || [], t),
    [trendQ.data, t],
  );

  const topQueuesOption = useMemo(
    () => buildTopQueuesOption(topByBreaches, t),
    [topByBreaches, t],
  );

  const heatmapOption = useMemo(
    () => buildHeatmapOption(filteredHeatmap, t),
    [filteredHeatmap, t],
  );

  // ──────────────────────────────────────────────────────────────
  // Table columns — queues
  // ──────────────────────────────────────────────────────────────
  const onSort = (key: string) => {
    setSortDir((prev) =>
      sortKey === key ? (prev === "asc" ? "desc" : "asc") : "asc",
    );
    setSortKey(key);
  };

  const queueColumns: ColumnsType<PortalQueue> = useMemo(
    // onSort is a stable closure over set-state setters that React
    // guarantees are referentially stable — safe to omit from deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    () => [
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.queue")}
            active={sortKey === "name"}
            direction={sortDir}
          />
        ),
        key: "name",
        onHeaderCell: () => ({ onClick: () => onSort("name") }),
        render: (_, q) => (
          <div>
            <div
              style={{
                fontWeight: 600,
                fontSize: 13.5,
                color: "var(--ink)",
                letterSpacing: "-0.1px",
              }}
            >
              {q.name}
            </div>
            <div
              className="mono"
              style={{
                fontSize: 11.5,
                color: "var(--ink-3)",
                marginTop: 3,
              }}
            >
              {q.calendar}
            </div>
          </div>
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.priority")}
            active={sortKey === "priority"}
            direction={sortDir}
          />
        ),
        key: "priority",
        width: 110,
        onHeaderCell: () => ({ onClick: () => onSort("priority") }),
        render: (_, q) => {
          const cls =
            q.priority >= 20 ? "p20" : q.priority >= 10 ? "p10" : "p5";
          const bg =
            cls === "p20"
              ? "var(--crit-soft)"
              : cls === "p10"
                ? "var(--warn-soft)"
                : "var(--brand-soft)";
          const color =
            cls === "p20"
              ? "var(--crit)"
              : cls === "p10"
                ? "var(--warn)"
                : "var(--brand)";
          return (
            <span
              style={{
                background: bg,
                color,
                padding: "0 8px",
                height: 22,
                lineHeight: "22px",
                borderRadius: 6,
                fontSize: 11.5,
                fontWeight: 600,
                display: "inline-block",
              }}
            >
              P{q.priority}
            </span>
          );
        },
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.tickets")}
            active={sortKey === "tickets"}
            direction={sortDir}
            numeric
          />
        ),
        key: "tickets",
        width: 110,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("tickets") }),
        render: (_, q) => (
          <span
            className="mono"
            style={{ fontSize: 13, fontWeight: 600 }}
          >
            {fmtNum(q.tickets)}
          </span>
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.slaReact")}
            active={sortKey === "reaction"}
            direction={sortDir}
            numeric
          />
        ),
        key: "reaction",
        width: 130,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("reaction") }),
        render: (_, q) => <MetricBar kind="reaction" pct={q.reaction_pct} />,
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.slaResolve")}
            active={sortKey === "resolution"}
            direction={sortDir}
            numeric
          />
        ),
        key: "resolution",
        width: 130,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("resolution") }),
        render: (_, q) => (
          <MetricBar kind="resolution" pct={q.resolution_pct} />
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.breachReact")}
            active={sortKey === "rbreach"}
            direction={sortDir}
            numeric
          />
        ),
        key: "rbreach",
        width: 130,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("rbreach") }),
        render: (_, q) => (
          <span
            className="mono"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color:
                q.reaction_breach > 30
                  ? "var(--crit)"
                  : q.reaction_breach > 10
                    ? "var(--warn)"
                    : "var(--ink)",
            }}
          >
            {fmtNum(q.reaction_breach)}
          </span>
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.breachResolve")}
            active={sortKey === "sbreach"}
            direction={sortDir}
            numeric
          />
        ),
        key: "sbreach",
        width: 130,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("sbreach") }),
        render: (_, q) => (
          <span
            className="mono"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color:
                q.resolution_breach > 30
                  ? "var(--crit)"
                  : q.resolution_breach > 10
                    ? "var(--warn)"
                    : "var(--ink)",
            }}
          >
            {fmtNum(q.resolution_breach)}
          </span>
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.atRisk")}
            active={sortKey === "at_risk"}
            direction={sortDir}
            numeric
          />
        ),
        key: "at_risk",
        width: 110,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("at_risk") }),
        render: (_, q) => (
          <span
            className="mono"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color:
                q.at_risk > 30
                  ? "var(--crit)"
                  : q.at_risk > 12
                    ? "var(--warn)"
                    : "var(--ink)",
            }}
          >
            {fmtNum(q.at_risk)}
          </span>
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.avgWait")}
            active={sortKey === "wait"}
            direction={sortDir}
            numeric
          />
        ),
        key: "wait",
        width: 130,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("wait") }),
        render: (_, q) => (
          <span
            className="mono"
            style={{ fontSize: 12.5, color: "var(--ink-3)" }}
          >
            {fmtMin(q.avg_wait_min)}
          </span>
        ),
      },
      {
        title: t("slaPortal.columns.trend"),
        key: "trend",
        width: 140,
        render: (_, q) => (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <Sparkline data={q.reaction_trend} color="var(--reaction)" />
            <Sparkline data={q.resolution_trend} color="var(--resolution)" />
          </div>
        ),
      },
      {
        title: (
          <SortableHeader
            label={t("slaPortal.columns.health")}
            active={sortKey === "health"}
            direction={sortDir}
            numeric
          />
        ),
        key: "health",
        width: 100,
        align: "right",
        onHeaderCell: () => ({ onClick: () => onSort("health") }),
        render: (_, q) => <HealthPip value={q.health} />,
      },
    ],
    [sortKey, sortDir, t],
  );

  // ──────────────────────────────────────────────────────────────
  // Loading guard — single Spin only if EVERYTHING is loading first
  // time. Otherwise show partial data with skeletons in place.
  // ──────────────────────────────────────────────────────────────
  const firstLoad =
    (queuesQ.isLoading || queuesQ.isPending) &&
    (trendQ.isLoading || trendQ.isPending) &&
    !queuesQ.data;

  // ──────────────────────────────────────────────────────────────
  // RENDER
  // ──────────────────────────────────────────────────────────────
  return (
    <div
      style={{
        background: "var(--bg)",
        minHeight: "100vh",
        margin: -24,
        padding: 0,
      }}
    >
      {/* TOPBAR */}
      <div
        style={{
          background: "var(--surface)",
          borderBottom: "1px solid var(--line)",
          padding: "14px 28px 0",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            paddingBottom: 14,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                fontSize: 11.5,
                color: "var(--ink-3)",
                textTransform: "uppercase",
                letterSpacing: 0.5,
                marginBottom: 4,
                fontWeight: 500,
              }}
            >
              {t("slaPortal.crumb")}
            </div>
            <h1
              style={{
                margin: 0,
                fontSize: 20,
                fontWeight: 700,
                letterSpacing: "-0.4px",
                lineHeight: 1.2,
                color: "var(--ink)",
                display: "flex",
                alignItems: "center",
              }}
            >
              {t("slaPortal.title")}
              <span style={{ marginLeft: 10 }}>
                <LivePill label={t("slaPortal.live")} />
              </span>
            </h1>
          </div>
          <div style={{ flex: 1 }} />
          <Input
            allowClear
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("slaPortal.filters.search")}
            prefix={<SearchOutlined style={{ color: "var(--ink-4)" }} />}
            style={{ width: 280 }}
          />
          <Button icon={<DownloadOutlined />}>{t("slaPortal.export")}</Button>
          <Button type="primary" icon={<PlusOutlined />}>
            {t("slaPortal.createRule")}
          </Button>
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            padding: "4px 0 14px",
            flexWrap: "wrap",
          }}
        >
          <FilterLabel>{t("slaPortal.filters.period")}</FilterLabel>
          <Select
            size="small"
            value={period}
            onChange={setPeriod}
            style={{ width: 180 }}
            options={[
              { value: 7, label: t("slaPortal.period.last7") },
              { value: 14, label: t("slaPortal.period.last14") },
              { value: 30, label: t("slaPortal.period.last30") },
              { value: 60, label: t("slaPortal.period.last60") },
              { value: 90, label: t("slaPortal.period.last90") },
            ]}
          />
          <Separator />
          <FilterLabel>{t("slaPortal.filters.scope")}</FilterLabel>
          <ScopeChips<ScopeKey>
            value={scope}
            onChange={setScope}
            ariaLabel={t("slaPortal.filters.scope")}
            items={[
              { value: "all", label: t("slaPortal.scope.all") },
              { value: "support", label: "Support" },
              { value: "infra", label: "Infrastructure" },
              { value: "biz", label: t("slaPortal.scope.business") },
            ]}
            hideCounts
          />
          <Separator />
          <FilterLabel>{t("slaPortal.filters.calendar")}</FilterLabel>
          <Select
            size="small"
            value={calendar}
            onChange={setCalendar}
            style={{ width: 160 }}
            options={[
              { value: "all", label: t("slaPortal.calendar.all") },
              { value: "24x7", label: "24×7" },
              { value: "bh", label: t("slaPortal.calendar.bh") },
            ]}
          />
          <div style={{ flex: 1 }} />
          <Button
            size="small"
            type="text"
            icon={<ReloadOutlined />}
            onClick={() => {
              setScope("all");
              setCalendar("all");
              setSearch("");
              setPeriod(30);
            }}
          >
            {t("slaPortal.reset")}
          </Button>
        </div>
      </div>

      {/* CANVAS */}
      <div
        style={{
          padding: "20px 28px 32px",
          maxWidth: 1480,
          margin: "0 auto",
        }}
      >
        {firstLoad ? (
          <div style={{ textAlign: "center", padding: 60 }}>
            <Spin size="large" />
          </div>
        ) : (
          <div
            style={{ display: "flex", flexDirection: "column", gap: 20 }}
          >
            {/* KPI ROW */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 14,
              }}
            >
              <KpiCard
                label={t("slaPortal.kpi.reaction")}
                value={`${scopedKpi.rPct}%`}
                icon={<ClockCircleOutlined />}
                accent="react"
                foot={`${fmtNum(scopedKpi.rB)} нарушений / ${fmtNum(scopedKpi.total)} тикетов`}
              />
              <KpiCard
                label={t("slaPortal.kpi.resolution")}
                value={`${scopedKpi.sPct}%`}
                icon={<AimOutlined />}
                accent="resolve"
                foot={`${fmtNum(scopedKpi.sB)} ${t("slaPortal.kpi.breaches")}`}
              />
              <KpiCard
                label={t("slaPortal.kpi.atRisk")}
                value={fmtNum(scopedKpi.atRisk)}
                icon={<WarningOutlined />}
                accent={scopedKpi.atRisk > 50 ? "crit" : ""}
                foot={t("slaPortal.kpi.closeToBreach")}
              />
              <KpiCard
                label={t("slaPortal.kpi.avgWait")}
                value={fmtMin(scopedKpi.avgWait)}
                icon={<HourglassOutlined />}
                accent="brand"
                foot={`${scopedKpi.qCount} ${t("slaPortal.kpi.queuesInScope")}`}
              />
            </div>

            {/* MAIN CHARTS */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.65fr) minmax(0, 1fr)",
                gap: 16,
              }}
            >
              <PortalCard
                title={t("slaPortal.charts.trend")}
                subtitle={`${period} ${t("slaPortal.charts.daysReactResolve")}`}
                rightSlot={
                  <div
                    style={{
                      display: "inline-flex",
                      gap: 16,
                      fontSize: 12,
                      color: "var(--ink-3)",
                    }}
                  >
                    <span>
                      <Swatch color="var(--reaction)" />
                      {t("slaConfig.responseTime")}
                    </span>
                    <span>
                      <Swatch color="var(--resolution)" />
                      {t("slaConfig.resolutionTime")}
                    </span>
                  </div>
                }
              >
                {trendQ.isLoading ? (
                  <Spin />
                ) : (
                  <ReactECharts
                    theme={SLA_ECHARTS_THEME_NAME}
                    option={trendOption}
                    style={{ height: 280 }}
                    notMerge
                  />
                )}
              </PortalCard>
              <PortalCard
                title={t("slaPortal.charts.topQueues")}
                subtitle={t("slaPortal.charts.forPeriod")}
              >
                {filteredQueues.length === 0 ? (
                  <Empty description={t("slaPortal.empty.queues")} />
                ) : (
                  <ReactECharts
                    theme={SLA_ECHARTS_THEME_NAME}
                    option={topQueuesOption}
                    style={{ height: 280 }}
                    notMerge
                    onEvents={{
                      click: (params: { dataIndex?: number }) => {
                        if (params.dataIndex == null) return;
                        const q = topByBreaches[params.dataIndex];
                        if (q)
                          setDrawer({
                            open: true,
                            kind: "queue",
                            payload: q,
                          });
                      },
                    }}
                  />
                )}
              </PortalCard>
            </div>

            {/* TABS */}
            <div
              style={{
                background: "var(--surface)",
                borderRadius: "var(--radius-lg)",
                boxShadow: "var(--shadow-card)",
                overflow: "hidden",
              }}
            >
              <Tabs
                activeKey={tab}
                onChange={(k) =>
                  setTab(k as "queues" | "tickets" | "heat" | "team")
                }
                style={{ padding: "0 16px" }}
                items={[
                  {
                    key: "queues",
                    label: (
                      <span>
                        <ApartmentOutlined />{" "}
                        {t("slaPortal.tabs.queues")}{" "}
                        <Tag style={{ marginInlineStart: 4 }}>
                          {sortedQueues.length}
                        </Tag>
                      </span>
                    ),
                    children: (
                      <Table<PortalQueue>
                        rowKey="id"
                        dataSource={sortedQueues}
                        columns={queueColumns}
                        pagination={{ pageSize: 25, showSizeChanger: false }}
                        size="middle"
                        sticky
                        onRow={(record) => ({
                          onClick: () =>
                            setDrawer({
                              open: true,
                              kind: "queue",
                              payload: record,
                            }),
                          style: { cursor: "pointer" },
                        })}
                        loading={queuesQ.isLoading || queuesQ.isPending}
                      />
                    ),
                  },
                  {
                    key: "tickets",
                    label: (
                      <span>
                        <WarningOutlined />{" "}
                        {t("slaPortal.tabs.tickets")}{" "}
                        <Tag style={{ marginInlineStart: 4 }}>
                          {filteredRisks.length}
                        </Tag>
                      </span>
                    ),
                    children: (
                      <Table<PortalRisk>
                        rowKey="id"
                        dataSource={filteredRisks}
                        pagination={{ pageSize: 25, showSizeChanger: false }}
                        size="middle"
                        loading={risksQ.isLoading || risksQ.isPending}
                        onRow={(record) => ({
                          onClick: () =>
                            setDrawer({
                              open: true,
                              kind: "ticket",
                              payload: record,
                            }),
                          style: { cursor: "pointer" },
                        })}
                        columns={[
                          {
                            title: "№",
                            dataIndex: "ticket_number",
                            width: 110,
                            render: (v) => (
                              <span
                                className="mono"
                                style={{
                                  color: "var(--brand)",
                                  fontWeight: 600,
                                }}
                              >
                                {v}
                              </span>
                            ),
                          },
                          {
                            title: t("slaPortal.columns.title"),
                            dataIndex: "title",
                            ellipsis: true,
                          },
                          {
                            title: t("slaPortal.columns.queueOwner"),
                            key: "qo",
                            render: (_, r) => (
                              <div>
                                <div
                                  className="mono"
                                  style={{
                                    fontSize: 12.5,
                                    color: "var(--ink-2)",
                                  }}
                                >
                                  {r.queue}
                                </div>
                                <div
                                  className="mono"
                                  style={{
                                    fontSize: 11.5,
                                    color: "var(--ink-3)",
                                    marginTop: 2,
                                  }}
                                >
                                  {r.owner}
                                </div>
                              </div>
                            ),
                          },
                          {
                            title: t("slaConfig.responseTime"),
                            key: "r_used",
                            width: 130,
                            align: "right",
                            render: (_, r) => (
                              <MetricBar
                                kind="reaction"
                                pct={r.r_used}
                                severity={r.r_over ? "crit" : undefined}
                              />
                            ),
                          },
                          {
                            title: t("slaConfig.resolutionTime"),
                            key: "s_used",
                            width: 130,
                            align: "right",
                            render: (_, r) => (
                              <MetricBar
                                kind="resolution"
                                pct={r.s_used}
                                severity={r.s_over ? "crit" : undefined}
                              />
                            ),
                          },
                          {
                            title: t("slaPortal.columns.eta"),
                            key: "eta",
                            width: 140,
                            align: "right",
                            render: (_, r) => {
                              const cls =
                                r.breach_eta_min < 0
                                  ? "crit"
                                  : r.breach_eta_min < 30
                                    ? "warn"
                                    : "ok";
                              const color =
                                cls === "crit"
                                  ? "var(--crit)"
                                  : cls === "warn"
                                    ? "var(--warn)"
                                    : "var(--ok)";
                              return (
                                <span
                                  className="mono"
                                  style={{ fontWeight: 600, color }}
                                >
                                  {r.breach_eta_min < 0
                                    ? `+${fmtMin(Math.abs(r.breach_eta_min))}`
                                    : fmtMin(r.breach_eta_min)}
                                </span>
                              );
                            },
                          },
                        ]}
                      />
                    ),
                  },
                  {
                    key: "heat",
                    label: (
                      <span>
                        <HeatMapOutlined />{" "}
                        {t("slaPortal.tabs.heat")}
                      </span>
                    ),
                    children: (
                      <div style={{ padding: 20 }}>
                        {filteredHeatmap.length === 0 ? (
                          <Empty description={t("slaPortal.empty.heat")} />
                        ) : (
                          <ReactECharts
                            theme={SLA_ECHARTS_THEME_NAME}
                            option={heatmapOption}
                            style={{ height: Math.max(380, filteredHeatmap.length * 24) }}
                            notMerge
                          />
                        )}
                      </div>
                    ),
                  },
                  {
                    key: "team",
                    label: (
                      <span>
                        <TeamOutlined /> {t("slaPortal.tabs.team")}{" "}
                        <Tag style={{ marginInlineStart: 4 }}>
                          {agentsQ.data?.length ?? 0}
                        </Tag>
                      </span>
                    ),
                    children: (
                      <Table<PortalAgent>
                        rowKey="name"
                        dataSource={agentsQ.data || []}
                        loading={agentsQ.isLoading || agentsQ.isPending}
                        pagination={{ pageSize: 25, showSizeChanger: false }}
                        size="middle"
                        columns={[
                          {
                            title: t("slaPortal.columns.agent"),
                            key: "agent",
                            render: (_, a) => (
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 10,
                                }}
                              >
                                <div
                                  style={{
                                    width: 30,
                                    height: 30,
                                    borderRadius: "50%",
                                    background:
                                      "linear-gradient(135deg, var(--brand), #6366f1)",
                                    color: "#fff",
                                    fontSize: 11,
                                    fontWeight: 700,
                                    display: "grid",
                                    placeItems: "center",
                                  }}
                                >
                                  {a.initials}
                                </div>
                                <div>
                                  <div
                                    className="mono"
                                    style={{
                                      fontSize: 13,
                                      fontWeight: 600,
                                    }}
                                  >
                                    {a.name}
                                  </div>
                                  <div
                                    style={{
                                      fontSize: 11.5,
                                      color: "var(--ink-3)",
                                      marginTop: 2,
                                    }}
                                  >
                                    {a.status === "over"
                                      ? t("slaPortal.status.over")
                                      : a.status === "top"
                                        ? t("slaPortal.status.top")
                                        : t("slaPortal.status.norm")}
                                  </div>
                                </div>
                              </div>
                            ),
                          },
                          {
                            title: t("slaPortal.columns.open"),
                            dataIndex: "open",
                            align: "right",
                            width: 100,
                            render: (v: number) => (
                              <span
                                className="mono"
                                style={{
                                  fontWeight: 700,
                                  color:
                                    v > 20
                                      ? "var(--crit)"
                                      : v > 15
                                        ? "var(--warn)"
                                        : "var(--ink)",
                                }}
                              >
                                {v}
                              </span>
                            ),
                          },
                          {
                            title: t("slaPortal.columns.handled"),
                            dataIndex: "handled",
                            align: "right",
                            width: 110,
                            render: (v: number) => (
                              <span
                                className="mono"
                                style={{ color: "var(--ink-2)" }}
                              >
                                {fmtNum(v)}
                              </span>
                            ),
                          },
                          {
                            title: t("slaPortal.columns.slaPct"),
                            dataIndex: "sla_pct",
                            align: "right",
                            width: 100,
                            render: (v: number) => (
                              <HealthPip value={v} size={32} />
                            ),
                          },
                          {
                            title: t("slaPortal.columns.avgTime"),
                            dataIndex: "avg_min",
                            align: "right",
                            width: 110,
                            render: (v: number) => (
                              <span
                                className="mono"
                                style={{
                                  fontSize: 12.5,
                                  color: "var(--ink-3)",
                                }}
                              >
                                {fmtMin(v)}
                              </span>
                            ),
                          },
                        ]}
                      />
                    ),
                  },
                ]}
              />
            </div>

            <div
              style={{
                fontSize: 12,
                color: "var(--ink-4)",
                textAlign: "center",
                padding: 12,
              }}
            >
              SLA Portal · {period} {t("slaPortal.days")} · {t("slaPortal.scopeLabel")}: {scope === "all" ? t("slaPortal.scope.all") : scope}
            </div>
          </div>
        )}
      </div>

      {/* DRAWER */}
      {drawer.kind === "queue" && drawer.payload && (
        <QueueDrawerContent
          q={drawer.payload as PortalQueue}
          open={drawer.open}
          onClose={() => setDrawer((d) => ({ ...d, open: false }))}
        />
      )}
      {drawer.kind === "ticket" && drawer.payload && (
        <TicketDrawerContent
          tk={drawer.payload as PortalRisk}
          open={drawer.open}
          onClose={() => setDrawer((d) => ({ ...d, open: false }))}
        />
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Helpers — local micro-components.
// ──────────────────────────────────────────────────────────────────
function FilterLabel({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontSize: 11,
        color: "var(--ink-3)",
        textTransform: "uppercase",
        letterSpacing: 0.4,
        fontWeight: 500,
        marginRight: 4,
      }}
    >
      {children}
    </span>
  );
}

function Separator() {
  return (
    <div
      style={{
        width: 1,
        height: 18,
        background: "var(--line)",
        margin: "0 6px",
      }}
    />
  );
}

function PortalCard({
  title,
  subtitle,
  rightSlot,
  children,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  rightSlot?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        background: "var(--surface)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-card)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "16px 20px",
          borderBottom: "1px solid var(--line)",
          gap: 12,
          minHeight: 56,
        }}
      >
        <div>
          <div
            style={{
              fontWeight: 600,
              fontSize: 14.5,
              letterSpacing: "-0.2px",
              color: "var(--ink)",
            }}
          >
            {title}
          </div>
          {subtitle && (
            <div
              style={{ color: "var(--ink-3)", fontSize: 12.5, marginTop: 2 }}
            >
              {subtitle}
            </div>
          )}
        </div>
        {rightSlot && (
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            {rightSlot}
          </div>
        )}
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </div>
  );
}

function Swatch({ color }: { color: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 14,
        height: 3,
        borderRadius: 2,
        background: color,
        verticalAlign: "middle",
        marginRight: 6,
      }}
    />
  );
}

// ──────────────────────────────────────────────────────────────────
// ECharts option builders.
// ──────────────────────────────────────────────────────────────────
type TFunc = (key: string) => string;

function buildTrendOption(daily: DailyTrendPoint[], t: TFunc) {
  const dates = daily.map((d) => {
    const dt = new Date(d.date);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${pad(dt.getDate())}.${pad(dt.getMonth() + 1)}`;
  });
  return {
    grid: { top: 16, right: 16, bottom: 28, left: 44 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
    },
    legend: {
      bottom: 0,
      data: [t("slaConfig.responseTime"), t("slaConfig.resolutionTime")],
    },
    xAxis: { type: "category", boundaryGap: false, data: dates },
    yAxis: { type: "value" },
    series: [
      {
        name: t("slaConfig.responseTime"),
        type: "line",
        stack: "breaches",
        symbol: "none",
        areaStyle: { opacity: 0.32 },
        color: "#f59e0b",
        lineStyle: { color: "#f59e0b", width: 2 },
        itemStyle: { color: "#f59e0b" },
        data: daily.map((d) => d.reaction),
      },
      {
        name: t("slaConfig.resolutionTime"),
        type: "line",
        stack: "breaches",
        symbol: "none",
        areaStyle: { opacity: 0.22 },
        color: "#8b5cf6",
        lineStyle: { color: "#8b5cf6", width: 2 },
        itemStyle: { color: "#8b5cf6" },
        data: daily.map((d) => d.resolution),
      },
    ],
  };
}

function buildTopQueuesOption(rows: PortalQueue[], t: TFunc) {
  const ordered = [...rows].reverse(); // ECharts plots first row at bottom
  return {
    grid: { top: 8, right: 16, bottom: 24, left: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: {
      bottom: 0,
      data: [t("slaConfig.responseTime"), t("slaConfig.resolutionTime")],
    },
    xAxis: { type: "value" },
    yAxis: {
      type: "category",
      data: ordered.map((q) => q.name),
      axisLabel: { width: 160, overflow: "truncate" },
    },
    series: [
      {
        name: t("slaConfig.responseTime"),
        type: "bar",
        stack: "breaches",
        color: "#f59e0b",
        itemStyle: { color: "#f59e0b" },
        data: ordered.map((q) => q.reaction_breach),
      },
      {
        name: t("slaConfig.resolutionTime"),
        type: "bar",
        stack: "breaches",
        color: "#8b5cf6",
        itemStyle: { color: "#8b5cf6" },
        data: ordered.map((q) => q.resolution_breach),
      },
    ],
  };
}

function buildHeatmapOption(rows: HeatmapRow[], _t: TFunc) {
  const queues = rows.map((r) => r.queue);
  const hours = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, "0"));
  const data: [number, number, number][] = [];
  rows.forEach((r, y) => {
    r.hours.forEach((v, x) => data.push([x, y, v]));
  });
  const max = Math.max(1, ...data.map((d) => d[2]));
  return {
    grid: { left: 180, right: 24, top: 16, bottom: 40, containLabel: false },
    tooltip: {
      position: "top",
      formatter: (p: { value: [number, number, number] }) => {
        const [x, y, v] = p.value;
        return `${queues[y]} · ${hours[x]}:00<br/><b>${v}</b>`;
      },
    },
    xAxis: { type: "category", data: hours, splitArea: { show: true } },
    yAxis: { type: "category", data: queues, splitArea: { show: true } },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: {
        color: ["#fff7ed", "#fed7aa", "#fb923c", "#ea580c"],
      },
    },
    series: [
      {
        name: "breaches",
        type: "heatmap",
        data,
        label: { show: false },
      },
    ],
  };
}

// ──────────────────────────────────────────────────────────────────
// Drawers
// ──────────────────────────────────────────────────────────────────
function QueueDrawerContent({
  q,
  open,
  onClose,
}: {
  q: PortalQueue;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const sev = severityFor(q.health);
  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      kind="queue"
      crumb={`${t("slaPortal.drawer.queue")} · ${q.calendar}`}
      title={q.name}
      meta={
        <>
          <Tag color={q.priority >= 20 ? "red" : q.priority >= 10 ? "orange" : "blue"}>
            P{q.priority}
          </Tag>
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
            {fmtMin(q.avg_wait_min)} {t("slaPortal.drawer.avgWait")}
          </span>
        </>
      }
    >
      <div className="sla-metric-row">
        <div className={`sla-metric-tile ${sev === "ok" ? "ok" : sev === "warn" ? "warn" : "crit"}`}>
          <div className="lab">Health</div>
          <div className="val">{q.health}</div>
          <div className="sub">{t("slaPortal.drawer.outOf100")}</div>
        </div>
        <div className="sla-metric-tile">
          <div className="lab">{t("slaPortal.columns.tickets")}</div>
          <div className="val">{fmtNum(q.tickets)}</div>
          <div className="sub">{t("slaPortal.drawer.forPeriod")}</div>
        </div>
        <div
          className={`sla-metric-tile ${q.at_risk > 30 ? "crit" : q.at_risk > 12 ? "warn" : ""}`}
        >
          <div className="lab">{t("slaPortal.columns.atRisk")}</div>
          <div className="val">{q.at_risk}</div>
          <div className="sub">{t("slaPortal.kpi.closeToBreach")}</div>
        </div>
      </div>

      <PortalCard title={t("slaPortal.drawer.slaCompliance")}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div
              style={{
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: 0.4,
                color: "var(--reaction)",
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              {t("slaConfig.responseTime")}
            </div>
            <MetricBar kind="reaction" pct={q.reaction_pct} />
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 8 }}>
              {q.reaction_breach} {t("slaPortal.kpi.breaches")}
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: 0.4,
                color: "var(--resolution)",
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              {t("slaConfig.resolutionTime")}
            </div>
            <MetricBar kind="resolution" pct={q.resolution_pct} />
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 8 }}>
              {q.resolution_breach} {t("slaPortal.kpi.breaches")}
            </div>
          </div>
        </div>
      </PortalCard>

      <div style={{ display: "flex", gap: 8 }}>
        <Button type="primary">{t("slaPortal.drawer.openTickets")}</Button>
        <Button>{t("slaPortal.drawer.editRule")}</Button>
        <Button icon={<DownloadOutlined />}>{t("slaPortal.export")}</Button>
      </div>
    </DetailDrawer>
  );
}

function TicketDrawerContent({
  tk,
  open,
  onClose,
}: {
  tk: PortalRisk;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      kind="ticket"
      crumb={t("slaPortal.drawer.ticket")}
      title={tk.title}
      meta={
        <>
          <span
            className="mono"
            style={{ fontSize: 12, color: "var(--brand)", fontWeight: 600 }}
          >
            {tk.ticket_number}
          </span>
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
            {tk.queue} · {tk.owner}
          </span>
        </>
      }
    >
      <div className="sla-metric-row">
        <div
          className={`sla-metric-tile ${tk.r_over ? "crit" : tk.r_used > 80 ? "warn" : ""}`}
        >
          <div className="lab">{t("slaConfig.responseTime")}</div>
          <div className="val">{tk.r_used}%</div>
          <div className="sub">
            {tk.r_over
              ? `${t("slaPortal.drawer.overdue")} ${fmtMin(Math.abs(tk.breach_eta_min))}`
              : `${t("slaPortal.drawer.remaining")} ${fmtMin(tk.breach_eta_min)}`}
          </div>
        </div>
        <div
          className={`sla-metric-tile ${tk.s_over ? "crit" : tk.s_used > 80 ? "warn" : ""}`}
        >
          <div className="lab">{t("slaConfig.resolutionTime")}</div>
          <div className="val">{tk.s_used}%</div>
          <div className="sub">
            {tk.s_over
              ? `${t("slaPortal.drawer.overdue")} ${fmtMin(Math.abs(tk.breach_eta_min))}`
              : `${t("slaPortal.drawer.remaining")} ${fmtMin(tk.breach_eta_min)}`}
          </div>
        </div>
        <div className="sla-metric-tile">
          <div className="lab">{t("slaPortal.columns.eta")}</div>
          <div className="val" style={{ fontSize: 18 }}>
            {tk.breach_eta_min < 0
              ? `+${fmtMin(Math.abs(tk.breach_eta_min))}`
              : fmtMin(tk.breach_eta_min)}
          </div>
        </div>
      </div>

      <PortalCard title={`SLA · ${t("slaConfig.responseTime")}`}>
        <MetricBar
          kind="reaction"
          pct={tk.r_used}
          severity={tk.r_over ? "crit" : undefined}
        />
      </PortalCard>
      <PortalCard title={`SLA · ${t("slaConfig.resolutionTime")}`}>
        <MetricBar
          kind="resolution"
          pct={tk.s_used}
          severity={tk.s_over ? "crit" : undefined}
        />
      </PortalCard>

      <div style={{ display: "flex", gap: 8 }}>
        <Button type="primary">{t("slaPortal.drawer.openInOtrs")}</Button>
        <Button>{t("slaPortal.drawer.reassign")}</Button>
        <Button>{t("slaPortal.drawer.escalate")}</Button>
      </div>
    </DetailDrawer>
  );
}

// ──────────────────────────────────────────────────────────────────
// Exported component wrapped in an error boundary so one broken
// widget never blanks the entire portal.
// ──────────────────────────────────────────────────────────────────
export default function SLAPortal() {
  return (
    <RuntimeErrorBoundary label="SLA Portal">
      <SLAPortalInner />
    </RuntimeErrorBoundary>
  );
}
