import { useState, useEffect } from "react";
import { Card, Row, Col, Statistic, Table, Tag, Spin, Progress, Alert } from "antd";
import {
  ArrowUpOutlined, ArrowDownOutlined,
  WarningOutlined, CheckCircleOutlined,
  TeamOutlined, ClockCircleOutlined,
} from "@ant-design/icons";
import { fetchExecutiveOverview } from "../api/analytics";

interface ExecutiveData {
  sla_health_score: number;
  total_metrics_analyzed: number;
  total_breaches: number;
  breach_rate_pct: number;
  avg_response_time_hours: number;
  avg_resolution_time_hours: number;
  tickets_at_risk: number;
  worst_queue?: string;
  key_insights: string[];
}

export default function DashboardExecutive() {
  const [data, setData] = useState<ExecutiveData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExecutiveOverview().then((res: any) => setData(res.summary)).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!data) return <Alert message="Нет данных" type="warning" />;

  const healthColor = data.sla_health_score >= 95 ? "#52c41a" : data.sla_health_score >= 80 ? "#faad14" : "#f5222d";

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]}>
        <Col span={24}><h2 style={{ fontSize: 22, color: "#1a1a2e", margin: 0 }}>Executive Command Center</h2></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="SLA Health Score"
              value={data.sla_health_score}
              suffix="%"
              valueStyle={{ color: healthColor, fontSize: 32 }}
              prefix={data.sla_health_score >= 80 ? <CheckCircleOutlined /> : <WarningOutlined />}
            />
            <Progress percent={data.sla_health_score} strokeColor={healthColor} showInfo={false} style={{ marginTop: 8 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Breach Rate" value={data.breach_rate_pct} suffix="%" valueStyle={{ color: data.breach_rate_pct > 10 ? "#f5222d" : "#52c41a" }} />
            <small style={{ color: "#888" }}>{data.total_breaches} нарушений из {data.total_metrics_analyzed} метрик</small>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Avg Response Time" value={data.avg_response_time_hours} suffix="h" prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Tickets at Risk" value={data.tickets_at_risk} valueStyle={{ color: data.tickets_at_risk > 10 ? "#f5222d" : "#52c41a" }} prefix={<TeamOutlined />} />
            {data.worst_queue && <small style={{ color: "#888" }}>Worst: {data.worst_queue}</small>}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="Key Insights">
            {data.key_insights.map((insight, i) => (
              <Alert key={i} message={insight} type={data.sla_health_score >= 80 ? "success" : "warning"} style={{ marginBottom: 8 }} showIcon />
            ))}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Operational Risk">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="Avg Resolution" value={data.avg_resolution_time_hours} suffix="h" />
              </Col>
              <Col span={12}>
                <Statistic title="Analytics Coverage" value={data.total_metrics_analyzed} suffix="metrics" />
              </Col>
            </Row>
            <Tag color={data.sla_health_score >= 90 ? "green" : data.sla_health_score >= 70 ? "orange" : "red"} style={{ marginTop: 16 }}>
              {data.sla_health_score >= 90 ? "Excellent" : data.sla_health_score >= 70 ? "Attention Needed" : "Critical"}
            </Tag>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
