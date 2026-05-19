import { useParams, useNavigate } from "react-router-dom";
import { Typography, Card, Descriptions, Table, Tag, Timeline, Tabs, Space, Button, Empty, Spin } from "antd";
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { ticketsApi } from "../api/tickets";
import { formatDuration } from "../utils/format";
import SLAExplainer from "../components/sla/SLAExplainer";

export default function TicketDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const ticketId = Number(id);

  const { data: ticketData, isLoading: ticketLoading } = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: async () => {
      const resp = await ticketsApi.get(ticketId);
      return resp.data;
    },
    enabled: !!ticketId,
  });

  const { data: timelineData } = useQuery({
    queryKey: ["ticket-timeline", ticketId],
    queryFn: async () => {
      const resp = await ticketsApi.timeline(ticketId);
      return resp.data.events;
    },
    enabled: !!ticketId,
  });

  const { data: ownershipData } = useQuery({
    queryKey: ["ticket-ownership", ticketId],
    queryFn: async () => {
      const resp = await ticketsApi.ownership(ticketId);
      return resp.data.ownership_periods;
    },
    enabled: !!ticketId,
  });

  const { data: queuePeriodsData } = useQuery({
    queryKey: ["ticket-queue-periods", ticketId],
    queryFn: async () => {
      const resp = await ticketsApi.queuePeriods(ticketId);
      return resp.data.queue_periods;
    },
    enabled: !!ticketId,
  });

  const { data: slaData } = useQuery({
    queryKey: ["ticket-sla", ticketId],
    queryFn: async () => {
      const resp = await ticketsApi.sla(ticketId);
      return resp.data.sla_metrics;
    },
    enabled: !!ticketId,
  });

  if (ticketLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!ticketData) return <Empty description={t("ticketDetail.notFound")} />;

  const ticket = ticketData;

  const slaColumns = [
    { title: t("ticketDetail.slaColumns.metric"), dataIndex: "metric_name", key: "metric_name" },
    {
      title: t("ticketDetail.slaColumns.value"), dataIndex: "metric_seconds", key: "metric_seconds",
      render: (v: number) => formatDuration(v),
    },
    {
      title: t("ticketDetail.slaColumns.breached"), dataIndex: "sla_breached", key: "sla_breached",
      render: (v: boolean) => v
        ? <Tag icon={<CloseCircleOutlined />} color="error">{t("common.yes")}</Tag>
        : <Tag icon={<CheckCircleOutlined />} color="success">{t("common.no")}</Tag>,
    },
    { title: t("ticketDetail.slaColumns.queue"), dataIndex: "queue_name", key: "queue_name" },
    { title: t("ticketDetail.slaColumns.owner"), dataIndex: "owner", key: "owner" },
    { title: t("ticketDetail.slaColumns.confidence"), dataIndex: "confidence", key: "confidence" },
  ];

  const timelineItems = (timelineData || []).map((e: any) => ({
    color: e.event_type === "StateUpdate" ? "blue" : e.event_type === "Move" ? "orange" : e.event_type === "OwnerUpdate" ? "green" : "gray",
    children: (
      <div>
        <div style={{ fontWeight: 500 }}>{e.event_type}</div>
        <div style={{ fontSize: 12, color: "#888" }}>{new Date(e.event_time).toLocaleString()}</div>
        <div style={{ fontSize: 13 }}>
          {e.src_queue && e.dest_queue && `${e.src_queue} → ${e.dest_queue}`}
          {e.old_owner && e.new_owner && ` ${e.old_owner} → ${e.new_owner}`}
          {e.old_state && e.new_state && ` ${e.old_state} → ${e.new_state}`}
          {e.queue_name && ` Queue: ${e.queue_name}`}
          {e.state_name && ` State: ${e.state_name}`}
          {e.owner_name && ` Owner: ${e.owner_name}`}
        </div>
      </div>
    ),
  }));

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tickets")}>{t("ticketDetail.back")}</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {t("ticketDetail.fields.ticketNumber")} #{ticket.ticket_number || ticket.ticket_id}
        </Typography.Title>
        <Tag>{ticket.confidence}</Tag>
        {ticket.is_closed ? <Tag color="green">{t("ticketDetail.closed")}</Tag> : <Tag color="blue">{t("ticketDetail.open")}</Tag>}
      </Space>

      <Tabs defaultActiveKey="overview" items={[
        {
          key: "overview",
          label: t("ticketDetail.overview"),
          children: (
            <Card size="small">
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label={t("ticketDetail.fields.ticketId")}>{ticket.ticket_id}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.ticketNumber")}>{ticket.ticket_number || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.title")} span={2}>{ticket.title || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.queue")}>{ticket.current_queue || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.state")}>{ticket.current_state || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.owner")}>{ticket.current_owner || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.customer")}>{ticket.customer_id || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.created")}>{ticket.created_at ? new Date(ticket.created_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.updated")}>{ticket.updated_at ? new Date(ticket.updated_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.firstResponse")}>{ticket.first_response_at ? new Date(ticket.first_response_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.resolution")}>{ticket.resolution_at ? new Date(ticket.resolution_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.confidence")}>{ticket.confidence || "-"}</Descriptions.Item>
                <Descriptions.Item label={t("ticketDetail.fields.isMerged")}>{ticket.is_merged ? t("common.yes") : t("common.no")}</Descriptions.Item>
              </Descriptions>
            </Card>
          ),
        },
        {
          key: "timeline",
          label: t("ticketDetail.eventTimeline"),
          children: timelineItems.length > 0
            ? <Timeline items={timelineItems} style={{ maxHeight: 500, overflow: "auto" }} />
            : <Empty description={t("common.noEvents")} />,
        },
        {
          key: "ownership",
          label: t("ticketDetail.ownershipPeriods"),
          children: (
            <Table
              dataSource={ownershipData || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: t("ticketDetail.ownershipColumns.owner"), dataIndex: "owner", key: "owner" },
                { title: t("ticketDetail.ownershipColumns.queue"), dataIndex: "queue_name", key: "queue_name" },
                { title: t("ticketDetail.ownershipColumns.team"), dataIndex: "team_prefix", key: "team_prefix" },
                { title: t("ticketDetail.ownershipColumns.start"), dataIndex: "start_time", key: "start_time", render: (v: string) => v ? new Date(v).toLocaleString() : "-" },
                { title: t("ticketDetail.ownershipColumns.end"), dataIndex: "end_time", key: "end_time", render: (v: string) => v ? new Date(v).toLocaleString() : t("common.active") },
                { title: t("ticketDetail.ownershipColumns.duration"), dataIndex: "duration_seconds", key: "duration_seconds", render: (v: number) => formatDuration(v) },
              ]}
            />
          ),
        },
        {
          key: "queue_periods",
          label: t("ticketDetail.queuePeriods"),
          children: (
            <Table
              dataSource={queuePeriodsData || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: t("ticketDetail.queueColumns.queue"), dataIndex: "queue_name", key: "queue_name" },
                { title: t("ticketDetail.queueColumns.entered"), dataIndex: "entered_at", key: "entered_at", render: (v: string) => v ? new Date(v).toLocaleString() : "-" },
                { title: t("ticketDetail.queueColumns.exited"), dataIndex: "exited_at", key: "exited_at", render: (v: string) => v ? new Date(v).toLocaleString() : t("common.active") },
                { title: t("ticketDetail.queueColumns.duration"), dataIndex: "duration_seconds", key: "duration_seconds", render: (v: number) => formatDuration(v) },
                { title: t("ticketDetail.queueColumns.owners"), dataIndex: "owner_count", key: "owner_count" },
              ]}
            />
          ),
        },
        {
          key: "sla",
          label: t("ticketDetail.slaMetrics"),
          children: (
            <Table
              dataSource={slaData || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={slaColumns}
            />
          ),
        },
        {
          key: "sla_explain",
          label: <span><InfoCircleOutlined /> SLA Explanation</span>,
          children: <SLAExplainer ticketId={ticketId} />,
        },
      ]} />
    </div>
  );
}
