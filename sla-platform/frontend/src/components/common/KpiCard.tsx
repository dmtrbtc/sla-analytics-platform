import type { CSSProperties, ReactNode } from "react";
import { palette } from "../../design/colors";
import { typography } from "../../design/typography";
import { shadows } from "../../design/shadows";
import { radius, spacing } from "../../design/spacing";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; positive: boolean };
  sparkline?: ReactNode;
  icon?: ReactNode;
  color?: string;
  style?: CSSProperties;
  small?: boolean;
}

export function KpiCard({ title, value, subtitle, trend, sparkline, icon, color, style, small }: KpiCardProps) {
  const valSize = small ? "20px" : typography.size["4xl"];
  return (
    <div
      style={{
        background: palette.card,
        border: `1px solid ${palette.border}`,
        borderRadius: radius.lg,
        boxShadow: shadows.card,
        padding: small ? "12px 16px" : spacing[4],
        display: "flex",
        flexDirection: "column",
        gap: small ? 2 : spacing[1.5],
        ...style,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span
          style={{
            fontFamily: typography.fontFamily,
            fontSize: typography.size.xs,
            fontWeight: typography.weight.semibold,
            color: palette.text.tertiary,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          {title}
        </span>
        {icon && <span style={{ color: color || palette.text.tertiary, fontSize: 14, opacity: 0.6 }}>{icon}</span>}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: spacing[2] }}>
        <span
          style={{
            fontFamily: typography.fontFamily,
            fontSize: valSize,
            fontWeight: typography.weight.bold,
            color: color || palette.text.primary,
            lineHeight: "1.2",
          }}
        >
          {value}
        </span>
        {trend && (
          <span
            style={{
              fontFamily: typography.fontFamily,
              fontSize: typography.size.sm,
              fontWeight: typography.weight.medium,
              color: trend.positive ? palette.accent.emerald : palette.accent.rose,
              display: "inline-flex",
              alignItems: "center",
              gap: 2,
            }}
          >
            {trend.positive ? "▲" : "▼"} {trend.value}%
          </span>
        )}
      </div>
      {subtitle && (
        <span
          style={{
            fontFamily: typography.fontFamily,
            fontSize: typography.size.sm,
            color: palette.text.tertiary,
          }}
        >
          {subtitle}
        </span>
      )}
      {sparkline && <div style={{ marginTop: small ? 0 : spacing[1] }}>{sparkline}</div>}
    </div>
  );
}
