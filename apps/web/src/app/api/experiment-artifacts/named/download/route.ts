import { cookies } from "next/headers";
import { env } from "@/lib/env";

export async function GET(request: Request) {
  const token = (await cookies()).get("auth_token")?.value;
  const requestUrl = new URL(request.url);
  const experimentId = requestUrl.searchParams.get("experiment_id");
  const name = requestUrl.searchParams.get("name");
  const filepath = requestUrl.searchParams.get("filepath");
  const disposition = requestUrl.searchParams.get("disposition") === "inline"
    ? "inline"
    : "attachment";

  if (!experimentId || !name || !filepath) {
    return new Response(
      "Missing required query parameters: experiment_id, name, filepath",
      { status: 400 }
    );
  }

  const targetUrl = new URL(`${env.BASE_URL}/api/experiment-artifacts/download`);
  targetUrl.searchParams.set("experiment_id", experimentId);
  targetUrl.searchParams.set("name", name);
  targetUrl.searchParams.set("filepath", filepath);

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
      "Content-Disposition": `${disposition}; filename="${encodeURIComponent(filepath.split("/").pop() || "artifact")}"`,
      "Cache-Control": "no-store",
    },
  });
}

