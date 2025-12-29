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
    const envVariables = {
      // Base URL
      BASE_URL: process.env.NEXT_PUBLIC_BASE_URL,
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
