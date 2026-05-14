import { useParams, useNavigate } from "react-router-dom";
import { Typography, Card, Descriptions, Tag, Spin, Table, Timeline, Empty, Button, Space, Steps } from "antd";
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { importsApi, ImportSession } from "../api/imports";

export default function ImportDetail() {
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
  if (!sessionData) return <Empty description="Session not found" />;

  const s = sessionData;
  const stats = s.stats as Record<string, any>;

  const statusColors: Record<string, string> = {
    draft: "default", validating: "processing", parsing: "processing",
    normalizing: "processing", rebuilding: "processing", computing_sla: "processing",
    completed: "success", failed: "error",
  };

  const stepStatus: Record<string, "process" | "finish" | "error" | "wait"> = {
    draft: "process", validating: "process", parsing: "process",
    normalizing: "process", rebuilding: "process", computing_sla: "process",
    completed: "finish", failed: "error",
  };

  const pipelineSteps = [
    { title: "Validate", status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "validate") ? "error" : "finish") : "finish" },
    { title: "Backlog", status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "backlog") ? "error" : "finish") : "finish" },
    { title: "Parse", status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "parse") ? "error" : "finish") : "finish" },
    { title: "Normalize", status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "normalize") ? "error" : "finish") : "finish" },
    { title: "Rebuild", status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "rebuild") ? "error" : "finish") : "finish" },
    { title: "SLA", status: s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "compute_sla") ? "error" : "finish") : "finish" },
    { title: "Complete", status: s.status === "completed" ? "finish" : (s.status === "failed" ? (s.error_details?.some((e: any) => e.step === "complete") ? "error" : "wait") : "process") },
  ];

  const statsEntries = Object.entries(stats).filter(([k]) => !["step_durations"].includes(k));

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/imports")}>Back</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Import Session Details
        </Typography.Title>
        <Tag icon={s.status === "completed" ? <CheckCircleOutlined /> : s.status === "failed" ? <CloseCircleOutlined /> : <SyncOutlined spin />} color={statusColors[s.status]}>
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

      <Card title="Session Info" size="small" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label="Session ID">{s.id}</Descriptions.Item>
          <Descriptions.Item label="Status"><Tag color={statusColors[s.status]}>{s.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="Backlog File">{s.backlog_file || "-"}</Descriptions.Item>
          <Descriptions.Item label="History File">{s.history_file || "-"}</Descriptions.Item>
          <Descriptions.Item label="Backlog Rows">{s.backlog_rows ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="History Rows">{s.history_rows ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="Created">{s.created_at ? new Date(s.created_at).toLocaleString() : "-"}</Descriptions.Item>
          <Descriptions.Item label="Completed">{s.completed_at ? new Date(s.completed_at).toLocaleString() : "-"}</Descriptions.Item>
          <Descriptions.Item label="Error Count">{s.error_details?.length ?? 0}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Pipeline Stats" size="small" style={{ marginBottom: 16 }}>
        {statsEntries.length > 0 ? (
          <Table
            dataSource={statsEntries.map(([k, v]) => ({ key: k, metric: k, value: typeof v === "object" ? JSON.stringify(v) : String(v) }))}
            columns={[
              { title: "Metric", dataIndex: "metric", key: "metric" },
              { title: "Value", dataIndex: "value", key: "value", ellipsis: true },
            ]}
            rowKey="key"
            size="small"
            pagination={false}
          />
        ) : <Typography.Text type="secondary">No stats available</Typography.Text>}
      </Card>

      {s.error_details && s.error_details.length > 0 && (
        <Card title="Errors" size="small" style={{ marginBottom: 16 }}>
          <Table
            dataSource={s.error_details as any[]}
            columns={[
              { title: "Step", dataIndex: "step", key: "step", render: (v: string) => <Tag color="error">{v}</Tag> },
              { title: "Message", dataIndex: "message", key: "message" },
              { title: "Timestamp", dataIndex: "timestamp", key: "timestamp", render: (v: string) => new Date(v).toLocaleString() },
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
