import type { HparamsDocument, JsonValue } from "@/domain/experiments/types";

const HPARAMS_INLINE_ARRAY_MAX_LEN = 8;

function isJsonContainer(value: JsonValue | undefined): value is JsonValue[] | HparamsDocument {
  return value !== null && typeof value === "object";
}

function canInlineArray(value: JsonValue[]): boolean {
  if (value.length > HPARAMS_INLINE_ARRAY_MAX_LEN) return false;
  return value.every((item) => !isJsonContainer(item));
}

function formatInlineArray(value: JsonValue[]): string {
  return `[${value.map((item) => displayHparamsValue(item)).join(", ")}]`;
}

export function hparamsValueClassName(value: JsonValue | undefined | null): string {
  const mono = "font-mono font-normal";
  if (value === null || value === undefined) return `${mono} italic text-muted-foreground`;
  if (typeof value === "boolean") return `${mono} text-violet-600 dark:text-violet-400`;
  if (typeof value === "number") return `${mono} text-blue-600 dark:text-blue-400`;
  if (typeof value === "string") return `${mono} text-emerald-700 dark:text-emerald-400`;
  return `${mono} text-muted-foreground`;
}

export function displayHparamsValue(value: JsonValue | null | undefined): string {
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value) && canInlineArray(value)) return formatInlineArray(value);
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string") return JSON.stringify(value);
  return String(value);
}
