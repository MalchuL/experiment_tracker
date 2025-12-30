/**
 * Helper function to get auth token from cookie
 */

export const AUTH_TOKEN_NAME = "auth_token";

export function getAuthToken(): string | null {
    if (typeof document === "undefined") return null;
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith(AUTH_TOKEN_NAME + "="))
      ?.split("=")[1];
    return cookieValue ? decodeURIComponent(cookieValue) : null;
  }

export function deleteAuthToken(): void {
    if (typeof document === "undefined") return;
    document.cookie = `${AUTH_TOKEN_NAME}=; Max-Age=0; path=/`;
}

export function setAuthToken(token: string): void {
    if (typeof document === "undefined") return;
    document.cookie = `${AUTH_TOKEN_NAME}=${token}; path=/`;
}
