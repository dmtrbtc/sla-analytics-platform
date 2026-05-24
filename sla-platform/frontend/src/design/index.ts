/**
 * Public surface of the SLA Platform design system.
 *
 * Always import from "../design" (or `@/design`) — never reach into
 * sub-modules directly. This keeps the import graph flat and lets us
 * refactor internals without breaking page-level imports.
 */

export { slaTheme, theme } from "./theme";
export {
  slaEChartsTheme,
  SLA_ECHARTS_THEME_NAME,
} from "./echarts-theme";

export { KpiCard } from "./components/KpiCard";
export type { KpiAccent, KpiCardProps } from "./components/KpiCard";

export { HealthPip, severityFor } from "./components/HealthPip";
export type { HealthPipProps, HealthSeverity } from "./components/HealthPip";

export { MetricBar } from "./components/MetricBar";
export type { MetricBarProps } from "./components/MetricBar";

export { Sparkline } from "./components/Sparkline";
export type { SparklineProps } from "./components/Sparkline";

export { ScopeChips } from "./components/ScopeChips";
export type {
  ScopeChipItem,
  ScopeChipsProps,
} from "./components/ScopeChips";

export { SortableHeader } from "./components/SortableHeader";
export type {
  SortableHeaderProps,
  SortDirection,
} from "./components/SortableHeader";

export { DetailDrawer } from "./components/DetailDrawer";
export type {
  DetailDrawerKind,
  DetailDrawerProps,
} from "./components/DetailDrawer";

export { LivePill } from "./components/LivePill";
export type { LivePillProps } from "./components/LivePill";
