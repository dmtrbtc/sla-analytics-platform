import { palette } from "../../design/colors";

interface ProgressBarProps {
  pct: number;
  height?: number;
  color?: string;
  bgColor?: string;
  showLabel?: boolean;
  labelPosition?: "left" | "right" | "inside";
}

export function ProgressBar({ pct, height = 8, color, bgColor, showLabel = false, labelPosition = "right" }: ProgressBarProps) {
  const finalColor = color || (pct >= 95 ? palette.accent.emerald : pct >= 85 ? palette.accent.amber : pct >= 70 ? palette.severity.high : palette.accent.rose);
  const bar = (
    <div style={{ flex: 1, height, background: bgColor || palette.borderLight, borderRadius: height / 2, overflow: "hidden" }}>
      <div style={{ width: `${Math.max(2, Math.min(pct, 100))}%`, height: "100%", background: finalColor, borderRadius: height / 2, transition: "width 0.4s ease" }} />
    </div>
  );
  if (!showLabel) return bar;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      {labelPosition === "left" && <span style={{ minWidth: 36, textAlign: "right", fontSize: 12, fontWeight: 600, color: finalColor }}>{pct}%</span>}
      {bar}
      {labelPosition === "right" && <span style={{ minWidth: 36, fontSize: 12, fontWeight: 600, color: finalColor }}>{pct}%</span>}
    </div>
  );
}
