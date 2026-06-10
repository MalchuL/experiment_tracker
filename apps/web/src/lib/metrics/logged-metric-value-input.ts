/**
 * Strict parse for logged metric value fields. `Number.parseFloat` only reads a prefix and drops
 * trailing garbage (`parseFloat("1.2x") === 1.2`); `Number(trimmed)` requires the whole string to
 * be a numeric literal, so typos at the end are rejected instead of truncated.
 */
export function parseLoggedMetricValueInput(trimmed: string): number | null {
  if (trimmed === "") return null;
  const num = Number(trimmed);
  if (!Number.isFinite(num)) return null;
  return num;
}
