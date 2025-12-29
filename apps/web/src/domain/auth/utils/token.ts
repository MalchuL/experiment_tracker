/**
 * Helper function to get auth token from cookie
 */
export function getAuthToken(): string | null {
    if (typeof document === "undefined") return null;
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith("auth_token="))
      ?.split("=")[1];
    return cookieValue ? decodeURIComponent(cookieValue) : null;
  }
