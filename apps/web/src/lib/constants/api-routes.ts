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
  
      BY_ID: {
        GET: (teamId: string) => `/api/teams/${teamId}`,
        UPDATE: (teamId: string) => `/api/teams/${teamId}`,
        DELETE: (teamId: string) => `/api/teams/${teamId}`,
  
        LEAVE: (teamId: string) => `/api/teams/${teamId}/leave`,
  
        MEMBERS: {
          ADD: (teamId: string) => `/api/teams/${teamId}/members`,
          UPDATE_ROLE: (teamId: string, memberId: string) =>
            `/api/teams/${teamId}/members/${memberId}`,
          REMOVE: (teamId: string, memberId: string) =>
            `/api/teams/${teamId}/members/${memberId}`,
        },
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
        SETTINGS: (projectId: string) =>
          `/api/projects/${projectId}/settings`,
        SETTINGS_MAP: (projectId: string) =>
          `/api/projects/${projectId}/settings/map`,
        SETTINGS_BY_NAME: (projectId: string, name: string) =>
          `/api/projects/${projectId}/settings/${encodeURIComponent(name)}`,
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
      DOWNLOAD_AT_STEP: (experimentId: string, path: string, mediaType?: string) =>
        mediaType
          ? `/api/experiment-artifacts/${experimentId}/download-at-step?path=${encodeURIComponent(path)}&media_type=${encodeURIComponent(mediaType)}`
          : `/api/experiment-artifacts/${experimentId}/download-at-step?path=${encodeURIComponent(path)}`,
      DELETE_AT_STEP: (experimentId: string, path: string) =>
        `/api/experiment-artifacts/${experimentId}/at-step?path=${encodeURIComponent(path)}`,
      DELETE_ALL_AT_STEP: (experimentId: string) =>
        `/api/experiment-artifacts/${experimentId}/at-step`,
      UPSERT: "/api/experiment-artifacts/upsert",
      GET: (experimentId: string, name: string, filepath: string) =>
        `/api/experiment-artifacts/get?experiment_id=${encodeURIComponent(experimentId)}&name=${encodeURIComponent(name)}&filepath=${encodeURIComponent(filepath)}`,
      DOWNLOAD: (experimentId: string, name: string, filepath: string) =>
        `/api/experiment-artifacts/download?experiment_id=${encodeURIComponent(experimentId)}&name=${encodeURIComponent(name)}&filepath=${encodeURIComponent(filepath)}`,
      DOWNLOAD_ARCHIVE: (experimentId: string, name: string) =>
        `/api/experiment-artifacts/download/archive?experiment_id=${encodeURIComponent(experimentId)}&name=${encodeURIComponent(name)}`,
      DELETE: (experimentId: string, name: string, filepath?: string) =>
        filepath
          ? `/api/experiment-artifacts/delete?experiment_id=${encodeURIComponent(experimentId)}&name=${encodeURIComponent(name)}&filepath=${encodeURIComponent(filepath)}`
          : `/api/experiment-artifacts/delete?experiment_id=${encodeURIComponent(experimentId)}&name=${encodeURIComponent(name)}`,
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
  