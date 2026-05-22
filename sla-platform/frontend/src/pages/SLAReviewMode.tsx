import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Spin, Empty, Alert, Typography, Card, Row, Col, Table, Tag, Tabs,
} from "antd";
import { AlertOutlined, EyeInvisibleOutlined, FireOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { operationsReviewApi, type ReviewOverviewResponse } from "../api/operationsReview";
import { useFavorites } from "../contexts/FavoritesContext";
import RuntimeErrorBoundary from "../components/safety/RuntimeErrorBoundary";
import "../design/v1-tokens.css";

const { Title, Text } = Typography;

function pct(n: number, total: number) {
  return total > 0 ? `${((n / total) * 100).toFixed(1)}%` : "—";
}

function SLAReviewModeInner() {
  const { activeFilter } = useFavorites();
  const queues = activeFilter.length ? activeFilter : undefined;

  const q = useQuery({
    queryKey: ["sla-review-overview", queues?.join(",") || ""],
    queryFn: () => operationsReviewApi.reviewOverview(queues),
    refetchInterval: 60_000,
  });

  const d: ReviewOverviewResponse | undefined = q.data;

  const summary = useMemo(() => {
    if (!d) return null;
    return {
      lossHours: d.top_loss_queues.reduce((a, x) => a + x.total_wall_hours, 0),
      noOwnerHours: d.parking_lots.reduce((a, x) => a + x.no_owner_hours, 0),
      hiddenBreaches: d.hidden_breach_delta.hidden_breaches,
      silentCount: d.silent_breaches.length,
      hotPotato: d.hot_potato.length,
      dyingTickets: d.dying_in_queue.length,
    };
  }, [d]);

  if (q.isLoading || q.isPending) {
    return <div style={{ padding: 60, textAlign: "center" }}><Spin size="large" /></div>;
  }
  if (q.isError) {
    return <Alert type="error" showIcon message="Не удалось загрузить SLA Review"
      description={(q.error as Error | undefined)?.message ?? "Ошибка"} />;
  }
  if (!d || !summary) return <Empty description="Нет данных" />;

  return (
    <div className="v1" style={{ background: "var(--v1-bg)", minHeight: "100vh", padding: 24 }}>
      <Title level={3} style={{ margin: 0, color: "var(--v1-text)" }}>
        SLA Review Mode
      </Title>
      <Text style={{ color: "var(--v1-text-3)" }}>
        Единая панель для еженедельного review:&nbsp;
        где потеряли SLA, кто держал, что зациклилось, какие нарушения скрыты.
        {queues ? ` · фильтр на ${queues.length} очередей` : ""}
      </Text>

      {/* KPI strip */}
      <Row gutter={[12, 12]} style={{ marginTop: 18 }}>
        <Col xs={12} md={6}>
          <div className="v1-kpi">
            <span className="label">Совокупные часы SLA</span>
            <span className="value num">{Math.round(summary.lossHours).toLocaleString("ru-RU")}</span>
            <span className="sub">по топ-10 очередям</span>
          </div>
        </Col>
        <Col xs={12} md={6}>
          <div className="v1-kpi">
            <span className="label">Часов без владельца</span>
            <span className="value num" style={{ color: "var(--v1-warning)" }}>
              {Math.round(summary.noOwnerHours).toLocaleString("ru-RU")}
            </span>
            <span className="sub">parking lots</span>
          </div>
        </Col>
        <Col xs={12} md={6}>
          <div className="v1-kpi">
            <span className="label">Скрытые нарушения</span>
            <span className="value num" style={{ color: "var(--v1-danger)" }}>
              {summary.hiddenBreaches}
            </span>
            <span className="sub">wall − active</span>
          </div>
        </Col>
        <Col xs={12} md={6}>
          <div className="v1-kpi">
            <span className="label">Тихих нарушений</span>
            <span className="value num">{summary.silentCount}</span>
            <span className="sub">silent breaches</span>
          </div>
        </Col>
      </Row>

      <Card
        bordered={false}
        style={{
          background: "var(--v1-surface)",
          border: "1px solid var(--v1-border)",
          borderRadius: "var(--v1-radius-lg)",
          marginTop: 18,
        }}
      >
        <Tabs
          items={[
            {
              key: "loss",
              label: <span><FireOutlined /> Топ потерь ({d.top_loss_queues.length})</span>,
              children: (
                <Table
                  size="small" rowKey="queue" pagination={false}
                  dataSource={d.top_loss_queues}
                  columns={[
                    { title: "Очередь", dataIndex: "queue" },
                    {
                      title: "Часов всего", dataIndex: "total_wall_hours", width: 140, align: "right",
                      render: (v: number) => <span className="num">{v.toLocaleString("ru-RU")}</span>,
                    },
                    {
                      title: "Часов no-owner", dataIndex: "no_owner_hours", width: 150, align: "right",
                      render: (v: number) => <span className="num">{v.toLocaleString("ru-RU")}</span>,
                    },
                    {
                      title: "Доля", dataIndex: "share_of_total_pct", width: 100, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 20 ? "red" : v >= 10 ? "orange" : "default"}>
                          {v.toFixed(1)}%
                        </Tag>
                      ),
                    },
                    { title: "Тикетов", dataIndex: "distinct_tickets", width: 100, align: "right" },
                  ]}
                />
              ),
            },
            {
              key: "parking",
              label: <span><EyeInvisibleOutlined /> Parking lots ({d.parking_lots.length})</span>,
              children: (
                <Table
                  size="small" rowKey="queue" pagination={false}
                  dataSource={d.parking_lots}
                  columns={[
                    { title: "Очередь", dataIndex: "queue" },
                    {
                      title: "Часов без владельца", dataIndex: "no_owner_hours", width: 180, align: "right",
                      render: (v: number) => <span className="num">{v.toLocaleString("ru-RU")}</span>,
                    },
                    {
                      title: "% без владельца", dataIndex: "no_owner_pct", width: 140, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 90 ? "red" : v >= 60 ? "orange" : "default"}>{v.toFixed(0)}%</Tag>
                      ),
                    },
                    { title: "Тикетов", dataIndex: "distinct_tickets", width: 100, align: "right" },
                  ]}
                />
              ),
            },
            {
              key: "dying",
              label: <span><AlertOutlined /> Dying ({d.dying_in_queue.length})</span>,
              children: (
                <Table
                  size="small" rowKey="ticket_id" pagination={false}
                  dataSource={d.dying_in_queue}
                  columns={[
                    { title: "№", dataIndex: "ticket_number", width: 170,
                      render: (v) => <span className="mono">{v}</span> },
                    { title: "Очередь", dataIndex: "current_queue" },
                    { title: "Состояние", dataIndex: "current_state", width: 130 },
                    { title: "Владелец", dataIndex: "current_owner", width: 160,
                      render: (v) => v ?? <Tag color="red">нет</Tag> },
                    {
                      title: "Часов всего", dataIndex: "total_wall_hours", width: 130, align: "right",
                      render: (v: number) => <span className="num">{v.toLocaleString("ru-RU")}</span>,
                    },
                  ]}
                />
              ),
            },
            {
              key: "potato",
              label: <span><ThunderboltOutlined /> Hot-potato ({d.hot_potato.length})</span>,
              children: (
                <Table
                  size="small" rowKey="ticket_id" pagination={false}
                  dataSource={d.hot_potato}
                  columns={[
                    { title: "№", dataIndex: "ticket_number", width: 170,
                      render: (v) => <span className="mono">{v}</span> },
                    { title: "Перемещений", dataIndex: "moves", width: 130, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 20 ? "red" : v >= 10 ? "orange" : "default"}>{v}</Tag>
                      ) },
                    { title: "Смены владельца", dataIndex: "owner_changes", width: 160, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 10 ? "red" : v >= 5 ? "orange" : "default"}>{v}</Tag>
                      ) },
                    { title: "Очередей затронуто", dataIndex: "distinct_queues", width: 170, align: "right" },
                  ]}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}

export default function SLAReviewMode() {
  return (
    <RuntimeErrorBoundary label="SLA Review">
      <SLAReviewModeInner />
    </RuntimeErrorBoundary>
  );
}
