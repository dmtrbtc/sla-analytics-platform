export function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0 sec";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (m === 0) return `${h} h`;
  return `${h} h ${m} min`;
}

export function formatDurationHuman(seconds: number): string {
  if (!seconds || seconds <= 0) return "0с";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d}д`);
  if (h > 0) parts.push(`${h}ч`);
  if (m > 0) parts.push(`${m}м`);
  if (s > 0 && d === 0) parts.push(`${s}с`);
  return parts.join(" ") || "0с";
}
