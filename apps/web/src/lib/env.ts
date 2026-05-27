/**
 * Environment variable validation using Zod framework
 * Provides type-safe access to environment variables with validation
 */

import { z } from "zod";

/**
 * Environment variable schema with Zod validation
 */
const envSchema = z.object({
  BASE_URL: z
    .url("BASE_URL must be a valid URL")
    .describe(
      "Base URL (e.g., https://yourdomain.com or http://localhost:3000)"
    ),

  /** When set (e.g. Docker: `http://backend:8000`), server-side BFF routes use this instead of BASE_URL. */
  SERVER_API_BASE_URL: z.url().optional(),

  /** API path prefix for SDK config hints (matches backend `API_PREFIX`, default `/api`). */
  API_PREFIX: z
    .string()
    .min(1, "API_PREFIX must be non-empty")
    .describe("API path prefix, e.g. /api"),

  NODE_ENV: z
    .enum(["development", "production", "test"], {
      message: "NODE_ENV must be one of: development, production, test",
    })
    .describe("Environment mode (development, production, test)"),
});

/**
 * Validates and parses environment variables
 * @throws Error if validation fails
 */
function validateEnvironment(): z.infer<typeof envSchema> {
  try {
    const serverApi = process.env.SERVER_API_BASE_URL?.trim();
    const apiPrefix = process.env.NEXT_PUBLIC_API_PREFIX?.trim();
    const envVariables = {
      // Base URL (browser + default server; use host-reachable URL in Docker for client bundles)
      BASE_URL: process.env.NEXT_PUBLIC_BASE_URL,
      SERVER_API_BASE_URL:
        serverApi && serverApi.length > 0 ? serverApi : undefined,
      API_PREFIX: apiPrefix && apiPrefix.length > 0 ? apiPrefix : "/api",
      // Node
      NODE_ENV: process.env.NODE_ENV,
    };
    return envSchema.parse(envVariables);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const missingVars: string[] = [];
      const invalidVars: string[] = [];

      error.issues.forEach((issue) => {
        const varName = issue.path.join(".");
        if (issue.code === "invalid_type") {
          missingVars.push(`${varName}: ${issue.message}`);
        } else {
          invalidVars.push(`${varName}: ${issue.message}`);
        }
      });

      let errorMessage = "Environment validation failed:\n\n";

      if (missingVars.length > 0) {
        errorMessage += "Missing environment variables:\n";
        missingVars.forEach((varName) => {
          errorMessage += `  ${varName}\n`;
        });
        errorMessage += "\n";
      }

      if (invalidVars.length > 0) {
        errorMessage += "Invalid environment variables:\n";
        invalidVars.forEach((varInfo) => {
          errorMessage += `  ${varInfo}\n`;
        });
        errorMessage += "\n";
      }

      errorMessage +=
        "Please check your .env file and ensure all required variables are set correctly.";

      throw new Error(errorMessage);
    }

    throw error;
  }
}

/**
 * Validated environment variables with type safety
 */
export const env = validateEnvironment();

/** Backend origin for Route Handlers and other server-only `fetch` (Compose service DNS, etc.). */
export function getServerApiBaseUrl(): string {
  return env.SERVER_API_BASE_URL ?? env.BASE_URL;
}

/**
 * Type-safe environment variable access
 * Usage: import { env } from '@/lib/env'
 * Access: env.AUTH_URL
 */
export type Env = typeof env;

/**
 * Checks if the application is running in development mode
 */
export const isDevelopment = env.NODE_ENV === "development";

/**
 * Checks if the application is running in production mode
 */
export const isProduction = env.NODE_ENV === "production";

/**
 * Checks if the application is running in test mode
 */
export const isTest = env.NODE_ENV === "test";
