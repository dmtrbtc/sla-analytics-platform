import type { ReactNode } from "react";

/**
 * SortableHeader — column-header wrapper that renders ↑ ↓ ↕ arrow indicators
 * matching the SLA Portal look.
 *
 * It's intentionally framework-agnostic: it does NOT plug directly into AntD
 * Table's `sorter`. Use it inside a `column.title` render function so you
 * control the underlying state machine (single-column sort with toggle).
 *
 * Pattern:
 *
 *   columns={[
 *     {
 *       title: (
 *         <SortableHeader
 *           label={t("slaPortal.columns.queue")}
 *           active={sort.k === "name"}
 *           direction={sort.d}
 *         />
 *       ),
 *       onHeaderCell: () => ({ onClick: () => onSort("name") }),
 *       ...
 *     },
 *   ]}
 *
 * Visual reference: `.qtbl thead th.sortable` in SLA Portal/portal.css.
 */

export type SortDirection = "asc" | "desc";

export interface SortableHeaderProps {
  /** Column label (will already be t("...")). */
  label: ReactNode;
  /** Whether THIS column is the currently sorted one. */
  active: boolean;
  /** Sort direction when `active` is true (ignored otherwise). */
  direction?: SortDirection;
  /** Right-align the label (numeric columns). */
  numeric?: boolean;
}

export function SortableHeader({
  label,
  active,
  direction,
  numeric,
}: SortableHeaderProps) {
  const arrow = !active ? "↕" : direction === "desc" ? "↓" : "↑";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        cursor: "pointer",
        userSelect: "none",
        color: active ? "var(--brand)" : "var(--ink-3)",
        fontWeight: 600,
        fontSize: 11,
        textTransform: "uppercase",
        letterSpacing: 0.5,
        justifyContent: numeric ? "flex-end" : "flex-start",
        width: numeric ? "100%" : undefined,
      }}
    >
      {label}
      <span className={`sla-sort-arr ${active ? "active" : ""}`.trim()}>
        {arrow}
      </span>
    </span>
  );
}

export default SortableHeader;
