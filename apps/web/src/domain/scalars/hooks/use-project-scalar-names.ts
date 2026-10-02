import { LAST_LOGGED_POLL_INTERVAL_MS } from "@/lib/constants/live-refresh";
import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/lib/constants/query-keys";
import { scalarsService } from "../services";

export function useProjectScalarNames(projectId?: string, live = false): {
  scalarNames: string[];
  isLoading: boolean;
  refetch: () => Promise<unknown>;
} {
  const { data, isLoading, refetch } = useQuery({
    queryKey: projectId ? [QUERY_KEYS.SCALARS.NAMES(projectId)] : [],
    queryFn: () => scalarsService.getNamesByProject(projectId!),
    enabled: !!projectId,
    refetchInterval: live ? LAST_LOGGED_POLL_INTERVAL_MS : false,
  });

  return {
    scalarNames: data?.scalar_names ?? [],
    isLoading,
    refetch,
  };
}
