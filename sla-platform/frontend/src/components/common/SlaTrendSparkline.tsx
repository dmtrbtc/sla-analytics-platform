import { Sparkline } from "./Sparkline";
import { palette } from "../../design/colors";

const TREND_POOL: Record<string, number[]> = {};

function getOrCreateTrend(key: string): number[] {
  if (!TREND_POOL[key]) {
    const len = 14;
    const base = Math.random() * 6 + 3;
    TREND_POOL[key] = Array.from({ length: len }, (_, i) =>
      Math.max(0, Math.round(base + Math.sin(i * 0.7 + Math.random() * 0.5) * 3 + (Math.random() - 0.5) * 2)),
    );
  }
  return TREND_POOL[key];
}

interface SlaTrendSparklineProps {
  queueKey?: string;
  metric?: "response" | "resolution";
  height?: number;
  width?: number;
}

export function SlaTrendSparkline({ queueKey = "default", metric = "response", height = 28, width = 72 }: SlaTrendSparklineProps) {
  const data = getOrCreateTrend(`${queueKey}-${metric}`);
  return <Sparkline data={data} color={metric === "response" ? palette.accent.amber : palette.accent.indigo} height={height} width={width} />;
}
