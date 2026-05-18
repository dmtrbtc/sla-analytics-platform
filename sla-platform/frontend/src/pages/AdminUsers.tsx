import { useEffect, useState } from "react";
import {
  Typography,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Space,
  message,
  Popconfirm,
} from "antd";
import { PlusOutlined, EditOutlined, StopOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { authApi } from "../api/auth";

interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  admin: "red",
  analyst: "blue",
  viewer: "green",
};

export default function AdminUsers() {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const resp = await authApi.listUsers();
      setUsers(resp.data.users || []);
      setTotal(resp.data.total || 0);
    } catch {
      message.error(t("adminUsers.failedToLoad"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue(user);
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingUser) {
        await authApi.updateUser(editingUser.id, values);
        message.success(t("adminUsers.userUpdated"));
      } else {
        await authApi.createUser(values);
        message.success(t("adminUsers.userCreated"));
      }
      setModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    }
  };

  const handleDeactivate = async (user: User) => {
    try {
      await authApi.deleteUser(user.id);
      message.success(t("adminUsers.userDeactivated"));
      fetchUsers();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || t("adminUsers.failedToDeactivate"));
    }
  };

  const columns = [
    {
      title: t("adminUsers.columns.name"),
      dataIndex: "display_name",
      key: "display_name",
    },
    {
      title: t("adminUsers.columns.email"),
      dataIndex: "email",
      key: "email",
    },
    {
      title: t("adminUsers.columns.role"),
      dataIndex: "role",
      key: "role",
      render: (role: string) => (
        <Tag color={ROLE_COLORS[role] || "default"}>{t(`adminUsers.roles.${role}`, role)}</Tag>
      ),
    },
    {
      title: t("adminUsers.columns.status"),
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean) =>
        active ? <Tag color="green">{t("adminUsers.statusLabels.active")}</Tag> : <Tag color="red">{t("adminUsers.statusLabels.inactive")}</Tag>,
    },
    {
      title: t("adminUsers.columns.created"),
      dataIndex: "created_at",
      key: "created_at",
      render: (d: string) => new Date(d).toLocaleDateString(),
    },
    {
      title: t("adminUsers.columns.actions"),
      key: "actions",
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          >
            {t("common.edit")}
          </Button>
          {record.is_active && (
            <Popconfirm
              title={t("adminUsers.deactivateConfirm")}
              onConfirm={() => handleDeactivate(record)}
            >
              <Button type="link" danger icon={<StopOutlined />}>
                {t("common.delete")}
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Typography.Title level={4} style={{ margin: 0 }}>
          {t("adminUsers.title")}
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {t("adminUsers.createUser")}
        </Button>
      </div>

      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ total, pageSize: 100 }}
      />

      <Modal
        title={editingUser ? t("adminUsers.editUser") : t("adminUsers.createUser")}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        okText={editingUser ? t("adminUsers.save") : t("adminUsers.create")}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="display_name"
            label={t("adminUsers.form.displayName")}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="email"
            label={t("adminUsers.form.email")}
            rules={[
              { required: true },
              { type: "email", message: t("adminUsers.form.invalidEmail") },
            ]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>
          {!editingUser && (
            <Form.Item
              name="password"
              label={t("adminUsers.form.password")}
              rules={[{ required: true, min: 6, message: t("adminUsers.form.passwordMinLength") }]}
            >
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="role" label={t("adminUsers.form.role")} rules={[{ required: true }]}>
            <Select>
              <Select.Option value="admin">{t("adminUsers.roles.admin")}</Select.Option>
              <Select.Option value="analyst">{t("adminUsers.roles.analyst")}</Select.Option>
              <Select.Option value="viewer">{t("adminUsers.roles.viewer")}</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
