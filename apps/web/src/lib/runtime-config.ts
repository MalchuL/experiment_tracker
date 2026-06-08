/**
 * Runtime configuration shared between the Next.js server and browser.
 *
 * Unlike `NEXT_PUBLIC_*` variables, `PUBLIC_API_BASE_URL` is not compiled into
 * the JavaScript bundle during `next build`. The Next.js server reads it when
 * serving a page and `getRuntimeConfigScript()` exposes the intentionally public
 * value to browser code through `window.__EXPERIMENT_TRACKER_CONFIG__`.
 *
 * This allows the same built web image to run against different public backend
 * URLs without rebuilding the image.
 */

/**
 * Browser-reachable backend URL used when no runtime override is provided.
 */
const DEFAULT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";

/**
 * Values that the Next.js server is allowed to expose to browser JavaScript.
 *
 * Never add secrets or internal-only service URLs to this object. Everything in
 * this type is serialized into the HTML response and is visible to users.
 */
type RuntimeConfig = {
  publicApiBaseUrl: string;
};

/**
 * Type declaration for the runtime configuration object injected into the page
 * before the frontend application starts.
 */
declare global {
  interface Window {
    __EXPERIMENT_TRACKER_CONFIG__?: RuntimeConfig;
  }
}

/**
 * Validates and normalizes a browser-reachable API URL.
 *
 * Trimming a trailing slash keeps URL composition consistent across callers.
 * `new URL()` rejects missing or invalid URL values.
 *
 * @throws TypeError when the configured value is not a valid absolute URL
 */
function validatePublicApiBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/$/, "");
  return new URL(normalized).toString().replace(/\/$/, "");
}

/**
 * Returns the public backend URL for the current execution environment.
 *
 * On the server, the value comes from the container/process environment at
 * runtime. In the browser, it comes from the configuration script rendered by
 * the root Next.js layout.
 *
 * This URL is intentionally browser-visible and must be reachable from the
 * user's browser. Server-only routes should use `getServerApiBaseUrl()` from
 * `env.ts` so they can use private Compose DNS such as `http://backend:8000`.
 *
 * @throws Error when browser runtime configuration was not injected
 * @throws TypeError when the configured URL is invalid
 */
export function getPublicApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const value = window.__EXPERIMENT_TRACKER_CONFIG__?.publicApiBaseUrl;
    if (!value) {
      throw new Error("PUBLIC_API_BASE_URL is missing from runtime configuration");
    }
    return validatePublicApiBaseUrl(value);
  }

  return validatePublicApiBaseUrl(
    process.env.PUBLIC_API_BASE_URL ?? DEFAULT_PUBLIC_API_BASE_URL
  );
}

/**
 * Creates the inline JavaScript rendered by the root layout.
 *
 * Browser JavaScript cannot directly read Docker/container environment
 * variables. This script transfers only the approved public runtime values from
 * the Next.js server process into a global browser object before client modules
 * initialize.
 *
 * Less-than characters are escaped because an untrusted configured value
 * containing `</script>` could otherwise close the inline script element and
 * inject HTML or JavaScript.
 */
export function getRuntimeConfigScript(): string {
  const config: RuntimeConfig = {
    publicApiBaseUrl: getPublicApiBaseUrl(),
  };

  return `window.__EXPERIMENT_TRACKER_CONFIG__=${JSON.stringify(config).replaceAll("<", "\\u003c")};`;
}
