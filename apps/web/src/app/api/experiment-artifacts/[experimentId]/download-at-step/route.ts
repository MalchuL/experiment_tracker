import { cookies } from "next/headers";
import { getServerApiBaseUrl } from "@/lib/env";

export async function GET(
  request: Request,
  context: { params: Promise<{ experimentId: string }> }
) {
  const { experimentId } = await context.params;
  const token = (await cookies()).get("auth_token")?.value;
  const requestUrl = new URL(request.url);
  const stepRaw = requestUrl.searchParams.get("step");
  const name = requestUrl.searchParams.get("name");
  const artifactType = requestUrl.searchParams.get("artifact_type");
  if (stepRaw === null || name === null || name === "") {
    return new Response("Missing step or name query parameter", { status: 400 });
  }
  const step = Number(stepRaw);
  if (!Number.isFinite(step)) {
    return new Response("Invalid step", { status: 400 });
  }

  const targetUrl = new URL(
    `${getServerApiBaseUrl()}/api/experiment-artifacts/${encodeURIComponent(experimentId)}/download-at-step`
  );
  targetUrl.searchParams.set("step", String(step));
  targetUrl.searchParams.set("name", name);
  if (artifactType) {
    targetUrl.searchParams.set("artifact_type", artifactType);
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
