import { useEffect, useState } from "react";
import {
  Typography, Card, Row, Col, Statistic, Table, Tag, Spin, Alert, Space, Descriptions, Badge,
} from "antd";
import {
  CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined, ApiOutlined,
  TeamOutlined, DashboardOutlined, CloudServerOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import client from "../api/client";

interface HealthStatus {
  status: string;
  version: string;
  services: Record<string, string>;
}

export default function AdminDiagnostics() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [metrics, setMetrics] = useState<string>("");

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const resp = await fetch("/health");
        const data = await resp.json();
        setHealth(data);
      } catch {
        // ignore
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const resp = await fetch("/metrics");
        const text = await resp.text();
        setMetrics(text);
      } catch {
        // ignore
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000);
    return () => clearInterval(interval);
  }, []);

  const parseMetric = (name: string): number => {
    const match = metrics.match(new RegExp(`${name}\\s+([\\d.]+)`));
    return match ? parseFloat(match[1]) : 0;
  };

  const parseMetricWithLabels = (name: string): { labels: string; value: number }[] => {
    const results: { labels: string; value: number }[] = [];
    const regex = new RegExp(`${name}\\{([^}]+)\\}\\s+([\\d.]+)`, "g");
    let m;
    while ((m = regex.exec(metrics)) !== null) {
      results.push({ labels: m[1], value: parseFloat(m[2]) });
    }
    return results;
  };

  const dbQueries = parseMetric("db_query_duration_seconds_count");
  const httpRequests = parseMetric("http_requests_total");
  const activeImports = parseMetric("active_imports");
  const wsActive = parseMetric("ws_connections_active");
  const slaMetrics = parseMetric("sla_metrics_processed_total");
  const celeryTasks = parseMetric("celery_tasks_total");
  const errorCount = parseMetric("app_errors_total");
  const pythonMem = parseMetric("process_resident_memory_bytes") / (1024 * 1024);

  const queueBacklogs = parseMetricWithLabels("queue_backlog");

  const serviceStatus = (name: string) => {
    const s = health?.services?.[name];
    if (!s) return <Tag icon={<CloseCircleOutlined />} color="default">Unknown</Tag>;
    if (s === "healthy" || s.startsWith("healthy")) return <Tag icon={<CheckCircleOutlined />} color="success">Healthy</Tag>;
    return <Tag icon={<CloseCircleOutlined />} color="error">{s}</Tag>;
  };

  return (
    <div>
      <Typography.Title level={4}>Системная диагностика</Typography.Title>

      {health?.status !== "healthy" && health && (
        <Alert type="warning" showIcon message={`Статус системы: ${health.status}`} description={JSON.stringify(health.services)} style={{ marginBottom: 16 }} />
      )}

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={12}>
          <Card title={<><CloudServerOutlined /> Состояние сервисов</>} size="small">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label={<><DatabaseOutlined /> База данных</>}>{serviceStatus("database")}</Descriptions.Item>
              <Descriptions.Item label={<><ApiOutlined /> Redis</>}>{serviceStatus("redis")}</Descriptions.Item>
              <Descriptions.Item label={<><TeamOutlined /> WebSocket</>}>{serviceStatus("websocket")}</Descriptions.Item>
              <Descriptions.Item label="Приложение">{serviceStatus("app")}</Descriptions.Item>
              <Descriptions.Item label="Версия">{health?.version || "—"}</Descriptions.Item>
              <Descriptions.Item label="Общий статус">
                <Badge status={health?.status === "healthy" ? "success" : "error"} text={health?.status === "healthy" ? "Здоров" : "Деградирован"} />
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={<><DashboardOutlined /> Метрики производительности</>} size="small">
            <Row gutter={[8, 8]}>
              <Col span={12}><Statistic title="HTTP запросов" value={httpRequests} prefix={<ApiOutlined />} /></Col>
              <Col span={12}><Statistic title="Запросов к БД" value={dbQueries} prefix={<DatabaseOutlined />} /></Col>
              <Col span={12}><Statistic title="WebSocket клиентов" value={wsActive} prefix={<TeamOutlined />} /></Col>
              <Col span={12}><Statistic title="Активных импортов" value={activeImports} prefix={<CloudServerOutlined />} /></Col>
              <Col span={12}><Statistic title="SLA метрик обработано" value={slaMetrics} prefix={<DashboardOutlined />} /></Col>
              <Col span={12}><Statistic title="Ошибок" value={errorCount} valueStyle={{ color: errorCount > 0 ? "#ff4d4f" : undefined }} prefix={<CloseCircleOutlined />} /></Col>
              <Col span={12}><Statistic title="Celery задач" value={celeryTasks} prefix={<CloudServerOutlined />} /></Col>
              <Col span={12}><Statistic title="Память Python" value={`${pythonMem.toFixed(0)} MB`} prefix={<DatabaseOutlined />} /></Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24}>
          <Card title="Очереди с бэклогом" size="small">
            {queueBacklogs.length > 0 ? (
              <Table
                dataSource={queueBacklogs.filter((q) => q.value > 0).sort((a, b) => b.value - a.value).slice(0, 20)}
                columns={[
                  { title: "Очередь", dataIndex: "labels", key: "queue", render: (v: string) => v.replace("queue_name=", "").replace(/"/g, "") },
                  { title: "Бэклог", dataIndex: "value", key: "value", render: (v: number) => <Tag color={v > 50 ? "red" : v > 20 ? "orange" : "green"}>{v}</Tag> },
                ]}
                rowKey="labels"
                size="small"
                pagination={false}
              />
            ) : (
              <Typography.Text type="secondary">Нет данных по бэклогам</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={12}>
          <Card title="Prometheus метрики (сырые)" size="small" style={{ maxHeight: 400, overflow: "auto" }}>
            <pre style={{ fontSize: 11, lineHeight: 1.4 }}>
              {metrics.slice(0, 5000) || "Загрузка..."}
            </pre>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Конфигурация" size="small">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Redis хост">redis:6379</Descriptions.Item>
              <Descriptions.Item label="Пул соединений async">20/30 (size/overflow)</Descriptions.Item>
              <Descriptions.Item label="Пул соединений sync">10/20 (size/overflow)</Descriptions.Item>
              <Descriptions.Item label="Auto-refresh интервал">30-60s</Descriptions.Item>
              <Descriptions.Item label="WebSocket heartbeat">30s</Descriptions.Item>
              <Descriptions.Item label="Кол-во миграций">15</Descriptions.Item>
              <Descriptions.Item label="Последняя миграция">015_enterprise_idx</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
