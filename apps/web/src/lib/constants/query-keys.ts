export const QUERY_KEYS = {
    TEAMS: {
        LIST: "teams",
        GET_BY_ID: (teamId: string) => `teams/${teamId}`,
        MEMBERS: (teamId: string) => `teams/${teamId}/members`,
    },
    PROJECT_MEMBERS: {
        LIST: (projectId: string) => `projects/${projectId}/members`,
    },
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
        SNAPSHOTS: (experimentIds: string[]) => `experiments/snapshots:${experimentIds.join(",")}`,
    },
    HYPOTHESES: {
        RECENT: (projectId: string, limit?: number | undefined, offset?: number | undefined) => `hypotheses/recent?projectId=${projectId}&limit=${limit}&offset=${offset}`,
        BY_PROJECT: (projectId: string) => `projects/${projectId}/hypotheses`,
    },
    REPORTS: {
        BY_PROJECT: (projectId: string) => `projects/${projectId}/reports`,
        BY_ID: (reportId: string) => `reports/${reportId}`,
    },
    METRICS: {
        GET: (experimentId: string) => `experiments/${experimentId}/metrics`,
        BY_PROJECT: (projectId: string) => `projects/${projectId}/metrics`,
        LABELS: (projectId: string) => `projects/${projectId}/metric-labels`,
        UNIQUE_DIMENSIONS: (projectId: string) =>
            `projects/${projectId}/metrics/unique-dimensions`,
        BY_LABEL_SNAPSHOT: (projectId: string, label: string, includeAll: boolean) =>
            `projects/${projectId}/metrics/by-label:${label}:inc:${includeAll ? "1" : "0"}`,
    },
    SCALARS: {
        BY_PROJECT: (projectId: string) => `projects/${projectId}/scalars`,
        LAST_LOGGED: (projectId: string) => `projects/${projectId}/scalars/last-logged`,
    },
    ARTIFACTS: {
        BY_PROJECT: (projectId: string) => `projects/${projectId}/artifacts`,
        NAMED_BY_EXPERIMENT: (experimentId: string) => `experiments/${experimentId}/artifacts/named`,
    },
    EVIDENCE: {
        GET: (experimentId: string) => `experiments/${experimentId}/evidence`,
    },
    DAG: {
        GET: (projectId: string) => `projects/${projectId}/dag`,
    },
    COMPARE: {
        SNAPSHOT_FILES_BY_EXPERIMENT: (experimentId: string | undefined) =>
            `compare/snapshot-files:${experimentId ?? ""}`,
        SNAPSHOT_FILES: (experimentIds: string[]) =>
            `compare/snapshot-files:${experimentIds.join(",")}`,
        SNAPSHOT_FILE_CONTENT: (
            experimentId: string | undefined,
            snapshotId: string | undefined,
            path: string | undefined,
            hash: string | undefined
        ) => `compare/snapshot-file-content:${experimentId ?? ""}:${snapshotId ?? ""}:${path ?? ""}:${hash ?? ""}`,
    },
};
