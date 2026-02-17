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
  