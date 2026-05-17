import { useParams, useNavigate } from "react-router-dom";
import { Typography, Card, Descriptions, Tag, Spin, Table, Empty, Button, Space, Steps } from "antd";
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { importsApi, ImportSession } from "../api/imports";
import { IMPORT_STATUS_COLORS } from "../utils/constants";

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
      if (!d || ["draft", "validating", "parsing", "normalizing", "rebuilding", "computing_sla"].includes((d as ImportSession).status)) {
        return 5000;
      }
      return false;
    },
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!sessionData) return <Empty description={t("importDetail.notFound")} />;

  const s = sessionData;
  const stats = s.stats as Record<string, any>;

  const stepStatus: Record<string, "process" | "finish" | "error" | "wait"> = {
    draft: "process", validating: "process", parsing: "process",
    normalizing: "process", rebuilding: "process", computing_sla: "process",
    completed: "finish", failed: "error",
  };

  const pipelineSteps = [
    { title: t("importDetail.pipeline.validate"), status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "validate") ? "error" : "finish") : "finish" },
    { title: t("importDetail.pipeline.backlog"), status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "backlog") ? "error" : "finish") : "finish" },
    { title: t("importDetail.pipeline.parse"), status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "parse") ? "error" : "finish") : "finish" },
    { title: t("importDetail.pipeline.normalize"), status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "normalize") ? "error" : "finish") : "finish" },
    { title: t("importDetail.pipeline.rebuild"), status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "rebuild") ? "error" : "finish") : "finish" },
    { title: t("importDetail.pipeline.sla"), status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "compute_sla") ? "error" : "finish") : "finish" },
    { title: t("importDetail.pipeline.complete"), status: s.status === "completed" ? "finish" : (s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "complete") ? "error" : "wait") : "process") },
  ];

  const statsEntries = Object.entries(stats).filter(([k]) => !["step_durations"].includes(k));

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/imports")}>{t("importDetail.back")}</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {t("importDetail.title")}
        </Typography.Title>
        <Tag icon={s.status === "completed" ? <CheckCircleOutlined /> : s.status === "failed" ? <CloseCircleOutlined /> : <SyncOutlined spin />} color={IMPORT_STATUS_COLORS[s.status]}>
          {s.status.toUpperCase()}
        </Tag>
      </Space>

      <Steps
        current={pipelineSteps.findIndex((ps) => ps.status === "process")}
        status={s.status === "failed" ? "error" : "process"}
        items={pipelineSteps.map((ps) => ({ title: ps.title, status: ps.status as any }))}
        style={{ marginBottom: 24 }}
        size="small"
      />

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
        {statsEntries.length > 0 ? (
          <Table
            dataSource={statsEntries.map(([k, v]) => ({ key: k, metric: k, value: typeof v === "object" ? JSON.stringify(v) : String(v) }))}
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
