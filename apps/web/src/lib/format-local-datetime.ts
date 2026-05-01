import { format, isValid, parseISO } from "date-fns";

/** Format an API ISO-8601 UTC string (with `Z`) in the user's local timezone. */
export function formatLocalDateTime(
  iso: string | null | undefined,
  fmt: string,
): string {
  if (!iso) return "";
  const d = parseISO(iso);
  return isValid(d) ? format(d, fmt) : "";
}
