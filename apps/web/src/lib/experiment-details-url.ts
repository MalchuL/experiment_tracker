import { encodeStringSelection } from "@/domain/scalars/utils/selection-codec";

export type ExperimentDetailsTab =
  | "overview"
  | "metrics"
  | "artifacts"
  | "hparams"
  | "features";

/** Path + `exp` query (ordered experiment ids, same encoding as scalars page). */
export function buildExperimentDetailsHref(
  projectId: string,
  experimentIds: string[],
  options?: { detailsTab?: ExperimentDetailsTab }
): string {
  const params = new URLSearchParams();
  const exp = encodeStringSelection(experimentIds);
  if (exp) {
    params.set("exp", exp);
  }
  if (options?.detailsTab && options.detailsTab !== "overview") {
    params.set("detailsTab", options.detailsTab);
  }
  const q = params.toString();
  return `/projects/${projectId}/experiments/details${q ? `?${q}` : ""}`;
}
