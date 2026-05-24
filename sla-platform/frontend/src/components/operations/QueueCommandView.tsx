import { useQuery } from "@tanstack/react-query";
import { Card, Col, Row, Tag, Typography, Table, Tabs, Spin, Empty, Alert } from "antd";
import { useMemo } from "react";
import {
  queueCommandCenterApi,
  type QueueCommandCenterResponse,
  type QueueCCMetric,
} from "../../api/queueCommandCenter";
import { useTimeScope } from "../../contexts/TimeScopeContext";
import RuntimeErrorBoundary from "../safety/RuntimeErrorBoundary";
import "../../design/v1-tokens.css";

const { Title, Text } = Typography;

interface Props {
  queueName: string;
}

function fmtSec(sec: number): string {
  if (!Number.isFinite(sec) || sec <= 0) return "—";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h >= 24) {
    const d = Math.floor(h / 24);
    return `${d}д ${h % 24}ч`;
  }
  if (h > 0) return m ? `${h}ч ${m}м` : `${h}ч`;
  return `${m}м`;
}

function breachColor(pct: number): string {
  if (pct >= 60) return "red";
  if (pct >= 30) return "orange";
  if (pct >= 10) return "gold";
  return "default";
}

function MetricCard({ label, m, suffix = "" }: {
  label: string;
  m: QueueCCMetric | undefined;
  suffix?: string;
}) {
  const breach = m?.breach_pct ?? 0;
  return (
    <div className="v1-kpi">
      <span className="label">{label}</span>
      <span className="value num" style={{ fontSize: 22 }}>
        {m?.n ? `${m.breaches}/${m.n}` : "—"}
        {suffix}
      </span>
      <span className="sub">
        <Tag color={breachColor(breach)} style={{ marginRight: 6 }}>{breach.toFixed(1)}%</Tag>
        avg {fmtSec(m?.avg_seconds ?? 0)} · p90 {fmtSec(m?.p90_seconds ?? 0)}
      </span>
    </div>
  );
}

/**
 * Per-queue operational command view. Renders an aggregate dashboard for ONE queue.
 *
 * Hooks-first pattern (post-v1.8.1 stabilization rule):
 *   - All hooks (useQuery + useMemo) called UNCONDITIONALLY
 *   - All branching happens AFTER hooks
 *   - Wrapped by parent in RuntimeErrorBoundary so any per-widget crash
 *     does not blank the whole page
 */
function QueueCommandViewInner({ queueName }: Props) {
  // ── ALL HOOKS FIRST ─────────────────────────────────────────────
  const { toParams } = useTimeScope();
  const scopeParams = toParams();
  const scopeKey = JSON.stringify(scopeParams);
  const q = useQuery({
    queryKey: ["queue-command-center", queueName, scopeKey],
    queryFn: () => queueCommandCenterApi.get(queueName, scopeParams),
    refetchInterval: 60_000,
  });

  const d: QueueCommandCenterResponse | undefined = q.data;

  const hidden = useMemo(() => {
    const w = d?.sla_metrics?.wall_resolution_time?.breaches ?? 0;
    const a = d?.sla_metrics?.resolution_time?.breaches ?? 0;
    return Math.max(0, w - a);
  }, [d?.sla_metrics?.wall_resolution_time?.breaches,
      d?.sla_metrics?.resolution_time?.breaches]);

  const topEngineerOverload = useMemo(() => {
    const e = d?.engineers?.[0];
    if (!e) return null;
    const h = Number(e.hours_owned ?? 0);
    return { owner: e.owner, hours: h, ratio: h / 160 };
  }, [d?.engineers]);

  // ── BRANCHING NOW SAFE ──────────────────────────────────────────
  if (q.isLoading || q.isPending) {
    return <div style={{ textAlign: "center", padding: 40 }}><Spin size="large" /></div>;
  }
  if (q.isError) {
    const message = (q.error as Error | undefined)?.message ?? "Ошибка загрузки";
    return <Alert type="error" showIcon message="Не удалось загрузить очередь" description={message} />;
  }
  if (!d) return <Empty description="Нет данных" />;

  const s = d.snapshot;
  const fr = d.sla_metrics.first_response_time;
  const rt = d.sla_metrics.resolution_time;
  const wr = d.sla_metrics.wall_resolution_time;

  return (
    <div className="v1">
      <Row gutter={[16, 16]} style={{ marginBottom: 18 }}>
        <Col xs={24} md={6}>
          <div className="v1-kpi">
            <span className="label">Тикеты</span>
            <span className="value num">{s.total}</span>
            <span className="sub">
              открыто <b>{s.open_now}</b> · закрыто {s.closed_now}
              {s.open_no_owner > 0 && (
                <Tag color="red" style={{ marginLeft: 6 }}>{s.open_no_owner} без owner'а</Tag>
              )}
            </span>
          </div>
        </Col>
        <Col xs={24} md={6}>
          <MetricCard label="Первая реакция (active SLA)" m={fr} />
        </Col>
        <Col xs={24} md={6}>
          <MetricCard label="Разрешение (active SLA)" m={rt} />
        </Col>
        <Col xs={24} md={6}>
          <div className="v1-kpi">
            <span className="label">Скрытые нарушения</span>
            <span className="value num" style={{ color: hidden > 0 ? "var(--v1-danger)" : "var(--v1-text)" }}>
              {hidden}
            </span>
            <span className="sub">
              wall-clock {wr?.breaches ?? 0} − active {rt?.breaches ?? 0}
            </span>
          </div>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: "engineers",
            label: `Инженеры (${d.engineers.length})`,
            children: (
              <>
                {topEngineerOverload && topEngineerOverload.ratio >= 2 && (
                  <Alert
                    type="warning" showIcon style={{ marginBottom: 12 }}
                    message={`${topEngineerOverload.owner} перегружен в ${topEngineerOverload.ratio.toFixed(1)}× от месячной нормы (${topEngineerOverload.hours.toFixed(0)}ч)`}
                  />
                )}
                <Table
                  size="small" rowKey="owner" pagination={false}
                  dataSource={d.engineers}
                  columns={[
                    { title: "Инженер", dataIndex: "owner" },
                    { title: "Тикетов", dataIndex: "tickets_held", width: 110, align: "right" },
                    {
                      title: "Часов",
                      dataIndex: "hours_owned",
                      width: 120, align: "right",
                      render: (v) => <span className="num">{Number(v).toFixed(1)}</span>,
                    },
                    {
                      title: "Overload",
                      key: "overload", width: 140, align: "right",
                      render: (_v, r) => {
                        const ratio = Number(r.hours_owned) / 160;
                        return (
                          <Tag color={ratio >= 2 ? "red" : ratio >= 1 ? "orange" : "default"}>
                            {ratio.toFixed(2)}×
                          </Tag>
                        );
                      },
                    },
                  ]}
                />
              </>
            ),
          },
          {
            key: "aging",
            label: `Aging open (${d.aging_open_tickets.length})`,
            children: d.aging_open_tickets.length === 0
              ? <Empty description="Нет открытых тикетов" />
              : (
                <Table
                  size="small" rowKey="ticket_id" pagination={false}
                  dataSource={d.aging_open_tickets}
                  columns={[
                    { title: "№", dataIndex: "ticket_number", width: 170, render: (v) => <span className="mono">{v}</span> },
                    { title: "Заголовок", dataIndex: "title", ellipsis: true },
                    { title: "Owner", dataIndex: "current_owner", width: 160, render: (v) => v ?? <Tag color="red">нет</Tag> },
                    { title: "Состояние", dataIndex: "current_state", width: 130 },
                    {
                      title: "Возраст (дней)", dataIndex: "age_days", width: 130, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 30 ? "red" : v >= 7 ? "orange" : "default"}>
                          {v.toFixed(0)}
                        </Tag>
                      ),
                    },
                  ]}
                />
              ),
          },
          {
            key: "routes",
            label: "Маршруты",
            children: (
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Card title="Куда уходят отсюда (top 8)" size="small" bordered={false}>
                    <Table
                      size="small" rowKey="dest_queue" pagination={false}
                      dataSource={d.transitions.outbound}
                      columns={[
                        { title: "Очередь", dataIndex: "dest_queue" },
                        { title: "Переходов", dataIndex: "n", align: "right", width: 110 },
                        { title: "Тикетов", dataIndex: "tickets", align: "right", width: 90 },
                      ]}
                    />
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card title="Откуда приходят (top 8)" size="small" bordered={false}>
                    <Table
                      size="small" rowKey="src_queue" pagination={false}
                      dataSource={d.transitions.inbound}
                      columns={[
                        { title: "Очередь", dataIndex: "src_queue" },
                        { title: "Переходов", dataIndex: "n", align: "right", width: 110 },
                        { title: "Тикетов", dataIndex: "tickets", align: "right", width: 90 },
                      ]}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: "bounces",
            label: `Bounces (${d.bounces.length})`,
            children: d.bounces.length === 0
              ? <Empty description="Тикеты не возвращаются в эту очередь" />
              : (
                <Table
                  size="small" rowKey="ticket_id" pagination={false}
                  dataSource={d.bounces}
                  columns={[
                    { title: "Ticket ID", dataIndex: "ticket_id", width: 150 },
                    {
                      title: "Возвраты в очередь", dataIndex: "visits", width: 200, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 5 ? "red" : v >= 3 ? "orange" : "default"}>{v}×</Tag>
                      ),
                    },
                  ]}
                />
              ),
          },
        ]}
      />
    </div>
  );
}

export default function QueueCommandView(props: Props) {
  // Wrap each per-queue card in its own boundary so one broken queue
  // doesn't blank the dashboard.
  return (
    <RuntimeErrorBoundary label={`виджет очереди ${props.queueName}`} resetKey={props.queueName}>
      <QueueCommandViewInner {...props} />
    </RuntimeErrorBoundary>
  );
}
