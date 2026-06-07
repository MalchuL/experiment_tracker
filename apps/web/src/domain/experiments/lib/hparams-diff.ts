import type { HparamsDocument, JsonValue } from "../types/hparams";

export interface HparamsDiffSummary {
  added: number;
  removed: number;
  changed: number;
}

export function summarizeHparamsDiff(
  parent: HparamsDocument,
  current: HparamsDocument | null
): HparamsDiffSummary {
  const parentValues = flattenValues(parent);
  const currentValues = flattenValues(current ?? {});
  const keys = new Set([...parentValues.keys(), ...currentValues.keys()]);
  const summary: HparamsDiffSummary = { added: 0, removed: 0, changed: 0 };

  keys.forEach((key) => {
    const parentValue = parentValues.get(key);
    const currentValue = currentValues.get(key);
    if (parentValue === undefined) summary.added += 1;
    else if (currentValue === undefined) summary.removed += 1;
    else if (parentValue !== currentValue) summary.changed += 1;
  });

  return summary;
}

function flattenValues(document: HparamsDocument): Map<string, string> {
  const values = new Map<string, string>();
  const visit = (value: JsonValue, path: string) => {
    if (Array.isArray(value)) {
      if (value.length === 0) values.set(path, JSON.stringify(value));
      value.forEach((child, index) => visit(child, `${path}[${index}]`));
      return;
    }
    if (value !== null && typeof value === "object") {
      const entries = Object.entries(value);
      if (entries.length === 0) values.set(path, JSON.stringify(value));
      entries.forEach(([key, child]) => visit(child, path ? `${path}.${key}` : key));
      return;
    }
    values.set(path, JSON.stringify(value));
  };

  Object.entries(document).forEach(([key, value]) => visit(value, key));
  return values;
}
