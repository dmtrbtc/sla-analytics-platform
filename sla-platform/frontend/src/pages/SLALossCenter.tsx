import { useMemo } from "react";
import { Spin, Empty, Tag, Table, Tabs, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { slaLossApi, type LossOverview } from "../api/slaLoss";
import { useFavorites } from "../contexts/FavoritesContext";
import { useTimeScope } from "../contexts/TimeScopeContext";
import "../design/v1-tokens.css";

const { Title, Text } = Typography;

/**
 * SLA Loss Center — first page rendered with the v1 design tokens.
 *
 * Verifies the rollout strategy: opt-in via `<div className="v1">`,
 * use Ant Design `<Table>` underneath (no custom table primitives),
 * apply the calm light palette to KPI cards only. No global theme
 * override. Verified by `npm run build` clean.
 */
export default function SLALossCenter() {
  const { activeFilter } = useFavorites();
  const { toParams, label: scopeLabel } = useTimeScope();
  const queues = activeFilter.length ? activeFilter : undefined;
  const scopeParams = toParams();

  const overviewQ = useQuery({
    queryKey: [
      "sla-loss-overview",
      queues?.join(",") || "",
      JSON.stringify(scopeParams),
    ],
    queryFn: () => slaLossApi.overview(queues, scopeParams),
    refetchInterval: 60_000,
  });

  // CRITICAL: every hook below must run on EVERY render, regardless of
  // loading / error / data state. The previous version returned early
  // (Spin / Empty) and then called useMemo — that violates React's hooks
  // rules and produced a runtime crash ("Rendered more hooks than during
  // the previous render"), which blanked the whole page. Hooks first,
  // branching second.
  const d: LossOverview | undefined = overviewQ.data;

  const totalLossHours = useMemo(
    () => (d?.top_loss_queues ?? []).reduce((a, q) => a + (q.total_wall_hours || 0), 0),
    [d?.top_loss_queues],
  );
  const totalNoOwnerHours = useMemo(
    () => (d?.parking_lots ?? []).reduce((a, q) => a + (q.no_owner_hours || 0), 0),
    [d?.parking_lots],
  );

  if (overviewQ.isLoading) {
    return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  }
  if (overviewQ.isError || !d) {
    return <Empty description="Нет данных по потерям SLA" style={{ marginTop: 80 }} />;
  }

  const dyingCount = d.dying_in_queue.length;
  const mostExp = d.most_expensive[0];

  return (
    <div className="v1" style={{ background: "var(--v1-bg)", minHeight: "100vh", padding: 24 }}>
      <Title level={3} style={{ margin: 0, color: "var(--v1-text)" }}>
        Где теряется SLA
      </Title>
      <Text style={{ color: "var(--v1-text-3)" }}>
        Атрибуция времени по очередям и владельцам · scope: <b>{scopeLabel}</b>
        {queues ? ` · фильтр на ${queues.length} очередей` : ""}
      </Text>

      {/* KPI strip */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 18,
      }}>
        <div className="v1-kpi">
          <span className="label">Совокупные часы SLA</span>
          <span className="value num">{Math.round(totalLossHours).toLocaleString("ru-RU")}</span>
          <span className="sub">по топ-15 очередям</span>
        </div>
        <div className="v1-kpi">
          <span className="label">Часов без владельца</span>
          <span className="value num" style={{ color: "var(--v1-danger)" }}>
            {Math.round(totalNoOwnerHours).toLocaleString("ru-RU")}
          </span>
          <span className="sub">parking lots — топ 15</span>
        </div>
        <div className="v1-kpi">
          <span className="label">Тикетов «умирают» в очереди</span>
          <span className="value num" style={{ color: "var(--v1-warning)" }}>
            {dyingCount}
          </span>
          <span className="sub">открытые, высокий wall time</span>
        </div>
        <div className="v1-kpi">
          <span className="label">Дороже всего на тикет</span>
          <span className="value num" style={{ fontSize: 22 }}>
            {mostExp?.cost_per_ticket_hours?.toFixed(1) ?? "—"} ч
          </span>
          <span className="sub" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
            {mostExp?.queue || "—"}
          </span>
        </div>
      </div>

      {/* Detail tabs */}
      <div style={{
        background: "var(--v1-surface)",
        border: "1px solid var(--v1-border)",
        borderRadius: "var(--v1-radius-lg)",
        boxShadow: "var(--v1-shadow-1)",
        marginTop: 18, padding: 16,
      }}>
        <Tabs
          items={[
            {
              key: "top",
              label: `Топ потерь (${d.top_loss_queues.length})`,
              children: (
                <Table
                  size="small" rowKey="queue" pagination={false}
                  dataSource={d.top_loss_queues}
                  columns={[
                    { title: "Очередь", dataIndex: "queue" },
                    {
                      title: "Часов всего", dataIndex: "total_wall_hours",
                      width: 130, align: "right",
                      render: (v: number) => <span className="num">{v?.toLocaleString("ru-RU")}</span>,
                      sorter: (a, b) => (a.total_wall_hours || 0) - (b.total_wall_hours || 0),
                    },
                    {
                      title: "Доля", dataIndex: "share_of_total_pct",
                      width: 90, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 20 ? "red" : v >= 10 ? "orange" : "default"}>
                          {v?.toFixed(1)}%
                        </Tag>
                      ),
                    },
                    {
                      title: "Часов без владельца", dataIndex: "no_owner_hours",
                      width: 170, align: "right",
                      render: (v: number) => <span className="num">{v?.toLocaleString("ru-RU")}</span>,
                    },
                    {
                      title: "Тикетов", dataIndex: "distinct_tickets",
                      width: 90, align: "right",
                    },
                  ]}
                />
              ),
            },
            {
              key: "expensive",
              label: `Самые дорогие на тикет (${d.most_expensive.length})`,
              children: (
                <Table
                  size="small" rowKey="queue" pagination={false}
                  dataSource={d.most_expensive}
                  columns={[
                    { title: "Очередь", dataIndex: "queue" },
                    { title: "Тикетов", dataIndex: "tickets", width: 90, align: "right" },
                    {
                      title: "Часов всего", dataIndex: "total_wall_hours",
                      width: 130, align: "right",
                      render: (v: number) => <span className="num">{v?.toLocaleString("ru-RU")}</span>,
                    },
                    {
                      title: "Стоимость/тикет (ч)", dataIndex: "cost_per_ticket_hours",
                      width: 170, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 60 ? "red" : v >= 30 ? "orange" : "default"}>
                          {v?.toFixed(1)}
                        </Tag>
                      ),
                    },
                  ]}
                />
              ),
            },
            {
              key: "parking",
              label: `Parking lots (${d.parking_lots.length})`,
              children: (
                <Table
                  size="small" rowKey="queue" pagination={false}
                  dataSource={d.parking_lots}
                  columns={[
                    { title: "Очередь", dataIndex: "queue" },
                    {
                      title: "Часов без владельца", dataIndex: "no_owner_hours",
                      width: 170, align: "right",
                      render: (v: number) => <span className="num">{v?.toLocaleString("ru-RU")}</span>,
                    },
                    {
                      title: "% без владельца", dataIndex: "no_owner_pct",
                      width: 140, align: "right",
                      render: (v: number) => (
                        <Tag color={v >= 90 ? "red" : v >= 60 ? "orange" : "default"}>
                          {v?.toFixed(0)}%
                        </Tag>
                      ),
                    },
                    {
                      title: "Тикетов", dataIndex: "distinct_tickets",
                      width: 90, align: "right",
                    },
                  ]}
                />
              ),
            },
            {
              key: "dying",
              label: `Тикеты в зоне риска (${d.dying_in_queue.length})`,
              children: (
                <Table
                  size="small" rowKey="ticket_id" pagination={false}
                  dataSource={d.dying_in_queue}
                  columns={[
                    { title: "№", dataIndex: "ticket_number", width: 170, render: (v) => <span className="mono">{v}</span> },
                    { title: "Очередь", dataIndex: "current_queue" },
                    { title: "Состояние", dataIndex: "current_state", width: 130 },
                    { title: "Владелец", dataIndex: "current_owner", width: 160, render: (v) => v ?? <Tag color="red">нет</Tag> },
                    {
                      title: "Часов всего", dataIndex: "total_wall_hours",
                      width: 130, align: "right",
                      render: (v: number) => <span className="num">{v?.toLocaleString("ru-RU")}</span>,
                    },
                    { title: "Очередей пройдено", dataIndex: "queues_visited", width: 160, align: "right" },
                    { title: "Сегментов", dataIndex: "segments", width: 100, align: "right" },
                  ]}
                />
              ),
            },
          ]}
        />
      </div>
    </div>
  );
}
