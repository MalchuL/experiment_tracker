import { encodeStringSelection } from "@/domain/scalars/utils/selection-codec";

/** Path + `exp` query (ordered experiment ids, same encoding as scalars page). */
export function buildExperimentDetailsHref(projectId: string, experimentIds: string[]): string {
  const exp = encodeStringSelection(experimentIds);
  const q = exp ? `?exp=${encodeURIComponent(exp)}` : "";
  return `/projects/${projectId}/experiments/details${q}`;
}
