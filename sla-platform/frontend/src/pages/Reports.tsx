import { useState, useEffect, useCallback } from "react";
import { Typography, Card, Select, Button, Table, Tag, message, Spin, Space, Alert } from "antd";
import { DownloadOutlined, FileExcelOutlined, ReloadOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "../api/reports";

export default function Reports() {
  const { t } = useTranslation();
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
          message.success(t("reports.reportGenerated"));
          setGenerating(false);
          setActiveTaskId(null);
          refetchList();
          return;
        }
        if (status === "failed") {
          message.error(t("reports.reportFailed"));
          setGenerating(false);
          setActiveTaskId(null);
          return;
        }
      } catch {
        // continue polling
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    message.warning(t("reports.reportTakingLonger"));
    setGenerating(false);
    setActiveTaskId(null);
  }, [refetchList]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const resp = await reportsApi.generate({ report_type: reportType, fmt: format });
      const taskId = resp.data.task_id;
      setActiveTaskId(taskId);
      message.info(t("reports.reportStarted"));
      pollStatus(taskId);
    } catch {
      message.error(t("reports.failedToStart"));
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
      message.error(t("reports.failedToDownload"));
    }
  };

  const reportsColumns = [
    { title: t("reports.columns.filename"), dataIndex: "filename", key: "filename" },
    {
      title: t("reports.columns.size"), dataIndex: "size_bytes", key: "size_bytes",
      render: (v: number) => v > 1024 * 1024 ? `${(v / 1024 / 1024).toFixed(1)} MB` : `${(v / 1024).toFixed(1)} KB`,
    },
    {
      title: t("reports.columns.modified"), dataIndex: "modified", key: "modified",
      render: (v: number) => new Date(v * 1000).toLocaleString(),
    },
    {
      title: t("reports.columns.action"), key: "action",
      render: (_: any, record: any) => (
        <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(record.filename)}>
          {t("common.download")}
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>{t("reports.title")}</Typography.Title>

      <Card title={t("reports.generateReport")} size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Space wrap>
            <Select value={reportType} onChange={setReportType} style={{ width: 250 }}>
              <Select.Option value="sla_breaches">{t("reports.types.slaBreaches")}</Select.Option>
              <Select.Option value="team_performance">{t("reports.types.teamPerformance")}</Select.Option>
              <Select.Option value="ticket_lifecycle">{t("reports.types.ticketLifecycle")}</Select.Option>
              <Select.Option value="imports_summary">{t("reports.types.importsSummary")}</Select.Option>
            </Select>
            <Select value={format} onChange={setFormat} style={{ width: 100 }}>
              <Select.Option value="xlsx">XLSX</Select.Option>
              <Select.Option value="csv">CSV</Select.Option>
            </Select>
            <Button type="primary" icon={<FileExcelOutlined />} onClick={handleGenerate} loading={generating}>
              {t("reports.generate")}
            </Button>
          </Space>
          {generating && (
            <Alert
              message={t("reports.generatingMessage")}
              type="info"
              showIcon
              icon={<Spin size="small" />}
            />
          )}
        </Space>
      </Card>

      <Card
        title={t("reports.generatedReports")}
        size="small"
        extra={<Button icon={<ReloadOutlined />} onClick={() => refetchList()} loading={listLoading}>{t("reports.refresh")}</Button>}
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
