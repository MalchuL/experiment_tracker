/**
 * Axios-based API client with interceptors
 * Handles authentication, error handling, and request/response transformation
 */

import axios, { AxiosInstance } from "axios";
import { env } from "@/lib/env";
import { ErrorResponse } from "../error-response";

/**
 * Service names for type safety
 */
export type ServiceName = "api";

/**
 * Service URL configuration
 */
export interface ServiceConfig {
  baseURL: string;
  timeout?: number;
}

/**
 * Service registry - maps service names to their base URLs
 */
const serviceRegistry: Record<ServiceName, ServiceConfig> = {
  "api": {
    baseURL: env.BASE_URL,
  },
};

/**
 * Helper function to get auth token from cookie
 */
function getAuthToken(): string | null {
  if (typeof document === "undefined") return null;
  const cookieValue = document.cookie
    .split("; ")
    .find((row) => row.startsWith("auth_token="))
    ?.split("=")[1];
  return cookieValue ? decodeURIComponent(cookieValue) : null;
}

/**
 * Creates a service-specific axios client instance
 * @param serviceName - Name of the service or custom config
 * @param customConfig - Optional custom configuration to override defaults
 * @returns Configured AxiosInstance for the specified service
 */
export function createServiceClient(config: ServiceConfig): AxiosInstance {
  const client: AxiosInstance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeout || 30000,
    withCredentials: true,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Add request interceptor to include Authorization header
  client.interceptors.request.use(
    (config) => {
      const token = getAuthToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Add response interceptor to handle 401 errors
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Clear token on unauthorized
        if (typeof document !== "undefined") {
          document.cookie = 'auth_token=; Max-Age=0; path=/';
        }
        delete client.defaults.headers.common['Authorization'];
      }
      let wrappedError = new ErrorResponse(error.status,
         error.message,
         error.code);
      return Promise.reject(wrappedError);
    }
  );

  return client;
}

/**
 * Pre-configured service clients for convenience
 */
export const serviceClients = {
  /**
   * API Gateway client (default)
   */
  api: createServiceClient(serviceRegistry["api"]),
} as const;

// Initialize Authorization header if token exists
const initialToken = getAuthToken();
if (initialToken) {
  serviceClients.api.defaults.headers.common['Authorization'] = `Bearer ${initialToken}`;
}
