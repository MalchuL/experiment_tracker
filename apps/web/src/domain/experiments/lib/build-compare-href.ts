import { FRONTEND_ROUTES } from "@/lib/constants/frontend-routes";

export function buildCompareHref(projectId: string, experimentIds: string[]): string {
  const params = new URLSearchParams();
  experimentIds.forEach((id) => params.append("exp", id));
  const query = params.toString();
  return query
    ? `${FRONTEND_ROUTES.PROJECT_PAGES.COMPARE(projectId)}?${query}`
    : FRONTEND_ROUTES.PROJECT_PAGES.COMPARE(projectId);
}
