import { cookies } from "next/headers";
import { env } from "@/lib/env";

export async function GET(
  request: Request,
  context: { params: Promise<{ experimentId: string }> }
) {
  const { experimentId } = await context.params;
  const token = (await cookies()).get("auth_token")?.value;
  const requestUrl = new URL(request.url);
  const path = requestUrl.searchParams.get("path");
  const mediaType = requestUrl.searchParams.get("media_type");
  if (!path) {
    return new Response("Missing path query parameter", { status: 400 });
  }

  const targetUrl = new URL(
    `${env.BASE_URL}/api/experiment-artifacts/${encodeURIComponent(experimentId)}/download-at-step`
  );
  targetUrl.searchParams.set("path", path);
  if (mediaType) {
    targetUrl.searchParams.set("media_type", mediaType);
  }

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
      "Cache-Control": "no-store",
    },
  });
}
