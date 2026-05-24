import { type ReactNode } from "react";

export type KpiAccent = "" | "brand" | "react" | "resolve" | "crit";

export interface KpiCardProps {
  /** UPPERCASE-ish label rendered above the value. */
  label: string;
  /** Main number/string. Use pre-formatted text. */
  value: ReactNode;
  /** Optional icon shown in the top-right corner badge. */
  icon?: ReactNode;
  /** Accent — paints the icon badge in identity colors. Defaults to neutral. */
  accent?: KpiAccent;
  /** Bottom-left auxiliary text. */
  foot?: ReactNode;
  /**
   * Percent delta versus previous period (signed). When omitted the delta
   * pill is hidden. When `deltaBad` is true, growth (positive) is "bad" —
   * the pill becomes red on positive values.
   */
  delta?: number;
  deltaBad?: boolean;
}

/**
 * KpiCard — canonical SLA Portal KPI tile.
 *
 * Visual reference: `.kpi` in SLA Portal/portal.css.
 *
 * Layout (top→bottom):
 *   label                       icon badge
 *   VALUE (30/700, tnum)
 *   [delta]  foot text
 *
 * Color discipline:
 *   - The value itself stays neutral (--ink) unless `accent="crit"`,
 *     which paints the value red. Other accents only tint the icon.
 *   - Delta pill goes green/red based on direction + `deltaBad`.
 */
export function KpiCard({
  label,
  value,
  icon,
  accent = "",
  foot,
  delta,
  deltaBad,
}: KpiCardProps) {
  const cls =
    delta == null
      ? "flat"
      : deltaBad
        ? delta > 0
          ? "bad"
          : "good"
        : delta > 0
          ? "good"
          : "bad";

  return (
    <div className={`sla-kpi ${accent}`.trim()}>
      <div className="head">
        <span className="lab">{label}</span>
        {icon && <span className="ic">{icon}</span>}
      </div>
      <div className="val tnum">{value}</div>
      <div className="foot">
        {delta != null && (
          <span className={`delta ${cls}`}>
            {delta > 0 ? "▲" : delta < 0 ? "▼" : "—"}
            {Math.abs(delta)}%
          </span>
        )}
        {foot && <span>{foot}</span>}
      </div>
    </div>
  );
}

export default KpiCard;
