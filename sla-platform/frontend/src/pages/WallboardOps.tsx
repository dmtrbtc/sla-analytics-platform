import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Spin, Empty, Alert } from "antd";
import { operationsReviewApi, type ReviewOverviewResponse } from "../api/operationsReview";
import RuntimeErrorBoundary from "../components/safety/RuntimeErrorBoundary";
import "../design/v1-tokens.css";

const DOMAINS: Record<string, { label: string; queues: string[] }> = {
  workplace: {
    label: "Workplace · Veshki + Plaza",
    queues: ["MBR-137-Workplace-Veshki", "MBR-137-Workplace-Plaza"],
  },
  asset: {
    label: "Asset Management · Veshki + Plaza",
    queues: ["MBR-137-AssetManagement-Veshki", "MBR-137-AssetManagement-Plaza"],
  },
};

/**
 * Fullscreen operational wallboard — TV-safe, large typography, 30s
 * auto-refresh. Renders headlines from /operations/review/overview.
 * Hooks-safe: every hook called BEFORE any conditional return.
 */
function WallboardOpsInner() {
  const { domain } = useParams<{ domain: string }>();
  const cfg = domain && DOMAINS[domain] ? DOMAINS[domain] : null;

  const q = useQuery({
    queryKey: ["wallboard-ops", domain, cfg?.queues?.join(",") || ""],
    queryFn: () => operationsReviewApi.reviewOverview(cfg?.queues),
    refetchInterval: 30_000,
    enabled: !!cfg,
  });

  const d: ReviewOverviewResponse | undefined = q.data;

  const headline = useMemo(() => {
    if (!d) return null;
    return {
      hidden: d.hidden_breach_delta.hidden_breaches,
      lossH: Math.round(d.top_loss_queues.reduce((a, x) => a + x.total_wall_hours, 0)),
      noOwnerH: Math.round(d.parking_lots.reduce((a, x) => a + x.no_owner_hours, 0)),
      silent: d.silent_breaches.length,
      dying: d.dying_in_queue.length,
      topLoss: d.top_loss_queues[0],
      worstPotato: d.hot_potato[0],
    };
  }, [d]);

  // Branches AFTER hooks
  if (!cfg) {
    return <Alert
      type="error" showIcon
      message="Unknown domain"
      description="Используйте /wallboard-ops/workplace или /wallboard-ops/asset"
    />;
  }
  if (q.isLoading || q.isPending) {
    return <div style={{ height: "100vh", display: "grid", placeItems: "center", background: "#0a0e1a" }}>
      <Spin size="large" />
    </div>;
  }
  if (q.isError) {
    return <Alert type="error" showIcon message="Wallboard data error" />;
  }
  if (!d || !headline) return <Empty />;

  return (
    <div
      style={{
        background: "#0a0e1a",
        color: "#f8fafc",
        minHeight: "100vh",
        padding: "32px 56px",
        fontFamily: "Inter, system-ui, sans-serif",
        fontVariantNumeric: "tabular-nums",
      }}
    >
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "baseline",
        marginBottom: 24, borderBottom: "1px solid #1e293b", paddingBottom: 16,
      }}>
        <div>
          <div style={{ fontSize: 14, color: "#94a3b8", letterSpacing: "0.1em", textTransform: "uppercase" }}>
            SLA Operations Wallboard
          </div>
          <div style={{ fontSize: 38, fontWeight: 600, marginTop: 4 }}>
            {cfg.label}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>auto-refresh 30s</div>
          <div style={{ fontSize: 14, color: "#cbd5e1" }}>{new Date().toLocaleString("ru-RU")}</div>
        </div>
      </div>

      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 28, marginBottom: 36,
      }}>
        {[
          { label: "Часов в SLA-нагрузке", value: headline.lossH.toLocaleString("ru-RU"), color: "#f8fafc" },
          { label: "Без владельца, часов",  value: headline.noOwnerH.toLocaleString("ru-RU"), color: "#fbbf24" },
          { label: "Скрытых нарушений",     value: String(headline.hidden), color: "#fca5a5" },
          { label: "Dying в очереди",       value: String(headline.dying), color: "#f87171" },
        ].map(t => (
          <div key={t.label} style={{
            background: "#111827", padding: "26px 28px",
            border: "1px solid #1f2937", borderRadius: 10,
          }}>
            <div style={{ fontSize: 12, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {t.label}
            </div>
            <div style={{ fontSize: 64, fontWeight: 700, color: t.color, lineHeight: 1.05, marginTop: 10 }}>
              {t.value}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28 }}>
        <div style={{ background: "#111827", padding: "26px 28px", borderRadius: 10, border: "1px solid #1f2937" }}>
          <div style={{ fontSize: 12, color: "#94a3b8", textTransform: "uppercase" }}>
            Самая дорогая очередь
          </div>
          <div style={{ fontSize: 28, fontWeight: 600, marginTop: 8 }}>
            {headline.topLoss?.queue ?? "—"}
          </div>
          <div style={{ fontSize: 18, color: "#cbd5e1", marginTop: 6 }}>
            {headline.topLoss
              ? `${headline.topLoss.total_wall_hours.toLocaleString("ru-RU")} ч · ${headline.topLoss.share_of_total_pct.toFixed(1)}% от scope`
              : "—"}
          </div>
        </div>

        <div style={{ background: "#111827", padding: "26px 28px", borderRadius: 10, border: "1px solid #1f2937" }}>
          <div style={{ fontSize: 12, color: "#94a3b8", textTransform: "uppercase" }}>
            Худший hot-potato тикет
          </div>
          {headline.worstPotato ? (
            <>
              <div style={{ fontSize: 24, fontFamily: "JetBrains Mono, monospace", marginTop: 8 }}>
                #{headline.worstPotato.ticket_number}
              </div>
              <div style={{ fontSize: 16, color: "#cbd5e1", marginTop: 6 }}>
                {headline.worstPotato.moves} перемещений · {headline.worstPotato.owner_changes} смены владельца
              </div>
            </>
          ) : <div style={{ color: "#64748b" }}>—</div>}
        </div>
      </div>
    </div>
  );
}

export default function WallboardOps() {
  return (
    <RuntimeErrorBoundary label="wallboard-ops">
      <WallboardOpsInner />
    </RuntimeErrorBoundary>
  );
}
