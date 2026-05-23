/**
 * Shared poll interval for ``GET /api/scalars/last_logged/{projectId}``.
 *
 * **Scalars** (`useScalarsLiveRefresh`): on timestamp advances, fetches incremental scalar
 * points (bounded by ``startTime``) and merges into the project scalars infinite cache. The
 * same sampled merge path is used by the manual refresh button; it caps each series at
 * ``maxPoints`` and always keeps the latest point.
 *
 * **Artifacts** (`useArtifactsLiveRefresh`): uses the same query key so React Query dedupes
 * network calls; when timestamps advance, fetches incremental artifact rows and merges them
 * into the project artifacts infinite cache.
 */
export const LAST_LOGGED_POLL_INTERVAL_MS = 30_000;

/**
 * How often the project experiments list is refetched (scalars page) so new runs appear
 * without a full reload. After each refetch, ``useProjectExperimentsPollSync`` compares
 * experiment ids + statuses to the previous snapshot; only when something changed does it
 * invalidate project scalars and artifacts queries (see that hook).
 */
export const EXPERIMENTS_LIST_POLL_INTERVAL_MS = 60_000;
