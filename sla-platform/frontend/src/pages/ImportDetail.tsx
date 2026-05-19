import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Typography, Card, Descriptions, Tag, Spin, Table, Empty, Button, Space, Progress, Statistic, Row, Col } from "antd";
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, DashboardOutlined, FieldTimeOutlined, DatabaseOutlined, ExperimentOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { importsApi, ImportSession } from "../api/imports";
import { IMPORT_STATUS_COLORS } from "../utils/constants";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const STAGE_LABELS: Record<string, { label: string; pct: number }> = {
  validate: { label: "Валидация", pct: 10 },
  backlog: { label: "Загрузка бэкапа", pct: 25 },
  parse: { label: "Парсинг событий", pct: 40 },
  normalize: { label: "Нормализация", pct: 55 },
  rebuild: { label: "Восстановление", pct: 70 },
  compute_sla: { label: "Расчёт SLA", pct: 85 },
  complete: { label: "Завершение", pct: 100 },
  failed: { label: "Ошибка", pct: 0 },
};

export default function ImportDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: sessionData, isLoading } = useQuery({
    queryKey: ["import-session", id],
    queryFn: async () => {
      const resp = await importsApi.get(id!);
      return resp.data as ImportSession;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d || ["draft", "validating", "parsing", "normalizing", "rebuilding", "computing_sla"].includes((d as ImportSession).status)) return 5000;
      return false;
    },
  });

  const { data: progress } = useQuery({
    queryKey: ["import-progress", id],
    queryFn: async () => {
      const resp = await axios.get(`${API_BASE}/imports/sessions/${id}/progress`);
      return resp.data;
    },
    enabled: !!id,
    refetchInterval: 5000,
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!sessionData) return <Empty description={t("importDetail.notFound")} />;

  const s = sessionData;
  const stats = s.stats as Record<string, any>;
  const p = progress || {};

  const activeStatuses = ["validating", "parsing", "normalizing", "rebuilding", "computing_sla"];
  const isActive = activeStatuses.includes(s.status);

  const currentStage = p.current_stage || s.status;
  const stageInfo = STAGE_LABELS[currentStage] || STAGE_LABELS.validate;
  const progressPct = s.status === "completed" ? 100 : s.status === "failed" ? 0 : (p.progress_pct ?? stageInfo.pct);

  const stepStatus: Record<string, "process" | "finish" | "error" | "wait"> = {
    draft: "process", validating: "process", parsing: "process",
    normalizing: "process", rebuilding: "process", computing_sla: "process",
    completed: "finish", failed: "error",
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/imports")}>{t("importDetail.back")}</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {t("importDetail.title")}
        </Typography.Title>
        <Tag icon={s.status === "completed" ? <CheckCircleOutlined /> : s.status === "failed" ? <CloseCircleOutlined /> : <SyncOutlined spin />} color={IMPORT_STATUS_COLORS[s.status]}>
          {t(`imports.status.${s.status}`, s.status.toUpperCase())}
        </Tag>
      </Space>

      {isActive && (
        <Card size="small" style={{ marginBottom: 16, background: "#fafafa" }}>
          <Progress
            percent={progressPct}
            strokeColor={{ from: "#108ee9", to: "#87d068" }}
            status={s.status === "failed" ? "exception" : "active"}
            format={(pct) => `${pct}%`}
            style={{ marginBottom: 12 }}
          />
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="Текущий этап" value={stageInfo.label} prefix={<SyncOutlined spin />} valueStyle={{ fontSize: 14 }} />
            </Col>
            <Col span={4}>
              <Statistic title="Строк/сек" value={p.rows_per_second ?? "-"} prefix={<DashboardOutlined />} valueStyle={{ fontSize: 14 }} />
            </Col>
            <Col span={4}>
              <Statistic title="ETA" value={p.eta_seconds ? `${Math.round(p.eta_seconds / 60)} мин` : "-"} prefix={<FieldTimeOutlined />} valueStyle={{ fontSize: 14 }} />
            </Col>
            <Col span={4}>
              <Statistic title="Прошло" value={p.elapsed_seconds ? `${Math.round(p.elapsed_seconds / 60)} мин` : "-"} prefix={<ExperimentOutlined />} valueStyle={{ fontSize: 14 }} />
            </Col>
            <Col span={4}>
              <Statistic title="Память" value={p.memory_mb ? `${p.memory_mb} MB` : "-"} prefix={<DatabaseOutlined />} valueStyle={{ fontSize: 14 }} />
            </Col>
            <Col span={2}>
              <Statistic title="Ошибки" value={p.errors ?? 0} valueStyle={{ fontSize: 14, color: (p.errors ?? 0) > 0 ? "red" : undefined }} />
            </Col>
          </Row>
        </Card>
      )}

      <Card title={t("importDetail.sessionInfo")} size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label={t("importDetail.fields.sessionId")}>{s.id}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.status")}><Tag color={IMPORT_STATUS_COLORS[s.status]}>{s.status}</Tag></Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.backlogFile")}>{s.backlog_file || "-"}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.historyFile")}>{s.history_file || "-"}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.backlogRows")}>{s.backlog_rows ?? "-"}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.historyRows")}>{s.history_rows ?? "-"}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.created")}>{s.created_at ? new Date(s.created_at).toLocaleString() : "-"}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.completed")}>{s.completed_at ? new Date(s.completed_at).toLocaleString() : "-"}</Descriptions.Item>
          <Descriptions.Item label={t("importDetail.fields.errorCount")}>{s.error_details?.length ?? 0}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={t("importDetail.pipelineStats")} size="small" style={{ marginBottom: 16 }}>
        {Object.keys(stats).length > 0 ? (
          <Table
            dataSource={Object.entries(stats).filter(([k]) => k !== "step_durations").map(([k, v]) => ({ key: k, metric: k, value: typeof v === "object" ? JSON.stringify(v) : String(v) }))}
            columns={[
              { title: t("importDetail.fields.sessionId"), dataIndex: "metric", key: "metric" },
              { title: t("common.title"), dataIndex: "value", key: "value", ellipsis: true },
            ]}
            rowKey="key"
            size="small"
            pagination={false}
          />
        ) : <Typography.Text type="secondary">{t("importDetail.noStats")}</Typography.Text>}
      </Card>

      {s.error_details && s.error_details.length > 0 && (
        <Card title={t("importDetail.errors")} size="small" style={{ marginBottom: 16 }}>
          <Table
            dataSource={s.error_details as any[]}
            columns={[
              { title: t("importDetail.errorColumns.step"), dataIndex: "step", key: "step", render: (v: string) => <Tag color="error">{v}</Tag> },
              { title: t("importDetail.errorColumns.message"), dataIndex: "message", key: "message" },
              { title: t("importDetail.errorColumns.timestamp"), dataIndex: "timestamp", key: "timestamp", render: (v: string) => new Date(v).toLocaleString() },
            ]}
            rowKey={(r: any) => `${r.step}-${r.timestamp}`}
            size="small"
            pagination={false}
          />
        </Card>
      )}
    </div>
  );
}
