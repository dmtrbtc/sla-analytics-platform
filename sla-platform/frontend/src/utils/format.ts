export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("ru-RU");
}

export function formatDateTime(date: string): string {
  return new Date(date).toLocaleString("ru-RU");
}
