/** Helpers for storage usage DTO shapes (`{ bytes: number }` fragments). */

export function bytesFrom(value: unknown): number {
  if (!value || typeof value !== "object") return 0;
  const bytes = (value as Record<string, unknown>).bytes;
  return typeof bytes === "number" ? bytes : 0;
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}
