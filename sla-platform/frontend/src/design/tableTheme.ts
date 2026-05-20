/* Enterprise Design System V3 — Ant Design table theme overrides (light + dark) */
import { palette, darkPalette } from "./colors";
import { typography } from "./typography";

const base = {
  fontSize: typography.size.xs,
  fontWeight: 600,
  textTransform: "uppercase" as const,
  letterSpacing: "0.04em",
};

export const tableTheme = {
  header: { background: palette.page, color: palette.text.secondary, ...base },
  body: { fontSize: typography.size.base, color: palette.text.primary },
  row: { hoverBackground: palette.brand[50], selectedBackground: palette.brand[100], height: "44px" },
  pagination: { fontSize: typography.size.sm },
  radius: "6px",
};

export const darkTableTheme = {
  header: { background: darkPalette.page, color: darkPalette.text.secondary, ...base },
  body: { fontSize: typography.size.base, color: darkPalette.text.primary },
  row: { hoverBackground: darkPalette.brand[50], selectedBackground: darkPalette.brand[100], height: "44px" },
  pagination: { fontSize: typography.size.sm },
  radius: "6px",
};
