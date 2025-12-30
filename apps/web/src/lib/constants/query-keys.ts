export const QUERY_KEYS = {
    PROJECTS: {
        LIST: "/projects",
        GET_BY_ID: (projectId: string) => `projects/${projectId}`,
    },
    DASHBOARD: {
        STATS: "/dashboard/stats",
    },
};