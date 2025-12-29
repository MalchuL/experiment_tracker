import { getAuthToken } from "./token";

/**
 * Helper function to get auth headers
 */
export function getAuthHeaders(): Record<string, string> {
    const token = getAuthToken();
    if (!token) return {};
    return {
        Authorization: `Bearer ${token}`
    };
}