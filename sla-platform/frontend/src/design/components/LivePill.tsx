import type { ReactNode } from "react";

/**
 * LivePill — small green pulsing pill that signals live data.
 *
 * Sits inside the page header next to the H1. The pulse is pure CSS
 * (`@keyframes sla-pulse` in `tokens.css`). Pass a custom `label` to vary
 * the text; default is "live · обновлено только что".
 *
 * Visual reference: `.live-pill` in SLA Portal/portal.css.
 */

export interface LivePillProps {
  /** Text shown next to the pulsing dot. Already-translated. */
  label?: ReactNode;
  /** When false, the pulse stops and the pill switches to a muted color. */
  live?: boolean;
}

export function LivePill({ label = "live", live = true }: LivePillProps) {
  if (!live) {
    return (
      <span
        className="sla-live-pill"
        style={{
          background: "var(--surface-3)",
          color: "var(--ink-3)",
        }}
      >
        {label}
      </span>
    );
  }
  return <span className="sla-live-pill">{label}</span>;
}

export default LivePill;
