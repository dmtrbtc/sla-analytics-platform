import type { ReactNode } from "react";

/**
 * ScopeChips — segmented pill filter used in topbar (canonical pattern).
 *
 * The active chip is filled with `var(--ink)` (dark pill on white).
 * Inactive chips are outlined. Each chip can show a `count` badge.
 *
 * Visual reference: `.chip` group in SLA Portal/portal.css.
 *
 * NOTE: This is a controlled component. The parent owns `value` and reacts
 * to `onChange`. Use `useTimeScope().toParams()` separately for scope-time;
 * this widget is for orthogonal categorical filters (segment, calendar).
 */

export interface ScopeChipItem<V extends string = string> {
  value: V;
  label: ReactNode;
  count?: number;
}

export interface ScopeChipsProps<V extends string = string> {
  value: V;
  onChange: (next: V) => void;
  items: ScopeChipItem<V>[];
  /** Hide count badges (for compact mode). */
  hideCounts?: boolean;
  /** aria-label for the chip group, e.g. "Сегмент" / "Сегмент". */
  ariaLabel?: string;
}

export function ScopeChips<V extends string = string>({
  value,
  onChange,
  items,
  hideCounts,
  ariaLabel,
}: ScopeChipsProps<V>) {
  return (
    <div className="sla-chips" role="radiogroup" aria-label={ariaLabel}>
      {items.map((it) => {
        const active = it.value === value;
        return (
          <button
            type="button"
            key={String(it.value)}
            className={`sla-chip ${active ? "active" : ""}`.trim()}
            onClick={() => onChange(it.value)}
            role="radio"
            aria-checked={active}
          >
            {it.label}
            {!hideCounts && it.count != null && (
              <span className="count">{it.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default ScopeChips;
