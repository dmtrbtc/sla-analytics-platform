import { useEffect, useState } from "react";
import { Typography, Button, Space, Table, Tag, message } from "antd";
import { UploadOutlined, ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { importsApi, ImportSession } from "../api/imports";

const statusColors: Record<string, string> = {
  draft: "default",
  validating: "processing",
  parsing: "processing",
  normalizing: "processing",
  rebuilding: "processing",
  computing_sla: "processing",
  completed: "success",
  failed: "error",
};

const statusIcons: Record<string, React.ReactNode> = {
  completed: <CheckCircleOutlined />,
  failed: <CloseCircleOutlined />,
  parsing: <SyncOutlined spin />,
  normalizing: <SyncOutlined spin />,
  rebuilding: <SyncOutlined spin />,
  computing_sla: <SyncOutlined spin />,
};

export default function Imports() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ImportSession[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const resp = await importsApi.list();
      setSessions(resp.data);
    } catch {
      message.error("Failed to load sessions");
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
      message.success("Pipeline started");
      fetchSessions();
    } catch {
      message.error("Failed to start pipeline");
    }
  };

  const handleReprocess = async (id: string) => {
    try {
      await importsApi.reprocess(id);
      message.success("Reprocessing started");
      fetchSessions();
    } catch {
      message.error("Failed to reprocess");
    }
  };

  const columns = [
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (status: string) => (
        <Tag icon={statusIcons[status]} color={statusColors[status] || "default"}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: "Backlog",
      key: "backlog",
      render: (_: unknown, record: ImportSession) => record.backlog_file || "-",
    },
    {
      title: "History",
      key: "history",
      render: (_: unknown, record: ImportSession) => record.history_file || "-",
    },
    {
      title: "Events",
      key: "events",
      render: (_: unknown, record: ImportSession) => (record.stats as any)?.events_parsed ?? "-",
    },
    {
      title: "Tickets",
      key: "tickets",
      render: (_: unknown, record: ImportSession) => (record.stats as any)?.tickets ?? "-",
    },
    {
      title: "Errors",
      key: "errors",
      render: (_: unknown, record: ImportSession) => record.error_details?.length ?? 0,
    },
    {
      title: "Created",
      dataIndex: "created_at",
      key: "created_at",
      render: (d: string) => new Date(d).toLocaleString(),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, record: ImportSession) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/imports/${record.id}`)}>
            View
          </Button>
          {record.status === "draft" || record.status === "validating" ? (
            <Button size="small" type="primary" onClick={() => handleStart(record.id)}>
              Start
            </Button>
          ) : null}
          {record.status === "failed" || record.status === "completed" ? (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => handleReprocess(record.id)}>
              Reprocess
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4}>Import Sessions</Typography.Title>
        <Space>
          <Button onClick={fetchSessions} loading={loading}>Refresh</Button>
          <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate("/imports/new")}>
            New Import
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
