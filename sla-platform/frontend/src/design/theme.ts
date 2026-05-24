/**
 * AntD ConfigProvider theme for SLA Platform.
 *
 * Source of truth: DESIGN_SYSTEM.md (section 2). Values mirror
 * `frontend/src/design/tokens.css` so a single change to the CSS variables
 * translates into the same change here. AntD itself reads from this theme
 * via `<ConfigProvider theme={slaTheme}>` in App.tsx.
 *
 * Do NOT introduce hardcoded hex values in components — extend tokens.css
 * and reference them here.
 */
import type { ThemeConfig } from "antd";

export const slaTheme: ThemeConfig = {
  token: {
    colorPrimary: "#4f46e5",
    colorSuccess: "#10b981",
    colorWarning: "#f59e0b",
    colorError: "#ef4444",
    colorInfo: "#4f46e5",
    colorTextBase: "#101828",
    colorBgBase: "#ffffff",
    colorBgLayout: "#f6f7f9",
    colorBorder: "#e4e7ec",
    colorBorderSecondary: "#eef0f3",
    borderRadius: 6,
    borderRadiusLG: 10,
    fontFamily:
      '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: 14,
    fontSizeHeading1: 20,
    fontSizeHeading2: 18,
    controlHeight: 34,
    controlHeightSM: 28,
    boxShadow: "0 1px 2px rgba(16,24,40,0.04)",
    boxShadowSecondary: "0 12px 24px rgba(16,24,40,0.08)",
  },
  components: {
    Table: {
      headerBg: "#ffffff",
      headerColor: "#667085",
      headerSplitColor: "transparent",
      rowHoverBg: "#f9fafb",
      borderColor: "#eef0f3",
    },
    Card: {
      headerBg: "#ffffff",
      headerHeight: 56,
    },
    Button: {
      fontWeight: 500,
      controlHeight: 34,
    },
    Tabs: {
      itemColor: "#667085",
      itemActiveColor: "#101828",
      itemSelectedColor: "#101828",
      inkBarColor: "#4f46e5",
    },
    Drawer: {
      colorBgElevated: "#f6f7f9",
    },
    Tag: {
      defaultBg: "#f3f4f6",
      defaultColor: "#344054",
    },
  },
};

/**
 * Legacy alias — kept so existing imports of `theme` keep working until
 * everything migrates. New code should import `slaTheme`.
 */
export const theme = slaTheme;
