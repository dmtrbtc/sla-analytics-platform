import { useEffect, useState } from "react";
import { Typography, Button, Space, Table, Tag, message, Tooltip } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined, EyeOutlined, ReloadOutlined, SyncOutlined, UploadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { importsApi, ImportSession } from "../api/imports";
import { IMPORT_STATUS_COLORS } from "../utils/constants";

export default function Imports() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ImportSession[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const resp = await importsApi.list();
      setSessions(resp.data);
    } catch {
      message.error(t("imports.failedToLoad"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async (id: string) => {
    try {
      await importsApi.start(id);
      message.success(t("imports.pipelineStarted"));
      fetchSessions();
    } catch {
      message.error(t("imports.failedToStart"));
    }
  };

  const handleReprocess = async (id: string) => {
    try {
      await importsApi.reprocess(id);
      message.success(t("imports.reprocessingStarted"));
      fetchSessions();
    } catch {
      message.error(t("imports.failedToReprocess"));
    }
  };

  const columns = [
    {
      title: t("imports.columns.status"),
      dataIndex: "status",
      key: "status",
      render: (status: string) => {
        const statusLabels: Record<string, string> = {
          draft: t("imports.status.draft"),
          validating: t("imports.status.validating"),
          processing: t("imports.status.processing"),
          completed: t("imports.status.completed"),
          failed: t("imports.status.failed"),
        };
        return (
          <Tag icon={status === "completed" ? <CheckCircleOutlined /> : status === "failed" ? <CloseCircleOutlined /> : <SyncOutlined spin />} color={IMPORT_STATUS_COLORS[status] || "default"}>
            {statusLabels[status] || status}
          </Tag>
        );
      },
    },
    {
      title: t("imports.columns.backlog"),
      key: "backlog",
      render: (_: unknown, record: ImportSession) => record.backlog_file || "-",
    },
    {
      title: t("imports.columns.history"),
      key: "history",
      render: (_: unknown, record: ImportSession) => record.history_file || "-",
    },
    {
      title: t("imports.columns.events"),
      key: "events",
      render: (_: unknown, record: ImportSession) => (record.stats as any)?.events_parsed ?? "-",
    },
    {
      title: t("imports.columns.tickets"),
      key: "tickets",
      render: (_: unknown, record: ImportSession) => (record.stats as any)?.tickets ?? "-",
    },
    {
      title: t("imports.columns.errors"),
      key: "errors",
      render: (_: unknown, record: ImportSession) => record.error_details?.length ?? 0,
    },
    {
      title: t("imports.columns.created"),
      dataIndex: "created_at",
      key: "created_at",
      render: (d: string) => new Date(d).toLocaleString(),
    },
    {
      title: t("common.actions"),
      key: "actions",
      render: (_: unknown, record: ImportSession) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/imports/${record.id}`)}>
            {t("common.view")}
          </Button>
          {record.status === "draft" || record.status === "validating" ? (
            <Button size="small" type="primary" onClick={() => handleStart(record.id)}>
              {t("common.start")}
            </Button>
          ) : null}
          {record.status === "failed" || record.status === "completed" ? (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => handleReprocess(record.id)}>
              {t("common.reprocess")}
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4}>{t("imports.title")}</Typography.Title>
        <Space>
          <Button onClick={fetchSessions} loading={loading}>{t("imports.refresh")}</Button>
          <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate("/imports/new")}>
            {t("imports.newImport")}
          </Button>
        </Space>
      </div>
      <Table
        dataSource={sessions}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
}
