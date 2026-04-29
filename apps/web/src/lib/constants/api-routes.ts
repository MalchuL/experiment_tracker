/**
 * Backend API route constants
 * Generated from OpenAPI 3.1 specification
 * Centralized and type-safe access to all backend endpoints
 */

export const API_ROUTES = {
    ROOT: "/",
  
    AUTH: {
      LOGIN: "api/auth/jwt/login",
      LOGOUT: "api/auth/jwt/logout",
      REGISTER: "api/auth/register",
  
      FORGOT_PASSWORD: "api/auth/forgot-password",
      RESET_PASSWORD: "api/auth/reset-password",
  
      REQUEST_VERIFY_TOKEN: "api/auth/request-verify-token",
      VERIFY: "api/auth/verify",
    },
  
    USERS: {
      ME: "api/users/me",
      API_TOKENS: {
        LIST: "api/users/me/api-tokens",
        CREATE: "api/users/me/api-tokens",
        BY_ID: {
          UPDATE: (tokenId: string) => `api/users/me/api-tokens/${tokenId}`,
          DELETE: (tokenId: string) => `api/users/me/api-tokens/${tokenId}`,
        },
      },
  
      BY_ID: {
        GET: (id: string) => `api/users/${id}`,
        PATCH: (id: string) => `api/users/${id}`,
        DELETE: (id: string) => `api/users/${id}`,
      },
    },
  
    TEAMS: {
      LIST: "/api/teams",
      CREATE: "/api/teams",
      PATCH: "/api/teams",
      BY_ID: {
        GET: (teamId: string) => `/api/teams/${teamId}`,
        MEMBERS: (teamId: string) => `/api/teams/${teamId}/members`,
        USERS_LOOKUP: (teamId: string) => `/api/teams/${teamId}/users/lookup`,
        DELETE: (teamId: string) => `/api/teams/${teamId}`,
      },
      MEMBERS: {
        ADD: "/api/teams/members",
        PATCH: "/api/teams/members",
        DELETE: "/api/teams/members",
      },
    },
  
    DASHBOARD: {
      STATS: (projectId: string) => `/api/dashboard/project/${projectId}/stats`,
    },
  
    PROJECTS: {
      LIST: "/api/projects",
      CREATE: "/api/projects",
  
      BY_ID: {
        GET: (projectId: string) => `/api/projects/${projectId}`,
        UPDATE: (projectId: string) => `/api/projects/${projectId}`,
        DELETE: (projectId: string) => `/api/projects/${projectId}`,
  
        EXPERIMENTS: (projectId: string) =>
          `/api/projects/${projectId}/experiments`,
        REORDER_EXPERIMENTS: (projectId: string) =>
          `/api/projects/${projectId}/experiments/reorder`,
  
        HYPOTHESES: (projectId: string) =>
          `/api/projects/${projectId}/hypotheses`,
        HYPOTHESES_BY_ID: (projectId: string, hypothesisId: string) =>
          `/api/projects/${projectId}/hypotheses/${hypothesisId}`,
        METRICS: (projectId: string) =>
          `/api/projects/${projectId}/metrics`,
        METRIC_LABELS: (projectId: string) =>
          `/api/projects/${projectId}/metric-labels`,
        METRICS_UNIQUE_DIMENSIONS: (projectId: string) =>
          `/api/projects/${projectId}/metrics/unique-dimensions`,
        METRICS_BY_LABEL: (projectId: string) =>
          `/api/projects/${projectId}/metrics/by-label`,
        SETTINGS: (projectId: string) =>
          `/api/projects/${projectId}/settings`,
        SETTINGS_MAP: (projectId: string) =>
          `/api/projects/${projectId}/settings/map`,
        SETTINGS_BY_NAME: (projectId: string, name: string) =>
          `/api/projects/${projectId}/settings/${encodeURIComponent(name)}`,
        MEMBERS: (projectId: string) => `/api/projects/${projectId}/members`,
        USERS_LOOKUP: (projectId: string) => `/api/projects/${projectId}/users/lookup`,
      },
    },
  
    EXPERIMENTS: {
      LIST: "/api/experiments",
      CREATE: "/api/experiments",
  
      RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) =>
        limit !== undefined && offset !== undefined
          ? `/api/experiments/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`
          : `/api/experiments/recent?projectId=${projectId}`,
  
      REORDER: "/api/experiments/reorder",
  
      BY_ID: {
        GET: (experimentId: string) =>
          `/api/experiments/${experimentId}`,
        UPDATE: (experimentId: string) =>
          `/api/experiments/${experimentId}`,
        DELETE: (experimentId: string) =>
          `/api/experiments/${experimentId}`,
  
        METRICS: (experimentId: string) =>
          `/api/experiments/${experimentId}/metrics`,
      },
    },
  
    HYPOTHESES: {
      LIST: "/api/hypotheses",
      CREATE: "/api/hypotheses",
  
      RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) =>
        limit !== undefined && offset !== undefined
          ? `/api/hypotheses/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`
          : `/api/hypotheses/recent?projectId=${projectId}`,
  
      BY_ID: {
        GET: (hypothesisId: string) =>
          `/api/hypotheses/${hypothesisId}`,
        UPDATE: (hypothesisId: string) =>
          `/api/hypotheses/${hypothesisId}`,
        DELETE: (hypothesisId: string) =>
          `/api/hypotheses/${hypothesisId}`,
      },
    },
  
    METRICS: {
      CREATE: "/api/metrics",
      DELETE: (metricId: string) => `/api/metrics/${metricId}`,
    },

    SCALARS: {
      BY_EXPERIMENT: {
        GET: (experimentId: string) => `/api/scalars/get/${experimentId}`,
      },
      BY_PROJECT: {
        GET: (projectId: string) => `/api/scalars/get/project/${projectId}`,
        LAST_LOGGED: (projectId: string) => `/api/scalars/last_logged/${projectId}`,
      },
    },

    EXPERIMENT_ARTIFACTS: {
      LIST_BY_EXPERIMENT: (experimentId: string) =>
        `/api/experiment-artifacts/experiments/${experimentId}`,
      LOG_AT_STEP: (experimentId: string) =>
        `/api/experiment-artifacts/${experimentId}/log-at-step`,
      BY_PROJECT: {
        GET_AT_STEP: (projectId: string) =>
          `/api/experiment-artifacts/projects/${projectId}/get-at-step`,
      },
      DOWNLOAD_AT_STEP: (
        experimentId: string,
        step: number,
        name: string,
        artifactType?: string
      ) => {
        const q = new URLSearchParams();
        q.set("step", String(step));
        q.set("name", name);
        if (artifactType) q.set("artifact_type", artifactType);
        return `/api/experiment-artifacts/${experimentId}/download-at-step?${q.toString()}`;
      },
      DELETE_AT_STEP: (experimentId: string, hash: string) =>
        `/api/experiment-artifacts/${experimentId}/at-step?hash=${encodeURIComponent(hash)}`,
      DELETE_ALL_AT_STEP: (experimentId: string) =>
        `/api/experiment-artifacts/${experimentId}/at-step`,
      UPSERT: "/api/experiment-artifacts/upsert",
      GET: (
        experimentId: string,
        filepath?: string,
        blobId?: string,
        artifactHash?: string
      ) => {
        const q = new URLSearchParams();
        q.set("experiment_id", experimentId);
        if (filepath) q.set("filepath", filepath);
        if (blobId) q.set("blob_id", blobId);
        if (artifactHash) q.set("artifact_hash", artifactHash);
        return `/api/experiment-artifacts/get?${q.toString()}`;
      },
      DOWNLOAD: (
        experimentId: string,
        filepath?: string,
        blobId?: string,
        artifactHash?: string
      ) => {
        const q = new URLSearchParams();
        q.set("experiment_id", experimentId);
        if (filepath) q.set("filepath", filepath);
        if (blobId) q.set("blob_id", blobId);
        if (artifactHash) q.set("artifact_hash", artifactHash);
        return `/api/experiment-artifacts/download?${q.toString()}`;
      },
      DOWNLOAD_ARCHIVE: (experimentId: string, name: string) =>
        `/api/experiment-artifacts/download/archive?experiment_id=${encodeURIComponent(experimentId)}&name=${encodeURIComponent(name)}`,
      DELETE: (
        experimentId: string,
        filepath?: string,
        blobId?: string,
        artifactHash?: string
      ) => {
        const q = new URLSearchParams();
        q.set("experiment_id", experimentId);
        if (filepath) q.set("filepath", filepath);
        if (blobId) q.set("blob_id", blobId);
        if (artifactHash) q.set("artifact_hash", artifactHash);
        return `/api/experiment-artifacts/delete?${q.toString()}`;
      },
    },
    PROJECT_ARTIFACTS: {
      ARTIFACTS: {
        GET: (projectId: string, artifactHash: string, contentType?: string) =>
          contentType
            ? `/api/project-artifacts/${projectId}/artifacts/${artifactHash}?contentType=${encodeURIComponent(contentType)}`
            : `/api/project-artifacts/${projectId}/artifacts/${artifactHash}`,
      },
    },
  } as const;
  
  /**
   * ---------- Type helpers ----------
   */
  
  export type ApiRouteKey = keyof typeof API_ROUTES;
  export type AuthApiRouteKey = keyof typeof API_ROUTES.AUTH;
  export type TeamApiRouteKey = keyof typeof API_ROUTES.TEAMS;
  export type ProjectApiRouteKey = keyof typeof API_ROUTES.PROJECTS;
  export type ExperimentApiRouteKey = keyof typeof API_ROUTES.EXPERIMENTS;
  export type HypothesisApiRouteKey = keyof typeof API_ROUTES.HYPOTHESES;
  
  /**
   * ---------- Utilities ----------
   */
  
  export function isApiRoute(path: string, route: string): boolean {
    return path === route;
  }
  
  export function isApiRoutePrefix(
    path: string,
    prefix: string,
  ): boolean {
    return path.startsWith(prefix);
  }
  