import { useEffect, useState } from "react";
import { Typography, Table, Button, Modal, Form, Input, Space, Tag, message, Popconfirm, Switch } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { teamsApi } from "../api/teams";
import { useTheme } from "../design/ThemeContext";
import { cardStyle, pageHeaderStyle } from "../design/tokens";
import { spacing } from "../design/spacing";

interface Team {
  id: number;
  name: string;
  queue_prefix: string;
  description: string;
  is_active: boolean;
  created_at: string;
  member_count?: number;
}

export default function Teams() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Team | null>(null);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await teamsApi.list();
      setTeams(resp.data.teams || []);
    } catch { message.error(t("common.error")); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const openCreate = () => { setEditing(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (t: Team) => { setEditing(t); form.setFieldsValue(t); setModalOpen(true); };

  const handleSave = async () => {
    const values = await form.validateFields();
    if (editing) {
      await teamsApi.update(editing.id, values);
      message.success("Команда обновлена");
    } else {
      await teamsApi.create(values);
      message.success("Команда создана");
    }
    setModalOpen(false);
    fetch();
  };

  const handleDelete = async (id: number) => {
    await teamsApi.delete(id);
    message.success("Команда удалена");
    fetch();
  };

  const columns = [
    { title: t("teams.name", "Название"), dataIndex: "name", key: "name", render: (v: string) => <Typography.Text strong>{v}</Typography.Text> },
    { title: t("teams.queuePrefix", "Префикс очереди"), dataIndex: "queue_prefix", key: "queue_prefix", render: (v: string) => <Tag style={{ fontSize: 11, fontFamily: "monospace" }}>{v}</Tag> },
    { title: t("teams.description", "Описание"), dataIndex: "description", key: "description", ellipsis: true },
    { title: t("teams.status", "Статус"), dataIndex: "is_active", key: "active", render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "Активна" : "Неактивна"}</Tag> },
    {
      title: "", key: "actions", width: 160,
      render: (_: any, r: Team) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(r)} size="small">{t("common.edit")}</Button>
          <Popconfirm title="Удалить команду?" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} size="small">{t("common.delete")}</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: spacing[4], maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing[4] }}>
        <div>
          <Typography.Title level={3} style={{ margin: 0, fontSize: 20, fontWeight: 600, color: colors.text.primary }}>
            <TeamOutlined style={{ marginRight: 8 }} />{t("teams.title")}
          </Typography.Title>
          <Typography.Text style={{ fontSize: 12, color: colors.text.tertiary }}>{t("teams.description")}</Typography.Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t("teams.createTeam", "Создать команду")}</Button>
      </div>

      <div style={cardStyle}>
        <Table dataSource={teams} columns={columns} rowKey="id" loading={loading} pagination={false} size="middle"
          locale={{ emptyText: "Нет команд. Создайте первую команду." }} />
      </div>

      <Modal title={editing ? "Редактировать команду" : "Создать команду"} open={modalOpen}
        onOk={handleSave} onCancel={() => setModalOpen(false)} okText="Сохранить" cancelText="Отмена">
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true, message: "Введите название" }]}>
            <Input placeholder="Support Team" />
          </Form.Item>
          <Form.Item name="queue_prefix" label="Префикс очереди" rules={[{ required: true, message: "Введите префикс" }]}>
            <Input placeholder="Support" />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} placeholder="Описание команды" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
