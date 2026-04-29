import { buildExperimentDetailsHref } from "@/lib/experiment-details-url";

export const FRONTEND_ROUTES = {
  ROOT: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  PROJECTS: "/projects",
  EXPERIMENTS: "/experiments",
  HYPOTHESES: "/hypotheses",
  TEAMS: "/teams",
  TEAM_BY_ID: (teamId: string) => `/teams/${teamId}`,
  PROFILE: "/profile",
  PROFILE_API_TOKENS: "/profile/api-tokens",
  USERS: "/users",
  SETTINGS: "/settings",
  
  PROJECT_PAGES: {
    OVERVIEW: (projectId: string) => `/projects/${projectId}`,
    EXPERIMENTS: (projectId: string) => `/projects/${projectId}/experiments`,
    METRICS: (projectId: string) => `/projects/${projectId}/metrics`,
    EXPERIMENT_ARTIFACTS: (projectId: string, experimentId: string) =>
      `/projects/${projectId}/experiments/${experimentId}/artifacts`,
    /** Ordered experiment ids (query `exp`, base64 JSON array). */
    EXPERIMENT_DETAILS: (projectId: string, experimentIds: string[]) =>
      buildExperimentDetailsHref(projectId, experimentIds),
    HYPOTHESES: (projectId: string) => `/projects/${projectId}/hypotheses`,
    HYPOTHESIS_BY_ID: (projectId: string, hypothesisId: string) => `/projects/${projectId}/hypotheses/${hypothesisId}`,
    KANBAN: (projectId: string) => `/projects/${projectId}/kanban`,
    SCALARS: (projectId: string) => `/projects/${projectId}/scalars`,
    DAG: (projectId: string) => `/projects/${projectId}/dag`,
    SETTINGS: (projectId: string) => `/projects/${projectId}/settings`,
  },
} as const;