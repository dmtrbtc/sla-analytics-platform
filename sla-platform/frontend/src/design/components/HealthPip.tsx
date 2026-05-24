/**
 * HealthPip — 40px round badge containing a health score (0–100).
 *
 * Color is auto-derived from the value via the canonical severity scale:
 *   ≥ 92  → ok (green)
 *   ≥ 85  → warn (amber)
 *   ≥ 75  → high (orange)
 *   else  → crit (red)
 *
 * Visual reference: `.hp` in SLA Portal/portal.css.
 */

export type HealthSeverity = "ok" | "warn" | "high" | "crit";

export function severityFor(value: number): HealthSeverity {
  if (value >= 92) return "ok";
  if (value >= 85) return "warn";
  if (value >= 75) return "high";
  return "crit";
}

export interface HealthPipProps {
  /** Health value 0–100. */
  value: number;
  /** Override the auto-derived severity (rare — usually let the scale decide). */
  severity?: HealthSeverity;
  /** Pixel size — default 40 (canonical), pass `32` for compact tables. */
  size?: number;
}

export function HealthPip({ value, severity, size = 40 }: HealthPipProps) {
  const sev = severity ?? severityFor(value);
  const fontSize = size <= 32 ? 11 : 13;
  return (
    <span
      className={`sla-hp ${sev}`}
      style={{ width: size, height: size, fontSize }}
      role="img"
      aria-label={`Health ${value}`}
    >
      {Math.round(value)}
    </span>
  );
}

export default HealthPip;
