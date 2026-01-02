/**
 * Backend API route constants
 * Generated from OpenAPI 3.1 specification
 * Centralized and type-safe access to all backend endpoints
 */

export const API_ROUTES = {
    ROOT: "/",
  
    AUTH: {
      LOGIN: "/auth/jwt/login",
      LOGOUT: "/auth/jwt/logout",
      REGISTER: "/auth/register",
  
      FORGOT_PASSWORD: "/auth/forgot-password",
      RESET_PASSWORD: "/auth/reset-password",
  
      REQUEST_VERIFY_TOKEN: "/auth/request-verify-token",
      VERIFY: "/auth/verify",
    },
  
    USERS: {
      ME: "/users/me",
  
      BY_ID: {
        GET: (id: string) => `/users/${id}`,
        PATCH: (id: string) => `/users/${id}`,
        DELETE: (id: string) => `/users/${id}`,
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
      STATS: "/api/dashboard/stats",
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
  