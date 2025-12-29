/**
 * Axios-based API client with interceptors
 * Handles authentication, error handling, and request/response transformation
 */

import axios, { AxiosInstance } from "axios";
import { env } from "@/lib/env";

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
