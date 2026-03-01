import { cookies } from "next/headers";
import { env } from "@/lib/env";

export async function GET(
  request: Request,
  context: { params: Promise<{ projectId: string; blobHash: string }> }
) {
  const { projectId, blobHash } = await context.params;
  const token = (await cookies()).get("auth_token")?.value;
  const requestedContentType =
    new URL(request.url).searchParams.get("contentType") ?? undefined;

  const targetUrl = `${env.BASE_URL}/api/project-artifacts/${encodeURIComponent(projectId)}/blobs/${encodeURIComponent(blobHash)}${requestedContentType ? `?contentType=${encodeURIComponent(requestedContentType)}` : ""}`;
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
        (response.headers.get("content-type") === "application/octet-stream" &&
        requestedContentType
          ? requestedContentType
          : response.headers.get("content-type")) ?? "application/octet-stream",
      "Cache-Control": "no-store",
    },
  });
}
