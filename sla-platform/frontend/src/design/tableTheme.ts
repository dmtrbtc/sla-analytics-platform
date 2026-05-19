import { palette } from "./colors";
import { typography } from "./typography";
import { radius } from "./spacing";

export const tableTheme = {
  header: {
    background: "#f8f9fa",
    color: palette.text.secondary,
    fontSize: "11px",
    fontWeight: 600,
    textTransform: "uppercase" as const,
    letterSpacing: "0.04em",
    borderColor: palette.borderLight,
    padding: "10px 12px",
  },
  body: {
    fontSize: "13px",
    color: palette.text.primary,
    borderColor: palette.borderLight,
    padding: "10px 12px",
  },
  row: {
    hoverBackground: "#f8f9fa",
    selectedBackground: "#eef2ff",
    height: "44px",
  },
  radius: radius.md,
  pagination: {
    fontSize: "12px",
    color: palette.text.secondary,
    activeColor: palette.brand[500],
  },
} as const;
