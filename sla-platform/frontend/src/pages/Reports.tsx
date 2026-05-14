import { useState, useEffect, useCallback } from "react";
import { Typography, Card, Select, Button, Table, Tag, message, Spin, Space, Alert } from "antd";
import { DownloadOutlined, FileExcelOutlined, ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "../api/reports";

export default function Reports() {
  const [reportType, setReportType] = useState("sla_breaches");
  const [format, setFormat] = useState("xlsx");
  const [generating, setGenerating] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const { data: reportsData, isLoading: listLoading, refetch: refetchList } = useQuery({
    queryKey: ["reports-list"],
    queryFn: async () => {
      const resp = await reportsApi.list();
      return resp.data.reports;
    },
  });

  const pollStatus = useCallback(async (taskId: string) => {
    const maxAttempts = 30;
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const resp = await reportsApi.status(taskId);
        const status = resp.data.status;
        if (status === "completed") {
          message.success("Report generated successfully");
          setGenerating(false);
          setActiveTaskId(null);
          refetchList();
          return;
        }
        if (status === "failed") {
          message.error("Report generation failed");
          setGenerating(false);
          setActiveTaskId(null);
          return;
        }
      } catch {
        // continue polling
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    message.warning("Report generation is taking longer than expected");
    setGenerating(false);
    setActiveTaskId(null);
  }, [refetchList]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const resp = await reportsApi.generate({ report_type: reportType, fmt: format });
      const taskId = resp.data.task_id;
      setActiveTaskId(taskId);
      message.info("Report generation started");
      pollStatus(taskId);
    } catch {
      message.error("Failed to start report generation");
      setGenerating(false);
    }
  };

  const handleDownload = async (filename: string) => {
    try {
      const resp = await reportsApi.download(filename);
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error("Failed to download report");
    }
  };

  const reportsColumns = [
    { title: "Filename", dataIndex: "filename", key: "filename" },
    {
      title: "Size", dataIndex: "size_bytes", key: "size_bytes",
      render: (v: number) => v > 1024 * 1024 ? `${(v / 1024 / 1024).toFixed(1)} MB` : `${(v / 1024).toFixed(1)} KB`,
    },
    {
      title: "Modified", dataIndex: "modified", key: "modified",
      render: (v: number) => new Date(v * 1000).toLocaleString(),
    },
    {
      title: "Action", key: "action",
      render: (_: any, record: any) => (
        <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(record.filename)}>
          Download
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>Reports</Typography.Title>

      <Card title="Generate Report" size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Space wrap>
            <Select value={reportType} onChange={setReportType} style={{ width: 250 }}>
              <Select.Option value="sla_breaches">SLA Breaches</Select.Option>
              <Select.Option value="team_performance">Team Performance</Select.Option>
              <Select.Option value="ticket_lifecycle">Ticket Lifecycle</Select.Option>
              <Select.Option value="imports_summary">Imports Summary</Select.Option>
            </Select>
            <Select value={format} onChange={setFormat} style={{ width: 100 }}>
              <Select.Option value="xlsx">XLSX</Select.Option>
              <Select.Option value="csv">CSV</Select.Option>
            </Select>
            <Button type="primary" icon={<FileExcelOutlined />} onClick={handleGenerate} loading={generating}>
              Generate
            </Button>
          </Space>
          {generating && (
            <Alert
              message="Report is being generated in the background. Please wait..."
              type="info"
              showIcon
              icon={<Spin size="small" />}
            />
          )}
        </Space>
      </Card>

      <Card
        title="Generated Reports"
        size="small"
        extra={<Button icon={<ReloadOutlined />} onClick={() => refetchList()} loading={listLoading}>Refresh</Button>}
      >
        <Table
          dataSource={reportsData || []}
          columns={reportsColumns}
          rowKey="filename"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
}
