import type { HealthSeverity } from "./HealthPip";
import { severityFor } from "./HealthPip";

/**
 * MetricBar — narrow value + 4px progress bar for one metric (Реакция или Решение).
 *
 * The bar is filled to `pct` percent using the identity color of the chosen
 * metric. If `pct` triggers warn/high/crit severity, the value label is
 * tinted accordingly; the bar itself remains in identity color UNLESS
 * `severity === "crit"`, in which case the bar turns red (operationally
 * "this metric is breaching, not just degrading").
 *
 * Visual reference: `.bar-cell` in SLA Portal/portal.css.
 */

export interface MetricBarProps {
  /** Identity — "reaction" = orange, "resolution" = violet. */
  kind: "reaction" | "resolution";
  /** Percentage 0–100. */
  pct: number;
  /** Override the auto-derived severity (rare). */
  severity?: HealthSeverity;
  /** Hide the numeric value above the bar. */
  hideValue?: boolean;
}

export function MetricBar({ kind, pct, severity, hideValue }: MetricBarProps) {
  const sev = severity ?? severityFor(pct);
  const valueCls =
    sev === "crit" ? "crit" : sev === "warn" ? "warn" : sev === "high" ? "high" : "";
  // Bar color goes red only on breach; warn/high stays identity color.
  const barCellCls = `sla-bar-cell ${kind} ${sev === "crit" ? "crit" : ""}`.trim();

  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className={barCellCls}>
      {!hideValue && (
        <span className={`v ${valueCls}`.trim()}>{clamped.toFixed(1)}%</span>
      )}
      <div className="bar" aria-hidden>
        <i style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

export default MetricBar;
