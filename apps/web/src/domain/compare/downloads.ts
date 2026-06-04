"use client";

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function filenameFromContentDisposition(
  contentDisposition: string | undefined,
  fallback: string
): string {
  if (!contentDisposition) return fallback;
  const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      return encodedMatch[1];
    }
  }
  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) return quotedMatch[1];
  const plainMatch = contentDisposition.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() || fallback;
}

export function sanitizeDownloadName(value: string): string {
  const cleaned = value.trim().replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
  return cleaned || "download";
}

export function basenameFromPath(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  return sanitizeDownloadName(normalized.split("/").filter(Boolean).at(-1) ?? "snapshot-file");
}
