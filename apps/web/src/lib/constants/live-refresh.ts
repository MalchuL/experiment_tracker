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
