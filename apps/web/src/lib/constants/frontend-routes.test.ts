import { describe, expect, it } from "vitest";
import { FRONTEND_ROUTES, isPublicFrontendPath } from "./frontend-routes";

describe("isPublicFrontendPath", () => {
  it("allows auth and admin routes without login", () => {
    expect(isPublicFrontendPath(FRONTEND_ROUTES.LOGIN)).toBe(true);
    expect(isPublicFrontendPath(FRONTEND_ROUTES.REGISTER)).toBe(true);
    expect(isPublicFrontendPath(FRONTEND_ROUTES.ADMIN)).toBe(true);
    expect(isPublicFrontendPath(FRONTEND_ROUTES.ADMIN_STORAGE)).toBe(true);
  });

  it("requires login for workspace routes", () => {
    expect(isPublicFrontendPath(FRONTEND_ROUTES.PROJECTS)).toBe(false);
    expect(isPublicFrontendPath(FRONTEND_ROUTES.DOCS)).toBe(false);
    expect(isPublicFrontendPath(null)).toBe(false);
  });
});
