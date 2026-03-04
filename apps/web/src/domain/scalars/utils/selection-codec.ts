function toBase64(value: string): string {
  const utf8 = encodeURIComponent(value).replace(
    /%([0-9A-F]{2})/g,
    (_, hex: string) => String.fromCharCode(Number.parseInt(hex, 16))
  );
  return btoa(utf8);
}

function fromBase64(value: string): string {
  const binary = atob(value);
  const encoded = Array.from(binary)
    .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, "0")}`)
    .join("");
  return decodeURIComponent(encoded);
}

export function encodeStringSelection(values: string[]): string {
  if (values.length === 0) return "";
  const unique = Array.from(new Set(values));
  return toBase64(JSON.stringify(unique));
}

export function decodeStringSelection(encoded: string | null): string[] {
  if (!encoded) return [];
  try {
    const decoded = fromBase64(encoded);
    const parsed = JSON.parse(decoded);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is string => typeof value === "string");
  } catch {
    return [];
  }
}

// Backward compatibility for old links where indexes were encoded as "0,1,2".
export function decodeLegacyNumberSelection(encoded: string | null): number[] {
  if (!encoded) return [];
  try {
    const decoded = atob(encoded);
    return decoded
      .split(",")
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value));
  } catch {
    return [];
  }
}
