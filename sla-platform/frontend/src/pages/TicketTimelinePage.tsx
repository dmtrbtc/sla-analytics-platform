import { useParams } from "react-router-dom";
import { Typography, Card } from "antd";
import ForensicTimelineVisual from "../components/forensics/ForensicTimelineVisual";
import RuntimeErrorBoundary from "../components/safety/RuntimeErrorBoundary";
import "../design/v1-tokens.css";

const { Title, Text } = Typography;

/**
 * Per-ticket forensic timeline page. URL: /tickets/{id}/timeline
 *
 * Hooks-safe: only one hook (useParams), no early-return-before-hook
 * patterns. Wrapped by parent in RuntimeErrorBoundary.
 */
function TicketTimelinePageInner() {
  const { id } = useParams<{ id: string }>();
  const ticketId = Number(id);

  if (!Number.isFinite(ticketId) || ticketId <= 0) {
    return <Text type="danger">Invalid ticket id</Text>;
  }

  return (
    <div className="v1" style={{ background: "var(--v1-bg)", minHeight: "100vh", padding: 24 }}>
      <Title level={3} style={{ margin: 0, color: "var(--v1-text)" }}>
        Forensic Timeline · Ticket {ticketId}
      </Title>
      <Text style={{ color: "var(--v1-text-3)" }}>
        Полный путь тикета по очередям. Каждый сегмент пропорционален wall-clock минутам.
        Hover — детали сегмента (owner, response/resolution loss, no-owner, pending).
      </Text>

      <Card
        bordered={false}
        style={{
          marginTop: 18,
          background: "var(--v1-surface)",
          border: "1px solid var(--v1-border)",
          borderRadius: "var(--v1-radius-lg)",
        }}
      >
        <ForensicTimelineVisual
          ticketId={ticketId}
          responseTargetSec={1800}
          resolutionTargetSec={28800}
          height={64}
        />
      </Card>
    </div>
  );
}

export default function TicketTimelinePage() {
  return (
    <RuntimeErrorBoundary label="timeline ticket">
      <TicketTimelinePageInner />
    </RuntimeErrorBoundary>
  );
}
