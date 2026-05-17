import { useState } from "react";
import {
  Typography, Tabs, Card, Table, Button, Modal, Form, Input, InputNumber, Select, Switch,
  Space, Tag, message, Popconfirm, Row, Col, Spin, Alert,
} from "antd";
import { PlusOutlined, EditOutlined, CopyOutlined, StopOutlined, DeleteOutlined, ExperimentOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { slaApi } from "../api/sla";
import { formatHumanDuration, parseHumanDuration } from "../utils/format";

export default function SLAConfig() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("rules");
  const [modalOpen, setModalOpen] = useState(false);
  const [editRule, setEditRule] = useState<any>(null);
  const [calModalOpen, setCalModalOpen] = useState(false);
  const [editCal, setEditCal] = useState<any>(null);
  const [escModalOpen, setEscModalOpen] = useState(false);
  const [editEsc, setEditEsc] = useState<any>(null);
  const [simOpen, setSimOpen] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);
  const [form] = Form.useForm();
  const [calForm] = Form.useForm();
  const [escForm] = Form.useForm();
  const [simForm] = Form.useForm();

  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ["sla-queue-rules"],
    queryFn: async () => { const r = await slaApi.listQueueRules(); return r.data.queue_rules; },
    refetchInterval: 30_000,
  });
  const { data: calendars } = useQuery({
    queryKey: ["sla-calendars"],
    queryFn: async () => { const r = await slaApi.listCalendars(); return r.data.calendars; },
  });
  const { data: escalations } = useQuery({
    queryKey: ["sla-escalations"],
    queryFn: async () => { const r = await slaApi.listEscalations(); return r.data.escalations; },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => slaApi.deleteQueueRule(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["sla-queue-rules"] }); message.success(t("common.deleted")); },
  });
  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => slaApi.updateQueueRule(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sla-queue-rules"] }),
  });
  const dupMut = useMutation({
    mutationFn: (data: any) => slaApi.createQueueRule(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["sla-queue-rules"] }); message.success(t("common.created")); },
  });

  const saveRule = async (values: any) => {
    const data = {
      ...values,
      response_target_seconds: parseHumanDuration(values.response_human),
      resolution_target_seconds: parseHumanDuration(values.resolution_human),
    };
    if (editRule) {
      await slaApi.updateQueueRule(editRule.id, data);
    } else {
      await slaApi.createQueueRule(data);
    }
    queryClient.invalidateQueries({ queryKey: ["sla-queue-rules"] });
    message.success(editRule ? t("common.saved") : t("common.created"));
    setModalOpen(false);
    setEditRule(null);
    form.resetFields();
  };

  const openEdit = (rule: any) => {
    setEditRule(rule);
    form.setFieldsValue({
      ...rule,
      response_human: formatHumanDuration(rule.response_target_seconds),
      resolution_human: formatHumanDuration(rule.resolution_target_seconds),
    });
    setModalOpen(true);
  };

  const openDup = (rule: any) => {
    dupMut.mutate({
      name: `${rule.name} (копия)`,
      queue_pattern: rule.queue_pattern,
      priority: rule.priority,
      response_target_seconds: rule.response_target_seconds,
      resolution_target_seconds: rule.resolution_target_seconds,
      description: rule.description,
    });
  };

  const saveCalendar = async (values: any) => {
    const payload = { ...values };
    if (editCal) {
      await slaApi.updateCalendar(editCal.id, payload);
    } else {
      await slaApi.createCalendar(payload);
    }
    queryClient.invalidateQueries({ queryKey: ["sla-calendars"] });
    message.success(editCal ? t("common.saved") : t("common.created"));
    setCalModalOpen(false);
    setEditCal(null);
    calForm.resetFields();
  };

  const saveEscalation = async (values: any) => {
    if (editEsc) {
      await slaApi.updateEscalation(editEsc.id, values);
    } else {
      await slaApi.createEscalation(values);
    }
    queryClient.invalidateQueries({ queryKey: ["sla-escalations"] });
    message.success(editEsc ? t("common.saved") : t("common.created"));
    setEscModalOpen(false);
    setEditEsc(null);
    escForm.resetFields();
  };

  const runSim = async (values: any) => {
    const data = {
      queue_name: values.queue_name,
      response_target_seconds: parseHumanDuration(values.response_human),
      resolution_target_seconds: parseHumanDuration(values.resolution_human),
      calendar_id: values.calendar_id || undefined,
    };
    const resp = await slaApi.simulate(data);
    setSimResult(resp.data);
  };

  const rules = rulesData || [];

  const ruleColumns = [
    { title: t("slaConfig.queue"), dataIndex: "queue_pattern", key: "queue_pattern", width: 180 },
    { title: t("slaConfig.priority"), dataIndex: "priority", key: "priority", width: 80 },
    { title: t("slaConfig.responseTime"), dataIndex: "response_target_seconds", key: "response", width: 140, render: (v: number) => formatHumanDuration(v) },
    { title: t("slaConfig.resolutionTime"), dataIndex: "resolution_target_seconds", key: "resolution", width: 140, render: (v: number) => formatHumanDuration(v) },
    {
      title: t("slaConfig.calendar"), dataIndex: "calendar_id", key: "calendar", width: 120,
      render: (v: string) => v ? <Tag>{calendars?.find((c: any) => c.id === v)?.name || "—"}</Tag> : <Tag>24x7</Tag>,
    },
    {
      title: t("common.active"), dataIndex: "is_active", key: "active", width: 80,
      render: (v: boolean, r: any) => <Switch checked={v} onChange={(ch) => toggleMut.mutate({ id: r.id, is_active: ch })} size="small" />,
    },
    {
      title: "", key: "actions", width: 200,
      render: (_: any, r: any) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          <Button size="small" icon={<CopyOutlined />} onClick={() => openDup(r)} />
          <Popconfirm title={t("common.delete") + "?"} onConfirm={() => deleteMut.mutate(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const calColumns = [
    { title: t("slaConfig.calendarName"), dataIndex: "name", key: "name" },
    { title: t("slaConfig.timezone"), dataIndex: "timezone", key: "tz", width: 80 },
    { title: t("slaConfig.hours"), key: "hours", width: 120, render: (_: any, r: any) => r.is_24x7 ? "24x7" : `${r.start_time}-${r.end_time}` },
    { title: t("common.active"), dataIndex: "is_active", key: "active", width: 80, render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? t("common.yes") : t("common.no")}</Tag> },
    {
      title: "", key: "actions", width: 120,
      render: (_: any, r: any) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => { setEditCal(r); calForm.setFieldsValue(r); setCalModalOpen(true); }} />
        </Space>
      ),
    },
  ];

  const escColumns = [
    { title: t("slaConfig.slaRule"), dataIndex: "sla_rule_id", key: "rule", render: (v: string) => rules.find((r: any) => r.id === v)?.name || v.slice(0, 8) },
    { title: t("slaConfig.threshold"), dataIndex: "threshold_percent", key: "threshold", render: (v: number) => `${v}%` },
    {
      title: t("slaConfig.severity"), dataIndex: "severity", key: "severity",
      render: (v: string) => {
        const colors: Record<string, string> = { warning: "gold", high: "orange", critical: "red" };
        return <Tag color={colors[v] || "default"}>{t(`slaConfig.severity_${v}`)}</Tag>;
      },
    },
    { title: t("common.active"), dataIndex: "is_active", key: "active", render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? t("common.yes") : t("common.no")}</Tag> },
    {
      title: "", key: "actions", width: 120,
      render: (_: any, r: any) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => { setEditEsc(r); escForm.setFieldsValue(r); setEscModalOpen(true); }} />
        </Space>
      ),
    },
  ];

  const severityColors: Record<string, string> = { low: "green", medium: "gold", high: "orange", critical: "red" };

  return (
    <div>
      <Typography.Title level={4}>{t("slaConfig.title")}</Typography.Title>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: "rules",
          label: t("slaConfig.queueRules"),
          children: (
            <Card size="small" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditRule(null); form.resetFields(); setModalOpen(true); }}>{t("common.create")}</Button>}>
              {rulesLoading ? <Spin /> : (
                <Table dataSource={rules} rowKey="id" size="small" pagination={false} columns={ruleColumns} scroll={{ x: true }} />
              )}
            </Card>
          ),
        },
        {
          key: "calendars",
          label: t("slaConfig.businessCalendars"),
          children: (
            <Card size="small" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditCal(null); calForm.resetFields(); setCalModalOpen(true); }}>{t("common.create")}</Button>}>
              <Table dataSource={calendars || []} rowKey="id" size="small" pagination={false} columns={calColumns} scroll={{ x: true }} />
            </Card>
          ),
        },
        {
          key: "escalations",
          label: t("slaConfig.escalationRules"),
          children: (
            <Card size="small" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditEsc(null); escForm.resetFields(); setEscModalOpen(true); }}>{t("common.create")}</Button>}>
              <Table dataSource={escalations || []} rowKey="id" size="small" pagination={false} columns={escColumns} scroll={{ x: true }} />
            </Card>
          ),
        },
        {
          key: "simulator",
          label: t("slaConfig.simulator"),
          children: (
            <Row gutter={16}>
              <Col xs={24} md={10}>
                <Card size="small" title={<><ExperimentOutlined /> {t("slaConfig.simulateTitle")}</>}>
                  <Form form={simForm} layout="vertical" onFinish={runSim}>
                    <Form.Item name="queue_name" label={t("slaConfig.queue")} rules={[{ required: true, message: t("common.required") }]}>
                      <Input placeholder={t("slaConfig.queuePatternPlaceholder")} />
                    </Form.Item>
                    <Form.Item name="response_human" label={t("slaConfig.responseTime")} rules={[{ required: true }]}>
                      <Input placeholder="15 мин" />
                    </Form.Item>
                    <Form.Item name="resolution_human" label={t("slaConfig.resolutionTime")} rules={[{ required: true }]}>
                      <Input placeholder="4 ч" />
                    </Form.Item>
                    <Form.Item name="calendar_id" label={t("slaConfig.calendar")}>
                      <Select allowClear placeholder={t("common.no") + " (24x7)"}>
                        {(calendars || []).filter((c: any) => c.is_active).map((c: any) => (
                          <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Button type="primary" htmlType="submit" icon={<ExperimentOutlined />}>{t("slaConfig.runSimulation")}</Button>
                  </Form>
                </Card>
              </Col>
              <Col xs={24} md={14}>
                {simResult && (
                  <Card size="small" title={t("slaConfig.simulationResult")}>
                    <Row gutter={[12, 12]}>
                      <Col span={8}><Typography.Text strong>{t("slaConfig.riskLevel")}:</Typography.Text><br /><Tag color={severityColors[simResult.risk_level] || "default"}>{t(`analytics.riskLevel_${simResult.risk_level}`)}</Tag></Col>
                      <Col span={8}><Typography.Text strong>{t("slaConfig.riskScore")}:</Typography.Text><br /><b>{simResult.risk_score}</b></Col>
                      <Col span={8}><Typography.Text strong>{t("slaConfig.breachStatus")}:</Typography.Text><br />{simResult.will_breach_response || simResult.will_breach_resolution ? <Tag color="red">{t("slaConfig.willBreach")}</Tag> : <Tag color="green">{t("slaConfig.safe")}</Tag>}</Col>
                    </Row>
                    <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
                      <Col span={6}><Typography.Text strong>{t("slaConfig.responseBreach")}:</Typography.Text><br />{simResult.will_breach_response ? <Tag color="red">{t("common.yes")}</Tag> : <Tag color="green">{t("common.no")}</Tag>}</Col>
                      <Col span={6}><Typography.Text strong>{t("slaConfig.resolutionBreach")}:</Typography.Text><br />{simResult.will_breach_resolution ? <Tag color="red">{t("common.yes")}</Tag> : <Tag color="green">{t("common.no")}</Tag>}</Col>
                      <Col span={6}><Typography.Text strong>{t("slaConfig.simRatio")}:</Typography.Text><br />{(simResult.simulated_response_ratio * 100).toFixed(0)}% / {(simResult.simulated_resolution_ratio * 100).toFixed(0)}%</Col>
                    </Row>
                  </Card>
                )}
              </Col>
            </Row>
          ),
        },
      ]} />

      <Modal title={editRule ? t("slaConfig.editQueueRule") : t("slaConfig.createQueueRule")} open={modalOpen} onCancel={() => { setModalOpen(false); setEditRule(null); }} footer={null} width={560}>
        <Form form={form} layout="vertical" onFinish={saveRule} initialValues={{ priority: 0, is_active: true }}>
          <Form.Item name="name" label={t("slaConfig.ruleName")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="queue_pattern" label={t("slaConfig.queuePattern")} rules={[{ required: true }]} help={t("slaConfig.patternHelp")}>
            <Input placeholder="Support*" />
          </Form.Item>
          <Form.Item name="priority" label={t("slaConfig.priority")}>
            <InputNumber min={0} max={100} style={{ width: 120 }} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="response_human" label={t("slaConfig.responseTime")} rules={[{ required: true }]}>
                <Input placeholder="15 мин" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="resolution_human" label={t("slaConfig.resolutionTime")} rules={[{ required: true }]}>
                <Input placeholder="1 ч 30 мин" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="calendar_id" label={t("slaConfig.calendar")}>
            <Select allowClear placeholder={t("slaConfig.noCalendar")}>
              {(calendars || []).filter((c: any) => c.is_active).map((c: any) => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="description" label={t("common.description")}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_active" label={t("common.active")} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">{t("common.save")}</Button>
            <Button onClick={() => { setModalOpen(false); setEditRule(null); }}>{t("common.cancel")}</Button>
          </Space>
        </Form>
      </Modal>

      <Modal title={editCal ? t("slaConfig.editCalendar") : t("slaConfig.createCalendar")} open={calModalOpen} onCancel={() => { setCalModalOpen(false); setEditCal(null); }} footer={null} width={480}>
        <Form form={calForm} layout="vertical" onFinish={saveCalendar} initialValues={{ timezone: "UTC", start_time: "09:00", end_time: "18:00", is_active: true }}>
          <Form.Item name="name" label={t("slaConfig.calendarName")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="timezone" label={t("slaConfig.timezone")}>
            <Input placeholder="UTC" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="start_time" label={t("slaConfig.startTime")}><Input placeholder="09:00" /></Form.Item></Col>
            <Col span={12}><Form.Item name="end_time" label={t("slaConfig.endTime")}><Input placeholder="18:00" /></Form.Item></Col>
          </Row>
          <Form.Item name="is_24x7" label={t("slaConfig.is24x7")} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="description" label={t("common.description")}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">{t("common.save")}</Button>
            <Button onClick={() => { setCalModalOpen(false); setEditCal(null); }}>{t("common.cancel")}</Button>
          </Space>
        </Form>
      </Modal>

      <Modal title={editEsc ? t("slaConfig.editEscalation") : t("slaConfig.createEscalation")} open={escModalOpen} onCancel={() => { setEscModalOpen(false); setEditEsc(null); }} footer={null} width={480}>
        <Form form={escForm} layout="vertical" onFinish={saveEscalation} initialValues={{ is_active: true, severity: "warning" }}>
          <Form.Item name="sla_rule_id" label={t("slaConfig.slaRule")} rules={[{ required: true }]}>
            <Select>
              {(rules || []).filter((r: any) => r.is_active).map((r: any) => (
                <Select.Option key={r.id} value={r.id}>{r.name} ({r.queue_pattern})</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="threshold_percent" label={t("slaConfig.threshold")} rules={[{ required: true }]}>
            <InputNumber min={1} max={100} style={{ width: 120 }} addonAfter="%" />
          </Form.Item>
          <Form.Item name="severity" label={t("slaConfig.severity")} rules={[{ required: true }]}>
            <Select>
              <Select.Option value="warning">{t("slaConfig.severity_warning")}</Select.Option>
              <Select.Option value="high">{t("slaConfig.severity_high")}</Select.Option>
              <Select.Option value="critical">{t("slaConfig.severity_critical")}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="notify_email" label={t("slaConfig.notifyEmail")}>
            <Input placeholder="admin@example.com" />
          </Form.Item>
          <Form.Item name="webhook_url" label={t("slaConfig.webhookUrl")}>
            <Input placeholder="https://hooks.example.com/alert" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">{t("common.save")}</Button>
            <Button onClick={() => { setEscModalOpen(false); setEditEsc(null); }}>{t("common.cancel")}</Button>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
