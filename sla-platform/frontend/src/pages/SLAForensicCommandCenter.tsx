import { useMemo } from "react";
import {
  Row, Col, Card, Typography, Table, Tag, Tabs, Statistic, Spin, Empty, Tooltip, Progress,
} from "antd";
import {
  AlertOutlined, ApartmentOutlined, ClockCircleOutlined, EyeInvisibleOutlined,
  FireOutlined, NodeIndexOutlined, RadarChartOutlined, WarningOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import ReactEChartsCore from "echarts-for-react";
import { forensicsApi, formatDuration } from "../api/forensics";
import { useFavorites } from "../contexts/FavoritesContext";
import { useTheme } from "../design/ThemeContext";
import { cardStyle } from "../design/tokens";
import { spacing } from "../design/spacing";

const { Title, Text } = Typography;

export default function SLAForensicCommandCenter() {
  const { colors } = useTheme();
  const { activeFilter } = useFavorites();
  const summaryQ = useQuery({
    queryKey: ["forensic-summary", activeFilter.join(",")],
    queryFn: () => forensicsApi.summary(activeFilter.length ? activeFilter : undefined),
    refetchInterval: 60_000,
  });

  if (summaryQ.isLoading) {
    return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  }
  if (summaryQ.isError || !summaryQ.data) {
    return <Empty description="Нет данных по форензике SLA" style={{ marginTop: 80 }} />;
  }
  const s = summaryQ.data;
  const k = s.kpis;
  const total = (k.pause_total || 0) + (k.idle_total || 0) + (k.no_owner_total || 0);

  // Pie of "where time was lost"
  const lossPie = useMemo(() => ({
    backgroundColor: "transparent",
    tooltip: { trigger: "item" as const, formatter: (p: any) => `${p.name}: ${formatDuration(p.value)} (${p.percent}%)` },
    legend: { bottom: 0, textStyle: { color: colors.text.secondary, fontSize: 11 } },
    series: [{
      type: "pie" as const,
      radius: ["45%", "70%"],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: colors.surface, borderWidth: 2 },
      label: { color: colors.text.primary, fontSize: 11 },
      data: [
        { name: "Pause", value: k.pause_total, itemStyle: { color: "#b65709" } },
        { name: "Idle", value: k.idle_total, itemStyle: { color: "#b98a1f" } },
        { name: "No owner", value: k.no_owner_total, itemStyle: { color: "#b42333" } },
        { name: "Transfer wait", value: k.xfer_total, itemStyle: { color: "#1a7f3b" } },
        { name: "Stagnation", value: k.stag_total, itemStyle: { color: "#5a3eb0" } },
      ].filter(d => d.value > 0),
    }],
  }), [k, colors]);

  // Sankey of transitions (top routing chaos)
  const sankey = useMemo(() => {
    const txs = (s.transitions || []).slice(0, 30);
    const nodeSet = new Set<string>();
    txs.forEach(t => { nodeSet.add(t.src); nodeSet.add(t.dst); });
    const nodes = Array.from(nodeSet).map(n => ({ name: n }));
    const links = txs.map(t => ({ source: t.src, target: t.dst, value: t.count }));
    return {
      backgroundColor: "transparent",
      tooltip: { trigger: "item" as const },
      series: [{
        type: "sankey" as const,
        emphasis: { focus: "adjacency" as const },
        nodeAlign: "left" as const,
        data: nodes,
        links,
        lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.4 },
        label: { color: colors.text.primary, fontSize: 10 },
      }],
    };
  }, [s.transitions, colors]);

  // Black-hole heatmap (bar chart)
  const bhBar = useMemo(() => {
    const data = (s.queues_top_blackholes || []).slice(0, 12).reverse();
    return {
      backgroundColor: "transparent",
      grid: { left: 200, right: 60, top: 10, bottom: 30 },
      tooltip: { trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
      xAxis: {
        type: "value" as const, max: 1,
        axisLabel: { fontSize: 10, color: colors.text.tertiary, formatter: (v: number) => `${(v * 100).toFixed(0)}%` },
        splitLine: { lineStyle: { color: colors.divider, type: "dashed" as const } },
      },
      yAxis: {
        type: "category" as const,
        data: data.map(q => q.queue),
        axisLabel: { fontSize: 10, color: colors.text.secondary, width: 190, overflow: "truncate" },
      },
      series: [
        {
          name: "Black-hole", type: "bar" as const,
          data: data.map(q => q.black_hole_score),
          itemStyle: { color: "#b42333", borderRadius: [0, 4, 4, 0] as any },
        },
      ],
    };
  }, [s.queues_top_blackholes, colors]);

  return (
    <div style={{ padding: spacing[6], maxWidth: 1500, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: spacing[2] }}>
        <RadarChartOutlined /> Командный центр форензики SLA
      </Title>
      <Text type="secondary">
        Где именно теряется SLA, какие очереди превращаются в чёрные дыры,
        какие тикеты тихо нарушают сроки без событий, и кто отвечает за потери.
      </Text>

      {/* ── KPI strip ────────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginTop: spacing[4] }}>
        <Col xs={24} md={6}>
          <Card style={cardStyle} bordered={false}>
            <Statistic
              title="Wall-clock SLA нарушено"
              value={k.wall_breached || 0}
              prefix={<WarningOutlined style={{ color: "#b42333" }} />}
              valueStyle={{ color: "#b42333" }}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              против active-time: {k.active_breached || 0}
            </Text>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card style={cardStyle} bordered={false}>
            <Statistic
              title="Без owner'а (часов)"
              value={Math.round((k.no_owner_total || 0) / 3600)}
              prefix={<EyeInvisibleOutlined style={{ color: "#b98a1f" }} />}
              valueStyle={{ color: "#b98a1f" }}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {total > 0 ? `${Math.round((k.no_owner_total / total) * 100)}% lifecycle` : "—"}
            </Text>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card style={cardStyle} bordered={false}>
            <Statistic
              title="Тихих нарушений"
              value={s.silent_breaches?.length || 0}
              prefix={<ClockCircleOutlined style={{ color: "#b65709" }} />}
              valueStyle={{ color: "#b65709" }}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              открытые тикеты без событий ≥50% SLA
            </Text>
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card style={cardStyle} bordered={false}>
            <Statistic
              title="Hot-potato тикетов"
              value={s.hot_potato?.length || 0}
              prefix={<FireOutlined style={{ color: "#5a3eb0" }} />}
              valueStyle={{ color: "#5a3eb0" }}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              ≥3 перемещения / смены владельца
            </Text>
          </Card>
        </Col>
      </Row>

      {/* ── Top blame queues + loss pie ──────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginTop: spacing[4] }}>
        <Col xs={24} lg={14}>
          <Card style={cardStyle} bordered={false}
                title={<><AlertOutlined /> Топ очередей чёрных дыр (black-hole score)</>}>
            <ReactEChartsCore option={bhBar} style={{ height: 360 }} />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card style={cardStyle} bordered={false}
                title={<><FireOutlined /> Где теряется время</>}>
            <ReactEChartsCore option={lossPie} style={{ height: 360 }} />
          </Card>
        </Col>
      </Row>

      {/* ── Routing chaos sankey ─────────────────────────────────── */}
      <Card style={{ ...cardStyle, marginTop: spacing[4] }} bordered={false}
            title={<><NodeIndexOutlined /> Карта маршрутов (transition graph)</>}>
        <ReactEChartsCore option={sankey} style={{ height: 460 }} />
      </Card>

      {/* ── Detail tables ─────────────────────────────────────────── */}
      <Card style={{ ...cardStyle, marginTop: spacing[4] }} bordered={false}>
        <Tabs
          items={[
            {
              key: "blackholes", label: "Чёрные дыры",
              children: <QueueTable rows={s.queues_top_blackholes} highlight="black_hole_score" />,
            },
            {
              key: "chaos", label: "Routing chaos",
              children: <QueueTable rows={s.queues_top_chaos} highlight="routing_chaos_score" />,
            },
            {
              key: "breach", label: "По breach-rate",
              children: <QueueTable rows={s.queues_top_breach} highlight="breach_rate" />,
            },
            {
              key: "silent", label: `Тихие нарушения (${s.silent_breaches?.length || 0})`,
              children: <SilentTable rows={s.silent_breaches} />,
            },
            {
              key: "potato", label: `Hot-potato (${s.hot_potato?.length || 0})`,
              children: <HotPotatoTable rows={s.hot_potato} />,
            },
            {
              key: "owners", label: "Owner forensics",
              children: <OwnerTable rows={s.owners_top_load} idle={s.owners_idle} />,
            },
            {
              key: "silence", label: "Тишина по очередям",
              children: <QueueSilenceTable rows={s.queue_silence} />,
            },
          ]}
        />
      </Card>
    </div>
  );
}

// ── Sub-tables ──────────────────────────────────────────────────────

function pct(v: number): string { return `${(v * 100).toFixed(1)}%`; }

function QueueTable({ rows, highlight }: { rows: any[]; highlight: string }) {
  if (!rows?.length) return <Empty />;
  return (
    <Table
      size="small" rowKey="queue" dataSource={rows} pagination={false}
      columns={[
        { title: "Очередь", dataIndex: "queue", width: 280 },
        { title: "Тикетов", dataIndex: "total_tickets", width: 90, align: "right" },
        {
          title: "Часов держала",
          dataIndex: "total_wall_hours", width: 130, align: "right",
          render: (v: number) => v.toFixed(1),
        },
        {
          title: "Среднее (ч)", dataIndex: "mean_stay_hours", width: 110, align: "right",
          render: (v: number) => v.toFixed(1),
        },
        {
          title: "No-owner %",
          dataIndex: "no_owner_ratio", width: 110, align: "right",
          render: (v: number) => (
            <Tag color={v >= 0.95 ? "red" : v >= 0.7 ? "orange" : "default"}>{pct(v)}</Tag>
          ),
        },
        {
          title: "Энтропия", dataIndex: "entropy_bits", width: 100, align: "right",
          render: (v: number) => v.toFixed(2),
        },
        {
          title: "Breach %", dataIndex: "breach_rate", width: 100, align: "right",
          render: (v: number) => (
            <Tag color={v >= 0.3 ? "red" : v >= 0.1 ? "orange" : "default"}>{pct(v)}</Tag>
          ),
        },
        {
          title: "Black-hole", dataIndex: "black_hole_score", width: 130, align: "right",
          render: (v: number) => (
            <Tooltip title={`Score: ${v.toFixed(3)}`}>
              <Progress percent={Math.min(100, v * 100)} size="small" showInfo={false}
                strokeColor={v >= 0.5 ? "#b42333" : v >= 0.3 ? "#b65709" : "#1a7f3b"}/>
            </Tooltip>
          ),
        },
        {
          title: "Routing chaos", dataIndex: "routing_chaos_score", width: 130, align: "right",
          render: (v: number) => v.toFixed(2),
        },
        {
          title: "Stagnation", dataIndex: "stagnation_score", width: 110, align: "right",
          render: (v: number) => v.toFixed(2),
        },
      ]}
    />
  );
}

function SilentTable({ rows }: { rows: any[] }) {
  if (!rows?.length) return <Empty description="Тихих нарушений не найдено" />;
  return (
    <Table
      size="small" rowKey="ticket_id" dataSource={rows} pagination={{ pageSize: 20 }}
      columns={[
        { title: "№", dataIndex: "ticket_number", width: 140 },
        { title: "Очередь", dataIndex: "queue_name", width: 230 },
        { title: "Состояние", dataIndex: "state_name", width: 140 },
        { title: "Owner", dataIndex: "owner", width: 180,
          render: (v) => v || <Tag color="red">нет</Tag> },
        {
          title: "Без событий", dataIndex: "last_activity_age_seconds",
          render: (v: number) => formatDuration(v), width: 130,
        },
        {
          title: "Целевой SLA", dataIndex: "sla_target_seconds",
          render: (v: number) => formatDuration(v), width: 130,
        },
        {
          title: "Inactivity",
          dataIndex: "inactivity_ratio",
          width: 120, align: "right",
          render: (v: number) => (
            <Tag color={v >= 1 ? "red" : v >= 0.8 ? "orange" : "blue"}>{pct(v)}</Tag>
          ),
        },
        {
          title: "Риск", dataIndex: "risk_level", width: 110,
          render: (v) => (
            <Tag color={v === "breached" ? "red" : v === "critical" ? "magenta" : v === "high" ? "orange" : "blue"}>
              {v}
            </Tag>
          ),
        },
      ]}
    />
  );
}

function HotPotatoTable({ rows }: { rows: any[] }) {
  if (!rows?.length) return <Empty />;
  return (
    <Table
      size="small" rowKey="ticket_id" dataSource={rows} pagination={{ pageSize: 20 }}
      columns={[
        { title: "№", dataIndex: "ticket_number", width: 160 },
        { title: "Текущая очередь", dataIndex: "current_queue", width: 240 },
        { title: "Состояние", dataIndex: "current_state", width: 140 },
        { title: "Перемещений", dataIndex: "moves", width: 130, align: "right",
          render: (v: number) => <Tag color={v >= 10 ? "red" : v >= 5 ? "orange" : "default"}>{v}</Tag> },
        { title: "Смены владельца", dataIndex: "owner_changes", width: 140, align: "right",
          render: (v: number) => <Tag color={v >= 5 ? "red" : v >= 3 ? "orange" : "default"}>{v}</Tag> },
        { title: "Очередей затронуто", dataIndex: "distinct_queues", width: 150, align: "right" },
      ]}
    />
  );
}

function OwnerTable({ rows, idle }: { rows: any[]; idle: any[] }) {
  const all = [...(rows || []), ...(idle || []).filter(o => !rows?.some(r => r.owner === o.owner))];
  if (!all.length) return <Empty />;
  return (
    <Table
      size="small" rowKey="owner" dataSource={all} pagination={{ pageSize: 20 }}
      columns={[
        { title: "Owner", dataIndex: "owner", width: 240 },
        { title: "Тикеты", dataIndex: "load_tickets", width: 90, align: "right" },
        { title: "Часов", dataIndex: "load_hours", width: 100, align: "right",
          render: (v: number) => v?.toFixed(1) },
        { title: "Brak (события)", dataIndex: "non_sys_events", width: 130, align: "right" },
        { title: "Touch/час", dataIndex: "touch_frequency", width: 110, align: "right",
          render: (v: number) => v?.toFixed(2) },
        { title: "Reassign pressure", dataIndex: "reassignment_pressure", width: 140, align: "right",
          render: (v: number) => v?.toFixed(2) },
        { title: "Parked", dataIndex: "parked_tickets", width: 90, align: "right",
          render: (v: number) => <Tag color={v > 0 ? "orange" : "default"}>{v || 0}</Tag> },
        { title: "Overload", dataIndex: "overload_score", width: 110, align: "right",
          render: (v: number) => (
            <Tag color={v >= 1.5 ? "red" : v >= 1 ? "orange" : "default"}>{v?.toFixed(2)}</Tag>
          ) },
        { title: "Idle", dataIndex: "idle_flag", width: 70,
          render: (v: boolean) => v ? <Tag color="red">да</Tag> : "—" },
      ]}
    />
  );
}

function QueueSilenceTable({ rows }: { rows: any[] }) {
  if (!rows?.length) return <Empty />;
  return (
    <Table
      size="small" rowKey="queue" dataSource={rows} pagination={false}
      columns={[
        { title: "Очередь", dataIndex: "queue", width: 280 },
        { title: "Открытых", dataIndex: "open_tickets", width: 110, align: "right" },
        { title: "Медиана тишины", dataIndex: "median_age_seconds", width: 160,
          render: (v: number) => formatDuration(v) },
        { title: "P90 тишины", dataIndex: "p90_age_seconds", width: 140,
          render: (v: number) => formatDuration(v) },
        { title: "Silence score", dataIndex: "silence_score", width: 140, align: "right",
          render: (v: number) => (
            <Progress percent={v * 100} size="small" showInfo={false}
              strokeColor={v >= 0.8 ? "#b42333" : v >= 0.5 ? "#b98a1f" : "#1a7f3b"} />
          ) },
      ]}
    />
  );
}
