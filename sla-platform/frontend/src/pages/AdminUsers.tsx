import { useEffect, useState } from "react";
import { Typography, Table, Button, Modal, Form, Input, Select, Tag, Space, message, Popconfirm, Badge, Row, Col } from "antd";
import { PlusOutlined, EditOutlined, StopOutlined, SearchOutlined, UserOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { authApi } from "../api/auth";
import { useTheme } from "../design/ThemeContext";
import { cardStyle } from "../design/tokens";
import { spacing } from "../design/spacing";
import { typography } from "../design/typography";

interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  organization_id?: string;
}

const ROLE_COLORS: Record<string, string> = { admin: "red", analyst: "blue", team_lead: "orange", viewer: "green" };

export default function AdminUsers() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [users, setUsers] = useState<User[]>([]);
  const [filtered, setFiltered] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const resp = await authApi.listUsers(500, 0);
      const list = resp.data.users || [];
      setUsers(list);
      setTotal(resp.data.total || 0);
    } catch { message.error(t("adminUsers.failedToLoad")); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchUsers(); }, []);

  useEffect(() => {
    let list = [...users];
    if (search) { const s = search.toLowerCase(); list = list.filter(u => u.display_name?.toLowerCase().includes(s) || u.email?.toLowerCase().includes(s)); }
    if (roleFilter) list = list.filter(u => u.role === roleFilter);
    if (statusFilter === "active") list = list.filter(u => u.is_active);
    if (statusFilter === "inactive") list = list.filter(u => !u.is_active);
    setFiltered(list);
  }, [users, search, roleFilter, statusFilter]);

  const openCreate = () => { setEditingUser(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (user: User) => { setEditingUser(user); form.setFieldsValue(user); setModalOpen(true); };

  const handleSave = async () => {
    const values = await form.validateFields();
    if (editingUser) { await authApi.updateUser(editingUser.id, values); message.success(t("adminUsers.userUpdated")); }
    else { await authApi.createUser(values); message.success(t("adminUsers.userCreated")); }
    setModalOpen(false); fetchUsers();
  };

  const handleDeactivate = async (user: User) => {
    await authApi.deleteUser(user.id);
    message.success(t("adminUsers.userDeactivated"));
    fetchUsers();
  };

  const columns = [
    { title: t("adminUsers.columns.name"), dataIndex: "display_name", key: "name", render: (v: string, r: User) => <Space><UserOutlined style={{ color: colors.text.tertiary }} /><Typography.Text strong>{v || "—"}</Typography.Text></Space> },
    { title: t("adminUsers.columns.email"), dataIndex: "email", key: "email", render: (v: string) => <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text> },
    { title: t("adminUsers.columns.role"), dataIndex: "role", key: "role", render: (role: string) => <Tag color={ROLE_COLORS[role] || "default"}>{t(`adminUsers.roles.${role}`, role)}</Tag> },
    {
      title: t("adminUsers.columns.status"), dataIndex: "is_active", key: "status", render: (active: boolean) =>
        active ? <Tag color="success" style={{ borderRadius: 12 }}>Активен</Tag> : <Tag color="error" style={{ borderRadius: 12 }}>Неактивен</Tag>
    },
    { title: t("adminUsers.columns.created"), dataIndex: "created_at", key: "created", render: (d: string) => <Typography.Text style={{ fontSize: 11, fontFamily: typography.fontMono }}>{d ? new Date(d).toLocaleDateString("ru-RU") : "—"}</Typography.Text> },
    {
      title: "", key: "actions", width: 160,
      render: (_: any, record: User) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)} size="small">{t("common.edit")}</Button>
          {record.is_active && <Popconfirm title={t("adminUsers.deactivateConfirm")} onConfirm={() => handleDeactivate(record)}><Button type="link" danger icon={<StopOutlined />} size="small">{t("common.delete")}</Button></Popconfirm>}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: spacing[4], maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing[4] }}>
        <Typography.Title level={3} style={{ margin: 0, fontSize: 20, fontWeight: 600, color: colors.text.primary }}>
          <UserOutlined style={{ marginRight: 8 }} />{t("adminUsers.title")}
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t("adminUsers.createUser")}</Button>
      </div>

      <Row gutter={[12, 12]} style={{ marginBottom: spacing[3] }}>
        <Col span={8}>
          <Input prefix={<SearchOutlined style={{ color: colors.text.tertiary }} />} placeholder="Поиск по имени или email" value={search} onChange={e => setSearch(e.target.value)} allowClear />
        </Col>
        <Col span={4}>
          <Select placeholder="Роль" value={roleFilter} onChange={setRoleFilter} allowClear style={{ width: "100%" }}>
            <Select.Option value="admin">Admin</Select.Option>
            <Select.Option value="analyst">Analyst</Select.Option>
            <Select.Option value="team_lead">Team Lead</Select.Option>
            <Select.Option value="viewer">Viewer</Select.Option>
          </Select>
        </Col>
        <Col span={4}>
          <Select placeholder="Статус" value={statusFilter} onChange={setStatusFilter} allowClear style={{ width: "100%" }}>
            <Select.Option value="active">Активен</Select.Option>
            <Select.Option value="inactive">Неактивен</Select.Option>
          </Select>
        </Col>
        <Col span={8}>
          <Typography.Text style={{ fontSize: 12, color: colors.text.tertiary, lineHeight: "32px" }}>
            {t("adminUsers.total", "Всего")}: {total} · Отображено: {filtered.length}
          </Typography.Text>
        </Col>
      </Row>

      <div style={cardStyle}>
        <Table dataSource={filtered} columns={columns} rowKey="id" loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t: number) => `${t} пользователей` }}
          size="middle" locale={{ emptyText: "Нет пользователей" }} />
      </div>

      <Modal title={editingUser ? t("adminUsers.editUser") : t("adminUsers.createUser")} open={modalOpen}
        onOk={handleSave} onCancel={() => setModalOpen(false)} okText={editingUser ? "Сохранить" : "Создать"} cancelText="Отмена">
        <Form form={form} layout="vertical">
          <Form.Item name="display_name" label={t("adminUsers.form.displayName")} rules={[{ required: true }]}>
            <Input placeholder="Имя пользователя" />
          </Form.Item>
          <Form.Item name="email" label={t("adminUsers.form.email")} rules={[{ required: true }, { type: "email", message: t("adminUsers.form.invalidEmail") }]}>
            <Input disabled={!!editingUser} placeholder="user@example.com" />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="password" label={t("adminUsers.form.password")} rules={[{ required: true, min: 6, message: t("adminUsers.form.passwordMinLength") }]}>
              <Input.Password placeholder="Минимум 6 символов" />
            </Form.Item>
          )}
          <Form.Item name="role" label={t("adminUsers.form.role")} rules={[{ required: true }]}>
            <Select>
              <Select.Option value="admin">{t("adminUsers.roles.admin")}</Select.Option>
              <Select.Option value="analyst">{t("adminUsers.roles.analyst")}</Select.Option>
              <Select.Option value="team_lead">Team Lead</Select.Option>
              <Select.Option value="viewer">{t("adminUsers.roles.viewer")}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
