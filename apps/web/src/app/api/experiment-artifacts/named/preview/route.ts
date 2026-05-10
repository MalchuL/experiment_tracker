import { Buffer } from "node:buffer";
import { cookies } from "next/headers";
import { env } from "@/lib/env";

const DEFAULT_MAX_BYTES = 2 * 1024 * 1024;
const TEXT_EXTENSIONS = new Set(["txt", "yaml", "yml", "json", "toml", "md", "log", "csv", "ini", "cfg"]);

type PreviewResponse =
  | { status: "ok"; text: string; sizeBytes: number; contentType: string }
  | {
      status: "image_ok";
      dataUrl: string;
      sizeBytes: number;
      contentType: string;
    }
  | {
      status: "too_large";
      message: string;
      sizeBytes: number;
      thresholdBytes: number;
      contentType: string;
    }
  | { status: "binary"; message: string; sizeBytes: number; contentType: string }
  | { status: "decode_error"; message: string; sizeBytes: number; contentType: string };

function isTextByExtension(filepath: string): boolean {
  const extension = filepath.split(".").pop()?.toLowerCase() ?? "";
  return TEXT_EXTENSIONS.has(extension);
}

function isTextByContentType(contentType: string): boolean {
  return (
    contentType.startsWith("text/") ||
    contentType.includes("json") ||
    contentType.includes("yaml") ||
    contentType.includes("toml")
  );
}

async function readUpTo(
  response: Response,
  maxBytes: number
): Promise<{ bytes: Uint8Array; exceeded: boolean }> {
  if (!response.body) {
    return { bytes: new Uint8Array(), exceeded: false };
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  let exceeded = false;
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    if (!value) {
      continue;
    }
    total += value.byteLength;
    if (total > maxBytes) {
      exceeded = true;
      break;
    }
    chunks.push(value);
  }
  if (exceeded) {
    return { bytes: new Uint8Array(), exceeded: true };
  }
  const merged = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return { bytes: merged, exceeded: false };
}

function bytesToDataUrl(bytes: Uint8Array, contentType: string): string {
  const b64 = Buffer.from(bytes).toString("base64");
  return `data:${contentType};base64,${b64}`;
}

export async function GET(request: Request) {
  const token = (await cookies()).get("auth_token")?.value;
  const requestUrl = new URL(request.url);
  const experimentId = requestUrl.searchParams.get("experiment_id");
  const filepath = requestUrl.searchParams.get("filepath");
  const blobId = requestUrl.searchParams.get("blob_id");
  const artifactHash = requestUrl.searchParams.get("artifact_hash");
  const maxBytesRaw = Number(requestUrl.searchParams.get("max_bytes") ?? DEFAULT_MAX_BYTES);
  const maxBytes = Number.isFinite(maxBytesRaw) && maxBytesRaw > 0 ? maxBytesRaw : DEFAULT_MAX_BYTES;

  if (!experimentId || (!filepath && !blobId && !artifactHash)) {
    return Response.json(
      {
        status: "decode_error",
        message: "Missing required query parameters",
        sizeBytes: 0,
        contentType: "application/octet-stream",
      } satisfies PreviewResponse,
      { status: 400 }
    );
  }

  const targetUrl = new URL(`${env.BASE_URL}/api/experiment-artifacts/download`);
  targetUrl.searchParams.set("experiment_id", experimentId);
  if (filepath) targetUrl.searchParams.set("filepath", filepath);
  if (blobId) targetUrl.searchParams.set("blob_id", blobId);
  if (artifactHash) targetUrl.searchParams.set("artifact_hash", artifactHash);

  const response = await fetch(targetUrl.toString(), {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    return Response.json(
      {
        status: "decode_error",
        message: `Backend returned ${response.status}`,
        sizeBytes: 0,
        contentType: "application/octet-stream",
      } satisfies PreviewResponse,
      { status: response.status }
    );
  }

  const contentType = response.headers.get("content-type") ?? "application/octet-stream";
  const contentLength = Number(response.headers.get("content-length") ?? NaN);
  const declaredSize = Number.isFinite(contentLength) && contentLength >= 0 ? contentLength : 0;

  if (contentType.startsWith("image/")) {
    if (declaredSize > maxBytes) {
      return Response.json({
        status: "too_large",
        message: "Image is larger than the in-browser preview limit.",
        sizeBytes: declaredSize,
        thresholdBytes: maxBytes,
        contentType,
      } satisfies PreviewResponse);
    }

    const { bytes, exceeded } = await readUpTo(response, maxBytes);
    if (exceeded) {
      return Response.json({
        status: "too_large",
        message: "Image is larger than the in-browser preview limit.",
        sizeBytes: maxBytes + 1,
        thresholdBytes: maxBytes,
        contentType,
      } satisfies PreviewResponse);
    }

    return Response.json({
      status: "image_ok",
      dataUrl: bytesToDataUrl(bytes, contentType),
      sizeBytes: bytes.byteLength,
      contentType,
    } satisfies PreviewResponse);
  }

  if (!isTextByExtension(filepath ?? "") && !isTextByContentType(contentType)) {
    return Response.json({
      status: "binary",
      message: "Binary file can't be shown in UI preview.",
      sizeBytes: declaredSize,
      contentType,
    } satisfies PreviewResponse);
  }

  if (declaredSize > maxBytes) {
    return Response.json({
      status: "too_large",
      message: "File is larger than preview threshold.",
      sizeBytes: declaredSize,
      thresholdBytes: maxBytes,
      contentType,
    } satisfies PreviewResponse);
  }

  const { bytes, exceeded } = await readUpTo(response, maxBytes);
  if (exceeded) {
    return Response.json({
      status: "too_large",
      message: "File is larger than preview threshold.",
      sizeBytes: maxBytes + 1,
      thresholdBytes: maxBytes,
      contentType,
    } satisfies PreviewResponse);
  }

  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return Response.json({
      status: "ok",
      text,
      sizeBytes: bytes.byteLength,
      contentType,
    } satisfies PreviewResponse);
  } catch {
    return Response.json({
      status: "decode_error",
      message: "Unable to decode file as UTF-8 text.",
      sizeBytes: bytes.byteLength,
      contentType,
    } satisfies PreviewResponse);
  }
}
