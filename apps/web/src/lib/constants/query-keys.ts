export const QUERY_KEYS = {
    PROJECTS: {
        LIST: "/projects",
        GET_BY_ID: (projectId: string) => `projects/${projectId}`,
    },
    DASHBOARD: {
        STATS: "/dashboard/stats",
    },
    EXPERIMENTS: {
        RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) => `experiments/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`,
    },
    HYPOTHESES: {
        RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) => `hypotheses/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`,
    },
    METRICS: {
        GET: (experimentId: string) => `experiments/${experimentId}/metrics`,
    },
    EVIDENCE: {
        GET: (experimentId: string) => `experiments/${experimentId}/evidence`,
    },
    DAG: {
        GET: (projectId: string) => `projects/${projectId}/dag`,
    },
};