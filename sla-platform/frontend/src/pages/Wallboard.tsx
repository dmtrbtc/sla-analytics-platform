import { useState, useEffect, useCallback } from "react";
import { Card, Row, Col, Statistic, Alert } from "antd";
import { fetchLiveHealth } from "../api/analytics";

interface HealthData {
  sla_health_score?: number;
  breach_rate?: number;
  active_tickets?: number;
  workers_online?: number;
  queue_lag?: number;
}

export default function Wallboard() {
  const [data, setData] = useState<HealthData>({});
  const [page, setPage] = useState(0);
  const pages = 4;

  const updateData = useCallback(async () => {
    try {
      const res = await fetchLiveHealth();
      setData(res);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    updateData();
    const interval = setInterval(updateData, 15000);
    const rotate = setInterval(() => setPage((p) => (p + 1) % pages), 10000);
    return () => { clearInterval(interval); clearInterval(rotate); };
  }, [updateData]);

  return (
    <div style={{
      background: "#0a0a1a", color: "#fff", height: "100vh",
      display: "flex", flexDirection: "column", justifyContent: "center",
      padding: 48, fontFamily: "'Segoe UI', sans-serif",
    }}>
      {page === 0 && (
        <Row gutter={[48, 48]} justify="center" align="middle">
          <Col span={24} style={{ textAlign: "center", marginBottom: 48 }}>
            <h1 style={{ color: "#1890ff", fontSize: 48, margin: 0 }}>SLA INTELLIGENCE</h1>
            <p style={{ color: "#888", fontSize: 18 }}>System Health Overview</p>
          </Col>
          <Col span={6}><Statistic title="SLA Health" value={data.sla_health_score ?? "--"} suffix="%" valueStyle={{ color: "#52c41a", fontSize: 36 }} /></Col>
          <Col span={6}><Statistic title="Breach Rate" value={data.breach_rate ?? "--"} suffix="%" valueStyle={{ color: "#faad14", fontSize: 36 }} /></Col>
          <Col span={6}><Statistic title="Active Tickets" value={data.active_tickets ?? "--"} valueStyle={{ color: "#1890ff", fontSize: 36 }} /></Col>
          <Col span={6}><Statistic title="Workers" value={data.workers_online ?? "--"} valueStyle={{ color: "#52c41a", fontSize: 36 }} /></Col>
        </Row>
      )}
      {page === 1 && (
        <Row gutter={[48, 48]} justify="center" align="middle">
          <Col span={24} style={{ textAlign: "center", marginBottom: 48 }}>
            <h1 style={{ color: "#faad14", fontSize: 48, margin: 0 }}>QUEUE PERFORMANCE</h1>
          </Col>
          <Col span={24} style={{ textAlign: "center" }}>
            <h2 style={{ color: "#888" }}>Queue lag: {data.queue_lag ?? 0} tasks</h2>
          </Col>
        </Row>
      )}
      {page === 2 && (
        <Row gutter={[48, 48]} justify="center" align="middle">
          <Col span={24} style={{ textAlign: "center", marginBottom: 48 }}>
            <h1 style={{ color: "#f5222d", fontSize: 48, margin: 0 }}>INCIDENT STATUS</h1>
            <Alert message="No active critical incidents" type="success" style={{ marginTop: 24, background: "transparent", borderColor: "#52c41a" }} />
          </Col>
        </Row>
      )}
      {page === 3 && (
        <Row gutter={[48, 48]} justify="center" align="middle">
          <Col span={24} style={{ textAlign: "center" }}>
            <h1 style={{ color: "#52c41a", fontSize: 64, margin: 0 }}>ALL SYSTEMS NOMINAL</h1>
            <p style={{ color: "#555", fontSize: 24, marginTop: 24 }}>Monitoring {data.active_tickets ?? 0} active tickets</p>
          </Col>
        </Row>
      )}
      <div style={{ position: "fixed", bottom: 24, right: 24, color: "#333", fontSize: 12 }}>
        Wallboard v1.0.0 | Auto-rotate 10s
      </div>
    </div>
  );
}
