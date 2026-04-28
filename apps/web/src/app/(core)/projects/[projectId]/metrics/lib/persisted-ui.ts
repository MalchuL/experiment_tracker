import type { PersistedMetricsUi } from "./types";
import { persistedMetricsUiKey } from "./constants";

/** Read persisted table prefs (not edit-session: row/column/tints). */
export function loadPersistedMetricsUi(projectId: string): PersistedMetricsUi | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(persistedMetricsUiKey(projectId));
    if (!raw) return null;
    return JSON.parse(raw) as PersistedMetricsUi;
  } catch {
    return null;
  }
}

/** Debounced caller saves after state changes (see page effect). */
export function savePersistedMetricsUi(projectId: string, data: PersistedMetricsUi): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(persistedMetricsUiKey(projectId), JSON.stringify(data));
  } catch {
    /* ignore quota / private mode */
  }
}
