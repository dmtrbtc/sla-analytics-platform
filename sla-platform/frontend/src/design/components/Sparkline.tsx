/**
 * Sparkline — inline SVG line, 56×20px by default.
 *
 * Used inside table cells to show a 14-point trend. NO axis, NO grid,
 * single colored polyline. Use identity colors:
 *   - `var(--reaction)` for response-time trend
 *   - `var(--resolution)` for resolution-time trend
 *   - `var(--ink-3)` for generic trends
 *
 * Visual reference: `Spark` in SLA Portal/portal-charts.jsx.
 */

export interface SparklineProps {
  /** 4–32 numeric points. Empty array renders nothing. */
  data: number[];
  /** Stroke color — pass a CSS variable token, not a hardcoded hex. */
  color?: string;
  /** Width in pixels (default 56). */
  width?: number;
  /** Height in pixels (default 20). */
  height?: number;
}

export function Sparkline({
  data,
  color = "var(--ink-3)",
  width = 56,
  height = 20,
}: SparklineProps) {
  if (!data || data.length === 0) return null;

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = Math.max(max - min, 1);
  const stepX = width / Math.max(1, data.length - 1);
  const pts = data
    .map(
      (d, i) =>
        `${(i * stepX).toFixed(2)},${(
          height - ((d - min) / range) * (height - 4) - 2
        ).toFixed(2)}`,
    )
    .join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      style={{ display: "block" }}
      aria-hidden
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default Sparkline;
