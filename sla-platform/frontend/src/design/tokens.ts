export { palette } from "./colors";
export { typography } from "./typography";
export { spacing, radius, breakpoint, layout } from "./spacing";
export { shadows } from "./shadows";
export { chartTheme } from "./chartTheme";
export { tableTheme } from "./tableTheme";

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
  letterSpacing: "0.04em",
  padding: `${spacing[3]} ${spacing[4]}`,
  borderBottom: `1px solid ${palette.borderLight}`,
};

export const kpiValueStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size["4xl"],
  fontWeight: typography.weight.bold,
  color: palette.text.primary,
  lineHeight: "1.2",
};

export const kpiLabelStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size.xs,
  fontWeight: typography.weight.semibold,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

export const pageHeaderStyle: CSSProperties = {
  fontFamily: typography.fontFamily,
  fontSize: typography.size["2xl"],
  fontWeight: typography.weight.semibold,
  color: palette.text.primary,
  letterSpacing: "-0.02em",
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
  fontWeight: typography.weight.semibold,
  color: palette.text.tertiary,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  marginBottom: spacing[2],
};
