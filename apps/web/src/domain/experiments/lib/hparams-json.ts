import type { HparamsDocument } from "../types/hparams";

export function parseHparamsJson(text: string): HparamsDocument {
  const value = JSON.parse(text) as unknown;
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    throw new Error("Hyperparameters must be a JSON object.");
  }
  return value as HparamsDocument;
}

export function formatHparamsJson(hparams: HparamsDocument | null): string {
  return JSON.stringify(hparams ?? {}, null, 2);
}

export function jsonPath(path: (string | number)[]): string {
  return path.reduce<string>((result, part) => {
    if (typeof part === "number") return `${result}[${part}]`;
    return result ? `${result}.${part}` : part;
  }, "");
}
