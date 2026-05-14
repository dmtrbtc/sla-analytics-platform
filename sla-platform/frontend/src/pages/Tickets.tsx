import { useState } from "react";
import { Typography, Table, Tag, Input, Select, Space, Button } from "antd";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ticketsApi } from "../api/tickets";

export default function Tickets() {
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
      title: "ID", dataIndex: "ticket_id", key: "ticket_id", width: 80,
    },
    {
      title: "Ticket#", dataIndex: "ticket_number", key: "ticket_number", width: 120,
      render: (v: string, r: any) => <a onClick={() => navigate(`/tickets/${r.ticket_id}`)}>{v || r.ticket_id}</a>,
    },
    { title: "Title", dataIndex: "title", key: "title", ellipsis: true },
    { title: "Queue", dataIndex: "current_queue", key: "current_queue", width: 150 },
    {
      title: "State", dataIndex: "current_state", key: "current_state", width: 120,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: "Owner", dataIndex: "current_owner", key: "current_owner", width: 130 },
    {
      title: "Status", dataIndex: "is_closed", key: "is_closed", width: 80,
      render: (v: boolean) => v ? <Tag color="green">Closed</Tag> : <Tag color="blue">Open</Tag>,
    },
    {
      title: "Confidence", dataIndex: "confidence", key: "confidence", width: 100,
      render: (v: string) => {
        const color = v === "full" ? "green" : v === "partial" ? "orange" : "red";
        return <Tag color={color}>{v}</Tag>;
      },
    },
    {
      title: "Created", dataIndex: "created_at", key: "created_at", width: 160,
      render: (v: string) => v ? new Date(v).toLocaleString() : "-",
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Tickets</Typography.Title>
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="Search ticket # or title..."
          allowClear
          onSearch={(v) => { setSearch(v); setPage(1); }}
          style={{ width: 300 }}
        />
        <Select
          placeholder="Filter state"
          allowClear
          style={{ width: 150 }}
          onChange={(v) => { setStateFilter(v); setPage(1); }}
          options={[
            { value: "open", label: "Open" },
            { value: "closed", label: "Closed" },
            { value: "pending", label: "Pending" },
            { value: "closed successful", label: "Closed Successful" },
            { value: "closed unsuccessful", label: "Closed Unsuccessful" },
          ]}
        />
        <Select
          placeholder="Status"
          allowClear
          style={{ width: 120 }}
          onChange={(v) => { setClosedFilter(v === "all" ? undefined : v); setPage(1); }}
          options={[
            { value: false, label: "Open" },
            { value: true, label: "Closed" },
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
