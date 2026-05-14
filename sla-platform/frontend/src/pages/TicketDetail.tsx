import { useParams, useNavigate } from "react-router-dom";
import { Typography, Card, Descriptions, Table, Tag, Spin, Timeline, Tabs, Space, Button, Empty } from "antd";
import { ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { ticketsApi } from "../api/tickets";

export default function TicketDetail() {
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
  if (!ticketData) return <Empty description="Ticket not found" />;

  const ticket = ticketData;

  const slaColumns = [
    { title: "Metric", dataIndex: "metric_name", key: "metric_name" },
    {
      title: "Value", dataIndex: "metric_seconds", key: "metric_seconds",
      render: (v: number) => formatDuration(v),
    },
    {
      title: "Breached", dataIndex: "sla_breached", key: "sla_breached",
      render: (v: boolean) => v
        ? <Tag icon={<CloseCircleOutlined />} color="error">Yes</Tag>
        : <Tag icon={<CheckCircleOutlined />} color="success">No</Tag>,
    },
    { title: "Queue", dataIndex: "queue_name", key: "queue_name" },
    { title: "Owner", dataIndex: "owner", key: "owner" },
    { title: "Confidence", dataIndex: "confidence", key: "confidence" },
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
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tickets")}>Back</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Ticket #{ticket.ticket_number || ticket.ticket_id}
        </Typography.Title>
        <Tag>{ticket.confidence}</Tag>
        {ticket.is_closed ? <Tag color="green">Closed</Tag> : <Tag color="blue">Open</Tag>}
      </Space>

      <Tabs defaultActiveKey="overview" items={[
        {
          key: "overview",
          label: "Overview",
          children: (
            <Card size="small">
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="Ticket ID">{ticket.ticket_id}</Descriptions.Item>
                <Descriptions.Item label="Ticket Number">{ticket.ticket_number || "-"}</Descriptions.Item>
                <Descriptions.Item label="Title" span={2}>{ticket.title || "-"}</Descriptions.Item>
                <Descriptions.Item label="Queue">{ticket.current_queue || "-"}</Descriptions.Item>
                <Descriptions.Item label="State">{ticket.current_state || "-"}</Descriptions.Item>
                <Descriptions.Item label="Owner">{ticket.current_owner || "-"}</Descriptions.Item>
                <Descriptions.Item label="Customer">{ticket.customer_id || "-"}</Descriptions.Item>
                <Descriptions.Item label="Created">{ticket.created_at ? new Date(ticket.created_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label="Updated">{ticket.updated_at ? new Date(ticket.updated_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label="First Response">{ticket.first_response_at ? new Date(ticket.first_response_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label="Resolution">{ticket.resolution_at ? new Date(ticket.resolution_at).toLocaleString() : "-"}</Descriptions.Item>
                <Descriptions.Item label="Confidence">{ticket.confidence || "-"}</Descriptions.Item>
                <Descriptions.Item label="Is Merged">{ticket.is_merged ? "Yes" : "No"}</Descriptions.Item>
              </Descriptions>
            </Card>
          ),
        },
        {
          key: "timeline",
          label: "Event Timeline",
          children: timelineItems.length > 0
            ? <Timeline items={timelineItems} style={{ maxHeight: 500, overflow: "auto" }} />
            : <Empty description="No events" />,
        },
        {
          key: "ownership",
          label: "Ownership Periods",
          children: (
            <Table
              dataSource={ownershipData || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: "Owner", dataIndex: "owner", key: "owner" },
                { title: "Queue", dataIndex: "queue_name", key: "queue_name" },
                { title: "Team", dataIndex: "team_prefix", key: "team_prefix" },
                { title: "Start", dataIndex: "start_time", key: "start_time", render: (v: string) => v ? new Date(v).toLocaleString() : "-" },
                { title: "End", dataIndex: "end_time", key: "end_time", render: (v: string) => v ? new Date(v).toLocaleString() : "Active" },
                { title: "Duration", dataIndex: "duration_seconds", key: "duration_seconds", render: (v: number) => formatDuration(v) },
              ]}
            />
          ),
        },
        {
          key: "queue_periods",
          label: "Queue Periods",
          children: (
            <Table
              dataSource={queuePeriodsData || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: "Queue", dataIndex: "queue_name", key: "queue_name" },
                { title: "Entered", dataIndex: "entered_at", key: "entered_at", render: (v: string) => v ? new Date(v).toLocaleString() : "-" },
                { title: "Exited", dataIndex: "exited_at", key: "exited_at", render: (v: string) => v ? new Date(v).toLocaleString() : "Active" },
                { title: "Duration", dataIndex: "duration_seconds", key: "duration_seconds", render: (v: number) => formatDuration(v) },
                { title: "Owners", dataIndex: "owner_count", key: "owner_count" },
              ]}
            />
          ),
        },
        {
          key: "sla",
          label: "SLA Metrics",
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
      ]} />
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds === 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}
