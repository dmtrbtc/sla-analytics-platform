/* Enterprise Design System V3 — composite style tokens */
export { palette, darkPalette } from "./colors";
export { typography } from "./typography";
export { spacing, radius, breakpoint, layout } from "./spacing";
export { shadows, darkShadows } from "./shadows";
export { chartTheme, darkChartTheme } from "./chartTheme";
export { tableTheme, darkTableTheme } from "./tableTheme";

import type { CSSProperties } from "react";
import { palette } from "./colors";
import { typography } from "./typography";
import { shadows } from "./shadows";
import { radius, spacing } from "./spacing";

export const cardStyle: CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.border}`,
  borderRadius: radius.lg,
  boxShadow: shadows.card,
};

export const cardHeaderStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.sm,
  fontWeight: typography.weight.semibold,
  color: palette.text.secondary,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  padding: `${spacing[3]} ${spacing[4]}`,
  borderBottom: `1px solid ${palette.borderLight}`,
};

export const kpiValueStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.heading.kpi.size,
  fontWeight: typography.weight.bold as number,
  color: palette.text.primary,
  lineHeight: typography.heading.kpi.lineHeight,
  letterSpacing: typography.heading.kpi.letterSpacing,
};

export const kpiLabelStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.xs,
  fontWeight: typography.weight.semibold as number,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

export const pageHeaderStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.heading.h2.size,
  fontWeight: typography.weight.semibold as number,
  color: palette.text.primary,
  letterSpacing: typography.heading.h2.letterSpacing,
  lineHeight: typography.heading.h2.lineHeight,
};

export const toolbarStyle: CSSProperties = {
  background: palette.white,
  borderBottom: `1px solid ${palette.borderLight}`,
  padding: `${spacing[2.5]} ${spacing[4]}`,
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: spacing[3],
};

export const sectionTitle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.xs,
  fontWeight: typography.weight.semibold as number,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  marginBottom: spacing[2],
};

export const kpiCardStyle: CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.border}`,
  borderRadius: radius.lg,
  boxShadow: shadows.kpi,
  padding: spacing[4],
  display: "flex",
  flexDirection: "column",
  gap: spacing[1],
  position: "relative",
  overflow: "hidden",
  transition: "box-shadow 0.15s ease, border-color 0.15s ease",
};

export const statusStrip: CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  height: "3px",
  borderRadius: `${radius.lg} ${radius.lg} 0 0`,
};
