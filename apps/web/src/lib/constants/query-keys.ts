export const QUERY_KEYS = {
    PROJECTS: {
        LIST: "/projects",
        GET_BY_ID: (projectId: string) => `projects/${projectId}`,
    },
    DASHBOARD: {
        STATS: (projectId: string) => `dashboard/project/${projectId}/stats`,
    },
    EXPERIMENTS: {
        RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) => `experiments/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`,
        BY_PROJECT: (projectId: string) => `projects/${projectId}/experiments`,
        BY_ID: (experimentId: string) => `experiments/${experimentId}`,
    },
    HYPOTHESES: {
        RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) => `hypotheses/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`,
        BY_PROJECT: (projectId: string) => `projects/${projectId}/hypotheses`,
    },
    METRICS: {
        GET: (experimentId: string) => `experiments/${experimentId}/metrics`,
        BY_PROJECT: (projectId: string) => `projects/${projectId}/metrics`,
    },
    EVIDENCE: {
        GET: (experimentId: string) => `experiments/${experimentId}/evidence`,
    },
    DAG: {
        GET: (projectId: string) => `projects/${projectId}/dag`,
    },
};