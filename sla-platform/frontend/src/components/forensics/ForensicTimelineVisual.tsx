import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Spin, Empty, Alert, Typography, Tag, Tooltip } from "antd";
import { forensicTimelineApi, type TimelineSegment } from "../../api/forensicTimeline";
import RuntimeErrorBoundary from "../safety/RuntimeErrorBoundary";
import "../../design/v1-tokens.css";

const { Text } = Typography;

interface Props {
  ticketId: number;
  responseTargetSec?: number;
  resolutionTargetSec?: number;
  height?: number;
}

const COLORS = [
  "#2563eb", "#16a34a", "#d97706", "#dc2626", "#8b5cf6",
  "#0891b2", "#65a30d", "#c026d3", "#0284c7", "#ea580c",
  "#475569", "#7c3aed",
];

function fmtMin(min: number): string {
  if (!Number.isFinite(min) || min <= 0) return "0м";
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h >= 24) return `${Math.floor(h / 24)}д ${h % 24}ч`;
  if (h > 0) return m ? `${h}ч ${m}м` : `${h}ч`;
  return `${m}м`;
}

/**
 * SVG-based queue timeline strip. No chart library — single horizontal
 * track of colored segments proportional to wall minutes, with overlays:
 *   - first-response marker (gold pin at first_response_at)
 *   - breach marker         (red pin at created+resolution_target)
 *   - paused segments       (orange diagonal stripes)
 *   - no-owner segments     (gray hatched)
 *
 * Hooks-safe: useQuery + useMemo always run before any conditional return.
 * Wrapped by parent in RuntimeErrorBoundary.
 */
function ForensicTimelineVisualInner({
  ticketId,
  responseTargetSec = 1800,
  resolutionTargetSec = 28800,
  height = 56,
}: Props) {
  // ── ALL HOOKS FIRST ────────────────────────────────────────────
  const q = useQuery({
    queryKey: ["forensic-timeline", ticketId, responseTargetSec, resolutionTargetSec],
    queryFn: () => forensicTimelineApi.forTicket(ticketId, responseTargetSec, resolutionTargetSec),
    staleTime: 30_000,
  });

  const d = q.data;

  const queueColorMap = useMemo(() => {
    const map = new Map<string, string>();
    const segs = d?.segments ?? [];
    let i = 0;
    for (const s of segs) {
      if (!map.has(s.queue_name)) {
        map.set(s.queue_name, COLORS[i % COLORS.length]);
        i++;
      }
    }
    return map;
  }, [d?.segments]);

  const totalMin = useMemo(
    () => Math.max(1, (d?.segments ?? []).reduce((a, s) => a + s.minutes_in_queue, 0)),
    [d?.segments],
  );

  // ── Branches now safe ──────────────────────────────────────────
  if (q.isLoading || q.isPending) {
    return <div style={{ padding: 16, textAlign: "center" }}><Spin size="small" /></div>;
  }
  if (q.isError) {
    const message = (q.error as Error | undefined)?.message ?? "Ошибка";
    return <Alert type="error" showIcon message="Не удалось загрузить timeline" description={message} />;
  }
  if (!d) return <Empty description="Нет данных" />;

  const segs = d.segments;
  if (!segs.length) {
    return <Empty description="Тикет не имеет queue_periods" />;
  }

  // Build the strip
  const widthPct = (m: number) => (m / totalMin) * 100;

  return (
    <div className="v1" style={{ fontFamily: "var(--v1-font)" }}>
      {/* HEADER LINE */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8, alignItems: "baseline" }}>
        <Text strong>#{d.ticket.ticket_number}</Text>
        <Tag color={d.ticket.is_closed ? "default" : "blue"}>
          {d.ticket.is_closed ? "закрыт" : "открыт"}
        </Tag>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {segs.length} сегментов · {fmtMin(totalMin)} wall-clock
        </Text>
        {d.summary.first_response_rule_check !== "ok" && (
          <Tag color="red">FR-rule: {d.summary.first_response_rule_check}</Tag>
        )}
        {d.summary.breach_queue && (
          <Tag color="red">breach в: {d.summary.breach_queue}</Tag>
        )}
      </div>

      {/* TIMELINE STRIP */}
      <div className="v1-timeline" style={{ height, position: "relative", display: "flex" }}>
        {segs.map((s: TimelineSegment, i: number) => {
          const w = widthPct(s.minutes_in_queue);
          const color = queueColorMap.get(s.queue_name) || "#94a3b8";
          let className = "seg ok";
          if (s.breach_inside_segment) className = "seg breach";
          else if (s.no_owner_minutes > 0 && s.no_owner_minutes >= s.minutes_in_queue * 0.8) className = "seg no-owner";
          else if (s.paused) className = "seg paused";
          const bg = className === "seg ok" ? color : undefined;
          return (
            <Tooltip
              key={`${s.queue_name}-${i}`}
              title={
                <div style={{ fontSize: 12, lineHeight: 1.5 }}>
                  <div><b>{s.queue_name}</b></div>
                  <div>wall: {fmtMin(s.minutes_in_queue)}</div>
                  <div>resp-loss: {fmtMin(s.response_loss_minutes)}</div>
                  <div>resol-loss: {fmtMin(s.resolution_loss_minutes)}</div>
                  <div>no-owner: {fmtMin(s.no_owner_minutes)}</div>
                  {s.paused && <div style={{ color: "#fbbf24" }}>⏸ pending</div>}
                  {s.breach_inside_segment && <div style={{ color: "#fca5a5" }}>⚠ deadline crossed here</div>}
                  <div style={{ marginTop: 4, opacity: 0.7 }}>
                    {s.entered_at?.replace("T", " ").slice(0, 16) ?? "?"} →{" "}
                    {s.exited_at?.replace("T", " ").slice(0, 16) ?? "now"}
                  </div>
                  {(s.owners_during || []).map((o, oi) => (
                    <div key={oi}>
                      {o.is_system ? "—" : o.owner}: {Math.round(o.seconds / 60)}м
                    </div>
                  ))}
                </div>
              }
            >
              <div
                className={className}
                style={{
                  width: `${w}%`,
                  background: bg,
                  minWidth: 2,
                  fontSize: 10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                  whiteSpace: "nowrap",
                }}
              >
                {w >= 6 ? s.queue_name.replace("MBR-137-", "").slice(0, 14) : ""}
              </div>
            </Tooltip>
          );
        })}
      </div>

      {/* SUMMARY ROW */}
      <div style={{ marginTop: 10, display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12 }}>
        <Text type="secondary">
          first-response в: <b>{d.summary.response_passed_in_queue ?? "не доставлен"}</b>
        </Text>
        <Text type="secondary">
          top loss: <b>{d.summary.top_loss_queue ?? "—"}</b> ({fmtMin(d.summary.top_loss_minutes)})
        </Text>
        {d.summary.bounces?.length > 0 && (
          <Text type="secondary">
            bounces:{" "}
            {d.summary.bounces.slice(0, 3).map(b => `${b.queue.replace("MBR-137-", "")}×${b.visits}`).join(", ")}
          </Text>
        )}
      </div>
    </div>
  );
}

export default function ForensicTimelineVisual(props: Props) {
  return (
    <RuntimeErrorBoundary label={`timeline тикета ${props.ticketId}`} resetKey={props.ticketId}>
      <ForensicTimelineVisualInner {...props} />
    </RuntimeErrorBoundary>
  );
}
