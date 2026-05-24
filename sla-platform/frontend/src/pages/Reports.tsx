import { useState, useEffect, useCallback } from "react";
import { Typography, Select, Button, Table, Tag, message, Spin, Space, Alert, Tabs } from "antd";
import { DownloadOutlined, FileExcelOutlined, ReloadOutlined, StarOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "../api/reports";
import { useTimeScope } from "../contexts/TimeScopeContext";
import { palette } from "../design/colors";
import { typography } from "../design/typography";
import { cardStyle, sectionTitle } from "../design/tokens";

const REPORT_PRESETS = [
  { key: "sla_breaches", labelKey: "reports.types.slaBreaches", icon: "📊" },
  { key: "team_performance", labelKey: "reports.types.teamPerformance", icon: "👥" },
  { key: "ticket_lifecycle", labelKey: "reports.types.ticketLifecycle", icon: "🔄" },
  { key: "imports_summary", labelKey: "reports.types.importsSummary", icon: "📥" },
  { key: "executive", labelKey: "reports.types.executive", icon: "📈" },
];

export default function Reports() {
  const { t } = useTranslation();
  const { toParams, label: scopeLabel } = useTimeScope();
  const [reportType, setReportType] = useState("sla_breaches");
  const [format, setFormat] = useState("xlsx");
  const [generating, setGenerating] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const { data: reportsData, isLoading: listLoading, refetch: refetchList } = useQuery({
    queryKey: ["reports-list"],
    queryFn: async () => (await reportsApi.list()).data.reports,
  });

  const pollStatus = useCallback(async (taskId: string) => {
    for (let i = 0; i < 30; i++) {
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
      } catch { /* retry */ }
      await new Promise((r) => setTimeout(r, 2000));
    }
    message.warning(t("reports.reportTakingLonger"));
    setGenerating(false);
    setActiveTaskId(null);
  }, [refetchList]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      // Pass the global TimeScope into the report job so the XLSX/CSV
      // covers EXACTLY the window the analyst selected (1д/7д/30д/90д
      // /custom). Without scope the worker generates an all-time report.
      const resp = await reportsApi.generate(
        { report_type: reportType, fmt: format },
        toParams(),
      );
      setActiveTaskId(resp.data.task_id);
      message.info(t("reports.reportStarted"));
      pollStatus(resp.data.task_id);
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
    } catch { message.error(t("reports.failedToDownload")); }
  };

  const reportsColumns = [
    { title: t("reports.columns.filename"), dataIndex: "filename", key: "filename", render: (v: string) => <span style={{ color: palette.text.primary }}>{v}</span> },
    { title: t("reports.columns.size"), dataIndex: "size_bytes", key: "size_bytes", render: (v: number) => <span style={{ color: palette.text.secondary, fontFamily: typography.fontMono, fontSize: 12 }}>{v > 1024 * 1024 ? `${(v / 1024 / 1024).toFixed(1)} MB` : `${(v / 1024).toFixed(1)} KB`}</span> },
    { title: t("reports.columns.modified"), dataIndex: "modified", key: "modified", render: (v: number) => <span style={{ color: palette.text.tertiary, fontSize: 12 }}>{new Date(v * 1000).toLocaleString()}</span> },
    { title: t("reports.columns.action"), key: "action", render: (_: any, record: any) => (
      <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(record.filename)} style={{ fontSize: 12 }}>{t("common.download")}</Button>
    )},
  ];

  return (
    <div style={{ padding: "0 0 32px" }}>
      <div style={{ marginBottom: 20 }}>
        <Typography.Title level={4} style={{ margin: 0, fontFamily: typography.fontFamily, fontSize: typography.size["2xl"], fontWeight: 600, letterSpacing: "-0.02em", color: palette.text.primary }}>
          {t("reports.title")}
        </Typography.Title>
        <span style={{ fontFamily: typography.fontFamily, fontSize: typography.size.sm, color: palette.text.tertiary, marginTop: 2, display: "inline-block" }}>
          Генерация и управление отчётами
        </span>
      </div>

      <div style={{ ...cardStyle, marginBottom: 16 }}>
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, ...sectionTitle }}>
          {t("reports.generateReport")}
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            {REPORT_PRESETS.map((p) => (
              <div
                key={p.key}
                onClick={() => setReportType(p.key)}
                style={{
                  padding: "8px 14px",
                  border: `1px solid ${reportType === p.key ? palette.brand[500] : palette.border}`,
                  borderRadius: 8,
                  cursor: "pointer",
                  background: reportType === p.key ? palette.brand[50] : "transparent",
                  transition: "all 0.15s",
                  fontSize: 13,
                  color: reportType === p.key ? palette.brand[700] : palette.text.secondary,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span>{p.icon}</span>
                <span style={{ fontWeight: reportType === p.key ? 600 : 400 }}>{t(p.labelKey)}</span>
              </div>
            ))}
          </div>
          <Space wrap>
            <span style={{ fontSize: 13, color: palette.text.secondary }}>Формат:</span>
            <Select value={format} onChange={setFormat} size="small" style={{ width: 100 }}>
              <Select.Option value="xlsx">XLSX</Select.Option>
              <Select.Option value="csv">CSV</Select.Option>
            </Select>
            <Tag icon={<ClockCircleOutlined />} color="blue">
              Период: {scopeLabel}
            </Tag>
            <Button type="primary" icon={<FileExcelOutlined />} onClick={handleGenerate} loading={generating} style={{ fontSize: 12 }}>
              {t("reports.generate")}
            </Button>
          </Space>
          {generating && (
            <Alert
              message={t("reports.generatingMessage")}
              type="info"
              showIcon
              icon={<Spin size="small" />}
              style={{ marginTop: 12, fontSize: 13 }}
            />
          )}
        </div>
      </div>

      <div style={cardStyle}>
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${palette.borderLight}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={sectionTitle}>{t("reports.generatedReports")}</span>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => refetchList()} loading={listLoading} style={{ fontSize: 11 }}>{t("reports.refresh")}</Button>
        </div>
        <Table
          dataSource={reportsData || []}
          columns={reportsColumns}
          rowKey="filename"
          size="small"
          pagination={{ pageSize: 20, showSizeChanger: false }}
          style={{ fontSize: 13 }}
        />
      </div>
    </div>
  );
}
