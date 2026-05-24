import { Drawer } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

/**
 * DetailDrawer — 640px right-side drawer for drill-down (queue / ticket).
 *
 * Wraps AntD `<Drawer>` with the SLA Portal header pattern:
 *   - crumb (uppercase tiny label)
 *   - h3 main title
 *   - meta row (chips, secondary text)
 *
 * The body is a flex column with 20px gap — children typically render
 * `.sla-metric-row`, AntD `<Card>` instances, and action button rows.
 *
 * Visual reference: `.drawer-h` / `.drawer-b` in SLA Portal/portal.css.
 */

export type DetailDrawerKind = "queue" | "ticket";

export interface DetailDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Tiny uppercase crumb above the title — e.g. "Очередь · 24×7". */
  crumb?: ReactNode;
  /** Main h3 title. */
  title: ReactNode;
  /** Optional secondary meta row under the title (chips, owner counts...). */
  meta?: ReactNode;
  /** Kind for semantics (drives the data-attr; useful for analytics). */
  kind?: DetailDrawerKind;
  /** Drawer body. */
  children: ReactNode;
}

export function DetailDrawer({
  open,
  onClose,
  crumb,
  title,
  meta,
  kind,
  children,
}: DetailDrawerProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      placement="right"
      width={640}
      closable={false}
      data-drawer-kind={kind}
      // We render our own header to match SLA Portal exactly.
      title={null}
      bodyStyle={{
        padding: 0,
        background: "var(--bg)",
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
      headerStyle={{ display: "none" }}
    >
      <div
        className="sla-drawer-h"
        style={{
          padding: "18px 24px",
          background: "var(--surface)",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          {crumb && <div className="crumb">{crumb}</div>}
          <h3>{title}</h3>
          {meta && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 8,
                flexWrap: "wrap",
              }}
            >
              {meta}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          style={{
            width: 30,
            height: 30,
            borderRadius: 6,
            border: "1px solid var(--line)",
            background: "var(--surface)",
            color: "var(--ink-3)",
            cursor: "pointer",
            display: "grid",
            placeItems: "center",
            padding: 0,
            flexShrink: 0,
          }}
        >
          <CloseOutlined style={{ fontSize: 12 }} />
        </button>
      </div>
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "20px 24px 32px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {children}
      </div>
    </Drawer>
  );
}

export default DetailDrawer;
