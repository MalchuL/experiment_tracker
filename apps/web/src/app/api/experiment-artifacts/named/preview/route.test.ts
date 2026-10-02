import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => ({ value: "test-token" }) }),
}));
vi.mock("@/lib/env", () => ({
  getServerApiBaseUrl: () => "http://backend:8000",
}));

afterEach(() => vi.unstubAllGlobals());

async function preview(filepath: string, response: Response, maxBytes?: number) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  const params = new URLSearchParams({ experiment_id: "exp-1", filepath });
  if (maxBytes !== undefined) params.set("max_bytes", String(maxBytes));
  const result = await GET(new Request(`http://localhost/api/experiment-artifacts/named/preview?${params}`));
  return { data: await result.json(), fetchMock };
}

describe("final artifact text previews", () => {
  it.each([
    ["scripts/train.sh", "application/x-sh"],
    ["scripts/TRAIN.SH", "application/octet-stream"],
    ["scripts/train.bash", "application/octet-stream"],
    ["src/train.py", "application/octet-stream"],
    ["src/train.ts", "application/octet-stream"],
    ["config/.env", "application/octet-stream"],
    ["config/run.conf", "application/octet-stream"],
    ["metrics/results.jsonl", "application/octet-stream"],
    ["config/run.yaml", "application/octet-stream"],
    ["notes", "text/plain"],
  ])("previews %s as text with MIME type %s", async (filepath, contentType) => {
    const text = "#!/bin/sh\necho 'Привет'\n";
    const { data, fetchMock } = await preview(filepath, new Response(text, {
      headers: { "content-type": contentType },
    }));
    expect(data).toEqual({
      status: "ok", text, sizeBytes: new TextEncoder().encode(text).byteLength, contentType,
    });
    const [target, options] = fetchMock.mock.calls[0];
    expect(new URL(target).searchParams.get("filepath")).toBe(filepath);
    expect(options.headers).toEqual({ Authorization: "Bearer test-token" });
  });

  it("keeps model checkpoints out of the text viewer", async () => {
    const { data } = await preview("model.pt", new Response(new Uint8Array([0, 255]), {
      headers: { "content-type": "application/octet-stream" },
    }));
    expect(data.status).toBe("binary");
  });

  it("rejects invalid UTF-8 in a shell script", async () => {
    const { data } = await preview("train.sh", new Response(new Uint8Array([255]), {
      headers: { "content-type": "application/x-sh" },
    }));
    expect(data.status).toBe("decode_error");
  });

  it.each([false, true])("limits script preview size (declared size: %s)", async (declaredSize) => {
    const headers = new Headers({ "content-type": "application/x-sh" });
    if (declaredSize) headers.set("content-length", "5");
    const { data } = await preview("train.sh", new Response("12345", { headers }), 4);
    expect(data).toMatchObject({ status: "too_large", thresholdBytes: 4 });
  });
});
