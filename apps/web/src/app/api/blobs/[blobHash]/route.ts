import { cookies } from "next/headers";
import { env } from "@/lib/env";

export async function GET(
  request: Request,
  context: { params: Promise<{ blobHash: string }> }
) {
  const { blobHash } = await context.params;
  const token = (await cookies()).get("auth_token")?.value;
  const requestedContentType =
    new URL(request.url).searchParams.get("contentType") ?? undefined;

  const targetUrl = `${env.BASE_URL}/api/blobs/${encodeURIComponent(blobHash)}`;
  const response = await fetch(targetUrl, {
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
        // If backend returns generic binary type, prefer UI-provided contentType hint.
        (response.headers.get("content-type") === "application/octet-stream" &&
        requestedContentType
          ? requestedContentType
          : response.headers.get("content-type")) ?? "application/octet-stream",
      "Cache-Control": "no-store",
    },
  });
}
