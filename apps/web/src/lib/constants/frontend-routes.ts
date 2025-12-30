export const FRONTEND_ROUTES = {
  ROOT: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  PROJECTS: "/projects",
  EXPERIMENTS: "/experiments",
  HYPOTHESES: "/hypotheses",
  TEAMS: "/teams",
  USERS: "/users",
  SETTINGS: "/settings",

  BY_ID: {
    PROJECT: (projectId: string) => `/projects/${projectId}`,
    EXPERIMENT: (experimentId: string) => `/experiments/${experimentId}`,
    HYPOTHESIS: (hypothesisId: string) => `/hypotheses/${hypothesisId}`,
    KANBAN: (projectId: string) => `/projects/${projectId}/kanban`,
    SCALARS: (projectId: string) => `/projects/${projectId}/scalars`,
    DAG: (projectId: string) => `/projects/${projectId}/dag`,
    SETTINGS: (projectId: string) => `/projects/${projectId}/settings`,
  },
} as const;