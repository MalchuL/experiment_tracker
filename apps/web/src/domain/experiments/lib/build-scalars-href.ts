import { encodeStringSelection } from "@/domain/scalars/utils";
import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

export function buildScalarsHref(projectId: string, experimentIds: string[]): string {
  const base = FRONTEND_ROUTES.PROJECT_PAGES.SCALARS(projectId);
  if (experimentIds.length === 0) return base;
  const params = new URLSearchParams();
  params.set("exp", encodeStringSelection(experimentIds));
  return `${base}?${params.toString()}`;
}
