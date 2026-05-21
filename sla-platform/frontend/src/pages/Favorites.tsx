import { useEffect, useMemo, useState } from "react";
import {
  Row, Col, Card, Typography, Button, Input, Tag, Table, Modal, Form,
  Select, Switch, Space, Popconfirm, message, Tabs, Empty, Tooltip,
} from "antd";
import {
  StarFilled, StarOutlined, PlusOutlined, DeleteOutlined, EditOutlined,
  PushpinOutlined, RadarChartOutlined, AppstoreOutlined,
} from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { favoritesApi, type QueueGroup, type DashboardPreset } from "../api/favorites";
import { useFavorites } from "../contexts/FavoritesContext";
import { spacing } from "../design/spacing";
import { cardStyle } from "../design/tokens";

const { Title, Text } = Typography;

const WORKSPACE_KINDS = [
  { value: "noc",         label: "NOC View" },
  { value: "servicedesk", label: "ServiceDesk View" },
  { value: "infra",       label: "Infra View" },
  { value: "sap",         label: "SAP View" },
  { value: "executive",   label: "Executive View" },
  { value: "custom",      label: "Custom" },
];

export default function Favorites() {
  const qc = useQueryClient();
  const { favorites, refresh, toggle, enableFavoritesOnly, setEnableFavoritesOnly, activeFilter, setActiveFilter } = useFavorites();

  const groupsQ = useQuery({
    queryKey: ["favorites", "groups"],
    queryFn: () => favoritesApi.listGroups(true),
  });
  const presetsQ = useQuery({
    queryKey: ["favorites", "presets"],
    queryFn: () => favoritesApi.listPresets(true),
  });

  const groups = groupsQ.data?.groups ?? [];
  const presets = presetsQ.data?.presets ?? [];

  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<QueueGroup | null>(null);
  const [groupForm] = Form.useForm();

  const [presetModalOpen, setPresetModalOpen] = useState(false);
  const [editingPreset, setEditingPreset] = useState<DashboardPreset | null>(null);
  const [presetForm] = Form.useForm();

  const saveGroup = useMutation({
    mutationFn: async (vals: any) => {
      const queues = (vals.queues || "").split(",").map((s: string) => s.trim()).filter(Boolean);
      if (editingGroup) {
        return favoritesApi.updateGroup(editingGroup.id, {
          name: vals.name, description: vals.description, color: vals.color,
          is_shared: !!vals.is_shared, queues,
        });
      }
      return favoritesApi.createGroup({
        name: vals.name, description: vals.description, color: vals.color,
        is_shared: !!vals.is_shared, queues,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites", "groups"] });
      setGroupModalOpen(false); setEditingGroup(null); groupForm.resetFields();
      message.success("Группа сохранена");
    },
    onError: () => message.error("Не удалось сохранить группу"),
  });

  const removeGroup = useMutation({
    mutationFn: (id: string) => favoritesApi.deleteGroup(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites", "groups"] });
      message.success("Группа удалена");
    },
  });

  const savePreset = useMutation({
    mutationFn: async (vals: any) => {
      if (editingPreset) {
        return favoritesApi.updatePreset(editingPreset.id, vals);
      }
      return favoritesApi.createPreset(vals);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites", "presets"] });
      setPresetModalOpen(false); setEditingPreset(null); presetForm.resetFields();
      message.success("Воркспейс сохранён");
    },
    onError: () => message.error("Не удалось сохранить воркспейс"),
  });

  const removePreset = useMutation({
    mutationFn: (id: string) => favoritesApi.deletePreset(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["favorites", "presets"] });
      message.success("Воркспейс удалён");
    },
  });

  const applyPreset = (p: DashboardPreset) => {
    const g = groups.find(x => x.id === p.queue_group_id);
    if (g) {
      setActiveFilter(g.queues);
      setEnableFavoritesOnly(false);
      message.success(`Применён воркспейс «${p.name}» — ${g.queues.length} очередей`);
    } else {
      message.warning("Воркспейс без группы — фильтр не применён");
    }
  };

  return (
    <div style={{ padding: spacing[6], maxWidth: 1500, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: spacing[2] }}>
        <StarFilled style={{ color: "#f5c518", marginRight: 8 }} />
        Избранные очереди и воркспейсы
      </Title>
      <Text type="secondary">
        Закрепите критические очереди, объедините их в группы, переключайтесь между операционными воркспейсами.
      </Text>

      {/* Active filter bar */}
      <Card style={{ ...cardStyle, marginTop: spacing[4] }} bordered={false}>
        <Row gutter={[16, 12]} align="middle">
          <Col flex="0 0 auto">
            <Space>
              <Switch
                checked={enableFavoritesOnly}
                onChange={setEnableFavoritesOnly}
                checkedChildren="Только избранные"
                unCheckedChildren="Все"
              />
              <Tag color={activeFilter.length ? "blue" : "default"}>
                Активный фильтр: {activeFilter.length ? `${activeFilter.length} очередей` : "нет"}
              </Tag>
            </Space>
          </Col>
          <Col flex="1 1 auto" />
          <Col flex="0 0 auto">
            <Button onClick={() => setActiveFilter([])} disabled={activeFilter.length === 0}>
              Сбросить фильтр
            </Button>
          </Col>
        </Row>
        {activeFilter.length > 0 && (
          <div style={{ marginTop: spacing[3] }}>
            {activeFilter.map(q => (
              <Tag key={q} closable onClose={() => setActiveFilter(activeFilter.filter(x => x !== q))}
                   style={{ marginBottom: 4 }}>
                {q}
              </Tag>
            ))}
          </div>
        )}
      </Card>

      <Tabs
        style={{ marginTop: spacing[4] }}
        items={[
          {
            key: "favs",
            label: <span><StarFilled style={{ color: "#f5c518" }} /> Избранное ({favorites.length})</span>,
            children: (
              <Card style={cardStyle} bordered={false}>
                {favorites.length === 0 ? (
                  <Empty description="Пока нет избранных очередей. Звезда отображается рядом с именем очереди везде в приложении — нажмите её." />
                ) : (
                  <Table
                    size="small" pagination={false} rowKey="queue_name"
                    dataSource={favorites}
                    columns={[
                      { title: "#", dataIndex: "position", width: 60 },
                      { title: "Очередь", dataIndex: "queue_name" },
                      {
                        title: "Добавлено",
                        dataIndex: "starred_at", width: 220,
                        render: (v) => v ? new Date(v).toLocaleString("ru-RU") : "—",
                      },
                      {
                        title: "Действия", width: 140,
                        render: (_v, r) => (
                          <Space size="small">
                            <Button size="small" onClick={() => { setActiveFilter([r.queue_name]); message.info(`Фильтр: ${r.queue_name}`); }}>
                              Фильтровать
                            </Button>
                            <Button size="small" danger icon={<DeleteOutlined />}
                                    onClick={() => toggle(r.queue_name)} />
                          </Space>
                        ),
                      },
                    ]}
                  />
                )}
              </Card>
            ),
          },
          {
            key: "groups",
            label: <span><AppstoreOutlined /> Группы ({groups.length})</span>,
            children: (
              <Card
                style={cardStyle} bordered={false}
                title="Группы очередей"
                extra={<Button type="primary" icon={<PlusOutlined />}
                  onClick={() => { setEditingGroup(null); groupForm.resetFields(); setGroupModalOpen(true); }}>
                  Создать группу
                </Button>}
              >
                {groups.length === 0 ? (
                  <Empty description="Создайте группы — «Critical Infra», «ServiceDesk Hot Queues», «SAP Support» и т.д." />
                ) : (
                  <Table
                    size="small" pagination={false} rowKey="id"
                    dataSource={groups}
                    columns={[
                      {
                        title: "Группа", dataIndex: "name",
                        render: (n, r) => (
                          <Space>
                            {r.color && <span style={{
                              display: "inline-block", width: 10, height: 10,
                              borderRadius: 2, background: r.color,
                            }} />}
                            <Text strong>{n}</Text>
                            {r.is_shared && <Tag color="purple">общая</Tag>}
                          </Space>
                        ),
                      },
                      { title: "Очередей", dataIndex: "queue_count", width: 100, align: "right" },
                      {
                        title: "Очереди", dataIndex: "queues", width: 480,
                        render: (qs: string[]) => (
                          <span style={{ fontSize: 12 }}>
                            {qs.slice(0, 4).join(", ")}
                            {qs.length > 4 && <Text type="secondary"> +{qs.length - 4}</Text>}
                          </span>
                        ),
                      },
                      {
                        title: "Действия", width: 200,
                        render: (_v, r) => (
                          <Space size="small">
                            <Button size="small"
                              onClick={() => { setActiveFilter(r.queues); message.info(`Применена группа «${r.name}»`); }}>
                              Применить
                            </Button>
                            <Button size="small" icon={<EditOutlined />}
                              onClick={() => {
                                setEditingGroup(r);
                                groupForm.setFieldsValue({
                                  name: r.name, description: r.description, color: r.color,
                                  is_shared: r.is_shared, queues: (r.queues || []).join(", "),
                                });
                                setGroupModalOpen(true);
                              }} />
                            <Popconfirm title="Удалить группу?" onConfirm={() => removeGroup.mutate(r.id)}>
                              <Button size="small" danger icon={<DeleteOutlined />} />
                            </Popconfirm>
                          </Space>
                        ),
                      },
                    ]}
                  />
                )}
              </Card>
            ),
          },
          {
            key: "presets",
            label: <span><RadarChartOutlined /> Воркспейсы ({presets.length})</span>,
            children: (
              <Card
                style={cardStyle} bordered={false}
                title="Операционные воркспейсы"
                extra={<Button type="primary" icon={<PlusOutlined />}
                  onClick={() => { setEditingPreset(null); presetForm.resetFields(); presetForm.setFieldsValue({ workspace_kind: "custom" }); setPresetModalOpen(true); }}>
                  Создать воркспейс
                </Button>}
              >
                {presets.length === 0 ? (
                  <Empty description="Создайте воркспейсы — NOC, ServiceDesk, Infra, SAP, Executive..." />
                ) : (
                  <Table
                    size="small" pagination={false} rowKey="id"
                    dataSource={presets}
                    columns={[
                      { title: "Имя", dataIndex: "name", render: (v, r) => (
                        <Space>
                          <Text strong>{v}</Text>
                          {r.is_default && <Tag color="gold">по умолчанию</Tag>}
                          {r.is_shared && <Tag color="purple">общий</Tag>}
                        </Space>
                      ) },
                      { title: "Тип", dataIndex: "workspace_kind", width: 160 },
                      {
                        title: "Группа очередей", dataIndex: "queue_group_id", width: 240,
                        render: (gid) => {
                          const g = groups.find(x => x.id === gid);
                          return g ? g.name : <Text type="secondary">—</Text>;
                        },
                      },
                      {
                        title: "Действия", width: 240,
                        render: (_v, r) => (
                          <Space size="small">
                            <Button size="small" type="primary" icon={<PushpinOutlined />}
                              onClick={() => applyPreset(r)}>Применить</Button>
                            <Button size="small" icon={<EditOutlined />}
                              onClick={() => {
                                setEditingPreset(r);
                                presetForm.setFieldsValue({
                                  name: r.name, workspace_kind: r.workspace_kind,
                                  queue_group_id: r.queue_group_id, is_shared: r.is_shared,
                                  is_default: r.is_default,
                                });
                                setPresetModalOpen(true);
                              }} />
                            <Popconfirm title="Удалить воркспейс?" onConfirm={() => removePreset.mutate(r.id)}>
                              <Button size="small" danger icon={<DeleteOutlined />} />
                            </Popconfirm>
                          </Space>
                        ),
                      },
                    ]}
                  />
                )}
              </Card>
            ),
          },
        ]}
      />

      {/* Group modal */}
      <Modal
        open={groupModalOpen} onCancel={() => setGroupModalOpen(false)}
        title={editingGroup ? "Изменить группу" : "Создать группу"}
        onOk={() => groupForm.validateFields().then(saveGroup.mutate)}
        okButtonProps={{ loading: saveGroup.isPending }}
      >
        <Form form={groupForm} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input placeholder="Critical Infra" />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="color" label="Цвет"><Input placeholder="#b42333" /></Form.Item>
          <Form.Item name="queues" label="Очереди (через запятую)">
            <Input.TextArea rows={3} placeholder="MBR-137-ServiceDesk, MBR-137-Network, MBR-137-DC-WintelOperations" />
          </Form.Item>
          <Form.Item name="is_shared" label="Общая для всех" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Preset modal */}
      <Modal
        open={presetModalOpen} onCancel={() => setPresetModalOpen(false)}
        title={editingPreset ? "Изменить воркспейс" : "Создать воркспейс"}
        onOk={() => presetForm.validateFields().then(savePreset.mutate)}
        okButtonProps={{ loading: savePreset.isPending }}
      >
        <Form form={presetForm} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input placeholder="NOC View" />
          </Form.Item>
          <Form.Item name="workspace_kind" label="Тип" rules={[{ required: true }]}>
            <Select options={WORKSPACE_KINDS} />
          </Form.Item>
          <Form.Item name="queue_group_id" label="Группа очередей">
            <Select allowClear options={groups.map(g => ({ value: g.id, label: g.name }))} />
          </Form.Item>
          <Form.Item name="is_shared" label="Общий" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item name="is_default" label="По умолчанию для меня" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
