/**
 * Shared poll interval for ``GET /api/scalars/last_logged/{projectId}``.
 *
 * **Scalars** (`useScalarsLiveRefresh`): on timestamp advances, fetches incremental scalar
 * points (bounded by ``startTime``) and merges into the project scalars infinite cache.
 *
 * **Artifacts** (`useArtifactsLiveRefresh`): uses the same query key so React Query dedupes
 * network calls; when timestamps advance, invalidates the project artifacts infinite query so
 * logged objects (images, etc.) refetch.
 */
export const LAST_LOGGED_POLL_INTERVAL_MS = 5000;

/**
 * How often the project experiments list is refetched (scalars page) so new runs appear
 * without a full reload. After each refetch, ``useProjectExperimentsPollSync`` compares
 * experiment ids + statuses to the previous snapshot; only when something changed does it
 * invalidate project scalars and artifacts queries (see that hook).
 */
export const EXPERIMENTS_LIST_POLL_INTERVAL_MS = 60_000;
