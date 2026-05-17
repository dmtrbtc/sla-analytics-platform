import { useState } from "react";
import { Typography, Table, Tag, Input, Select, Space, Button } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { ticketsApi } from "../api/tickets";

export default function Tickets() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<string | undefined>();
  const [closedFilter, setClosedFilter] = useState<boolean | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["tickets", page, pageSize, search, stateFilter, closedFilter],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (search) params.search = search;
      if (stateFilter) params.state = stateFilter;
      if (closedFilter !== undefined) params.is_closed = closedFilter;
      const resp = await ticketsApi.list(params);
      return resp.data;
    },
  });

  const columns = [
    {
      title: t("tickets.columns.id"), dataIndex: "ticket_id", key: "ticket_id", width: 80,
    },
    {
      title: t("tickets.columns.ticketNo"), dataIndex: "ticket_number", key: "ticket_number", width: 120,
      render: (v: string, r: any) => <a onClick={() => navigate(`/tickets/${r.ticket_id}`)}>{v || r.ticket_id}</a>,
    },
    { title: t("tickets.columns.title"), dataIndex: "title", key: "title", ellipsis: true },
    { title: t("tickets.columns.queue"), dataIndex: "current_queue", key: "current_queue", width: 150 },
    {
      title: t("tickets.columns.state"), dataIndex: "current_state", key: "current_state", width: 120,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: t("tickets.columns.owner"), dataIndex: "current_owner", key: "current_owner", width: 130 },
    {
      title: t("tickets.columns.status"), dataIndex: "is_closed", key: "is_closed", width: 80,
      render: (v: boolean) => v ? <Tag color="green">{t("tickets.closed")}</Tag> : <Tag color="blue">{t("tickets.open")}</Tag>,
    },
    {
      title: t("tickets.columns.confidence"), dataIndex: "confidence", key: "confidence", width: 100,
      render: (v: string) => {
        const color = v === "full" ? "green" : v === "partial" ? "orange" : "red";
        return <Tag color={color}>{v}</Tag>;
      },
    },
    {
      title: t("tickets.columns.created"), dataIndex: "created_at", key: "created_at", width: 160,
      render: (v: string) => v ? new Date(v).toLocaleString() : "-",
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>{t("tickets.title")}</Typography.Title>
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder={t("tickets.search")}
          allowClear
          onSearch={(v) => { setSearch(v); setPage(1); }}
          style={{ width: 300 }}
        />
        <Select
          placeholder={t("tickets.filterState")}
          allowClear
          style={{ width: 150 }}
          onChange={(v) => { setStateFilter(v); setPage(1); }}
          options={[
            { value: "open", label: t("tickets.open") },
            { value: "closed", label: t("tickets.closed") },
            { value: "pending", label: t("tickets.pending") },
            { value: "closed successful", label: t("tickets.closedSuccessful") },
            { value: "closed unsuccessful", label: t("tickets.closedUnsuccessful") },
          ]}
        />
        <Select
          placeholder={t("tickets.filterStatus")}
          allowClear
          style={{ width: 120 }}
          onChange={(v) => { setClosedFilter(v === "all" ? undefined : v); setPage(1); }}
          options={[
            { value: false, label: t("tickets.open") },
            { value: true, label: t("tickets.closed") },
          ]}
        />
      </Space>

      <Table
        dataSource={data?.tickets || []}
        columns={columns}
        rowKey="ticket_id"
        loading={isLoading}
        size="small"
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          onChange: (p) => setPage(p),
          showSizeChanger: false,
        }}
        onRow={(record) => ({
          onClick: () => navigate(`/tickets/${record.ticket_id}`),
          style: { cursor: "pointer" },
        })}
      />
    </div>
  );
}
