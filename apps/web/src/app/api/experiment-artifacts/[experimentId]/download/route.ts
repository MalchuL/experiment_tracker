import { cookies } from "next/headers";
import { env } from "@/lib/env";

export async function GET(
  request: Request,
  context: { params: Promise<{ experimentId: string }> }
) {
  const { experimentId } = await context.params;
  const token = (await cookies()).get("auth_token")?.value;
  const path = new URL(request.url).searchParams.get("path");
  if (!path) {
    return new Response("Missing path query parameter", { status: 400 });
  }

  const targetUrl =
    `${env.BASE_URL}/api/experiment-artifacts/${encodeURIComponent(experimentId)}` +
    `/download?path=${encodeURIComponent(path)}`;

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
        response.headers.get("content-type") ?? "application/octet-stream",
      "Cache-Control": "no-store",
    },
  });
}

