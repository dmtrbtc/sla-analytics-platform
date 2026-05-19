import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, Typography, Tag, Badge, Row, Col, Space, Table, Tooltip, Progress, Divider } from "antd";
import {
  QuestionCircleOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  UserOutlined,
  ApartmentOutlined,
  PauseCircleOutlined,
  FieldTimeOutlined,
  AlertOutlined,
  RightCircleOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import client from "../../api/client";
import { formatHumanDuration } from "../../utils/format";
import { palette } from "../../design/colors";
import { typography } from "../../design/typography";
import { spacing } from "../../design/spacing";
import { radius } from "../../design/spacing";
import { shadows } from "../../design/shadows";

interface Interval {
  start: string;
  end: string;
  type: string;
  label: string;
  duration_seconds?: number;
  metadata?: Record<string, unknown>;
}

interface Metric {
  name: string;
  seconds: number;
  breached: boolean;
  risk_level?: string;
  risk_score?: number;
  risk_reason?: string;
  business_hours_excluded?: number;
  paused_time?: number;
  counted_time?: number;
  target_seconds?: number;
  delta?: number;
}

interface TimelineData {
  ticket_id: number;
  intervals: Interval[];
  queue_intervals: Interval[];
  owner_intervals: Interval[];
  pending_intervals: Interval[];
  working_intervals: Interval[];
  metrics: Metric[];
  sla_policy?: {
    name: string;
    match_reason: string;
    response_target_seconds: number;
    resolution_target_seconds: number;
    calendar: string;
    escalation_rules?: string[];
  };
  total_intervals?: number;
}

interface BreachPrediction {
  eta_seconds: number;
  probability: number;
  risk_level: string;
}

const iconMap: Record<string, React.ReactNode> = {
  queue: <ApartmentOutlined />,
  owner: <UserOutlined />,
  pending: <PauseCircleOutlined />,
  working: <FieldTimeOutlined />,
};

const typeColorMap: Record<string, string> = {
  queue: palette.brand[500],
  owner: palette.accent.indigo,
  pending: palette.text.disabled,
  working: palette.accent.teal,
};

const queueColors = [
  palette.brand[500],
  palette.accent.teal,
  palette.accent.indigo,
  palette.accent.amber,
  palette.accent.rose,
  palette.accent.sky,
  palette.brand[300],
  palette.accent.emerald,
];

function getQueueColor(index: number): string {
  return queueColors[index % queueColors.length];
}

function formatDateTime(iso: string): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function intervalDurationSeconds(start: string, end: string): number {
  return (new Date(end).getTime() - new Date(start).getTime()) / 1000;
}

function getBreachProbabilityColor(pct: number): string {
  if (pct >= 80) return palette.severity.crit;
  if (pct >= 50) return palette.severity.warn;
  return palette.severity.ok;
}

const labelStyle: React.CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.xs,
  fontWeight: typography.weight.semibold,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  marginBottom: spacing[2],
};

const valueStyle: React.CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.md,
  fontWeight: typography.weight.medium,
  color: palette.text.primary,
};

const smallValueStyle: React.CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.sm,
  color: palette.text.secondary,
};

export interface SLAExplainerProps {
  ticketId: number;
}

export default function SLAExplainer({ ticketId }: SLAExplainerProps) {
  const { data: timeline, isLoading: timelineLoading } = useQuery<TimelineData>({
    queryKey: ["sla-timeline", ticketId],
    queryFn: async () => {
      const resp = await client.get(`/sla/timeline/${ticketId}`);
      return resp.data;
    },
    enabled: !!ticketId,
  });

  const { data: metricsData, isLoading: metricsLoading } = useQuery<Metric[]>({
    queryKey: ["sla-metrics", ticketId],
    queryFn: async () => {
      const resp = await client.get("/sla/v2/metrics", { params: { ticket_id: ticketId } });
      return resp.data;
    },
    enabled: !!ticketId,
  });

  const { data: prediction, isLoading: predLoading } = useQuery<BreachPrediction>({
    queryKey: ["sla-prediction", ticketId],
    queryFn: async () => {
      const resp = await client.get("/sla/predictive/breach-eta", {
        params: { ticket_id: ticketId, metric_name: "first_response_time" },
      });
      return resp.data;
    },
    enabled: !!ticketId,
  });

  const metrics = metricsData || timeline?.metrics || [];

  const isBreached = useMemo(() => {
    return metrics.some((m) => m.breached);
  }, [metrics]);

  const breachedMetrics = useMemo(() => metrics.filter((m) => m.breached), [metrics]);

  const totalLifecycleSeconds = useMemo(() => {
    const intervals = timeline?.intervals;
    if (!intervals || intervals.length === 0) return 0;
    const first = new Date(intervals[0].start).getTime();
    const last = new Date(intervals[intervals.length - 1].end).getTime();
    return Math.max(0, (last - first) / 1000);
  }, [timeline]);

  const totalPendingSeconds = useMemo(() => {
    const intervals = timeline?.pending_intervals;
    if (!intervals) return 0;
    return intervals.reduce((sum, iv) => sum + intervalDurationSeconds(iv.start, iv.end), 0);
  }, [timeline]);

  const totalPauseSeconds = totalPendingSeconds;

  const totalWorkingSeconds = useMemo(() => {
    const intervals = timeline?.working_intervals;
    if (!intervals) return 0;
    return intervals.reduce((sum, iv) => sum + intervalDurationSeconds(iv.start, iv.end), 0);
  }, [timeline]);

  const ownerTimeMap = useMemo(() => {
    const map = new Map<string, number>();
    const intervals = timeline?.owner_intervals;
    if (!intervals) return map;
    for (const iv of intervals) {
      const dur = intervalDurationSeconds(iv.start, iv.end);
      map.set(iv.label, (map.get(iv.label) || 0) + dur);
    }
    return map;
  }, [timeline]);

  const maxOwnerSeconds = useMemo(() => {
    let max = 0;
    for (const v of ownerTimeMap.values()) {
      if (v > max) max = v;
    }
    return max;
  }, [ownerTimeMap]);

  const longestOwner = useMemo(() => {
    let max = 0;
    let name = "";
    for (const [k, v] of ownerTimeMap.entries()) {
      if (v > max) {
        max = v;
        name = k;
      }
    }
    return { name, seconds: max };
  }, [ownerTimeMap]);

  const longestQueue = useMemo(() => {
    const map = new Map<string, number>();
    const intervals = timeline?.queue_intervals;
    if (!intervals) return { name: "", seconds: 0 };
    for (const iv of intervals) {
      const dur = intervalDurationSeconds(iv.start, iv.end);
      map.set(iv.label, (map.get(iv.label) || 0) + dur);
    }
    let max = 0;
    let name = "";
    for (const [k, v] of map.entries()) {
      if (v > max) {
        max = v;
        name = k;
      }
    }
    return { name, seconds: max };
  }, [timeline]);

  const reassignmentCount = useMemo(() => {
    const intervals = timeline?.owner_intervals;
    if (!intervals) return 0;
    return Math.max(0, intervals.length - 1);
  }, [timeline]);

  const longestPauseInterval = useMemo(() => {
    const intervals = timeline?.pending_intervals;
    if (!intervals || intervals.length === 0) return { label: "", seconds: 0 };
    let max = 0;
    let label = "";
    for (const iv of intervals) {
      const dur = intervalDurationSeconds(iv.start, iv.end);
      if (dur > max) {
        max = dur;
        label = iv.label;
      }
    }
    return { label, seconds: max };
  }, [timeline]);

  const businessHoursExcluded = useMemo(() => {
    return metrics.reduce((sum, m) => sum + (m.business_hours_excluded || 0), 0);
  }, [metrics]);

  const slaPolicy = timeline?.sla_policy;

  const timelineColumns = [
    {
      title: "Тип",
      dataIndex: "type",
      key: "type",
      width: 80,
      render: (_: string, record: Interval) => (
        <Tooltip title={record.type}>
          <span style={{ color: typeColorMap[record.type] || palette.text.secondary, fontSize: 16 }}>
            {iconMap[record.type] || <RightCircleOutlined />}
          </span>
        </Tooltip>
      ),
    },
    {
      title: "Интервал",
      dataIndex: "label",
      key: "label",
      render: (_: string, record: Interval) => (
        <span style={valueStyle}>{record.label}</span>
      ),
    },
    {
      title: "Начало",
      dataIndex: "start",
      key: "start",
      width: 130,
      render: (v: string) => (
        <span style={smallValueStyle}>{formatDateTime(v)}</span>
      ),
    },
    {
      title: "Конец",
      dataIndex: "end",
      key: "end",
      width: 130,
      render: (v: string) => (
        <span style={smallValueStyle}>{v ? formatDateTime(v) : "текущий"}</span>
      ),
    },
    {
      title: "Длительность",
      dataIndex: "duration_seconds",
      key: "duration_seconds",
      width: 120,
      render: (_: unknown, record: Interval) => {
        const dur = record.duration_seconds || intervalDurationSeconds(record.start, record.end);
        return (
          <span style={{ ...valueStyle, fontVariantNumeric: "tabular-nums" }}>
            {formatHumanDuration(dur)}
          </span>
        );
      },
    },
  ];

  const metricColumns = [
    {
      title: "Метрика",
      dataIndex: "name",
      key: "name",
      render: (v: string) => {
        const labels: Record<string, string> = {
          first_response_time: "Время первого ответа",
          resolution_time: "Время решения",
          update_time: "Время обновления",
          close_time: "Время закрытия",
        };
        return <span style={valueStyle}>{labels[v] || v}</span>;
      },
    },
    {
      title: "Прошло времени",
      key: "elapsed",
      width: 120,
      render: (_: unknown, record: Metric) => (
        <span style={{ ...valueStyle, fontVariantNumeric: "tabular-nums" }}>
          {formatHumanDuration(record.seconds)}
        </span>
      ),
    },
    {
      title: "Исключено (раб. часы)",
      key: "biz_excluded",
      width: 130,
      render: (_: unknown, record: Metric) => (
        <span style={smallValueStyle}>
          {record.business_hours_excluded ? formatHumanDuration(record.business_hours_excluded) : "—"}
        </span>
      ),
    },
    {
      title: "Паузы",
      key: "paused",
      width: 100,
      render: (_: unknown, record: Metric) => (
        <span style={smallValueStyle}>
          {record.paused_time ? formatHumanDuration(record.paused_time) : "—"}
        </span>
      ),
    },
    {
      title: "Зачтено",
      key: "counted",
      width: 100,
      render: (_: unknown, record: Metric) => {
        const counted = record.counted_time ?? record.seconds - (record.business_hours_excluded || 0) - (record.paused_time || 0);
        return (
          <span style={{ ...valueStyle, fontVariantNumeric: "tabular-nums" }}>
            {formatHumanDuration(counted)}
          </span>
        );
      },
    },
    {
      title: "Цель",
      dataIndex: "target_seconds",
      key: "target",
      width: 100,
      render: (v: number) => (
        <span style={smallValueStyle}>{v ? formatHumanDuration(v) : "—"}</span>
      ),
    },
    {
      title: "Δ",
      dataIndex: "delta",
      key: "delta",
      width: 100,
      render: (v: number, record: Metric) => {
        const delta = v ?? record.seconds - (record.target_seconds || 0);
        const isPositive = delta > 0;
        return (
          <span
            style={{
              ...valueStyle,
              color: isPositive ? palette.severity.crit : palette.severity.ok,
              fontWeight: typography.weight.semibold,
            }}
          >
            {isPositive ? "+" : ""}{formatHumanDuration(Math.abs(delta))}
          </span>
        );
      },
    },
    {
      title: "Статус",
      key: "status",
      width: 100,
      render: (_: unknown, record: Metric) =>
        record.breached ? (
          <Tag icon={<CloseCircleOutlined />} color="error" style={{ margin: 0 }}>Нарушен</Tag>
        ) : (
          <Tag icon={<CheckCircleOutlined />} color="success" style={{ margin: 0 }}>В норме</Tag>
        ),
    },
    {
      title: "Риск",
      key: "risk",
      width: 180,
      render: (_: unknown, record: Metric) =>
        record.risk_level ? (
          <Space size={4}>
            <Tag
              color={
                record.risk_level === "high" ? "red" :
                record.risk_level === "medium" ? "orange" : "green"
              }
              style={{ margin: 0 }}
            >
              {record.risk_level === "high" ? "Высокий" :
               record.risk_level === "medium" ? "Средний" : "Низкий"}
            </Tag>
            {record.risk_score != null && (
              <span style={smallValueStyle}>({record.risk_score}%)</span>
            )}
          </Space>
        ) : (
          <span style={smallValueStyle}>—</span>
        ),
    },
    {
      title: "Причина риска",
      dataIndex: "risk_reason",
      key: "risk_reason",
      width: 200,
      render: (v: string) => (
        <span style={{ ...smallValueStyle, maxWidth: 200, display: "inline-block" }}>
          {v || "—"}
        </span>
      ),
    },
  ];

  const ownerColumns = [
    {
      title: "Владелец",
      dataIndex: "owner",
      key: "owner",
      render: (_: unknown, record: { owner: string; seconds: number }) => (
        <Space>
          <UserOutlined style={{ color: palette.text.tertiary }} />
          <span style={valueStyle}>{record.owner}</span>
        </Space>
      ),
    },
    {
      title: "Длительность",
      dataIndex: "seconds",
      key: "seconds",
      width: 140,
      render: (v: number) => (
        <span style={{ ...valueStyle, fontVariantNumeric: "tabular-nums" }}>
          {formatHumanDuration(v)}
        </span>
      ),
    },
    {
      title: "Доля",
      key: "pct",
      width: 100,
      render: (_: unknown, record: { seconds: number }) => {
        const pct = totalLifecycleSeconds > 0
          ? Math.round((record.seconds / totalLifecycleSeconds) * 100)
          : 0;
        return <span style={smallValueStyle}>{pct}%</span>;
      },
    },
    {
      title: "Прогресс",
      key: "progress",
      render: (_: unknown, record: { seconds: number }) => {
        const pct = totalLifecycleSeconds > 0
          ? (record.seconds / totalLifecycleSeconds) * 100
          : 0;
        const barColor =
          pct > 50 ? palette.severity.crit :
          pct > 25 ? palette.severity.warn :
          palette.severity.ok;
        return (
          <Progress
            percent={Math.round(pct)}
            size="small"
            strokeColor={barColor}
            trailColor={palette.borderLight}
            showInfo={false}
            style={{ margin: 0 }}
          />
        );
      },
    },
  ];

  const ownerTableData = useMemo(() => {
    return Array.from(ownerTimeMap.entries()).map(([owner, seconds]) => ({
      key: owner,
      owner,
      seconds,
    })).sort((a, b) => b.seconds - a.seconds);
  }, [ownerTimeMap]);

  const timelineBarSegments = useMemo(() => {
    const allIntervals = timeline?.intervals || [];
    if (allIntervals.length === 0) return [];

    const totalMs = new Date(allIntervals[allIntervals.length - 1].end).getTime() -
                    new Date(allIntervals[0].start).getTime();
    if (totalMs <= 0) return [];

    return allIntervals.map((iv, idx) => {
      const startMs = new Date(iv.start).getTime();
      const endMs = new Date(iv.end).getTime();
      const elapsedMs = endMs - startMs;
      const leftPct = ((startMs - new Date(allIntervals[0].start).getTime()) / totalMs) * 100;
      const widthPct = Math.max((elapsedMs / totalMs) * 100, 1);

      let color: string;
      let pattern: React.CSSProperties = {};
      if (iv.type === "pending") {
        color = palette.text.disabled;
        pattern = {
          backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 4px, ${palette.border} 4px, ${palette.border} 8px)`,
        };
      } else if (iv.type === "queue") {
        color = getQueueColor(idx);
      } else if (iv.type === "working") {
        color = palette.accent.teal;
      } else {
        color = palette.accent.indigo;
      }

      return { iv, leftPct, widthPct, color, pattern, idx };
    });
  }, [timeline]);

  const isBreachedMetric = timeline?.metrics?.some((m) => m.breached);

  if (timelineLoading || metricsLoading || predLoading) {
    return (
      <Card style={{ ...cardBaseStyle, textAlign: "center", padding: spacing[10] }}>
        <Typography.Text type="secondary" style={{ fontSize: typography.size.sm }}>
          Загрузка данных SLA...
        </Typography.Text>
      </Card>
    );
  }

  if (!timeline) {
    return (
      <Card style={{ ...cardBaseStyle, textAlign: "center", padding: spacing[10] }}>
        <Typography.Text type="secondary" style={{ fontSize: typography.size.sm }}>
          Нет данных SLA для данного тикета
        </Typography.Text>
      </Card>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: spacing[6] }}>
      {/* Header Section */}
      <Card style={cardBaseStyle}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space size={12}>
              <HistoryOutlined style={{ fontSize: 20, color: palette.brand[500] }} />
              <Typography.Title level={4} style={{ margin: 0, ...pageHeaderTitle }}>
                SLA Explanation
              </Typography.Title>
              <Tag style={{ fontSize: typography.size.xs, fontWeight: typography.weight.semibold, marginLeft: spacing[1] }}>
                #{ticketId}
              </Tag>
            </Space>
          </Col>
          <Col>
            <Space size={12}>
              {isBreached ? (
                <Badge
                  count="Нарушено"
                  style={{
                    backgroundColor: palette.severity.crit,
                    color: palette.white,
                    fontWeight: typography.weight.semibold,
                    fontSize: typography.size.xs,
                    border: "none",
                    boxShadow: "none",
                    padding: "0 12px",
                    lineHeight: "22px",
                    height: 24,
                    borderRadius: radius.full,
                  }}
                />
              ) : (
                <Badge
                  count="В норме"
                  style={{
                    backgroundColor: palette.severity.ok,
                    color: palette.white,
                    fontWeight: typography.weight.semibold,
                    fontSize: typography.size.xs,
                    border: "none",
                    boxShadow: "none",
                    padding: "0 12px",
                    lineHeight: "22px",
                    height: 24,
                    borderRadius: radius.full,
                  }}
                />
              )}
              {prediction && (
                <Tooltip title={`Прогнозируемая вероятность нарушения: ${Math.round(prediction.probability)}%`}>
                  <Space size={4}>
                    <AlertOutlined style={{ color: getBreachProbabilityColor(prediction.probability) }} />
                    <span style={{ ...smallValueStyle }}>
                      Риск: {Math.round(prediction.probability)}%
                    </span>
                  </Space>
                </Tooltip>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Section 1: SLA Policy Applied */}
      <Card style={cardBaseStyle} title={<span style={sectionTitleStyle}>Политика SLA</span>}>
        <Row gutter={[spacing[6], spacing[4]]}>
          <Col span={12}>
            <div style={labelStyle}>Применённая политика</div>
            <div style={valueStyle}>{slaPolicy?.name || "—"}</div>
            {slaPolicy?.match_reason && (
              <div style={{ ...smallValueStyle, marginTop: spacing[1] }}>
                {slaPolicy.match_reason}
              </div>
            )}
          </Col>
          <Col span={6}>
            <div style={labelStyle}>Цель ответа</div>
            <div style={valueStyle}>
              {slaPolicy?.response_target_seconds
                ? formatHumanDuration(slaPolicy.response_target_seconds)
                : "—"}
            </div>
          </Col>
          <Col span={6}>
            <div style={labelStyle}>Цель решения</div>
            <div style={valueStyle}>
              {slaPolicy?.resolution_target_seconds
                ? formatHumanDuration(slaPolicy.resolution_target_seconds)
                : "—"}
            </div>
          </Col>
          <Col span={8}>
            <div style={labelStyle}>Календарь</div>
            <Space>
              <ClockCircleOutlined style={{ color: palette.accent.indigo }} />
              <span style={valueStyle}>{slaPolicy?.calendar || "24x7"}</span>
            </Space>
          </Col>
          <Col span={16}>
            <div style={labelStyle}>Правила эскалации</div>
            {slaPolicy?.escalation_rules && slaPolicy.escalation_rules.length > 0 ? (
              <Space wrap>
                {slaPolicy.escalation_rules.map((rule, i) => (
                  <Tag key={i} color="blue" style={{ margin: 0 }}>{rule}</Tag>
                ))}
              </Space>
            ) : (
              <span style={smallValueStyle}>Не настроены</span>
            )}
          </Col>
        </Row>
      </Card>

      {/* Section 2: Timeline Visualization */}
      <Card style={cardBaseStyle} title={<span style={sectionTitleStyle}>Хронология</span>}>
        {/* Visual bar chart */}
        {timelineBarSegments.length > 0 && (
          <div style={{ position: "relative", height: 40, marginBottom: spacing[6], marginTop: spacing[2] }}>
            {/* Bar track */}
            <div style={{ position: "relative", height: 28, background: palette.borderLight, borderRadius: radius.sm, overflow: "hidden" }}>
              {timelineBarSegments.map((seg) => (
                <Tooltip
                  key={seg.idx}
                  title={`${seg.iv.label}: ${formatHumanDuration(intervalDurationSeconds(seg.iv.start, seg.iv.end))}`}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: `${seg.leftPct}%`,
                      width: `${seg.widthPct}%`,
                      height: "100%",
                      backgroundColor: seg.color,
                      opacity: seg.iv.type === "pending" ? 0.4 : 0.7,
                      ...seg.pattern,
                      borderRight: seg.idx < timelineBarSegments.length - 1
                        ? `1px solid ${palette.white}`
                        : "none",
                      cursor: "pointer",
                      transition: "opacity 0.15s",
                    }}
                    onMouseEnter={(e) => { (e.target as HTMLElement).style.opacity = "1"; }}
                    onMouseLeave={(e) => { (e.target as HTMLElement).style.opacity = seg.iv.type === "pending" ? "0.4" : "0.7"; }}
                  />
                </Tooltip>
              ))}
              {/* Breach indicator */}
              {isBreached && (
                <Tooltip title="Момент нарушения SLA">
                  <div
                    style={{
                      position: "absolute",
                      right: `${Math.max(2, 100 - (timelineBarSegments.length > 0 ? timelineBarSegments[timelineBarSegments.length - 1].leftPct + timelineBarSegments[timelineBarSegments.length - 1].widthPct : 0))}%`,
                      top: -4,
                      width: 2,
                      height: 36,
                      backgroundColor: palette.severity.crit,
                      zIndex: 10,
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        top: -6,
                        left: -5,
                        width: 12,
                        height: 12,
                        borderRadius: "50%",
                        backgroundColor: palette.severity.crit,
                        border: `2px solid ${palette.white}`,
                      }}
                    />
                  </div>
                </Tooltip>
              )}
            </div>
            {/* Legend */}
            <div style={{ display: "flex", gap: spacing[4], marginTop: spacing[2], flexWrap: "wrap" }}>
              <LegendItem color={palette.brand[500]} label="Очередь" />
              <LegendItem color={palette.accent.indigo} label="Владелец" />
              <LegendItem color={palette.accent.teal} label="В работе" />
              <LegendItem color={palette.text.disabled} label="Пауза" dashed />
              {isBreached && <LegendItem color={palette.severity.crit} label="Нарушение" />}
            </div>
          </div>
        )}

        {/* Timeline table */}
        <Table
          dataSource={timeline.intervals || []}
          columns={timelineColumns}
          rowKey={(_, idx) => String(idx)}
          size="small"
          pagination={false}
          style={{ marginTop: spacing[2] }}
          components={{
            header: {
              cell: (props: React.HTMLAttributes<HTMLTableHeaderCellElement>) => (
                <th {...props} style={{ ...props.style, ...tableHeaderStyle }} />
              ),
            },
          }}
        />
      </Card>

      {/* Section 3: Metric Breakdown */}
      <Card style={cardBaseStyle} title={<span style={sectionTitleStyle}>Разбор метрик</span>}>
        <Table
          dataSource={metrics}
          columns={metricColumns}
          rowKey="name"
          size="small"
          pagination={false}
          scroll={{ x: "max-content" }}
          components={{
            header: {
              cell: (props: React.HTMLAttributes<HTMLTableHeaderCellElement>) => (
                <th {...props} style={{ ...props.style, ...tableHeaderStyle }} />
              ),
            },
          }}
        />
      </Card>

      {/* Section 4: Breach Root Cause */}
      {isBreached && (
        <Card style={cardBaseStyle} title={<span style={sectionTitleStyle}>Причина нарушения</span>}>
          <Row gutter={[spacing[6], spacing[4]]}>
            <Col span={8}>
              <div style={rootCauseCardStyle}>
                <ApartmentOutlined style={{ color: palette.severity.crit, fontSize: 20 }} />
                <div style={{ ...labelStyle, marginTop: spacing[2], marginBottom: spacing[1] }}>
                  Какая очередь вызвала нарушение
                </div>
                <div style={valueStyle}>{longestQueue.name || "—"}</div>
                {longestQueue.seconds > 0 && (
                  <div style={smallValueStyle}>
                    {formatHumanDuration(longestQueue.seconds)} в очереди
                  </div>
                )}
              </div>
            </Col>
            <Col span={8}>
              <div style={rootCauseCardStyle}>
                <FieldTimeOutlined style={{ color: palette.accent.amber, fontSize: 20 }} />
                <div style={{ ...labelStyle, marginTop: spacing[2], marginBottom: spacing[1] }}>
                  Где потеряно больше всего времени
                </div>
                <div style={valueStyle}>{longestQueue.name || "—"}</div>
                {longestQueue.seconds > 0 && (
                  <div style={smallValueStyle}>
                    {formatHumanDuration(longestQueue.seconds)}
                  </div>
                )}
              </div>
            </Col>
            <Col span={8}>
              <div style={rootCauseCardStyle}>
                <UserOutlined style={{ color: palette.accent.indigo, fontSize: 20 }} />
                <div style={{ ...labelStyle, marginTop: spacing[2], marginBottom: spacing[1] }}>
                  Кто владел тикетом дольше всех
                </div>
                <div style={valueStyle}>{longestOwner.name || "—"}</div>
                {longestOwner.seconds > 0 && (
                  <div style={smallValueStyle}>
                    {formatHumanDuration(longestOwner.seconds)}
                  </div>
                )}
              </div>
            </Col>
            <Col span={8}>
              <div style={rootCauseCardStyle}>
                <PauseCircleOutlined style={{ color: palette.text.disabled, fontSize: 20 }} />
                <div style={{ ...labelStyle, marginTop: spacing[2], marginBottom: spacing[1] }}>
                  Самый долгий простой
                </div>
                <div style={valueStyle}>{longestPauseInterval.label || "—"}</div>
                {longestPauseInterval.seconds > 0 && (
                  <div style={smallValueStyle}>
                    {formatHumanDuration(longestPauseInterval.seconds)}
                  </div>
                )}
              </div>
            </Col>
            <Col span={8}>
              <div style={rootCauseCardStyle}>
                <ArrowRightOutlined style={{ color: palette.accent.sky, fontSize: 20 }} />
                <div style={{ ...labelStyle, marginTop: spacing[2], marginBottom: spacing[1] }}>
                  Передачи тикета
                </div>
                <div style={valueStyle}>{reassignmentCount} передач</div>
              </div>
            </Col>
            <Col span={8}>
              <div style={rootCauseCardStyle}>
                <ClockCircleOutlined style={{ color: palette.accent.teal, fontSize: 20 }} />
                <div style={{ ...labelStyle, marginTop: spacing[2], marginBottom: spacing[1] }}>
                  Исключено по бизнес-часам
                </div>
                <div style={valueStyle}>
                  {businessHoursExcluded > 0 ? formatHumanDuration(businessHoursExcluded) : "—"}
                </div>
              </div>
            </Col>
          </Row>

          {breachedMetrics.length > 0 && (
            <div style={{ marginTop: spacing[4] }}>
              <Divider style={{ margin: `${spacing[3]} 0` }} />
              <div style={labelStyle}>Какие метрики нарушены</div>
              <Space wrap>
                {breachedMetrics.map((m) => (
                  <Tag
                    key={m.name}
                    icon={<CloseCircleOutlined />}
                    color="error"
                    style={{ margin: 0 }}
                  >
                    {m.name === "first_response_time" ? "Время первого ответа" :
                     m.name === "resolution_time" ? "Время решения" : m.name}
                    {m.delta ? ` (+${formatHumanDuration(Math.abs(m.delta))})` : ""}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
        </Card>
      )}

      {/* Section 5: Who Delayed */}
      {ownerTableData.length > 0 && (
        <Card style={cardBaseStyle} title={<span style={sectionTitleStyle}>Кто задерживал</span>}>
          <Table
            dataSource={ownerTableData}
            columns={ownerColumns}
            rowKey="owner"
            size="small"
            pagination={false}
            components={{
              header: {
                cell: (props: React.HTMLAttributes<HTMLTableHeaderCellElement>) => (
                  <th {...props} style={{ ...props.style, ...tableHeaderStyle }} />
                ),
              },
            }}
          />
        </Card>
      )}
    </div>
  );
}

function LegendItem({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <Space size={6} style={{ display: "inline-flex", alignItems: "center" }}>
      <span
        style={{
          display: "inline-block",
          width: 12,
          height: 4,
          borderRadius: 2,
          backgroundColor: color,
          opacity: 0.7,
          ...(dashed ? { backgroundImage: `repeating-linear-gradient(90deg, ${color}, ${color} 4px, transparent 4px, transparent 8px)` } : {}),
        }}
      />
      <span style={{ fontSize: typography.size.xs, color: palette.text.tertiary }}>{label}</span>
    </Space>
  );
}

const cardBaseStyle: React.CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.border}`,
  borderRadius: radius.lg,
  boxShadow: shadows.card,
};

const sectionTitleStyle: React.CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.xs,
  fontWeight: typography.weight.semibold,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
};

const pageHeaderTitle: React.CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size["2xl"],
  fontWeight: typography.weight.semibold,
  color: palette.text.primary,
  letterSpacing: "-0.02em",
};

const tableHeaderStyle: React.CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.xs,
  fontWeight: typography.weight.semibold,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  background: "transparent",
  borderBottom: `1px solid ${palette.borderLight}`,
  padding: `${spacing[2]} ${spacing[3]}`,
};

const rootCauseCardStyle: React.CSSProperties = {
  background: palette.page,
  borderRadius: radius.md,
  padding: spacing[4],
  border: `1px solid ${palette.borderLight}`,
};
