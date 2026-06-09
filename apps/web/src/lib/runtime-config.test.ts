import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getPublicApiBaseUrl,
  getRuntimeConfigScript,
} from "./runtime-config";

const originalPublicApiBaseUrl = process.env.PUBLIC_API_BASE_URL;

afterEach(() => {
  vi.unstubAllGlobals();
  if (originalPublicApiBaseUrl === undefined) {
    delete process.env.PUBLIC_API_BASE_URL;
  } else {
    process.env.PUBLIC_API_BASE_URL = originalPublicApiBaseUrl;
  }
});

describe("runtime config", () => {
  it("reads and normalizes the server runtime environment", () => {
    process.env.PUBLIC_API_BASE_URL = "https://api.example.com/";

    expect(getPublicApiBaseUrl()).toBe("https://api.example.com");
  });

  it("reads the browser runtime config", () => {
    vi.stubGlobal("window", {
      __EXPERIMENT_TRACKER_CONFIG__: {
        publicApiBaseUrl: "https://browser-api.example.com/",
      },
    });

    expect(getPublicApiBaseUrl()).toBe("https://browser-api.example.com");
  });

  it("escapes less-than characters in the injected script", () => {
    process.env.PUBLIC_API_BASE_URL = "https://api.example.com/?value=%3Cscript%3E";

    const script = getRuntimeConfigScript();

    expect(script).not.toContain("<");
    expect(script).toContain("window.__EXPERIMENT_TRACKER_CONFIG__=");
  });
});
