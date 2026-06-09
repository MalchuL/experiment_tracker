import { afterEach, describe, expect, it, vi } from "vitest";
import { createClientId } from "./utils";

describe("createClientId", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses crypto.randomUUID when available", () => {
    const randomUUID = vi.fn(() => "test-uuid");
    vi.stubGlobal("crypto", { randomUUID });

    expect(createClientId()).toBe("test-uuid");
    expect(randomUUID).toHaveBeenCalledOnce();
  });

  it("falls back when crypto.randomUUID is missing", () => {
    vi.stubGlobal("crypto", {});

    const id = createClientId();
    expect(id).toMatch(/^\d+-\d+$/);
  });

  it("falls back when crypto is undefined", () => {
    vi.stubGlobal("crypto", undefined);

    const id = createClientId();
    expect(id).toMatch(/^\d+-\d+$/);
  });
});
