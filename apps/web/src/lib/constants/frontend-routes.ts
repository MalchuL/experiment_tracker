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
  
  PROJECT_PAGES: {
    OVERVIEW: (projectId: string) => `/projects/${projectId}`,
    EXPERIMENTS: (projectId: string) => `/projects/${projectId}/experiments`,
    HYPOTHESES: (projectId: string) => `/projects/${projectId}/hypotheses`,
    KANBAN: (projectId: string) => `/projects/${projectId}/kanban`,
    SCALARS: (projectId: string) => `/projects/${projectId}/scalars`,
    DAG: (projectId: string) => `/projects/${projectId}/dag`,
    SETTINGS: (projectId: string) => `/projects/${projectId}/settings`,
  },
} as const;