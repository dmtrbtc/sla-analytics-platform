import { useState } from "react";
import {
  Typography, Card, Table, Tag, Button, Space, Modal, Input, Timeline, message, Badge, Alert, Row, Col, Statistic, Tooltip,
} from "antd";
import {
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  FireOutlined, MessageOutlined, ReloadOutlined, EyeOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { incidentsApi, Incident } from "../api/incidents";
import { aiApi } from "../api/ai";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "red", high: "orange", medium: "gold", low: "green",
};

const STATUS_COLORS: Record<string, string> = {
  active: "red", acknowledged: "orange", resolved: "green",
};

const INCIDENT_TYPE_LABELS: Record<string, string> = {
  breach_spike: "Всплеск нарушений SLA",
  queue_overload: "Перегрузка очереди",
  high_reassignments: "Аномальные переназначения",
  stalled_queue: "Зависшие тикеты",
  import_failures: "Сбои импорта",
  high_risk: "Накопление рисков",
  worker_down: "Отказ воркера",
};

export default function OperationsIncidents() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>("active");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [commentText, setCommentText] = useState("");
  const [resolveNote, setResolveNote] = useState("");

  const { data: incidentsData, isLoading } = useQuery({
    queryKey: ["incidents", filter],
    queryFn: async () => {
      const resp = await incidentsApi.list({ status: filter === "all" ? undefined : filter });
      return resp.data.incidents || [];
    },
    refetchInterval: 30000,
  });

  const { data: anomaliesData } = useQuery({
    queryKey: ["ai-anomalies"],
    queryFn: async () => {
      const resp = await aiApi.anomalies(1);
      return resp.data.anomalies || [];
    },
    refetchInterval: 60000,
  });

  const { data: hintsData } = useQuery({
    queryKey: ["ai-hints"],
    queryFn: async () => {
      const resp = await aiApi.hints(1);
      return resp.data.hints || [];
    },
    refetchInterval: 120000,
  });

  const { data: detailData } = useQuery({
    queryKey: ["incident-detail", detailId],
    queryFn: async () => {
      if (!detailId) return null;
      const resp = await incidentsApi.get(detailId);
      return resp.data;
    },
    enabled: !!detailId,
  });

  const acknowledgeMut = useMutation({
    mutationFn: (id: string) => incidentsApi.acknowledge(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["incidents"] }); message.success("Инцидент принят"); },
  });

  const resolveMut = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) => incidentsApi.resolve(id, { resolution: note }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["incidents"] }); message.success("Инцидент разрешён"); setResolveNote(""); },
  });

  const commentMut = useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) => incidentsApi.addComment(id, { text, author: "Оператор" }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["incident-detail"] }); setCommentText(""); },
  });

  const incidents: Incident[] = incidentsData || [];
  const anomalies = anomaliesData || [];
  const hints = hintsData || [];
  const activeCritical = incidents.filter((i) => i.status === "active" && i.severity === "critical").length;

  const columns = [
    {
      title: "Важность", dataIndex: "severity", key: "severity", width: 90,
      render: (v: string) => <Tag color={SEVERITY_COLORS[v] || "default"}>{v === "critical" ? "Критичный" : v === "high" ? "Высокий" : v === "medium" ? "Средний" : "Низкий"}</Tag>,
    },
    { title: "Тип", dataIndex: "type", key: "type", width: 160, render: (v: string) => INCIDENT_TYPE_LABELS[v] || v },
    { title: "Описание", dataIndex: "summary", key: "summary", ellipsis: true },
    { title: "Очередь", dataIndex: "queue", key: "queue", width: 180, render: (v: string) => v || "—" },
    {
      title: "Статус", dataIndex: "status", key: "status", width: 110,
      render: (v: string) => <Tag color={STATUS_COLORS[v] || "default"}>{v === "active" ? "Активен" : v === "acknowledged" ? "Принят" : "Решён"}</Tag>,
    },
    {
      title: "Создан", dataIndex: "created_at", key: "created_at", width: 160,
      render: (v: string) => v ? new Date(v).toLocaleString("ru") : "—",
    },
    {
      title: "", key: "actions", width: 200,
      render: (_: any, r: Incident) => (
        <Space size="small">
          <Tooltip title="Просмотр"><Button size="small" icon={<EyeOutlined />} onClick={() => setDetailId(r.id)} /></Tooltip>
          {r.status === "active" && (
            <Tooltip title="Принять"><Button size="small" icon={<CheckCircleOutlined />} onClick={() => acknowledgeMut.mutate(r.id)} /></Tooltip>
          )}
          {r.status !== "resolved" && (
            <Tooltip title="Разрешить"><Button size="small" icon={<FireOutlined />} onClick={() => {
              const note = prompt("Причина разрешения:");
              if (note) resolveMut.mutate({ id: r.id, note });
            }} /></Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "center" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          <Badge count={activeCritical} offset={[8, 0]}>
            <span>Операционные инциденты</span>
          </Badge>
        </Typography.Title>
        <Space>
          <Button onClick={() => queryClient.invalidateQueries({ queryKey: ["incidents"] })} icon={<ReloadOutlined />}>{t("common.refresh")}</Button>
          <Button.Group>
            {["active", "acknowledged", "resolved", "all"].map((f) => (
              <Button key={f} type={filter === f ? "primary" : "default"} size="small" onClick={() => setFilter(f)}>
                {f === "active" ? "Активные" : f === "acknowledged" ? "Принятые" : f === "resolved" ? "Решённые" : "Все"}
              </Button>
            ))}
          </Button.Group>
        </Space>
      </div>

      {activeCritical > 0 && (
        <Alert
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
          message={`${activeCritical} критических инцидентов требуют внимания`}
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={6}>
          <Card size="small"><Statistic title="Активные инциденты" value={incidents.filter((i) => i.status === "active").length} valueStyle={{ color: "#ff4d4f" }} prefix={<WarningOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small"><Statistic title="Критические" value={activeCritical} valueStyle={{ color: "#ff4d4f" }} prefix={<FireOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small"><Statistic title="Аномалий (24ч)" value={anomalies.length} valueStyle={{ color: "#faad14" }} prefix={<ExclamationCircleOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small"><Statistic title="Операционных подсказок" value={hints.length} valueStyle={{ color: "#1677ff" }} prefix={<MessageOutlined />} /></Card>
        </Col>
      </Row>

      <Card size="small">
        <Table
          dataSource={incidents.filter((i) => filter === "all" || i.status === filter)}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={`Инцидент: ${detailData?.incident?.title || ""}`}
        open={!!detailId}
        onCancel={() => { setDetailId(null); setCommentText(""); }}
        footer={null}
        width={600}
      >
        {detailData && (
          <div>
            <Card size="small" style={{ marginBottom: 12 }}>
              <Space direction="vertical" style={{ width: "100%" }}>
                <Typography.Text strong>Тип: {INCIDENT_TYPE_LABELS[detailData.incident.type] || detailData.incident.type}</Typography.Text>
                <Typography.Text>Важность: <Tag color={SEVERITY_COLORS[detailData.incident.severity]}>{detailData.incident.severity}</Tag></Typography.Text>
                <Typography.Text>Статус: <Tag color={STATUS_COLORS[detailData.incident.status]}>{detailData.incident.status}</Tag></Typography.Text>
                <Typography.Text>Описание: {detailData.incident.summary}</Typography.Text>
                <Typography.Text>Очередь: {detailData.incident.queue || "—"}</Typography.Text>
                <Typography.Text>Источник: {detailData.incident.source}</Typography.Text>
                <Typography.Text>Создан: {new Date(detailData.incident.created_at).toLocaleString("ru")}</Typography.Text>
                {detailData.incident.resolved_at && (
                  <Typography.Text>Разрешён: {new Date(detailData.incident.resolved_at).toLocaleString("ru")}</Typography.Text>
                )}
                {detailData.incident.resolution && (
                  <Typography.Text>Причина: {detailData.incident.resolution}</Typography.Text>
                )}
              </Space>
            </Card>

            {detailData.comments?.length > 0 && (
              <Card title="Хронология" size="small" style={{ marginBottom: 12 }}>
                <Timeline items={detailData.comments.map((c: any) => ({
                  children: <><Typography.Text strong>{c.author}</Typography.Text>: {c.text}<br /><Typography.Text type="secondary" style={{ fontSize: 11 }}>{new Date(c.created_at).toLocaleString("ru")}</Typography.Text></>,
                }))} />
              </Card>
            )}

            <Space>
              <Input.TextArea
                placeholder="Добавить комментарий..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                style={{ width: 400 }}
                rows={2}
              />
              <Button
                type="primary"
                disabled={!commentText}
                onClick={() => detailId && commentMut.mutate({ id: detailId, text: commentText })}
              >
                Отправить
              </Button>
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
}
