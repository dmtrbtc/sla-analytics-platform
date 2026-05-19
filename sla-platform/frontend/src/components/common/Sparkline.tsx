import { palette } from "../../design/colors";

interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  width?: number;
  area?: boolean;
}

export function Sparkline({ data, color = palette.brand[500], height = 24, width = 72, area = true }: SparklineProps) {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const pts = data
    .map((d, i) => `${(i * stepX).toFixed(1)},${(height - ((d - min) / range) * (height - 4) - 2).toFixed(1)}`)
    .join(" ");
  const areaPts = `0,${height} ${pts} ${width},${height}`;
  const lx = (data.length - 1) * stepX;
  const ly = height - ((data[data.length - 1] - min) / range) * (height - 4) - 2;
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      style={{ display: "block" }}
    >
      {area && <polygon points={areaPts} fill={color} fillOpacity={0.1} />}
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="2" fill={color} />
    </svg>
  );
}
