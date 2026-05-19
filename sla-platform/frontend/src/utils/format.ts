export function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0 сек";
  if (seconds < 60) return `${Math.round(seconds)} сек`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} мин`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}

export function parseHumanDuration(input: string): number {
  if (!input) return 0;
  let total = 0;
  // Match "15 мин", "1ч30мин", "2 д 4 ч", "15мин" — any whitespace between number and unit
  const regex = /(\d+)\s*([дdчhмmсs])/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(input)) !== null) {
    const val = parseInt(match[1], 10);
    const unit = match[2].toLowerCase();
    if (unit === "д" || unit === "d") total += val * 86400;
    else if (unit === "ч" || unit === "h") total += val * 3600;
    else if (unit === "м" || unit === "m") total += val * 60;
    else if (unit === "с" || unit === "s") total += val;
  }
  return total;
}

export function formatHumanDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "0 мин";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.round((seconds % 3600) / 60);
  const parts: string[] = [];
  if (d > 0) parts.push(`${d} д`);
  if (h > 0) parts.push(`${h} ч`);
  if (m > 0 || parts.length === 0) parts.push(`${m} мин`);
  return parts.join(" ").trim();
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
