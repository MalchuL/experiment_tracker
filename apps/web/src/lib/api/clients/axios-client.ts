/**
 * Axios-based API client with interceptors
 * Handles authentication, error handling, and request/response transformation
 */

import axios, { AxiosInstance, AxiosRequestHeaders } from "axios";
import { env } from "@/lib/env";
import { ErrorResponse } from "../error-response";
import { getAuthHeaders } from "@/domain/auth/utils/headers";
import { deleteAuthToken } from "@/domain/auth/utils/token";

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
      const headers = getAuthHeaders();
      if (Object.keys(headers).length > 0) {
        config.headers = { ...config.headers, ...headers } as AxiosRequestHeaders;
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
      // TODO: In some 401 errors, the error.response is not present. Fix this
      if (error.response?.status === 401) {
        // Clear token on unauthorized
        if (typeof document !== "undefined") {
          deleteAuthToken();
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
