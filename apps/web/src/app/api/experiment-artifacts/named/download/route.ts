import { cookies } from "next/headers";
import { getServerApiBaseUrl } from "@/lib/env";

export async function GET(request: Request) {
  const token = (await cookies()).get("auth_token")?.value;
  const requestUrl = new URL(request.url);
  const experimentId = requestUrl.searchParams.get("experiment_id");
  const filepath = requestUrl.searchParams.get("filepath");
  const blobId = requestUrl.searchParams.get("blob_id");
  const artifactHash = requestUrl.searchParams.get("artifact_hash");
  const disposition = requestUrl.searchParams.get("disposition") === "inline"
    ? "inline"
    : "attachment";

  if (!experimentId || (!filepath && !blobId && !artifactHash)) {
    return new Response(
      "Missing required query parameters: experiment_id and one of filepath/blob_id/artifact_hash",
      { status: 400 }
    );
  }

  const targetUrl = new URL(`${getServerApiBaseUrl()}/api/experiment-artifacts/download`);
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
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
    });
  }

  return new Response(response.body, {
    status: 200,
    headers: {
      "Content-Type":
        response.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition": `${disposition}; filename="${encodeURIComponent(filepath?.split("/").pop() || "artifact")}"`,
      "Cache-Control": "no-store",
    },
  });
}

